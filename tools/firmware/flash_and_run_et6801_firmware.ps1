[CmdletBinding()]
param(
    [string]$Project = '',
    [string]$Target = 'ET6801_SILICON_FLASH',
    [string]$Image = '',
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe',
    [string]$RtePath = '',
    [string]$JLink = '',
    [int]$JLinkSpeedKHz = 1000,
    [string]$JLinkSerial = '',
    [uint32]$FlashBase = 0x08000000,
    [uint32]$FlashSize = 0x00080000,
    [int]$KeilFlashTimeoutSeconds = 120,
    [int]$RunMilliseconds = 1500,
    [switch]$SkipFlash,
    [switch]$ConfirmPFlashProgram,
    [switch]$ConfirmRunControl,
    [switch]$PrepareOnly
)

# Generic ET6801 firmware Flash download and direct-vector run.
#
# Flash programming uses Keil UV4 -f with the ET6801.FLM algorithm, because the
# generic J-Link Cortex-M7 device has no ET6801 PFLASH loader. Run control uses
# J-Link to read the Flash vector table and jump through the reset handler into
# the firmware (startup -> main). This script is firmware-neutral: it proves the
# CPU is executing Flash code after the jump, but does not check any per-firmware
# symbol. Functional proof (for example UART HELLO) belongs to the PC side.

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')

if ([string]::IsNullOrWhiteSpace($Project)) {
    $Project = Join-Path $codeRoot 'firmware\build\et6801\ET6801_Automated_Test.uvprojx'
}
if ([string]::IsNullOrWhiteSpace($JLink)) {
    $JLink = Join-Path $projectRoot 'workspaces\et6801_gpio_toggle\tools\jlink_7_22b\JLink.exe'
}

$flashLow = [uint32]$FlashBase
$flashHigh = [uint32]($FlashBase + $FlashSize)

# The generated project and its generation record are one atomic input. Refuse
# a Keil-GUI-edited or otherwise stale project before inspecting its Flash
# settings. This prevents the FLM configuration from silently moving between
# targets after the generated project is opened and saved.
$projectItem = Get-Item -LiteralPath $Project -ErrorAction Stop
$Project = $projectItem.FullName
$generationRecordPath = [System.IO.Path]::ChangeExtension(
    $projectItem.FullName,
    '.generation.json'
)
if (-not (Test-Path -LiteralPath $generationRecordPath -PathType Leaf)) {
    throw "Generated-project record not found: $generationRecordPath. Rebuild or regenerate the Keil project first."
}
$generationRecord = Get-Content -LiteralPath $generationRecordPath -Raw |
    ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace([string]$generationRecord.sha256)) {
    throw "Generated-project record has no sha256: $generationRecordPath"
}
$recordedOutput = [System.IO.Path]::GetFullPath(
    [string]$generationRecord.output
)
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $recordedOutput,
        $projectItem.FullName
    )) {
    throw "Generated-project record belongs to another project: $recordedOutput"
}
$projectHash = (Get-FileHash -LiteralPath $projectItem.FullName -Algorithm SHA256).Hash
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $projectHash,
        [string]$generationRecord.sha256
    )) {
    throw ("Generated Keil project drift detected: expected {0}, actual {1}. " +
        "Rebuild or regenerate the project; do not repair the generated .uvprojx in Keil GUI.") -f `
        $generationRecord.sha256, $projectHash
}
$jlinkSettingsRecord = $generationRecord.support_files.jlink_settings
if (-not $jlinkSettingsRecord) {
    throw "Generation record has no J-Link settings binding: $generationRecordPath"
}
$jlinkSettings = Join-Path $projectItem.DirectoryName 'JLinkSettings.ini'
$recordedJLinkSettings = [System.IO.Path]::GetFullPath(
    [string]$jlinkSettingsRecord.output
)
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $recordedJLinkSettings,
        $jlinkSettings
    )) {
    throw "J-Link settings record points outside the generated project: $recordedJLinkSettings"
}
if (-not (Test-Path -LiteralPath $jlinkSettings -PathType Leaf)) {
    throw "Generated J-Link settings are missing: $jlinkSettings"
}
$jlinkSettingsHash = (
    Get-FileHash -LiteralPath $jlinkSettings -Algorithm SHA256
).Hash
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $jlinkSettingsHash,
        [string]$jlinkSettingsRecord.sha256
    )) {
    throw ("Generated J-Link settings drift detected: expected {0}, actual {1}." -f `
        $jlinkSettingsRecord.sha256, $jlinkSettingsHash)
}
$jlinkSettingsText = Get-Content -LiteralPath $jlinkSettings -Raw
if ($jlinkSettingsText -notmatch '(?m)^\s*Override\s*=\s*1\s*$' -or
    $jlinkSettingsText -notmatch '(?m)^\s*Device\s*=\s*"Cortex-M7"\s*$') {
    throw "J-Link settings do not enforce the ET6801 Cortex-M7 route: $jlinkSettings"
}
$keilOptionsRecord = $generationRecord.support_files.keil_options
if (-not $keilOptionsRecord) {
    throw "Generation record has no Keil options binding: $generationRecordPath"
}
$keilOptions = [System.IO.Path]::ChangeExtension(
    $projectItem.FullName,
    '.uvoptx'
)
$recordedKeilOptions = [System.IO.Path]::GetFullPath(
    [string]$keilOptionsRecord.output
)
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $recordedKeilOptions,
        $keilOptions
    )) {
    throw "Keil options record points outside the generated project: $recordedKeilOptions"
}
if (-not (Test-Path -LiteralPath $keilOptions -PathType Leaf)) {
    throw "Generated Keil options are missing: $keilOptions"
}
$keilOptionsHash = (
    Get-FileHash -LiteralPath $keilOptions -Algorithm SHA256
).Hash
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $keilOptionsHash,
        [string]$keilOptionsRecord.sha256
    )) {
    throw ("Generated Keil options drift detected: expected {0}, actual {1}." -f `
        $keilOptionsRecord.sha256, $keilOptionsHash)
}
[xml]$keilOptionsXml = Get-Content -LiteralPath $keilOptions
$keilOptionTarget = $keilOptionsXml.ProjectOpt.Target |
    Where-Object TargetName -eq $Target
if (-not $keilOptionTarget) {
    throw "Keil options target not found: $Target"
}
$keilMonitor = [string]$keilOptionTarget.TargetOption.DebugOpt.pMon
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $keilMonitor,
        'Segger\JL2CM3.dll'
    )) {
    throw ("Keil options target '{0}' does not select the Segger J-Link driver." -f `
        $Target)
}
$keilJLinkRegistry = $keilOptionTarget.TargetOption.TargetDriverDllRegistry.SetRegEntry |
    Where-Object Key -eq 'JL2CM3'
