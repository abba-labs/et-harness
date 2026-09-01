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
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$assertGuarded = 'D:\lihuan\vibe_code\codex\scripts\resource-control\assert-guarded.ps1'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $assertGuarded -ProjectRoot $projectRoot
if ($LASTEXITCODE -ne 0) {
    throw 'RAM load must run inside the project resource guard.'
}

if ([string]::IsNullOrWhiteSpace($Image)) {
    $Image = Join-Path $codeRoot 'firmware\build\et6801\Objects\FPGA_ITCM\et6801_test_fpga.axf'
}
if ([string]::IsNullOrWhiteSpace($JLink)) {
    $JLink = Join-Path $projectRoot 'workspaces\et6801_gpio_toggle\tools\jlink_7_22b\JLink.exe'
}
$fromelf = 'C:\Keil_v5\ARM\ARMCLANG\bin\fromelf.exe'
foreach ($required in @($Image, $JLink, $fromelf)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required file not found: $required"
    }
}
if (Get-Process JLink -ErrorAction SilentlyContinue) {
    throw 'J-Link Commander is already running.'
}

$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'firmware_ram_load'
$artifactDirectory = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'load_firmware_ram'
$binary = Join-Path $artifactDirectory 'et6801_test_fpga.bin'
& $fromelf --bincombined --output $binary $Image
if ($LASTEXITCODE -ne 0) {
    throw 'fromelf failed to extract the vector table.'
}
$bytes = [IO.File]::ReadAllBytes($binary)
if ($bytes.Length -lt 8) {
    throw 'Image is too small to contain an ET6801 vector table.'
}
$msp = [BitConverter]::ToUInt32($bytes, 0)
$resetHandler = [BitConverter]::ToUInt32($bytes, 4)
if (($msp -lt 0x20000000) -or ($msp -ge 0x20020000) -or
    (($resetHandler -band 1) -eq 0) -or ($resetHandler -ge 0x00040000)) {
    throw ('Vector table is outside bounded ET6801 ITCM/DTCM: MSP=0x{0:X8}, Reset=0x{1:X8}' -f $msp, $resetHandler)
}

$commandFile = Join-Path $artifactDirectory 'load_run.jlink'
@(
    'h'
    "loadfile $((Resolve-Path $Image).Path)"
    'mem32 0x00000000, 2'
    'w4 0xE000ED08, 0x00000000'
    ('wreg MSP, 0x{0:X8}' -f $msp)
    'wreg PSP, 0x00000000'
    'wreg XPSR, 0x01000000'
    ('SetPC 0x{0:X8}' -f $resetHandler)
    'g'
    'Sleep 1000'
    'h'
    'regs'
    'g'
    'exit'
) | Set-Content -LiteralPath $commandFile -Encoding ASCII

$stdout = Join-Path $artifactDirectory 'jlink.stdout.log'
$stderr = Join-Path $artifactDirectory 'jlink.stderr.log'
$arguments = @(
    '-NoGui', '1',
    '-Device', 'Cortex-M7',
    '-If', 'JTAG',
    '-Speed', [string]$JLinkSpeedKHz,
    '-AutoConnect', '1'
)
if (-not [string]::IsNullOrWhiteSpace($JLinkSerial)) {
    $arguments += @('-SelectEmuBySN', $JLinkSerial)
}
$arguments += @('-CommanderScript', $commandFile)
$process = Start-Process -FilePath $JLink `
    -ArgumentList $arguments `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -Wait `
    -PassThru

$text = Get-Content -LiteralPath $stdout -Raw
if (($process.ExitCode -ne 0) -or
    ($text -match 'Cannot connect|FAILED:|Could not connect|Error while programming|Failed to download')) {
    throw "J-Link RAM load failed. Log: $stdout"
}
if ($text -notmatch 'Cortex-M7 identified') {
    throw "J-Link did not identify the ET6801 Cortex-M7. Log: $stdout"
}
$vectorMatch = [regex]::Match(
    $text,
    '00000000\s*=\s*([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})')
if (-not $vectorMatch.Success) {
    throw "J-Link output does not contain the loaded vector table. Log: $stdout"
}
$observedMsp = [Convert]::ToUInt32($vectorMatch.Groups[1].Value, 16)
$observedReset = [Convert]::ToUInt32($vectorMatch.Groups[2].Value, 16)
if (($observedMsp -ne $msp) -or ($observedReset -ne $resetHandler)) {
    throw ('Loaded vector mismatch: expected {0:X8}/{1:X8}, got {2:X8}/{3:X8}' -f $msp, $resetHandler, $observedMsp, $observedReset)
}

$record = [ordered]@{
    schemaVersion = 1
    time = Get-Date -Format 'yyyy-MM-dd HH:mm:ss K'
    result = 'PASS'
    target = 'ET6801 FPGA prototype CORE0'
    operation = 'temporary ITCM/DTCM RAM load and run'
    destructive = $false
    image = (Resolve-Path $Image).Path
    imageSha256 = (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash
    msp = ('0x{0:X8}' -f $msp)
    resetHandler = ('0x{0:X8}' -f $resetHandler)
    jlinkLog = $stdout
    recovery = 'Reset the ET6801 FPGA prototype or reload the previous RAM image.'
}
$record | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath (Join-Path $artifactDirectory 'manifest.json') -Encoding UTF8
Write-Output ('ET6801_TEST_FIRMWARE_RAM_LOAD_PASS|msp=0x{0:X8}|reset=0x{1:X8}|artifact={2}' -f $msp, $resetHandler, $artifactDirectory)
