#requires -Version 7.0
<#
.SYNOPSIS
Default-off owner review runner for the COMP-REQ-540/541 browser successor.
#>

[CmdletBinding()]
param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $OwnerStartAcknowledged,
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9A-Fa-f]{64}$")]
    [string] $ExpectedPacketSha256,
    [ValidateRange(60, 3600)]
    [int] $OperatorTimeoutSeconds = 1800,
    [string] $WorkflowRepo = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$modeCount = @($CheckOnly.IsPresent, $Execute.IsPresent).Where({ $_ }).Count
if ($modeCount -ne 1) {
    throw "Default-off: choose exactly one of -CheckOnly or -Execute."
}
if ($Execute -and -not $OwnerStartAcknowledged) {
    throw "Execute requires explicit -OwnerStartAcknowledged."
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$validationRelative = "docs\validation\companion-browser-family-micro-choreography-comp-req-540"
$validationDir = Join-Path $repoRoot $validationRelative
$packetPath = Join-Path $validationDir "owner-review-packet.json"
$ownerResultPath = Join-Path $validationDir "owner-review.json"
$ownerRawPath = Join-Path $validationDir "owner-review.raw.json"
$ownerNotePath = Join-Path $validationDir "owner-review.note.txt"
$ownerFaultPath = Join-Path $validationDir "owner-review-fault.json"
$promptLockPath = Join-Path $validationDir ".owner-review.prompt-active.lock"
$exactUrl = "http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"

function Get-CanonicalSha256 {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [bool] $Text
    )
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($Text) {
        $value = [Text.Encoding]::UTF8.GetString($bytes).Replace("`r`n", "`n")
        $bytes = [Text.Encoding]::UTF8.GetBytes($value)
    }
    $hash = [Security.Cryptography.SHA256]::HashData($bytes)
    return [Convert]::ToHexString($hash)
}

function Test-IsTextPath {
    param([string] $Path)
    return @(".c", ".h", ".html", ".json", ".mjs", ".py", ".ps1") -contains
        [IO.Path]::GetExtension($Path).ToLowerInvariant()
}