$keilULinkRegistry = $keilOptionTarget.TargetOption.TargetDriverDllRegistry.SetRegEntry |
    Where-Object Key -eq 'UL2CM3'
$keilJLinkFlash = [string]$keilJLinkRegistry.Name
$keilULinkFlash = [string]$keilULinkRegistry.Name
if (-not $keilJLinkRegistry -or -not $keilULinkRegistry -or
    $keilJLinkFlash -notmatch '-FN1' -or
    $keilJLinkFlash -notmatch 'ET6801\.FLM' -or
    $keilJLinkFlash -notmatch '-FS08000000' -or
    $keilJLinkFlash -notmatch '-FL080000' -or
    $keilULinkFlash -notmatch 'ET6801\.FLM') {
    throw ("Keil options target '{0}' does not bind ET6801.FLM to PFLASH 0x08000000..0x0807FFFF." -f `
        $Target)
}
$keilJLinkSerialMatch = [regex]::Match(
    $keilJLinkFlash,
    '(?:^|\s)-U(\d+)(?:\s|$)'
)
if (-not $keilJLinkSerialMatch.Success) {
    throw ("Keil options target '{0}' does not bind a J-Link probe serial." -f `
        $Target)
}
$configuredJLinkSerial = $keilJLinkSerialMatch.Groups[1].Value
if ([string]::IsNullOrWhiteSpace($JLinkSerial)) {
    $JLinkSerial = $configuredJLinkSerial
} else {
    # J-Link uses -1 for automatic probe selection, while Keil persists the
    # same sentinel as UINT32_MAX. Canonicalize only this documented pair;
    # every concrete serial number must still match exactly.
    $runControlAutoSerial = '-1'
    $keilAutoSerial = [uint32]::MaxValue.ToString(
        [System.Globalization.CultureInfo]::InvariantCulture
    )
    $requestedJLinkSerial = $JLinkSerial.Trim()
    if ([System.StringComparer]::Ordinal.Equals(
            $requestedJLinkSerial,
            $runControlAutoSerial
        )) {
        $requestedJLinkSerial = $keilAutoSerial
    }

    if (-not [System.StringComparer]::Ordinal.Equals(
        $requestedJLinkSerial,
        $configuredJLinkSerial
    )) {
        throw ("J-Link serial mismatch: Keil Flash uses '{0}', but run-control requested '{1}'." -f `
            $configuredJLinkSerial, $JLinkSerial)
    }

    # Keep Flash and run-control on the exact serial representation generated
    # into Keil options after the equivalence check has passed.
    $JLinkSerial = $configuredJLinkSerial
}

# Bound the Flash target so a wrong manifest can never erase an unexpected range.
[xml]$projectXml = Get-Content -LiteralPath $projectItem.FullName
$targetNode = $projectXml.Project.Targets.Target | Where-Object TargetName -eq $Target
if (-not $targetNode) {
    throw "Keil target not found: $Target"
}
$common = $targetNode.TargetOption.TargetCommonOption
$driver = [string]$common.FlashDriverDll
$flashUpdate = [string]$targetNode.TargetOption.Utilities.Flash1.UpdateFlashBeforeDebugging
$expectedFs = ('-FS{0:X8}' -f $flashLow)
$expectedFl = ('-FL{0:X6}' -f $FlashSize)
if ($common.Device -ne 'ET6801' -or
    $common.Vendor -ne 'ETMCU' -or
    [string]$common.PackID -notmatch '^ETMCU\.ET6801_DFP\.' -or
    [string]$common.Cpu -notmatch 'IROM\(0x08000000,0x80000\)' -or
    [string]$common.RegisterFile -notmatch 'Device:ET6801' -or
    [string]$common.TargetStatus.InvalidFlash -ne '0' -or
    $flashUpdate -ne '1' -or
    $driver -notmatch 'ET6801\.FLM' -or
    $driver -notmatch [regex]::Escape($expectedFs) -or
    $driver -notmatch [regex]::Escape($expectedFl)) {
    throw ("Refusing download: target '{0}' is not an enabled ETMCU ET6801 PFLASH target bounded to {1:X8}..{2:X8} with ET6801.FLM." -f `
        $Target, $flashLow, ($flashHigh - 1))
}

# Keil "-f" always downloads the selected target's configured AXF. Derive that
# path from the project and require any caller-supplied -Image to name exactly
# the same file, so evidence can never describe a different artifact.
$outputDirectory = [string]$common.OutputDirectory
$outputName = [string]$common.OutputName
if ([string]::IsNullOrWhiteSpace($outputDirectory) -or
    [string]::IsNullOrWhiteSpace($outputName)) {
    throw "Keil target '$Target' has no output directory or output name."
}
$configuredImage = [System.IO.Path]::GetFullPath(
    (Join-Path $projectItem.DirectoryName (
        Join-Path $outputDirectory "$outputName.axf"
    ))
)
if ([string]::IsNullOrWhiteSpace($Image)) {
    $Image = $configuredImage
} else {
    $Image = [System.IO.Path]::GetFullPath($Image)
    if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
            $Image,
            $configuredImage
        )) {
        throw ("Image mismatch: Keil target '{0}' downloads '{1}', but -Image names '{2}'." -f `
            $Target, $configuredImage, $Image)
    }
}
if (-not (Test-Path -LiteralPath $Image -PathType Leaf)) {
    throw "Keil target output is missing: $Image. Build target '$Target' first."
}
$imageHash = (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash

if ($PrepareOnly) {
    $prepareRecord = [ordered]@{
        Action = 'Keil ET6801.FLM PFLASH download, then J-Link direct-vector run'
        Project = (Resolve-Path $Project).Path
        Project_SHA256 = $projectHash
        Generation_Record = $generationRecordPath
        Target = $Target
        Image = $Image
        Image_SHA256 = $imageHash
        JLinkSettings = $jlinkSettings
        JLinkSettings_SHA256 = $jlinkSettingsHash
        KeilOptions = $keilOptions
        KeilOptions_SHA256 = $keilOptionsHash
        JLinkSerial = $JLinkSerial
        FlashRange = ('0x{0:X8}..0x{1:X8}' -f $flashLow, ($flashHigh - 1))
        FlashAlgorithm = 'ET6801.FLM'
        SkipFlash = [bool]$SkipFlash
        Destructive = (-not $SkipFlash)
        RunControl = 'Writes CORE0 MSP/PC/xPSR and resumes from the Flash reset vector.'
        Recovery = 'Re-flash a known-good image, or halt/reset/power-cycle the ET6801 prototype.'
    }

    # Emit one stable key/value record per line. Format-List wraps long hashes at
    # the host width, which makes captured evidence depend on terminal geometry.
    $prepareRecord.GetEnumerator() | ForEach-Object {
        Write-Output ('{0}={1}' -f $_.Key, $_.Value)
    }
    exit 0
}

foreach ($required in @($Keil, $JLink, $Project)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required file not found: $required"
    }
}

if (-not $SkipFlash) {
    # ET6801 FPGA PFLASH programming depends on the prototype logic and BootROM
    # initialization completed earlier in this exact Pipeline run. Their PASS
    # manifests are the only accepted proof; a direct subscript call fails here.
    $runRoot = Assert-EtPipelineStagePassed -CodeRoot $codeRoot -StageName 'deploy_bitfile'
    $verifiedRunRoot = Assert-EtPipelineStagePassed -CodeRoot $codeRoot -StageName 'deploy_bootrom'
    if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals($runRoot, $verifiedRunRoot)) {
        throw 'FPGA prerequisite evidence does not belong to one Pipeline run.'
    }
}
else {
    # Run-only control does not alter PFLASH and therefore does not require the
    # deployment prerequisites, but it still writes evidence to the active run.
    $runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'firmware_flash_run'
}

$artifactDirectory = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'deploy_firmware'

# ---- Step 1: Flash download via Keil UV4 -f (ET6801.FLM) ----
if (-not $SkipFlash) {
    if (-not $ConfirmPFlashProgram) {
        throw 'Destructive Flash gate not confirmed. Re-run with -ConfirmPFlashProgram (or -SkipFlash to only run).'
    }
    if (Get-Process UV4 -ErrorAction SilentlyContinue) {
        throw 'Keil UV4 is already running. Close it before command-line Flash programming.'
    }

    $projectItem = Get-Item -LiteralPath $Project
    $projectDir = $projectItem.DirectoryName
    $localLog = 'keil_cli_flash.log'
    $localLogPath = Join-Path $projectDir $localLog
    $keilLog = Join-Path $artifactDirectory $localLog
    if (-not [string]::IsNullOrWhiteSpace($RtePath)) {
        if (-not (Test-Path -LiteralPath $RtePath -PathType Container)) {
            throw "Arm Pack root not found: $RtePath"
        }
        $env:RTEPATH = (Resolve-Path -LiteralPath $RtePath).Path
    }

    Push-Location $projectDir
    try {
        Remove-Item -LiteralPath $localLogPath -Force -ErrorAction SilentlyContinue
        $process = Start-Process -FilePath $Keil `
            -ArgumentList @('-f', $projectItem.Name, '-t', $Target, '-sg', '-o', $localLog) `
            -WorkingDirectory $projectDir `
            -WindowStyle Hidden `
            -PassThru
        $deadline = (Get-Date).AddSeconds($KeilFlashTimeoutSeconds)
        $terminalLogSeen = $false
        while ((Get-Date) -lt $deadline) {
            if (Test-Path -LiteralPath $localLogPath -PathType Leaf) {
                $liveLog = Get-Content -LiteralPath $localLogPath -Raw
                if ($liveLog -match '(?i)Verify OK|Flash Download failed|cannot load|programming failed|verify failed|error:') {
                    $terminalLogSeen = $true
                    break
                }
            }
            if ($process.HasExited) {
                break
            }
            Start-Sleep -Milliseconds 250
            $process.Refresh()
        }
        if (-not $process.HasExited) {
            # UV4 -f can leave its GUI server loop alive after the log already
            # contains the terminal Flash result. Stop only the process that
            # this invocation created; never sweep unrelated Keil processes.
            Stop-Process -Id $process.Id -Force
            $process.WaitForExit()
        }
        $keilExit = if ($terminalLogSeen) { 0 } else { $process.ExitCode }
        if (-not $terminalLogSeen -and (Get-Date) -ge $deadline) {
            throw "Keil Flash operation did not reach a terminal log result within $KeilFlashTimeoutSeconds seconds."
        }
        if (-not (Test-Path -LiteralPath $localLogPath)) {
            throw "Keil exited with code $keilExit but did not create its flash log: $localLogPath"
        }
        Copy-Item -LiteralPath $localLogPath -Destination $keilLog -Force
    }
    finally {
        Pop-Location
    }

    $logText = Get-Content -LiteralPath $keilLog -Raw
    $logText | Write-Output
    if ($keilExit -ne 0 -or
        $logText -match '(?i)flash download failed|cannot load|programming failed|verify failed|error:') {
        throw "ET6801 PFLASH programming failed with exit code $keilExit. Log: $keilLog"
    }
    $missingFlashEvidence = @(
        'Erase Done'
        'Programming Done'
        'Verify OK'
    ) | Where-Object { $logText -notmatch [regex]::Escape($_) }
    if ($missingFlashEvidence.Count -ne 0) {
        throw ("Keil Flash log has no positive erase/program/verify evidence ({0}). Log: {1}" -f `
            ($missingFlashEvidence -join ', '), $keilLog)
    }

    $projectHashAfterFlash = (
        Get-FileHash -LiteralPath $projectItem.FullName -Algorithm SHA256
    ).Hash
    if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
            $projectHashAfterFlash,
            [string]$generationRecord.sha256
        )) {
        throw ("Keil changed the generated project during Flash download. " +
            "Regenerate before the next operation. Log: $keilLog")
    }
    $jlinkSettingsHashAfterFlash = (
        Get-FileHash -LiteralPath $jlinkSettings -Algorithm SHA256
    ).Hash
    if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
            $jlinkSettingsHashAfterFlash,
            [string]$jlinkSettingsRecord.sha256
        )) {
        throw ("Keil changed JLinkSettings.ini during Flash download. " +
            "Regenerate before the next operation. Log: $keilLog")
    }
    $keilOptionsHashAfterFlash = (
        Get-FileHash -LiteralPath $keilOptions -Algorithm SHA256
    ).Hash
    if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
            $keilOptionsHashAfterFlash,
            [string]$keilOptionsRecord.sha256
        )) {
        throw ("Keil changed the generated .uvoptx during Flash download. " +
            "Regenerate before the next operation. Log: $keilLog")
    }
}

