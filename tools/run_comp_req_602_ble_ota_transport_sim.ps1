# COMP-REQ-602 transport-scenario host simulation (machine closure).
#
# "Machine closure" = the machine mimics the real transport scenario that a
# human exercises on the physical pendant, run OFFLINE on the host:
#   BLE device-control state machine  (caps / settings / write / invoke,
#      duplicate + idempotency replay detection, terminal accounting)
#   product-entry transport           (ordered begin>callback>mutation>
#      readback>terminal, collision rejection, failure replay)
#   diagnostics transport             (diag_log_pull positive + negatives)
#   OTA orchestration transport       (manifest admit -> accepted=1,
#      transport_contact=0, apply=0  ... FAIL-CLOSED: admission only,
#      no real transfer / apply / flash)
#
# It compiles the canonical host fixture (tools/fixtures/companion_platform_
# adapters_test.c) + the REAL platform / GATT / OTA-orchestration sources with
# MSVC into a host executable and RUNS it.  This is the "machine runs the
# transport scenario" half of verify_companion_platform_integration_fresh.py,
# stripped of the manifest / firmware-build-wrapper bindings so it can be
# reproduced against any source tree whose denzic-platform submodule is
# populated.  It is NOT a real-BLE / real-OTA / hardware PASS: the OTA path is
# fail-closed (transport_contact=0, apply=0) and CheckOnly is all zero.
#
# This script does not mutate the SSD1681 driver, the Platform pin, the
# submodule, or any art / upper-layer source.

