# Resolve bounded records workspaces; legacy runs are never written or adopted.

function Assert-EtRecordsCurrentPath {
    param([string]$CodeRoot, [string]$RunRoot, [switch]$PipelineOnly)
    $records = [System.IO.Path]::GetFullPath((Join-Path $CodeRoot 'artifacts\records'))
    $full = [System.IO.Path]::GetFullPath($RunRoot)
    if (-not $full.StartsWith($records + [System.IO.Path]::DirectorySeparatorChar,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Artifact workspace must stay inside $records"
    }
    $relative = $full.Substring($records.Length + 1).Replace('/', '\')
    $pattern = if ($PipelineOnly) { '^[A-Z0-9][A-Z0-9_.-]*\\_PIPELINE\\current$' } else {
        '^(_DIAGNOSTICS|[A-Z0-9][A-Z0-9_.-]*)\\[_A-Z0-9][A-Z0-9_.-]*\\current$'
    }
    if ($relative -cnotmatch $pattern) { throw 'Artifact workspace must use a fixed records current path.' }
    $cursor = $full
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            if ((Get-Item -LiteralPath $cursor).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Linked Artifact path is forbidden: $cursor"
            }
        }
        $cursor = Split-Path -Parent $cursor
    }
    return $full
}

function Invoke-EtDiagnosticWorkspace {
    param([string]$CodeRoot, [string]$RunRoot, [string]$Operation)
    $python = Join-Path $CodeRoot '.venv\Scripts\python.exe'
    $helper = Join-Path $CodeRoot 'tools\runner\record_workspace_cli.py'
    & $python $helper $Operation --repository $CodeRoot --workspace $RunRoot
    if ($LASTEXITCODE -ne 0) { throw 'Diagnostic current is not reusable; preserve/review/archive it first.' }
}

function Get-EtArtifactRunRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CodeRoot,

        [Parameter(Mandatory = $true)]
        [string]$RunName
    )

    $artifactRoot = [System.IO.Path]::GetFullPath((Join-Path $CodeRoot 'artifacts\records'))
    if ($env:ET_ARTIFACT_RUN_DIR) {
        # Diagnostic wrappers share their current path; PFLASH guards still require Pipeline.
        $runRoot = Assert-EtRecordsCurrentPath -CodeRoot $CodeRoot -RunRoot $env:ET_ARTIFACT_RUN_DIR
        New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
        return $runRoot
    }

    $now = Get-Date
    $safeName = ($RunName.ToUpperInvariant() -replace '[^A-Z0-9_]+', '_').Trim('_')
    if ([string]::IsNullOrWhiteSpace($safeName)) {
        throw 'RunName must contain at least one letter or digit.'
    }
    $runId = [guid]::NewGuid().ToString()
    $runRoot = Assert-EtRecordsCurrentPath -CodeRoot $CodeRoot -RunRoot (Join-Path $artifactRoot "_DIAGNOSTICS\$safeName\current")
    Invoke-EtDiagnosticWorkspace -CodeRoot $CodeRoot -RunRoot $runRoot -Operation prepare
    @{
        schema = 'et-artifact-run/v1'
        run_id = $runId
        run_name = $safeName
        status = 'STANDALONE'
        started_at = $now.ToString('yyyy-MM-dd HH:mm:ss K')
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runRoot 'manifest.json') -Encoding UTF8
    return $runRoot
}

function New-EtArtifactStageDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RunRoot,

        [Parameter(Mandatory = $true)]
        [string]$StageName
    )

    $safeStage = ($StageName.ToLowerInvariant() -replace '[^a-z0-9_]+', '_').Trim('_')
    if ([string]::IsNullOrWhiteSpace($safeStage)) {
        throw 'StageName must contain at least one letter or digit.'
    }
    $stage = Join-Path $RunRoot "stages\$safeStage"
    New-Item -ItemType Directory -Force -Path $stage | Out-Null
    return $stage
}

# Fail closed when a destructive low-level stage is invoked outside the current
# Pipeline run or before one of its required predecessor stages has passed.
function Assert-EtPipelineStagePassed {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CodeRoot,

        [Parameter(Mandatory = $true)]
        [string]$StageName
    )

    if ([string]::IsNullOrWhiteSpace($env:ET_ARTIFACT_RUN_DIR)) {
        throw ("Pipeline run context is missing. Execute this hardware flow through " +
            "run_test.bat or tools/runner/run_pipeline.py.")
    }

    $runRoot = Assert-EtRecordsCurrentPath -CodeRoot $CodeRoot -RunRoot $env:ET_ARTIFACT_RUN_DIR -PipelineOnly
    if (-not (Test-Path -LiteralPath $runRoot -PathType Container)) {
        throw "Pipeline run directory does not exist: $runRoot"
    }

    $safeStage = ($StageName.ToLowerInvariant() -replace '[^a-z0-9_]+', '_').Trim('_')
    if ([string]::IsNullOrWhiteSpace($safeStage)) {
        throw 'StageName must contain at least one letter or digit.'
    }
    $manifestPath = Join-Path $runRoot "stages\$safeStage\manifest.txt"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Required Pipeline stage has no completion evidence: $safeStage"
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw
    if ($manifest -notmatch '(?m)^result=PASS\s*$') {
        throw "Required Pipeline stage did not pass: $safeStage"
    }

    return $runRoot
}

function Complete-EtArtifactRun {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RunRoot,

        [Parameter(Mandatory = $true)]
        [bool]$Succeeded,

        [int]$ExitCode = 0
    )

    $manifestPath = Join-Path $RunRoot 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        return
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $manifest.status = if ($Succeeded) { 'PASS' } else { 'FAIL' }
    $manifest | Add-Member -NotePropertyName exit_code -NotePropertyValue $ExitCode -Force
    $manifest | Add-Member -NotePropertyName finished_at `
        -NotePropertyValue (Get-Date -Format 'yyyy-MM-dd HH:mm:ss K') -Force
    $temporary = "$manifestPath.tmp"
    $manifest | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $manifestPath -Force
    if ([IO.Directory]::GetParent($RunRoot).Parent.Name -eq '_DIAGNOSTICS' -and $Succeeded) {
        $codeRoot = [IO.Directory]::GetParent($RunRoot).Parent.Parent.Parent.Parent.FullName
        Invoke-EtDiagnosticWorkspace -CodeRoot $codeRoot -RunRoot $RunRoot -Operation complete
    }
}