# ---- Step 2: J-Link direct-vector run through the Flash reset handler ----
if (-not $ConfirmRunControl) {
    throw 'Run-control gate not confirmed. Re-run with -ConfirmRunControl.'
}
if (Get-Process JLink -ErrorAction SilentlyContinue) {
    throw 'J-Link Commander is already running. Close it before deterministic run-control.'
}

function Invoke-JLinkCommandFile {
    param(
        [Parameter(Mandatory)][string]$CommandFile,
        [Parameter(Mandatory)][string]$Stdout,
        [Parameter(Mandatory)][string]$Stderr
    )
    $arguments = @(
        '-NoGui', '1',
        '-Device', 'Cortex-M7',
        '-If', 'JTAG',
        '-JTAGConf', '-1,-1',
        '-Speed', [string]$JLinkSpeedKHz,
        '-AutoConnect', '1'
    )
    if (-not [string]::IsNullOrWhiteSpace($JLinkSerial)) {
        $arguments += @('-SelectEmuBySN', $JLinkSerial)
    }
    $arguments += @('-CommanderScript', $CommandFile)

    $process = Start-Process -FilePath $JLink `
        -ArgumentList $arguments `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden -Wait -PassThru

    $text = Get-Content -LiteralPath $Stdout -Raw
    $text | Write-Output
    if ($process.ExitCode -ne 0 -or
        $text -match 'Cannot connect|Could not connect|FAILED:|Failed to open|Error while') {
        throw "J-Link command failed with exit code $($process.ExitCode). Log: $Stdout"
    }
    if ($text -notmatch 'Cortex-M7 identified') {
        throw "J-Link did not identify the ET6801 Cortex-M7. Log: $Stdout"
    }
    return $text
}

