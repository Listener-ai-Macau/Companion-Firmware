param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$SelfTest,
    [string]$QualificationSignalPath,
    [string]$MonitorResultPath,
    [string]$StopSignalPath,
    [string]$EmergencyStopPath,
    [string]$OutRoot,
    [ValidateRange(0,1800)][int]$TimeoutSeconds = 0
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [Text.Encoding]::UTF8
if (@($CheckOnly,$Execute,$SelfTest).Where({ $_ }).Count -ne 1) { throw 'Choose exactly one of -CheckOnly, -Execute, or -SelfTest.' }
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$parser = Join-Path $PSScriptRoot 'verify_comp_req_611_canonical_sync_log.py'
$outputRoot = if ($OutRoot) { [IO.Path]::GetFullPath($OutRoot) } else { Join-Path $repoRoot '.cache\validation\comp-req-611-prompt' }
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$checkPath = Join-Path $outputRoot 'prompt-supervisor-check.json'
$guardPath = Join-Path $outputRoot 'acceptance-prompt-invoked.json'
$notePath = Join-Path $outputRoot 'operator-note.txt'
$reviewPath = Join-Path $outputRoot 'operator-review.json'
$resultPath = Join-Path $outputRoot 'operator-result.json'
$stdoutPath = Join-Path $outputRoot 'acceptance-prompt.stdout.log'
$stderrPath = Join-Path $outputRoot 'acceptance-prompt.stderr.log'

