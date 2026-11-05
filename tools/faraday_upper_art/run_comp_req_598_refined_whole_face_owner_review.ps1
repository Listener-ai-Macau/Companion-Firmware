param(
    [int]$OperatorTimeoutSeconds = 3600
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$artifact = Join-Path $repo ".cache\validation\comp-req-597-refined-whole-face-choreography"
$page = Join-Path $artifact "index.html"
$evidence = Join-Path $artifact "verification.json"
$raw = Join-Path $artifact "owner-review-raw.json"
$note = Join-Path $artifact "owner-review-note.txt"
$result = Join-Path $artifact "owner-review-result.json"
$lockPath = Join-Path $artifact "owner-review.lock"
$url = "http://127.0.0.1:4173/.cache/validation/comp-req-597-refined-whole-face-choreography/index.html?candidate=598"
$expectedPage = "FF2841ED2B27C0F4AF599416F16C2E9A12A55B9A81FF7082E4BF7FCCD3AA6820"
$expectedEvidence = "C730FB1D8ABE32CC0586E020325AE8DE97CEB359AB81571788F00DF49A3FB15B"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

if ((Get-Sha256 $page) -ne $expectedPage -or (Get-Sha256 $evidence) -ne $expectedEvidence) {
    throw "The COMP-REQ-598 review artifact changed after machine verification."
}
$response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 8
$served = [Convert]::ToHexString(
    [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($response.Content))
)
if ($response.StatusCode -ne 200 -or $served -ne $expectedPage) {
    throw "The exact COMP-REQ-598 review page is not reachable."
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
        -Title "Companion 精修整脸编舞验收" `
        -ProgressText "1/1 三种代表情绪" `
        -ScopeText "仅验收浏览器中的精修动作语言；不修改正式页面，不接触固件、硬件或 production。" `
        -Message "请分别点击日常平静、好奇倾听、开心雀跃，每种至少观察两次短动作。重点看：眼神只有主高光和小闪点且没有重影；黑色眼球外壳不动；眉毛、脸颊、鼻子和嘴围绕同一情绪一起回应；动作之间有自然长短变化，不像固定短循环，也没有五官被切掉或突然跳动。" `
        -ExpectedText "只有你认为这套编舞已经有精修感、可作为其余表情的设计基准时才选通过；只是看过或仍需修改请选择失败并写明问题。" `
        -ObservationLabel "备注（请写出具体表情和不自然的部位或节奏）" `
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
        schema = "companion.comp_req_598.owner_review.v1"
        requirement = "COMP-REQ-598"
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
