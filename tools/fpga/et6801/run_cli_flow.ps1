[CmdletBinding()]
param(
    [int]$HwServerPort = 3121,
    [string]$ToolRoot,
    [string]$BitFile,
    [string]$JLinkSerial = '',
    [switch]$ConfirmVolatileProgram,
    [switch]$ConfirmRamLoad,
    [switch]$ConfirmPFlashProgram,
    [switch]$ConfirmRunControl,
    [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$previousRunRoot = $env:ET_ARTIFACT_RUN_DIR
$ownsRunRoot = [string]::IsNullOrWhiteSpace($previousRunRoot)
if ($ownsRunRoot) {
    $env:ET_ARTIFACT_RUN_DIR = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'et6801_cli_flow'
}
$flowSucceeded = $false

try {
& (Join-Path $PSScriptRoot 'build_bootrom.ps1')
if ($LASTEXITCODE -ne 0) { throw 'BootROM build failed.' }

& (Join-Path $PSScriptRoot 'build_gpio_toggle.ps1') -Target FLASH
if ($LASTEXITCODE -ne 0) { throw 'GPIO PFLASH build failed.' }

if ($PrepareOnly) {
    & (Join-Path $PSScriptRoot 'program_xc7vx980t.ps1') `
        -ToolRoot $ToolRoot -BitFile $BitFile -ServerPort $HwServerPort -PrepareOnly
    & (Join-Path $PSScriptRoot 'load_bootrom_keil_debug.ps1') -SkipBuild -PrepareOnly
    & (Join-Path $PSScriptRoot 'flash_gpio_toggle.ps1') -PrepareOnly
    & (Join-Path $PSScriptRoot 'verify_gpio_runtime.ps1') `
        -JLinkSerial $JLinkSerial -PrepareOnly
    $flowSucceeded = $true
    return
}

& (Join-Path $PSScriptRoot 'program_xc7vx980t.ps1') `
    -ToolRoot $ToolRoot `
    -BitFile $BitFile `
    -ServerPort $HwServerPort `
    -ConfirmVolatileProgram:$ConfirmVolatileProgram
if ($LASTEXITCODE -ne 0) { throw 'XC7VX980T programming failed.' }

& (Join-Path $PSScriptRoot 'load_bootrom_keil_debug.ps1') `
    -SkipBuild `
    -ConfirmRamLoad:$ConfirmRamLoad
if ($LASTEXITCODE -ne 0) { throw 'BootROM Keil debug load failed.' }

& (Join-Path $PSScriptRoot 'flash_gpio_toggle.ps1') `
    -ConfirmPFlashProgram:$ConfirmPFlashProgram
if ($LASTEXITCODE -ne 0) { throw 'GPIO PFLASH programming failed.' }

& (Join-Path $PSScriptRoot 'verify_gpio_runtime.ps1') `
    -JLinkSerial $JLinkSerial `
    -ConfirmRunControl:$ConfirmRunControl
if ($LASTEXITCODE -ne 0) { throw 'GPIO PFLASH runtime verification failed.' }

Write-Output 'ET6801_CLI_FLOW_PASS'
$flowSucceeded = $true
}
finally {
    if ($ownsRunRoot) {
        Complete-EtArtifactRun -RunRoot $env:ET_ARTIFACT_RUN_DIR `
            -Succeeded $flowSucceeded -ExitCode $(if ($flowSucceeded) { 0 } else { 1 })
        Remove-Item Env:ET_ARTIFACT_RUN_DIR -ErrorAction SilentlyContinue
    }
    else {
        $env:ET_ARTIFACT_RUN_DIR = $previousRunRoot
    }
}
