#requires -Version 7.0
[CmdletBinding()]
param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $OwnerStartAcknowledged,
    [ValidateRange(60, 3600)]
    [int] $OperatorTimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if (@($CheckOnly.IsPresent, $Execute.IsPresent).Where({ $_ }).Count -ne 1) {
    throw "Choose exactly one of -CheckOnly or -Execute."
}
if ($Execute -and -not $OwnerStartAcknowledged) {
    throw "Execute requires -OwnerStartAcknowledged."
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$dir = Join-Path $root "docs\validation\companion-coordinated-face-recording-comp-req-553-554"
$page = Join-Path $root "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v7\candidate\wb55-browser-parity-attempt-01\index.html"
$machine = Join-Path $dir "MACHINE_READY.json"
$url = "http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html#expression"
$pageSha = "718D564BEBACCBA4AEFD055C29E3B80E8D7CA5C427153C8194C0137158FEA8E6"
$machineSha = "230D343B6376EE216E612108AE34A965700F80275DF6ACC925C112ABB5CA2029"
$note = Join-Path $dir "owner-review.note.txt"
$raw = Join-Path $dir "owner-review.raw.json"
$result = Join-Path $dir "owner-review.json"
$lockPath = Join-Path $dir ".owner-review.prompt-active.lock"

function Get-Hash([string] $Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

$failures = @()
if ((Get-Hash $page) -ne $pageSha) { $failures += "page hash drift" }
if ((Get-Hash $machine) -ne $machineSha) { $failures += "MACHINE_READY hash drift" }
foreach ($path in @($note, $raw, $result, $lockPath)) {
    if (Test-Path $path) { $failures += "owner lifecycle already exists: $path" }
}
if ($CheckOnly) {
    [pscustomobject]@{
        status = if ($failures.Count -eq 0) { "PASS_CHECKONLY_NO_EXECUTE" } else { "NO_GO" }
        failures = $failures
        hardware_contact = 0
        write = 0
        popup = 0
    }
    if ($failures.Count -ne 0) { exit 2 }
    return
}
if ($failures.Count -ne 0) { throw ($failures -join "; ") }

$workflow = $env:AI_WORKFLOW_REPO
if (-not $workflow -or -not (Test-Path (Join-Path $workflow "docs\agent_quickstart.md"))) {
    $workflow = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
}
$response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 8
$servedSha = [Convert]::ToHexString(
    [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($response.Content))
)
if ($response.StatusCode -ne 200 -or $servedSha -ne $pageSha) {
    throw "Exact review page is not reachable."
}

$lock = $null
try {
    $lock = [IO.File]::Open($lockPath, "CreateNew", "ReadWrite", "None")
    Start-Process $url
    $promptOutput = & pwsh -NoProfile -File (Join-Path $workflow "scripts\aiw.ps1") operator-prompt `
        -Title "Companion 动态表情与录音编舞验收" `
        -ProgressText "1/1 动态表情与录音编舞" `
        -ScopeText "仅验收浏览器中的双眼、日常整脸编舞和录音中持续编舞；不接触硬件或 production。" `
        -Message "请先不操作，等待一轮日常编舞：双眼小高光应一起转向，眉毛和嘴形成一次自然回应并回到平静。再上下左右拖动，确认两只眼睛都动且无旧高光残留。然后双击进入录音：右侧输入柱应变化，底下的脸仍继续同样的眼神、眉毛和嘴部编舞，不能冻结；再次双击应只退出录音。任何可见问题请选择失败并写备注。" `
        -ExpectedText "通过表示双眼、日常编舞和录音中持续编舞均无需继续修正；失败会继续迭代。" `
        -ObservationLabel "备注（失败时请写出看到的问题）" `
        -ReviewStyle -Input -Buttons "通过,失败" -OutputPath $note `
        -TimeoutSeconds $OperatorTimeoutSeconds -Json
    $rawText = $promptOutput -join [Environment]::NewLine
    [IO.File]::WriteAllText($raw, $rawText, [Text.UTF8Encoding]::new($false))
    if ($LASTEXITCODE -ne 0) { throw "operator-prompt exit $LASTEXITCODE" }
    $parsed = $rawText | ConvertFrom-Json
    if (@("通过", "失败") -notcontains [string] $parsed.selected) {
        throw "operator-prompt returned no owner verdict: $($parsed.selected)"
    }
    $noteText = if (Test-Path $note) { [IO.File]::ReadAllText($note) } else { "" }
    $record = [ordered]@{
        schema = "companion.comp_req_555.owner_review.v1"
        requirements = @("COMP-REQ-553", "COMP-REQ-554", "COMP-REQ-555")
        status = if ($parsed.selected -eq "通过") {
            "PASS_OWNER_COORDINATED_FACE_RECORDING_ACCEPTED"
        } else {
            "FAIL_OWNER_COORDINATED_FACE_RECORDING_RETURN_TO_ITERATION"
        }
        selected = [string] $parsed.selected
        note = $noteText
        page_sha256 = $pageSha
        machine_ready_sha256 = $machineSha
        url = $url
    }
    [IO.File]::WriteAllText($result, ($record | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
    [pscustomobject] $record
} finally {
    if ($null -ne $lock) { $lock.Dispose() }
    Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}
