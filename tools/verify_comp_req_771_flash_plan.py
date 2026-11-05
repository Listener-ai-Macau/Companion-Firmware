#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".cache/validation/comp-req-771-same-source-flash/PRECHECK_READY.json"
PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
SOURCE_ROOT = ROOT / ".cache/validation/comp-req-771-browser-life-source-pack-auto"
SOURCE_MANIFEST = SOURCE_ROOT / "source-pack-manifest.json"
CEMP_ROOT = SOURCE_ROOT / "cemp"
CEMP = CEMP_ROOT / "comp_req_771_browser_life.cemp"
CEMP_MANIFEST = CEMP_ROOT / "manifest.json"
CEMP_VERIFICATION = CEMP_ROOT / "verification.json"
BUILD_ROOT = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup"
PRODUCT_BUILD = BUILD_ROOT / "build_comp_req_771_current_ota_product"
PRODUCT_MAP = PRODUCT_BUILD / "Companion_Nucleo_WB55RG_Bringup.map"
CONTRACT = PRODUCT_BUILD / "generated/companion_browser_cemp_contract.json"
PROVISION_CHUNK_BYTES = 0x40000


def make_provision_chunks(pack_bytes: int) -> tuple[dict[str, object], ...]:
    chunks = []
    for index, offset in enumerate(range(0, pack_bytes, PROVISION_CHUNK_BYTES)):
        chunks.append(
            {
                "name": f"provision_chunk_{index}",
                "build": BUILD_ROOT
                / f"build_comp_req_771_current_provision_chunk_{index}",
                "target": f"Companion_CompReq771_ProvisionChunk{index}",
                "offset": offset,
                "bytes": min(PROVISION_CHUNK_BYTES, pack_bytes - offset),
                "finalizes_pack": index == 0,
            }
        )
    return tuple(chunks)


PROVISION_CHUNKS = make_provision_chunks(CEMP.stat().st_size)
FILES = {
    "loader": ROOT
    / "cubeide/Companion_BLE_Ota_Loader/build/Companion_BLE_Ota_Loader.hex",
    "app": PRODUCT_BUILD / "Companion_Nucleo_WB55RG_Bringup.hex",
    **{
        chunk["name"]: chunk["build"] / f"{chunk['target']}.hex"
        for chunk in PROVISION_CHUNKS
    },
}
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
APP_BLE = BUILD_ROOT / "Core/Src/app_ble.c"
MAIN = BUILD_ROOT / "Core/Src/main.c"
MAKEFILE = BUILD_ROOT / "Makefile"
FIXED_URL = (
    "http://127.0.0.1:4185/"
    ".cache/validation/comp-req-628-status-bar/index.html"
)
EXPECTED_IMAGES = {
    "loader": "7AF74009DCDCC82601DE1F04BEC94248FC5CE48C9B44F6298A44B0763FBD8324",
}
EXPECTED_DRIVER_FUNCTIONS = {
    "ssd1681_native_cached_mode2_movement_activation": (
        "EE83A0BA3366357C93233FEB7EBD7E581FA39B6A12379FDFCE28FF949D8954F8"
    ),
    "ssd1681_native_two_pass_activation": (
        "D01C9FF988A11BF976F412469A6E769BC72DDAAB1D11B7B4D9FAF8EEC15115B7"
    ),
}
LIFE_FAMILIES = (
    "calm",
    "curious",
    "warm",
    "delighted",
    "thoughtful",
    "alert",
)
EXPECTED_LIFE_BEATS = [
    ("calm", "rest", 0, 2, "hold", 0, 2, "life_calm_e0_s0_rest_hold"),
    (
        "calm",
        "notice_right",
        0,
        1,
        "orient",
        0,
        2,
        "life_calm_e0_s0_notice_right_orient",
    ),
    (
        "calm",
        "notice_right",
        0,
        2,
        "anticipate",
        1,
        3,
        "life_calm_e0_s1_notice_right_anticipate",
    ),
    (
        "calm",
        "notice_right",
        0,
        2,
        "accent",
        1,
        2,
        "life_calm_e0_s2_notice_right_accent",
    ),
    (
        "calm",
        "notice_right",
        0,
        0,
        "follow",
        2,
        2,
        "life_calm_e0_s3_notice_right_follow",
    ),
    (
        "calm",
        "notice_right",
        0,
        0,
        "settle",
        2,
        3,
        "life_calm_e0_s4_notice_right_settle",
    ),
    ("calm", "rest", 1, 0, "hold", 1, 3, "life_calm_e1_s0_rest_hold"),
]


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