# Read the Flash vector table (initial MSP + reset handler).
$readCommand = Join-Path $artifactDirectory 'read_flash_vectors.jlink'
@(
    'exec DisableAutoUpdateFW'
    'h'
    ('mem32 0x{0:X8}, 2' -f $flashLow)
    'exit'
) | Set-Content -LiteralPath $readCommand -Encoding ASCII
$readText = Invoke-JLinkCommandFile `
    -CommandFile $readCommand `
    -Stdout (Join-Path $artifactDirectory 'read_flash_vectors.stdout.log') `
    -Stderr (Join-Path $artifactDirectory 'read_flash_vectors.stderr.log')

$vectorPattern = ('{0:X8}\s*=\s*([0-9A-Fa-f]{{8}})\s+([0-9A-Fa-f]{{8}})' -f $flashLow)
$vectorMatch = [regex]::Match($readText, $vectorPattern)
if (-not $vectorMatch.Success) {
    throw 'Could not parse the Flash vector table from J-Link output.'
}
$initialSp = [Convert]::ToUInt32($vectorMatch.Groups[1].Value, 16)
$resetHandler = [Convert]::ToUInt32($vectorMatch.Groups[2].Value, 16)
if ($initialSp -lt 0x20000000 -or $initialSp -gt 0x20020000) {
    throw ('Invalid Flash initial MSP: 0x{0:X8}' -f $initialSp)
}
if ($resetHandler -lt ($flashLow + 1) -or $resetHandler -gt $flashHigh -or
    ($resetHandler -band 1) -eq 0) {
    throw ('Invalid Flash reset handler: 0x{0:X8}' -f $resetHandler)
}

# Jump through the reset handler, let the firmware run, then sample the PC.
$runCommand = Join-Path $artifactDirectory 'direct_jump_run.jlink'
@(
    'exec DisableAutoUpdateFW'
    'r'
    'h'
    ('w4 0xE000ED08, 0x{0:X8}' -f $flashLow)
    ('wreg MSP, 0x{0:X8}' -f $initialSp)
    'wreg PSP, 0x00000000'
    'wreg XPSR, 0x01000000'
    ('SetPC 0x{0:X8}' -f $resetHandler)
    'g'
    "Sleep $RunMilliseconds"
    'h'
    'regs'
    'g'
    'exit'
) | Set-Content -LiteralPath $runCommand -Encoding ASCII
$runText = Invoke-JLinkCommandFile `
    -CommandFile $runCommand `
    -Stdout (Join-Path $artifactDirectory 'direct_jump_run.stdout.log') `
    -Stderr (Join-Path $artifactDirectory 'direct_jump_run.stderr.log')

