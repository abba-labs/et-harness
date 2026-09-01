[CmdletBinding()]
param(
    [string]$VivadoRoot = 'D:\Software\Xilinx\Vivado\2024.2',
    [string]$AdapterDescriptionPattern = '*Realtek USB GbE Family Controller*',
    [switch]$ConfirmHardwareWrite
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$guard = 'D:\lihuan\vibe_code\codex\scripts\resource-control\run-guarded.ps1'
$xsdb = Join-Path $VivadoRoot 'bin\xsdb.bat'
$testScript = Join-Path $projectRoot 'workspaces\xc7z045_ethernet_smoke\xsdb\read_phy_link.tcl'
$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'xc7z045_ethernet_phy'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'ethernet_phy_smoke'
$logPath = Join-Path $outputDir 'ethernet_phy_link.log'
$pcBeforePath = Join-Path $outputDir 'pc_adapter_before.txt'
$pcAfterPath = Join-Path $outputDir 'pc_adapter_after.txt'

if (-not $ConfirmHardwareWrite) {
    throw @'
Hardware gate not confirmed. This test temporarily enables GEM0 MDIO and
temporarily muxes MIO52/MIO53 to GEM0 MDC/MDIO. MIO52/MIO53 and GEM0
NWCFG/NWCTRL are restored and verified before exit.
Re-run after approval with -ConfirmHardwareWrite.
'@
}

foreach ($required in @($guard, $xsdb, $testScript)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required file not found: $required" }
}
$adapter = @(Get-NetAdapter | Where-Object {
    $_.InterfaceDescription -like $AdapterDescriptionPattern -and $_.Status -eq 'Up'
})
if ($adapter.Count -ne 1) {
    throw "Expected exactly one Up adapter matching '$AdapterDescriptionPattern', found $($adapter.Count)"
}
$adapter = $adapter[0]
if ($adapter.Status -ne 'Up' -or $adapter.LinkSpeed -ne '1 Gbps') {
    throw "Adapter '$($adapter.InterfaceDescription)' is not Up at 1 Gbps: status=$($adapter.Status), speed=$($adapter.LinkSpeed)"
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$adapter |
    Format-List Name,InterfaceDescription,Status,LinkSpeed,MediaType,ifIndex |
    Out-File -LiteralPath $pcBeforePath -Encoding utf8
Get-NetAdapterStatistics -InterfaceDescription $adapter.InterfaceDescription |
    Format-List * | Out-File -LiteralPath $pcBeforePath -Encoding utf8 -Append

$command = 'call "{0}" "{1}"' -f $xsdb, $testScript
& $guard `
    -ProjectRoot $projectRoot `
    -TimeoutSeconds 90 `
    -Command @('cmd.exe', '/d', '/c', $command) 2>&1 |
    Tee-Object -FilePath $logPath
$testExit = $LASTEXITCODE

Get-NetAdapter -InterfaceDescription $adapter.InterfaceDescription |
    Format-List Name,InterfaceDescription,Status,LinkSpeed,MediaType,ifIndex |
    Out-File -LiteralPath $pcAfterPath -Encoding utf8
Get-NetAdapterStatistics -InterfaceDescription $adapter.InterfaceDescription |
    Format-List * | Out-File -LiteralPath $pcAfterPath -Encoding utf8 -Append

if ($testExit -ne 0 -or
    -not (Select-String -Quiet -SimpleMatch 'ETHERNET_PHY_SELFTEST_PASS|1' -LiteralPath $logPath) -or
    -not (Select-String -Quiet -SimpleMatch 'GEM0_RESTORE_PASS|1' -LiteralPath $logPath) -or
    -not (Select-String -Quiet -SimpleMatch 'MIO_RESTORE_PASS|1' -LiteralPath $logPath)) {
    throw "XC7Z045 Ethernet PHY smoke failed; log: $logPath. Power-cycle is the recovery path."
}

$adapterAfter = Get-NetAdapter -InterfaceDescription $adapter.InterfaceDescription
if ($adapterAfter.Status -ne 'Up' -or $adapterAfter.LinkSpeed -ne '1 Gbps') {
    throw "PC link did not remain Up at 1 Gbps after PHY test"
}

Write-Output 'XC7Z045_ETHERNET_PHY_SMOKE_PASS|1'
Write-Output "ETHERNET_PHY_ARTIFACT_DIR|$outputDir"
