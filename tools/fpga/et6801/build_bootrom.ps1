[CmdletBinding()]
param(
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe',
    [string]$RtePath = '',
    [string]$Project = '',
    [string]$Target = 'ROM'
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
if ([string]::IsNullOrWhiteSpace($Project)) {
    $Project = Join-Path $projectRoot 'workspaces\et6801_bootrom_runtime\source\Project\ET6801.uvprojx'
}

foreach ($required in @($Keil, $Project)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

if (Get-Process UV4 -ErrorAction SilentlyContinue) {
    throw 'Keil UV4 is already running. Close it before the deterministic command-line build.'
}

$projectItem = Get-Item -LiteralPath $Project
$projectDir = $projectItem.DirectoryName
$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'bootrom_build'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'build_bootrom'
$keilLog = Join-Path $outputDir 'keil_build_rom.log'
$localLog = 'keil_cli_build_rom.log'
if (-not [string]::IsNullOrWhiteSpace($RtePath)) {
    if (-not (Test-Path -LiteralPath $RtePath -PathType Container)) {
        throw "Arm Pack root not found: $RtePath"
    }
    $env:RTEPATH = (Resolve-Path -LiteralPath $RtePath).Path
}

Push-Location $projectDir
try {
    $localLogPath = Join-Path $projectDir $localLog
    Remove-Item -LiteralPath $localLogPath -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $Keil `
        -ArgumentList @('-b', $projectItem.Name, '-t', $Target, '-sg', '-o', $localLog) `
        -WorkingDirectory $projectDir `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    $keilExit = $process.ExitCode
    if (-not (Test-Path -LiteralPath $localLogPath)) {
        throw "Keil exited with code $keilExit but did not create its build log: $localLogPath"
    }
    Copy-Item -LiteralPath $localLogPath -Destination $keilLog -Force
}
finally {
    Pop-Location
}

$logText = Get-Content -LiteralPath $keilLog -Raw
$logText | Write-Output
if ($keilExit -gt 1 -or $logText -notmatch '- 0 Error\(s\)') {
    throw "BootROM build failed with exit code $keilExit. Log: $keilLog"
}

$objects = Join-Path $projectDir 'Objects'
$axf = Join-Path $objects 'rom.axf'
$hex = Join-Path $objects 'rom.hex'
$bin = Join-Path $projectDir 'rom.bin'
$map = Join-Path $projectDir 'Listings\rom.map'
foreach ($required in @($axf, $hex, $bin, $map)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "BootROM output missing: $required"
    }
}

$mapText = Get-Content -LiteralPath $map -Raw
if ($mapText -notmatch 'Image Entry point\s*:\s*0x205[0-9A-Fa-f]{5}' -or
    $mapText -notmatch 'Load Region LR_IROM1 \(Base: 0x20500000') {
    throw "BootROM map does not prove the expected 0x20500000 placement: $map"
}

$manifest = Join-Path $outputDir 'manifest.txt'
@(
    "time=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
    "project=$($projectItem.FullName)"
    "target=$Target"
    "axf=$axf"
    "axf_sha256=$((Get-FileHash $axf -Algorithm SHA256).Hash)"
    "hex=$hex"
    "hex_sha256=$((Get-FileHash $hex -Algorithm SHA256).Hash)"
    "bin=$bin"
    "bin_sha256=$((Get-FileHash $bin -Algorithm SHA256).Hash)"
    'link_base=0x20500000'
    'result=PASS'
) | Set-Content -LiteralPath $manifest -Encoding UTF8

Write-Output "ET6801_BOOTROM_BUILD_PASS|artifact=$outputDir|axf=$axf"
