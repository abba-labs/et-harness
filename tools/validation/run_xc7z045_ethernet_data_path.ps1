[CmdletBinding()]
param(
    [string]$VivadoRoot = 'D:\Software\Xilinx\Vivado\2024.2',
    [string]$AdapterDescriptionPattern = '*Realtek USB GbE Family Controller*',
    [switch]$PhyLoopback,
    [switch]$GemLocalLoopback,
    [ValidateSet('both', 'rx', 'tx', 'none')]
    [string]$RgmiiDelay = 'both',
    [switch]$ConfirmHardwareWrite
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$guard = 'D:\lihuan\vibe_code\codex\scripts\resource-control\run-guarded.ps1'
$xsdb = Join-Path $VivadoRoot 'bin\xsdb.bat'
$workspace = Join-Path $projectRoot 'workspaces\xc7z045_ethernet_data_path'
$buildScript = Join-Path $workspace 'build_ethernet_data_path.cmd'
$elf = Join-Path $workspace 'build\ethernet_data_path.elf'
$runner = Join-Path $workspace 'xsdb\run_ethernet_data_path.tcl'
$benchmark = Join-Path $workspace 'tools\udp_echo_benchmark.py'
$python = (Get-Command python.exe -ErrorAction Stop).Source
$boardAddress = '169.254.200.139'
$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'xc7z045_ethernet_data'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'ethernet_data_path'
$buildLog = Join-Path $outputDir 'build.log'
$hardwareLog = Join-Path $outputDir 'ethernet_data_path.log'
$pcBefore = Join-Path $outputDir 'pc_adapter_before.txt'
$pcAfter = Join-Path $outputDir 'pc_adapter_after.txt'
$ocmBackup = Join-Path $outputDir 'high_ocm_before.bin'
$ocmReadback = Join-Path $outputDir 'high_ocm_restored_readback.bin'
$manifest = Join-Path $outputDir 'manifest.txt'

if (-not $ConfirmHardwareWrite) {
    throw @'
Hardware gate not confirmed. The test temporarily resets/stops Cortex-A9,
overwrites and restores the mapped 64 KiB high OCM bank, muxes GEM0 RGMII/MDIO MIO pins, changes the
GEM0 clock/registers, and may reset/restart PHY autonegotiation. It uses the
adapter's existing APIPA address and does not modify PC IP configuration. No
nonvolatile storage is written. Re-run only after approval with
-ConfirmHardwareWrite.
'@
}
if ($PhyLoopback -and $GemLocalLoopback) {
    throw 'Choose only one loopback profile'
}

foreach ($required in @($guard, $xsdb, $buildScript, $runner, $benchmark, $python)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required file not found: $required" }
}

$adapter = @(Get-NetAdapter | Where-Object {
    $_.InterfaceDescription -like $AdapterDescriptionPattern -and $_.Status -eq 'Up'
})
if ($adapter.Count -ne 1) {
    throw "Expected exactly one Up adapter matching '$AdapterDescriptionPattern', found $($adapter.Count)"
}
$adapter = $adapter[0]
if ($adapter.LinkSpeed -ne '1 Gbps') {
    throw "Adapter '$($adapter.InterfaceDescription)' is not linked at 1 Gbps"
}
$pcAddress = @(Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 `
    -ErrorAction Stop | Where-Object {
        $_.IPAddress -like '169.254.*' -and $_.AddressState -eq 'Preferred'
    }) | Select-Object -First 1
if ($null -eq $pcAddress) {
    throw 'The USB GbE adapter has no Preferred 169.254/16 APIPA address'
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$adapter | Format-List Name,InterfaceDescription,Status,LinkSpeed,MediaType,ifIndex |
    Out-File -LiteralPath $pcBefore -Encoding utf8
Get-NetAdapterStatistics -InterfaceDescription $adapter.InterfaceDescription |
    Format-List * | Out-File -LiteralPath $pcBefore -Encoding utf8 -Append

if ($PhyLoopback) {
    $reg21 = (@{
        both = '0x2030u'
        rx   = '0x2020u'
        tx   = '0x2010u'
        none = '0x2000u'
    })[$RgmiiDelay]
    $buildCommand = 'set "ETHERNET_TEST_DEFINES=-DPHY_LOOPBACK_TEST=1" && set "PHY_LOOPBACK_REG21_DEFINE=-DPHY_LOOPBACK_REG21={0}" && call "{1}" 2>&1' -f `
        $reg21, $buildScript
} elseif ($GemLocalLoopback) {
    $buildCommand = 'set "ETHERNET_TEST_DEFINES=-DGEM_LOCAL_LOOPBACK_TEST=1" && call "{0}" 2>&1' -f $buildScript
} else {
    $buildCommand = 'call "{0}" 2>&1' -f $buildScript
}
$savedErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $guard -ProjectRoot $projectRoot -TimeoutSeconds 120 `
    -Command @('cmd.exe', '/d', '/c', $buildCommand) 2>&1 |
    Tee-Object -FilePath $buildLog
$buildExit = $LASTEXITCODE
$ErrorActionPreference = $savedErrorActionPreference
if ($buildExit -ne 0) { throw "Ethernet firmware build failed; log: $buildLog" }

$hardwareExit = 1
try {
    $profile = if ($PhyLoopback) { 'phy-loopback' } elseif ($GemLocalLoopback) { 'gem-loopback' } else { 'network' }
    $hardwareCommand = 'call "{0}" "{1}" "{2}" "{3}" "{4}" "{5}" "{6}" hardware {7}' -f `
        $xsdb, $runner, $elf, $ocmBackup, $ocmReadback, $benchmark, $python, $profile
    $ErrorActionPreference = 'Continue'
    & $guard -ProjectRoot $projectRoot -TimeoutSeconds 180 `
        -Command @('cmd.exe', '/d', '/c', $hardwareCommand) 2>&1 |
        Tee-Object -FilePath $hardwareLog
    $hardwareExit = $LASTEXITCODE
    $ErrorActionPreference = $savedErrorActionPreference
}
finally {
    $ErrorActionPreference = $savedErrorActionPreference
    Get-NetAdapter -InterfaceDescription $adapter.InterfaceDescription |
        Format-List Name,InterfaceDescription,Status,LinkSpeed,MediaType,ifIndex |
        Out-File -LiteralPath $pcAfter -Encoding utf8
    Get-NetAdapterStatistics -InterfaceDescription $adapter.InterfaceDescription |
        Format-List * | Out-File -LiteralPath $pcAfter -Encoding utf8 -Append
}

$profilePass = if ($PhyLoopback) {
    Select-String -Quiet -SimpleMatch 'GEM0_RGMII_PHY_DIGITAL_LOOPBACK_PASS|1' `
        -LiteralPath $hardwareLog
} elseif ($GemLocalLoopback) {
    Select-String -Quiet -SimpleMatch 'GEM0_LOCAL_LOOPBACK_PASS|1' `
        -LiteralPath $hardwareLog
} else {
    (Select-String -Quiet -SimpleMatch 'GEM0_RGMII_DMA_DATA_PATH_PASS|1' -LiteralPath $hardwareLog) -and
    (Select-String -Quiet -SimpleMatch 'ICMP_PING_PASS|1' -LiteralPath $hardwareLog) -and
    (Select-String -Quiet -SimpleMatch 'UDP_ECHO_BENCHMARK_PASS|1' -LiteralPath $hardwareLog)
}
if ($hardwareExit -ne 0 -or -not $profilePass -or
    -not (Select-String -Quiet -SimpleMatch 'ETHERNET_DATA_PATH_CLEANUP_PASS|1' -LiteralPath $hardwareLog) -or
    -not (Select-String -Quiet -SimpleMatch 'ETHERNET_DATA_PATH_SELFTEST_PASS|1' -LiteralPath $hardwareLog)) {
    throw "XC7Z045 Ethernet data-path test failed; log: $hardwareLog. Power-cycle is the recovery path."
}

$adapterAfter = Get-NetAdapter -InterfaceDescription $adapter.InterfaceDescription
if ($adapterAfter.Status -ne 'Up' -or $adapterAfter.LinkSpeed -ne '1 Gbps') {
    throw 'PC adapter did not remain Up at 1 Gbps after cleanup'
}

$elfSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $elf).Hash
@(
    'TARGET|XC7Z045-FFG900'
    'ROUTE|Digilent JTAG-SMT2 + GEM0 RGMII + J54 + PC USB GbE'
    "BOARD_IP|$BoardAddress"
    "PC_EXISTING_APIPA|$($pcAddress.IPAddress)"
    "RGMII_DELAY_PROFILE|$RgmiiDelay"
    "ELF_SHA256|$elfSha256"
    "OCM_BACKUP|$ocmBackup"
    "HARDWARE_LOG|$hardwareLog"
    'NONVOLATILE_WRITE|0'
) | Set-Content -LiteralPath $manifest -Encoding utf8

Write-Output 'XC7Z045_ETHERNET_DATA_PATH_PASS|1'
Write-Output "ETHERNET_DATA_PATH_ARTIFACT_DIR|$outputDir"
