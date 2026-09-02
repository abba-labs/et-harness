param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$GatewayConfigPath
)

$ErrorActionPreference = 'Stop'

function Test-WindowsAbsolutePath {
    param([string]$Value)

    return $Value -match '^[A-Za-z]:[\\/]' -or $Value -match '^\\\\[^\\/]+[\\/][^\\/]+'
}

try {
    $configPath = [System.IO.Path]::GetFullPath($GatewayConfigPath)
    if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
        throw "Gateway config does not exist: $configPath"
    }

    $config = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
    $pointerValue = $config.runtimeReleasePointerPath
    if ($pointerValue -isnot [string] -or -not $pointerValue.Trim()) {
        throw 'Gateway config does not contain runtimeReleasePointerPath'
    }
    if (-not (Test-WindowsAbsolutePath $pointerValue)) {
        throw "Runtime release pointer must be absolute: $pointerValue"
    }

    $pointerPath = [System.IO.Path]::GetFullPath($pointerValue)
    if (-not (Test-Path -LiteralPath $pointerPath -PathType Leaf)) {
        throw "Runtime release pointer does not exist: $pointerPath"
    }

    $fastTrackStateRoot = Split-Path -Parent $pointerPath
    $stateRoot = Split-Path -Parent $fastTrackStateRoot
    $environmentRoot = Split-Path -Parent $stateRoot
    if (-not $environmentRoot -or -not (Test-WindowsAbsolutePath $environmentRoot)) {
        throw "Runtime release pointer does not identify an absolute machine environment: $pointerPath"
    }
    if (-not (Test-Path -LiteralPath $environmentRoot -PathType Container)) {
        throw "Machine environment root does not exist: $environmentRoot"
    }

    [Console]::Out.WriteLine([System.IO.Path]::GetFullPath($environmentRoot))
}
catch {
    [Console]::Error.WriteLine("ET Harness environment resolution failed: $($_.Exception.Message)")
    exit 1
}
