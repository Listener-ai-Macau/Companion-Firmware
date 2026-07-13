param(
    [switch]$Json,
    [switch]$Check,
    [switch]$UpdateFromAccepted,
    [string]$Plan,
    [string]$StepId,
    [string]$Commit,
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$features = [ordered]@{
    repo = "Companion-Firmware"
    purpose = "STM32WB firmware for the Companion pendant MVP."
    stack = @(
        "STM32CubeWB official package pinned at v1.24.0",
        "NUCLEO-WB55RG first bring-up board",
        "STM32_WPAN BLE stack with HAL/LL, IPCC, HSEM, RTC/LPM, and CubeProgrammer validation"
    )
    baseline = [ordered]@{
        upstream = "STMicroelectronics/STM32CubeWB"
        tag = "v1.24.0"
        commit = "7c5aa7dcd2c0abe787f922bb06a6213c724d08e4"
        starter = "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer"
        ota_core = "third_party/denzic-platform denzic_ota_v1"
        ota_adapter = "Companion_BLE_Ota_Loader STM32WB platform adapter"
        throughput_reference = "BLE_DataThroughput"
    }
    responsibilities = @(
        "Prove the official ST BLE_p2pServer example before custom Companion services.",
        "Own Companion GATT, diagnostic log foundation, microphone capture, e-paper update path, SPI flash recording cache, and BLE OTA readiness.",
        "Own the Listener feature migration track, including reuse boundaries, forbidden direct reuse, and guardrail validation.",
        "Keep ST upstream code under third_party/STM32CubeWB read-only for product work."
    )
    key_paths = @(
        "app/companion_pendant/",
        "docs/bringup_steps.md",
        "docs/stm32wb_official_starter.md",
        "docs/listener_reuse_map.md",
        "docs/listener_feature_migration.md",
        "tools/bootstrap_stm32cubewb.ps1",
        "tools/build.ps1",
        "tools/flash.ps1",
        "third_party/STM32CubeWB/"
    )
    validation_commands = @(
        "pwsh -NoProfile -File .\tools\ai\repo_features.ps1 -Check",
        'pwsh -NoProfile -Command ''$p="docs/listener_feature_migration.md"; if(!(Test-Path $p)){ throw "missing listener_feature_migration" }; $need=@("| Listener capability | Companion target | reuse mode | first implementation step | validation | risk |","Listener-Type BLE recovery","actionable BLE failure","diagnostics bundle","recording byte-offset transfer","delete-after-sync","OTA manifest","low-power state","forbidden direct reuse","ESP-IDF","NimBLE","PWR_HOLD"); foreach($n in $need){ if(-not (Select-String -LiteralPath $p -Pattern $n -SimpleMatch -Quiet)){ throw ("missing migration anchor: "+$n) } }''',
        "pwsh -NoProfile -Command `"Test-Path third_party\STM32CubeWB\Projects\P-NUCLEO-WB55.Nucleo\Applications\BLE\BLE_p2pServer`"",
        "git submodule status -- third_party/STM32CubeWB",
        "git diff --check"
    )
    migration_track = [ordered]@{
        name = "Listener feature migration guardrails"
        map = "docs/listener_feature_migration.md"
        proves = @(
            "Listener-Type BLE recovery and actionable BLE failure classification are mapped to Companion host fixtures.",
            "Diagnostics bundle, recording byte-offset transfer, delete-after-sync privacy, OTA manifest discipline, low-power state modeling, and product validation matrices have first-step targets.",
            "ESP-IDF, NimBLE, HID keyboard behavior, ESP partitions/NVS, PWR_HOLD, Listener LEDs, and Listener device names are forbidden direct reuse."
        )
    }
    hardware_lock_rule = "Real flash, serial monitor, BLE capture, or board validation must use the workflow hardware lock around the shortest exclusive window; code edits and static checks run outside the lock."
    boundaries = @(
        "Listener-Firmware is read-only source_ref material for reuse classification.",
        "Listener-Type is read-only source_ref material for desktop BLE tooling lessons.",
        "Companion-Hardware owns PCB, mechanical, manufacturing, and hardware envelope assets."
    )
}

if ($UpdateFromAccepted) {
    Write-Output "No generated feature log is needed yet for Companion-Firmware."
    if ($Plan -or $StepId -or $Commit) {
        Write-Output "Accepted context: plan=$Plan step=$StepId commit=$Commit"
    }
    exit 0
}

function Assert-FileContains {
    param(
        [Parameter(Mandatory=$true)][string]$RelativePath,
        [Parameter(Mandatory=$true)][string[]]$Needles
    )

    $path = Join-Path $RepoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing required file: $RelativePath"
    }

    $text = Get-Content -LiteralPath $path -Raw
    foreach ($needle in $Needles) {
        if ($text -notmatch [regex]::Escape($needle)) {
            throw "Missing '$needle' in $RelativePath"
        }
    }
}

if ($Check) {
    Assert-FileContains -RelativePath "README.md" -Needles @(
        "STM32CubeWB",
        "NUCLEO-WB55RG",
        "BLE_p2pServer"
    )
    Assert-FileContains -RelativePath "docs/bringup_steps.md" -Needles @(
        "STM32CubeWB",
        "BLE_p2pServer",
        "STM32CubeProgrammer"
    )
    Assert-FileContains -RelativePath "docs/listener_reuse_map.md" -Needles @(
        "audio_capture",
        "voice_recording_control",
        "firmware_ota",
        "diag_log",
        "Listener-Type",
        "STM32_WPAN",
        "no reuse"
    )
    Assert-FileContains -RelativePath "docs/listener_feature_migration.md" -Needles @(
        "| Listener capability | Companion target | reuse mode | first implementation step | validation | risk |",
        "Listener-Type BLE recovery",
        "actionable BLE failure",
        "diagnostics bundle",
        "recording byte-offset transfer",
        "delete-after-sync",
        "OTA manifest",
        "low-power state",
        "product validation matrices",
        "forbidden direct reuse",
        "ESP-IDF drivers",
        "NimBLE services",
        "HID keyboard behavior",
        "ESP partitions/NVS",
        "PWR_HOLD",
        "Listener LEDs",
        "Listener device names"
    )
    Assert-FileContains -RelativePath "docs/stm32wb_official_starter.md" -Needles @(
        "v1.24.0",
        "7c5aa7dcd2c0abe787f922bb06a6213c724d08e4",
        "BLE_p2pServer_reference.hex",
        "stm32wb5x_BLE_Stack_full_fw.bin",
        "app/companion_pendant",
        "aiw with-lock -Resource Companion-WB55"
    )
    Assert-FileContains -RelativePath "app/companion_pendant/README.md" -Needles @(
        "product-owned starter surface",
        "NUCLEO-WB55RG",
        "BLE_p2pServer",
        "aiw with-lock -Resource Companion-WB55"
    )
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "third_party\STM32CubeWB") -PathType Container)) {
        throw "Missing third_party/STM32CubeWB submodule directory"
    }
    Write-Output "PASS: Companion-Firmware repo feature check passed for STM32CubeWB/NUCLEO-WB55RG bring-up and Listener feature migration guardrails."
    Write-Output "Migration track: docs/listener_feature_migration.md"
    Write-Output "Guardrail validation commands: pwsh -NoProfile -Command '<listener_feature_migration anchor check>'; pwsh -NoProfile -File .\tools\ai\repo_features.ps1 -Check; git diff --check"
    exit 0
}

if ($Json) {
    $features | ConvertTo-Json -Depth 6
    exit 0
}

Write-Output "$($features.repo): $($features.purpose)"
Write-Output "Stack:"
foreach ($item in $features.stack) {
    Write-Output "  - $item"
}
Write-Output "Starter: $($features.baseline.starter)"
Write-Output "Hardware lock: $($features.hardware_lock_rule)"

