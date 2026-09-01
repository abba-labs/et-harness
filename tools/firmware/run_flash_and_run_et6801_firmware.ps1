[CmdletBinding()]
param(
    [string]$Project = '',
    [string]$Target = 'ET6801_SILICON_FLASH',
    [string]$Image = '',
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe',
    [string]$JLink = '',
    [int]$JLinkSpeedKHz = 1000,
    [string]$JLinkSerial = '',
    [uint32]$FlashBase = 0x08000000,
    [uint32]$FlashSize = 0x00080000,
    [int]$RunMilliseconds = 1500,
    [switch]$SkipFlash,
    [switch]$ConfirmPFlashProgram,
    [switch]$ConfirmRunControl,
    [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
$inner = Join-Path $PSScriptRoot 'flash_and_run_et6801_firmware.ps1'
$guard = 'D:\lihuan\vibe_code\codex\scripts\resource-control\run-guarded.ps1'

$command = @(
    'powershell.exe',
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    $inner,
    '-Target', $Target,
    '-Keil', $Keil,
    '-JLinkSpeedKHz', [string]$JLinkSpeedKHz,
    '-FlashBase', [string]([uint32]$FlashBase),
    '-FlashSize', [string]([uint32]$FlashSize),
    '-RunMilliseconds', [string]$RunMilliseconds
)
if (-not [string]::IsNullOrWhiteSpace($Project)) { $command += @('-Project', $Project) }
if (-not [string]::IsNullOrWhiteSpace($Image)) { $command += @('-Image', $Image) }
if (-not [string]::IsNullOrWhiteSpace($JLink)) { $command += @('-JLink', $JLink) }
if (-not [string]::IsNullOrWhiteSpace($JLinkSerial)) { $command += @('-JLinkSerial', $JLinkSerial) }
if ($SkipFlash) { $command += '-SkipFlash' }
if ($ConfirmPFlashProgram) { $command += '-ConfirmPFlashProgram' }
if ($ConfirmRunControl) { $command += '-ConfirmRunControl' }
if ($PrepareOnly) { $command += '-PrepareOnly' }

& $guard -ProjectRoot $projectRoot -Command $command -TimeoutSeconds 600
exit $LASTEXITCODE
