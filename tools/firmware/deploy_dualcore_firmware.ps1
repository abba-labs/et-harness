[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Manifest,

    [ValidateSet('Build', 'Deploy', 'DryRun')]
    [string]$Action = 'DryRun',

    [string]$Keil = '',
    [string]$RtePath = '',
    [string]$JLink = '',
    [string]$JLinkSerial = '',
    [string]$SerialPort = '',

    [ValidateRange(1, 20)]
    [int]$Repeat = 1,

    [switch]$ConfirmHardware
)

# Generic dual-core firmware build and deployment stage.
# Chip addresses, projects, AP routes and verification text come only from the
# reviewed chip manifest. Local tools and physical endpoints remain parameters.

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')

function Resolve-CodePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,

        [switch]$AllowMissing
    )

    if ([System.IO.Path]::IsPathRooted($RelativePath)) {
        throw "Dual-core manifest paths must be repository-relative: $RelativePath"
    }

    $resolved = [System.IO.Path]::GetFullPath((Join-Path $codeRoot $RelativePath))
    $prefix = $codeRoot + [System.IO.Path]::DirectorySeparatorChar

    if (-not $resolved.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Dual-core manifest path escapes the repository: $RelativePath"
    }

    if ((-not $AllowMissing) -and (-not (Test-Path -LiteralPath $resolved))) {
        throw "Dual-core manifest path does not exist: $resolved"
    }

    return $resolved
}

function Convert-HexUInt32 {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Value,

        [Parameter(Mandatory = $true)]
        [string]$Field
    )

    $text = [string]$Value

    if ($text -notmatch '^0x[0-9A-Fa-f]{1,8}$') {
        throw "$Field must be a 32-bit hexadecimal string."
    }

    return [Convert]::ToUInt32($text.Substring(2), 16)
}

function Get-ValidatedManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $manifestPath = Resolve-CodePath -RelativePath $Path
    $profile = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

    if ($profile.schema -ne 'et-dualcore-deploy/v1') {
        throw 'Dual-core deployment manifest schema must be et-dualcore-deploy/v1.'
    }

    if (($profile.cores.Count -ne 2) -or
        (@($profile.cores.id | Sort-Object) -join ',') -ne 'core0,core1') {
        throw 'Dual-core deployment manifest must define exactly core0 and core1.'
    }

    if ($profile.program_method -notin @('jlink_ram', 'keil_flash')) {
        throw "Unsupported dual-core program method: $($profile.program_method)"
    }

    foreach ($core in $profile.cores) {
        foreach ($field in @(
                'build_manifest',
                'project',
                'target',
                'output_axf',
                'output_bin',
                'jlink_script'
            )) {
            if ([string]::IsNullOrWhiteSpace([string]$core.$field)) {
                throw "Dual-core manifest $($core.id).$field is required."
            }
        }

        [void](Resolve-CodePath -RelativePath ([string]$core.build_manifest))
        [void](Resolve-CodePath -RelativePath ([string]$core.jlink_script))
        [void](Resolve-CodePath -RelativePath ([string]$core.project) -AllowMissing)
        [void](Resolve-CodePath -RelativePath ([string]$core.output_axf) -AllowMissing)
        [void](Resolve-CodePath -RelativePath ([string]$core.output_bin) -AllowMissing)
        [void](Convert-HexUInt32 -Value $core.load_address -Field "$($core.id).load_address")
        [void](Convert-HexUInt32 -Value $core.code_limit -Field "$($core.id).code_limit")
        [void](Convert-HexUInt32 -Value $core.stack_low -Field "$($core.id).stack_low")
        [void](Convert-HexUInt32 -Value $core.stack_high -Field "$($core.id).stack_high")
    }

    return $profile
}

