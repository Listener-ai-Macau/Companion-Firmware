# Candidate-art import test; it creates only disposable files under .cache.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& python (Join-Path $repoRoot "tools\test_v9_motion_extension_pipeline.py")
if ($LASTEXITCODE -ne 0) {
    throw "v9 motion extension pipeline test failed with exit code $LASTEXITCODE."
}
