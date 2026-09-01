[CmdletBinding()]
param(
    [string]$Image = '',
    [string]$JLink = '',
    [int]$JLinkSpeedKHz = 1000,
    [string]$JLinkSerial = ''
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
$inner = Join-Path $PSScriptRoot 'load_et6801_test_firmware_ram.ps1'
$guard = 'D:\lihuan\vibe_code\codex\scripts\resource-control\run-guarded.ps1'
$command = @(
    'powershell.exe',
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    $inner,
    '-JLinkSpeedKHz',
    [string]$JLinkSpeedKHz
)
if (-not [string]::IsNullOrWhiteSpace($Image)) {
    $command += @('-Image', $Image)
}
if (-not [string]::IsNullOrWhiteSpace($JLink)) {
    $command += @('-JLink', $JLink)
}
if (-not [string]::IsNullOrWhiteSpace($JLinkSerial)) {
    $command += @('-JLinkSerial', $JLinkSerial)
}
& $guard -ProjectRoot $projectRoot -Command $command -TimeoutSeconds 180
exit $LASTEXITCODE
