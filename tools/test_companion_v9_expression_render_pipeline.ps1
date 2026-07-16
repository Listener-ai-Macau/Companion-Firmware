param()

$ErrorActionPreference = "Stop"

$manifest = "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-cemp-manifest.json"
$pack = "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/companion-v9-expression-candidate-200x200.cemp"
$metadata = "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/companion-v9-expression-candidate-200x200.cemp.json"

function Invoke-Python([string[]]$Arguments) {
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "python $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

Invoke-Python @("tools/verify_companion_v9_art_baseline.py", "--write")
Invoke-Python @("tools/render_companion_v9_expression_assets.py", "--write")
Invoke-Python @("tools/build_emote_asset_pack.py", "--manifest", $manifest, "--output", $pack, "--metadata", $metadata)
$firstPackHash = (Get-FileHash -LiteralPath $pack -Algorithm SHA256).Hash

Invoke-Python @("tools/render_companion_v9_expression_assets.py", "--write")
Invoke-Python @("tools/build_emote_asset_pack.py", "--manifest", $manifest, "--output", $pack, "--metadata", $metadata)
$secondPackHash = (Get-FileHash -LiteralPath $pack -Algorithm SHA256).Hash
if ($firstPackHash -ne $secondPackHash) {
    throw "FAIL: v9 CEMP changed across identical source-locked render runs"
}

Invoke-Python @("tools/verify_companion_v9_expression_cemp.py", "--write")
Invoke-Python @("tools/build_companion_v9_scene_coverage.py", "--write")
Invoke-Python @("tools/verify_companion_v9_scene_coverage.py", "--write")
Invoke-Python @("tools/verify_companion_art_retirement.py", "--write")
Write-Output "PASS: v9 source -> 39/39 PBM -> deterministic CEMP -> decoded PBM -> no-fallback scene coverage -> v9-only art workspace."
