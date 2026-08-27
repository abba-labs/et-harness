[CmdletBinding()]
param(
    [ValidateSet('FPGA', 'SILICON')]
    [string]$Target = 'FPGA',
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe'
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
$inner = Join-Path $PSScriptRoot 'build_et6801_test_firmware.ps1'
$guard = 'D:\lihuan\vibe_code\codex\scripts\resource-control\run-guarded.ps1'
$command = @(
    'powershell.exe',
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    $inner,
    '-Target',
    $Target,
    '-Keil',
    $Keil
)

& $guard -ProjectRoot $projectRoot -Command $command -TimeoutSeconds 600
exit $LASTEXITCODE
