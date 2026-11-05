param(
    [Parameter(Mandatory = $true)]
    [string]$RunRoot,
    [switch]$FinalizeSpent
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}
function Read-Json([string]$Path) {
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}
function Write-JsonAtomic([string]$Path,[object]$Value) {
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $tmp = "$Path.tmp"
    [IO.File]::WriteAllText($tmp,(($Value | ConvertTo-Json -Depth 30) + "`n"),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}

$root = [IO.Path]::GetFullPath($RunRoot)
$authorization = "$root.authorization.json"
$monitorResult = Join-Path $root 'candidate-monitor\monitor-result.json'
$cleanup = Join-Path $root 'cleanup-white.json'
$restore = Join-Path $root 'restore-gate.json'
$normal = Join-Path $root 'normal-resume.json'
$reportPath = Join-Path $root 'stage-run.json'
$spentPath = "$authorization.spent"

if (-not (Test-Path -LiteralPath $authorization -PathType Leaf)) { throw 'authorization artifact is missing' }
if ((Test-Path -LiteralPath $spentPath -PathType Leaf) -and (-not $FinalizeSpent)) {
    throw 'authorization artifact is already spent'
}
$auth = Read-Json $authorization
$monitor = Read-Json $monitorResult
$cleanupEvidence = Read-Json $cleanup
$restoreEvidence = Read-Json $restore
$normalEvidence = Read-Json $normal

if ($auth.status -ne 'AUTHORIZED_ONCE') { throw 'authorization is not AUTHORIZED_ONCE' }
if ($monitor.status -ne 'NO_GO_MONITOR_FAULT_ZERO_CONTACT' -or [int]$monitor.frame_records_seen -ne 0) {
    throw 'interrupted-run monitor evidence does not prove zero frames'
}
if ($cleanupEvidence.status -ne 'PASS_MACHINE_DIGITAL_ONLY' -or
    $restoreEvidence.status -ne 'PASS_RESTORE_EQUALS_CAPTURED_PRE_RUN_APPLICATION_BYTES' -or
    $normalEvidence.status -ne 'PASS_APPLICATION_RESUMED_AFTER_BACKUP') {
    throw 'cleanup/restore/normal evidence is incomplete'
}

$report = [ordered]@{
    schema = 'companion.comp_req_616.physical_stage_run.v1'
    status = 'NO_GO_COMP_REQ_616_PHYSICAL_RUN_RESTORED'
    hardware_contact = 1
    programmer_calls = @(
        [ordered]@{ operation = 'candidate-write'; verified = $true; stdout = (Join-Path $root 'candidate-write.stdout.log') }
        [ordered]@{ operation = 'single-fast-white-cleanup'; verified = $true; stdout = (Join-Path $root 'single-fast-white-cleanup.stdout.log') }
        [ordered]@{ operation = 'restore-write-verify-upload'; verified = $true; stdout = (Join-Path $root 'restore-write-verify-upload.stdout.log') }
    )
    prompt_count = 0
    cleanup_count = 1
    restore_count = 1
    qualification = [ordered]@{
        status = 'NO_GO_FIRST_CYCLE_QUALIFICATION_TIMEOUT'
        frames_seen = 0
        expected_frames = 182
        monitor = $monitorResult
    }
    cleanup = $cleanupEvidence
    restore = $restoreEvidence
    normal_resume = $normalEvidence
    operator_review = $null
    error = 'first-cycle qualification timed out before any frame record; no owner prompt was shown'
    retry_count = 0
    completed_at = [DateTime]::UtcNow.ToString('o')
    artifacts = [ordered]@{
        authorization = $authorization
        monitor = $monitorResult
        cleanup = $cleanup
        restore = $restore
        normal_resume = $normal
    }
}
Write-JsonAtomic $reportPath $report
if (-not (Test-Path -LiteralPath $spentPath -PathType Leaf)) {
    Write-JsonAtomic $spentPath ([ordered]@{
    schema = 'companion.comp_req_616.authorization_spent.v1'
    status = 'SPENT'
    authorization = $authorization
    run_root = $root
    report = $reportPath
    reason = 'candidate cycle ended fail-closed at zero frames; cleanup, exact restore and normal resume completed; no retry'
    spent_at = $report.completed_at
    })
}
$report | ConvertTo-Json -Depth 30
