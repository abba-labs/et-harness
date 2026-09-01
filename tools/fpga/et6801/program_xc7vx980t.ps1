[CmdletBinding()]
param(
    [Alias('VivadoRoot')]
    [string]$ToolRoot,
    [string]$BitFile,
    [int]$ServerPort = 3121,
    [Alias('ConfirmVolatileProgram')]
    [switch]$ConfirmProgram,
    [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
if (-not $ToolRoot) {
    throw 'ToolRoot is required.'
}
if (-not $BitFile) {
    throw 'BitFile is required.'
}
$vivado = Join-Path $ToolRoot 'bin\vivado.bat'
$hwServer = Join-Path $ToolRoot 'bin\hw_server.bat'
$tcl = Join-Path $PSScriptRoot 'tcl\program_xc7vx980t.tcl'

foreach ($required in @($vivado, $hwServer, $tcl, $BitFile)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

$bit = Get-Item -LiteralPath $BitFile
$bitHash = (Get-FileHash -LiteralPath $bit.FullName -Algorithm SHA256).Hash

if ($PrepareOnly) {
    [pscustomobject]@{
        Action = 'XC7VX980T volatile SRAM configuration'
        ServerUrl = "localhost:$ServerPort"
        BitFile = $bit.FullName
        Bytes = $bit.Length
        SHA256 = $bitHash
        Destructive = $false
        Recovery = 'Reprogram the previous bitfile or power-cycle the FPGA board.'
    } | Format-List
    exit 0
}

if (-not $ConfirmProgram) {
    throw 'Hardware gate not confirmed. Re-run with -ConfirmProgram.'
}

$mutex = [System.Threading.Mutex]::new($false, 'Global\ET_XC7VX980T_VOLATILE_PROGRAM')
$mutexOwned = $false
if (-not $mutex.WaitOne(0)) {
    $mutex.Dispose()
    throw 'Another XC7VX980T programming operation is already running on this computer.'
}
$mutexOwned = $true

$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'xc7vx980t_program'
$outputDir = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'deploy_bitfile'
$vivadoLog = Join-Path $outputDir 'vivado_program.log'
$vivadoJournal = Join-Path $outputDir 'vivado_program.jou'
$properties = Join-Path $outputDir 'xc7vx980t_properties.txt'
$serverStdout = Join-Path $outputDir 'hw_server.stdout.log'
$serverStderr = Join-Path $outputDir 'hw_server.stderr.log'
$manifest = Join-Path $outputDir 'manifest.txt'
$serverUrl = "localhost:$ServerPort"
$serverProcess = $null
$reusedServer = $false
$serverStartedAfter = $null
$ownedServerPid = $null

try {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $ServerPort -ErrorAction SilentlyContinue
    if ($listener) {
        $reusedServer = $true
    }
    else {
        $serverStartedAfter = (Get-Date).AddSeconds(-1)
        $serverProcess = Start-Process -FilePath $hwServer `
            -ArgumentList @('-s', "tcp::$ServerPort") `
            -RedirectStandardOutput $serverStdout `
            -RedirectStandardError $serverStderr `
            -WindowStyle Hidden -PassThru

        $deadline = (Get-Date).AddSeconds(20)
        do {
            Start-Sleep -Milliseconds 250
            if ($serverProcess.HasExited) {
                throw "Temporary hw_server exited with code $($serverProcess.ExitCode)."
            }
            $listener = Get-NetTCPConnection -State Listen -LocalPort $ServerPort -ErrorAction SilentlyContinue
        } until ($listener -or (Get-Date) -ge $deadline)
        if (-not $listener) {
            throw "Temporary hw_server did not listen on port $ServerPort."
        }
        $ownedServerPid = @($listener | Select-Object -ExpandProperty OwningProcess -Unique)[0]
    }

    & cmd.exe /d /c ('call "{0}" -mode batch -source "{1}" -log "{2}" -journal "{3}" -tclargs "{4}" "{5}" "{6}"' -f `
        $vivado, $tcl, $vivadoLog, $vivadoJournal, $bit.FullName, $serverUrl, $properties) 2>&1 | Out-Host

    if ($LASTEXITCODE -ne 0 -or
        -not (Select-String -Quiet -SimpleMatch 'XC7VX980T_VOLATILE_PROGRAM_PASS' -LiteralPath $vivadoLog)) {
        throw "XC7VX980T volatile programming failed. Log: $vivadoLog"
    }

    @(
        "time=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
        'target=XC7VX980T'
        "server_url=$serverUrl"
        "reused_hw_server=$reusedServer"
        "bitfile=$($bit.FullName)"
        "bitfile_bytes=$($bit.Length)"
        "bitfile_sha256=$bitHash"
        'write_scope=volatile FPGA configuration SRAM only'
        'result=PASS'
    ) | Set-Content -LiteralPath $manifest -Encoding UTF8

    Write-Output "XC7VX980T_VOLATILE_PROGRAM_PASS|artifact=$outputDir"
}
finally {
    if (-not $reusedServer -and $ownedServerPid) {
        $ownedServer = Get-CimInstance Win32_Process -Filter "ProcessId=$ownedServerPid" -ErrorAction SilentlyContinue
        if ($ownedServer -and
            $ownedServer.Name -eq 'hw_server.exe' -and
            $ownedServer.CreationDate -ge $serverStartedAfter -and
            $ownedServer.CommandLine -match ":$ServerPort(?:\\s|`"|$)") {
            Stop-Process -Id $ownedServerPid -Force -ErrorAction SilentlyContinue
        }
    }
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($mutexOwned) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
