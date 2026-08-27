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
$workspace = Join-Path $projectRoot 'workspaces\xc7z045_ps_selftest'
$buildScript = Join-Path $workspace 'build_ps_selftest.cmd'
$elf = Join-Path $workspace 'build\ps_selftest.elf'
$runner = Join-Path $workspace 'xsdb\run_ddr_l2_selftest.tcl'
$boot = Join-Path $projectRoot 'tmp\et6001_z7_boot.bin'
$bistReader = Join-Path $projectRoot 'workspaces\xc7z045_fabric_bist\xsdb\read_fabric_bist_status.tcl'
$expectedBootSha256 = '6335508377CA8D7D878AA79722958708D7615DF888A9C01CB5EA2E0F4FF32455'
$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'xc7z045_ddr_l2'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'ddr_l2_selftest'
$backup = Join-Path $outputDir 'ddr_0x3fffc000_16k_before_test.bin'
$buildLog = Join-Path $outputDir 'build.log'
$hardwareLog = Join-Path $outputDir 'ddr_l2_hardware.log'
$bistLog = Join-Path $outputDir 'fabric_bist_final.log'
$manifest = Join-Path $outputDir 'manifest.txt'

if (-not $ConfirmHardwareWrite) {
    throw @'
Hardware gate not confirmed. This test will initialize volatile DDR using the
original board FSBL revision-3 settings and write 16 KiB at
0x3FFFC000..0x3FFFFFFF. Re-run only after approval with
-ConfirmHardwareWrite. No nonvolatile storage is written.
'@
}

foreach ($required in @($guard, $xsdb, $buildScript, $runner, $boot, $bistReader)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

$actualBootSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $boot).Hash
if ($actualBootSha256 -ne $expectedBootSha256) {
    throw "BOOT.bin SHA256 mismatch: expected $expectedBootSha256, got $actualBootSha256"
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$buildCommand = 'call "{0}"' -f $buildScript
& $guard `
    -ProjectRoot $projectRoot `
    -TimeoutSeconds 120 `
    -Command @('cmd.exe', '/d', '/c', $buildCommand) 2>&1 |
    Tee-Object -FilePath $buildLog
$buildExit = $LASTEXITCODE
if ($buildExit -ne 0) {
    throw "XC7Z045 PS self-test build failed with exit code $buildExit; log: $buildLog"
}

$hardwareCommand = 'call "{0}" "{1}" "{2}" "{3}" "{4}" hardware' -f `
    $xsdb, $runner, $elf, $boot, $backup
& $guard `
    -ProjectRoot $projectRoot `
    -TimeoutSeconds 240 `
    -Command @('cmd.exe', '/d', '/c', $hardwareCommand) 2>&1 |
    Tee-Object -FilePath $hardwareLog
$hardwareExit = $LASTEXITCODE
if ($hardwareExit -ne 0 -or
    -not (Select-String -Quiet -SimpleMatch 'DDR_L2_SELFTEST_PASS|1' -LiteralPath $hardwareLog)) {
    throw "XC7Z045 DDR/L2 hardware test failed; log: $hardwareLog. Power-cycle is the recovery path."
}

$bistCommand = 'call "{0}" "{1}"' -f $xsdb, $bistReader
& $guard `
    -ProjectRoot $projectRoot `
    -TimeoutSeconds 120 `
    -Command @('cmd.exe', '/d', '/c', $bistCommand) 2>&1 |
    Tee-Object -FilePath $bistLog
$bistExit = $LASTEXITCODE
if ($bistExit -ne 0 -or
    -not (Select-String -Quiet -SimpleMatch 'FABRIC_BIST_HARDWARE_PASS|1' -LiteralPath $bistLog)) {
    throw "Final PL Fabric BIST check failed; log: $bistLog"
}

$elfSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $elf).Hash
@(
    'TARGET|XC7Z045-FFG900'
    'ROUTE|Digilent JTAG-SMT2'
    'DDR_TEST_RANGE|0x3FFFC000-0x3FFFFFFF'
    "BOOT_SHA256|$actualBootSha256"
    "ELF_SHA256|$elfSha256"
    "BACKUP|$backup"
    "HARDWARE_LOG|$hardwareLog"
    "BIST_LOG|$bistLog"
    'NONVOLATILE_WRITE|0'
) | Set-Content -LiteralPath $manifest -Encoding utf8

Write-Output 'XC7Z045_DDR_L2_VALIDATION_PASS|1'
Write-Output "DDR_L2_ARTIFACT_DIR|$outputDir"
