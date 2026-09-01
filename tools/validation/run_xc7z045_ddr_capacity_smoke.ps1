[CmdletBinding()]
param(
    [string]$VivadoRoot = 'D:\Software\Xilinx\Vivado\2024.2',
    [switch]$ConfirmHardwareWrite
)

$ErrorActionPreference = 'Stop'

$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$guard = 'D:\lihuan\vibe_code\codex\scripts\resource-control\run-guarded.ps1'
$xsdb = Join-Path $VivadoRoot 'bin\xsdb.bat'
$runner = Join-Path $projectRoot 'workspaces\xc7z045_ps_selftest\xsdb\run_ddr_capacity_smoke.tcl'
$bistReader = Join-Path $projectRoot 'workspaces\xc7z045_fabric_bist\xsdb\read_fabric_bist_status.tcl'
$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'xc7z045_ddr_capacity'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'ddr_capacity_smoke'
$hardwareLog = Join-Path $outputDir 'ddr_capacity_hardware.log'
$bistLog = Join-Path $outputDir 'fabric_bist_final.log'
$manifest = Join-Path $outputDir 'manifest.txt'

if (-not $ConfirmHardwareWrite) {
    throw @'
Hardware gate not confirmed. This test temporarily writes eight volatile 4 KiB
DDR windows from 0x07FFF000 through 0x3FFFF000, then restores and verifies every
window. Re-run only after approval with -ConfirmHardwareWrite. No nonvolatile
storage is written.
'@
}

foreach ($required in @($guard, $xsdb, $runner, $bistReader)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$hardwareCommand = 'call "{0}" "{1}" "{2}" hardware' -f `
    $xsdb, $runner, $outputDir
& $guard `
    -ProjectRoot $projectRoot `
    -TimeoutSeconds 240 `
    -Command @('cmd.exe', '/d', '/c', $hardwareCommand) 2>&1 |
    Tee-Object -FilePath $hardwareLog
$hardwareExit = $LASTEXITCODE
$hardwarePass = $hardwareExit -eq 0 -and
    (Select-String -Quiet -SimpleMatch 'DDR_CAPACITY_SMOKE_PASS|1' -LiteralPath $hardwareLog) -and
    (Select-String -Quiet -SimpleMatch 'DDR_ALIAS_CHECK_PASS|1' -LiteralPath $hardwareLog) -and
    (Select-String -Quiet -SimpleMatch 'DDR_WINDOWS_RESTORE_PASS|1' -LiteralPath $hardwareLog)

# Always attempt the final PL health check after the DDR runner returns.
$bistCommand = 'call "{0}" "{1}"' -f $xsdb, $bistReader
& $guard `
    -ProjectRoot $projectRoot `
    -TimeoutSeconds 120 `
    -Command @('cmd.exe', '/d', '/c', $bistCommand) 2>&1 |
    Tee-Object -FilePath $bistLog
$bistExit = $LASTEXITCODE
$bistPass = $bistExit -eq 0 -and
    (Select-String -Quiet -SimpleMatch 'FABRIC_BIST_HARDWARE_PASS|1' -LiteralPath $bistLog)

$hardwareLogSha256 = if (Test-Path -LiteralPath $hardwareLog) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $hardwareLog).Hash
} else { 'MISSING' }
$bistLogSha256 = if (Test-Path -LiteralPath $bistLog) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $bistLog).Hash
} else { 'MISSING' }

@(
    'TARGET|XC7Z045-FFG900'
    'ROUTE|Digilent JTAG-SMT2'
    'JTAG_SPEED_MHZ|15'
    'DDR_DECLARED_RANGE|0x00000000-0x3FFFFFFF'
    'DDR_SAMPLE_WINDOW_BYTES|4096'
    'DDR_SAMPLE_WINDOWS|0x07FFF000,0x0FFFF000,0x17FFF000,0x1FFFF000,0x27FFF000,0x2FFFF000,0x37FFF000,0x3FFFF000'
    "HARDWARE_EXIT|$hardwareExit"
    "HARDWARE_PASS|$([int]$hardwarePass)"
    "BIST_EXIT|$bistExit"
    "BIST_PASS|$([int]$bistPass)"
    "HARDWARE_LOG_SHA256|$hardwareLogSha256"
    "BIST_LOG_SHA256|$bistLogSha256"
    'NONVOLATILE_WRITE|0'
    'RECOVERY|Power-cycle the board if automatic DDR/APU restoration fails'
) | Set-Content -LiteralPath $manifest -Encoding utf8

if (-not $hardwarePass) {
    throw "XC7Z045 DDR capacity smoke failed; log: $hardwareLog. Power-cycle is the recovery path."
}
if (-not $bistPass) {
    throw "Final PL Fabric BIST check failed; log: $bistLog"
}

Write-Output 'XC7Z045_DDR_CAPACITY_VALIDATION_PASS|1'
Write-Output "DDR_CAPACITY_ARTIFACT_DIR|$outputDir"
