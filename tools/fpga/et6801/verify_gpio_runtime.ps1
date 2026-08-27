[CmdletBinding()]
param(
    [string]$JLink = '',
    [string]$MapFile = '',
    [int]$JLinkSpeedKHz = 1000,
    [string]$JLinkSerial = '',
    [int]$RunMilliseconds = 2600,
    [switch]$ConfirmRunControl,
    [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$assertGuarded = 'D:\lihuan\vibe_code\codex\scripts\resource-control\assert-guarded.ps1'
if ([string]::IsNullOrWhiteSpace($JLink)) {
    $JLink = Join-Path $projectRoot 'workspaces\et6801_gpio_toggle\tools\jlink_7_22b\JLink.exe'
}
if ([string]::IsNullOrWhiteSpace($MapFile)) {
    $MapFile = Join-Path $projectRoot 'workspaces\et6801_gpio_toggle\DFP\Project\Listings\et6801_gpio_pflash.map'
}

foreach ($required in @($assertGuarded, $JLink, $MapFile)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

$mapText = Get-Content -LiteralPath $MapFile -Raw
$addresses = @{}
foreach ($symbol in 'g_et6801_gpio_signature', 'g_et6801_gpio_phase', 'g_et6801_gpio_toggle_count') {
    $match = [regex]::Match($mapText, "(?m)^\s+$symbol\s+(0x[0-9A-Fa-f]+)")
    if (-not $match.Success) {
        throw "Could not resolve symbol $symbol in $MapFile"
    }
    $addresses[$symbol] = $match.Groups[1].Value
}

if ($PrepareOnly) {
    [pscustomobject]@{
        Action = 'Read PFLASH vectors, direct-jump CORE0, and prove GPIO firmware progress'
        JLink = $JLink
        JLinkSerial = $(if ($JLinkSerial) { $JLinkSerial } else { 'auto; requires exactly one probe' })
        PFlashVector = '0x08000000'
        SignatureAddress = $addresses.g_et6801_gpio_signature
        PhaseAddress = $addresses.g_et6801_gpio_phase
        ToggleCountAddress = $addresses.g_et6801_gpio_toggle_count
        SideEffect = 'Writes CORE0 MSP/PC/xPSR and resumes execution; does not program Flash.'
        Recovery = 'Halt/reset CORE0 or reload BootROM/application.'
    } | Format-List
    exit 0
}

if (-not $ConfirmRunControl) {
    throw 'Hardware run-control gate not confirmed. Re-run with -ConfirmRunControl.'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $assertGuarded -ProjectRoot $projectRoot
if ($LASTEXITCODE -ne 0) {
    throw 'GPIO runtime validation must run inside the project resource guard.'
}

if (Get-Process JLink -ErrorAction SilentlyContinue) {
    throw 'J-Link Commander is already running. Close it before deterministic run-control.'
}

$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'gpio_runtime'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'verify_gpio_runtime'

function Invoke-JLinkCommandFile {
    param(
        [Parameter(Mandatory)][string]$CommandFile,
        [Parameter(Mandatory)][string]$Stdout,
        [Parameter(Mandatory)][string]$Stderr
    )

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
    $arguments += @('-CommanderScript', $CommandFile)

    $process = Start-Process -FilePath $JLink `
        -ArgumentList $arguments `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden -Wait -PassThru

    $text = Get-Content -LiteralPath $Stdout -Raw
    $text | Write-Output
    if ($process.ExitCode -ne 0 -or
        $text -match 'Cannot connect|Could not connect|FAILED:|Error while') {
        throw "J-Link command failed with exit code $($process.ExitCode). Log: $Stdout"
    }
    return $text
}

$readCommand = Join-Path $outputDir 'read_pflash_vectors.jlink'
@(
    'h'
    'mem32 0x08000000, 4'
    'regs'
    'exit'
) | Set-Content -LiteralPath $readCommand -Encoding ASCII

$readText = Invoke-JLinkCommandFile `
    -CommandFile $readCommand `
    -Stdout (Join-Path $outputDir 'read_pflash_vectors.stdout.log') `
    -Stderr (Join-Path $outputDir 'read_pflash_vectors.stderr.log')

$vectorMatch = [regex]::Match(
    $readText,
    '08000000\s*=\s*([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})'
)
if (-not $vectorMatch.Success) {
    throw 'Could not parse PFLASH0 vector table from J-Link output.'
}

$initialSp = [Convert]::ToUInt32($vectorMatch.Groups[1].Value, 16)
$resetHandler = [Convert]::ToUInt32($vectorMatch.Groups[2].Value, 16)
if ($initialSp -lt 0x20000000 -or $initialSp -gt 0x20020000) {
    throw ('Invalid PFLASH initial MSP: 0x{0:X8}' -f $initialSp)
}
if ($resetHandler -lt 0x08000001 -or $resetHandler -gt 0x08080000 -or
    ($resetHandler -band 1) -eq 0) {
    throw ('Invalid PFLASH reset handler: 0x{0:X8}' -f $resetHandler)
}

$runCommand = Join-Path $outputDir 'direct_jump_pflash_gpio.jlink'
@(
    'h'
    ('wreg MSP, 0x{0:X8}' -f $initialSp)
    'wreg PSP, 0x00000000'
    'wreg XPSR, 0x01000000'
    ('SetPC 0x{0:X8}' -f $resetHandler)
    'g'
    "Sleep $RunMilliseconds"
    'h'
    "mem32 $($addresses.g_et6801_gpio_signature), 1"
    "mem32 $($addresses.g_et6801_gpio_phase), 1"
    "mem32 $($addresses.g_et6801_gpio_toggle_count), 1"
    'regs'
    'g'
    'exit'
) | Set-Content -LiteralPath $runCommand -Encoding ASCII

$runText = Invoke-JLinkCommandFile `
    -CommandFile $runCommand `
    -Stdout (Join-Path $outputDir 'direct_jump_pflash_gpio.stdout.log') `
    -Stderr (Join-Path $outputDir 'direct_jump_pflash_gpio.stderr.log')

function Read-SingleWord {
    param([string]$Text, [string]$Address)
    $plain = $Address.Substring(2)
    $match = [regex]::Match($Text, "$plain\s*=\s*([0-9A-Fa-f]{8})", 'IgnoreCase')
    if (-not $match.Success) {
        throw "Could not parse memory word at $Address."
    }
    return [Convert]::ToUInt32($match.Groups[1].Value, 16)
}

$signature = Read-SingleWord $runText $addresses.g_et6801_gpio_signature
$phase = Read-SingleWord $runText $addresses.g_et6801_gpio_phase
$count = Read-SingleWord $runText $addresses.g_et6801_gpio_toggle_count
if ($signature -ne 0x45543638) {
    throw ('Unexpected GPIO firmware signature: 0x{0:X8}' -f $signature)
}
if ($count -lt 2) {
    throw "GPIO toggle counter did not advance: $count"
}

@(
    "time=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
    "map=$MapFile"
    ('initial_msp=0x{0:X8}' -f $initialSp)
    ('reset_handler=0x{0:X8}' -f $resetHandler)
    ('signature=0x{0:X8}' -f $signature)
    "phase=$phase"
    "toggle_count=$count"
    "run_milliseconds=$RunMilliseconds"
    'start_mode=direct PFLASH vector jump'
    'result=PASS'
) | Set-Content -LiteralPath (Join-Path $outputDir 'manifest.txt') -Encoding UTF8

Write-Output ('ET6801_GPIO_PFLASH_RUN_PASS|signature=0x{0:X8}|phase={1}|count={2}|artifact={3}' -f `
    $signature, $phase, $count, $outputDir)
