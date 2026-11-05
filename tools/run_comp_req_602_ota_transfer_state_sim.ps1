# COMP-REQ-602 host-side OTA byte-transfer state-machine simulation.
#
# This is the OTA half of "machine mimics the real transport scenario". The real
# production OTA flow is: build -> package -> BLE-radio deliver -> device LOADER
# RECEIVES bytes -> VERIFY + APPLY (erase/write internal flash) -> reset/boot.
# Only the bold device-side transport logic is machine-runnable offline; the
# physical radio delivery, internal-flash erase/write and reset stay
# CLOSED_UNPROVEN (see physical_scope below; NEVER impersonate them).
#
# The ported OTA core (third_party/denzic-platform/ota/embedded/c/src/
# denzic_ota_v1.c) is the SAME shared code the STM32WB loader links (via
# companion_ota_v1.c) and that the Listener product also consumes. It is used
# DIRECTLY. This script drives that real, unmodified core two ways and reports
# exactly what it observes:
#
#   (1) CANONICAL test  (test_denzic_ota_v1.c)  -- the project's own host test.
#       Requires the platform fix below. Without it, a test/impl divergence
#       (re-BEGIN shrinks chunk_payload_bytes below the payload the test then
#       sends) trips BAD_SIZE before the intended OFFSET_MISMATCH check. With
#       the fix (offset-mismatch packet sized to the renegotiated chunk), the
#       canonical test PASSES.
#   (2) SUPPLEMENTAL fixture (tools/fixtures/companion_ota_transfer_scenario_host.c)
#       -- prints an observable per-step trace of the same state machine
#       (AIW-REQ-017 observable result; the canonical test is assert-only).
#
# PLATFORM FIX (denzic-platform, test_denzic_ota_v1.c L116):
#   offset-mismatch data packet length  sizeof(data) -> DATA_HEADER_BYTES + 4u
#   so it fits the chunk renegotiated to 4 by the preceding re-BEGIN. Impl is
#   correct (intentional chunk/window renegotiation on resume); the test
#   scenario was not respecting it. Durability needs an upstream commit to
#   Denzic-Platform.git + a submodule re-pin (owner-gated; flagged, not done).
#
# AIW-REQ-016 alignment: each threshold is an explicit invariant with an
# automatic PASS/FAIL.
#
# Compiled in an isolated cache dir; the denzic-platform submodule tree carries
# only the one-line platform fix above. No hardware, no flash, no real BLE/OTA.

param(
    [string]$Root,
    [string]$OutRoot = 'docs/validation/comp-req-602-platform-adapter-closure/transport-sim/ota_transfer'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
$Root = (Resolve-Path $Root).Path
if ([System.IO.Path]::IsPathRooted($OutRoot)) { $Out = $OutRoot } else { $Out = Join-Path $Root $OutRoot }
New-Item -ItemType Directory -Force $Out | Out-Null

$vcvars = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path -LiteralPath $vcvars)) {
    $where = Get-Command vswhere.exe -ErrorAction SilentlyContinue
    if ($where) {
        $install = & $where.Source -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null | Select-Object -First 1
        if ($install) { $vcvars = Join-Path $install 'VC\Auxiliary\Build\vcvars64.bat' }
    }
}
if (-not (Test-Path -LiteralPath $vcvars)) { throw 'MSVC vcvars64 unavailable' }

$ota = Join-Path $Root 'third_party\denzic-platform\ota\embedded\c'
$inc = Join-Path $ota 'include'
$iso = Join-Path $Root '.cache\denzic-ota-transfer-test'
New-Item -ItemType Directory -Force $iso | Out-Null
$clCommon = '/nologo /O2 /Brepro /W4 /wd4100 /wd4244 /wd4245 /wd4701 /wd4295 /std:c11 /I"' + $inc + '"'

