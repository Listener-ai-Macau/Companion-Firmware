param(
    [string] $PackagePath,
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [string] $EvidencePath,
    [string] $OutDir,
    [switch] $Execute,
    [switch] $WorkflowLockHeld
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$typeRoot = (Resolve-Path $TypeRepoRoot).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $repoRoot ".cache\validation\companion-type-ui-manual-$stamp"
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

function Show-OperatorPrompt {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message,
        [System.Windows.Forms.MessageBoxButtons] $Buttons = [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon] $Icon = [System.Windows.Forms.MessageBoxIcon]::Information
    )

    try {
        [System.Media.SystemSounds]::Exclamation.Play()
        [Console]::Beep(880, 220)
    } catch {
        Write-Warning "Could not play operator prompt sound: $($_.Exception.Message)"
    }

    try {
        Add-Type -AssemblyName System.Windows.Forms
        return [System.Windows.Forms.MessageBox]::Show($Message, $Title, $Buttons, $Icon)
    } catch {
        Write-Host ""
        Write-Host "=== $Title ==="
        Write-Host $Message
        Write-Host ""
        if ($Buttons -eq [System.Windows.Forms.MessageBoxButtons]::YesNo) {
            $answer = Read-Host "输入 Y 表示通过，输入 N 表示失败"
            if ($answer -match '^[Yy]') { return [System.Windows.Forms.DialogResult]::Yes }
            return [System.Windows.Forms.DialogResult]::No
        }
        return [System.Windows.Forms.DialogResult]::OK
    }
}

function Read-OperatorFailureNote {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message
    )

    try {
        [System.Media.SystemSounds]::Exclamation.Play()
        [Console]::Beep(660, 220)
    } catch {
        Write-Warning "Could not play operator prompt sound: $($_.Exception.Message)"
    }

    try {
        Add-Type -AssemblyName Microsoft.VisualBasic
        return [Microsoft.VisualBasic.Interaction]::InputBox($Message, $Title, "")
    } catch {
        Write-Host ""
        Write-Host "=== $Title ==="
        Write-Host $Message
        return Read-Host "没通过的地方"
    }
}

