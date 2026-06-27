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
    "打开 Listener Type 的 Settings > Companion Pendant bring-up，或开发可视化路由 $visualRoute。",
    "确认页面在 Companion section，选择或沿用同一个 Companion package：$resolvedPackage。",
    "确认 Companion 真机可连接，点击 BLE 订阅并看到 PASS。",
    "点击 A1 smoke，等待短链路 PASS，确认 PCM bytes 大于 0 且 missing 为 0。",
    "点击 A2 smoke，等待长窗口 PASS，确认 PCM bytes 大于 0 且 missing 为 0。",
    "确认页面仍显示同包 BLE OTA + 有线刷机入口，并显示 ST-LINK / SWD。",
    "确认页面有总体验收按钮，并能复制 Companion hardware acceptance 命令。"
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
$errors = [System.Collections.Generic.List[string]]::new()
$checks = [System.Collections.Generic.List[string]]::new()
$copiedEvidence = $null

$promptText = @(
    "请现在操作 Listener Type 的 Companion Pendant bring-up 页面：",
    "",
    "1. 打开 Settings > Companion Pendant bring-up，或开发可视化路由 $visualRoute。",
    "2. 使用同一个 Companion package：$resolvedPackage。",
    "3. 确认 Companion 真机可连接。",
    "4. 点击 BLE 订阅，看到 PASS。",
    "5. 点击 A1 smoke，看到 PASS，PCM bytes 大于 0，missing 为 0。",
    "6. 点击 A2 smoke，看到 PASS，PCM bytes 大于 0，missing 为 0。",
    "7. 确认页面仍有 BLE OTA + 有线刷机入口，且有线显示 ST-LINK / SWD。",
    "8. 点击或确认总体验收按钮，确认它能复制 Companion hardware acceptance 命令。",
    "",
    "完成后点击 OK。若需要截图或日志，请保存后用 -EvidencePath 传给本脚本。"
) -join [Environment]::NewLine

[void](Show-OperatorPrompt -Title "Companion Type 页面真机验证" -Message $promptText)

$confirmText = @(
    "请确认刚才 Type Companion 页面三项真机验证都已经通过：",
    "",
    "- BLE 订阅 PASS",
    "- A1 smoke PASS，PCM bytes > 0，missing = 0",
    "- A2 smoke PASS，PCM bytes > 0，missing = 0",
    "- 同一个 package 的 BLE OTA / 有线刷机入口可见",
    "- 有线入口显示 ST-LINK / SWD",
    "- 总体验收入口可见，并能复制 Companion hardware acceptance 命令",
    "",
    "点击 Yes 记录 PASS；点击 No 记录 FAIL。"
) -join [Environment]::NewLine

$dialog = Show-OperatorPrompt `
    -Title "确认 Companion Type 页面结果" `
    -Message $confirmText `
    -Buttons ([System.Windows.Forms.MessageBoxButtons]::YesNo) `
    -Icon ([System.Windows.Forms.MessageBoxIcon]::Question)

if ($dialog -eq [System.Windows.Forms.DialogResult]::Yes) {
    $operatorConfirmed = $true
    $checks.Add("operator confirmed BLE subscription, A1 smoke, A2 smoke, aggregate acceptance command, same-package controls, and ST-LINK / SWD") | Out-Null
} else {
    $errors.Add("operator reported Companion Type UI validation did not pass") | Out-Null
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
