[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Build', 'Deploy')]
    [string]$Action,

    [string]$Keil = '',
    [string]$RtePath = '',
    [string]$JLink = '',
    [string]$JLinkSerial = '',

    # Existing SPINLOCK deployment remains the default; other peers use reviewed manifests.
    [string]$PeerManifest = 'firmware\chips\et6801\core1_peer\deploy\et6801_fpga_itcm.json',

    [switch]$ConfirmPFlashProgram,
    [switch]$ConfirmRunControl,
    [switch]$ConfirmPeerDeploy
)

# ET6801 formal dual-core orchestration.
# Core0 remains the normal ET-Frame firmware in PFLASH. Core1 is the reviewed
# peer image in ITCM. The manifest selects the peer, not the Case or public Pipeline.

$ErrorActionPreference = 'Stop'
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $codeRoot 'tools\runner\artifact_paths.ps1')

$formalBuild = Join-Path $codeRoot 'tools\firmware\build_et6801_test_firmware.ps1'
$formalDeploy = Join-Path $codeRoot 'tools\firmware\flash_and_run_et6801_firmware.ps1'
$dualCoreTool = Join-Path $codeRoot 'tools\firmware\deploy_dualcore_firmware.ps1'

# Pipeline resolves file arguments to absolute paths; the manifest tool deliberately
# accepts repository-relative paths only. Normalize once without relaxing that boundary.
if ([System.IO.Path]::IsPathRooted($PeerManifest)) {
    $resolvedManifest = [System.IO.Path]::GetFullPath($PeerManifest)
    $repositoryPrefix = $codeRoot + [System.IO.Path]::DirectorySeparatorChar

    if (-not $resolvedManifest.StartsWith($repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Core1 peer manifest must stay inside the repository.'
    }

    $PeerManifest = $resolvedManifest.Substring($repositoryPrefix.Length)
}

$syscCpu1BootAddress = [uint32]0x404000B8
$syscCriticalUnlockAddress = [uint32]0x404000BC
$syscCpuWaitAddress = [uint32]0x40400154
$syscCpuControlAddress = [uint32]0x40400158
$crgSoftwareReset0Address = [uint32]0x4040C03C
$core1ResetMask = [uint32]0x02000000
$core1WaitMask = [uint32]0x00000002
$core1ResetModeMask = [uint32]0x00000002
$syscCriticalUnlockValue = [uint32]0x12345678
$syscCriticalLockValue = [uint32]0x00123456
$peerMailboxAddress = [uint32]0x20440000
$peerMailboxMagic = [uint32]0x45544331
$peerMailboxReady = [uint32]1
$peerExpectedCoreIndex = [uint32]2

function Get-PeerProfile {
    $manifestPath = $PeerManifest

    if (-not [System.IO.Path]::IsPathRooted($manifestPath)) {
        $manifestPath = Join-Path $codeRoot $manifestPath
    }

    $profile = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $core1 = $profile.cores | Where-Object id -eq 'core1'

    if (($profile.schema -ne 'et-dualcore-deploy/v1') -or ($null -eq $core1)) {
        throw "Invalid ET6801 Core1 peer manifest: $manifestPath"
    }

    $binary = Join-Path $codeRoot ([string]$core1.output_bin)
    $script = Join-Path $codeRoot ([string]$core1.jlink_script)

    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
        throw "Core1 peer image not found: $binary"
    }

    if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
        throw "Core1 J-Link AP-selection script not found: $script"
    }

    return [ordered]@{
        profile = $profile
        core = $core1
        binary = (Resolve-Path -LiteralPath $binary).Path
        script = (Resolve-Path -LiteralPath $script).Path
    }
}

function Invoke-JLinkCommand {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Peer,

        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string[]]$Commands,

        [Parameter(Mandatory = $true)]
        [string]$ArtifactDirectory
    )

    $commandFile = Join-Path $ArtifactDirectory "$Name.jlink"
    $stdout = Join-Path $ArtifactDirectory "$Name.stdout.log"
    $stderr = Join-Path $ArtifactDirectory "$Name.stderr.log"
    (@('exec DisableAutoUpdateFW') + $Commands + @('exit')) |
        Set-Content -LiteralPath $commandFile -Encoding ASCII

    $arguments = @(
        '-NoGui', '1',
        '-Device', [string]$Peer.profile.probe.device,
        '-If', [string]$Peer.profile.probe.interface,
        '-Speed', [string]$Peer.profile.probe.speed_khz,
        '-AutoConnect', '1',
        '-JLinkScriptFile', [string]$Peer.script
    )

    if (-not [string]::IsNullOrWhiteSpace([string]$Peer.profile.probe.jtag_conf)) {
        $arguments += @('-JTAGConf', [string]$Peer.profile.probe.jtag_conf)
    }

    if (-not [string]::IsNullOrWhiteSpace($JLinkSerial)) {
        $arguments += @('-SelectEmuBySN', $JLinkSerial)
    }

    $arguments += @('-CommanderScript', $commandFile)
    $process = Start-Process -FilePath $JLink `
        -ArgumentList $arguments `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    $text = Get-Content -LiteralPath $stdout -Raw
    $checkedText = $text -replace '(?im)^.*CPU could not be halted.*$', ''

    if (($process.ExitCode -ne 0) -or
        ($checkedText -match 'Cannot connect|FAILED:|Could not connect|Error while programming|Failed to download|Failed to verify|Verification failed|Script file read error')) {
        throw "J-Link $Name failed. Log: $stdout"
    }

    if ($text -notmatch 'Cortex-M7 identified') {
        throw "J-Link did not identify Cortex-M7 during $Name. Log: $stdout"
    }

    return [ordered]@{
        text = $text
        log = $stdout
    }
}

