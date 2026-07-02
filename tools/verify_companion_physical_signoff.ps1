param(
    [string] $OutDir,
    [string] $EvidenceMarkdown,
    [switch] $Execute,
    [switch] $WorkflowLockHeld,
    [switch] $NoEpaperPanel,
    [string] $NoEpaperNote = "no e-paper panel installed",
    [switch] $NoPopup,
    [switch] $WriteEvidenceOnCancel
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$evidenceMarkdownWasProvided = -not [string]::IsNullOrWhiteSpace($EvidenceMarkdown)
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $repoRoot ".cache\validation\companion-physical-signoff-$stamp"
}
if ([string]::IsNullOrWhiteSpace($EvidenceMarkdown)) {
    $EvidenceMarkdown = Join-Path $repoRoot "docs\validation\companion_pendant_mvp_go_no_go.md"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$outDirResolved = (Resolve-Path -LiteralPath $OutDir).Path
$summaryJson = Join-Path $outDirResolved "companion-physical-signoff-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-physical-signoff-summary.md"
$promptTranscript = Join-Path $outDirResolved "companion-physical-signoff-prompt.md"
$evidenceMarkdownResolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($EvidenceMarkdown)
$devBoardButtonLabel = "NUCLEO-WB55RG SW3/B3 user button (PD1)"
$devBoardButtonInstruction = "开发板阶段请按 NUCLEO-WB55RG 开发板上的 SW3/B3 user button (PD1)。不要按 RESET、ST-LINK reset、BOOT0，或电脑键盘。"
$epaperUnavailableInstruction = "如果本轮开发板没有接真实 e-paper panel，请点 Cancel=N/A，并在说明里写 no e-paper panel；不要把 PBM fallback 当作真实屏幕 PASS。"

function Show-OperatorPrompt {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message,
        [System.Windows.Forms.MessageBoxButtons] $Buttons = [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon] $Icon = [System.Windows.Forms.MessageBoxIcon]::Information
    )

    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Media.SystemSounds]::Exclamation.Play()
        [Console]::Beep(880, 180)
        return [System.Windows.Forms.MessageBox]::Show($Message, $Title, $Buttons, $Icon)
    } catch {
        Write-Host ""
        Write-Host "=== $Title ==="
        Write-Host $Message
        Write-Host ""
        if ($Buttons -eq [System.Windows.Forms.MessageBoxButtons]::YesNoCancel) {
            $answer = Read-Host "输入 Y=通过，N=失败，C=不适用/未安装"
            if ($answer -match '^[Yy]') { return [System.Windows.Forms.DialogResult]::Yes }
            if ($answer -match '^[Cc]') { return [System.Windows.Forms.DialogResult]::Cancel }
            return [System.Windows.Forms.DialogResult]::No
        }
        if ($Buttons -eq [System.Windows.Forms.MessageBoxButtons]::YesNo) {
            $answer = Read-Host "输入 Y=是，N=否"
            if ($answer -match '^[Yy]') { return [System.Windows.Forms.DialogResult]::Yes }
            return [System.Windows.Forms.DialogResult]::No
        }
        return [System.Windows.Forms.DialogResult]::OK
    }
}

function Read-OperatorText {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message,
        [string] $Default = ""
    )

    try {
        Add-Type -AssemblyName Microsoft.VisualBasic
        [System.Media.SystemSounds]::Question.Play()
        [Console]::Beep(660, 160)
        return [Microsoft.VisualBasic.Interaction]::InputBox($Message, $Title, $Default)
    } catch {
        Write-Host ""
        Write-Host "=== $Title ==="
        Write-Host $Message
        return Read-Host "输入"
    }
}

function Convert-DialogToResult {
    param([System.Windows.Forms.DialogResult] $Result)

    if ($Result -eq [System.Windows.Forms.DialogResult]::Yes) { return "PASS" }
    if ($Result -eq [System.Windows.Forms.DialogResult]::Cancel) { return "N/A" }
    return "FAIL"
}

function New-CheckResult {
    param(
        [Parameter(Mandatory = $true)][string] $Id,
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Result,
        [string] $Note = ""
    )

    return [ordered]@{
        id = $Id
        title = $Title
        result = $Result
        note = $Note
    }
}

