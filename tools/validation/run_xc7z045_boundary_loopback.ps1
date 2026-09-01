param(
    [string]$VivadoRoot = 'D:\Software\Xilinx\Vivado\2024.2',
    [string]$ServerUrl = 'tcp:127.0.0.1:3121',
    [int]$StartHwServerPort = 0,
    [switch]$AlreadyGuarded,
    [switch]$ConfirmHardwareTest
)

$ErrorActionPreference = 'Stop'

$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$workspaceRoot = (Resolve-Path (Join-Path $projectRoot 'workspaces\xc7z045_io_loopback')).Path
$guard = 'D:\lihuan\vibe_code\codex\scripts\resource-control\run-guarded.ps1'
$assertGuarded = 'D:\lihuan\vibe_code\codex\scripts\resource-control\assert-guarded.ps1'
$xsdb = Join-Path $VivadoRoot 'bin\xsdb.bat'
$hwServer = Join-Path $VivadoRoot 'bin\hw_server.bat'
$testScript = Join-Path $workspaceRoot 'xsdb\xc7z045_boundary_loopback.tcl'
$identityScript = Join-Path $codeRoot 'tools\fpga\xilinx_jtag\tcl\xsdb_list_jtag_targets.tcl'
$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'xc7z045_io_loopback'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'boundary_scan'
$logPath = Join-Path $outputDir 'boundary_loopback.log'
$identityLog = Join-Path $outputDir 'jtag_identity.log'
$hwServerStdout = Join-Path $outputDir 'hw_server.stdout.log'
$hwServerStderr = Join-Path $outputDir 'hw_server.stderr.log'
$manifest = Join-Path $outputDir 'manifest.txt'

if (-not $ConfirmHardwareTest) {
    throw 'Hardware gate not confirmed. Re-run with -ConfirmHardwareTest.'
}

foreach ($required in @($guard, $assertGuarded, $xsdb, $hwServer, $testScript, $identityScript)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

function Invoke-Logged {
    param([string]$CommandLine, [string]$OutputPath, [int]$TimeoutSeconds = 180)
    if ($AlreadyGuarded) {
        & cmd.exe /d /c $CommandLine 2>&1 | Tee-Object -FilePath $OutputPath | Out-Host
    } else {
        & $guard -ProjectRoot $projectRoot -TimeoutSeconds $TimeoutSeconds `
            -Command @('cmd.exe', '/d', '/c', $CommandLine) 2>&1 |
            Tee-Object -FilePath $OutputPath | Out-Host
    }
    return $LASTEXITCODE
}

if ($AlreadyGuarded) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $assertGuarded -ProjectRoot $projectRoot
    if ($LASTEXITCODE -ne 0) {
        throw 'Boundary loopback must run inside the project resource guard.'
    }
}

$serverProcess = $null
try {
    if ($StartHwServerPort -gt 0) {
        if (Get-NetTCPConnection -State Listen -LocalPort $StartHwServerPort -ErrorAction SilentlyContinue) {
            throw "TCP port $StartHwServerPort is already occupied; refusing an unverified JTAG route."
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
        if (-not $listening) {
            throw "Temporary hw_server did not listen on port $StartHwServerPort."
        }
    }

    $identityCommand = 'call "{0}" "{1}" "{2}" observer' -f $xsdb, $identityScript, $ServerUrl
    $identityExit = Invoke-Logged $identityCommand $identityLog 120
    if ($identityExit -ne 0 -or
        -not (Select-String -Quiet -Pattern '\bxc7z045\b' -LiteralPath $identityLog) -or
        (Select-String -Quiet -Pattern '\bxc7vx980t\b' -LiteralPath $identityLog)) {
        throw "JTAG identity gate failed; expected only XC7Z045. Log: $identityLog"
    }

    $cmdLine = 'call "{0}" "{1}" "{2}"' -f $xsdb, $testScript, $ServerUrl
    $testExit = Invoke-Logged $cmdLine $logPath 180
    if ($testExit -ne 0 -or
        -not (Select-String -Quiet -SimpleMatch 'SAMPLE_SUMMARY|pass=24|fail=0' -LiteralPath $logPath) -or
        -not (Select-String -Quiet -SimpleMatch 'BOUNDARY_LOOPBACK_PASS|pairs=6|samples=24' -LiteralPath $logPath)) {
        throw "XC7Z045 boundary loopback failed; log: $logPath"
    }

    @(
        'TARGET|XC7Z045-FFG900'
        "SERVER_URL|$ServerUrl"
        'TEST|BSDL EXTEST bidirectional 0/1 loopback'
        'J58_PAIRS|95-96,91-92,87-88'
        'J59_PAIRS|3-4,7-8,11-12'
        'PAIR_COUNT|6'
        'SAMPLE_COUNT|24'
        'PASS_COUNT|24'
        'FAIL_COUNT|0'
        'BOUNDARY_LOOPBACK_PASS|1'
        'NONVOLATILE_WRITE|0'
        "IDENTITY_LOG|$identityLog"
        "LOOPBACK_LOG|$logPath"
    ) | Set-Content -LiteralPath $manifest -Encoding utf8

    Write-Output 'XC7Z045_BOUNDARY_LOOPBACK_REVALIDATION_PASS|1'
} finally {
    if ($null -ne $serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
        $serverProcess.WaitForExit(5000) | Out-Null
    }
}

Write-Output "LOOPBACK_LOG|$logPath"