function Get-JLinkWord {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text,

        [Parameter(Mandatory = $true)]
        [uint32]$Address
    )

    $match = [regex]::Match(
        $Text,
        ('(?im)^{0:X8}\s*=\s*([0-9A-Fa-f]{{8}})' -f $Address)
    )

    if ($match.Success) {
        return [Convert]::ToUInt32($match.Groups[1].Value, 16)
    }

    # J-Link prints a multiword mem32 read on one line. Resolve the requested
    # word from the line base instead of requiring one address label per word.
    $lines = [regex]::Matches(
        $Text,
        '(?im)^([0-9A-Fa-f]{8})\s*=\s*((?:[0-9A-Fa-f]{8}\s+)+)'
    )

    foreach ($line in $lines) {
        $base = [Convert]::ToUInt32($line.Groups[1].Value, 16)
        $words = @($line.Groups[2].Value.Trim() -split '\s+')
        $limit = [uint64]$base + ([uint64]$words.Count * 4u)

        if (([uint64]$Address -ge [uint64]$base) -and
            ([uint64]$Address -lt $limit) -and
            ((($Address - $base) % 4u) -eq 0u)) {
            $index = [int](($Address - $base) / 4u)

            return [Convert]::ToUInt32($words[$index], 16)
        }
    }

    throw ('J-Link readback does not contain address 0x{0:X8}.' -f $Address)
}