function Resolve-WorkflowRoot {
    param([string] $Requested)
    $candidates = @(
        $Requested,
        $env:AI_WORKFLOW_REPO,
        "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    ) | Where-Object { $_ }
    foreach ($candidate in $candidates) {
        $resolved = Resolve-Path -LiteralPath $candidate -ErrorAction SilentlyContinue
        if ($resolved -and
            (Test-Path -LiteralPath (Join-Path $resolved.Path "docs\agent_quickstart.md"))) {
            return $resolved.Path
        }
    }
    throw "Unable to resolve AI_WORKFLOW_REPO."
}

function Get-Readiness {
    $failures = [Collections.Generic.List[string]]::new()
    if (-not (Test-Path -LiteralPath $packetPath -PathType Leaf)) {
        $failures.Add("owner packet is missing")
        return [ordered]@{
            schema = "companion.comp-req-540-owner-review-checkonly.v1"
            status = "NO_GO"
            failures = @($failures)
            counters = [ordered]@{
                process = 0; browser = 0; popup = 0; server = 0
                owner_prompt = 0; hardware = 0; write = 0
                microphone_permission_request = 0
            }
        }
    }
    $packetSha = Get-CanonicalSha256 -Path $packetPath -Text $true
    if ($packetSha -ne $ExpectedPacketSha256.ToUpperInvariant()) {
        $failures.Add("owner packet SHA-256 mismatch")
    }
    $packet = Get-Content -LiteralPath $packetPath -Raw -Encoding UTF8 |
        ConvertFrom-Json -Depth 30
    if ($packet.status -ne "READY_DEFAULT_OFF" -or
        -not [bool]$packet.lifecycle.default_off -or
        [bool]$packet.lifecycle.execute_performed) {
        $failures.Add("packet is not default-off ready")
    }
    if ($packet.url -ne $exactUrl) {
        $failures.Add("4173 URL drifted")
    }
    if (($packet.prompt_contract.buttons -join ",") -ne "通过,失败" -or
        $packet.prompt_contract.title -ne "Companion 表情精修浏览器验收") {
        $failures.Add("canonical Chinese prompt contract drifted")
    }
    if (-not [bool]$packet.prompt_contract.acceptance_rule.pass_means_no_remaining_required_changes -or
        -not [bool]$packet.prompt_contract.acceptance_rule.viewed_only_is_not_pass -or
        -not [bool]$packet.prompt_contract.acceptance_rule.blocking_note_overrides_pass_button -or
        -not ([string]$packet.prompt_contract.expected_text).Contains('仅看过候选不能选择“通过”')) {
        $failures.Add("COMP-REQ-541 acceptance semantics drifted")
    }
    $identities = [Collections.Generic.List[object]]::new()
    foreach ($binding in $packet.bindings) {
        $path = Join-Path $repoRoot ([string]$binding.path).Replace("/", "\")
        $exists = Test-Path -LiteralPath $path -PathType Leaf
        $observed = if ($exists) {
            Get-CanonicalSha256 -Path $path -Text (Test-IsTextPath $path)
        } else {
            ""
        }
        $match = $exists -and
            $observed -eq ([string]$binding.sha256).ToUpperInvariant()
        $identities.Add([ordered]@{
            id = [string]$binding.id
            path = [string]$binding.path
            expected_sha256 = [string]$binding.sha256
            observed_sha256 = $observed
            match = $match
        })
        if (-not $match) {
            $failures.Add("binding drift: $($binding.id)")
        }
    }
    $machineBinding = @($packet.bindings).Where({ $_.id -eq "machine" })
    if ($machineBinding.Count -ne 1) {
        $failures.Add("machine binding is not unique")
    } else {
        $machinePath = Join-Path $repoRoot ([string]$machineBinding[0].path)
        if (Test-Path -LiteralPath $machinePath -PathType Leaf) {
            $machine = Get-Content -LiteralPath $machinePath -Raw -Encoding UTF8 |
                ConvertFrom-Json -Depth 30
            if ($machine.status -ne "MACHINE_READY" -or
                $machine.owner_gate -ne "PENDING" -or
                -not ($machine.checks.PSObject.Properties.Value -notcontains $false)) {
                $failures.Add("MACHINE_READY content drifted")
            }
        }
    }
    foreach ($path in @(
        $ownerResultPath, $ownerRawPath, $ownerNotePath, $promptLockPath
    )) {
        if (Test-Path -LiteralPath $path) {
            $failures.Add("owner lifecycle file already exists: $([IO.Path]::GetFileName($path))")
        }
    }
    return [ordered]@{
        schema = "companion.comp-req-540-owner-review-checkonly.v1"
        status = if ($failures.Count -eq 0) {
            "PASS_CHECKONLY_NO_EXECUTE"
        } else {
            "NO_GO"
        }
        default_off = $true
        execute_performed = $false
        requirements = @("COMP-REQ-540", "COMP-REQ-541")
        url = $exactUrl
        packet_sha256 = $packetSha
        prompt_contract = $packet.prompt_contract
        identities = @($identities)
        failures = @($failures)
        counters = [ordered]@{
            process = 0
            browser = 0
            popup = 0
            server = 0
            owner_prompt = 0
            hardware = 0
            write = 0
            microphone_permission_request = 0
        }
    }
}

if ($CheckOnly) {
    $readiness = Get-Readiness
    $readiness | ConvertTo-Json -Depth 30
    if ($readiness.status -ne "PASS_CHECKONLY_NO_EXECUTE") {
        exit 1
    }
    exit 0
}

$lock = $null
$ownedServer = $null
$promptAttempted = $false
try {
    $readiness = Get-Readiness
    if ($readiness.status -ne "PASS_CHECKONLY_NO_EXECUTE") {
        throw ($readiness.failures -join "; ")
    }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $exactUrl -TimeoutSec 3
    } catch {
        $ownedServer = Start-Process -FilePath "python" -ArgumentList @(
            "-m", "http.server", "4173", "--bind", "127.0.0.1"
        ) -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
        $response = $null
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            Start-Sleep -Milliseconds 250
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri $exactUrl `
                    -TimeoutSec 2
                break
            } catch {
                if ($ownedServer.HasExited) {
                    throw "Owned 4173 server exited before readiness."
                }
            }
        }
        if ($null -eq $response) {
            throw "Owned 4173 server did not become ready."
        }
    }
    if ($response.StatusCode -ne 200) {
        throw "Exact 4173 page is not reachable."
    }
    $pageBinding = @(
        (Get-Content -LiteralPath $packetPath -Raw -Encoding UTF8 |
            ConvertFrom-Json -Depth 30).bindings
    ).Where({ $_.id -eq "page" })
    $served = [Text.Encoding]::UTF8.GetBytes(
        ([string]$response.Content).Replace("`r`n", "`n")
    )
    $servedSha = [Convert]::ToHexString(
        [Security.Cryptography.SHA256]::HashData($served)
    )
    if ($pageBinding.Count -ne 1 -or
        $servedSha -ne ([string]$pageBinding[0].sha256).ToUpperInvariant()) {
        throw "Served page identity drifted."
    }
    $lock = [IO.File]::Open(
        $promptLockPath,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::ReadWrite,
        [IO.FileShare]::None
    )
    $packet = Get-Content -LiteralPath $packetPath -Raw -Encoding UTF8 |
        ConvertFrom-Json -Depth 30
    $null = Start-Process -FilePath $exactUrl -PassThru
    $workflowRoot = Resolve-WorkflowRoot -Requested $WorkflowRepo
    $aiwPath = Join-Path $workflowRoot "scripts\aiw.ps1"
    $promptAttempted = $true
    $promptOutput = & pwsh -NoProfile -File $aiwPath operator-prompt `
        -Title $packet.prompt_contract.title `
        -ProgressText $packet.prompt_contract.progress_text `
        -ScopeText $packet.prompt_contract.scope_text `
        -Message $packet.prompt_contract.message `
        -ExpectedText $packet.prompt_contract.expected_text `
        -ObservationLabel "备注（可留空；失败时请写出可见问题）" `
        -ReviewStyle -Input -Buttons "通过,失败" `
        -OutputPath $ownerNotePath `
        -TimeoutSeconds $OperatorTimeoutSeconds `
        -Json
    $rawText = $promptOutput -join [Environment]::NewLine
    Set-Content -LiteralPath $ownerRawPath -Value $rawText -Encoding utf8NoBOM
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical aiw operator-prompt failed with exit code $LASTEXITCODE."
    }
    $promptResult = $rawText | ConvertFrom-Json
    if (@("通过", "失败") -notcontains [string]$promptResult.selected) {
        throw "Canonical prompt returned an invalid selection."
    }
    $note = if (Test-Path -LiteralPath $ownerNotePath -PathType Leaf) {
        Get-Content -LiteralPath $ownerNotePath -Raw -Encoding UTF8
    } else {
        ""
    }
    $blockingNote = $note -match (
        "必须修改|需要修改|仍需修改|请修改|移除|删除|拒绝|失败|缺陷|" +
        "问题|不通过|changes.required|must.change|blocking"
    )
    $accepted = (
        [string]$promptResult.selected -eq "通过" -and -not $blockingNote
    )
    $ownerRecord = [ordered]@{
        schema = "companion.comp-req-540-owner-review.v1"
        requirements = @("COMP-REQ-540", "COMP-REQ-541")
        selected = [string]$promptResult.selected
        note = $note.TrimEnd()
        blocking_note = $blockingNote
        accepted = $accepted
        status = if ($accepted) {
            "ACCEPTED_OWNER_PASS"
        } else {
            "NOT_ACCEPTED_OWNER_CHANGES_REQUIRED"
        }
        machine_ready_sha256 = [string](
            @($packet.bindings).Where({ $_.id -eq "machine" })[0].sha256
        )
        packet_sha256 = $ExpectedPacketSha256.ToUpperInvariant()
        url = $exactUrl
    }
    $ownerRecord | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $ownerResultPath -Encoding utf8NoBOM
    $ownerRecord
} catch {
    if (-not (Test-Path -LiteralPath $ownerResultPath -PathType Leaf)) {
        [ordered]@{
            schema = "companion.comp-req-540-owner-review-fault.v1"
            status = "FAULT"
            error = $_.Exception.Message
            prompt_attempted = $promptAttempted
            raw_exists = Test-Path -LiteralPath $ownerRawPath
            note_exists = Test-Path -LiteralPath $ownerNotePath
        } | ConvertTo-Json -Depth 8 |
            Set-Content -LiteralPath $ownerFaultPath -Encoding utf8NoBOM
    }
    throw
} finally {
    if ($null -ne $lock) {
        $lock.Dispose()
    }
    if (Test-Path -LiteralPath $promptLockPath) {
        Remove-Item -LiteralPath $promptLockPath -Force
    }
    if ($null -ne $ownedServer) {
        $candidate = Get-Process -Id $ownedServer.Id -ErrorAction SilentlyContinue
        if ($null -ne $candidate) {
            Stop-Process -Id $ownedServer.Id -Force
            $candidate.WaitForExit()
        }
    }
}
