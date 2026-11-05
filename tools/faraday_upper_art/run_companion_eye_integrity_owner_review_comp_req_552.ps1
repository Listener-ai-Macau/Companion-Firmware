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
$dir = Join-Path $root "docs\validation\companion-eye-integrity-comp-req-551"
$page = Join-Path $root "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v7\candidate\wb55-browser-parity-attempt-01\index.html"
$machine = Join-Path $dir "MACHINE_READY.json"
$url = "http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html#expression"
$pageSha = "2CC12F774208F26DE7A5793591E8702A1BD9665F5A33E78B1CE5D3E480596626"
$machineSha = "B63040635412EB4881E98DFF408C45CCBF31D5B8C7300D50AF5F6579DD126A8D"
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
        -Title "Companion 完整眼睛动态验收" `
        -ProgressText "1/1 完整眼睛动态验收" `
        -ScopeText "仅验收浏览器中的眼睛完整性和自然小高光编舞；不接触硬件或 production。" `
        -Message "请观察并拖动眼神：两只眼睛始终应是完整、封闭的黑色轮廓，不能再有下方白色缺口；大块主高光稳定，只有小高光在眼内自然移动；等待一次空闲编舞并做上下左右拖动，确认无残留，闭眼帧无多余亮点。有任何可见问题请选择失败并写备注。" `
        -ExpectedText "通过表示这版不再需要修正眼睛完整性；失败会保留机器 PASS 并继续修。" `
        -ObservationLabel "备注（失败时请写出看到的问题）" `
        -ReviewStyle -Input -Buttons "通过,失败" -OutputPath $note `
        -TimeoutSeconds $OperatorTimeoutSeconds -Json
    $rawText = $promptOutput -join [Environment]::NewLine
    [IO.File]::WriteAllText($raw, $rawText, [Text.UTF8Encoding]::new($false))
    if ($LASTEXITCODE -ne 0) { throw "operator-prompt exit $LASTEXITCODE" }
    $parsed = $rawText | ConvertFrom-Json
    $noteText = if (Test-Path $note) { [IO.File]::ReadAllText($note) } else { "" }
    $record = [ordered]@{
        schema = "companion.comp_req_552.owner_review.v1"
        requirements = @("COMP-REQ-551", "COMP-REQ-552")
        status = if ($parsed.selected -eq "通过") {
            "PASS_OWNER_EYE_INTEGRITY_ACCEPTED"
        } else {
            "FAIL_OWNER_EYE_INTEGRITY_RETURN_TO_ITERATION"
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