function Get-ImageVector {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Core
    )

    $binary = Resolve-CodePath -RelativePath ([string]$Core.output_bin)
    $bytes = [System.IO.File]::ReadAllBytes($binary)

    if ($bytes.Length -lt 8) {
        throw "Image is too small to contain a vector table: $binary"
    }

    $msp = [BitConverter]::ToUInt32($bytes, 0)
    $resetHandler = [BitConverter]::ToUInt32($bytes, 4)
    $stackLow = Convert-HexUInt32 -Value $Core.stack_low -Field "$($Core.id).stack_low"
    $stackHigh = Convert-HexUInt32 -Value $Core.stack_high -Field "$($Core.id).stack_high"
    $loadAddress = Convert-HexUInt32 -Value $Core.load_address -Field "$($Core.id).load_address"
    $codeLimit = Convert-HexUInt32 -Value $Core.code_limit -Field "$($Core.id).code_limit"
    $thumbEntry = (($resetHandler % 2) -eq 1)
    $resetAddress = if ($thumbEntry) { $resetHandler - 1 } else { $resetHandler }

    if (($msp -lt $stackLow) -or ($msp -ge $stackHigh)) {
        throw ('{0} MSP 0x{1:X8} is outside 0x{2:X8}..0x{3:X8}.' -f `
            $Core.id, $msp, $stackLow, $stackHigh)
    }

    if ((-not $thumbEntry) -or
        ($resetAddress -lt $loadAddress) -or ($resetAddress -ge $codeLimit)) {
        throw ('{0} reset handler 0x{1:X8} is outside 0x{2:X8}..0x{3:X8}.' -f `
            $Core.id, $resetHandler, $loadAddress, $codeLimit)
    }

    return [ordered]@{
        binary = $binary
        sha256 = (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash
        length = $bytes.Length
        msp = $msp
        reset_handler = $resetHandler
        load_address = $loadAddress
    }
}

function Invoke-CoreBuild {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Core,

        [Parameter(Mandatory = $true)]
        [string]$ArtifactDirectory
    )

    $generator = Join-Path $codeRoot 'tools\firmware\generate_keil_project.py'
    $python = Join-Path $codeRoot '.venv\Scripts\python.exe'

    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        $python = (Get-Command python -ErrorAction Stop).Source
    }

    $buildManifest = Resolve-CodePath -RelativePath ([string]$Core.build_manifest)
    $project = Resolve-CodePath -RelativePath ([string]$Core.project) -AllowMissing
    $projectDirectory = Split-Path -Parent $project
    $logName = "keil_$($Core.id)_$($Core.target).log"
    $localLog = Join-Path $projectDirectory $logName
    $artifactLog = Join-Path $ArtifactDirectory $logName
    $generatorLog = Join-Path $ArtifactDirectory "generator_$($Core.id).log"

    $generatorOutput = & $python $generator --manifest $buildManifest
    $generatorOutput | Set-Content -LiteralPath $generatorLog -Encoding UTF8

    if ($LASTEXITCODE -ne 0) {
        throw "Keil project generation failed for $($Core.id). Log: $generatorLog"
    }

    if (-not (Test-Path -LiteralPath $project -PathType Leaf)) {
        throw "Generated Keil project is missing: $project"
    }

    Remove-Item -LiteralPath $localLog -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $Keil `
        -ArgumentList @('-r', (Split-Path -Leaf $project), '-t', $Core.target, '-sg', '-o', $logName) `
        -WorkingDirectory $projectDirectory `
        -WindowStyle Hidden `
        -Wait `
        -PassThru

    if (-not (Test-Path -LiteralPath $localLog -PathType Leaf)) {
        throw "Keil did not create a build log for $($Core.id): $localLog"
    }

    Copy-Item -LiteralPath $localLog -Destination $artifactLog -Force
    $logText = Get-Content -LiteralPath $artifactLog -Raw

    if (($process.ExitCode -gt 1) -or ($logText -notmatch '- 0 Error\(s\)')) {
        throw "Keil build failed for $($Core.id). Log: $artifactLog"
    }

    $axf = Resolve-CodePath -RelativePath ([string]$Core.output_axf)
    $binary = Resolve-CodePath -RelativePath ([string]$Core.output_bin) -AllowMissing
    $fromElf = Join-Path (Split-Path -Parent (Split-Path -Parent $Keil)) `
        'ARM\ARMCLANG\bin\fromelf.exe'

    if (-not (Test-Path -LiteralPath $fromElf -PathType Leaf)) {
        throw "ArmClang fromelf not found: $fromElf"
    }

    & $fromElf --bincombined --output $binary $axf

    if (($LASTEXITCODE -ne 0) -or (-not (Test-Path -LiteralPath $binary -PathType Leaf))) {
        throw "fromelf failed for $($Core.id)."
    }

    return Get-ImageVector -Core $Core
}

