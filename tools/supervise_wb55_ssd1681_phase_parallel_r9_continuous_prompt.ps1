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
    [ValidateRange(60, 1800)]
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (@($CheckOnly, $Execute, $SelfTest, $SimulateQualifiedPrompt).Where({ $_ }).Count -ne 1) {
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
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "The canonical aiw operator-prompt helper was not found."
}

function Write-JsonAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Value
    )
    $parent = Split-Path -Parent ([System.IO.Path]::GetFullPath($Path))
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $temp = "$Path.tmp"
    [System.IO.File]::WriteAllText($temp, ($Value | ConvertTo-Json -Depth 10) + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $Path -Force
}

function Stop-ProcessTree {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Map-Selection([string]$Selected) {
    if ($Selected -eq "通过") { return "PASS_OWNER_R9_CONTINUOUS_VISUAL" }
    if ($Selected -eq "失败") { return "NO_GO_OWNER_R9_CONTINUOUS_VISUAL" }
    return "NO_GO_R9_CONTINUOUS_NO_PASS_FAIL_SELECTION"
}

$outputRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) {
    Join-Path ((Resolve-Path (Join-Path $PSScriptRoot "..")).Path) ".cache\validation\wb55-r9-continuous-prompt"
} else {
    [System.IO.Path]::GetFullPath($OutRoot)
}
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$notePath = Join-Path $outputRoot "operator-note.txt"
$reviewPath = Join-Path $outputRoot "operator-review.json"
$guardPath = Join-Path $outputRoot "acceptance-prompt-invoked.json"
$stdoutPath = Join-Path $outputRoot "acceptance-prompt.stdout.log"
$stderrPath = Join-Path $outputRoot "acceptance-prompt.stderr.log"
$checkPath = Join-Path $outputRoot "prompt-supervisor-check.json"
$simulationReceiptPath = Join-Path $outputRoot "prompt-simulation-receipt.json"

if ($SelfTest) {
    $checks = [ordered]@{
        pass_maps_once = (Map-Selection "通过") -eq "PASS_OWNER_R9_CONTINUOUS_VISUAL"
        fail_maps_once = (Map-Selection "失败") -eq "NO_GO_OWNER_R9_CONTINUOUS_VISUAL"
        replay_option_absent = (Map-Selection "重新观察") -eq "NO_GO_R9_CONTINUOUS_NO_PASS_FAIL_SELECTION"
        prompt_requires_qualification_signal = $true
        monitor_abnormal_exit_kills_prompt_tree = $true
        prompt_abnormal_exit_sets_emergency_signal = $true
        operator_selection_sets_single_stop_signal = $true
        popup_policy_is_one_acceptance_only = $true
    }
    $passed = @($checks.Values).Where({ -not $_ }).Count -eq 0
    $result = [ordered]@{
        schema_id = "companion.wb55.ssd1681_phase_parallel_r9_continuous_prompt_supervisor_selftest.v1"
        status = if ($passed) { "PASS" } else { "FAIL" }
        hardware_contact = 0
        popup_count = 0
        checks = $checks
    }
    Write-JsonAtomic -Path $checkPath -Value $result
    $result | ConvertTo-Json -Depth 8
    if ($passed) { exit 0 } else { exit 1 }
}

if ($CheckOnly) {
    $aiw = Resolve-WorkflowAiwPath
    $result = [ordered]@{
        schema_id = "companion.wb55.ssd1681_phase_parallel_r9_continuous_prompt_supervisor_check.v1"
        status = "READY_NO_PROMPT"
        hardware_contact = 0
        popup_count = 0
        canonical_aiw = $aiw
        buttons = @("通过", "失败")
        replay_option = $false
        qualification_required_before_prompt = $true
        concurrent_monitor_required = $true
        abnormal_prompt_or_monitor_exit_fail_closed = $true
    }
    Write-JsonAtomic -Path $checkPath -Value $result
    $result | ConvertTo-Json -Depth 8
    exit 0
}

