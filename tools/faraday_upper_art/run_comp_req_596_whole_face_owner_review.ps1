param(
    [int]$OperatorTimeoutSeconds = 3600
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$artifact = Join-Path $repo ".cache\validation\comp-req-596-whole-face-choreography"
$page = Join-Path $artifact "index.html"
$evidence = Join-Path $artifact "verification.json"
$raw = Join-Path $artifact "owner-review-raw.json"
$note = Join-Path $artifact "owner-review-note.txt"
$result = Join-Path $artifact "owner-review-result.json"
$lockPath = Join-Path $artifact "owner-review.lock"
$url = "http://127.0.0.1:4173/.cache/validation/comp-req-596-whole-face-choreography/index.html"
$expectedPage = "8BBB058EF6F7C5CA848C7A89804AF43372004FEA819B33B62BAF9B9F0E12C923"
$expectedEvidence = "06E4273D43E9D6E5A0F84AF6E85738FE49A08A5EC720A041F2A72CBDE4EC27B6"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

if ((Get-Sha256 $page) -ne $expectedPage -or (Get-Sha256 $evidence) -ne $expectedEvidence) {
    throw "The COMP-REQ-596 review artifact changed after machine verification."
}
$response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 8
$served = [Convert]::ToHexString(
    [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($response.Content))
)
if ($response.StatusCode -ne 200 -or $served -ne $expectedPage) {
    throw "The exact COMP-REQ-596 review page is not reachable."
}

$workflow = $env:AI_WORKFLOW_REPO
if (-not $workflow -or -not (Test-Path (Join-Path $workflow "docs\agent_quickstart.md"))) {
    $workflow = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
}

$lock = $null
try {
    $lock = [IO.File]::Open($lockPath, "CreateNew", "ReadWrite", "None")
    Start-Process $url
    $promptOutput = & pwsh -NoProfile -File (Join-Path $workflow "scripts\aiw.ps1") operator-prompt `
        -Title "Companion 整张脸编舞验收" `
        -ProgressText "1/1 三种整脸动作语言" `
        -ScopeText "仅验收浏览器中的平静、好奇、开心三套整脸编舞；不修改正式页面，不接触硬件或 production。" `
        -Message "请连续观察至少两轮。确认眼内视线先动，眉毛随后响应，脸颊、鼻子和嘴共同完成动作；黑色眼睛外轮廓不能移动；动作不能像各部件分别乱跳，也不能有残留、切碎或突然闪变。请重点比较平静的轻微幅度、好奇的非对称动作和开心的较强动作。" `
        -ExpectedText "通过表示这三套动作语言已经不需要继续修正，可以据此扩展其余表情；仅仅看过请选择失败并写明问题。" `
        -ObservationLabel "备注（失败时请写出哪套表情、哪个阶段不对）" `
        -ReviewStyle -Input -Buttons "通过,失败" -OutputPath $note `
        -TimeoutSeconds $OperatorTimeoutSeconds -Json
    $rawText = $promptOutput -join [Environment]::NewLine
    [IO.File]::WriteAllText($raw, $rawText, [Text.UTF8Encoding]::new($false))
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical aiw operator-prompt failed with exit code $LASTEXITCODE."
    }
    $parsed = $rawText | ConvertFrom-Json
    $noteText = if (Test-Path $note) { [IO.File]::ReadAllText($note) } else { "" }
    $record = [ordered]@{
        schema = "companion.comp_req_596.owner_review.v1"
        requirement = "COMP-REQ-596"
        page_sha256 = $expectedPage
        evidence_sha256 = $expectedEvidence
        selected = [string]$parsed.selected
        note = $noteText
        accepted = ($parsed.selected -eq "通过" -and [string]::IsNullOrWhiteSpace($noteText))
        recorded_at = [DateTimeOffset]::Now.ToString("o")
    }
    [IO.File]::WriteAllText(
        $result,
        (($record | ConvertTo-Json -Depth 8) + [Environment]::NewLine),
        [Text.UTF8Encoding]::new($false)
    )
} finally {
    if ($lock) { $lock.Dispose() }
    if (Test-Path $lockPath) { Remove-Item -LiteralPath $lockPath -Force }
}
