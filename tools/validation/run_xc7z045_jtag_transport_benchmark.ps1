[CmdletBinding()]
param(
    [string]$VivadoRoot = 'D:\Software\Xilinx\Vivado\2024.2',
    [string]$Python = 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$ServerUrl = 'tcp:127.0.0.1:3121',
    [int]$StartHwServerPort = 0,
    [switch]$AlreadyGuarded,
    [switch]$ConfirmHardwareWrite
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$guard = 'D:\lihuan\vibe_code\codex\scripts\resource-control\run-guarded.ps1'
$xsdb = Join-Path $VivadoRoot 'bin\xsdb.bat'
$hwServer = Join-Path $VivadoRoot 'bin\hw_server.bat'
$workspace = Join-Path $projectRoot 'workspaces\xc7z045_jtag_transport'
$build = Join-Path $workspace 'build_jtag_agent.cmd'
$agent = Join-Path $workspace 'build\jtag_agent.elf'
$manager = Join-Path $workspace 'xsdb\manage_agent.tcl'
$bridge = Join-Path $workspace 'xsdb\jtag_bridge.tcl'
$benchmark = Join-Path $workspace 'host\benchmark.py'
$bistReader = Join-Path $projectRoot 'workspaces\xc7z045_fabric_bist\xsdb\read_fabric_bist_status.tcl'
$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'xc7z045_jtag_transport'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'jtag_transport_benchmark'
$ocmBackup = Join-Path $outputDir 'ocm_0xffff0000_64k_before.bin'
$ddrBackup = Join-Path $outputDir 'ddr_0x3fffc000_16k_before.bin'
$resultJson = Join-Path $outputDir 'benchmark.json'
$buildLog = Join-Path $outputDir 'build.log'
$prepareLog = Join-Path $outputDir 'prepare.log'
$benchmarkLog = Join-Path $outputDir 'benchmark.log'
$restoreLog = Join-Path $outputDir 'restore.log'
$bistLog = Join-Path $outputDir 'fabric_bist_final.log'
$manifest = Join-Path $outputDir 'manifest.txt'
$identityLog = Join-Path $outputDir 'jtag_identity.log'
$hwServerStdout = Join-Path $outputDir 'hw_server.stdout.log'
$hwServerStderr = Join-Path $outputDir 'hw_server.stderr.log'
$discoveryScript = Join-Path $codeRoot 'tools\fpga\xilinx_jtag\tcl\xsdb_list_jtag_targets.tcl'

if (-not $ConfirmHardwareWrite) {
    throw @'
Hardware gate not confirmed. This benchmark stops both Cortex-A9 cores, backs
up and temporarily writes high OCM 0xFFFF0000..0xFFFFFFFF and the already
qualified DDR window 0x3FFFC000..0x3FFFFFFF, runs the volatile JTAG agent,
restores and read-verifies both windows, then resets both cores to run. It does
not write Flash, QSPI, SD, OTP, NVR or fuses. Re-run only after approval with
-ConfirmHardwareWrite. A power cycle is the final recovery path.
'@
}

foreach ($required in @($guard, $xsdb, $hwServer, $Python, $build, $manager, $bridge, $benchmark, $bistReader, $discoveryScript)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required file not found: $required" }
}
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

function Invoke-GuardedLogged {
    param([string]$CommandLine, [string]$LogPath, [int]$TimeoutSeconds = 180)
    if ($AlreadyGuarded) {
        & cmd.exe /d /c $CommandLine 2>&1 | Tee-Object -FilePath $LogPath | Out-Host
    } else {
        & $guard -ProjectRoot $projectRoot -TimeoutSeconds $TimeoutSeconds `
            -Command @('cmd.exe', '/d', '/c', $CommandLine) 2>&1 |
            Tee-Object -FilePath $LogPath | Out-Host
    }
    $exitCode = $LASTEXITCODE
    return $exitCode
}

$serverProcess = $null
try {
    if ($StartHwServerPort -gt 0) {
        if (Get-NetTCPConnection -State Listen -LocalPort $StartHwServerPort -ErrorAction SilentlyContinue) {
            throw "TCP port $StartHwServerPort is already in use; refusing to attach an unverified server."
        }
        $serverProcess = Start-Process -FilePath $hwServer `
            -ArgumentList @('-s', "tcp::$StartHwServerPort") `
            -RedirectStandardOutput $hwServerStdout `
            -RedirectStandardError $hwServerStderr `
            -WindowStyle Hidden -PassThru
        $deadline = (Get-Date).AddSeconds(20)
        do {
            Start-Sleep -Milliseconds 250
            if ($serverProcess.HasExited) {
                throw "Temporary hw_server exited with code $($serverProcess.ExitCode)."
            }
            $listening = Get-NetTCPConnection -State Listen -LocalPort $StartHwServerPort -ErrorAction SilentlyContinue
        } until ($listening -or (Get-Date) -ge $deadline)
        if (-not $listening) { throw "Temporary hw_server did not listen on port $StartHwServerPort." }
    }

    $identityCommand = 'call "{0}" "{1}" "{2}" observer' -f $xsdb, $discoveryScript, $ServerUrl
    $identityExit = Invoke-GuardedLogged $identityCommand $identityLog 120
    if ($identityExit -ne 0 -or
        -not (Select-String -Quiet -Pattern '\bxc7z045\b' -LiteralPath $identityLog) -or
        (Select-String -Quiet -Pattern '\bxc7vx980t\b' -LiteralPath $identityLog)) {
        throw "JTAG identity gate failed; expected XC7Z045 only. Log: $identityLog"
    }

    $buildCommand = 'call "{0}"' -f $build
    if ((Invoke-GuardedLogged $buildCommand $buildLog 120) -ne 0) {
        throw "JTAG agent build failed; log: $buildLog"
    }

    $prepared = $false
    $benchmarkPassed = $false
    $primaryError = $null
    try {
        $prepareCommand = 'call "{0}" "{1}" prepare "{2}" "{3}" "{4}" "{5}"' -f `
            $xsdb, $manager, $agent, $ocmBackup, $ddrBackup, $ServerUrl
        $prepareExit = Invoke-GuardedLogged $prepareCommand $prepareLog 120
        if ($prepareExit -ne 0 -or
            -not (Select-String -Quiet -SimpleMatch 'JTAG_AGENT_READY|1' -LiteralPath $prepareLog)) {
            throw "JTAG agent preparation failed; log: $prepareLog"
        }
        $prepared = $true

        $benchmarkCommand = '"{0}" "{1}" --xsdb "{2}" --bridge "{3}" --output "{4}" --server-url "{5}"' -f `
            $Python, $benchmark, $xsdb, $bridge, $resultJson, $ServerUrl
        $benchmarkExit = Invoke-GuardedLogged $benchmarkCommand $benchmarkLog 300
        if ($benchmarkExit -ne 0 -or
            -not (Select-String -Quiet -SimpleMatch 'JTAG_TRANSPORT_BENCHMARK_PASS|1' -LiteralPath $benchmarkLog) -or
            -not (Test-Path -LiteralPath $resultJson)) {
            throw "JTAG transport benchmark failed; log: $benchmarkLog"
        }
        $benchmarkPassed = $true
    } catch {
        $primaryError = $_
    } finally {
        if ((Test-Path -LiteralPath $ocmBackup) -and (Test-Path -LiteralPath $ddrBackup)) {
            $restoreCommand = 'call "{0}" "{1}" restore "{2}" "{3}" "{4}" "{5}"' -f `
                $xsdb, $manager, $agent, $ocmBackup, $ddrBackup, $ServerUrl
            $restoreExit = Invoke-GuardedLogged $restoreCommand $restoreLog 180
            if ($restoreExit -ne 0 -or
                -not (Select-String -Quiet -SimpleMatch 'OCM_RESTORE_PASS|1' -LiteralPath $restoreLog) -or
                -not (Select-String -Quiet -SimpleMatch 'DDR_RESTORE_PASS|1' -LiteralPath $restoreLog) -or
                -not (Select-String -Quiet -SimpleMatch 'APU_RESET_RUN_PASS|1' -LiteralPath $restoreLog)) {
                throw "Volatile state restore failed; power-cycle the board. Log: $restoreLog"
            }
        } elseif ($prepared) {
            throw 'Agent was prepared but backups are missing; power-cycle the board.'
        }
    }

    if ($null -ne $primaryError) { throw $primaryError }
    if (-not $benchmarkPassed) { throw 'Benchmark did not complete.' }

    $bistCommand = 'call "{0}" "{1}" "{2}"' -f $xsdb, $bistReader, $ServerUrl
    $bistExit = Invoke-GuardedLogged $bistCommand $bistLog 120
    if ($bistExit -ne 0 -or
        -not (Select-String -Quiet -SimpleMatch 'FABRIC_BIST_HARDWARE_PASS|1' -LiteralPath $bistLog)) {
        throw "Final PL Fabric BIST check failed; log: $bistLog"
    }
} finally {
    if ($null -ne $serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
        $serverProcess.WaitForExit(5000) | Out-Null
    }
}

$agentSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $agent).Hash
@(
    'TARGET|XC7Z045-FFG900'
    'ROUTE|Digilent JTAG-SMT2 / XSDB / ARM DAP'
    "SERVER_URL|$ServerUrl"
    'OCM_TEMP_RANGE|0xFFFF0000-0xFFFFFFFF'
    'DDR_TEMP_RANGE|0x3FFFC000-0x3FFFFFFF'
    "AGENT_SHA256|$agentSha256"
    "RESULT_JSON|$resultJson"
    "OCM_BACKUP|$ocmBackup"
    "DDR_BACKUP|$ddrBackup"
    "PREPARE_LOG|$prepareLog"
    "BENCHMARK_LOG|$benchmarkLog"
    "RESTORE_LOG|$restoreLog"
    "BIST_LOG|$bistLog"
    "IDENTITY_LOG|$identityLog"
    'NONVOLATILE_WRITE|0'
) | Set-Content -LiteralPath $manifest -Encoding utf8

Write-Output 'XC7Z045_JTAG_TRANSPORT_VALIDATION_PASS|1'
Write-Output "JTAG_TRANSPORT_ARTIFACT_DIR|$outputDir"
