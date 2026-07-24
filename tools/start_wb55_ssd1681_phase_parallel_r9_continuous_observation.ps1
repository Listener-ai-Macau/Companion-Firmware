param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [string]$OutRoot,
    [string]$Port,
    [string]$AuthorizationArtifact,
    [ValidateRange(60, 1800)]
    [int]$HumanPromptTimeoutSeconds = 900,
    [string]$ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins",
    [switch]$LifecycleSelfTestFailure
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($CheckOnly -eq $Execute) {
    throw "Choose exactly one of -CheckOnly or -Execute."
}
if ($LifecycleSelfTestFailure -and -not $CheckOnly) {
    throw "LifecycleSelfTestFailure is allowed only with -CheckOnly."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $PSScriptRoot "run_wb55_ssd1681_phase_parallel_r9_continuous_observation.ps1"
$candidate = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_phase_parallel_r9_continuous_observation\Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9ContinuousObservation.hex"
$staticVerifier = Join-Path $PSScriptRoot "verify_wb55_ssd1681_phase_parallel_r9_continuous_observation.py"
$parser = Join-Path $PSScriptRoot "verify_wb55_ssd1681_phase_parallel_r9_continuous_log.py"
$monitor = Join-Path $PSScriptRoot "monitor_wb55_ssd1681_phase_parallel_r9_continuous.ps1"
$supervisor = Join-Path $PSScriptRoot "supervise_wb55_ssd1681_phase_parallel_r9_continuous_prompt.ps1"
$historicalRunner = Join-Path $PSScriptRoot "run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1"
$historicalCandidate = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_phase_parallel_r9\Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9.hex"
$workbench = Join-Path $repoRoot "docs\validation\companion-ssd1681-phase-parallel-r9-workbench-20260721.json"
$lockedHashes = [ordered]@{
    runner = "F608E9F1EF018EA215BD7189E415AF7490C21605C5BAE3FA8886EEC74004903A"
    candidate_hex = "3B416BFF08B630D23BDB6107B2C17DFE9FBBFAAA7D5CFBCA5063AE68E62B79C5"
    static_verifier = "DC8ED8C3D25556CD436BD6DC54E904DDFCF9A14E1BC24E16888D664D00E5B415"
    parser = "859F1E3868464676859821209C765E48B8A60BCFE2E4F8E17EDC9EBE0B963A34"
    monitor = "FF60FEEA483F6844DA7B252B8910D22D6240EABCB9C42AFAE2362122C7026920"
    prompt_supervisor = "39ACC31A561413717B77ACAFE5E7E562B0C44734F07D72007B46C900C85883D2"
    historical_runner = "0B0A536E7B03DD5F2A4F9CF7B2B76A1B0DB3F34745172E352CB0B4726011B34B"
    historical_candidate_hex = "724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF"
    workbench = "E7311523D6FE571434F0C1F2D5EC76B7ED9B64DC725B0726DDEC023421D7E4EF"
}
$lockedPaths = [ordered]@{
    runner = $runner
    candidate_hex = $candidate
    static_verifier = $staticVerifier
    parser = $parser
    monitor = $monitor
    prompt_supervisor = $supervisor
    historical_runner = $historicalRunner
    historical_candidate_hex = $historicalCandidate
    workbench = $workbench
}

foreach ($name in $lockedPaths.Keys) {
    $path = $lockedPaths[$name]
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Locked R9 continuous input is missing: $path"
    }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($actual -ne $lockedHashes[$name]) {
        throw "Locked R9 continuous input hash mismatch for $name; refusing child start."
    }
}

if ($Execute) {
    if ([string]::IsNullOrWhiteSpace($AuthorizationArtifact) -or
        -not (Test-Path -LiteralPath $AuthorizationArtifact -PathType Leaf)) {
        throw "Execute is not authorized by COMP-REQ-316 R2 MACHINE_READY; a later root-issued authorization artifact is required."
    }
    $authorization = Get-Content -LiteralPath $AuthorizationArtifact -Raw | ConvertFrom-Json
    if ($authorization.status -ne "AUTHORIZED_R9_CONTINUOUS_OBSERVATION_ONCE" -or
        $authorization.requirement_id -ne "COMP-REQ-313" -or
        $authorization.candidate_hex_sha256 -ne $lockedHashes.candidate_hex -or
        $authorization.consumed -ne $false) {
        throw "The supplied continuous-observation authorization is invalid or consumed."
    }
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) {
    Join-Path $repoRoot ".cache\validation\wb55-phase-parallel-r9-continuous-persistent-$stamp"
} else {
    [System.IO.Path]::GetFullPath($OutRoot)
}
if (Test-Path -LiteralPath $runRoot) {
    throw "R9 continuous persistent launch output directory already exists; reuse is forbidden: $runRoot"
}
New-Item -ItemType Directory -Path $runRoot | Out-Null

