param(
    [string]$StandingAuthorizationPath = '',
    [string]$OutputPath = '',
    [string]$OutRoot = '',
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($StandingAuthorizationPath)) {
    $StandingAuthorizationPath = Join-Path $repoRoot 'docs\validation\companion-comp-req-616-standing-authorization-20260726.json'
}
$machineReadyPath = Join-Path $repoRoot 'docs\validation\comp-req-616-upper-sync\MACHINE_READY.json'
$assetManifestPath = Join-Path $repoRoot '.cache\validation\comp-req-616-upper-sync\generated\canonical-input-evidence.json'
$runScript = Join-Path $PSScriptRoot 'run_comp_req_616_canonical_sync.ps1'
$monitorScript = Join-Path $PSScriptRoot 'monitor_comp_req_616_canonical_sync.ps1'
$supervisorScript = Join-Path $PSScriptRoot 'supervise_comp_req_616_canonical_sync_prompt.ps1'
$parserScript = Join-Path $PSScriptRoot 'verify_comp_req_616_canonical_sync_log.py'
$cleanupHex = Join-Path $repoRoot 'cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_diagnostic_white\Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex'
$expectedBaselineSha = '223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5265055A6C84D5BD6FE304CD7C'
$expected = [ordered]@{
    page = 'ECCC8D27A31209150B9EEBF8AB25CEB08708B32BBA00541E033C8378E5B77E73'
    evidence = '12E924C86A4A6787D2502ABE1F6D1DF278200FF9AC0E330CC002088144FEA76D'
    plan = '2A0DE4F6296BEAA18606E0AE40AB41F008D0DBE1CB9E668067A49DDB6D95046F'
    payload = '087654306CFC0ECA07BEE9F270DAF72C0DB269E3CF39C6D4D6098BB96EA137DC'
    frame_count = 182
    payload_bytes = 910000
    machine_status = 'READY_MACHINE_O2'
}

