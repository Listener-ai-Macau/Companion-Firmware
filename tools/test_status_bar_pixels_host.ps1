param(
    [string]$OutputDirectory = ".cache\host-tests\status-bar-pixels"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the status-bar pixel replay."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$touchRoot = Join-Path $repoRoot "app\companion_pendant\touch"
$fixture = Join-Path $epaperRoot "tests\test_status_bar_pixels.c"
$menu = Join-Path $epaperRoot "screen_menu.c"
$framebuffer = Join-Path $epaperRoot "screen_framebuffer.c"
$source = Join-Path $repoRoot ".cache\validation\comp776-component-clip-fix-20260812\source-pack-5059\frames\expression_sleepy_v0_0_hold.pbm"
$output = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
$build = Join-Path $repoRoot ".cache\host-tests\status-bar-pixels-build"
$exe = Join-Path $build "test_status_bar_pixels.exe"
foreach ($required in @($vsDevCmd, $fixture, $menu, $framebuffer, $source)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing status-bar replay dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $build, $output | Out-Null

$compile = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=0 /I"{1}" /I"{2}" "{3}" "{4}" "{5}" /Fe:"{6}"' -f `
    $vsDevCmd, $epaperRoot, $touchRoot, $fixture, $menu, $framebuffer, $exe
Push-Location $build
try {
    & $env:ComSpec /d /s /c $compile
    if ($LASTEXITCODE -ne 0) {
        throw "Status-bar pixel replay compile failed with exit code $LASTEXITCODE."
    }
    & $exe $source $output
    if ($LASTEXITCODE -ne 0) {
        throw "Status-bar pixel replay failed with exit code $LASTEXITCODE."
    }

    # The normal expression, recording, and low-power resources must all use
    # one authored status strip. The five upgrade progress screens deliberately
    # own their complete top bar and are the only permitted exceptions.
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $topStripRows = 16
    $topStripBytes = 25 * $topStripRows
    $topStripEntries = Get-ChildItem -LiteralPath (Join-Path (Split-Path $source -Parent) "") -Filter "*.pbm" | ForEach-Object {
        $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
        $newlineCount = 0
        $payloadStart = -1
        for ($index = 0; $index -lt $bytes.Length; $index++) {
            if ($bytes[$index] -eq 10) {
                $newlineCount++
                if ($newlineCount -eq 2) {
                    $payloadStart = $index + 1
                    break
                }
            }
        }
        if ($payloadStart -lt 0 -or $payloadStart + $topStripBytes -gt $bytes.Length) {
            throw "Malformed status-bar PBM: $($_.FullName)"
        }
        $topStrip = [byte[]]::new($topStripBytes)
        [Array]::Copy($bytes, $payloadStart, $topStrip, 0, $topStripBytes)
        [pscustomobject]@{
            Name = $_.Name
            # Convert.ToHexString is .NET 5+ and is absent from the Windows
            # PowerShell 5.1 used by the board toolchain.  Keep the receipt
            # deterministic on both hosts.
            Hash = ([BitConverter]::ToString($sha.ComputeHash($topStrip))).Replace("-", "")
        }
    }
    $topStripGroups = @($topStripEntries | Group-Object Hash | Sort-Object Count -Descending)
    $upgradeExceptions = @($topStripEntries | Where-Object Hash -ne $topStripGroups[0].Name | Sort-Object Name | Select-Object -ExpandProperty Name)
    $expectedUpgradeExceptions = @(
        "upgrade_progress_0_25.pbm",
        "upgrade_progress_0_5.pbm",
        "upgrade_progress_0_75.pbm",
        "upgrade_progress_0.pbm",
        "upgrade_progress_1.pbm"
    ) | Sort-Object
    if ($topStripGroups[0].Count -ne 5054 -or
        (Compare-Object $upgradeExceptions $expectedUpgradeExceptions)) {
        throw "The 5059 source pack no longer has one invariant daily status strip plus five upgrade-only exceptions."
    }
    $previewHashes = [ordered]@{}
    Get-ChildItem -LiteralPath $output -Filter "*.pbm" | Sort-Object Name | ForEach-Object {
        $previewHashes[$_.Name] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    }
    $receipt = [ordered]@{
        schema = "companion.comp785.status_bar_pixel_replay.v1"
        status = "MACHINE_READY"
        source = [ordered]@{
            path = $source
            sha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
            identity = "source-pack-5059 expression_sleepy_v0_0_hold"
        }
        checks = [ordered]@{
            actual_c_renderer_executed = $true
            pixels_below_y15_unchanged = $true
            canonical_top_strip_is_source_independent = $true
            connected_bluetooth_rune_visible = $true
            disconnected_bluetooth_marker_visible = $true
            connected_and_disconnected_are_distinct = $true
            nucleo_unmeasured_battery_screen_fallback_80 = $true
            measured_battery_glyph_visible = $true
            valid_clock_and_unknown_time_are_distinct = $true
            bluetooth_region_ends_before_battery_x172 = $true
            non_glyph_bar_regions_are_solid_black = $true
            normal_source_frames_share_authored_top_strip = "5054/5054"
            upgrade_full_bar_exceptions = $upgradeExceptions
            invalid_clock_rejected_without_mutation = $true
            framebuffer_polarity_matches_ssd1681 = "0=black"
        }
        preview_sha256 = $previewHashes
        hardware_contact = 0
    }
    [System.IO.File]::WriteAllText(
        (Join-Path $output "receipt.json"),
        (($receipt | ConvertTo-Json -Depth 6) + [Environment]::NewLine),
        [System.Text.UTF8Encoding]::new($false))
} finally {
    Pop-Location
}
