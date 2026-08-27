[CmdletBinding()]
param(
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe',
    [string]$Project = '',
    [string]$Target = 'FLASH',
    [switch]$ConfirmPFlashProgram,
    [switch]$PrepareOnly
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

[xml]$projectXml = Get-Content -LiteralPath $Project
$targetNode = $projectXml.Project.Targets.Target | Where-Object TargetName -eq $Target
if (-not $targetNode) {
    throw "Keil target not found: $Target"
}
$common = $targetNode.TargetOption.TargetCommonOption
$driver = [string]$common.FlashDriverDll
if ($common.Device -ne 'ET6801' -or
    $driver -notmatch 'ET6801\.FLM' -or
    $driver -notmatch '-FS08000000' -or
    $driver -notmatch '-FL080000') {
    throw 'Refusing download: target is not bounded to ET6801 PFLASH0 0x08000000..0x0807FFFF.'
}

$projectItem = Get-Item -LiteralPath $Project
$projectDir = $projectItem.DirectoryName
$axf = Join-Path $projectDir 'Objects_PFLASH\et6801_gpio_pflash.axf'
$hex = Join-Path $projectDir 'Objects_PFLASH\et6801_gpio_pflash.hex'
foreach ($required in @($axf, $hex)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Build output missing: $required. Run build_gpio_toggle.ps1 first."
    }
}

$axfHash = (Get-FileHash -LiteralPath $axf -Algorithm SHA256).Hash
$hexHash = (Get-FileHash -LiteralPath $hex -Algorithm SHA256).Hash
if ($PrepareOnly) {
    [pscustomobject]@{
        Action = 'Keil command-line PFLASH0 erase/program/verify'
        Project = $projectItem.FullName
        Target = $Target
        Image = $axf
        AXF_SHA256 = $axfHash
        HEX_SHA256 = $hexHash
        AddressRange = '0x08000000..0x0807FFFF'
        FlashAlgorithm = 'ET6801.FLM'
        Destructive = $true
        Recovery = 'Re-run this command with the previous known-good PFLASH image, or erase/reprogram PFLASH0.'
    } | Format-List
    exit 0
}

if (-not $ConfirmPFlashProgram) {
    throw 'Destructive hardware gate not confirmed. Re-run with -ConfirmPFlashProgram.'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $assertGuarded -ProjectRoot $projectRoot
if ($LASTEXITCODE -ne 0) {
    throw 'PFLASH programming must run inside the project resource guard.'
}

if (Get-Process UV4 -ErrorAction SilentlyContinue) {
    throw 'Keil UV4 is already running. Close it before command-line Flash programming.'
}

$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'gpio_pflash_program'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'deploy_gpio_pflash'
$localLog = 'keil_cli_flash_gpio.log'
$keilLog = Join-Path $outputDir $localLog
$env:RTEPATH = 'C:\Users\admin\AppData\Local\Arm\Packs'

Push-Location $projectDir
try {
    $localLogPath = Join-Path $projectDir $localLog
    Remove-Item -LiteralPath $localLogPath -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $Keil `
        -ArgumentList @('-f', $projectItem.Name, '-t', $Target, '-sg', '-o', $localLog) `
        -WorkingDirectory $projectDir `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    $keilExit = $process.ExitCode
    if (-not (Test-Path -LiteralPath $localLogPath)) {
        throw "Keil exited with code $keilExit but did not create its flash log: $localLogPath"
    }
    Copy-Item -LiteralPath $localLogPath -Destination $keilLog -Force
}
finally {
    Pop-Location
}

$logText = Get-Content -LiteralPath $keilLog -Raw
$logText | Write-Output
if ($keilExit -ne 0 -or
    $logText -match '(?i)flash download failed|cannot load|programming failed|verify failed') {
    throw "ET6801 PFLASH0 programming failed with exit code $keilExit. Log: $keilLog"
}

@(
    "time=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
    "project=$($projectItem.FullName)"
    "target=$Target"
    "image=$axf"
    "image_sha256=$axfHash"
    "hex_sha256=$hexHash"
    'flash_algorithm=ET6801.FLM'
    'address_range=0x08000000..0x0807FFFF'
    "keil_exit_code=$keilExit"
    'result=PASS'
) | Set-Content -LiteralPath (Join-Path $outputDir 'manifest.txt') -Encoding UTF8

Write-Output "ET6801_GPIO_PFLASH_PROGRAM_PASS|artifact=$outputDir|image_sha256=$axfHash"
