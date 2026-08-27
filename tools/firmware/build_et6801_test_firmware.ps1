[CmdletBinding()]
param(
    [ValidateSet('FPGA', 'SILICON')]
    [string]$Target = 'FPGA',
    [string]$Keil = 'C:\Keil_v5\UV4\UV4.exe',
    [string]$RtePath = ''
)

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRoot = (Resolve-Path (Join-Path $codeRoot '..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')
$manifest = Join-Path $codeRoot 'firmware\chips\et6801\project.yaml'
$generator = Join-Path $codeRoot 'tools\firmware\generate_keil_project.py'
$project = Join-Path $codeRoot 'firmware\build\et6801\ET6801_Automated_Test.uvprojx'
foreach ($required in @($Keil, $manifest, $generator)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required path not found: $required"
    }
}

if (Get-Process UV4 -ErrorAction SilentlyContinue) {
    throw 'Keil UV4 is already running. Close it before deterministic CLI build.'
}

$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}
& $python $generator --manifest $manifest
if ($LASTEXITCODE -ne 0) {
    throw 'Keil project generation failed.'
}
$generationRecordPath = [System.IO.Path]::ChangeExtension(
    $project,
    '.generation.json'
)
if (-not (Test-Path -LiteralPath $generationRecordPath -PathType Leaf)) {
    throw "Keil project generation record is missing: $generationRecordPath"
}
$generationRecord = Get-Content -LiteralPath $generationRecordPath -Raw |
    ConvertFrom-Json
$generatedProjectHash = (Get-FileHash -LiteralPath $project -Algorithm SHA256).Hash
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $generatedProjectHash,
        [string]$generationRecord.sha256
    )) {
    throw 'Generated Keil project does not match its generation record.'
}

$targetName = if ($Target -eq 'FPGA') {
    'ET6801_FPGA_ITCM'
} else {
    'ET6801_SILICON_FLASH'
}
$outputDirectory = if ($Target -eq 'FPGA') {
    'Objects\FPGA_ITCM'
} else {
    'Objects\SILICON_FLASH'
}
$outputName = if ($Target -eq 'FPGA') {
    'et6801_test_fpga'
} else {
    'et6801_test_silicon'
}

$runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName "firmware_$($Target.ToLowerInvariant())_build"
$artifactDirectory = New-EtArtifactStageDirectory `
    -RunRoot $runRoot `
    -StageName "build_firmware_$($Target.ToLowerInvariant())"
$projectDirectory = Split-Path -Parent $project
$localLogName = "keil_$($Target.ToLowerInvariant()).log"
$localLog = Join-Path $projectDirectory $localLogName
Remove-Item -LiteralPath $localLog -Force -ErrorAction SilentlyContinue

if (-not [string]::IsNullOrWhiteSpace($RtePath)) {
    if (-not (Test-Path -LiteralPath $RtePath -PathType Container)) {
        throw "Arm Pack root not found: $RtePath"
    }
    $env:RTEPATH = (Resolve-Path -LiteralPath $RtePath).Path
}
$process = Start-Process -FilePath $Keil `
    -ArgumentList @(
        '-r',
        (Split-Path -Leaf $project),
        '-t',
        $targetName,
        '-sg',
        '-o',
        $localLogName
    ) `
    -WorkingDirectory $projectDirectory `
    -WindowStyle Hidden `
    -Wait `
    -PassThru

if (-not (Test-Path -LiteralPath $localLog)) {
    throw "Keil did not create build log: $localLog"
}
$artifactLog = Join-Path $artifactDirectory $localLogName
Copy-Item -LiteralPath $localLog -Destination $artifactLog -Force
$logText = Get-Content -LiteralPath $artifactLog -Raw
if (($process.ExitCode -gt 1) -or ($logText -notmatch '- 0 Error\(s\)')) {
    throw "Keil build failed. Log: $artifactLog"
}
$projectHashAfterBuild = (Get-FileHash -LiteralPath $project -Algorithm SHA256).Hash
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $projectHashAfterBuild,
        [string]$generationRecord.sha256
    )) {
    throw ("Keil changed the generated project during the build. " +
        "Regenerate it before Flash or another build. Log: $artifactLog")
}

$objectRoot = Join-Path $projectDirectory $outputDirectory
$axf = Join-Path $objectRoot "$outputName.axf"
$hex = Join-Path $objectRoot "$outputName.hex"
foreach ($required in @($axf, $hex)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Expected build output not found: $required"
    }
}

$record = [ordered]@{
    schemaVersion = 1
    time = Get-Date -Format 'yyyy-MM-dd HH:mm:ss K'
    result = 'PASS'
    chip = 'et6801'
    target = $targetName
    project = $project
    projectSha256 = $projectHashAfterBuild
    generationRecord = $generationRecordPath
    firmwareSourceRoot = (Resolve-Path (
        Join-Path $codeRoot 'firmware'
    )).Path
    template = [string]$generationRecord.template
    keilExitCode = $process.ExitCode
    log = $artifactLog
    outputs = @(
        [ordered]@{
            path = $axf
            sha256 = (Get-FileHash $axf -Algorithm SHA256).Hash
        },
        [ordered]@{
            path = $hex
            sha256 = (Get-FileHash $hex -Algorithm SHA256).Hash
        }
    )
}
$record | ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath (Join-Path $artifactDirectory 'manifest.json') -Encoding UTF8

Write-Output "ET6801_TEST_FIRMWARE_BUILD_PASS|target=$targetName|artifact=$artifactDirectory"
