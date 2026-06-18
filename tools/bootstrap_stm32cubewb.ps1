param(
    [switch] $SkipNestedSubmodules
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$submodulePath = Join-Path $repoRoot "third_party\STM32CubeWB"
$upstreamTag = "v1.24.0"
$upstreamCommit = "7c5aa7dcd2c0abe787f922bb06a6213c724d08e4"

$sparsePaths = @(
    "Documentation",
    "Drivers",
    "Middlewares",
    "Utilities",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer",
    "Projects/STM32WB_Copro_Wireless_Binaries"
)

Push-Location $repoRoot
try {
    git submodule update --init --depth 1 -- third_party/STM32CubeWB

    git -C $submodulePath fetch --depth 1 origin "tag" $upstreamTag
    git -C $submodulePath checkout $upstreamCommit
    git -C $submodulePath sparse-checkout init --cone
    git -C $submodulePath sparse-checkout set $sparsePaths

    if (-not $SkipNestedSubmodules) {
        git -C $submodulePath submodule update --init --recursive --depth 1
    }

    $tag = git -C $submodulePath describe --tags --exact-match HEAD
    $short = git -C $submodulePath rev-parse --short HEAD
    Write-Host "STM32CubeWB ready: $tag ($short)"
    Write-Host "Example: third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer"
}
finally {
    Pop-Location
}
