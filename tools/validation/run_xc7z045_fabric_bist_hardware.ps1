[CmdletBinding()]
param(
    [string]$VivadoRoot = 'D:\Software\Xilinx\Vivado\2024.2',
    [string]$BitFile,
    [int]$ServerPort = 3122,
    [switch]$ConfirmVolatileProgram
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$assertGuarded = 'D:\lihuan\vibe_code\codex\scripts\resource-control\assert-guarded.ps1'
$vivado = Join-Path $VivadoRoot 'bin\vivado.bat'
$xsdb = Join-Path $VivadoRoot 'bin\xsdb.bat'
$hwServer = Join-Path $VivadoRoot 'bin\hw_server.bat'
$programScript = Join-Path $codeRoot 'tools\validation\fpga_program_fabric_bist.tcl'
$identityScript = Join-Path $codeRoot 'tools\fpga\xilinx_jtag\tcl\xsdb_list_jtag_targets.tcl'
$statusScript = Join-Path $projectRoot 'workspaces\xc7z045_fabric_bist\xsdb\read_fabric_bist_status.tcl'

if (-not $BitFile) {
    throw 'BitFile is required; historical artifacts are not valid implicit inputs.'
}

if (-not $ConfirmVolatileProgram) {
    throw 'Hardware gate not confirmed. Re-run with -ConfirmVolatileProgram.'
}

foreach ($required in @(
    $assertGuarded, $vivado, $xsdb, $hwServer, $programScript,
    $identityScript, $statusScript, $BitFile
)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $assertGuarded -ProjectRoot $projectRoot
if ($LASTEXITCODE -ne 0) {
    throw 'The Fabric BIST hardware test must run inside the project resource guard.'
}

$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'xc7z045_fabric_bist'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'fabric_bist_hardware'

$identityLog = Join-Path $outputDir 'jtag_identity.log'
$programLog = Join-Path $outputDir 'vivado_program.log'
$programJournal = Join-Path $outputDir 'vivado_program.jou'
$propertyLog = Join-Path $outputDir 'xc7z045_properties_after_program.txt'
$statusLog = Join-Path $outputDir 'fabric_bist_status.log'
$hwServerStdout = Join-Path $outputDir 'hw_server.stdout.log'
$hwServerStderr = Join-Path $outputDir 'hw_server.stderr.log'
$manifest = Join-Path $outputDir 'manifest.txt'
$xsdbUrl = "tcp:127.0.0.1:$ServerPort"
$vivadoUrl = "localhost:$ServerPort"

if (Get-NetTCPConnection -State Listen -LocalPort $ServerPort -ErrorAction SilentlyContinue) {
    throw "TCP port $ServerPort is already occupied; refusing an unverified JTAG route."
}

$serverProcess = $null
try {
    $serverProcess = Start-Process -FilePath $hwServer `
        -ArgumentList @('-s', "tcp::$ServerPort") `
        -RedirectStandardOutput $hwServerStdout `
        -RedirectStandardError $hwServerStderr `
        -WindowStyle Hidden -PassThru

    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 250
        if ($serverProcess.HasExited) {
            throw "Temporary hw_server exited with code $($serverProcess.ExitCode)."
        }
        $listening = Get-NetTCPConnection -State Listen -LocalPort $ServerPort -ErrorAction SilentlyContinue
    } until ($listening -or (Get-Date) -ge $deadline)
    if (-not $listening) {
        throw "Temporary hw_server did not listen on port $ServerPort."
    }

    & cmd.exe /d /c ('call "{0}" "{1}" "{2}" observer' -f $xsdb, $identityScript, $xsdbUrl) `
        2>&1 | Tee-Object -FilePath $identityLog | Out-Host
    $identityExit = $LASTEXITCODE
    if ($identityExit -ne 0 -or
        -not (Select-String -Quiet -Pattern '\bxc7z045\b' -LiteralPath $identityLog) -or
        (Select-String -Quiet -Pattern '\bxc7vx980t\b' -LiteralPath $identityLog)) {
        throw "JTAG identity gate failed; expected only XC7Z045. Log: $identityLog"
    }

    & cmd.exe /d /c ('call "{0}" -mode batch -source "{1}" -log "{2}" -journal "{3}" -tclargs "{4}" "{5}" "{6}"' -f `
        $vivado, $programScript, $programLog, $programJournal, $BitFile, $propertyLog, $vivadoUrl) `
        2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0 -or
        -not (Select-String -Quiet -SimpleMatch 'VOLATILE_SRAM_PROGRAM_PASS|1' -LiteralPath $programLog)) {
        throw "XC7Z045 volatile PL programming failed. Log: $programLog"
    }

    & cmd.exe /d /c ('call "{0}" "{1}" "{2}"' -f $xsdb, $statusScript, $xsdbUrl) `
        2>&1 | Tee-Object -FilePath $statusLog | Out-Host
    if ($LASTEXITCODE -ne 0 -or
        -not (Select-String -Quiet -SimpleMatch 'FINAL_STATUS|0xB101FFF0' -LiteralPath $statusLog) -or
        -not (Select-String -Quiet -SimpleMatch 'FABRIC_BIST_HARDWARE_PASS|1' -LiteralPath $statusLog)) {
        throw "XC7Z045 Fabric BIST failed. Log: $statusLog"
    }

    $bitSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $BitFile).Hash
    @(
        'TARGET|XC7Z045-FFG900'
        "SERVER_URL|$xsdbUrl"
        "BIT_FILE|$BitFile"
        "BIT_SHA256|$bitSha256"
        'PROGRAM_MODE|volatile SRAM only'
        'EXPECTED_STATUS|0xB101FFF0'
        'FINAL_STATUS|0xB101FFF0'
        'LOGIC_BIST|PASS'
        'BRAM_BIST|PASS'
        'DSP_BIST|PASS'
        'MMCM_LOCK|PASS'
        'FABRIC_BIST_HARDWARE_PASS|1'
        'NONVOLATILE_WRITE|0'
        "IDENTITY_LOG|$identityLog"
        "PROGRAM_LOG|$programLog"
        "STATUS_LOG|$statusLog"
    ) | Set-Content -LiteralPath $manifest -Encoding utf8

    Write-Output 'XC7Z045_FABRIC_BIST_REVALIDATION_PASS|1'
    Write-Output "FABRIC_BIST_ARTIFACT_DIR|$outputDir"
} finally {
    if ($null -ne $serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
        $serverProcess.WaitForExit(5000) | Out-Null
    }
}
