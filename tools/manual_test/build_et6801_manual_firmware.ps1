[CmdletBinding()]
param(
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe'
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
$guard = 'D:\lihuan\vibe_code\codex\scripts\resource-control\run-guarded.ps1'
$inner = Join-Path $PSScriptRoot 'build_et6801_manual_firmware_inner.ps1'

& $guard -ProjectRoot $projectRoot -Command @(
    'powershell.exe',
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    $inner,
    '-Keil',
    $Keil
) -TimeoutSeconds 600

exit $LASTEXITCODE