def parse_ihex(path: Path) -> dict[int, int]:
    memory: dict[int, int] = {}
    upper = 0
    for line in path.read_text(encoding="ascii").splitlines():
        if not line.startswith(":"):
            continue
        record = bytes.fromhex(line[1:])
        length = record[0]
        address = int.from_bytes(record[1:3], "big")
        kind = record[3]
        data = record[4 : 4 + length]
        if kind == 0:
            for offset, value in enumerate(data):
                memory[upper + address + offset] = value
        elif kind == 2:
            upper = int.from_bytes(data, "big") << 4
        elif kind == 4:
            upper = int.from_bytes(data, "big") << 16
    if not memory:
        raise RuntimeError(f"no data records: {path}")
    return memory


def word(memory: dict[int, int], address: int) -> int:
    return int.from_bytes(
        bytes(memory.get(address + offset, 0xFF) for offset in range(4)), "little"
    )


def pbm_pixels(path: Path) -> bytes:
    header = b"P4\n200 200\n"
    payload = path.read_bytes()
    if not payload.startswith(header) or len(payload) != len(header) + 5000:
        raise RuntimeError(f"invalid native 200x200 PBM: {path}")
    return payload[len(header) :]


def main() -> int:
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    cemp_manifest = json.loads(CEMP_MANIFEST.read_text(encoding="utf-8"))
    cemp_verification = json.loads(CEMP_VERIFICATION.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    driver = DRIVER.read_text(encoding="utf-8")
    app_ble = APP_BLE.read_text(encoding="utf-8")
    main_source = MAIN.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    product_map = PRODUCT_MAP.read_text(encoding="utf-8")
    cemp_bytes = CEMP.read_bytes()
    expected_page = sha256(PAGE)
    expected_cemp = sha256(CEMP)
    cemp_string_bytes = int.from_bytes(cemp_bytes[44:48], "little")

    clip_start: dict[str, int] = {}
    frame_index = 0
    for clip in cemp_manifest["clips"]:
        clip_start[clip["name"]] = frame_index
        frame_index += len(clip["frames"])
    expected_calm_life_prefix = [
        {
            "family": beat[0],
            "action": beat[1],
            "episode": beat[2],
            "phrase": beat[3],
            "phase": beat[4],
            "variation": beat[5],
            "dwell_commits": beat[6],
            "clip": beat[7],
            "frame_index": clip_start.get(beat[7]),
        }
        for beat in EXPECTED_LIFE_BEATS
    ]

    images = {}
    image_memories: dict[str, dict[int, int]] = {}
    for name, path in FILES.items():
        memory = parse_ihex(path)
        image_memories[name] = memory
        low, high = min(memory), max(memory)
        images[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "minimum_address": f"0x{low:08X}",
            "maximum_address": f"0x{high:08X}",
            "programmed_bytes": len(memory),
            "msp": f"0x{word(memory, low):08X}",
            "reset_vector": f"0x{word(memory, low + 4):08X}",
        }
        if name != "loader":
            magic_pointer = word(memory, 0x08007140)
            images[name]["magic_pointer"] = f"0x{magic_pointer:08X}"
            images[name]["magic_value"] = f"0x{word(memory, magic_pointer):08X}"

    chunk_evidence = []
    for chunk in PROVISION_CHUNKS:
        name = str(chunk["name"])
        receipt_path = (
            chunk["build"]
            / "generated"
            / "companion_screen_asset_provision_chunk.json"
        )
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        expected_slice = cemp_bytes[
            int(chunk["offset"]) : int(chunk["offset"]) + int(chunk["bytes"])
        ]
        memory = image_memories[name]
        low, high = min(memory), max(memory)
        image_bytes = bytes(
            memory.get(address, 0xFF) for address in range(low, high + 1)
        )
        chunk_evidence.append(
            {
                "name": name,
                "offset": int(chunk["offset"]),
                "bytes": int(chunk["bytes"]),
                "finalizes_pack": bool(chunk["finalizes_pack"]),
                "receipt": str(receipt_path.relative_to(ROOT)),
                "receipt_input_sha256": receipt["input_sha256"],
                "receipt_chunk_sha256": receipt["chunk_sha256"],
                "expected_chunk_sha256": hashlib.sha256(
                    expected_slice
                ).hexdigest().upper(),
                "embedded_exactly_once": image_bytes.count(expected_slice) == 1,
                "receipt_exact": (
                    receipt["input_bytes"] == len(cemp_bytes)
                    and receipt["input_sha256"] == expected_cemp
                    and receipt["chunk_offset"] == int(chunk["offset"])
                    and receipt["chunk_bytes"] == int(chunk["bytes"])
                    and receipt["chunk_sha256"]
                    == hashlib.sha256(expected_slice).hexdigest().upper()
                    and receipt["finalizes_pack"]
                    == bool(chunk["finalizes_pack"])
                    and receipt["sector_size"] == 4096
                    and receipt["header_commit_bytes"]
                    == (4096 if chunk["finalizes_pack"] else 0)
                ),
            }
        )

    protected_driver = {}
    for name, expected in EXPECTED_DRIVER_FUNCTIONS.items():
        observed = hashlib.sha256(
            extract_function(driver, f"static bool {name}").encode("utf-8")
        ).hexdigest().upper()
        protected_driver[name] = {
            "expected_raw_sha256": expected,
            "observed_raw_sha256": observed,
            "matches": observed == expected,
        }

    accepted_product_body = extract_function(
        driver,
        "static comp_epaper_panel_result_t "
        "ssd1681_accepted_cached_mode2_product_refresh",
    )
    accepted_prepare = accepted_product_body.find(
        "companion_epaper_panel_stm32wb_ssd1681_comp_req_616_prepare()"
    )
    accepted_frame_prepare = accepted_product_body.find(
        "frame_prepare(target->expression_assets, request)"
    )
    accepted_full = accepted_product_body.find(
        "companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff("
    )
    accepted_cached = accepted_product_body.find(
        "companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff("
    )
    cached_diff_body = extract_function(
        driver,
        "bool companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff",
    )

    try:
        local_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with local_opener.open(FIXED_URL, timeout=5) as response:
            http_status = response.status
    except Exception:
        http_status = 0

    family_counts = source_manifest["invariants"]["life_episode_counts"]
    source_state_by_id = {
        state["id"]: state for state in source_manifest["states"]
    }
    stable_status_hashes = {
        hashlib.sha256(
            pbm_pixels(SOURCE_ROOT / state["pbm_file"])[: 25 * 20]
        ).hexdigest()
        for state in source_manifest["states"]
        if state.get("kind") != "upgrade_progress"
    }
    stable_status = pbm_pixels(
        SOURCE_ROOT
        / next(
            state["pbm_file"]
            for state in source_manifest["states"]
            if state.get("kind") != "upgrade_progress"
        )
    )[: 25 * 20]
    upgrade_status_diffs = []
    for state in source_manifest["states"]:
        if state.get("kind") != "upgrade_progress":
            continue
        status = pbm_pixels(SOURCE_ROOT / state["pbm_file"])[: 25 * 20]
        changed = []
        for byte_index, (baseline_byte, status_byte) in enumerate(
            zip(stable_status, status)
        ):
            delta = baseline_byte ^ status_byte
            for bit_index in range(8):
                if delta & (1 << (7 - bit_index)):
                    changed.append(
                        ((byte_index % 25) * 8 + bit_index, byte_index // 25)
                    )
        upgrade_status_diffs.append(changed)
    life_status_hashes = {
        hashlib.sha256(
            pbm_pixels(SOURCE_ROOT / state["pbm_file"])[: 25 * 26]
        ).hexdigest()
        for state in source_manifest["states"]
        if state.get("kind") == "life"
    }
    expected_life_metadata_exact = all(
        beat[7] in source_state_by_id
        and source_state_by_id[beat[7]].get("family") == beat[0]
        and source_state_by_id[beat[7]].get("life_action") == beat[1]
        and source_state_by_id[beat[7]].get("action_episode") == beat[2]
        and source_state_by_id[beat[7]].get("phrase") == beat[3]
        and source_state_by_id[beat[7]].get("phase") == beat[4]
        and source_state_by_id[beat[7]].get("variation") == beat[5]
        and source_state_by_id[beat[7]].get("dwell_commits") == beat[6]
        for beat in EXPECTED_LIFE_BEATS
    )
    checks = {
        "fixed_url_http_200": http_status == 200,
        "page_identity": (
            source_manifest["source"]["page_sha256"] == expected_page
            and contract["browser_page_sha256"] == expected_page
        ),
        "cemp_identity": (
            contract["cemp_sha256"] == expected_cemp
            and cemp_verification["pack_sha256"] == expected_cemp
        ),
        "browser_source_pack_exact": (
            source_manifest["source"]["page_sha256"] == expected_page
            and source_manifest["format"]["width"] == 200
            and source_manifest["format"]["height"] == 200
            and source_manifest["format"]["stride_bytes"] == 25
            and source_manifest["invariants"]["all_inputs_binary"]
            and source_manifest["invariants"]["state_count"]
            == len(source_manifest["states"])
            and source_manifest["invariants"]["unique_frame_count"] > 0
            and set(family_counts) == set(LIFE_FAMILIES)
            and all(count == 32 for count in family_counts.values())
        ),
        "browser_cemp_exact": (
            cemp_verification["status"] == "PASS_CEMP_EXTERNAL_SOURCE_BOUND"
            and all(cemp_verification["checks"].values())
            and cemp_verification["pack_sha256"] == expected_cemp
            and cemp_verification["pack_bytes"] == len(cemp_bytes)
            and cemp_verification["clip_count"] == len(cemp_manifest["clips"])
            and cemp_verification["frame_count"] == frame_index
            and cemp_manifest["source"]["unique_frame_count"]
            == source_manifest["invariants"]["unique_frame_count"]
        ),
        "generated_contract_exact": (
            contract["status"] == "PASS"
            and contract["cemp_sha256"] == expected_cemp
            and contract["browser_page_sha256"] == expected_page
            and contract["clip_count"] == cemp_verification["clip_count"]
            and contract["frame_count"] == cemp_verification["frame_count"]
            and contract["string_bytes"] == cemp_string_bytes
            and contract["total_bytes"] == len(cemp_bytes)
            and contract["life_episode_limit"] == 32
        ),
        "first_calm_life_prefix_resolves": (
            all(beat["frame_index"] is not None for beat in expected_calm_life_prefix)
            and expected_life_metadata_exact
        ),
        "product_uses_generated_browser_contract": (
            "COMPANION_BROWSER_CEMP_CLIP_COUNT" in app_ble
            and "COMPANION_BROWSER_CEMP_FRAME_COUNT" in app_ble
            and "COMPANION_BROWSER_CEMP_STRING_BYTES" in app_ble
            and "COMPANION_BROWSER_LIFE_FAMILY_MASK" in app_ble
            and "COMPANION_BROWSER_LIFE_EPISODE_LIMIT" in app_ble
            and '"life_%s_e%lu_s%u_%s_%s"' in app_ble
            and "motion_request->action_step" in app_ble
            and "#define COMP_REQ_638_CEMP_CLIP_COUNT 1167u" not in app_ble
            and "#define COMP_REQ_638_CEMP_FRAME_COUNT 1177u" not in app_ble
        ),
        "make_chain_starts_at_fixed_page": (
            "BROWSER_PAGE_REPO_PATH := .cache/validation/comp-req-628-status-bar/index.html"
            in makefile
            and "comp-req-771-browser-life-source-pack-auto" in makefile
            and "generate_comp_req_628_source_pack.mjs" in makefile
            and "generate_comp_req_638_cemp_manifest.py" in makefile
            and "generate_browser_cemp_contract.py" in makefile
        ),
        "accepted_driver_functions_unchanged": all(
            item["matches"] for item in protected_driver.values()
        ),
        "product_calls_accepted_driver_path": (
            "ssd1681_native_no_reset_movement_activation(" in driver
            and "ssd1681_native_cached_mode2_movement_activation(" in driver
            and "ssd1681_accepted_product_apply_target_mapping" not in driver
        ),
        "status_bar_source_pixels_are_invariant": (
            len(stable_status_hashes) == 1
            and len(life_status_hashes) == 1
            and len(upgrade_status_diffs) == 5
            and all(
                changed
                and min(x for x, _ in changed) >= 103
                and max(x for x, _ in changed) <= 141
                and min(y for _, y in changed) >= 1
                and max(y for _, y in changed) <= 12
                for changed in upgrade_status_diffs
            )
        ),
        "accepted_product_uses_exact_comp_req_616_call_chain": (
            accepted_prepare >= 0
            and accepted_frame_prepare > accepted_prepare
            and accepted_full > accepted_frame_prepare
            and accepted_cached > accepted_full
            and "ssd1681_accepted_product_activate" not in driver
            and "ssd1681_accepted_product_prepare" not in driver
        ),
        "accepted_product_uses_fixed_comp_req_616_face_corridor": (
            "#if COMPANION_EPAPER_SSD1681_COMP_REQ_616_CANONICAL_SYNC ||"
            in cached_diff_body
            and "COMPANION_EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT"
            in cached_diff_body
            and ".x_start_byte = 4u" in cached_diff_body
            and ".x_end_byte = 21u" in cached_diff_body
            and ".y_start = 26u" in cached_diff_body
            and ".y_end = 179u" in cached_diff_body
        ),
        "accepted_product_reuses_mapped_previous_cache": (
            "#if COMPANION_EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT"
            in cached_diff_body
            and "(void)previous_frame;" in cached_diff_body
            and "ssd1681_comp_req_611_apply_r12_target_mapping(s_frame);"
            in cached_diff_body
            and "memcmp(s_frame, s_previous_frame, SSD1681_FRAME_BYTES)"
            in cached_diff_body
        ),
        "accepted_product_requires_comp_req_616_transport": (
            "Accepted cached Mode-2 product requires the COMP-REQ-616 direct GPIO SPI + BUSY transport"
            in driver
            and "!COMPANION_EPAPER_SSD1681_HAS_BUSY" in driver
            and "!COMPANION_EPAPER_SSD1681_USE_SOFTWARE_SPI" in driver
            and "!COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC" in driver
            and "COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_NOP_COUNT != 0u"
            in driver
        ),
        "external_cemp_reads_are_timeout_bounded": (
            "READ_CHUNK_BYTES = 4096u" in (
                BUILD_ROOT / "Core/Src/companion_screen_assets_stm32wb.c"
            ).read_text(encoding="utf-8")
        ),
        "real_ssd1681_driver_linked": (
            "panel_target_stm32wb_ssd1681.o" in product_map
            and "companion_epaper_panel_stm32wb_ssd1681_init" in product_map
            and ".text.ssd1681_refresh" in product_map
        ),
        "protected_image_identities": all(
            images[name]["sha256"] == expected
            for name, expected in EXPECTED_IMAGES.items()
        ),
        "external_ui_partition_is_2m": (
            "#define FLASH_UI_ASSETS_BASE 0x00000000u" in main_source
            and "#define FLASH_UI_ASSETS_SIZE 0x00200000u" in main_source
            and len(cemp_bytes) <= 0x00200000
        ),
        "provision_chunks_cover_exact_cemp": (
            [item["offset"] for item in chunk_evidence]
            == list(range(0, len(cemp_bytes), PROVISION_CHUNK_BYTES))
            and sum(item["bytes"] for item in chunk_evidence)
            == len(cemp_bytes)
            and all(
                item["receipt_exact"] and item["embedded_exactly_once"]
                for item in chunk_evidence
            )
        ),
        "provision_header_committed_last": (
            "COMPANION_SCREEN_ASSET_PROVISION_HEADER_COMMIT_BYTES"
            in main_source
            and "companion_screen_asset_provision_blob +"
            in main_source
            and "total_crc == COMPANION_SCREEN_ASSET_PROVISION_TOTAL_CRC32"
            in main_source
            and "SCREEN_ASSET_PROVISION_CHUNK_OFFSET" in makefile
            and "build_screen_asset_provision_chunk.py" in makefile
        ),
        "loader_bounded_to_reserved_region": (
            images["loader"]["minimum_address"] == "0x08000000"
            and int(images["loader"]["maximum_address"], 16) < 0x08007000
        ),
        "app_bounded_to_ota_region": (
            images["app"]["minimum_address"] == "0x08007000"
            and int(images["app"]["maximum_address"], 16) < 0x08080000
        ),
        "provision_chunks_bounded_to_ota_region": all(
            images[str(chunk["name"])]["minimum_address"] == "0x08007000"
            and int(
                images[str(chunk["name"])]["maximum_address"], 16
            ) < 0x08080000
            for chunk in PROVISION_CHUNKS
        ),
        "app_vector_valid": (
            int(images["app"]["msp"], 16) == 0x20030000
            and int(images["app"]["reset_vector"], 16) & 1 == 1
        ),
        "loader_vector_valid": (
            int(images["loader"]["msp"], 16) == 0x20030000
            and int(images["loader"]["reset_vector"], 16) & 1 == 1
        ),
        "app_ota_magic_valid": images["app"]["magic_value"] == "0x94448A29",
        "provision_ota_magic_valid": all(
            images[str(chunk["name"])]["magic_value"] == "0x94448A29"
            for chunk in PROVISION_CHUNKS
        ),
    }
    status = "PRECHECK_READY" if all(checks.values()) else "NO_GO"
    artifact = {
        "schema": "companion.comp_req_771.flash_plan.v2",
        "requirement": "COMP-REQ-771",
        "status": status,
        "hardware_contact": 0,
        "write_calls": 0,
        "erase_calls": 0,
        "fixed_url": FIXED_URL,
        "fixed_url_http_status": http_status,
        "page_sha256": sha256(PAGE),
        "cemp": {
            "path": str(CEMP.relative_to(ROOT)),
            "sha256": sha256(CEMP),
            "bytes": CEMP.stat().st_size,
            "clip_count": cemp_verification["clip_count"],
            "frame_count": cemp_verification["frame_count"],
            "string_bytes": contract["string_bytes"],
            "unique_frame_count": source_manifest["invariants"]["unique_frame_count"],
        },
        "expected_calm_life_prefix": expected_calm_life_prefix,
        "images": images,
        "external_ui_partition": {
            "base": "0x000000",
            "capacity_bytes": 0x200000,
            "cemp_bytes": len(cemp_bytes),
            "provision_order": list(
                reversed(range(len(PROVISION_CHUNKS)))
            ),
            "header_commit_bytes": 4096,
        },
        "provision_chunks": chunk_evidence,
        "protected_driver": protected_driver,
        "checks": checks,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "artifact": str(OUTPUT)}))
    return 0 if status == "PRECHECK_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