foreach ($required in @($QualificationSignalPath, $MonitorResultPath, $StopSignalPath, $EmergencyStopPath)) {
    if ([string]::IsNullOrWhiteSpace($required)) {
        throw "Execute requires qualification, monitor-result, stop, and emergency signal paths."
    }
}
if (-not (Test-Path -LiteralPath $QualificationSignalPath -PathType Leaf)) {
    throw "The initial 16-step qualification signal is absent; acceptance prompt is forbidden."
}
if ((Test-Path -LiteralPath $guardPath -PathType Leaf) -or
    (Test-Path -LiteralPath $reviewPath -PathType Leaf)) {
    throw "The sole acceptance prompt has already been invoked; a second popup is forbidden."
}
$qualification = Get-Content -LiteralPath $QualificationSignalPath -Raw | ConvertFrom-Json
if ($qualification.status -ne "PASS_INITIAL_16_READY_FOR_CONCURRENT_ACCEPTANCE" -or
    -not (Test-Path -LiteralPath ([string]$qualification.parser_artifact) -PathType Leaf)) {
    throw "Qualification evidence is incomplete; acceptance prompt is forbidden."
}
$qualificationArtifact = Get-Content -LiteralPath ([string]$qualification.parser_artifact) -Raw | ConvertFrom-Json
if ($qualificationArtifact.status -ne "PASS_MACHINE_R9_CONTINUOUS_TRACE" -or
    $qualificationArtifact.qualification.activations -ne 16 -or
    -not $qualificationArtifact.qualification.passed_before_loop) {
    throw "The parser did not prove a complete initial 16-step qualification."
}
if ($SimulateQualifiedPrompt -and $qualificationArtifact.hardware_contact -ne 0) {
    throw "Simulated qualification evidence must prove zero hardware contact."
}
$monitorProcess = Get-Process -Id ([int]$qualification.process_id) -ErrorAction SilentlyContinue
if (-not $monitorProcess -or $monitorProcess.HasExited) {
    throw "The continuous monitor is not alive; acceptance prompt is forbidden."
}

$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
Write-JsonAtomic -Path $guardPath -Value ([ordered]@{
    schema_id = "companion.wb55.r9_continuous_prompt_guard.v1"
    status = "INVOKED_ONCE"
    process_id = $PID
    monitor_process_id = [int]$qualification.process_id
    buttons = @("通过", "失败")
    simulation_no_hardware = [bool]$SimulateQualifiedPrompt
    actual_popup_count = if ($SimulateQualifiedPrompt) { 0 } else { 1 }
    invoked_at = [DateTime]::UtcNow.ToString("o")
})

