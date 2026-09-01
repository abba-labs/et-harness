[CmdletBinding()]
param(
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe'
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
$assertGuarded = 'D:\lihuan\vibe_code\codex\scripts\resource-control\assert-guarded.ps1'
$manifest = Join-Path $codeRoot 'firmware\chips\et6801\project.yaml'
$generator = Join-Path $codeRoot 'tools\firmware\generate_keil_project.py'
$project = Join-Path $codeRoot 'firmware\build\et6801\ET6801_Automated_Test.uvprojx'
$targetName = 'ET6801_FPGA_MANUAL_FLASH'
$outputDirectory = Join-Path $codeRoot 'firmware\build\et6801\Objects\FPGA_MANUAL_FLASH'
$outputName = 'et6801_manual_uart_crc_fpga_flash'

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $assertGuarded -ProjectRoot $projectRoot

if ($LASTEXITCODE -ne 0) {
    throw 'Manual firmware build must run inside the project resource guard.'
}

foreach ($required in @($Keil, $manifest, $generator)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required path not found: $required"
    }
}

if (Get-Process UV4 -ErrorAction SilentlyContinue) {
    throw 'Keil UV4 is already running. Close it before deterministic CLI build.'
}

$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}

& $python $generator --manifest $manifest

if ($LASTEXITCODE -ne 0) {
    throw 'Keil project generation failed.'
}

$projectDirectory = Split-Path -Parent $project
$logName = 'keil_fpga_manual.log'
$localLog = Join-Path $projectDirectory $logName
Remove-Item -LiteralPath $localLog -Force -ErrorAction SilentlyContinue

$process = Start-Process -FilePath $Keil `
    -ArgumentList @('-r', (Split-Path -Leaf $project), '-t', $targetName, '-sg', '-o', $logName) `
    -WorkingDirectory $projectDirectory `
    -WindowStyle Hidden `
    -Wait `
    -PassThru

if (-not (Test-Path -LiteralPath $localLog -PathType Leaf)) {
    throw "Keil did not create build log: $localLog"
}

$logText = Get-Content -LiteralPath $localLog -Raw

if (($process.ExitCode -gt 1) -or ($logText -notmatch '- 0 Error\(s\)')) {
    throw "Manual firmware build failed. Log: $localLog"
}

foreach ($extension in @('axf', 'hex')) {
    $output = Join-Path $outputDirectory "$outputName.$extension"

    if (-not (Test-Path -LiteralPath $output -PathType Leaf)) {
        throw "Expected manual firmware output not found: $output"
    }
}

Write-Output "ET6801_MANUAL_FIRMWARE_BUILD_PASS|target=$targetName|output=$outputDirectory"
