param(
    [string] $OutDir,
    [string] $HardwareAcceptanceSummary,
    [string] $RealBleBench,
    [switch] $Json
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$argsList = @(".\tools\verify_companion_operator_chain.py")
if (-not [string]::IsNullOrWhiteSpace($OutDir)) {
    $argsList += @("--out-dir", $OutDir)
}
if (-not [string]::IsNullOrWhiteSpace($HardwareAcceptanceSummary)) {
    $argsList += @("--hardware-acceptance-summary", $HardwareAcceptanceSummary)
}
if (-not [string]::IsNullOrWhiteSpace($RealBleBench)) {
    $argsList += @("--real-ble-bench", $RealBleBench)
}
if ($Json) {
    $argsList += "--json"
}

Push-Location $repoRoot
try {
    & python @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "Companion operator chain validation failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
