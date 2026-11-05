param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [string]$OutRoot,
    [string]$Port,
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
$runner = Join-Path $PSScriptRoot "run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1"
$candidate = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_ram_command_target_r8\Companion_Nucleo_WB55RG_Ssd1681RamCommandTargetR8.hex"
$r8MachineReady = Join-Path $repoRoot "docs\validation\companion-ssd1681-ram-command-target-r8-machine-ready-20260721.json"
$incident = Join-Path $repoRoot "docs\validation\companion-ssd1681-ram-command-target-r8-launch-transport-incident-20260721.json"
$lockedHashes = [ordered]@{
    runner = "3E1A3FFDC4B44BDE107CF6A0922E81ECA1F95442B8A6A3BDF4F71C018806D017"
    candidate_hex = "9ECF8F4A2A75A054077908C775879447ADCE089F55DC33315A8C852C4F47CB13"
    r8_machine_ready = "5FC97C92136A2EAC862620C847C1B6910491800EC84248ED8F255D32D9DFA568"
    incident = "C3D8C8809C2C807592A92D9749F235013AF465434DD16ED9B558308E71CB7900"
}
$lockedPaths = [ordered]@{
    runner = $runner
    candidate_hex = $candidate
    r8_machine_ready = $r8MachineReady
    incident = $incident
}

foreach ($name in $lockedPaths.Keys) {
    $path = $lockedPaths[$name]
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Locked R8 input is missing: $path"
    }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($actual -ne $lockedHashes[$name]) {
        throw "Locked R8 input hash mismatch for $name; refusing child start."
    }
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) {
    Join-Path $repoRoot ".cache\validation\wb55-ram-command-target-r8-persistent-$stamp"
} else {
    [System.IO.Path]::GetFullPath($OutRoot)
}
if (Test-Path -LiteralPath $runRoot) {
    throw "R8 persistent launch output directory already exists; reuse is forbidden: $runRoot"
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
        "-NoProfile",
        "-File", $runner,
        $(if ($CheckOnly) { "-CheckOnly" } else { "-Execute" }),
        "-RamCommandTargetR8",
        "-OutRoot", $runRoot,
        "-HumanPromptTimeoutSeconds", "$HumanPromptTimeoutSeconds",
        "-ProgrammerRoot", $ProgrammerRoot
    )
}
if (-not $LifecycleSelfTestFailure -and -not [string]::IsNullOrWhiteSpace($Port)) {
    $arguments += @("-Port", $Port)
}

$process = Start-Process -FilePath "pwsh" -ArgumentList $arguments `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
    -WindowStyle Hidden -PassThru

$report = [ordered]@{
    schema_id = "companion.wb55.ssd1681_ram_command_target_r8.persistent_launch.v1"
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
    observer_may_exit_without_closing_runner_streams = $true
    locked_hashes = $lockedHashes
    hardware_contact = if ($CheckOnly) { 0 } else { $null }
    write_counter_sum = if ($CheckOnly) { 0 } else { $null }
    lifecycle_self_test_failure = [bool]$LifecycleSelfTestFailure
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
        $writeNames = @(
            "preclean_write_calls",
            "postclean_write_calls",
            "candidate_write_calls",
            "restore_write_calls",
            "panel_writes",
            "panel_refresh_commands",
            "panel_hard_resets"
        )
        $writeSum = 0
        foreach ($name in $writeNames) {
            $value = $stage.counters.$name
            if ($null -eq $value) {
                $writeSum = -1
                break
            }
            $writeSum += [int64]$value
        }
        $report.stage_status = $stage.status
        $report.hardware_contact = $stage.hardware_contact
        $report.write_counter_sum = $writeSum
        $report.status = if (
            $stage.status -eq "READY_NO_HARDWARE_CONTACT" -and
            $stage.hardware_contact -eq 0 -and
            $writeSum -eq 0 -and
            $stage.pre_execute_prompt.required -eq $false -and
            $stage.pre_execute_prompt.invoked -eq $false -and
            $stage.operator_prompt.invoked -eq $false
        ) {
            "READY_NO_HARDWARE_CONTACT"
        } else {
            "NO_GO_CHECK_STAGE"
        }
    }
}

$report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $launchArtifact -Encoding UTF8
if ($report.status -eq "READY_NO_HARDWARE_CONTACT") {
    Write-Output "READY_NO_HARDWARE_CONTACT: pid=$($process.Id) artifact=$launchArtifact"
    exit 0
}
throw "R8 persistent launcher failed closed: $($report.status); see $launchArtifact"