function Ask-Check {
    param(
        [Parameter(Mandatory = $true)][string] $Id,
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Instruction
    )

    $dialog = Show-OperatorPrompt `
        -Title $Title `
        -Message ($Instruction + [Environment]::NewLine + [Environment]::NewLine + "点击 Yes=真实看到通过；No=失败或没看到；Cancel=硬件未安装/不适用。") `
        -Buttons ([System.Windows.Forms.MessageBoxButtons]::YesNoCancel) `
        -Icon ([System.Windows.Forms.MessageBoxIcon]::Question)
    $result = Convert-DialogToResult -Result $dialog
    $note = ""
    if ($result -ne "PASS") {
        $note = Read-OperatorText -Title "$Title 说明" -Message "请写明原因，例如：屏没接、没有刷新、按钮没反应、显示内容不对。留空也可以。"
    }
    return New-CheckResult -Id $Id -Title $Title -Result $result -Note $note
}

function Read-Measurement {
    param(
        [Parameter(Mandatory = $true)][string] $Id,
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)][string] $Prompt
    )

    $value = Read-OperatorText -Title "功耗测量：$Label" -Message ($Prompt + [Environment]::NewLine + [Environment]::NewLine + "请输入电流 mA，例如 12.4。没有仪表或未测就输入 NA。")
    $numeric = $false
    $number = $null
    if ($value -match '^\s*[0-9]+(\.[0-9]+)?\s*$') {
        $numeric = $true
        $number = [double]$value
    }
    return [ordered]@{
        id = $Id
        label = $Label
        raw = $value
        measured = $numeric
        current_ma = $number
    }
}

$knownMissingHardware = @()
if ($NoEpaperPanel) {
    $knownMissingHardware += [ordered]@{
        id = "epaper_panel"
        status = "not_installed"
        note = $NoEpaperNote
    }
}

function ConvertTo-SignoffMarkdown {
    param([Parameter(Mandatory = $true)] $Summary)

    $lines = @(
        "# Companion Pendant MVP Physical Signoff",
        "",
        "- Status: $($Summary.status)",
        "- Started: $($Summary.started_at)",
        "- Finished: $($Summary.finished_at)",
        "- Operator: $($Summary.operator)",
        "- Output: ``$($Summary.output_dir)``",
        "- Prompt transcript: ``$($Summary.prompt_transcript)``",
        "",
        "## Automated Evidence Already Passed",
        "",
        "- Operator chain: attach the current ``.cache\validation\companion-operator-chain-<timestamp>\companion-operator-chain-summary.json``.",
        "- Recording chain: attach the current flash or SW3 button recording chain JSON that proves non-empty capture, pull, SHA-256, and delete-after-sync; for preservation-only board checks, attach a no-delete existing recording pull artifact.",
        "- Real BLE GATT bench: attach the current ``.cache\validation\companion-v1-real-ble-gatt-<timestamp>\companion-ble-real-bench.json``.",
        "",
        "## Physical Checks",
        "",
        "| Check | Result | Note |",
        "|---|---:|---|"
    )
    foreach ($check in @($Summary.physical_checks)) {
        $lines += "| $($check.title) | $($check.result) | $($check.note) |"
    }
    $lines += ""
    $lines += "## Power Measurements"
    $lines += ""
    $lines += "| State | Current mA | Raw entry |"
    $lines += "|---|---:|---|"
    foreach ($measurement in @($Summary.power_measurements)) {
        $ma = if ($measurement.measured) { "{0:N3}" -f [double]$measurement.current_ma } else { "" }
        $lines += "| $($measurement.label) | $ma | $($measurement.raw) |"
    }
    $lines += ""
    $lines += "## PCB Go/No-Go"
    $lines += ""
    $lines += "- Decision: $($Summary.pcb_decision.decision)"
    $lines += "- Reason: $($Summary.pcb_decision.reason)"
    $lines += "- Human accepted current recommendation: $($Summary.pcb_decision.accepted_current_no_go)"
    $lines += ""
    $lines += "## Notes"
    $lines += ""
    $lines += $Summary.operator_notes
    return $lines
}

$lockCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"Companion final physical signoff`" -Run pwsh -NoProfile -File .\tools\verify_companion_physical_signoff.ps1 -Execute -WorkflowLockHeld"
if ($NoEpaperPanel) {
    $lockCommand += " -NoEpaperPanel -NoEpaperNote `"$NoEpaperNote`""
}
if ($NoPopup) {
    $lockCommand += " -NoPopup"
}

if (-not $Execute) {
    $dryRun = [ordered]@{
        schema = "companion.physical_signoff.v1"
        status = "DRY_RUN"
        generated_at = (Get-Date).ToString("o")
        repo_root = $repoRoot
        output_dir = $outDirResolved
        evidence_markdown = $evidenceMarkdownResolved
        lock_command = $lockCommand
        no_epaper_panel = [bool]$NoEpaperPanel
        no_popup = [bool]$NoPopup
        known_missing_hardware = @($knownMissingHardware)
        checks = @(
            if ($NoEpaperPanel) {
                "real e-paper default/recording/sync-complete/BLE-written cards are pre-recorded as N/A because no panel is installed"
            } else {
                "real e-paper default/recording/sync-complete/BLE-written cards; if no panel is connected, record N/A instead of PASS"
            }
            "real dev-board button capture affordance using $devBoardButtonLabel",
            "power measurements for boot/idle, advertising, connected idle, recording, e-paper refresh, chunk transfer, charge/external-power",
            "PCB go/no-go decision"
        )
    }
    $dryRun | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    Write-Host "DRY-RUN: Companion physical signoff guide is ready."
    Write-Host "Run under workflow hardware lock:"
    Write-Host "  $lockCommand"
    Write-Host "Summary: $summaryJson"
    exit 0
}

if (-not $WorkflowLockHeld -and -not $NoPopup) {
    Write-Host "Use the workflow hardware lock before executing:"
    Write-Host "  $lockCommand"
    throw "Refusing to run physical signoff without -WorkflowLockHeld."
}
if (-not $WorkflowLockHeld -and $NoPopup) {
    Write-Host "NO-POPUP: no human prompt or hardware action will run, so this partial artifact does not take a workflow lock."
}

$startedAt = (Get-Date).ToString("o")
if ($NoPopup) {
    $physicalChecks = @()
    $epaperCheckTitles = @(
        @{ Id = "epaper_default"; Title = "e-paper 默认卡" },
        @{ Id = "epaper_recording"; Title = "e-paper 录音状态卡" },
        @{ Id = "epaper_sync_complete"; Title = "e-paper 同步完成卡" },
        @{ Id = "epaper_ble_written_card"; Title = "BLE 写入短句卡" }
    )
    foreach ($check in $epaperCheckTitles) {
        if ($NoEpaperPanel) {
            $physicalChecks += New-CheckResult -Id $check.Id -Title $check.Title -Result "N/A" -Note $NoEpaperNote
        } else {
            $physicalChecks += New-CheckResult -Id $check.Id -Title $check.Title -Result "PENDING_HUMAN" -Note "not collected: -NoPopup"
        }
    }
    $physicalChecks += New-CheckResult -Id "button_capture_affordance" -Title "真实按钮 capture affordance" -Result "PENDING_HUMAN" -Note "not collected: -NoPopup"

    $powerMeasurements = @(
        [ordered]@{ id = "boot_idle"; label = "boot/idle"; raw = "not collected: -NoPopup"; measured = $false; current_ma = $null },
        [ordered]@{ id = "advertising"; label = "BLE advertising"; raw = "not collected: -NoPopup"; measured = $false; current_ma = $null },
        [ordered]@{ id = "connected_idle"; label = "connected idle"; raw = "not collected: -NoPopup"; measured = $false; current_ma = $null },
        [ordered]@{ id = "recording"; label = "recording"; raw = "not collected: -NoPopup"; measured = $false; current_ma = $null },
        [ordered]@{ id = "epaper_refresh"; label = "e-paper refresh"; raw = $(if ($NoEpaperPanel) { $NoEpaperNote } else { "not collected: -NoPopup" }); measured = $false; current_ma = $null },
        [ordered]@{ id = "chunk_transfer"; label = "BLE chunk transfer"; raw = "not collected: -NoPopup"; measured = $false; current_ma = $null },
        [ordered]@{ id = "charge_external_power"; label = "charge/external-power"; raw = "not collected: -NoPopup"; measured = $false; current_ma = $null }
    )
    $finishedAt = (Get-Date).ToString("o")
    $summary = [ordered]@{
        schema = "companion.physical_signoff.v1"
        status = "PENDING_HUMAN"
        artifact_mode = "NO_POPUP_PARTIAL"
        no_popup = $true
        started_at = $startedAt
        finished_at = $finishedAt
        operator = "not_collected_no_popup"
        repo_root = $repoRoot
        output_dir = $outDirResolved
        summary_json = $summaryJson
        summary_markdown = $summaryMd
        evidence_markdown = $evidenceMarkdownResolved
        prompt_transcript = $promptTranscript
        known_missing_hardware = @($knownMissingHardware)
        physical_checks = @($physicalChecks)
        power_measurements = @($powerMeasurements)
        physical_all_pass = $false
        power_all_measured = $false
        pcb_decision = [ordered]@{
            accepted_current_no_go = $false
            decision = "pending_operator_signoff"
            reason = "NoPopup mode intentionally did not ask for a human PCB decision."
        }
        operator_notes = "Partial artifact generated with -NoPopup; no desktop prompts, operator observations, or power measurements were collected."
    }
    $writeEvidenceMarkdown = $evidenceMarkdownWasProvided
    $summary["evidence_markdown_written"] = $writeEvidenceMarkdown

    $transcriptLines = @(
        "# Companion Physical Signoff Prompt Transcript",
        "",
        "- Started: $startedAt",
        "- Finished: $finishedAt",
        "- Operator: not_collected_no_popup",
        "- Mode: NO_POPUP_PARTIAL",
        "",
        "No desktop prompts were shown because -NoPopup was specified."
    )
    $transcriptLines | Set-Content -LiteralPath $promptTranscript -Encoding UTF8
    $md = ConvertTo-SignoffMarkdown -Summary ([pscustomobject]$summary)
    $md | Set-Content -LiteralPath $summaryMd -Encoding UTF8
    if ($writeEvidenceMarkdown) {
        $md | Set-Content -LiteralPath $evidenceMarkdownResolved -Encoding UTF8
    }
    $summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryJson -Encoding UTF8

    Write-Host "companion_physical_signoff_result_json=$($summary | ConvertTo-Json -Depth 10 -Compress)"
    Write-Host "NO-POPUP: Companion physical signoff partial artifact written; status=PENDING_HUMAN."
    Write-Host "Summary: $summaryJson"
    Write-Host "Markdown: $summaryMd"
    if ($writeEvidenceMarkdown) {
        Write-Host "Evidence: $evidenceMarkdownResolved"
    } else {
        Write-Host "Evidence: not updated because -EvidenceMarkdown was not explicitly provided."
    }
    exit 0
}

$operator = Read-OperatorText -Title "Companion 最终物理验收" -Message "请输入验收人名字或缩写，用于 evidence 记录。" -Default "Billy"

$intro = @(
    "接下来会逐步确认 Companion pendant 的最后物理链路。",
    "",
    "你需要真实观察或测量：",
    "1. e-paper 默认卡、录音卡、同步完成卡、BLE 写入短句卡。",
    "2. 开发板阶段按 $devBoardButtonLabel 后是否有 capture/录音 affordance。",
    "3. 用电流表或功耗仪记录各状态电流。",
    "4. 接受或推翻当前 PCB 暂不 go 的建议。",
    "",
    $devBoardButtonInstruction,
    $epaperUnavailableInstruction,
    $(if ($NoEpaperPanel) { "本次已指定 -NoEpaperPanel：e-paper 相关观察和 e-paper refresh 电流会自动记录为 N/A，说明：$NoEpaperNote。" }),
    "没有电流表或本轮未测量时请输入 NA 并说明原因；不要填 0 代替未测量。",
    "",
    "每一步请按真实结果点 Yes / No / Cancel。Cancel 表示硬件未安装或本轮不适用。"
) -join [Environment]::NewLine
[void](Show-OperatorPrompt -Title "开始 Companion 物理验收" -Message $intro)

$physicalChecks = @()
$epaperChecks = @(
    @{ Id = "epaper_default"; Title = "e-paper 默认卡"; Instruction = "请看真实目标 e-paper：上电或空闲状态能看到默认/固定卡片，且内容完整、没有明显花屏或错位。$epaperUnavailableInstruction" },
    @{ Id = "epaper_recording"; Title = "e-paper 录音状态卡"; Instruction = "让设备进入录音状态，观察真实 e-paper 是否显示录音/捕获状态卡，状态变化清楚。$epaperUnavailableInstruction" },
    @{ Id = "epaper_sync_complete"; Title = "e-paper 同步完成卡"; Instruction = "让设备完成同步/传输后，观察真实 e-paper 是否显示同步完成状态卡。$epaperUnavailableInstruction" },
    @{ Id = "epaper_ble_written_card"; Title = "BLE 写入短句卡"; Instruction = "确认 BLE 写入的短句或 fixture payload 能显示在真实 e-paper 上；期望短句类似 1234567 chain verified 或本轮测试短句。$epaperUnavailableInstruction" }
)
foreach ($check in $epaperChecks) {
    if ($NoEpaperPanel) {
        $physicalChecks += New-CheckResult -Id $check.Id -Title $check.Title -Result "N/A" -Note $NoEpaperNote
    } else {
        $physicalChecks += Ask-Check -Id $check.Id -Title $check.Title -Instruction $check.Instruction
    }
}
$physicalChecks += Ask-Check -Id "button_capture_affordance" -Title "真实按钮 capture affordance" -Instruction "$devBoardButtonInstruction 观察设备是否出现明确的录音/capture affordance，例如显示切换、状态反馈、LED/日志/主机状态变化。"

$powerMeasurements = @()
$powerMeasurements += Read-Measurement -Id "boot_idle" -Label "boot/idle" -Prompt "设备启动完成并处于空闲状态时，读取电流。没有仪表就输入 NA。"
$powerMeasurements += Read-Measurement -Id "advertising" -Label "BLE advertising" -Prompt "设备未连接、正在 BLE 广播时，读取电流。没有仪表就输入 NA。"
$powerMeasurements += Read-Measurement -Id "connected_idle" -Label "connected idle" -Prompt "BLE 已连接但没有录音/刷新/传输时，读取电流。没有仪表就输入 NA。"
$powerMeasurements += Read-Measurement -Id "recording" -Label "recording" -Prompt "正在录音并写入本地存储时，读取电流。没有仪表就输入 NA。"
if ($NoEpaperPanel) {
    $powerMeasurements += [ordered]@{
        id = "epaper_refresh"
        label = "e-paper refresh"
        raw = $NoEpaperNote
        measured = $false
        current_ma = $null
    }
} else {
    $powerMeasurements += Read-Measurement -Id "epaper_refresh" -Label "e-paper refresh" -Prompt "e-paper 正在刷新时，读取峰值或稳定读数；如只能读峰值，请在备注说明。没有屏幕或仪表就输入 NA。"
}
$powerMeasurements += Read-Measurement -Id "chunk_transfer" -Label "BLE chunk transfer" -Prompt "BLE 正在拉取录音 chunk 时，读取电流。没有仪表就输入 NA。"
$powerMeasurements += Read-Measurement -Id "charge_external_power" -Label "charge/external-power" -Prompt "外部供电/充电状态下，读取电流；没有充电/电源测量硬件就输入 NA 并说明原因。"

$acceptNoGo = Show-OperatorPrompt `
    -Title "PCB Go/No-Go 决策" `
    -Message "当前自动证据建议：继续 dev-board 迭代，暂不进入第一版 pendant PCB。`n`n点击 Yes 表示接受这个 no-go-for-PCB 建议；点击 No 表示你要推翻或修改这个决策。" `
    -Buttons ([System.Windows.Forms.MessageBoxButtons]::YesNo) `
    -Icon ([System.Windows.Forms.MessageBoxIcon]::Question)

if ($acceptNoGo -eq [System.Windows.Forms.DialogResult]::Yes) {
    $decision = "continue_dev_board_iteration_before_first_pendant_pcb"
    $decisionReason = "Operator accepted the current no-go-for-PCB recommendation after physical signoff prompts."
    $acceptedCurrentNoGo = $true
} else {
    $decision = Read-OperatorText -Title "请输入新的 PCB 决策" -Message "请输入 GO / NO-GO / ITERATE / CHANGE_PARTS，并补充一句原因。"
    $decisionReason = Read-OperatorText -Title "PCB 决策原因" -Message "请写明为什么推翻或修改当前 no-go-for-PCB 建议。"
    $acceptedCurrentNoGo = $false
}

$operatorNotes = Read-OperatorText -Title "补充说明" -Message "可选：记录照片/视频路径、仪表型号、异常现象、哪些硬件未安装。留空也可以。"
$finalConfirm = Show-OperatorPrompt `
    -Title "提交 Companion 物理验收 evidence" `
    -Message "请确认：刚才填写的是你真实看到和测到的结果。点击 Yes 会写入 JSON/Markdown evidence；点击 No 会写入取消状态。" `
    -Buttons ([System.Windows.Forms.MessageBoxButtons]::YesNo) `
    -Icon ([System.Windows.Forms.MessageBoxIcon]::Warning)

$allPhysicalPass = $true
foreach ($check in $physicalChecks) {
    if ($check.result -ne "PASS") { $allPhysicalPass = $false }
}
$allPowerMeasured = $true
foreach ($measurement in $powerMeasurements) {
    if (-not $measurement.measured) { $allPowerMeasured = $false }
}
$status = "PASS"
if ($finalConfirm -ne [System.Windows.Forms.DialogResult]::Yes) {
    $status = "CANCELLED"
} elseif (-not $allPhysicalPass -or -not $allPowerMeasured) {
    $status = "PENDING_HUMAN"
}

$finishedAt = (Get-Date).ToString("o")
$summary = [ordered]@{
    schema = "companion.physical_signoff.v1"
    status = $status
    artifact_mode = "INTERACTIVE"
    no_popup = $false
    started_at = $startedAt
    finished_at = $finishedAt
    operator = $operator
    repo_root = $repoRoot
    output_dir = $outDirResolved
    summary_json = $summaryJson
    summary_markdown = $summaryMd
    evidence_markdown = $evidenceMarkdownResolved
    prompt_transcript = $promptTranscript
    known_missing_hardware = @($knownMissingHardware)
    physical_checks = @($physicalChecks)
    power_measurements = @($powerMeasurements)
    physical_all_pass = $allPhysicalPass
    power_all_measured = $allPowerMeasured
    pcb_decision = [ordered]@{
        accepted_current_no_go = $acceptedCurrentNoGo
        decision = $decision
        reason = $decisionReason
    }
    operator_notes = $operatorNotes
}
$writeEvidenceMarkdown = $true
if ($status -eq "CANCELLED" -and -not $WriteEvidenceOnCancel) {
    $writeEvidenceMarkdown = $false
}
$summary["evidence_markdown_written"] = $writeEvidenceMarkdown

$transcriptLines = @(
    "# Companion Physical Signoff Prompt Transcript",
    "",
    "- Started: $startedAt",
    "- Finished: $finishedAt",
    "- Operator: $operator",
    "- Final dialog: $finalConfirm",
    "",
    "## Intro Prompt",
    "",
    $intro
)
$transcriptLines | Set-Content -LiteralPath $promptTranscript -Encoding UTF8
$summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
$md = ConvertTo-SignoffMarkdown -Summary ([pscustomobject]$summary)
$md | Set-Content -LiteralPath $summaryMd -Encoding UTF8
if ($writeEvidenceMarkdown) {
    $md | Set-Content -LiteralPath $evidenceMarkdownResolved -Encoding UTF8
}

Write-Host "companion_physical_signoff_result_json=$($summary | ConvertTo-Json -Depth 10 -Compress)"
Write-Host "Summary: $summaryJson"
Write-Host "Markdown: $summaryMd"
if ($writeEvidenceMarkdown) {
    Write-Host "Evidence: $evidenceMarkdownResolved"
} else {
    Write-Host "Evidence: not updated because status=CANCELLED; pass -WriteEvidenceOnCancel to override."
}

if ($status -eq "CANCELLED") {
    throw "Companion physical signoff was cancelled by operator. See $summaryJson"
}

if ($status -ne "PASS") {
    Write-Warning "Companion physical signoff is not complete: status=$status. Evidence was recorded, but workflow should remain waiting."
}