# --- (1) CANONICAL project test (requires the platform fix) ---------------
$canonicalExe = Join-Path $iso 'canonical_test.exe'
$canonSrc = '"' + (Join-Path $ota 'tests\test_denzic_ota_v1.c') + '" "' + (Join-Path $ota 'src\denzic_ota_v1.c') + '"'
$canonCmd = 'call "' + $vcvars + '" >nul && cd /d "' + $iso + '" && cl ' + $clCommon + ' ' + $canonSrc + ' /Fe:"canonical_test.exe"'
$canonCompileLog = Join-Path $Out 'compile_canonical.log'
& $env:ComSpec /d /s /c $canonCmd 2>&1 | Set-Content -Encoding utf8 $canonCompileLog
if ($LASTEXITCODE -ne 0) { throw "canonical OTA test compile failed (exit $LASTEXITCODE); see $canonCompileLog" }
$canonStdout = & $canonicalExe 2>&1 | Out-String
$canonCode = $LASTEXITCODE

# --- (2) SUPPLEMENTAL observable-trace fixture ----------------------------
$supExe = Join-Path $iso 'supplemental.exe'
$supSrc = '"' + (Join-Path $PSScriptRoot 'fixtures\companion_ota_transfer_scenario_host.c') + '" "' + (Join-Path $ota 'src\denzic_ota_v1.c') + '"'
$supCmd = 'call "' + $vcvars + '" >nul && cd /d "' + $iso + '" && cl ' + $clCommon + ' ' + $supSrc + ' /Fe:"supplemental.exe"'
$supCompileLog = Join-Path $Out 'compile_supplemental.log'
& $env:ComSpec /d /s /c $supCmd 2>&1 | Set-Content -Encoding utf8 $supCompileLog
if ($LASTEXITCODE -ne 0) { throw "supplemental OTA fixture compile failed (exit $LASTEXITCODE); see $supCompileLog" }
$supStdout = & $supExe 2>&1 | Out-String
$supCode = $LASTEXITCODE

# AIW-REQ-016: explicit invariants + automatic PASS/FAIL.
$thresholds = [ordered]@{
    begin_to_receiving          = 'BEGIN control -> state RECEIVING'
    data_offset0_writes         = 'data @offset0 -> bytes_written advances'
    offset_mismatch_recoverable = 'data @wrong-offset (payload <= chunk) -> ERROR_OFFSET_MISMATCH, state STAYS RECEIVING (impl set_recoverable_error)'
    resume_correct_offset       = 'data @correct-offset after mismatch -> appends, last_error NONE'
    finish_completes            = 'FINISH -> storage_finished, state COMPLETE'
    status_encodes_dov1         = 'encode_status -> "DOV1" magic + state COMPLETE + ACTIVE_LINK_CONFIRMED'
    rebegin_diff_crc_aborts     = 're-BEGIN different CRC -> abort, bytes_written==0 (interrupted_transfer)'
    bad_magic_rejected          = 'BAD_MAGIC control -> rejected, last_error BAD_MAGIC'
}
$canonPass = ($canonCode -eq 0)
$supPass = ($supCode -eq 0)

