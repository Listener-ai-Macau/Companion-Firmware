param(
    [string] $PackagePath,
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [string] $ListenerExe,
    [string] $EvidencePath,
    [string] $OutDir,
    [string] $Port = "SWD",
    [uint32] $Baud = 0,
    [int] $ProbeTimeoutMs = 30000,
    [int] $A1TimeoutMs = 45000,
    [int] $A1Rounds = 6,
    [int] $A2TimeoutMs = 120000,
    [int] $MaxMissingPackets = 0,
    [switch] $SkipWirelessStackProvisioning,
    [switch] $Execute,
    [switch] $WorkflowLockHeld
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$typeRoot = (Resolve-Path $TypeRepoRoot).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $repoRoot ".cache\validation\companion-hardware-acceptance-$stamp"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$outDirResolved = (Resolve-Path -LiteralPath $OutDir).Path

function Resolve-CompanionPackage {
    param([string] $Path)

    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        return (Resolve-Path -LiteralPath $Path).Path
    }

    $packageRoot = Join-Path $repoRoot ".cache\ota_firmware"
    $latest = Get-ChildItem -LiteralPath $packageRoot -Filter "companion-ota-*.zip" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        throw "No Companion OTA package found under $packageRoot. Run tools\package_ota_firmware.ps1 first."
    }
    return $latest.FullName
}

function ConvertTo-CommandLine {
    param(
        [Parameter(Mandatory = $true)][string] $FilePath,
        [string[]] $Arguments = @()
    )

    $parts = @($FilePath) + $Arguments
    return ($parts | ForEach-Object {
        $text = [string] $_
        if ($text -match '[\s"`]' -or $text -eq "") {
            '"' + ($text -replace '"', '\"') + '"'
        } else {
            $text
        }
    }) -join " "
}

function Get-SafeLogName {
    param([Parameter(Mandatory = $true)][string] $Name)
    return (($Name.ToLowerInvariant() -replace '[^a-z0-9_.-]+', '-') -replace '^-|-$', '') + ".log"
}

function Show-OperatorPrompt {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message
    )

    try {
        [System.Media.SystemSounds]::Exclamation.Play()
        [Console]::Beep(880, 220)
    } catch {
        Write-Warning "Could not play operator prompt sound: $($_.Exception.Message)"
    }

    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            $Title,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        ) | Out-Null
    } catch {
        Write-Host ""
        Write-Host "=== $Title ==="
        Write-Host $Message
        Write-Host ""
    }
}

function Invoke-AcceptanceStep {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [Parameter(Mandatory = $true)][string] $FilePath,
        [string[]] $Arguments = @()
    )

    $logPath = Join-Path $outDirResolved (Get-SafeLogName $Name)
    $commandLine = ConvertTo-CommandLine -FilePath $FilePath -Arguments $Arguments
    $started = Get-Date
    $status = "PASS"
    $message = "ok"
    $exitCode = 0

    Write-Host ""
    Write-Host "== $Name =="
    Write-Host $commandLine

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments 2>&1 | Tee-Object -FilePath $logPath
        $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        if ($exitCode -ne 0) {
            throw "$Name failed with exit code $exitCode."
        }
    } catch {
        $status = "FAIL"
        $message = $_.Exception.Message
        throw
    } finally {
        Pop-Location
        $ended = Get-Date
        $script:steps.Add([ordered]@{
            name = $Name
            status = $status
            command = $commandLine
            working_directory = $WorkingDirectory
            exit_code = $exitCode
            log = $logPath
            started_at = $started.ToString("o")
            ended_at = $ended.ToString("o")
            duration_ms = [int64]($ended - $started).TotalMilliseconds
            message = $message
        }) | Out-Null
    }
}

