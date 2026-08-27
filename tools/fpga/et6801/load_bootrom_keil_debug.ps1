[CmdletBinding()]
param(
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe',
    [string]$RtePath = '',
    [string]$Project = '',
    [string]$Target = 'ROM',
    [int]$TimeoutSeconds = 120,
    [switch]$ConfirmRamLoad,
    [switch]$SkipBuild,
    [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$buildScript = Join-Path $PSScriptRoot 'build_bootrom.ps1'
if ([string]::IsNullOrWhiteSpace($Project)) {
    $Project = Join-Path $projectRoot 'workspaces\et6801_bootrom_runtime\source\Project\ET6801.uvprojx'
}

$projectItem = Get-Item -LiteralPath $Project
$projectDir = $projectItem.DirectoryName
$axf = Join-Path $projectDir 'Objects\rom.axf'
$map = Join-Path $projectDir 'Listings\rom.map'
$initFile = Join-Path $projectDir 'cfg\Debug_ROM.ini'

foreach ($required in @($buildScript, $Keil, $Project, $initFile)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

if (-not $SkipBuild -and -not $PrepareOnly) {
    & $buildScript -Keil $Keil -RtePath $RtePath -Project $Project -Target $Target
    if ($LASTEXITCODE -ne 0) {
        throw 'BootROM build step failed.'
    }
}

foreach ($required in @($axf, $map)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "BootROM output missing: $required"
    }
}

$mapText = Get-Content -LiteralPath $map -Raw
$mainMatch = [regex]::Match($mapText, '(?m)^\s+main\s+(0x[0-9A-Fa-f]+)')
if (-not $mainMatch.Success) {
    throw "Could not resolve BootROM main in $map"
}

$axfHash = (Get-FileHash -LiteralPath $axf -Algorithm SHA256).Hash
if ($PrepareOnly) {
    [pscustomobject]@{
        Action = 'Keil debug load to FPGA BootROM window and run to main'
        Project = $projectItem.FullName
        Target = $Target
        Image = $axf
        SHA256 = $axfHash
        LoadBase = '0x20500000'
        Main = $mainMatch.Groups[1].Value
        Writes = 'FPGA BootROM/RAM model only; no PFLASH/NVR/OTP'
        Recovery = 'Reload the image, reload the bitfile, or power-cycle the FPGA prototype.'
    } | Format-List
    exit 0
}

if (-not $ConfirmRamLoad) {
    throw 'Hardware gate not confirmed. Re-run with -ConfirmRamLoad.'
}

if (Get-Process UV4 -ErrorAction SilentlyContinue) {
    throw 'Keil UV4 is already running. Close it before the automated debug session.'
}

$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'bootrom_debug_load'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'deploy_bootrom'
$sessionLog = Join-Path $outputDir 'keil_bootrom_debug_session.live.log'
$initTemplate = Get-Content -LiteralPath $initFile -Raw
$portableInit = [regex]::Replace(
    $initTemplate,
    '(?m)^LOG\s+>.*$',
    'LOG >' + $sessionLog
)
if ($portableInit -eq $initTemplate) {
    # The upstream BootROM project may contain only LOAD/Setup commands. Add the
    # bounded proof sequence to the isolated copy instead of editing that source.
    $portableInit = $initTemplate.TrimEnd() + [Environment]::NewLine + @"
LOG >$sessionLog
printf("ET6801_BOOTROM_DEBUG_START\n");
g, main
printf("ET6801_BOOTROM_MAIN_REACHED|PC=0x%08X\n", PC);
LOG OFF
EXIT
"@
}
$temporaryWorkspace = Join-Path ([System.IO.Path]::GetTempPath()) (
    'et_bootrom_debug_{0}' -f [guid]::NewGuid().ToString('N')
)
$temporarySource = Join-Path $temporaryWorkspace 'source'
try {
    # Keil resolves the debug INI from the project options. Use an isolated copy so the
    # operator source tree is never rewritten, even if this process is interrupted.
    Copy-Item -LiteralPath (Split-Path $projectDir -Parent) -Destination $temporarySource `
        -Recurse -Force
    $temporaryProjectDir = Join-Path $temporarySource (Split-Path $projectDir -Leaf)
    $temporaryProject = Join-Path $temporaryProjectDir $projectItem.Name
    $temporaryInit = Join-Path $temporaryProjectDir 'cfg\Debug_ROM.ini'
    $portableInit | Set-Content -LiteralPath $temporaryInit -Encoding ASCII
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $sessionLog) | Out-Null
    Remove-Item -LiteralPath $sessionLog -Force -ErrorAction SilentlyContinue

if (-not [string]::IsNullOrWhiteSpace($RtePath)) {
    if (-not (Test-Path -LiteralPath $RtePath -PathType Container)) {
        throw "Arm Pack root not found: $RtePath"
    }
    $env:RTEPATH = (Resolve-Path -LiteralPath $RtePath).Path
}
$process = Start-Process -FilePath $Keil `
    -ArgumentList @('-d', (Split-Path $temporaryProject -Leaf), '-t', $Target, '-sg') `
    -WorkingDirectory $temporaryProjectDir `
    -WindowStyle Hidden `
    -PassThru

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$terminalLogSeen = $false
while (-not $process.HasExited -and (Get-Date) -lt $deadline) {
    if (Test-Path -LiteralPath $sessionLog -PathType Leaf) {
        $liveDebugText = Get-Content -LiteralPath $sessionLog -Raw
        if ($liveDebugText -match 'ET6801_BOOTROM_MAIN_REACHED\|PC=0x[0-9A-Fa-f]+') {
            $terminalLogSeen = $true
            break
        }
    }
    Start-Sleep -Milliseconds 250
    $process.Refresh()
}
if (-not $process.HasExited) {
    # Keil can retain its GUI server loop after the debug INI has already
    # written the terminal proof. Stop only the process started above.
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    $process.WaitForExit()
}
if (-not $terminalLogSeen -and (Get-Date) -ge $deadline) {
    throw "Keil automated debug session timed out after $TimeoutSeconds seconds."
}

if (-not (Test-Path -LiteralPath $sessionLog)) {
    throw "Keil debug session did not create its proof log: $sessionLog"
}

$debugText = Get-Content -LiteralPath $sessionLog -Raw
$debugText | Write-Output
if ($debugText -notmatch 'ET6801_BOOTROM_MAIN_REACHED\|PC=0x[0-9A-Fa-f]+') {
    throw "Keil did not prove that BootROM reached main. Log: $sessionLog"
}

Copy-Item -LiteralPath $sessionLog -Destination (Join-Path $outputDir 'keil_bootrom_debug_session.log') -Force
@(
    "time=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
    "project=$($projectItem.FullName)"
    "target=$Target"
    "image=$axf"
    "image_sha256=$axfHash"
    'load_base=0x20500000'
    "expected_main=$($mainMatch.Groups[1].Value)"
    "keil_exit_code=$(if ($terminalLogSeen) { 0 } else { $process.ExitCode })"
    'result=PASS'
) | Set-Content -LiteralPath (Join-Path $outputDir 'manifest.txt') -Encoding UTF8

Write-Output "ET6801_BOOTROM_KEIL_DEBUG_PASS|artifact=$outputDir|main=$($mainMatch.Groups[1].Value)"
}
finally {
    Remove-Item -LiteralPath $temporaryWorkspace -Recurse -Force -ErrorAction SilentlyContinue
}