function Get-Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}
function Read-Json([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required JSON is missing: $Path" }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}
function Write-JsonAtomic([string]$Path,[object]$Value) {
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $tmp = "$Path.tmp"
    [IO.File]::WriteAllText($tmp,(($Value | ConvertTo-Json -Depth 20) + "`n"),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Fail([string]$Status,[string]$Reason) {
    $result = [ordered]@{schema='companion.comp_req_616.standing_authorization_materializer.v1';status=$Status;reason=$Reason;hardware_contact=0;flash=$false;reset=$false}
    $result | ConvertTo-Json -Depth 20
    exit 1
}

try {
    $standing = Read-Json $StandingAuthorizationPath
    if ($standing.schema -ne 'companion.comp_req_616.standing_authorization.v1' -or
        $standing.status -ne 'RECORDED_BUT_NOT_EXECUTABLE' -or
        $standing.requirement -ne 'COMP-REQ-616/617') {
        Fail 'NO_GO_STANDING_AUTH_INVALID' 'standing authorization schema/status/requirement mismatch'
    }
    $scope = $standing.scope
    foreach ($pair in @(
        @('page_sha256',$expected.page), @('evidence_sha256',$expected.evidence),
        @('frame_plan_sha256',$expected.plan), @('payload_sha256',$expected.payload),
        @('frame_count',$expected.frame_count), @('payload_bytes',$expected.payload_bytes))) {
        if ([string]$scope.($pair[0]) -ne [string]$pair[1]) {
            Fail 'NO_GO_STANDING_AUTH_SCOPE_MISMATCH' "scope mismatch: $($pair[0])"
        }
    }
    $machine = Read-Json $machineReadyPath
    if ([string]$machine.status -ne $expected.machine_status) {
        Fail 'NO_GO_STANDING_AUTH_MACHINE_NOT_READY' "machine status is $($machine.status)"
    }
    $asset = Read-Json $assetManifestPath
    if ([string]$asset.status -ne 'READY' -or
        [string]$asset.page_sha256 -ne $expected.page -or
        [string]$asset.expected_evidence_sha256 -ne $expected.evidence -or
        [string]$asset.observed_evidence_sha256 -ne $expected.evidence -or
        $asset.all_semantic_checks_true -ne $true -or
        [string]$asset.canonical_plan_sha256 -ne $expected.plan -or
        [string]$asset.canonical_payload_sha256 -ne $expected.payload -or
        [int]$asset.frame_count -ne $expected.frame_count -or
        [int]$asset.payload_bytes -ne $expected.payload_bytes -or
        $asset.header_roundtrip.matches_native_payload -ne $true) {
        Fail 'NO_GO_STANDING_AUTH_ASSET_NOT_READY' 'asset manifest is not exact READY/native-payload identity'
    }
    foreach ($counter in @('hardware_contact','serial_contact','programmer_contact')) {
        if ([int]$machine.$counter -ne 0) { Fail 'NO_GO_STANDING_AUTH_SIDE_EFFECT' "machine counter $counter is nonzero" }
    }
    if ($machine.flash -ne $false -or $machine.reset -ne $false -or $machine.operator_prompt -ne $false) {
        Fail 'NO_GO_STANDING_AUTH_SIDE_EFFECT' 'machine safety flags are not zero'
    }
    if ($machine.static.all_true -ne $true -or
        $machine.default_off_control_build.behavioral_identity -ne $true -or
        $machine.o2_build.object_proof.all_required -ne $true -or
        $machine.o2_build.disassembly_proof.all_required -ne $true -or
        $machine.o2_build.disassembly_proof.adapter_proof.all_required -ne $true -or
        $machine.o2_build.disassembly_proof.baseline_proof.all_required -ne $true) {
        Fail 'NO_GO_STANDING_AUTH_MACHINE_CHECKS' 'static/build/disassembly proof is incomplete'
    }
    $resolvedOutRoot = [IO.Path]::GetFullPath($OutRoot)
    if ([string]::IsNullOrWhiteSpace($OutRoot) -or (Test-Path -LiteralPath $resolvedOutRoot)) {
        Fail 'NO_GO_STANDING_AUTH_OUTPUT_INVALID' 'OutRoot is empty or already exists'
    }
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        $OutputPath = "$resolvedOutRoot.authorization.json"
    }
    $resolvedOutput = [IO.Path]::GetFullPath($OutputPath)
    if (Test-Path -LiteralPath $resolvedOutput) { Fail 'NO_GO_STANDING_AUTH_REUSE' 'authorization output already exists' }
    if (-not (Test-Path -LiteralPath $cleanupHex -PathType Leaf)) { Fail 'NO_GO_STANDING_AUTH_CLEANUP_MISSING' 'cleanup HEX is missing' }
    $candidateHex = Join-Path $repoRoot 'cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_616_canonical_sync\Companion_Nucleo_WB55RG_Bringup.hex'
    if (-not (Test-Path -LiteralPath $candidateHex -PathType Leaf)) { Fail 'NO_GO_STANDING_AUTH_CANDIDATE_MISSING' 'candidate HEX is missing' }
    if ([string]$machine.o2_build.artifacts.hex -ne (Get-Hash $candidateHex)) { Fail 'NO_GO_STANDING_AUTH_CANDIDATE_DRIFT' 'candidate HEX hash drift' }
    $result = [ordered]@{
        schema='companion.comp_req_616.main_review_authorization.v1'
        status='AUTHORIZED_ONCE'
        requirement_id='COMP-REQ-616'
        execute=$true
        output_root=$resolvedOutRoot
        standing_authorization_path=[IO.Path]::GetFullPath($StandingAuthorizationPath)
        standing_authorization_sha256=Get-Hash $StandingAuthorizationPath
        machine_ready_sha256=Get-Hash $machineReadyPath
        candidate_hex_sha256=[string]$machine.o2_build.artifacts.hex
        cleanup_hex_sha256=Get-Hash $cleanupHex
        launcher_sha256=Get-Hash $runScript
        monitor_sha256=Get-Hash $monitorScript
        supervisor_sha256=Get-Hash $supervisorScript
        log_parser_sha256=Get-Hash $parserScript
        backup_sha256=$expectedBaselineSha
        attempt_limit=1
        automatic_retries=0
        hardware_scope='WB55/SSD1681 exact COMP-REQ-616 182-frame candidate only'
        evidence_sha256=[string]$asset.observed_evidence_sha256
        expected_evidence_sha256=$expected.evidence
        evidence_sha256_informational=$false
    }
    if ($CheckOnly) {
        $result.status = 'READY_TO_MATERIALIZE_AUTHORIZED_ONCE'
        $result.execute = $false
        $result.hardware_contact = 0
        $result | ConvertTo-Json -Depth 20
        exit 0
    }
    Write-JsonAtomic $resolvedOutput $result
    $result | ConvertTo-Json -Depth 20
    exit 0
} catch {
    Fail 'NO_GO_STANDING_AUTH_VALIDATION_ERROR' $_.Exception.Message
}