$stdout = Join-Path $runRoot "runner.stdout.log"
$stderr = Join-Path $runRoot "runner.stderr.log"
$stageRun = Join-Path $runRoot "stage-run.json"
$launchArtifact = Join-Path $runRoot "persistent-launch.json"
$arguments = if ($LifecycleSelfTestFailure) {
    @("-NoProfile", "-Command", "exit 23")
} else {
    @(
        "-NoProfile", "-File", $runner,
        $(if ($CheckOnly) { "-CheckOnly" } else { "-Execute" }),
        "-PhaseParallelR9ContinuousObservation",
        "-OutRoot", $runRoot,
        "-HumanPromptTimeoutSeconds", "$HumanPromptTimeoutSeconds",
        "-ProgrammerRoot", $ProgrammerRoot
    )
}
if (-not $LifecycleSelfTestFailure -and -not [string]::IsNullOrWhiteSpace($Port)) {
    $arguments += @("-Port", $Port)
}
if ($Execute) {
    $arguments += @("-AuthorizationArtifact", ([System.IO.Path]::GetFullPath($AuthorizationArtifact)))
}

$process = Start-Process -FilePath "pwsh" -ArgumentList $arguments `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
    -WindowStyle Hidden -PassThru
$report = [ordered]@{
    schema_id = "companion.wb55.ssd1681_phase_parallel_r9_continuous_observation.persistent_launch.v1"
    status = if ($CheckOnly) { "CHECK_RUNNING" } else { "STARTED_DETACHED" }
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mode = if ($CheckOnly) { "check_only" } else { "execute" }
    process_id = $process.Id
    parent_process_id = $PID
    runner = $runner
    arguments = @($arguments)
    out_root = $runRoot
    stage_run = $stageRun
    stdout = $stdout
    stderr = $stderr
    durable_stdout_redirected = $true
    durable_stderr_redirected = $true
    hidden_child = $true
    persistent_child = $true
    output_directory_reuse_forbidden = $true
    locked_hashes = $lockedHashes
    hardware_contact = if ($CheckOnly) { 0 } else { $null }
    write_counter_sum = if ($CheckOnly) { 0 } else { $null }
    popup_count = if ($CheckOnly) { 0 } else { $null }
    lifecycle_self_test_failure = [bool]$LifecycleSelfTestFailure
    authorization_artifact = if ($Execute) { [System.IO.Path]::GetFullPath($AuthorizationArtifact) } else { $null }
    authorization_boundary = "COMP-REQ-316 authorizes R2 repair/build/CheckOnly/MACHINE_READY only; Execute requires a new explicit root-issued single-run artifact"
}
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $launchArtifact -Encoding UTF8

if ($Execute) {
    Write-Output "STARTED_DETACHED: pid=$($process.Id) artifact=$launchArtifact"
    exit 0
}

if (-not $process.WaitForExit(120000)) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    $report.status = "NO_GO_CHECK_TIMEOUT"
} else {
    $process.WaitForExit()
    $report.exit_code = $process.ExitCode
    if ($process.ExitCode -ne 0) {
        $report.status = "NO_GO_CHECK_CHILD_EXIT"
    } elseif (-not (Test-Path -LiteralPath $stageRun -PathType Leaf)) {
        $report.status = "NO_GO_CHECK_STAGE_MISSING"
    } else {
        $stage = Get-Content -LiteralPath $stageRun -Raw | ConvertFrom-Json
        $writeNames = @("preclean_write_calls", "postclean_write_calls", "candidate_write_calls", "restore_write_calls", "panel_writes", "panel_refresh_commands", "panel_hard_resets")
        $writeSum = 0
        foreach ($name in $writeNames) {
            if ($null -eq $stage.counters.$name) { $writeSum = -1; break }
            $writeSum += [int64]$stage.counters.$name
        }
        $report.stage_status = $stage.status
        $report.hardware_contact = $stage.hardware_contact
        $report.write_counter_sum = $writeSum
        $report.popup_count = if ($stage.operator_prompt.invoked) { 1 } else { 0 }
        $report.status = if (
            $stage.status -eq "READY_NO_HARDWARE_CONTACT" -and
            $stage.hardware_contact -eq 0 -and
            $writeSum -eq 0 -and
            $stage.pre_execute_prompt.required -eq $false -and
            $stage.pre_execute_prompt.invoked -eq $false -and
            $stage.operator_prompt.required -eq $true -and
            $stage.operator_prompt.invoked -eq $false -and
            $stage.popup_policy.pre_execute -eq 0 -and
            $stage.popup_policy.cleanup -eq 0 -and
            $stage.popup_policy.recovery_or_fault_acknowledgement -eq 0 -and
            $stage.popup_policy.visual_acceptance -eq 1
        ) { "READY_NO_HARDWARE_CONTACT" } else { "NO_GO_CHECK_STAGE" }
    }
}

$report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $launchArtifact -Encoding UTF8
if ($report.status -eq "READY_NO_HARDWARE_CONTACT") {
    Write-Output "READY_NO_HARDWARE_CONTACT: pid=$($process.Id) artifact=$launchArtifact"
    exit 0
}
throw "R9 continuous persistent launcher failed closed: $($report.status); see $launchArtifact"