function Invoke-JLink {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Profile,

        [Parameter(Mandatory = $true)]
        [object]$Core,

        [Parameter(Mandatory = $true)]
        [string[]]$Commands,

        [Parameter(Mandatory = $true)]
        [string]$ArtifactDirectory,

        [Parameter(Mandatory = $true)]
        [string]$Operation
    )

    $commandFile = Join-Path $ArtifactDirectory "$($Core.id)_$Operation.jlink"
    $stdout = Join-Path $ArtifactDirectory "$($Core.id)_$Operation.stdout.log"
    $stderr = Join-Path $ArtifactDirectory "$($Core.id)_$Operation.stderr.log"
    $script = Resolve-CodePath -RelativePath ([string]$Core.jlink_script)
    $image = Get-ImageVector -Core $Core
    $allCommands = @('exec DisableAutoUpdateFW') + $Commands + @('exit')
    $allCommands | Set-Content -LiteralPath $commandFile -Encoding ASCII

    $arguments = @(
        '-NoGui', '1',
        '-Device', [string]$Profile.probe.device,
        '-If', [string]$Profile.probe.interface,
        '-Speed', [string]$Profile.probe.speed_khz,
        '-AutoConnect', '1',
        '-JLinkScriptFile', $script
    )

    if (-not [string]::IsNullOrWhiteSpace([string]$Profile.probe.jtag_conf)) {
        $arguments += @('-JTAGConf', [string]$Profile.probe.jtag_conf)
    }

    if (-not [string]::IsNullOrWhiteSpace($JLinkSerial)) {
        $arguments += @('-SelectEmuBySN', $JLinkSerial)
    }

    $arguments += @('-CommanderScript', $commandFile)
    $process = Start-Process -FilePath $JLink `
        -ArgumentList $arguments `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -Wait `
        -PassThru

    $text = Get-Content -LiteralPath $stdout -Raw
    $checkedText = $text

    if ([bool]$Core.allow_halt_warning) {
        $checkedText = $checkedText -replace '(?im)^.*CPU could not be halted.*$', ''
    }

    if (($process.ExitCode -ne 0) -or
        ($checkedText -match 'Cannot connect|FAILED:|Could not connect|Error while programming|Failed to download|Failed to verify|Verification failed|Script file read error')) {
        throw "J-Link $Operation failed for $($Core.id). Log: $stdout"
    }

    if ($text -notmatch 'Cortex-M7 identified') {
        throw "J-Link did not identify Cortex-M7 for $($Core.id). Log: $stdout"
    }

    $vectorMatch = [regex]::Match(
        $text,
        ('{0:X8}\s*=\s*([0-9A-Fa-f]{{8}})\s+([0-9A-Fa-f]{{8}})' -f $image.load_address)
    )

    if (-not $vectorMatch.Success) {
        throw "J-Link output has no vector readback for $($Core.id). Log: $stdout"
    }

    $observedMsp = [Convert]::ToUInt32($vectorMatch.Groups[1].Value, 16)
    $observedReset = [Convert]::ToUInt32($vectorMatch.Groups[2].Value, 16)

    if (($observedMsp -ne $image.msp) -or ($observedReset -ne $image.reset_handler)) {
        throw ('{0} vector mismatch: expected {1:X8}/{2:X8}, got {3:X8}/{4:X8}.' -f `
            $Core.id, $image.msp, $image.reset_handler, $observedMsp, $observedReset)
    }

    return [ordered]@{
        exit_code = $process.ExitCode
        log = $stdout
        image_sha256 = $image.sha256
        msp = ('0x{0:X8}' -f $image.msp)
        reset_handler = ('0x{0:X8}' -f $image.reset_handler)
    }
}