function Copy-ManualEvidence {
    param([string] $Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $item = Get-Item -LiteralPath $resolved
    if ($item.Length -le 0) {
        throw "Type UI evidence file is empty: $resolved"
    }
    $dest = Join-Path $outDirResolved ("type-ui-evidence-" + $item.Name)
    Copy-Item -LiteralPath $resolved -Destination $dest -Force
    return (Resolve-Path -LiteralPath $dest).Path
}

function ConvertTo-TypeUiMarkdown {
    param([Parameter(Mandatory = $true)] $Summary)

    $lines = @(
        "# Companion Type UI Manual Validation",
        "",
        "- Status: $($Summary["status"])",
        "- Mode: $($Summary["mode"])",
        "- Package: ``$($Summary["package_path"])``",
        "- Type repo: ``$($Summary["type_repo_root"])``",
        "- Visual route: ``$($Summary["visual_route"])``",
        "- Operator confirmed: $($Summary["operator_confirmed"])",
        "- Prompt transcript: ``$($Summary["prompt_transcript"])``"
    )
    if ($Summary.Contains("operator_failure_note") -and $Summary["operator_failure_note"]) {
        $lines += "- Operator failure note: $($Summary["operator_failure_note"])"
    }
    if ($Summary["evidence_path"]) {
        $lines += "- Original evidence: ``$($Summary["evidence_path"])``"
    }
    if ($Summary["copied_evidence_path"]) {
        $lines += "- Copied evidence: ``$($Summary["copied_evidence_path"])``"
    }
    $lines += ""
    $lines += "## Required Actions"
    foreach ($action in @($Summary["required_actions"])) {
        $lines += "- $action"
    }
    foreach ($check in @($Summary["checks"])) {
        $lines += "- PASS: $check"
    }
    foreach ($errorItem in @($Summary["errors"])) {
        $lines += "- FAIL: $errorItem"
    }
    return $lines
}

$resolvedPackage = Resolve-CompanionPackage -Path $PackagePath
$summaryJson = Join-Path $outDirResolved "companion-type-ui-manual-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-type-ui-manual-summary.md"
$promptTranscript = Join-Path $outDirResolved "companion-type-ui-manual-prompt.md"
$visualRoute = "http://127.0.0.1:<vite-port>/?visual=settings-companion&theme=dark"
$lockCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion Type UI validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_type_ui_manual.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackage`" -EvidencePath <screenshot-or-log>"
$requiredActions = @(
    "打开 Listener Type 的 Companion 测试页面。",
    "确认 Companion 真机可连接。",
    "点击 BLE 订阅测试并看到绿色 PASS。",
    "点击 A1 短语音测试并看到绿色 PASS。",
    "点击 A2 长语音测试并看到绿色 PASS。",
    "确认页面显示蓝牙升级、有线刷机和总体验收入口。"
)

if (-not $Execute) {
    $summary = [ordered]@{
        schema = "companion.type_ui_manual.validation.v1"
        status = "DRY_RUN"
        mode = "dry-run"
        generated_at = (Get-Date).ToString("o")
        repo_root = $repoRoot
        type_repo_root = $typeRoot
        package_path = $resolvedPackage
        visual_route = $visualRoute
        lock_command = $lockCommand
        required_actions = @($requiredActions)
        operator_confirmed = $false
        evidence_path = $EvidencePath
        copied_evidence_path = $null
        operator_failure_note = ""
        prompt_transcript = $promptTranscript
        checks = @("manual UI wrapper is ready; execute requires workflow hardware lock and Chinese audible prompts")
        errors = @()
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    ConvertTo-TypeUiMarkdown -Summary $summary | Set-Content -LiteralPath $summaryMd -Encoding UTF8
    Write-Host "DRY-RUN: Companion Type UI manual validation is ready."
    Write-Host "Package: $resolvedPackage"
    Write-Host "TypeRepoRoot: $typeRoot"
    Write-Host "Run with workflow hardware lock:"
    Write-Host "  $lockCommand"
    Write-Host "Summary: $summaryJson"
    exit 0
}

if (-not $WorkflowLockHeld) {
    Write-Host "Use the workflow hardware lock before executing:"
    Write-Host "  $lockCommand"
    throw "Refusing to run Companion Type UI manual validation without -WorkflowLockHeld."
}

$startedAt = (Get-Date).ToUniversalTime().ToString("o")
$operatorConfirmed = $false
$operatorFailureNote = ""
$errors = [System.Collections.Generic.List[string]]::new()
$checks = [System.Collections.Generic.List[string]]::new()
$copiedEvidence = $null

$promptText = @(
    "请在 Listener Type 的 Companion 测试页面完成这几步：",
    "",
    "1. 确认页面能看到 Companion 设备，并且可以连接。",
    "2. 点击 BLE 订阅测试，看到绿色 PASS。",
    "3. 点击 A1 短语音测试，看到绿色 PASS。",
    "4. 点击 A2 长语音测试，看到绿色 PASS。",
    "5. 确认页面里能看到蓝牙升级和有线刷机入口。",
    "6. 确认有总体验收入口。",
    "",
    "全部完成后点击 OK。遇到红色错误、找不到设备或找不到入口，就先别点 OK，直接告诉 Codex。"
) -join [Environment]::NewLine

[void](Show-OperatorPrompt -Title "Companion Type 页面真机验证" -Message $promptText)

$confirmText = @(
    "请按你刚才看到的真实页面结果确认：",
    "",
    "- BLE 订阅是绿色 PASS",
    "- A1 短语音测试是绿色 PASS",
    "- A2 长语音测试是绿色 PASS",
    "- 蓝牙升级和有线刷机入口都能看到",
    "- 总体验收入口能看到",
    "",
    "点击 Yes 表示这轮真实验收通过；点击 No 表示没通过，需要继续修。"
) -join [Environment]::NewLine

$dialog = Show-OperatorPrompt `
    -Title "确认 Companion Type 页面结果" `
    -Message $confirmText `
    -Buttons ([System.Windows.Forms.MessageBoxButtons]::YesNo) `
    -Icon ([System.Windows.Forms.MessageBoxIcon]::Question)

if ($dialog -eq [System.Windows.Forms.DialogResult]::Yes) {
    $operatorConfirmed = $true
    $checks.Add("operator confirmed BLE subscription, A1 smoke, A2 smoke, OTA/wired entries, and aggregate acceptance entry") | Out-Null
} else {
    $operatorFailureNote = Read-OperatorFailureNote `
        -Title "哪一步没过？" `
        -Message "请用一句话写下没通过的地方，例如：找不到 Companion、BLE 订阅红色错误、A1 没有 PASS、A2 没有 PASS、没看到升级入口。留空也可以。"
    if ([string]::IsNullOrWhiteSpace($operatorFailureNote)) {
        $errors.Add("operator reported Companion Type UI validation did not pass") | Out-Null
    } else {
        $errors.Add("operator reported Companion Type UI validation did not pass: $operatorFailureNote") | Out-Null
    }
}

try {
    $copiedEvidence = Copy-ManualEvidence -Path $EvidencePath
    if ($copiedEvidence) {
        $checks.Add("operator evidence copied to $copiedEvidence") | Out-Null
    } else {
        $checks.Add("prompt transcript is the retained manual UI evidence artifact") | Out-Null
    }
} catch {
    $errors.Add($_.Exception.Message) | Out-Null
}

$finishedAt = (Get-Date).ToUniversalTime().ToString("o")
$promptLines = @(
    "# Companion Type UI Prompt Transcript",
    "",
    "- Started UTC: $startedAt",
    "- Finished UTC: $finishedAt",
    "- Package: ``$resolvedPackage``",
    "- Operator confirmed: $operatorConfirmed",
    "- Operator failure note: $operatorFailureNote",
    "",
    "## Prompt",
    "",
    $promptText,
    "",
    "## Confirmation",
    "",
    $confirmText,
    "",
    "- Dialog result: $dialog"
)
$promptLines | Set-Content -LiteralPath $promptTranscript -Encoding UTF8

$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
$summary = [ordered]@{
    schema = "companion.type_ui_manual.validation.v1"
    status = $status
    mode = "execute"
    started_at_utc = $startedAt
    finished_at_utc = $finishedAt
    repo_root = $repoRoot
    type_repo_root = $typeRoot
    package_path = $resolvedPackage
    visual_route = $visualRoute
    required_actions = @($requiredActions)
    operator_confirmed = $operatorConfirmed
    operator_failure_note = $operatorFailureNote
    evidence_path = $EvidencePath
    copied_evidence_path = $copiedEvidence
    prompt_transcript = $promptTranscript
    checks = @($checks)
    errors = @($errors)
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
ConvertTo-TypeUiMarkdown -Summary $summary | Set-Content -LiteralPath $summaryMd -Encoding UTF8

Write-Host "companion_type_ui_manual_result_json=$($summary | ConvertTo-Json -Depth 8 -Compress)"
Write-Host "Summary: $summaryJson"
Write-Host "Markdown: $summaryMd"

if ($status -ne "PASS") {
    throw "Companion Type UI manual validation failed. See $summaryJson"
}