[ordered]@{
    status            = if ($canonPass -and $supPass) { 'MACHINE_PASS_PENDING_FOCUSED_HUMAN_OTA_PHYSICAL_TRANSFER' }
                        elseif ($supPass) { 'MACHINE_NO_GO_CANONICAL_TEST__PASS_SUPPLEMENTAL_IMPL_PATH' }
                        else { 'NO_GO' }
    scenario          = 'OTA byte-transfer state machine (host simulation; machine mimics device loader RECEIVE/VERIFY path via RAM-backed fake storage)'
    real_scenario_step= 'device LOADER RECEIVES image bytes over transport -> VERIFY (offset/CRC) -> APPLY-ready (FINISH). Physical radio delivery + internal-flash erase/write + reset = PENDING human, NOT exercised.'
    real_core_compiled= 'third_party/denzic-platform/ota/embedded/c/src/denzic_ota_v1.c (same shared code the STM32WB loader links via companion_ota_v1.c, and that Listener also consumes; used DIRECTLY, unmodified)'
    canonical_test    = [ordered]@{
        source          = 'third_party/denzic-platform/ota/embedded/c/tests/test_denzic_ota_v1.c'
        status          = if ($canonPass) { 'PASS' } else { 'NO_GO' }
        exit_code       = $canonCode
        stdout          = $canonStdout.Trim()
        platform_fix    = [ordered]@{
            file            = 'third_party/denzic-platform/ota/embedded/c/tests/test_denzic_ota_v1.c'
            line            = 121
            change          = 'offset-mismatch data packet length: sizeof(data) -> DENZIC_OTA_V1_DATA_HEADER_BYTES + 4u (explanatory comment added at L116-120)'
            reason          = 'Test/impl divergence: the impl updates chunk_payload_bytes on resume (denzic_ota_v1.c L124-128, intentional), but the test re-BEGINs with chunk=4 then sent a 5-byte payload that tripped BAD_SIZE (hard error -> state ERROR) before the intended OFFSET_MISMATCH recoverable check. Impl is correct; test scenario fixed to respect the renegotiated chunk.'
            upstream_action = 'Commit to git@github.com:Listener-ai-Macau/Denzic-Platform.git + re-pin the Companion submodule (owner-gated; NOT done in this closure).'
        }
        executable_sha256 = (Get-FileHash $canonicalExe -Algorithm SHA256).Hash.ToUpper()
        compile_log_sha256 = (Get-FileHash $canonCompileLog -Algorithm SHA256).Hash.ToUpper()
    }
    supplemental_scenario = [ordered]@{
        source          = 'tools/fixtures/companion_ota_transfer_scenario_host.c'
        status          = if ($supPass) { 'PASS' } else { 'NO_GO' }
        exit_code       = $supCode
        stdout          = $supStdout.Trim()
        purpose         = 'Observable per-step trace of the same real core (AIW-REQ-017 observable result; the canonical test is assert-only, no stdout).'
        executable_sha256 = (Get-FileHash $supExe -Algorithm SHA256).Hash.ToUpper()
        compile_log_sha256 = (Get-FileHash $supCompileLog -Algorithm SHA256).Hash.ToUpper()
    }
    thresholds        = $thresholds
    fail_closed       = $true
    must_not_claim    = @(
        'The canonical test passes WITH the one-line platform fix applied in the denzic-platform submodule working tree; durability requires an upstream commit (Denzic-Platform.git) + submodule re-pin (owner-gated, not done).',
        'No artifact here proves a real BLE radio OTA transfer to a powered Companion pendant.',
        'No artifact here proves internal-flash erase/write/apply on a real STM32WB55 (FD_EraseSectors/FD_WriteData).',
        'No artifact here proves a device reset / boot to the new app or any post-update self-check.',
        'The RAM-backed fake storage is NOT internal flash: storage_finish==true is an in-RAM invariant, not a real FD_WriteData commit.'
    )
    pending_human_acceptance = @(
        'Real BLE radio OTA delivery via Companion-Type --firmware-ota-transfer under workflow lock (Companion-WB55,BLE-Companion).',
        'Real STM32WB55 internal-flash apply (FD_EraseSectors/FD_WriteData) + NVIC_SystemReset + boot to the new app.',
        'Post-update self-checks on device: boot_version_reported, ble_advertising, ota_readiness_notify, diag_log_tail.',
        'Owner action: commit the platform test fix upstream (Denzic-Platform.git) and re-pin the Companion submodule so the canonical test passes without a working-tree edit.'
    )
    root              = $Root
    runner_sha256     = (Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToUpper()
    validation_commands = @(
        'pwsh -NoProfile -File tools\run_comp_req_602_ota_transfer_state_sim.ps1 -Root <firmware-root-with-denzic-platform-populated>'
    )
    checkonly         = [ordered]@{ hardware_contact=0; programmer=0; serial=0; write=0; reset=0; refresh=0; popup=0; retry=0 }
    side_effects      = [ordered]@{ hardware=0; ble_write=0; ota_transfer=0; ota_apply=0; popup=0; push=0 }
    physical_scope    = 'closed_unproven'
    note              = 'Mirrors Listener product acceptance framing (MACHINE_PASS_PENDING_FOCUSED_HUMAN_* + must_not_claim). The ported OTA core is used DIRECTLY (shared denzic-platform code). Canonical project test PASSES with the one-line platform fix (test scenario now respects the renegotiated chunk); supplemental observable trace PASSES. Physical radio/flash/reset stay CLOSED_UNPROVEN. Paired with the OTA orchestration admission sim (ota positive accepted=1 transport_contact=0 apply=0).'
} | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $Out 'result.json')

if (-not ($canonPass -and $supPass)) { exit 1 }
