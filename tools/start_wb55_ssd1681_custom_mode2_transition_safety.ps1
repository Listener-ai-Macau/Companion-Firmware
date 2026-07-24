param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [ValidateRange(60, 1800)]
    [int]$HumanPromptTimeoutSeconds = 900,
    [string]$Port,
    [string]$OutRoot,
    [string]$ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($CheckOnly -eq $Execute) {
    throw "Choose exactly one of -CheckOnly or -Execute."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $PSScriptRoot "run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = if ($OutRoot) {
    [System.IO.Path]::GetFullPath($OutRoot)
} else {
    Join-Path $repoRoot ".cache\validation\wb55-custom-mode2-transition-safety-detached-$stamp"
}
if (Test-Path -LiteralPath $runRoot) {
    throw "Detached launch output directory already exists; reuse is forbidden: $runRoot"
}
New-Item -ItemType Directory -Path $runRoot | Out-Null

$stdout = Join-Path $runRoot "runner.stdout.log"
$stderr = Join-Path $runRoot "runner.stderr.log"
$stageRun = Join-Path $runRoot "stage-run.json"
$launchArtifact = Join-Path $runRoot "detached-launch.json"
$arguments = @(
    "-NoProfile",
    "-File", $runner,
    $(if ($CheckOnly) { "-CheckOnly" } else { "-Execute" }),
    "-CustomMode2TransitionSafety",
    "-OutRoot", $runRoot,
    "-HumanPromptTimeoutSeconds", "$HumanPromptTimeoutSeconds",
    "-ProgrammerRoot", $ProgrammerRoot
)
if (-not [string]::IsNullOrWhiteSpace($Port)) {
    $arguments += @("-Port", $Port)
}

$process = Start-Process -FilePath "pwsh" -ArgumentList $arguments `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
    -WindowStyle Hidden -PassThru

$report = [ordered]@{
    schema_id = "companion.wb55.ssd1681_custom_mode2_detached_launch.v1"
    status = if ($CheckOnly) { "CHECK_RUNNING" } else { "STARTED_DETACHED" }
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mode = if ($CheckOnly) { "check_only" } else { "execute" }
    process_id = $process.Id
    runner = $runner
    out_root = $runRoot
    stage_run = $stageRun
    stdout = $stdout
    stderr = $stderr
    durable_stdout_redirected = $true
    durable_stderr_redirected = $true
    output_directory_reuse_forbidden = $true
    observer_may_exit_without_closing_runner_streams = $true
    hardware_contact = if ($CheckOnly) { 0 } else { $null }
}

if ($CheckOnly) {
    if (-not $process.WaitForExit(120000)) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $report.status = "NO_GO_CHECK_TIMEOUT"
    } else {
        $process.WaitForExit()
        $report.exit_code = $process.ExitCode
        if ($process.ExitCode -eq 0 -and (Test-Path -LiteralPath $stageRun -PathType Leaf)) {
            $stage = Get-Content -LiteralPath $stageRun -Raw | ConvertFrom-Json
            $report.stage_status = $stage.status
            $report.hardware_contact = $stage.hardware_contact
            $report.status = if ($stage.status -eq "READY_NO_HARDWARE_CONTACT" -and $stage.hardware_contact -eq 0) {
                "READY_NO_HARDWARE_CONTACT"
            } else {
                "NO_GO_CHECK_STAGE"
            }
        } else {
            $report.status = "NO_GO_CHECK_PROCESS"
        }
    }
}

$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $launchArtifact -Encoding UTF8
if ($report.status -eq "READY_NO_HARDWARE_CONTACT" -or $report.status -eq "STARTED_DETACHED") {
    Write-Output "$($report.status): pid=$($process.Id) artifact=$launchArtifact"
    exit 0
}
throw "Detached custom Mode2 launcher failed: $($report.status); see $launchArtifact"
