# Resolve the repository-owned artifact run and stage directories for PowerShell tools.

function Get-EtArtifactRunRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CodeRoot,

        [Parameter(Mandatory = $true)]
        [string]$RunName
    )

    $artifactRoot = [System.IO.Path]::GetFullPath((Join-Path $CodeRoot 'artifacts\runs'))
    if ($env:ET_ARTIFACT_RUN_DIR) {
        $runRoot = [System.IO.Path]::GetFullPath($env:ET_ARTIFACT_RUN_DIR)
        if (-not $runRoot.StartsWith($artifactRoot + [System.IO.Path]::DirectorySeparatorChar,
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "ET_ARTIFACT_RUN_DIR must stay inside $artifactRoot"
        }
        New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
        return $runRoot
    }

    $now = Get-Date
    $safeName = ($RunName.ToLowerInvariant() -replace '[^a-z0-9_]+', '_').Trim('_')
    if ([string]::IsNullOrWhiteSpace($safeName)) {
        throw 'RunName must contain at least one letter or digit.'
    }
    $runId = '{0}_{1}' -f $now.ToString('yyyyMMdd_HHmmss_ffffff'), $safeName
    $runRoot = Join-Path $artifactRoot $runId
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
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

    $artifactRoot = [System.IO.Path]::GetFullPath((Join-Path $CodeRoot 'artifacts\runs'))
    $runRoot = [System.IO.Path]::GetFullPath($env:ET_ARTIFACT_RUN_DIR)
    if (-not $runRoot.StartsWith($artifactRoot + [System.IO.Path]::DirectorySeparatorChar,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "ET_ARTIFACT_RUN_DIR must stay inside $artifactRoot"
    }
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
}
