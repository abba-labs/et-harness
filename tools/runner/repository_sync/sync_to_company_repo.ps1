# ET automated testing platform company-repository copy tool.
# Responsibility: copy formal files from the current source worktree to a target directory.
# Boundary: overwrite matching files, keep target-only files, and never commit or push.

[CmdletBinding()]
param(
    [string]$Destination = 'D:\lihuan\vibe_code\code\SDK\git\Et_Automated_Testing_Platform_Code\et_automated_testing_platform',
    [string]$SourceRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SOURCE_ROOT_FROM_SCRIPT = '..\..\..'
$PRESERVED_ARTIFACT_FILE = '.gitkeep'
$EXCLUDED_EXACT_PATHS = @('run_config.yaml')
$EXCLUDED_PATH_PREFIXES = @('project-governance/runtime/')
$GENERATED_ARTIFACT_PREFIXES = @('artifacts/runs/', 'artifacts/reports/')

# Run Git and retain repository and command context on failure.
function Invoke-GitCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Repository,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = @(& git -C $Repository @Arguments 2>&1)

    if ($LASTEXITCODE -ne 0) {
        $commandText = $Arguments -join ' '
        $outputText = $output -join [Environment]::NewLine
        throw "git command failed in '$Repository': git $commandText`n$outputText"
    }

    return @($output | ForEach-Object { [string]$_ })
}

# Resolve the source Git worktree root used to enumerate formal files.
function Resolve-SourceRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "source directory does not exist: $Path"
    }

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $topLevel = @(Invoke-GitCommand -Repository $resolved -Arguments @('rev-parse', '--show-toplevel'))[0]
    $topLevel = (Resolve-Path -LiteralPath $topLevel).Path

    if (-not [string]::Equals($resolved, $topLevel, [StringComparison]::OrdinalIgnoreCase)) {
        throw "source must point to the Git worktree root: requested='$resolved', root='$topLevel'"
    }

    return $resolved
}

# Normalize repository-relative paths to forward slashes.
function Convert-ToRepositoryPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalized = $Path.Replace('\', '/').TrimStart('/')

    if (($normalized.Length -eq 0) -or $normalized.StartsWith('../') -or $normalized.Contains('/../')) {
        throw "unsafe repository-relative path: $Path"
    }

    return $normalized
}

# Keep source code and durable documents while excluding local and generated output.
function Test-ShouldCopy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $path = Convert-ToRepositoryPath -Path $RelativePath

    if ($EXCLUDED_EXACT_PATHS -contains $path) {
        return $false
    }

    foreach ($prefix in $EXCLUDED_PATH_PREFIXES) {
        if ($path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            return $false
        }
    }

    foreach ($prefix in $GENERATED_ARTIFACT_PREFIXES) {
        if ($path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            return ([IO.Path]::GetFileName($path) -eq $PRESERVED_ARTIFACT_FILE)
        }
    }

    return $true
}

# Join a repository-relative path without allowing root escape.
function Join-RepositoryPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Repository,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $platformPath = (Convert-ToRepositoryPath -Path $RelativePath).Replace(
        '/',
        [IO.Path]::DirectorySeparatorChar
    )
    $combined = [IO.Path]::GetFullPath((Join-Path $Repository $platformPath))
    $rootWithSeparator = $Repository.TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar

    if (-not $combined.StartsWith($rootWithSeparator, [StringComparison]::OrdinalIgnoreCase)) {
        throw "repository path escaped root: $RelativePath"
    }

    return $combined
}

