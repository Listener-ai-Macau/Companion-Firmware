#requires -Version 7.0
<#
.SYNOPSIS
Default-off supervisor for the final COMP-REQ-471 browser owner review.

.DESCRIPTION
CheckOnly calls the runner in-process and writes only the matching readiness
artifact. Execute requires explicit owner acknowledgement and an exclusive
supervisor lock before the runner may inspect/start port 4173 or open one prompt.
#>

[CmdletBinding()]
param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $OwnerStartAcknowledged,
    [ValidateRange(60, 3600)]
    [int] $OperatorTimeoutSeconds = 1800,
    [string] $WorkflowRepo = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$modeCount = @($CheckOnly.IsPresent, $Execute.IsPresent).Where({ $_ }).Count
if ($modeCount -ne 1) {
    throw "Default-off: choose exactly one of -CheckOnly or -Execute."
}
if ($Execute -and -not $OwnerStartAcknowledged) {
    throw "Refusing Execute until the owner explicitly starts browser acceptance."
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$runnerPath = Join-Path $PSScriptRoot "run_companion_browser_owner_review_comp_req_471.ps1"
$validationDir = Join-Path $repoRoot "docs\validation\companion-browser-visual-contract-comp-req-471"
$checkOnlyPath = Join-Path $validationDir "owner-review-checkonly.json"
$negativeFixturePath = Join-Path $validationDir "owner-review-negative-fixtures.json"
$negativeResultPath = Join-Path $validationDir "owner-review-negative-fixture-result.json"
$supervisorLockPath = Join-Path $validationDir ".owner-review.supervisor.lock"
$futureExecuteCommand = "pwsh -NoProfile -File .\tools\faraday_upper_art\supervise_companion_browser_owner_review_comp_req_471.ps1 -Execute -OwnerStartAcknowledged"

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

if (-not (Test-Path -LiteralPath $runnerPath -PathType Leaf)) {
    throw "Matching owner-review runner is missing: $runnerPath"
}

if ($CheckOnly) {
    $runnerArgs = @{
        CheckOnly = $true
    }
    if (-not [string]::IsNullOrWhiteSpace($WorkflowRepo)) {
        $runnerArgs.WorkflowRepo = $WorkflowRepo
    }
    $readiness = & $runnerPath @runnerArgs
    if ($null -eq $readiness -or
        $readiness.status -ne "PASS_READY_FOR_OWNER_BROWSER_REVIEW_CHECKONLY_NO_EXECUTE") {
        throw "Runner did not return the expected CheckOnly readiness."
    }
    foreach ($counter in @("process", "browser", "popup", "hardware", "write")) {
        if ([int]$readiness.counters.$counter -ne 0) {
            throw "CheckOnly side-effect counter is not zero: $counter"
        }
    }

    $artifact = [ordered]@{
        schema = "companion.browser-owner-review-checkonly.v1"
        requirement = "COMP-REQ-471"
        status = "PASS_READY_FOR_OWNER_BROWSER_REVIEW_CHECKONLY_NO_EXECUTE"
        mode = "CheckOnly"
        default_off = $true
        execute_performed = $false
        readiness = $readiness
        scripts = [ordered]@{
            runner = [ordered]@{
                path = "tools/faraday_upper_art/run_companion_browser_owner_review_comp_req_471.ps1"
                sha256 = Get-Sha256 -Path $runnerPath
            }
            supervisor = [ordered]@{
                path = "tools/faraday_upper_art/supervise_companion_browser_owner_review_comp_req_471.ps1"
                sha256 = Get-Sha256 -Path $PSCommandPath
            }
        }
        negative_fixture_evidence = [ordered]@{
            fixture_manifest = if (Test-Path -LiteralPath $negativeFixturePath -PathType Leaf) {
                [ordered]@{
                    path = "docs/validation/companion-browser-visual-contract-comp-req-471/owner-review-negative-fixtures.json"
                    sha256 = Get-Sha256 -Path $negativeFixturePath
                }
            } else {
                $null
            }
            result = if (Test-Path -LiteralPath $negativeResultPath -PathType Leaf) {
                [ordered]@{
                    path = "docs/validation/companion-browser-visual-contract-comp-req-471/owner-review-negative-fixture-result.json"
                    sha256 = Get-Sha256 -Path $negativeResultPath
                }
            } else {
                $null
            }
        }
        counters = [ordered]@{
            process = 0
            browser = 0
            popup = 0
            hardware = 0
            write = 0
        }
        evidence_artifact_write_count = 1
        evidence_artifact_write_excluded_from_product_write_counter = $true
        owner_result_written = $false
        exact_future_execute_command = $futureExecuteCommand
    }
    $artifact | ConvertTo-Json -Depth 24 |
        Set-Content -LiteralPath $checkOnlyPath -Encoding utf8NoBOM
    Write-Output "CHECKONLY_PASS=$([System.IO.Path]::GetRelativePath($repoRoot, $checkOnlyPath))"
    return
}

$supervisorLock = $null
$supervisorLockCreated = $false
try {
    $supervisorLock = [System.IO.File]::Open(
        $supervisorLockPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
    $supervisorLockCreated = $true
    $runnerArgs = @{
        Execute = $true
        OwnerStartAcknowledged = $true
        Supervised = $true
        OperatorTimeoutSeconds = $OperatorTimeoutSeconds
    }
    if (-not [string]::IsNullOrWhiteSpace($WorkflowRepo)) {
        $runnerArgs.WorkflowRepo = $WorkflowRepo
    }
    & $runnerPath @runnerArgs
} finally {
    if ($null -ne $supervisorLock) {
        $supervisorLock.Dispose()
    }
    if ($supervisorLockCreated -and
        (Test-Path -LiteralPath $supervisorLockPath -PathType Leaf)) {
        Remove-Item -LiteralPath $supervisorLockPath -Force
    }
}
