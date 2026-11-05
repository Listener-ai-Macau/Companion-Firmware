#!/usr/bin/env python3
"""Static and policy regression gate for the product board-mic recording path."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c"
PANEL = ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wb_ssd1681.c"
OPUS_RT = ROOT / "app" / "companion_pendant" / "recording" / "companion_opus16_rt.c"
SILK_PITCH = ROOT / "third_party" / "opus" / "silk" / "fixed" / "find_pitch_lags_FIX.c"
SILK_PRED = ROOT / "third_party" / "opus" / "silk" / "fixed" / "find_pred_coefs_FIX.c"
SILK_LPC = ROOT / "third_party" / "opus" / "silk" / "fixed" / "find_LPC_FIX.c"
OPUS_CONFIG = ROOT / "third_party" / "opus" / "config.h"
HOST_OPUS_CODEC = ROOT.parent / "Companion-Type" / "third_party" / "denzic-platform" / "host_audio" / "host" / "rust" / "src" / "opus_codec.rs"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def function_body(source: str, signature: str) -> str:
    # main.c keeps forward declarations; the implementation is the last match.
    start = source.rindex(signature)
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start : pos + 1]
    raise AssertionError(f"unterminated function: {signature}")


def macro(source: str, name: str) -> str:
    match = re.search(rf"^#define\s+{re.escape(name)}\s+(.+)$", source, re.MULTILINE)
    require(match is not None, f"missing macro {name}")
    return match.group(1).strip()


def agc_step(raw_peak: int, gain: int, release_hold: int) -> tuple[int, int]:
    gain_min = 8
    gain_max = 256
    target = 16000
    high = 28000
    low = 7000
    silence = 120
    projected = raw_peak * gain
    if projected > high:
        reduced = max(gain_min, gain * 230 // 256)
        reduced = max(reduced, max(gain_min, (target + raw_peak // 2) // raw_peak))
        gain = reduced
        release_hold = 20
    elif raw_peak > silence and projected < low and release_hold == 0:
        gain = min(gain_max, max(gain + 1, gain * 258 // 256))
    if release_hold > 0 and projected <= high:
        release_hold -= 1
    return gain, release_hold


def main() -> int:
    source = MAIN.read_text(encoding="utf-8")
    panel = PANEL.read_text(encoding="utf-8")
    opus_rt = OPUS_RT.read_text(encoding="utf-8")
    silk_pitch = SILK_PITCH.read_text(encoding="utf-8")
    silk_pred = SILK_PRED.read_text(encoding="utf-8")
    silk_lpc = SILK_LPC.read_text(encoding="utf-8")
    opus_config = OPUS_CONFIG.read_text(encoding="utf-8")
    host_opus_codec = HOST_OPUS_CODEC.read_text(encoding="utf-8")
    activate = function_body(source, "static bool recording_flash_activate_capture(")
    finalize = function_body(source, "static bool recording_flash_finalize_capture(")

    require(macro(source, "COMPANION_LIVE_MIC_CODEC3") == "1", "codec3 gate is not enabled")
    require(macro(source, "COMPANION_LIVE_MIC_OPUS_RATE_HZ") == "8000u", "live rate must be 8 kHz")
    require(macro(source, "COMPANION_LIVE_MIC_OPUS_FRAME_MS") == "20u", "live frame must be proven 20 ms")
    require(macro(source, "COMPANION_RTOS_REC_STACK_WORDS") == "2816u",
            "rec stack must stay at the proven activation floor")
    require(macro(source, "COMPANION_RTOS_ENCODE_STACK_WORDS") == "4608u",
            "standard-pitch encoder stack regression")
    require(macro(source, "COMPANION_RTOS_DISPLAY_STACK_WORDS") == "896u" and
            macro(source, "COMPANION_RTOS_SVC_STACK_WORDS") == "640u",
            "screen/BLE service stack regression")
    require("companion_opus16_rt_init_rate_frame(" in activate, "live capture does not initialise Opus")
    require("s_recording_flash.half_rate_pcm = false;" in activate, "codec3 path must not expose PCM")
    require("s_recording_flash.adpcm_encode = false;" in activate, "codec3 path must not enable ADPCM")
    require("s_recording_use_opus16 = true;" in activate, "codec3 path is not committed after init")
    require("s_recording_flash.capture_active = false;" in activate, "Opus init must fail closed")
    require("#error \"The product live-mic path requires COMPANION_LIVE_MIC_CODEC3=1\"" in activate,
            "codec3 must not be build-time disableable")
    require("header.codec = FLASH_RECORDING_CODEC_OPUS16;" in finalize,
            "finalizer does not map Opus capture to codec=3")

    require(macro(source, "COMPANION_PDM_CIC3_CHUNK_ACCUMULATE") == "0",
            "physical-board ASR baseline requires byte/bit CIC3")
    require(macro(source, "COMPANION_MIC_PREAMP_SHIFT") == "3u",
            "linear codec3 capture requires the physically proven fixed x8 preamp")
    require(macro(source, "COMPANION_MIC_AGC_ENABLE") == "0",
            "unproved high-gain AGC must not erase real speech pauses")
    require(macro(source, "COMPANION_MIC_LIMITER_CEILING") == "23170u",
            "codec3 input limiter must retain the physically ASR-proven ceiling")
    require("const uint64_t projected_batch_peak" in source and
            "preamp_scale_q15" in source and
            "if (preamp_gain > 8 &&" in source and
            "amplified_wide" in source and
            source.index("projected_batch_peak") < source.index("amplified_wide"),
            "preamp must scale the int64 batch before narrowing to PCM16")
    require(macro(source, "DISPLAY_BUSY_WAIT_SERVICE_PERIOD_MS") == "1u",
            "RTOS display BUSY wait must service every tick")
    wait_hook = function_body(source, "static void capture_touch_during_display_wait(")
    require("xTaskGetSchedulerState() == taskSCHEDULER_RUNNING" in wait_hook,
            "display wait may call FreeRTOS before scheduler start")
    require("vTaskDelay(pdMS_TO_TICKS(1u));" in wait_hook,
            "display BUSY callback does not block/yield CPU")
    require("HAL_Delay(1u);" in wait_hook,
            "pre-scheduler display wait has no safe fallback")
    require("recording_surface ? RECORDING_TOUCH_IDLE_POLL_MS" in source,
            "recording idle touch cadence is defined but not applied")
    require("host_ble_recording" in source and
            "GATT_RECORDING_TOUCH_IDLE_POLL_MS" in source,
            "GATT recording does not reserve codec3 CPU headroom")
    require("Encode at most one 10 ms input" in source and
            "s_recording_flash.half_rate_pcm" in source and
            "want = depth;" in source and
            "want = 1u;" in source and
            "want = 6u;" not in function_body(source, "static void Companion_Rtos_EncodeTask("),
            "codec3 encode task may exceed the bounded one-input turn")
    encode_task = function_body(source, "static void Companion_Rtos_EncodeTask(")
    require('"encode",\n                    COMPANION_RTOS_ENCODE_STACK_WORDS,\n                    NULL,\n                    6,' in source and
            "want = 1u;" in encode_task and
            "vTaskDelay(pdMS_TO_TICKS(1u));" in encode_task,
            "bounded codec consumer must preempt the SSD1681 BUSY waiter")
    require('"rec",\n                    COMPANION_RTOS_REC_STACK_WORDS,\n                    NULL,\n                    6,' in source and
            '"display",\n                    COMPANION_RTOS_DISPLAY_STACK_WORDS,\n                    NULL,\n                    6,' in source and
            '"input",\n                    320,\n                    NULL,\n                    6,' in source and
            '"svc",\n                    COMPANION_RTOS_SVC_STACK_WORDS,\n                    NULL,\n                    3,' in source,
            "64 MHz PDM capture/display/service priorities regressed")
    require("RCC_SYSCLKSOURCE_PLLCLK" in source and
            "AHBCLK2Divider = RCC_SYSCLK_DIV2" in source and
            "HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_3)" in source,
            "64 MHz CPU clock must keep wireless HCLK2 at 32 MHz and Flash at 3WS")
    finalize = function_body(source, "static bool recording_flash_finalize_capture(")
    require("s_encode_finalize_drain = true;" in finalize and
            "s_encode_flush_request = true;" in finalize and
            "companion_opus16_rt_flush(&s_recording_opus_rt" not in finalize.split("#else", 1)[0] and
            "live_mic_encode_drain(1u);" not in finalize,
            "RTOS finalize must drain and flush SILK only on EncodeTask's stack")
    encode_drain = function_body(source, "static void live_mic_encode_drain(")
    require("!s_live_pcm_ring_on" not in encode_drain and
            "!s_recording_flash.capture_active" in encode_drain,
            "finalize must drain queued PCM after disabling the live producer")
    dma_read = function_body(source, "static HAL_StatusTypeDef pdm_raw_dma_read_block(")
    require("s_pdm_raw_dma_overrun_count++;" not in dma_read and
            "Both pending are still intact" in dma_read,
            "two intact pending DMA halves must not be miscounted as data loss")
    flash_drain = function_body(source, "static bool recording_flash_drain_stage(")
    require("xTaskGetCurrentTaskHandle() == s_companion_encode_task" in flash_drain and
            "vTaskDelay(pdMS_TO_TICKS(1u));" in flash_drain and
            "PDM DMA owns only two 10 ms halves" in flash_drain,
            "live NOR page burst must yield between pages for PDM capture")
    require("OPUS_SET_FORCE_MODE(MODE_SILK_ONLY)" in opus_rt and
            "COMPANION_OPUS8_LIVE_BITRATE_BPS 16000" in opus_rt,
            "codec3 board capture must use the physically ASR-proven 16 kbps SILK path")
    whitening_filter = silk_pitch.index("silk_LPC_analysis_filter( res, x")
    pitch_search = silk_pitch.index("silk_pitch_analysis_core( res")
    require("silk_pitch_analysis_core" in silk_pitch and
            "companion_pitch_A_Q12" not in silk_pitch and
            "silk_NLSF2A( A_Q12, psEnc->sCmn.prev_NLSFq_Q15" not in silk_pitch and
            whitening_filter < pitch_search and
            "if( companion_silk_live_fast_enabled() )" not in silk_pitch and
            "silk_memcpy( res, x, buf_len * sizeof( opus_int16 ) )" not in silk_pitch,
            "codec3 LIVE_FAST must retain LPC whitening and its proven unvoiced fast gate")
    require("silk_find_LPC_FIX( &psEnc->sCmn, NLSF_Q15, LPC_in_pre, minInvGain_Q30 );" in silk_pred and
            "refresh_predictor" not in silk_pred and
            "companion_lpc_analysis_NLSF_Q15" not in silk_pred,
            "codec3 must retain the reference LPC call path")
    require("frameCounter %" not in silk_lpc and
            "silk_burg_modified" in silk_lpc and
            "silk_autocorr" not in silk_lpc,
            "codec3 LPC must use reference Burg every frame")
    require("#define OPUS_ARM_INLINE_ASM 1" not in opus_config and
            "#define OPUS_ARM_INLINE_EDSP 1" not in opus_config and
            "#define OPUS_ARM_INLINE_MEDIA 1" not in opus_config,
            "unproven Opus ARM inline macros regress the Aug-03 drops=0 baseline")
    require("if sample_rate == 8_000 { 48 } else { 1 }" in host_opus_codec and
            "scale_and_clamp_pcm16_wav(wav_out, post_decode_gain, 29_900)?;" in host_opus_codec,
            "Type must apply the physically accepted x48 gain only to 8 kHz board COP1 and clamp below full scale")
    require("static bool ssd1681_service_wait(void)" in panel,
            "panel wait hook must report whether it blocked")
    require(panel.count("if (!ssd1681_service_wait())") >= 2,
            "SSD1681 BUSY loops still unconditionally busy-wait")

    # 8 kbps CBR plus COP1's two-byte packet prefix is 1100 B/s at 20 ms.
    # Keep a conservative 5 kB/s erase budget; both fit comfortably in 14 MiB
    # and guard accidental return to raw-PCM sizing.
    opus_ten_min_bytes = 600 * (16000 // 8 + 2 * 50)
    require(opus_ten_min_bytes < 0x00E00000,
            "16 kbps 10-minute payload exceeds NOR region")
    require(600 * 5000 < 0x00E00000, "10-minute erase budget exceeds NOR region")

    print(
        "PASS live_mic_codec3_product "
        "codec=3 rate=8000 bitrate=16000 frame_ms=20 pitch=reference fail_closed=1 "
        "pdm=cic3_byte preamp=fixed_x8 host_decode_gain=x48 agc=off "
        "display_busy_wait=rtos_blocking "
        f"opus_ten_min_bytes={opus_ten_min_bytes} "
        f"ten_min_erase_budget_bytes={600 * 5000}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, ValueError) as exc:
        print(f"FAIL live_mic_codec3_product: {exc}", file=sys.stderr)
        raise SystemExit(1)
