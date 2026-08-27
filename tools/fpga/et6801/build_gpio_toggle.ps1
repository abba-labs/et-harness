[CmdletBinding()]
param(
    [ValidateSet('ITCM', 'FLASH')]
    [string]$Target = 'FLASH',
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe',
    [string]$Project = ''
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$assertGuarded = 'D:\lihuan\vibe_code\codex\scripts\resource-control\assert-guarded.ps1'
if ([string]::IsNullOrWhiteSpace($Project)) {
    $Project = Join-Path $projectRoot 'workspaces\et6801_gpio_toggle\DFP\Project\ET6801_GPIO_Toggle.uvprojx'
}

foreach ($required in @($assertGuarded, $Keil, $Project)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $assertGuarded -ProjectRoot $projectRoot
if ($LASTEXITCODE -ne 0) {
    throw 'GPIO firmware build must run inside the project resource guard.'
}

if (Get-Process UV4 -ErrorAction SilentlyContinue) {
    throw 'Keil UV4 is already running. Close it before the deterministic command-line build.'
}

[xml]$projectXml = Get-Content -LiteralPath $Project
$targetNode = $projectXml.Project.Targets.Target | Where-Object TargetName -eq $Target
if (-not $targetNode) {
    throw "Keil target not found: $Target"
}
if ($targetNode.TargetOption.TargetCommonOption.Device -ne 'ET6801') {
    throw "Target $Target is not bound to ET6801."
}

if ($Target -eq 'FLASH') {
    $driver = [string]$targetNode.TargetOption.TargetCommonOption.FlashDriverDll
    if ($driver -notmatch 'ET6801\.FLM' -or
        $driver -notmatch '-FS08000000' -or
        $driver -notmatch '-FL080000') {
        throw 'FLASH target does not contain the bounded ET6801 PFLASH0 algorithm configuration.'
    }
}

$projectItem = Get-Item -LiteralPath $Project
$projectDir = $projectItem.DirectoryName
$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName "gpio_$($Target.ToLowerInvariant())_build"
$outputDir = New-EtArtifactStageDirectory `
    -RunRoot $runRoot `
    -StageName "build_gpio_$($Target.ToLowerInvariant())"
$localLog = "keil_cli_build_$($Target.ToLowerInvariant()).log"
$keilLog = Join-Path $outputDir $localLog
$env:RTEPATH = 'C:\Users\admin\AppData\Local\Arm\Packs'

Push-Location $projectDir
try {
    $localLogPath = Join-Path $projectDir $localLog
    Remove-Item -LiteralPath $localLogPath -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $Keil `
        -ArgumentList @('-r', $projectItem.Name, '-t', $Target, '-sg', '-o', $localLog) `
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
    throw "GPIO $Target build failed with exit code $keilExit. Log: $keilLog"
}

if ($Target -eq 'FLASH') {
    $objects = Join-Path $projectDir 'Objects_PFLASH'
    $name = 'et6801_gpio_pflash'
    $expectedBase = '0x08000000'
}
else {
    $objects = Join-Path $projectDir 'Objects'
    $name = 'sbtest'
    $expectedBase = '0x00000000'
}

$axf = Join-Path $objects "$name.axf"
$hex = Join-Path $objects "$name.hex"
$bin = Join-Path $projectDir "$name.bin"
$map = Join-Path $projectDir "Listings\$name.map"
foreach ($required in @($axf, $hex, $bin, $map)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "GPIO $Target output missing: $required"
    }
}

$mapText = Get-Content -LiteralPath $map -Raw
if ($Target -eq 'FLASH') {
    if ($mapText -notmatch 'Image Entry point\s*:\s*0x08[0-9A-Fa-f]{6}' -or
        $mapText -notmatch 'Load Region LR_IROM1 \(Base: 0x08000000') {
        throw "GPIO FLASH map does not prove placement at 0x08000000: $map"
    }
}
elseif ($mapText -notmatch 'Load Region LR_IROM1 \(Base: 0x00000000') {
    throw "GPIO ITCM map does not prove placement at 0x00000000: $map"
}

$symbols = @{}
foreach ($symbol in 'g_et6801_gpio_signature', 'g_et6801_gpio_phase', 'g_et6801_gpio_toggle_count') {
    $match = [regex]::Match($mapText, "(?m)^\s+$symbol\s+(0x[0-9A-Fa-f]+)")
    if (-not $match.Success) {
        throw "Could not resolve symbol $symbol in $map"
    }
    $symbols[$symbol] = $match.Groups[1].Value
}

$manifest = Join-Path $outputDir 'manifest.txt'
@(
    "time=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
    "project=$($projectItem.FullName)"
    "target=$Target"
    "expected_base=$expectedBase"
    "axf=$axf"
    "axf_sha256=$((Get-FileHash $axf -Algorithm SHA256).Hash)"
    "hex=$hex"
    "hex_sha256=$((Get-FileHash $hex -Algorithm SHA256).Hash)"
    "bin=$bin"
    "bin_sha256=$((Get-FileHash $bin -Algorithm SHA256).Hash)"
    "signature_address=$($symbols.g_et6801_gpio_signature)"
    "phase_address=$($symbols.g_et6801_gpio_phase)"
    "toggle_count_address=$($symbols.g_et6801_gpio_toggle_count)"
    'result=PASS'
) | Set-Content -LiteralPath $manifest -Encoding UTF8

Write-Output "ET6801_GPIO_BUILD_PASS|target=$Target|artifact=$outputDir|axf=$axf"