param(
    [string]$Root,
    [string]$OutRoot = 'docs/validation/comp-req-602-platform-adapter-closure/transport-sim/ble_device_control'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
$Root = (Resolve-Path $Root).Path
# Honor an absolute OutRoot so the receipt can land in the 602 worktree while
# sources are read from a different checkout (e.g. the populated main checkout).
if ([System.IO.Path]::IsPathRooted($OutRoot)) { $Out = $OutRoot } else { $Out = Join-Path $Root $OutRoot }
New-Item -ItemType Directory -Force $Out | Out-Null

$vcvars = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path -LiteralPath $vcvars)) {
    $where = Get-Command vswhere.exe -ErrorAction SilentlyContinue
    if ($where) {
        $install = & $where.Source -latest -products '*' `
            -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
            -property installationPath 2>$null | Select-Object -First 1
        if ($install) { $vcvars = Join-Path $install 'VC\Auxiliary\Build\vcvars64.bat' }
    }
}
if (-not (Test-Path -LiteralPath $vcvars)) { throw 'MSVC vcvars64 unavailable' }

$isolated = Join-Path $Root '.cache\comp-req-602-host'
Remove-Item -Recurse -Force $isolated -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $isolated | Out-Null
$exe = Join-Path $isolated 'companion_platform_adapters_test.exe'

$sources = @(
    'tools/fixtures/companion_platform_adapters_test.c',
    'tools/fixtures/companion_gatt_host_stubs.c',
    'app/companion_pendant/platform/companion_platform_adapters.c',
    'app/companion_pendant/platform/companion_product_entry_glue.c',
    'app/companion_pendant/platform/companion_product_identity.c',
    'app/companion_pendant/platform/companion_product_transport.c',
    'app/companion_pendant/gatt/companion_gatt_stm32wb.c',
    'third_party/denzic-platform/device_control/embedded/c/src/denzic_device_control_v1.c',
    'third_party/denzic-platform/observability/embedded/c/src/denzic_diag_log_gatt_v1.c',
    'third_party/denzic-platform/ota/embedded/c/src/denzic_ota_orchestration_v1.c'
) | ForEach-Object { Join-Path $Root $_ }

$inc = @(
    'tools/fixtures',
    'app/companion_pendant/platform',
    'app/companion_pendant/gatt',
    'third_party/denzic-platform/device_control/embedded/c/include',
    'third_party/denzic-platform/observability/embedded/c/include',
    'third_party/denzic-platform/ota/embedded/c/include',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/core/auto',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/core/template',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/core',
    'third_party/STM32CubeWB/Drivers/CMSIS/Include',
    'third_party/STM32CubeWB/Drivers/CMSIS/Core/Include',
    'third_party/STM32CubeWB/Drivers/CMSIS/Device/ST/STM32WBxx/Include',
    'third_party/STM32CubeWB/Drivers/STM32WBxx_HAL_Driver/Inc',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/svc/Src',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/svc/Inc',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble',
    'third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32_WPAN/App',
    'third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Core/Inc',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl',
    'third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/utilities'
) | ForEach-Object { '/I"' + (Join-Path $Root $_) + '"' }

$fi = @(
    '/FI"' + (Join-Path $Root 'tools/fixtures/companion_gatt_msvc_compat.h') + '"',
    '/FI"' + (Join-Path $Root 'third_party/STM32CubeWB/Drivers/STM32WBxx_HAL_Driver/Inc/stm32wbxx_hal_rtc.h') + '"'
)

$srcQuoted = ($sources | ForEach-Object { '"' + $_ + '"' }) -join ' '
$exeLeaf = Split-Path $exe -Leaf
$cmd = 'call "' + $vcvars + '" >nul && cd /d "' + $isolated + '" && cl /nologo /O2 /Brepro /W4 /WX /wd4100 /wd4311 /wd4312 /DSTM32WB55xx /D_CRT_SECURE_NO_WARNINGS ' + ($fi -join ' ') + ' ' + ($inc -join ' ') + ' ' + $srcQuoted + ' /Fe:"' + $exeLeaf + '"'
$compileLog = Join-Path $Out 'compile.log'
& $env:ComSpec /d /s /c $cmd 2>&1 | Set-Content -Encoding utf8 $compileLog
if ($LASTEXITCODE -ne 0) { throw "COMP-REQ-602 BLE/OTA host fixture compile failed (exit $LASTEXITCODE); see $compileLog" }

$stdout = & $exe 2>&1 | Out-String
$code = $LASTEXITCODE

$expected = @(
    'ordered_trace=begin>callback>mutation>readback>terminal',
    'diag positive',
    'device terminal_count',
    'adapter_observer begin=',
    'ota positive'
)
$observed = @{}
foreach ($e in $expected) { $observed[$e] = $stdout.Contains($e) }
$otaFailClosed = $stdout.Contains('ota positive accepted=1') -and $stdout.Contains('transport_contact=0') -and $stdout.Contains('apply=0')

[ordered]@{
    status              = if ($code -eq 0 -and $observed.Values -notcontains $false) { 'MACHINE_PASS_PENDING_FOCUSED_HUMAN_BLE_DEVICE_CONTROL_AND_OTA_RADIO' } else { 'NO_GO' }
    auto_pass_fail      = if ($code -eq 0 -and $observed.Values -notcontains $false) { 'PASS (exit 0 + 5/5 traces observed)' } else { 'FAIL' }
    exit_code           = $code
    scenario            = 'BLE device-control + product-entry + diagnostics + OTA orchestration transport (host simulation, machine mimics human transport scenario)'
    observed_traces     = $observed
    ota_fail_closed     = $otaFailClosed
    must_not_claim      = @(
        'No artifact here proves a real BLE radio connection/write to a Companion pendant.',
        'No artifact here proves a real OTA transfer/apply; OTA is admission-only (transport_contact=0, apply=0).',
        'No artifact here proves real device GATT mutation over the air; the readback/mutation is host-fixture in-RAM only.'
    )
    pending_human_acceptance = @(
        'Real BLE radio device-control (rename/reconnect/re-pair, settings write, invoke) via Companion-Type under workflow lock.',
        'Real OTA radio transfer/apply (see run_comp_req_602_ota_transfer_state_sim.ps1 pending steps).'
    )
    stdout              = $stdout.Trim()
    root                = $Root
    executable_sha256   = (Get-FileHash $exe -Algorithm SHA256).Hash.ToUpper()
    compile_log_sha256  = (Get-FileHash $compileLog -Algorithm SHA256).Hash.ToUpper()
    runner_sha256       = (Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToUpper()
    validation_commands = @(
        'pwsh -NoProfile -File tools\run_comp_req_602_ble_ota_transport_sim.ps1 -Root <firmware-root-with-denzic-platform-populated>'
    )
    checkonly           = [ordered]@{ hardware_contact=0; programmer=0; serial=0; write=0; reset=0; refresh=0; popup=0; retry=0 }
    side_effects        = [ordered]@{ hardware=0; ble_write=0; ota_transfer=0; ota_apply=0; popup=0; push=0 }
    physical_scope      = 'closed_unproven'
    note                = 'Mirrors Listener product acceptance framing (MACHINE_PASS_PENDING_FOCUSED_HUMAN_* + must_not_claim). Host simulation of the transport scenario. NOT a real BLE radio / real OTA transfer / hardware PASS. OTA path is fail-closed (admission only, transport_contact=0 apply=0).'
} | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $Out 'result.json')

if ($code -ne 0 -or $observed.Values -contains $false) { exit 1 }