$pcMatches = [regex]::Matches(
    $runText,
    'PC\s*=\s*(?:0x)?([0-9A-Fa-f]{8})',
    'IgnoreCase'
)
if ($pcMatches.Count -eq 0) {
    throw 'Could not read PC after the direct-vector jump.'
}
$pcMatch = $pcMatches[$pcMatches.Count - 1]
$pc = [Convert]::ToUInt32($pcMatch.Groups[1].Value, 16)
$pcInFlash = ($pc -ge $flashLow -and $pc -lt $flashHigh)
$pcInRam = ($pc -ge 0x20000000 -and $pc -lt 0x20020000)
if (-not ($pcInFlash -or $pcInRam)) {
    throw ('After the jump the CPU PC 0x{0:X8} is not in ET6801 Flash or RAM; firmware is not running.' -f $pc)
}

$record = [ordered]@{
    schemaVersion = 1
    time = Get-Date -Format 'yyyy-MM-dd HH:mm:ss K'
    result = 'PASS'
    target = 'ET6801 prototype CORE0'
    operation = if ($SkipFlash) { 'Flash direct-vector run only' } else { 'ET6801.FLM PFLASH download and direct-vector run' }
    destructive = (-not $SkipFlash)
    project = (Resolve-Path $Project).Path
    projectSha256 = $projectHash
    generationRecord = $generationRecordPath
    keilTarget = $Target
    image = $Image
    imageSha256 = $imageHash
    jlinkSettings = $jlinkSettings
    jlinkSettingsSha256 = $jlinkSettingsHash
    keilOptions = $keilOptions
    keilOptionsSha256 = $keilOptionsHash
    jlinkSerial = $JLinkSerial
    flashRange = ('0x{0:X8}..0x{1:X8}' -f $flashLow, ($flashHigh - 1))
    initialMsp = ('0x{0:X8}' -f $initialSp)
    resetHandler = ('0x{0:X8}' -f $resetHandler)
    pcAfterJump = ('0x{0:X8}' -f $pc)
    pcRegion = if ($pcInFlash) { 'flash' } else { 'ram' }
    runMilliseconds = $RunMilliseconds
    recovery = 'Re-flash a known-good image, or halt/reset/power-cycle the ET6801 prototype.'
}
$record | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath (Join-Path $artifactDirectory 'manifest.json') -Encoding UTF8

Write-Output ('ET6801_FLASH_RUN_PASS|reset=0x{0:X8}|pc=0x{1:X8}|region={2}|artifact={3}' -f `
    $resetHandler, $pc, $record.pcRegion, $artifactDirectory)
