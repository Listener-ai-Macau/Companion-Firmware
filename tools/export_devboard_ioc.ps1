[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Companion_NUCLEO_WB55RG_Current.ioc'),
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $repoRoot 'cubeide\Companion_Nucleo_WB55RG\Companion_Nucleo_WB55RG.ioc'
$verifierPath = Join-Path $repoRoot 'tools\verify_devboard_ioc_import.py'

if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Canonical devboard IOC is missing: $sourcePath"
}

& python $verifierPath
if ($LASTEXITCODE -ne 0) {
    throw "Devboard IOC verification failed with exit code $LASTEXITCODE."
}

$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash

if ($CheckOnly) {
    [pscustomobject]@{
        status = 'PASS'
        mode = 'check_only'
        source = $sourcePath
        destination = $resolvedOutput
        sha256 = $sourceHash
    } | ConvertTo-Json
    exit 0
}

$outputDirectory = Split-Path -Parent $resolvedOutput
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

Copy-Item -LiteralPath $sourcePath -Destination $resolvedOutput -Force
$outputHash = (Get-FileHash -LiteralPath $resolvedOutput -Algorithm SHA256).Hash
if ($outputHash -ne $sourceHash) {
    throw "Exported IOC hash mismatch: source=$sourceHash destination=$outputHash"
}

[pscustomobject]@{
    status = 'PASS'
    mode = 'export'
    source = $sourcePath
    destination = $resolvedOutput
    sha256 = $outputHash
} | ConvertTo-Json