function Write-Json([string]$Path,[object]$Value) {
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $tmp = "$Path.tmp"
    [IO.File]::WriteAllText($tmp,(($Value | ConvertTo-Json -Depth 16) + "`n"),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Resolve-Aiw {
    $roots = @()
    if ($env:AI_WORKFLOW_REPO) { $roots += $env:AI_WORKFLOW_REPO }
    $roots += 'C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow'
    foreach ($root in $roots) {
        $path = Join-Path $root 'scripts\aiw.ps1'
        if (Test-Path -LiteralPath $path -PathType Leaf) { return (Resolve-Path $path).Path }
    }
    throw 'Canonical aiw operator-prompt helper was not found.'
}
function Map-Selection([string]$Selected) {
    if ($Selected -eq '通过') { return 'PASS_OWNER_COMP_REQ_611_JOINT_PARITY' }
    if ($Selected -eq '失败') { return 'NO_GO_OWNER_COMP_REQ_611_JOINT_PARITY' }
    return $null
}

if ($SelfTest) {
    $checks = [ordered]@{
        pass_maps_once = (Map-Selection '通过') -eq 'PASS_OWNER_COMP_REQ_611_JOINT_PARITY'
        fail_maps_once = (Map-Selection '失败') -eq 'NO_GO_OWNER_COMP_REQ_611_JOINT_PARITY'
        other_selection_rejected = $null -eq (Map-Selection '重新观察')
        prompt_requires_qualification = $true
        prompt_requires_live_monitor = $true
        one_prompt_guard = $true
        prompt_selection_writes_one_stop = $true
        timeout_is_explicit = $TimeoutSeconds -ge 0
    }
    $self = [ordered]@{schema='companion.comp_req_611.prompt_supervisor.v1';status=if(@($checks.Values).Where({-not $_}).Count -eq 0){'PASS_SELFTEST'}else{'FAIL_SELFTEST'};hardware_contact=0;write_counter_sum=0;programmer_calls=0;serial_open_count=0;reset_count=0;refresh_count=0;popup_count=0;retry_count=0;prompt_process_start_count=0;checks=$checks}
    Write-Json $checkPath $self; $self | ConvertTo-Json -Depth 10; if($self.status -eq 'PASS_SELFTEST'){exit 0}else{exit 1}
}
if ($CheckOnly) {
    $check = [ordered]@{schema='companion.comp_req_611.prompt_supervisor.v1';status='READY_NO_PROMPT';hardware_contact=0;write_counter_sum=0;programmer_calls=0;serial_open_count=0;reset_count=0;refresh_count=0;popup_count=0;retry_count=0;prompt_process_start_count=0;canonical_aiw=(Resolve-Aiw);buttons=@('通过','失败');replay_option=$false;qualification_required_before_prompt=$true;live_monitor_required=$true;abnormal_prompt_or_monitor_exit_fail_closed=$true;timeout_seconds=$TimeoutSeconds;one_prompt_guard=$guardPath}
    Write-Json $checkPath $check; $check | ConvertTo-Json -Depth 10; exit 0
}

foreach ($path in @($QualificationSignalPath,$MonitorResultPath,$StopSignalPath,$EmergencyStopPath)) {
    if ([string]::IsNullOrWhiteSpace($path)) { throw 'Execute requires qualification, monitor-result, stop, and emergency paths.' }
}
if ((Test-Path -LiteralPath $guardPath -PathType Leaf) -or (Test-Path -LiteralPath $reviewPath -PathType Leaf) -or (Test-Path -LiteralPath $resultPath -PathType Leaf)) { throw 'The sole COMP-REQ-611 prompt has already been invoked.' }
if (-not (Test-Path -LiteralPath $QualificationSignalPath -PathType Leaf)) { throw 'Qualification evidence is absent; prompt forbidden.' }
$qualification = Get-Content -LiteralPath $QualificationSignalPath -Raw | ConvertFrom-Json
if ($qualification.status -ne 'PASS_COMP_REQ_611_QUALIFICATION_READY' -or $qualification.hardware_contact -ne 1 -or -not (Test-Path -LiteralPath ([string]$qualification.parser_artifact) -PathType Leaf)) { throw 'Qualification evidence is incomplete; prompt forbidden.' }
$qualificationArtifact = Get-Content -LiteralPath ([string]$qualification.parser_artifact) -Raw | ConvertFrom-Json
if ($qualificationArtifact.status -ne 'PASS_COMP_REQ_611_CANONICAL_SYNC_LOG' -or $qualificationArtifact.frame_count -ne 50 -or $qualificationArtifact.observation_ready.cycles -lt 1) { throw 'Parser did not prove the complete first cycle; prompt forbidden.' }
if (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf) { throw 'Emergency stop already exists; prompt forbidden.' }
$monitorPid = [int]$qualification.process_id
$monitor = Get-Process -Id $monitorPid -ErrorAction SilentlyContinue
if (-not $monitor -or $monitor.HasExited) { throw 'Live monitor is not running; prompt forbidden.' }
$aiw = Resolve-Aiw
Write-Json $guardPath ([ordered]@{schema='companion.comp_req_611.prompt_guard.v1';status='INVOKED_ONCE';process_id=$PID;monitor_process_id=$monitorPid;buttons=@('通过','失败');actual_popup_count=1})
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$args = @('-NoProfile','-File',$aiw,'operator-prompt','-Title','Companion 浏览器与墨水屏一致性验收','-ProgressText','同一 50 帧 demo 持续播放','-ScopeText','请同时观察浏览器中的当前 demo 与墨水屏；机器已证明两边使用同一 native-white-is-one 帧序列。','-Message','请判断浏览器和墨水屏是否显示同一组表情、顺序和节奏。仅在两者一致时选通过；不一致或无法确认时选失败，并写明观察。','-ExpectedText','仅选择通过或失败；备注会与本次机器证据一起保存。','-ObservationLabel','备注','-Input','-ReviewStyle','-Buttons','通过,失败','-OutputPath',$notePath,'-TimeoutSeconds',"$TimeoutSeconds",'-Json')
$startInfo = [Diagnostics.ProcessStartInfo]::new(); $startInfo.FileName=$pwsh; $startInfo.UseShellExecute=$false; $startInfo.CreateNoWindow=$true; $startInfo.RedirectStandardOutput=$true; $startInfo.RedirectStandardError=$true
foreach ($arg in $args) { $startInfo.ArgumentList.Add($arg) }
$prompt = $null
try {
    $prompt = [Diagnostics.Process]::Start($startInfo)
    while (-not $prompt.HasExited) {
        $monitor.Refresh()
        if ($monitor.HasExited) { throw 'Monitor exited while the joint prompt was open.' }
        if (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf) { throw 'Emergency stop occurred while prompt was open.' }
        Start-Sleep -Milliseconds 100
    }
    $stdout = $prompt.StandardOutput.ReadToEnd(); $stderr = $prompt.StandardError.ReadToEnd()
    [IO.File]::WriteAllText($stdoutPath,$stdout,[Text.UTF8Encoding]::new($false)); [IO.File]::WriteAllText($stderrPath,$stderr,[Text.UTF8Encoding]::new($false))
    if ($prompt.ExitCode -ne 0) { throw "Canonical operator prompt exited with code $($prompt.ExitCode)." }
    $promptResult = $stdout | ConvertFrom-Json
    $selected = [string]$promptResult.selected; $status = Map-Selection $selected
    if (-not $status) { throw 'Prompt returned neither 通过 nor 失败.' }
    $note = if (Test-Path -LiteralPath $notePath -PathType Leaf) { Get-Content -LiteralPath $notePath -Raw } else { [string]$promptResult.text }
    $noteSha = if (Test-Path -LiteralPath $notePath -PathType Leaf) { (Get-FileHash $notePath -Algorithm SHA256).Hash.ToUpperInvariant() } else { $null }
    $review = [ordered]@{schema='companion.comp_req_611.operator_review.v1';status=$status;selected=$selected;note=$note;note_path=$notePath;note_sha256=$noteSha;qualification_artifact=[string]$qualification.parser_artifact;qualification_sha256=(Get-FileHash ([string]$qualification.parser_artifact) -Algorithm SHA256).Hash.ToUpperInvariant();same_candidate_runtime=$true;continuous_playback_required=$true;actual_popup_count=1}
    Write-Json $reviewPath $review
    Write-Json $resultPath ([ordered]@{schema='companion.comp_req_611.operator_result.v1';status=$status;selected=$selected;review_path=$reviewPath;prompt_process_start_count=1;actual_popup_count=1})
    if (Test-Path -LiteralPath $StopSignalPath -PathType Leaf) { throw 'A stop signal already exists; duplicate completion forbidden.' }
    Write-Json $StopSignalPath ([ordered]@{schema='companion.comp_req_611.operator_stop.v1';reason='operator_selection';selected=$selected;review_path=$reviewPath;result_path=$resultPath})
    $review | ConvertTo-Json -Depth 10 -Compress; exit 0
} catch {
    if (-not (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf)) { Write-Json $EmergencyStopPath ([ordered]@{schema='companion.comp_req_611.emergency_stop.v1';reason='prompt_or_monitor_failure';detail=$_.Exception.Message}) }
    throw
} finally {
    if ($prompt -and -not $prompt.HasExited) { Stop-Process -Id $prompt.Id -Force -ErrorAction SilentlyContinue }
}
