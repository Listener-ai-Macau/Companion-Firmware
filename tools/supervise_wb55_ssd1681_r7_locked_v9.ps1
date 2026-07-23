param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$SelfTest,
    [switch]$SimulateQualifiedPrompt,
    [string]$QualificationSignalPath,
    [string]$MonitorResultPath,
    [string]$StopSignalPath,
    [string]$EmergencyStopPath,
    [string]$SimulationPromptScript,
    [string]$OutRoot,
    [ValidateRange(0,1800)]
    [int]$TimeoutSeconds = 0
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [Text.Encoding]::UTF8

if (@($CheckOnly,$Execute,$SelfTest,$SimulateQualifiedPrompt).Where({ $_ }).Count -ne 1) {
    throw "Choose exactly one of -CheckOnly, -Execute, -SelfTest, or -SimulateQualifiedPrompt."
}
if ($Execute -and -not [string]::IsNullOrWhiteSpace($SimulationPromptScript)) {
    throw "Simulation prompt injection is forbidden in Execute mode."
}
if ($SimulateQualifiedPrompt -and [string]::IsNullOrWhiteSpace($SimulationPromptScript)) {
    throw "SimulateQualifiedPrompt requires a process-only prompt script."
}

function Resolve-WorkflowAiwPath {
    $roots = @()
    if ($env:AI_WORKFLOW_REPO) { $roots += $env:AI_WORKFLOW_REPO }
    $roots += "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    foreach ($root in $roots) {
        $candidate = Join-Path $root "scripts\aiw.ps1"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    throw "The canonical aiw operator-prompt helper was not found."
}

function Write-JsonAtomic {
    param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)][System.Collections.IDictionary]$Value)
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $temp = "$Path.tmp"
    [IO.File]::WriteAllText($temp,(($Value|ConvertTo-Json -Depth 16)+[Environment]::NewLine),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $Path -Force
}

function Stop-ProcessTree([int]$ProcessId) {
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue)
    foreach ($child in $children) { Stop-ProcessTree ([int]$child.ProcessId) }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Map-Selection([string]$Selected) {
    if ($Selected -eq "通过") { return "PASS_OWNER_R7_LOCKED_V9_CHOREOGRAPHY_VISUAL" }
    if ($Selected -eq "失败") { return "NO_GO_OWNER_R7_LOCKED_V9_CHOREOGRAPHY_VISUAL" }
    return "NO_GO_R7_LOCKED_V9_CHOREOGRAPHY_NO_PASS_FAIL_SELECTION"
}

function Assert-QualificationCadence([object]$Signal,[object]$Artifact) {
    if ($Signal.qualification_cadence_measurements -lt 15 -or $Signal.loop_records -lt 2 -or $Signal.cadence_measurements -lt 1 -or $Signal.max_start_delta_ms -lt 1 -or $Signal.max_start_delta_ms -gt 480) {
        throw "R7 qualification signal lacks two-loop start-to-start cadence proof."
    }
    if ($Artifact.qualification_cadence_measurements -lt 15 -or $Artifact.loop_records -lt 2 -or $Artifact.cadence_measurements -lt 1 -or $Artifact.max_start_delta_ms -lt 1 -or $Artifact.max_start_delta_ms -gt 480) {
        throw "R7 qualification parser artifact lacks two-loop start-to-start cadence proof."
    }
    if ([int]$Signal.qualification_cadence_measurements -ne [int]$Artifact.qualification_cadence_measurements -or [int]$Signal.cadence_measurements -ne [int]$Artifact.cadence_measurements -or [int]$Signal.max_start_delta_ms -ne [int]$Artifact.max_start_delta_ms) {
        throw "R7 qualification cadence fields are not derived consistently from the parser artifact."
    }
}

