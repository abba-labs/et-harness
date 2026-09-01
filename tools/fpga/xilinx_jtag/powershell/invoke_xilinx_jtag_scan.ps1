[CmdletBinding()]
param(
    [string]$VivadoRoot = 'D:\Software\Xilinx\Vivado\2024.2',
    [ValidateRange(1024, 65535)]
    [int]$ServerPort = 3122,
    [string]$ArtifactRoot
)

$ErrorActionPreference = 'Stop'

$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
if (-not $ArtifactRoot) {
    $runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'xilinx_jtag_scan'
    $ArtifactRoot = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'xilinx_jtag_scan'
}

$hwServer = Join-Path $VivadoRoot 'bin\hw_server.bat'
$vivado = Join-Path $VivadoRoot 'bin\vivado.bat'
$scanTcl = Join-Path $codeRoot 'tools\fpga\xilinx_jtag\tcl\vivado_scan_hw_devices.tcl'

foreach ($requiredPath in @($hwServer, $vivado, $scanTcl)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required file not found: $requiredPath"
    }
}

if (Get-NetTCPConnection -State Listen -LocalPort $ServerPort -ErrorAction SilentlyContinue) {
    throw "TCP port $ServerPort is already in use; refusing to stop or reuse an unknown hw_server."
}

New-Item -ItemType Directory -Force -Path $ArtifactRoot | Out-Null
$stdoutLog = Join-Path $ArtifactRoot 'hw_server.stdout.log'
$stderrLog = Join-Path $ArtifactRoot 'hw_server.stderr.log'
$vivadoLog = Join-Path $ArtifactRoot 'vivado_scan.log'
$vivadoJournal = Join-Path $ArtifactRoot 'vivado_scan.jou'
$serverStartedAfter = (Get-Date).AddSeconds(-1)
$ownedServerPid = $null

$server = Start-Process -FilePath $hwServer -ArgumentList @('-s', "tcp::$ServerPort") `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden -PassThru

try {
    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 250
        $listening = Get-NetTCPConnection -State Listen -LocalPort $ServerPort -ErrorAction SilentlyContinue
    } until ($listening -or $server.HasExited -or (Get-Date) -ge $deadline)

    if (-not $listening) {
        throw "Temporary hw_server did not listen on TCP port $ServerPort."
    }
    $ownedServerPid = @($listening | Select-Object -ExpandProperty OwningProcess -Unique)[0]

    & $vivado -mode batch -log $vivadoLog -journal $vivadoJournal `
        -source $scanTcl -tclargs "localhost:$ServerPort"
    if ($LASTEXITCODE -ne 0) {
        throw "Vivado JTAG scan failed with exit code $LASTEXITCODE."
    }
}
finally {
    if ($ownedServerPid) {
        $ownedServer = Get-CimInstance Win32_Process -Filter "ProcessId=$ownedServerPid" -ErrorAction SilentlyContinue
        if ($ownedServer -and
            $ownedServer.Name -eq 'hw_server.exe' -and
            $ownedServer.CreationDate -ge $serverStartedAfter -and
            $ownedServer.CommandLine -match ":$ServerPort(?:\\s|`"|$)") {
            Stop-Process -Id $ownedServerPid -Force -ErrorAction SilentlyContinue
        }
    }
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Output "JTAG_SCAN_ARTIFACTS=$ArtifactRoot"
