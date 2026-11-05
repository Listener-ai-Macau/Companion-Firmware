#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
SOURCE_PACK = (
    ROOT
    / ".cache/validation/comp-req-769-ota-safe-hardware-preview/source-pack"
)
CEMP = SOURCE_PACK / "cemp/comp_req_769.cemp"
CEMP_VERIFICATION = SOURCE_PACK / "cemp/verification.json"
SOURCE_MANIFEST = SOURCE_PACK / "source-pack-manifest.json"
PRODUCT_BUILD = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_comp_req_770_ota_driver_r7"
)
DEFAULT_BUILD = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/"
    "build_comp_req_770_ota_driver_default_r1"
)
OUTPUT = ROOT / ".cache/validation/comp-req-770-restored-driver/MACHINE_READY.json"
FIXED_URL = (
    "http://127.0.0.1:4185/"
    ".cache/validation/comp-req-628-status-bar/index.html"
)
EXPECTED_PAGE_SHA256 = (
    "F9A1AAD6717179B3BD459C940BD6C32F174D4E8AF85347E11D82FD5CF6F83F3B"
)
EXPECTED_CEMP_SHA256 = (
    "6CFB2EBC7CB615632FC65ACD17C9FC82DB5CB4069A2F150227BA59B4D9F0DF5A"
)
PROTECTED_FUNCTIONS = {
    "ssd1681_native_cached_mode2_movement_activation": (
        "EE83A0BA3366357C93233FEB7EBD7E581FA39B6A12379FDFCE28FF949D8954F8"
    ),
    "ssd1681_native_two_pass_activation": (
        "D01C9FF988A11BF976F412469A6E769BC72DDAAB1D11B7B4D9FAF8EEC15115B7"
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def extract_function(text: str, marker: str) -> str:
    start = text.index(marker)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise RuntimeError(f"unterminated function: {marker}")


def tool(name: str) -> Path:
    matches = list(
        Path("C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins").glob(
            "com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.*"
            f"/tools/bin/{name}.exe"
        )
    )
    if len(matches) != 1:
        raise RuntimeError(f"expected one {name}, found {len(matches)}")
    return matches[0]


def run(command: list[str]) -> str:
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def main() -> int:
    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    product_refresh = extract_function(
        driver, "static comp_epaper_panel_result_t "
        "ssd1681_accepted_cached_mode2_product_refresh"
    )
    product_activate = extract_function(
        driver, "static bool ssd1681_accepted_product_activate"
    )
    product_source_window = extract_function(
        driver, "static bool ssd1681_accepted_product_set_source_window"
    )
    product_prepare = extract_function(
        driver, "static bool ssd1681_accepted_product_prepare"
    )
    protected = {}
    for name, expected in PROTECTED_FUNCTIONS.items():
        observed = hashlib.sha256(
            extract_function(driver, f"static bool {name}").encode("utf-8")
        ).hexdigest().upper()
        protected[name] = {
            "expected_raw_sha256": expected,
            "observed_raw_sha256": observed,
            "matches": observed == expected,
        }

    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    cemp_verification = json.loads(CEMP_VERIFICATION.read_text(encoding="utf-8"))
    product_elf = PRODUCT_BUILD / "Companion_Nucleo_WB55RG_Bringup.elf"
    default_elf = DEFAULT_BUILD / "Companion_Nucleo_WB55RG_Bringup.elf"
    sections = run([str(tool("arm-none-eabi-objdump")), "-h", str(product_elf)])
    product_symbols = run([str(tool("arm-none-eabi-nm")), "-a", str(product_elf)])
    default_symbols = run([str(tool("arm-none-eabi-nm")), "-a", str(default_elf)])

    try:
        with urllib.request.urlopen(FIXED_URL, timeout=5) as response:
            http_status = response.status
            http_bytes = len(response.read())
    except Exception:
        http_status = 0
        http_bytes = 0

    page_sha = sha256(PAGE)
    cemp_sha = sha256(CEMP)
    checks = {
        "fixed_url_http_200": http_status == 200,
        "fixed_url_serves_current_page": http_bytes == PAGE.stat().st_size,
        "page_identity_locked": page_sha == EXPECTED_PAGE_SHA256,
        "source_manifest_pass": source_manifest["status"] == "PASS",
        "source_manifest_page_identity": (
            source_manifest["source"]["page_sha256"] == page_sha
        ),
        "source_frames_native_200x200_1bpp": (
            source_manifest["source"]["pixel_format"]
            == "row_major_msb_first_1_is_white"
            and source_manifest["invariants"]["all_states_are_5000_bytes"]
        ),
        "cemp_identity_locked": cemp_sha == EXPECTED_CEMP_SHA256,
        "cemp_roundtrip_pass": (
            cemp_verification["status"] == "PASS_CEMP_EXTERNAL_SOURCE_BOUND"
            and all(cemp_verification["checks"].values())
        ),
        "protected_driver_cores_unchanged": all(
            item["matches"] for item in protected.values()
        ),
        "product_switch_default_off": (
            "#define COMPANION_EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT 0"
            in driver
        ),
        "product_switch_in_makefile": (
            "EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT" in makefile
        ),
        "product_uses_current_external_frame": (
            "frame_prepare(target->expression_assets, request)" in product_refresh
            and "ssd1681_accepted_product_apply_target_mapping" not in driver
        ),
        "product_uses_accepted_controls": (
            "first_frame ? 0xFFu : 0xCFu" in product_refresh
            and "ssd1681_write_plane_region(0x24u, s_frame, window)"
            in product_activate
            and "ssd1681_command_data(0x22u, &control, sizeof(control))"
            in product_activate
            and "ssd1681_command(0x20u)" in product_activate
        ),
        "product_preserves_accepted_face_corridor": all(
            token in product_refresh
            for token in (
                "ssd1681_window_from_difference()",
                ".x_start_byte = 4u",
                ".x_end_byte = 21u",
                ".y_start = 26u",
                ".y_end = 179u",
            )
        ),
        "product_preserves_white_cleanup": (
            "memset(s_frame, 0xFF, SSD1681_FRAME_BYTES)" in product_prepare
            and "&full_window, 0xFFu" in product_prepare
        ),
        "product_has_only_transport_mapping": (
            "frame_apply_target_rotation" not in product_refresh
            and "frame_apply_target_mirror" not in product_refresh
            and "(SSD1681_HEIGHT - 1u) - window->y_start"
            in product_source_window
            and "(SSD1681_HEIGHT - 1u) - window->y_end"
            in product_source_window
        ),
        "ota_vector_at_0x08007000": (
            ".isr_vector" in sections and "08007000  08007000" in sections
        ),
        "product_symbol_linked": "ssd1681_accepted_product_activate" in product_symbols,
        "default_control_excludes_product_symbol": (
            "ssd1681_accepted_product_activate" not in default_symbols
        ),
    }
    status = "MACHINE_READY" if all(checks.values()) else "NO_GO"
    artifact = {
        "schema": "companion.comp_req_770.restored_driver.v1",
        "requirement": "COMP-REQ-770",
        "status": status,
        "hardware_contact": 0,
        "flash": False,
        "reset": False,
        "fixed_url": {
            "url": FIXED_URL,
            "http_status": http_status,
            "bytes": http_bytes,
            "page_sha256": page_sha,
        },
        "same_source_frames": {
            "source_pack_status": source_manifest["status"],
            "source_state_count": source_manifest["invariants"]["state_count"],
            "source_unique_frame_count": source_manifest["invariants"][
                "unique_frame_count"
            ],
            "cemp_sha256": cemp_sha,
            "cemp_frame_count": cemp_verification["frame_count"],
            "cemp_clip_count": cemp_verification["clip_count"],
            "roundtrip_checks": cemp_verification["checks"],
        },
        "protected_function_audit": protected,
        "product_build": {
            "elf_sha256": sha256(product_elf),
            "hex_sha256": sha256(
                PRODUCT_BUILD / "Companion_Nucleo_WB55RG_Bringup.hex"
            ),
            "bin_sha256": sha256(
                PRODUCT_BUILD / "Companion_Nucleo_WB55RG_Bringup.bin"
            ),
            "ota_vector_address": "0x08007000",
            "recording_stage_blocks": 32,
        },
        "default_off_control": {"elf_sha256": sha256(default_elf)},
        "checks": checks,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "artifact": str(OUTPUT)}, ensure_ascii=False))
    return 0 if status == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