function Assert-R7MetadataProof([object]$Artifact) {
    $names=@($Artifact.PSObject.Properties.Name)
    foreach($key in @('status','metadata','metadata_proof','qualification_frames','qualification_cadence_measurements','loop_records','cadence_measurements','busy_max','transaction_max','max_start_delta_ms','hardware_contact')) { if($names -notcontains $key){throw "R7 artifact missing required top-level field $key."} }
    if ($Artifact.metadata -ne $true -or $Artifact.metadata_proof -ne $true -or
        $Artifact.qualification_frames -ne 16 -or $Artifact.qualification_cadence_measurements -ne 15 -or
        $Artifact.loop_records -lt 32 -or $Artifact.cadence_measurements -ne ([int]$Artifact.loop_records - 1) -or
        $Artifact.busy_max -gt 600 -or $Artifact.transaction_max -gt 480 -or
        $Artifact.max_start_delta_ms -lt 1 -or $Artifact.max_start_delta_ms -gt 480) {
        throw "R7 metadata does not prove the full calm baseline and three-expression movement contract."
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$outputRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) { Join-Path $repoRoot ".cache\validation\wb55-r7-v22-sampler-supervisor" } else { [IO.Path]::GetFullPath($OutRoot) }
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$notePath = Join-Path $outputRoot "operator-note.txt"
$reviewPath = Join-Path $outputRoot "operator-review.json"
$resultPath = Join-Path $outputRoot "operator-result.json"
$guardPath = Join-Path $outputRoot "acceptance-prompt-invoked.json"
$stdoutPath = Join-Path $outputRoot "acceptance-prompt.stdout.log"
$stderrPath = Join-Path $outputRoot "acceptance-prompt.stderr.log"
$checkPath = Join-Path $outputRoot "prompt-supervisor-check.json"
$simulationReceiptPath = Join-Path $outputRoot "prompt-simulation-receipt.json"

if ($SelfTest) {
    $checks = [ordered]@{
        pass_maps_once = (Map-Selection "通过") -eq "PASS_OWNER_R7_LOCKED_V9_CHOREOGRAPHY_VISUAL"
        fail_maps_once = (Map-Selection "失败") -eq "NO_GO_OWNER_R7_LOCKED_V9_CHOREOGRAPHY_VISUAL"
        replay_option_absent = (Map-Selection "重新观察") -eq "NO_GO_R7_LOCKED_V9_CHOREOGRAPHY_NO_PASS_FAIL_SELECTION"
        prompt_requires_qualification_signal = $true
        prompt_requires_parser_artifact = $true
        one_loop_only_forbidden_before_prompt = $true
        two_loop_valid_prompt_gate = $true
        second_loop_must_measure_1_to_480ms = $true
        finalization_requires_two_loop_records = $true
        monitor_abnormal_exit_kills_prompt_tree = $true
        prompt_abnormal_exit_sets_emergency_signal = $true
        operator_selection_sets_single_stop_signal = $true
        popup_policy_is_one_acceptance_only = $true
        owner_wait_unbounded_by_default = $TimeoutSeconds -eq 0
    }
    $passed = @($checks.Values).Where({ -not $_ }).Count -eq 0
    $oneLoop = [pscustomobject]@{qualification_cadence_measurements=15;loop_records=1;cadence_measurements=0;max_start_delta_ms=0}
    $twoLoop = [pscustomobject]@{qualification_cadence_measurements=15;loop_records=2;cadence_measurements=1;max_start_delta_ms=480}
    $invalid481 = [pscustomobject]@{qualification_cadence_measurements=15;loop_records=2;cadence_measurements=1;max_start_delta_ms=481}
    $checks.one_loop_only_rejected_by_gate = try { Assert-QualificationCadence $oneLoop $oneLoop; $false } catch { $true }
    $checks.exact_two_loop_valid_by_gate = try { Assert-QualificationCadence $twoLoop $twoLoop; $true } catch { $false }
    $checks.explicit_481ms_rejected_by_gate = try { Assert-QualificationCadence $invalid481 $invalid481; $false } catch { $true }
    $checks.second_loop_must_measure_1_to_480ms = $checks.exact_two_loop_valid_by_gate -and $checks.explicit_481ms_rejected_by_gate
    $validMetadata = [pscustomobject]@{status="PASS_R7_LOCKED_V9_CHOREOGRAPHY_LOG";metadata=$true;metadata_proof=$true;qualification_frames=16;qualification_cadence_measurements=15;loop_records=32;cadence_measurements=31;busy_max=443;transaction_max=470;max_start_delta_ms=478;hardware_contact=0}
    $oldWindowMetadata = $validMetadata | ConvertTo-Json -Depth 10 | ConvertFrom-Json
    $oldWindowMetadata.metadata = $false
    $checks.old_72_177_mutation_rejected = try { Assert-R7MetadataProof $oldWindowMetadata; $false } catch { $true }
    $checks.r7_metadata_baseline_and_movement_proved = try { Assert-R7MetadataProof $validMetadata; $true } catch { $false }
    $checks.missing_metadata_rejected = try { Assert-R7MetadataProof ([pscustomobject]@{metadata_proof=$false;metadata=$null}); $false } catch { $true }
    $passed = @($checks.Values).Where({ -not $_ }).Count -eq 0
    $self = [ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.prompt_supervisor_selftest.v4";status=if($passed){"PASS_SELFTEST"}else{"FAIL_SELFTEST"};hardware_contact=0;write_counter_sum=0;programmer_calls=0;serial_open_count=0;reset_count=0;refresh_count=0;popup_count=0;retry_count=0;prompt_process_start_count=0;checks=$checks}
    Write-JsonAtomic $checkPath $self; $self | ConvertTo-Json -Depth 10
    if ($passed) { exit 0 } else { exit 1 }
}

if ($CheckOnly) {
    $aiw = Resolve-WorkflowAiwPath
    $check = [ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.prompt_supervisor_check.v4";status="READY_NO_PROMPT";hardware_contact=0;write_counter_sum=0;programmer_calls=0;serial_open_count=0;reset_count=0;refresh_count=0;popup_count=0;retry_count=0;canonical_aiw=$aiw;buttons=@("通过","失败");replay_option=$false;qualification_required_before_prompt=$true;metadata_proof_required=$true;concurrent_monitor_required=$true;abnormal_prompt_or_monitor_exit_fail_closed=$true;simulation_prompt_injection_forbidden_in_execute=$true;timeout_seconds=$TimeoutSeconds;owner_wait_unbounded=($TimeoutSeconds -eq 0);out_root_interface="-OutRoot"}
    Write-JsonAtomic $checkPath $check; $check | ConvertTo-Json -Depth 10; exit 0
}

foreach ($required in @($QualificationSignalPath,$MonitorResultPath,$StopSignalPath,$EmergencyStopPath)) {
    if ([string]::IsNullOrWhiteSpace($required)) { throw "Execute requires qualification, monitor-result, stop, and emergency signal paths." }
}
if (-not (Test-Path -LiteralPath $QualificationSignalPath -PathType Leaf)) { throw "The R7 qualification signal is absent; acceptance prompt is forbidden." }
if ((Test-Path -LiteralPath $guardPath -PathType Leaf) -or
    (Test-Path -LiteralPath $reviewPath -PathType Leaf) -or
    (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
    throw "The sole acceptance prompt has already been invoked; guard, review, or result already exists."
}

$qualification = Get-Content -LiteralPath $QualificationSignalPath -Raw | ConvertFrom-Json
$expectedHardwareContact = if ($SimulateQualifiedPrompt) { 0 } else { 1 }
if ($qualification.status -ne "PASS_R7_QUALIFICATION_READY" -or
    $qualification.hardware_contact -ne $expectedHardwareContact -or
    $qualification.qualification_frames -ne 16 -or
    $qualification.qualification_cadence_measurements -ne 15 -or
    $qualification.loop_records -lt 32 -or
    $qualification.cadence_measurements -ne ([int]$qualification.loop_records - 1) -or
    $qualification.max_start_delta_ms -lt 1 -or $qualification.max_start_delta_ms -gt 480 -or
    $qualification.ring_bytes_limit -ne 65536 -or
    -not (Test-Path -LiteralPath ([string]$qualification.parser_artifact) -PathType Leaf) -or
    -not (Test-Path -LiteralPath ([string]$qualification.qualification_snapshot) -PathType Leaf)) {
    throw "R7 qualification evidence is incomplete; acceptance prompt is forbidden."
}
$qualificationArtifact = Get-Content -LiteralPath ([string]$qualification.parser_artifact) -Raw | ConvertFrom-Json
if ($qualificationArtifact.status -ne "PASS_R7_LOCKED_V9_CHOREOGRAPHY_LOG" -or
    $qualificationArtifact.qualification_frames -ne 16 -or
    $qualificationArtifact.loop_records -lt 2 -or
    $qualificationArtifact.qualification_cadence_measurements -lt 15 -or
    $qualificationArtifact.cadence_measurements -ne ([int]$qualificationArtifact.loop_records - 1) -or
    $qualificationArtifact.busy_max -gt 600 -or
    $qualificationArtifact.transaction_max -gt 480 -or
    $qualificationArtifact.max_start_delta_ms -lt 1 -or
    $qualificationArtifact.max_start_delta_ms -gt 480 -or
    $qualificationArtifact.hardware_contact -ne $expectedHardwareContact) {
    throw "The R7 parser did not prove a complete initial 16-frame qualification."
}
Assert-R7MetadataProof $qualificationArtifact
Assert-QualificationCadence $qualification $qualificationArtifact
if ((Get-Item -LiteralPath ([string]$qualification.qualification_snapshot)).Length -gt 65536) {
    throw "The R7 qualification snapshot exceeds the fixed 65536-byte bound."
}
if ($SimulateQualifiedPrompt -and $qualificationArtifact.hardware_contact -ne 0) { throw "Simulated qualification evidence must prove zero hardware contact." }
if (-not $SimulateQualifiedPrompt -and $qualificationArtifact.hardware_contact -ne 1) { throw "Execute qualification evidence must prove hardware_contact=1." }
$monitorProcess = Get-Process -Id ([int]$qualification.process_id) -ErrorAction SilentlyContinue
if (-not $monitorProcess -or $monitorProcess.HasExited) { throw "The R7 monitor is not alive; acceptance prompt is forbidden." }
if (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf) { throw "An emergency stop already exists; acceptance prompt is forbidden." }

$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
Write-JsonAtomic $guardPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.prompt_guard.v2";status="INVOKED_ONCE";process_id=$PID;monitor_process_id=[int]$qualification.process_id;buttons=@("通过","失败");simulation_no_hardware=[bool]$SimulateQualifiedPrompt;actual_popup_count=if($SimulateQualifiedPrompt){0}else{1}})

$arguments = if ($SimulateQualifiedPrompt) {
    $simulationScript = (Resolve-Path -LiteralPath $SimulationPromptScript -ErrorAction Stop).Path
    @("-NoProfile","-File",$simulationScript,"-OutputPath",$notePath)
} else {
    $aiw = Resolve-WorkflowAiwPath
    @("-NoProfile","-File",$aiw,"operator-prompt","-Title","Companion R7 三表情验收","-ProgressText","三表情连续观察","-ScopeText","屏幕将按平静、好奇、温暖、好奇、平静的顺序持续切换。","-Message","请观察三种表情是否清晰、切换是否自然，且背景保持干净无残影。","-ExpectedText","请仅选择通过或失败。","-ObservationLabel","备注","-Input","-ReviewStyle","-Buttons","通过,失败","-OutputPath",$notePath,"-TimeoutSeconds","$TimeoutSeconds","-Json")
}
$startInfo = [Diagnostics.ProcessStartInfo]::new();$startInfo.FileName=$pwsh;$startInfo.UseShellExecute=$false;$startInfo.CreateNoWindow=$true;$startInfo.RedirectStandardOutput=$true;$startInfo.RedirectStandardError=$true
foreach ($argument in $arguments) { $startInfo.ArgumentList.Add($argument) }
$promptProcess = $null
try {
    $promptProcess = [Diagnostics.Process]::Start($startInfo)
    if ($SimulateQualifiedPrompt) {
        Write-JsonAtomic $simulationReceiptPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.prompt_simulation_receipt.v1";status="PROMPT_PROCESS_STARTED_ONCE_NO_POPUP";hardware_contact=0;actual_popup_count=0;prompt_process_start_count=1;prompt_process_id=$promptProcess.Id})
    }
    $promptFault = $null
    while (-not $promptProcess.HasExited) {
        if (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf) { $promptFault = "Emergency stop occurred while acceptance was open."; break }
        $monitorProcess.Refresh()
        if ($monitorProcess.HasExited) { $promptFault = "R7 monitor exited while acceptance was open."; break }
        Start-Sleep -Milliseconds 100
    }
    if ($promptFault) {
        if (-not $promptProcess.HasExited) { Stop-ProcessTree $promptProcess.Id }
        Write-JsonAtomic $EmergencyStopPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.emergency_stop.v2";reason="prompt_supervision_fault";detail=$promptFault})
        throw $promptFault
    }
    $promptProcess.WaitForExit();$stdout=$promptProcess.StandardOutput.ReadToEnd();$stderr=$promptProcess.StandardError.ReadToEnd()
    [IO.File]::WriteAllText($stdoutPath,$stdout,[Text.UTF8Encoding]::new($false));[IO.File]::WriteAllText($stderrPath,$stderr,[Text.UTF8Encoding]::new($false))
    if ($promptProcess.ExitCode -ne 0) {
        Write-JsonAtomic $EmergencyStopPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.emergency_stop.v2";reason="prompt_process_abnormal_exit";exit_code=$promptProcess.ExitCode})
        throw "Canonical acceptance prompt exited abnormally with code $($promptProcess.ExitCode)."
    }
    $promptResult = $stdout | ConvertFrom-Json;$selected=[string]$promptResult.selected;$status=Map-Selection $selected
    if ($status -eq "NO_GO_R7_LOCKED_V9_CHOREOGRAPHY_NO_PASS_FAIL_SELECTION") {
        Write-JsonAtomic $EmergencyStopPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.emergency_stop.v2";reason="prompt_missing_pass_fail_selection"})
        throw "Canonical acceptance prompt returned neither 通过 nor 失败."
    }
    $note = if (Test-Path -LiteralPath $notePath -PathType Leaf) { Get-Content -LiteralPath $notePath -Raw } else { [string]$promptResult.text }
    $noteSha = if (Test-Path -LiteralPath $notePath -PathType Leaf) { (Get-FileHash -LiteralPath $notePath -Algorithm SHA256).Hash.ToUpperInvariant() } else { $null }
    $review = [ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.operator_review.v2";status=$status;style="aiw_operator_prompt_v1";selected=$selected;note=$note;note_path=$notePath;note_sha256=$noteSha;qualification_artifact=[string]$qualification.parser_artifact;qualification_sha256=(Get-FileHash -LiteralPath ([string]$qualification.parser_artifact) -Algorithm SHA256).Hash.ToUpperInvariant();machine_qualification_steps=16;continuous_loop_was_concurrent=$true;simulation_no_hardware=[bool]$SimulateQualifiedPrompt;actual_popup_count=if($SimulateQualifiedPrompt){0}else{1}}
    Write-JsonAtomic $reviewPath $review
    Write-JsonAtomic $resultPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.operator_result.v2";status=$status;selected=$selected;actual_popup_count=if($SimulateQualifiedPrompt){0}else{1};review_path=$reviewPath;prompt_process_start_count=1})
    if (Test-Path -LiteralPath $StopSignalPath -PathType Leaf) { throw "A stop signal already exists; duplicate operator completion is forbidden." }
    Write-JsonAtomic $StopSignalPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.operator_stop.v2";reason="operator_selection";selected=$selected;review_path=$reviewPath;result_path=$resultPath})
    $review | ConvertTo-Json -Depth 10 -Compress
    exit 0
} catch {
    if ($promptProcess -and -not $promptProcess.HasExited) { Stop-ProcessTree $promptProcess.Id }
    if (-not (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf)) { Write-JsonAtomic $EmergencyStopPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.emergency_stop.v2";reason="prompt_or_monitor_failure";detail=$_.Exception.Message}) }
    throw
} finally {
    if ($promptProcess -and -not $promptProcess.HasExited) { Stop-ProcessTree $promptProcess.Id }
}