function Invoke-RamDeployRound {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Profile,

        [Parameter(Mandatory = $true)]
        [string]$ArtifactDirectory
    )

    $core0 = $Profile.cores | Where-Object id -eq 'core0'
    $core1 = $Profile.cores | Where-Object id -eq 'core1'
    $core0Image = Get-ImageVector -Core $core0
    $core1Image = Get-ImageVector -Core $core1
    # Core0 first resets the SoC and prepares its ITCM/vector state, but must remain halted.
    # Core1 is loaded next while it is still held by the platform startup state. Only after
    # both images have been verified may Core0 run and release Core1 from firmware.
    $core0LoadCommands = @(
        'r',
        'h',
        ('loadbin "{0}", 0x{1:X8}' -f $core0Image.binary, $core0Image.load_address),
        ('verifybin "{0}", 0x{1:X8}' -f $core0Image.binary, $core0Image.load_address),
        ('mem32 0x{0:X8}, 2' -f $core0Image.load_address),
        ('w4 0xE000ED08, 0x{0:X8}' -f $core0Image.load_address),
        ('wreg MSP, 0x{0:X8}' -f $core0Image.msp),
        'wreg PSP, 0x00000000',
        'wreg XPSR, 0x01000000',
        ('SetPC 0x{0:X8}' -f $core0Image.reset_handler)
    )
    $core1Commands = @(
        ('loadbin "{0}", 0x{1:X8}' -f $core1Image.binary, $core1Image.load_address),
        ('verifybin "{0}", 0x{1:X8}' -f $core1Image.binary, $core1Image.load_address),
        ('mem32 0x{0:X8}, 2' -f $core1Image.load_address)
    )
    $core0LoadResult = Invoke-JLink -Profile $Profile -Core $core0 `
        -Commands $core0LoadCommands -ArtifactDirectory $ArtifactDirectory -Operation 'load_halt'
    $core1Result = Invoke-JLink -Profile $Profile -Core $core1 `
        -Commands $core1Commands -ArtifactDirectory $ArtifactDirectory -Operation 'load_verify'
    $core0RunResult = Invoke-JLink -Profile $Profile -Core $core0 `
        -Commands @(
            ('mem32 0x{0:X8}, 2' -f $core0Image.load_address),
            'g'
        ) -ArtifactDirectory $ArtifactDirectory -Operation 'run'

    $python = Join-Path $codeRoot '.venv\Scripts\python.exe'

    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        $python = (Get-Command python -ErrorAction Stop).Source
    }

    $capture = Join-Path $codeRoot 'tools\manual_test\capture_serial_log.py'
    $serialLog = Join-Path $ArtifactDirectory 'diagnostics.log'
    $captureRunnerLog = Join-Path $ArtifactDirectory 'capture_runner.log'
    $captureOutput = & $python $capture `
        --port $SerialPort `
        --baudrate ([string]$Profile.verification.baudrate) `
        --timeout-s ([string]$Profile.verification.timeout_s) `
        --end-marker ([string]$Profile.verification.end_marker) `
        --output $serialLog
    $captureOutput | Set-Content -LiteralPath $captureRunnerLog -Encoding UTF8

    if ($LASTEXITCODE -ne 0) {
        throw "Dual-core serial verification timed out. Logs: $serialLog, $captureRunnerLog"
    }

    $serialText = Get-Content -LiteralPath $serialLog -Raw

    foreach ($requiredLine in $Profile.verification.required_lines) {
        if (-not $serialText.Contains([string]$requiredLine)) {
            throw "Dual-core serial evidence is missing '$requiredLine'. Log: $serialLog"
        }
    }

    return [ordered]@{
        result = 'PASS'
        core0_load = $core0LoadResult
        core0_run = $core0RunResult
        core1 = $core1Result
        serial_log = $serialLog
    }
}

function Invoke-KeilFlashCore {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Core,

        [Parameter(Mandatory = $true)]
        [string]$ArtifactDirectory
    )

    $project = Resolve-CodePath -RelativePath ([string]$Core.project)
    $projectDirectory = Split-Path -Parent $project
    $logName = "keil_flash_$($Core.id).log"
    $localLog = Join-Path $projectDirectory $logName
    $artifactLog = Join-Path $ArtifactDirectory $logName
    Remove-Item -LiteralPath $localLog -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $Keil `
        -ArgumentList @('-f', (Split-Path -Leaf $project), '-t', $Core.target, '-o', $logName) `
        -WorkingDirectory $projectDirectory `
        -WindowStyle Hidden `
        -Wait `
        -PassThru

    if (-not (Test-Path -LiteralPath $localLog -PathType Leaf)) {
        throw "Keil did not create a Flash log for $($Core.id)."
    }

    Copy-Item -LiteralPath $localLog -Destination $artifactLog -Force
    $logText = Get-Content -LiteralPath $artifactLog -Raw

    if (($process.ExitCode -gt 1) -or ($logText -notmatch '0 Error\(s\)')) {
        throw "Keil Flash failed for $($Core.id). Log: $artifactLog"
    }

    return $artifactLog
}

function Write-DryRun {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Profile
    )

    Write-Output "DUALCORE_DRY_RUN|chip=$($Profile.chip)|lane=$($Profile.lane)|method=$($Profile.program_method)"

    foreach ($core in $Profile.cores) {
        Write-Output ("CORE|id={0}|target={1}|image={2}|address={3}|script={4}" -f `
            $core.id, $core.target, $core.output_bin, $core.load_address, $core.jlink_script)
    }

    if (-not [bool]$Profile.deployment_enabled) {
        Write-Output "DEPLOYMENT_BLOCKED|reason=$($Profile.blocked_reason)"
    }
}