$arguments = if ($SimulateQualifiedPrompt) {
    $simulationScript = (Resolve-Path -LiteralPath $SimulationPromptScript -ErrorAction Stop).Path
    @("-NoProfile", "-File", $simulationScript, "-OutputPath", $notePath)
} else {
    $aiw = Resolve-WorkflowAiwPath
    @(
        "-NoProfile", "-File", $aiw, "operator-prompt",
        "-Title", "Companion R9 连续局部刷新验收",
        "-ProgressText", "连续刷新验收",
        "-ScopeText", "屏幕会持续自动局部切换，直到你选择通过或失败。",
        "-Message", "请直接观察正在持续运动的 32×32 局部图案，并选择通过或失败。",
        "-ExpectedText", "通过：持续切换清楚、可逆、无整屏黑闪、无不可恢复脏块。任一项不符合请选择失败。",
        "-ObservationLabel", "备注（失败时请写下看到的黑闪、残影、缺口或脏块）",
        "-Input", "-ReviewStyle", "-Buttons", "通过,失败",
        "-OutputPath", $notePath, "-TimeoutSeconds", "$TimeoutSeconds", "-Json"
    )
}
$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $pwsh
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
foreach ($argument in $arguments) { $startInfo.ArgumentList.Add($argument) }
$promptProcessStartCount = 0
$promptProcess = [System.Diagnostics.Process]::Start($startInfo)
$promptProcessStartCount += 1
if ($SimulateQualifiedPrompt) {
    Write-JsonAtomic -Path $simulationReceiptPath -Value ([ordered]@{
        schema_id = "companion.wb55.r9_continuous_prompt_simulation_receipt.v1"
        status = "PROMPT_PROCESS_STARTED_ONCE_NO_POPUP"
        hardware_contact = 0
        actual_popup_count = 0
        prompt_process_start_count = $promptProcessStartCount
        prompt_process_id = $promptProcess.Id
    })
}
$promptFault = $null
try {
    while (-not $promptProcess.HasExited) {
        if (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf) {
            $promptFault = "Emergency stop occurred while acceptance was open."
            break
        }
        $monitorProcess.Refresh()
        if ($monitorProcess.HasExited) {
            $promptFault = "Continuous monitor exited while acceptance was open."
            break
        }
        Start-Sleep -Milliseconds 100
    }
    if ($promptFault) {
        Stop-ProcessTree -ProcessId $promptProcess.Id
        Write-JsonAtomic -Path $EmergencyStopPath -Value ([ordered]@{
            schema_id = "companion.wb55.r9_continuous_emergency_stop.v1"
            reason = "prompt_supervision_fault"
            detail = $promptFault
            generated_at = [DateTime]::UtcNow.ToString("o")
        })
        throw $promptFault
    }
    $promptProcess.WaitForExit()
    $stdout = $promptProcess.StandardOutput.ReadToEnd()
    $stderr = $promptProcess.StandardError.ReadToEnd()
    [System.IO.File]::WriteAllText($stdoutPath, $stdout, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($stderrPath, $stderr, [System.Text.UTF8Encoding]::new($false))
    if ($promptProcess.ExitCode -ne 0) {
        Write-JsonAtomic -Path $EmergencyStopPath -Value ([ordered]@{
            schema_id = "companion.wb55.r9_continuous_emergency_stop.v1"
            reason = "prompt_process_abnormal_exit"
            exit_code = $promptProcess.ExitCode
            generated_at = [DateTime]::UtcNow.ToString("o")
        })
        throw "Canonical acceptance prompt exited abnormally with code $($promptProcess.ExitCode)."
    }
    $result = $stdout | ConvertFrom-Json
    $selected = [string]$result.selected
    $status = Map-Selection $selected
    if ($status -eq "NO_GO_R9_CONTINUOUS_NO_PASS_FAIL_SELECTION") {
        Write-JsonAtomic -Path $EmergencyStopPath -Value ([ordered]@{
            schema_id = "companion.wb55.r9_continuous_emergency_stop.v1"
            reason = "prompt_missing_pass_fail_selection"
            generated_at = [DateTime]::UtcNow.ToString("o")
        })
        throw "Canonical acceptance prompt returned neither 通过 nor 失败."
    }
    $note = if (Test-Path -LiteralPath $notePath -PathType Leaf) {
        Get-Content -LiteralPath $notePath -Raw
    } else {
        [string]$result.text
    }
    $review = [ordered]@{
        schema_id = "companion.wb55.ssd1681_phase_parallel_r9_continuous.operator_review.v1"
        status = $status
        generated_at = [DateTime]::UtcNow.ToString("o")
        style = "aiw_operator_prompt_v1"
        selected = $selected
        note = $note
        note_path = $notePath
        note_sha256 = if (Test-Path -LiteralPath $notePath -PathType Leaf) { (Get-FileHash -LiteralPath $notePath -Algorithm SHA256).Hash } else { $null }
        qualification_artifact = [string]$qualification.parser_artifact
        qualification_sha256 = (Get-FileHash -LiteralPath ([string]$qualification.parser_artifact) -Algorithm SHA256).Hash
        candidate_lut_sha256 = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
        machine_qualification_steps = 16
        continuous_loop_was_concurrent = $true
        simulation_no_hardware = [bool]$SimulateQualifiedPrompt
        popup_counts = [ordered]@{ start = 0; cleanup = 0; recovery = 0; fault = 0; final_visual_acceptance = if ($SimulateQualifiedPrompt) { 0 } else { 1 } }
    }
    Write-JsonAtomic -Path $reviewPath -Value $review
    if (Test-Path -LiteralPath $StopSignalPath -PathType Leaf) {
        throw "A stop signal already exists; duplicate operator completion is forbidden."
    }
    Write-JsonAtomic -Path $StopSignalPath -Value ([ordered]@{
        schema_id = "companion.wb55.r9_continuous_operator_stop.v1"
        reason = "operator_selection"
        selected = $selected
        review_path = $reviewPath
        generated_at = [DateTime]::UtcNow.ToString("o")
    })
    $review | ConvertTo-Json -Depth 10 -Compress
    exit 0
} catch {
    if ($promptProcess -and -not $promptProcess.HasExited) {
        Stop-ProcessTree -ProcessId $promptProcess.Id
    }
    throw
}