function ConvertTo-HardwareAcceptanceMarkdown {
    param([Parameter(Mandatory = $true)] $Report)

    $lines = @(
        "# Companion Hardware Acceptance",
        "",
        "- Status: $($Report["status"])",
        "- Mode: $($Report["mode"])",
        "- Package: ``$($Report["package_path"])``",
        "- Output dir: ``$($Report["output_dir"])``",
        "- Hardware lock command: ``$($Report["lock_command"])``",
        "",
        "## Evidence",
        "",
        "- A1/A2: ``$($Report["evidence"]["a1_a2"])``",
        "- Type UI: ``$($Report["evidence"]["type_ui"])``",
        "- Wired flash: ``$($Report["evidence"]["wired_flash"])``",
        "- BLE OTA: ``$($Report["evidence"]["ble_ota"])``",
        "- Wireless stack: ``$($Report["evidence"]["wireless_stack"])``",
        "- Manual gate report: ``$($Report["evidence"]["manual_gate_report"])``",
        "",
        "## Steps"
    )
    foreach ($step in @($Report["steps"])) {
        $message = if ($step.Contains("message")) { $step["message"] } else { "" }
        $lines += "- $($step["name"]): $($step["status"]) ($message)"
    }
    if (@($Report["errors"]).Count -gt 0) {
        $lines += ""
        $lines += "## Errors"
        foreach ($errorItem in @($Report["errors"])) {
            $lines += "- $errorItem"
        }
    }
    return $lines
}

$resolvedPackage = Resolve-CompanionPackage -Path $PackagePath
$summaryJson = Join-Path $outDirResolved "companion-hardware-acceptance-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-hardware-acceptance-summary.md"
$a1Dir = Join-Path $outDirResolved "a1-a2"
$bleDir = Join-Path $outDirResolved "ble-ota"
$wiredDir = Join-Path $outDirResolved "wired-flash"
$typeUiDir = Join-Path $outDirResolved "type-ui-manual"
$manualDir = Join-Path $outDirResolved "manual-gate-evidence"
$wirelessDir = Join-Path $outDirResolved "wireless-stack"
$a1Summary = Join-Path $a1Dir "companion-type-a1-a2-summary.json"
$bleSummary = Join-Path $bleDir "companion-ble-ota-summary.json"
$wiredSummary = Join-Path $wiredDir "companion-wired-flash-summary.json"
$typeUiSummary = Join-Path $typeUiDir "companion-type-ui-manual-summary.json"
$manualSummary = Join-Path $manualDir "companion-manual-gate-evidence-summary.json"
$wirelessSummary = Join-Path $wirelessDir "companion-wireless-stack-summary.json"