# Enumerate tracked files and non-ignored new files from the current source worktree.
function Get-SourceWorktreeFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Repository
    )

    # NUL-delimited Git output preserves spaces, Chinese text, quotes and other
    # path content without line-oriented quoting or console-code-page damage.
    $startInfo = New-Object Diagnostics.ProcessStartInfo
    $startInfo.FileName = 'git.exe'
    $startInfo.WorkingDirectory = $Repository
    $startInfo.Arguments = '-c core.quotepath=false ls-files -z --cached --others --exclude-standard'
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true
    $startInfo.StandardOutputEncoding = [Text.Encoding]::UTF8
    $startInfo.StandardErrorEncoding = [Text.Encoding]::UTF8

    $process = New-Object Diagnostics.Process
    $process.StartInfo = $startInfo

    try {
        [void]$process.Start()
        $rawOutput = $process.StandardOutput.ReadToEnd()
        $errorOutput = $process.StandardError.ReadToEnd()
        $process.WaitForExit()

        if ($process.ExitCode -ne 0) {
            throw "git path enumeration failed in '$Repository': $errorOutput"
        }
    }
    finally {
        $process.Dispose()
    }

    $entries = @(
        $rawOutput.Split([char[]]@([char]0), [StringSplitOptions]::RemoveEmptyEntries)
    )

    $files = @()

    foreach ($entry in $entries) {
        if ([string]::IsNullOrEmpty($entry)) {
            continue
        }

        $relativePath = Convert-ToRepositoryPath -Path $entry
        $sourcePath = Join-RepositoryPath -Repository $Repository -RelativePath $relativePath

        if (Test-Path -LiteralPath $sourcePath -PathType Leaf) {
            $files += $relativePath
        }
    }

    return @($files | Sort-Object -Unique)
}

# Use .NET SHA256 so the result does not depend on PowerShell modules.
function Get-FileSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $stream = [IO.File]::OpenRead($Path)
    $algorithm = [Security.Cryptography.SHA256]::Create()

    try {
        $hash = $algorithm.ComputeHash($stream)
        return ([BitConverter]::ToString($hash)).Replace('-', '')
    }
    finally {
        $algorithm.Dispose()
        $stream.Dispose()
    }
}

if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    $SourceRoot = Join-Path $PSScriptRoot $SOURCE_ROOT_FROM_SCRIPT
}

if ([string]::IsNullOrWhiteSpace($Destination)) {
    throw 'destination path must not be empty'
}

$source = Resolve-SourceRoot -Path $SourceRoot
$target = [IO.Path]::GetFullPath($Destination)

if ([string]::Equals($source, $target, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'source and target directories must be different'
}

[void][IO.Directory]::CreateDirectory($target)

$allSourceFiles = Get-SourceWorktreeFiles -Repository $source
$sourceFiles = @($allSourceFiles | Where-Object { Test-ShouldCopy -RelativePath $_ })
$excludedFiles = @($allSourceFiles | Where-Object { -not (Test-ShouldCopy -RelativePath $_) })

if ($sourceFiles.Count -eq 0) {
    throw 'source repository does not contain any files to copy'
}

Write-Host 'ET repository copy plan'
Write-Host "  source:                $source"
Write-Host "  target:                $target"
Write-Host "  files to copy:         $($sourceFiles.Count)"
Write-Host "  source files excluded: $($excludedFiles.Count)"

foreach ($relativePath in $sourceFiles) {
    $sourcePath = Join-RepositoryPath -Repository $source -RelativePath $relativePath
    $targetPath = Join-RepositoryPath -Repository $target -RelativePath $relativePath
    $targetDirectory = [IO.Path]::GetDirectoryName($targetPath)

    [void][IO.Directory]::CreateDirectory($targetDirectory)
    [IO.File]::Copy($sourcePath, $targetPath, $true)
}

foreach ($relativePath in $sourceFiles) {
    $sourcePath = Join-RepositoryPath -Repository $source -RelativePath $relativePath
    $targetPath = Join-RepositoryPath -Repository $target -RelativePath $relativePath

    if ((Get-FileSha256 -Path $sourcePath) -ne (Get-FileSha256 -Path $targetPath)) {
        throw "verification failed; file hash differs: $relativePath"
    }
}

Write-Host 'Copy completed and all selected files passed SHA256 verification.'
