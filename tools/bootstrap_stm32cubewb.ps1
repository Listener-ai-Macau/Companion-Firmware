param(
    [switch] $SkipNestedSubmodules,
    [switch] $ResetSubmodule
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$submodulePath = Join-Path $repoRoot "third_party\STM32CubeWB"
$upstreamUrl = "https://github.com/STMicroelectronics/STM32CubeWB.git"
$upstreamTag = "v1.24.0"
$upstreamCommit = "7c5aa7dcd2c0abe787f922bb06a6213c724d08e4"

$sparsePaths = @(
    "Documentation",
    "Drivers/BSP/Components/Common",
    "Drivers/BSP/P-NUCLEO-WB55.Nucleo",
    "Drivers/CMSIS/Device/ST/STM32WBxx",
    "Drivers/CMSIS/Include",
    "Drivers/STM32WBxx_HAL_Driver",
    "Middlewares/ST/STM32_WPAN",
    "Utilities/lpm/tiny_lpm",
    "Utilities/sequencer",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota",
    "Projects/STM32WB_Copro_Wireless_Binaries"
)

$nestedSubmodules = @(
    "Drivers/STM32WBxx_HAL_Driver",
    "Drivers/CMSIS/Device/ST/STM32WBxx",
    "Drivers/BSP/P-NUCLEO-WB55.Nucleo",
    "Drivers/BSP/Components/Common"
)

$requiredPaths = @(
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/.project",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/.cproject",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Binary/BLE_p2pServer_reference.hex",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota/STM32CubeIDE/.project",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota/STM32CubeIDE/.cproject",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota/Binary/BLE_Ota_reference.hex",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/STM32CubeIDE/.project",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/STM32CubeIDE/.cproject",
    "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/Binary/BLE_p2pServer_ota_reference.bin",
    "Projects/STM32WB_Copro_Wireless_Binaries/STM32WB5x/stm32wb5x_BLE_Stack_full_fw.bin",
    "Middlewares/ST/STM32_WPAN/ble/svc/Src/p2p_stm.c",
    "Utilities/sequencer/stm32_seq.c",
    "Utilities/lpm/tiny_lpm/stm32_lpm.c"
)

function Invoke-Git {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]] $Args
    )

    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Assert-RequiredPath {
    param([Parameter(Mandatory = $true)][string] $RelativePath)

    $path = Join-Path $submodulePath $RelativePath
    if (-not (Test-Path -LiteralPath $path)) {
        throw "STM32CubeWB bootstrap is incomplete; missing $RelativePath"
    }
}

Push-Location $repoRoot
try {
    Invoke-Git config core.longpaths true
    Invoke-Git submodule sync -- third_party/STM32CubeWB
    Invoke-Git submodule init -- third_party/STM32CubeWB

    if ($ResetSubmodule -and (Test-Path -LiteralPath $submodulePath)) {
        $resolvedSubmodule = (Resolve-Path -LiteralPath $submodulePath).Path
        if (-not $resolvedSubmodule.StartsWith($repoRoot.Path, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to reset submodule outside repo root: $resolvedSubmodule"
        }

        & git submodule deinit -f -- third_party/STM32CubeWB | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "git submodule deinit failed with exit code $LASTEXITCODE"
        }
        Remove-Item -LiteralPath $resolvedSubmodule -Recurse -Force
    }

    if ((Test-Path -LiteralPath $submodulePath) -and -not (Test-Path -LiteralPath (Join-Path $submodulePath ".git"))) {
        $children = @(Get-ChildItem -LiteralPath $submodulePath -Force)
        if ($children.Count -eq 0) {
            Remove-Item -LiteralPath $submodulePath -Force
        } else {
            throw "third_party/STM32CubeWB exists but is not a git checkout. Move it aside or rerun with -ResetSubmodule."
        }
    }

    if (-not (Test-Path -LiteralPath $submodulePath)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $submodulePath) | Out-Null
        Invoke-Git -c core.longpaths=true clone --filter=blob:none --no-checkout --depth 1 --branch $upstreamTag $upstreamUrl $submodulePath
    }

    Invoke-Git -C $submodulePath config core.longpaths true
    Invoke-Git -C $submodulePath remote set-url origin $upstreamUrl
    Invoke-Git -C $submodulePath fetch --depth 1 origin $upstreamCommit
    Invoke-Git -C $submodulePath fetch --depth 1 origin tag $upstreamTag
    Invoke-Git -C $submodulePath sparse-checkout init --cone
    $sparseCheckoutArgs = @("-C", $submodulePath, "sparse-checkout", "set", "--skip-checks", "--") + $sparsePaths
    Invoke-Git @sparseCheckoutArgs
    Invoke-Git -C $submodulePath checkout --force $upstreamCommit

    if (-not $SkipNestedSubmodules) {
        $nestedUpdateArgs = @(
            "-C", $submodulePath,
            "-c", "core.longpaths=true",
            "submodule", "update", "--init", "--recursive", "--depth", "1", "--"
        ) + $nestedSubmodules
        Invoke-Git @nestedUpdateArgs
    }

    foreach ($requiredPath in $requiredPaths) {
        Assert-RequiredPath -RelativePath $requiredPath
    }

    $head = (& git -C $submodulePath rev-parse HEAD).Trim()
    if ($head -ne $upstreamCommit) {
        throw "STM32CubeWB HEAD is $head, expected $upstreamCommit"
    }

    $tag = (& git -C $submodulePath describe --tags --exact-match HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($tag)) {
        $tag = $upstreamTag
    }
    $short = (& git -C $submodulePath rev-parse --short HEAD).Trim()
    Write-Host "STM32CubeWB ready: $tag ($short)"
    Write-Host "Example: third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer"
    Write-Host "OTA example: third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota"
    Write-Host "OTA app example: third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota"
}
finally {
    Pop-Location
}