$profile = Get-ValidatedManifest -Path $Manifest

if ($Action -eq 'DryRun') {
    Write-DryRun -Profile $profile

    exit 0
}

if (-not [string]::IsNullOrWhiteSpace($RtePath)) {
    if (-not (Test-Path -LiteralPath $RtePath -PathType Container)) {
        throw "Arm Pack root not found: $RtePath"
    }

    $env:RTEPATH = (Resolve-Path -LiteralPath $RtePath).Path
}

$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName "dualcore_$($profile.name)_$($Action.ToLowerInvariant())"
$artifactDirectory = New-EtArtifactStageDirectory `
    -RunRoot $runRoot `
    -StageName "dualcore_$($profile.name)_$($Action.ToLowerInvariant())"

if ($Action -eq 'Build') {
    if ((-not (Test-Path -LiteralPath $Keil -PathType Leaf)) -or
        (Get-Process UV4 -ErrorAction SilentlyContinue)) {
        throw 'A valid, closed Keil UV4 installation is required for dual-core build.'
    }

    $buildResults = @()

    foreach ($core in $profile.cores) {
        $buildResults += Invoke-CoreBuild -Core $core -ArtifactDirectory $artifactDirectory
    }

    [ordered]@{
        schema = 'et-dualcore-build-result/v1'
        result = 'PASS'
        chip = $profile.chip
        lane = $profile.lane
        cores = $buildResults
    } | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath (Join-Path $artifactDirectory 'dualcore_manifest.json') -Encoding UTF8
    Write-Output "DUALCORE_BUILD_PASS|lane=$($profile.lane)|artifact=$artifactDirectory"

    exit 0
}

if (-not $ConfirmHardware) {
    throw 'Dual-core deployment requires -ConfirmHardware.'
}

if (-not [bool]$profile.deployment_enabled) {
    throw "Dual-core deployment is blocked by the chip profile: $($profile.blocked_reason)"
}

if (-not (Test-Path -LiteralPath $JLink -PathType Leaf)) {
    throw "J-Link Commander not found: $JLink"
}

if (Get-Process JLink -ErrorAction SilentlyContinue) {
    throw 'J-Link Commander is already running.'
}

if ([string]::IsNullOrWhiteSpace($SerialPort)) {
    throw 'SerialPort is required for dual-core runtime verification.'
}

$roundResults = @()

if ($profile.program_method -eq 'jlink_ram') {
    for ($round = 1; $round -le $Repeat; ++$round) {
        $roundDirectory = Join-Path $artifactDirectory ('round_{0:D2}' -f $round)
        New-Item -ItemType Directory -Force -Path $roundDirectory | Out-Null
        $roundResults += Invoke-RamDeployRound -Profile $profile -ArtifactDirectory $roundDirectory
    }
} else {
    if (-not (Test-Path -LiteralPath $Keil -PathType Leaf)) {
        throw "Keil UV4 not found: $Keil"
    }

    foreach ($core in $profile.cores) {
        [void](Invoke-KeilFlashCore -Core $core -ArtifactDirectory $artifactDirectory)
    }

    throw 'Silicon Flash programming completed, but run-control is not enabled until the first-board Core1 release route is approved.'
}

[ordered]@{
    schema = 'et-dualcore-deploy-result/v1'
    result = 'PASS'
    chip = $profile.chip
    lane = $profile.lane
    repeat = $Repeat
    destructive = $false
    rounds = $roundResults
    recovery = 'Reset the target or reload the previous Core0/Core1 images.'
} | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath (Join-Path $artifactDirectory 'dualcore_manifest.json') -Encoding UTF8

Write-Output "DUALCORE_DEPLOY_PASS|lane=$($profile.lane)|repeat=$Repeat|artifact=$artifactDirectory"
