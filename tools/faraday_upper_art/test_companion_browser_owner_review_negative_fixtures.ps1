#requires -Version 7.0
<#
.SYNOPSIS
Runs filesystem-only fail-closed fixtures for COMP-REQ-471 owner-review readiness.
#>

[CmdletBinding()]
param(
    [string] $FixtureManifest = "docs\validation\companion-browser-visual-contract-comp-req-471\owner-review-negative-fixtures.json",
    [string] $OutputPath = "docs\validation\companion-browser-visual-contract-comp-req-471\owner-review-negative-fixture-result.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$runnerPath = Join-Path $PSScriptRoot "run_companion_browser_owner_review_comp_req_471.ps1"
$fixturePath = if ([System.IO.Path]::IsPathRooted($FixtureManifest)) {
    $FixtureManifest
} else {
    Join-Path $repoRoot $FixtureManifest
}
$resultPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
} else {
    Join-Path $repoRoot $OutputPath
}
$ownerArtifactPaths = @(
    (Join-Path $repoRoot "docs\validation\companion-browser-visual-contract-comp-req-471\owner-review.json"),
    (Join-Path $repoRoot "docs\validation\companion-browser-visual-contract-comp-req-471\owner-review.raw.json"),
    (Join-Path $repoRoot "docs\validation\companion-browser-visual-contract-comp-req-471\owner-review.note.txt")
)

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

foreach ($path in @($runnerPath, $fixturePath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required negative-fixture input is missing: $path"
    }
}
foreach ($path in $ownerArtifactPaths) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        throw "Negative fixtures refuse to run after an owner result exists: $path"
    }
}

$manifest = Get-Content -LiteralPath $fixturePath -Raw -Encoding UTF8 |
    ConvertFrom-Json
$results = [System.Collections.Generic.List[object]]::new()
$allPassed = $true
foreach ($fixture in @($manifest.fixtures)) {
    $returnedReadiness = $null
    $observedError = ""
    try {
        $returnedReadiness = & $runnerPath -CheckOnly `
            -FixturePath $fixturePath `
            -FixtureId ([string]$fixture.id)
    } catch {
        $observedError = $_.Exception.Message
    }
    $failedClosed = $null -eq $returnedReadiness -and
        -not [string]::IsNullOrWhiteSpace($observedError)
    $expectedErrorObserved = $observedError.Contains([string]$fixture.expected_error)
    $passed = $failedClosed -and $expectedErrorObserved
    if (-not $passed) {
        $allPassed = $false
    }
    $results.Add([ordered]@{
        id = [string]$fixture.id
        expected_error = [string]$fixture.expected_error
        observed_error = $observedError
        failed_closed = $failedClosed
        expected_error_observed = $expectedErrorObserved
        pass = $passed
    })
}

foreach ($path in $ownerArtifactPaths) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        throw "Negative fixture created a forbidden owner result: $path"
    }
}

$result = [ordered]@{
    schema = "companion.browser-owner-review-negative-fixture-result.v1"
    requirement = "COMP-REQ-471"
    status = if ($allPassed) {
        "PASS_ALL_OWNER_REVIEW_READINESS_NEGATIVES_FAIL_CLOSED"
    } else {
        "NO_GO_NEGATIVE_FIXTURE_DID_NOT_FAIL_CLOSED"
    }
    fixture_manifest = [ordered]@{
        path = [System.IO.Path]::GetRelativePath($repoRoot, $fixturePath).Replace("\", "/")
        sha256 = Get-Sha256 -Path $fixturePath
    }
    fixture_count = @($manifest.fixtures).Count
    passed_count = @($results | Where-Object { $_.pass }).Count
    results = @($results)
    counters = [ordered]@{
        process = 0
        browser = 0
        popup = 0
        hardware = 0
        write = 0
    }
    execute_performed = $false
    owner_result_written = $false
    evidence_artifact_write_count = 1
    evidence_artifact_write_excluded_from_product_write_counter = $true
}
$result | ConvertTo-Json -Depth 16 |
    Set-Content -LiteralPath $resultPath -Encoding utf8NoBOM
if (-not $allPassed) {
    throw "One or more owner-review readiness negative fixtures did not fail closed."
}
Write-Output "NEGATIVE_FIXTURES_PASS=$([System.IO.Path]::GetRelativePath($repoRoot, $resultPath))"