$aiw = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1"
$lockCommand = "pwsh -NoProfile -File $aiw with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion hardware acceptance`" -Run pwsh -NoProfile -File .\tools\verify_companion_hardware_acceptance.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackage`" -EvidencePath <type-ui-screenshot-or-log>"

$steps = [System.Collections.Generic.List[object]]::new()
$errors = [System.Collections.Generic.List[string]]::new()

$wirelessArgs = @(
    "-NoProfile", "-File", ".\tools\provision_companion_wireless_stack.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-InstallBleStack",
    "-OutDir", $wirelessDir
)
$a1Args = @(
    "-NoProfile", "-File", ".\tools\verify_companion_type_a1_a2.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-TypeRepoRoot", $typeRoot,
    "-OutDir", $a1Dir,
    "-ProbeTimeoutMs", [string]$ProbeTimeoutMs,
    "-A1TimeoutMs", [string]$A1TimeoutMs,
    "-A1Rounds", [string]$A1Rounds,
    "-A2TimeoutMs", [string]$A2TimeoutMs,
    "-MaxMissingPackets", [string]$MaxMissingPackets
)
$bleArgs = @(
    "-NoProfile", "-File", ".\tools\verify_companion_ble_ota.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-PackagePath", $resolvedPackage,
    "-TypeRepoRoot", $typeRoot,
    "-OutDir", $bleDir
)
$wiredArgs = @(
    "-NoProfile", "-File", ".\tools\verify_companion_wired_flash.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-PackagePath", $resolvedPackage,
    "-TypeRepoRoot", $typeRoot,
    "-OutDir", $wiredDir,
    "-Port", $Port
)
$typeUiArgs = @(
    "-NoProfile", "-File", ".\tools\verify_companion_type_ui_manual.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-PackagePath", $resolvedPackage,
    "-TypeRepoRoot", $typeRoot,
    "-OutDir", $typeUiDir
)
if (-not [string]::IsNullOrWhiteSpace($ListenerExe)) {
    $a1Args += @("-ListenerExe", $ListenerExe)
    $bleArgs += @("-ListenerExe", $ListenerExe)
    $wiredArgs += @("-ListenerExe", $ListenerExe)
}
if ($Baud -gt 0) {
    $wiredArgs += @("-Baud", [string]$Baud)
}
if (-not [string]::IsNullOrWhiteSpace($EvidencePath)) {
    $typeUiArgs += @("-EvidencePath", $EvidencePath)
}

$manualArgs = @(
    "-NoProfile", "-File", ".\tools\verify_companion_manual_gate_evidence.ps1",
    "-PackagePath", $resolvedPackage,
    "-A1A2SummaryPath", $a1Summary,
    "-BleOtaEvidencePath", $bleSummary,
    "-WiredFlashEvidencePath", $wiredSummary,
    "-TypeUiEvidencePath", $typeUiSummary,
    "-OutDir", $manualDir
)

if (-not $Execute) {
    $dryRunSteps = @(
        [ordered]@{ name = "ensure CPU2 BLE wireless stack"; status = $(if ($SkipWirelessStackProvisioning) { "SKIPPED" } else { "DRY_RUN" }); message = $(if ($SkipWirelessStackProvisioning) { "skipped by -SkipWirelessStackProvisioning; only use after a PASS provisioning summary exists" } else { "not executed; reads FUS and installs STM32CubeWB BLE full stack before CPU1 BLE apps" }); command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $wirelessArgs; evidence = $wirelessSummary },
        [ordered]@{ name = "real Companion wired flash from same package"; status = "DRY_RUN"; message = "not executed; flashes the same package OTA loader and unified Companion VKA1 app before A1/A2"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $wiredArgs; evidence = $wiredSummary },
        [ordered]@{ name = "real Companion Type A1/A2"; status = "DRY_RUN"; message = "not executed; requires workflow hardware lock"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $a1Args; evidence = $a1Summary },
        [ordered]@{ name = "Type temporary Companion debug page"; status = "DRY_RUN"; message = "not executed; runs against the same unified Companion VKA1 app"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $typeUiArgs; evidence = $typeUiSummary },
        [ordered]@{ name = "real Companion BLE OTA through Type"; status = "DRY_RUN"; message = "not executed; transfers the same package over the STM32WB ST OTA path"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $bleArgs; evidence = $bleSummary },
        [ordered]@{ name = "manual gate evidence verifier"; status = "DRY_RUN"; message = "not executed until all four gate summaries exist"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $manualArgs; evidence = $manualSummary }
    )
    $report = [ordered]@{
        schema = "companion.hardware_acceptance.validation.v1"
        status = "DRY_RUN"
        mode = "dry-run"
        generated_at = (Get-Date).ToString("o")
        repo_root = $repoRoot
        type_repo_root = $typeRoot
        package_path = $resolvedPackage
        output_dir = $outDirResolved
        lock_command = $lockCommand
        evidence = [ordered]@{
            a1_a2 = $a1Summary
            ble_ota = $bleSummary
            wired_flash = $wiredSummary
            type_ui = $typeUiSummary
            wireless_stack = $wirelessSummary
            manual_gate_report = $manualSummary
        }
        steps = $dryRunSteps
        errors = @()
    }
    $report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    ConvertTo-HardwareAcceptanceMarkdown -Report $report | Set-Content -LiteralPath $summaryMd -Encoding UTF8
    Write-Host "DRY-RUN: Companion hardware acceptance runner is ready."
    Write-Host "Package: $resolvedPackage"
    Write-Host "Run with workflow hardware lock:"
    Write-Host "  $lockCommand"
    Write-Host "Summary: $summaryJson"
    exit 0
}

if (-not $WorkflowLockHeld) {
    Write-Host "Use the workflow hardware lock before executing:"
    Write-Host "  $lockCommand"
    throw "Refusing to run Companion hardware acceptance without -WorkflowLockHeld."
}

$startedAt = (Get-Date).ToUniversalTime().ToString("o")
Show-OperatorPrompt `
    -Title "Companion 总体验收即将开始" `
    -Message "请确认 Companion NUCLEO 的 ST-LINK USB、电脑蓝牙、Listener Type 都处于测试状态。点击 OK 后脚本会在当前硬件锁内依次执行：CPU2 BLE wireless stack 预检/安装、有线 SWD 刷入同一个 Companion package、A1/A2 录音链路、Type Companion 页面人工确认、BLE OTA 同包传输，最后汇总证据。A1/A2 和 Type 页面现在都跑在统一 Companion app 上；BLE OTA gate 会继续验证同一个 package 的 STM32WB ST OTA 传输路径。输出目录：$outDirResolved"

try {
    if ($SkipWirelessStackProvisioning) {
        $steps.Add([ordered]@{
            name = "ensure CPU2 BLE wireless stack"
            status = "SKIPPED"
            command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $wirelessArgs
            working_directory = $repoRoot
            exit_code = 0
            log = $null
            started_at = (Get-Date).ToString("o")
            ended_at = (Get-Date).ToString("o")
            duration_ms = 0
            message = "Skipped by -SkipWirelessStackProvisioning; caller must provide prior PASS wireless-stack evidence."
        }) | Out-Null
    } else {
        Invoke-AcceptanceStep -Name "ensure CPU2 BLE wireless stack" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $wirelessArgs
    }
    Invoke-AcceptanceStep -Name "real Companion wired flash from same package" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $wiredArgs
    Invoke-AcceptanceStep -Name "real Companion Type A1/A2" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $a1Args
    Invoke-AcceptanceStep -Name "Type temporary Companion debug page" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $typeUiArgs
    Invoke-AcceptanceStep -Name "real Companion BLE OTA through Type" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $bleArgs
    Invoke-AcceptanceStep -Name "manual gate evidence verifier" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $manualArgs
} catch {
    $errors.Add($_.Exception.Message) | Out-Null
}

$finishedAt = (Get-Date).ToUniversalTime().ToString("o")
$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
$report = [ordered]@{
    schema = "companion.hardware_acceptance.validation.v1"
    status = $status
    mode = "execute"
    started_at_utc = $startedAt
    finished_at_utc = $finishedAt
    repo_root = $repoRoot
    type_repo_root = $typeRoot
    package_path = $resolvedPackage
    output_dir = $outDirResolved
    lock_command = $lockCommand
    evidence = [ordered]@{
        a1_a2 = $a1Summary
        ble_ota = $bleSummary
        wired_flash = $wiredSummary
        type_ui = $typeUiSummary
        wireless_stack = $wirelessSummary
        manual_gate_report = $manualSummary
    }
    steps = @($steps)
    errors = @($errors)
}
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
ConvertTo-HardwareAcceptanceMarkdown -Report $report | Set-Content -LiteralPath $summaryMd -Encoding UTF8

Write-Host "companion_hardware_acceptance_result_json=$($report | ConvertTo-Json -Depth 12 -Compress)"
Write-Host "Summary: $summaryJson"
Write-Host "Markdown: $summaryMd"

if ($status -ne "PASS") {
    throw "Companion hardware acceptance failed. See $summaryJson"
}