function Invoke-PeerDeploy {
    if (-not $ConfirmPeerDeploy) {
        throw 'Core1 peer deployment requires -ConfirmPeerDeploy.'
    }

    if (-not (Test-Path -LiteralPath $JLink -PathType Leaf)) {
        throw "J-Link Commander not found: $JLink"
    }

    if (Get-Process JLink -ErrorAction SilentlyContinue) {
        throw 'J-Link Commander is already running.'
    }

    $peer = Get-PeerProfile
    $runRoot = Get-EtArtifactRunRoot -CodeRoot $codeRoot -RunName 'et6801_formal_dualcore_deploy'
    $stage = New-EtArtifactStageDirectory -RunRoot $runRoot -StageName 'core1_peer_deploy'

    # AP1 owns SYSC/CRG. Hold Core1 before AP2 writes ITCM and clear stale mailbox evidence.
    $core0Script = Join-Path $codeRoot 'firmware\chips\et6801\core1_peer\debug\core0_select.JLinkScript'
    $core0Peer = [ordered]@{
        profile = $peer.profile
        script = $core0Script
    }
    $snapshot = Invoke-JLinkCommand -Peer $core0Peer -Name 'core1_hold_snapshot' -ArtifactDirectory $stage -Commands @(
        ('mem32 0x{0:X8}, 1' -f $syscCpuWaitAddress),
        ('mem32 0x{0:X8}, 1' -f $syscCpuControlAddress),
        ('mem32 0x{0:X8}, 1' -f $crgSoftwareReset0Address)
    )
    $cpuWait = Get-JLinkWord -Text $snapshot.text -Address $syscCpuWaitAddress
    $cpuControl = Get-JLinkWord -Text $snapshot.text -Address $syscCpuControlAddress
    $softwareReset0 = Get-JLinkWord -Text $snapshot.text -Address $crgSoftwareReset0Address
    $heldCpuWait = [uint32]($cpuWait -bor $core1WaitMask)
    $resetModeCpuControl = [uint32]($cpuControl -bor $core1ResetModeMask)
    $assertedSoftwareReset0 = [uint32]($softwareReset0 -band ([uint32](-bnot $core1ResetMask)))

    [void](Invoke-JLinkCommand -Peer $core0Peer -Name 'core1_hold' -ArtifactDirectory $stage -Commands @(
        ('w4 0x{0:X8}, 0x{1:X8}' -f $syscCriticalUnlockAddress, $syscCriticalUnlockValue),
        ('w4 0x{0:X8}, 0x{1:X8}' -f $syscCpuWaitAddress, $heldCpuWait),
        ('w4 0x{0:X8}, 0x{1:X8}' -f $syscCpuControlAddress, $resetModeCpuControl),
        ('w4 0x{0:X8}, 0x{1:X8}' -f $crgSoftwareReset0Address, $assertedSoftwareReset0),
        ('w4 0x{0:X8}, 0x00000000' -f $peerMailboxAddress),
        ('w4 0x{0:X8}, 0x00000000' -f ($peerMailboxAddress + 4)),
        ('w4 0x{0:X8}, 0x00000000' -f ($peerMailboxAddress + 8)),
        ('w4 0x{0:X8}, 0x00000000' -f ($peerMailboxAddress + 12)),
        ('w4 0x{0:X8}, 0x{1:X8}' -f $syscCriticalUnlockAddress, $syscCriticalLockValue)
    ))

    # AP2 exposes Core1 ITCM at address zero. Load and verify while reset remains asserted.
    [void](Invoke-JLinkCommand -Peer $peer -Name 'core1_load_verify' -ArtifactDirectory $stage -Commands @(
        ('loadbin "{0}", 0x00000000' -f $peer.binary),
        ('verifybin "{0}", 0x00000000' -f $peer.binary),
        'mem32 0x00000000, 2'
    ))

    # AP1 publishes the Core1 vector base, releases reset and removes the CPU_WAIT gate.
    $releasedSoftwareReset0 = [uint32]($softwareReset0 -bor $core1ResetMask)
    $releasedCpuWait = [uint32]($cpuWait -band ([uint32](-bnot $core1WaitMask)))
    [void](Invoke-JLinkCommand -Peer $core0Peer -Name 'core1_release' -ArtifactDirectory $stage -Commands @(
        ('w4 0x{0:X8}, 0x{1:X8}' -f $syscCriticalUnlockAddress, $syscCriticalUnlockValue),
        ('w4 0x{0:X8}, 0x00000000' -f $syscCpu1BootAddress),
        ('w4 0x{0:X8}, 0x{1:X8}' -f $crgSoftwareReset0Address, $releasedSoftwareReset0),
        ('w4 0x{0:X8}, 0x{1:X8}' -f $syscCpuWaitAddress, $releasedCpuWait),
        ('w4 0x{0:X8}, 0x{1:X8}' -f $syscCriticalUnlockAddress, $syscCriticalLockValue)
    ))

    Start-Sleep -Milliseconds 200
    $mailbox = Invoke-JLinkCommand -Peer $core0Peer -Name 'core1_mailbox_verify' -ArtifactDirectory $stage -Commands @(
        ('mem32 0x{0:X8}, 4' -f $peerMailboxAddress)
    )
    $magic = Get-JLinkWord -Text $mailbox.text -Address $peerMailboxAddress
    $state = Get-JLinkWord -Text $mailbox.text -Address ([uint32]($peerMailboxAddress + 4))
    $coreIndex = Get-JLinkWord -Text $mailbox.text -Address ([uint32]($peerMailboxAddress + 8))
    $heartbeat = Get-JLinkWord -Text $mailbox.text -Address ([uint32]($peerMailboxAddress + 12))

    if (($magic -ne $peerMailboxMagic) -or
        ($state -ne $peerMailboxReady) -or
        ($coreIndex -ne $peerExpectedCoreIndex) -or
        ($heartbeat -eq 0)) {
        throw ('Core1 peer mailbox verification failed: magic=0x{0:X8}, state={1}, core={2}, heartbeat={3}. Log: {4}' -f `
            $magic, $state, $coreIndex, $heartbeat, $mailbox.log)
    }

    [ordered]@{
        schema = 'et-formal-dualcore-deploy-result/v1'
        result = 'PASS'
        core0 = 'formal-et-frame-pflash'
        core1 = [string]$peer.core.target
        peer_manifest = $PeerManifest
        peer_image_sha256 = (Get-FileHash -LiteralPath $peer.binary -Algorithm SHA256).Hash
        mailbox = [ordered]@{
            magic = ('0x{0:X8}' -f $magic)
            state = $state
            core_index = $coreIndex
            heartbeat = $heartbeat
        }
    } | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath (Join-Path $stage 'manifest.json') -Encoding UTF8

    Write-Output "ET6801_FORMAL_DUALCORE_DEPLOY_PASS|artifact=$stage"
}

if ($Action -eq 'Build') {
    & $formalBuild -Target SILICON -Keil $Keil -RtePath $RtePath
    & $dualCoreTool -Manifest $peerManifest -Action BuildPeer -Keil $Keil -RtePath $RtePath
    Write-Output 'ET6801_FORMAL_DUALCORE_BUILD_PASS'

    exit 0
}

if ((-not $ConfirmPFlashProgram) -or (-not $ConfirmRunControl)) {
    throw 'Formal Core0 deployment requires -ConfirmPFlashProgram and -ConfirmRunControl.'
}

& $formalDeploy `
    -Project (Join-Path $codeRoot 'firmware\build\et6801\ET6801_Automated_Test.uvprojx') `
    -Target ET6801_SILICON_FLASH `
    -Keil $Keil `
    -RtePath $RtePath `
    -JLink $JLink `
    -JLinkSerial $JLinkSerial `
    -ConfirmPFlashProgram `
    -ConfirmRunControl
Invoke-PeerDeploy
