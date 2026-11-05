#!/usr/bin/env python3
"""Fail-closed offline verifier for the COMP-REQ-471 upper visual contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any


EXPECTED_URL = (
    "http://127.0.0.1:4173/docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/candidate/"
    "wb55-browser-parity-attempt-01/index.html"
)
EXPECTED_STATE_COUNT = 17
EXPECTED_FRAME_BYTES = 5000
EXPECTED_UNIQUE_FRAME_COUNT = 13
EXPECTED_PAYLOAD_BYTES = 65000
EXPECTED_PAIR_COUNT = 59
EXPECTED_NOOP_COUNT = 10
EXPECTED_MENU_FULL_FRAME_COUNT = 10

VALIDATION_DIR = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471"
)
EXPORT_DIR = Path("docs/art/exports/companion-browser-visual-contract-comp-req-471")

EXPECTED_FILES: dict[str, tuple[str, str, str]] = {
    "page": (
        "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
        "candidate/wb55-browser-parity-attempt-01/index.html",
        "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E",
        "html",
    ),
    "machine": (
        f"{VALIDATION_DIR.as_posix()}/machine-result.json",
        "6A7EDAC4A9624842B154B717C090441E745AC6F65F8E73BC235E8E3C16D11EBD",
        "json",
    ),
    "measured_diagnostic": (
        f"{VALIDATION_DIR.as_posix()}/measured-diagnostic.json",
        "652C33E7BFB155974FD369DB069800E14595C26F5F1D7B6A7322ED30320CCA76",
        "json",
    ),
    "capture": (
        f"{VALIDATION_DIR.as_posix()}/browser-capture/capture-manifest.json",
        "1BEA10C8B988F72F48886012859F1D6C8801B15AFA18E89171235B7E33D2C815",
        "json",
    ),
    "pointer": (
        f"{VALIDATION_DIR.as_posix()}/pointer-contract/"
        "touch-pointer-contract-result.json",
        "082344F03017DC54E0A385E5CFF8BB7F4031889A602476FFD2589B130CFFE09F",
        "json",
    ),
    "frames": (
        f"{EXPORT_DIR.as_posix()}/frames.bin",
        "D4DA2FCA6863C1B8F5DD28D70566712DCD91AB7383CA486735DFD253F7361E6D",
        "binary",
    ),
    "visual_contract": (
        f"{EXPORT_DIR.as_posix()}/visual-contract.json",
        "E5C6B30D8BF317FC8321D82E087D3B46552B4523FD8B67FFF3E6ABA89AAE4260",
        "json",
    ),
    "state_transitions": (
        f"{EXPORT_DIR.as_posix()}/state-transitions.json",
        "442F5A9E87988A3F8BE15ECC2A2500CA64537FA2B6DBD96F6FFDDD070DD7F918",
        "json",
    ),
    "c_pack_result": (
        f"{EXPORT_DIR.as_posix()}/c-asset-pack-machine-result.json",
        "17B71D7AC5FC777FEB301EED39E70431CC65BEFF8CC25FD7EEC613206280CD1E",
        "json",
    ),
    "c_pack_manifest": (
        f"{EXPORT_DIR.as_posix()}/c-asset-pack-manifest.json",
        "0F0FE7B91707F20CF942A0B994BD776B69D404A004D9985B98EC6838CA752DBA",
        "json",
    ),
    "c_pack_header": (
        f"{EXPORT_DIR.as_posix()}/companion_visual_asset_pack.h",
        "2180FE281AFF31C8688BCB290740F898CF7E032C90D97FFE679F535689A814F9",
        "c_header",
    ),
    "c_pack_source": (
        f"{EXPORT_DIR.as_posix()}/companion_visual_asset_pack.c",
        "1EE7BD5DDB210A3C3F90ADB607BA317CF2F00127099B876C9DB5948C7A5D03A0",
        "c_source",
    ),
    "c_pack_handoff": (
        f"{EXPORT_DIR.as_posix()}/c-asset-pack-handoff.json",
        "982B582FAEDDF956AF8557A9A333362A0D91DD7CA92FB3E0E7A37FC3D79F14D9",
        "json",
    ),
    "expanded_oracle": (
        f"{EXPORT_DIR.as_posix()}/expanded-window-oracle.json",
        "20C270A332F7AD75FAED3C44C9AE3C1D789F7902ABA525C07B0B40F4266C5B2E",
        "json",
    ),
    "physical_boundary": (
        f"{EXPORT_DIR.as_posix()}/physical-consumer-boundary.json",
        "FE4D44152F51E0496B3AEF0B0594F557995D09FE31A9148440DA98209D119DDC",
        "json",
    ),
    "expanded_oracle_result": (
        f"{VALIDATION_DIR.as_posix()}/expanded-window-oracle-machine-result.json",
        "4846266B1AE7DE40489598B7FFB05711F52110898D1C5938EC6FD3EB662FB957",
        "json",
    ),
    "owner_runner": (
        "tools/faraday_upper_art/"
        "run_companion_browser_owner_review_comp_req_471.ps1",
        "6739E7BDF6CEB8118CC8ED9E660D5FB193F110D36E5D84F3C152753D9A424C81",
        "powershell",
    ),
    "owner_supervisor": (
        "tools/faraday_upper_art/"
        "supervise_companion_browser_owner_review_comp_req_471.ps1",
        "E7E599F906886030B95B47A17B0ADA88F8648A232F2A45D0C86C901AD9096F87",
        "powershell",
    ),
    "owner_checkonly": (
        f"{VALIDATION_DIR.as_posix()}/owner-review-checkonly.json",
        "21FCE148BBD11C68074F98EE10E8F1A75A0DD4D86FAC4F65EE7CB03CFFABDCC7",
        "json",
    ),
    "protected_owner_acceptance": (
        "docs/validation/"
        "companion-pet-special-system-owner-acceptance-20260717.json",
        "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
        "raw_owner_note",
    ),
}

EXPECTED_MUTATIONS = [
    {
        "id": "page_hash_drift",
        "binding_class": "browser_page",
        "target": "files.page.sha256",
        "value": "0" * 64,
        "expected_check": "file_hash.page",
    },
    {
        "id": "machine_frame_count_drift",
        "binding_class": "machine_result",
        "target": "machine.frames",
        "value": 16,
        "expected_check": "machine.structure",
    },
    {
        "id": "capture_stale_layer",
        "binding_class": "capture",
        "target": "capture.stale_count",
        "value": 1,
        "expected_check": "capture.structure",
    },
    {
        "id": "pointer_negative_false",
        "binding_class": "pointer",
        "target": "pointer.negative_all_true",
        "value": False,
        "expected_check": "pointer.structure",
    },
    {
        "id": "bound_child_hash_drift",
        "binding_class": "per_file_rehash",
        "target": "rehash.mismatch_count",
        "value": 1,
        "expected_check": "rehash.all_bound_files",
    },
    {
        "id": "frame_count_drift",
        "binding_class": "17_state_frames",
        "target": "frames.frame_count",
        "value": 16,
        "expected_check": "frames.structure",
    },
    {
        "id": "pack_unique_count_drift",
        "binding_class": "c_asset_pack",
        "target": "c_pack.unique_frame_count",
        "value": 12,
        "expected_check": "c_pack.structure",
    },
    {
        "id": "pack_payload_capacity_drift",
        "binding_class": "c_asset_pack",
        "target": "c_pack.payload_bytes",
        "value": 64999,
        "expected_check": "c_pack.structure",
    },
    {
        "id": "oracle_pair_count_drift",
        "binding_class": "expanded_window_oracle",
        "target": "oracle.pair_count",
        "value": 58,
        "expected_check": "oracle.structure",
    },
    {
        "id": "oracle_noop_count_drift",
        "binding_class": "expanded_window_oracle",
        "target": "oracle.pixel_noop_pair_count",
        "value": 9,
        "expected_check": "oracle.structure",
    },
    {
        "id": "oracle_menu_full_count_drift",
        "binding_class": "expanded_window_oracle",
        "target": "oracle.menu_full_frame_pair_count",
        "value": 9,
        "expected_check": "oracle.structure",
    },
    {
        "id": "oracle_nonmenu_full_frame",
        "binding_class": "expanded_window_oracle",
        "target": "oracle.nonmenu_full_frame_pair_count",
        "value": 1,
        "expected_check": "oracle.structure",
    },
    {
        "id": "physical_guard_collapse",
        "binding_class": "physical_consumer_boundary",
        "target": "physical_boundary.guards_separated",
        "value": False,
        "expected_check": "physical_boundary.structure",
    },
    {
        "id": "owner_runner_hash_drift",
        "binding_class": "owner_review_runner",
        "target": "files.owner_runner.sha256",
        "value": "1" * 64,
        "expected_check": "file_hash.owner_runner",
    },
    {
        "id": "owner_supervisor_hash_drift",
        "binding_class": "owner_review_supervisor",
        "target": "files.owner_supervisor.sha256",
        "value": "2" * 64,
        "expected_check": "file_hash.owner_supervisor",
    },
    {
        "id": "owner_checkonly_hash_drift",
        "binding_class": "owner_review_checkonly",
        "target": "files.owner_checkonly.sha256",
        "value": "3" * 64,
        "expected_check": "file_hash.owner_checkonly",
    },
    {
        "id": "owner_checkonly_duplicate_button",
        "binding_class": "owner_review_checkonly",
        "target": "owner_review.prompt_contract_exact",
        "value": False,
        "expected_check": "owner_review.checkonly",
    },
    {
        "id": "protected_owner_acceptance_hash_drift",
        "binding_class": "protected_owner_acceptance",
        "target": "files.protected_owner_acceptance.sha256",
        "value": "4" * 64,
        "expected_check": "file_hash.protected_owner_acceptance",
    },
    {
        "id": "owner_result_exists",
        "binding_class": "owner_result_absence",
        "target": "owner_review.owner_result_count",
        "value": 1,
        "expected_check": "owner_review.result_absent",
    },
    {
        "id": "execute_counter_nonzero",
        "binding_class": "side_effect_counters",
        "target": "side_effects.execute",
        "value": 1,
        "expected_check": "side_effects.zero",
    },
    {
        "id": "prompt_counter_nonzero",
        "binding_class": "side_effect_counters",
        "target": "side_effects.prompt",
        "value": 1,
        "expected_check": "side_effects.zero",
    },
    {
        "id": "server_counter_nonzero",
        "binding_class": "side_effect_counters",
        "target": "side_effects.server",
        "value": 1,
        "expected_check": "side_effects.zero",
    },
    {
        "id": "hardware_counter_nonzero",
        "binding_class": "side_effect_counters",
        "target": "side_effects.hardware",
        "value": 1,
        "expected_check": "side_effects.zero",
    },
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.as_posix()} is not a JSON object")
    return value


def all_true(node: dict[str, Any]) -> bool:
    return bool(node) and all(value is True for value in node.values())


def transition_states(item: dict[str, Any], key: str) -> list[str]:
    if key in item:
        return [str(item[key])]
    values = item.get(f"{key}_any")
    if not isinstance(values, list):
        raise ValueError(f"transition lacks {key}/{key}_any")
    return [str(value) for value in values]


def parse_c_block(text: str, declaration: str) -> str:
    match = re.search(
        re.escape(declaration) + r"\s*=\s*\{\s*(.*?)\s*\};",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"cannot parse generated C block: {declaration}")
    return match.group(1)


def parse_unsigned_values(block: str) -> list[int]:
    return [int(value) for value in re.findall(r"\b(\d+)u\b", block)]


def set_dotted(root: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    node: dict[str, Any] = root
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            raise KeyError(f"fixture target parent is not an object: {dotted}")
        node = child
    if parts[-1] not in node:
        raise KeyError(f"fixture target does not exist: {dotted}")
    node[parts[-1]] = value


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


class RehashLedger:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.records: dict[str, dict[str, Any]] = {}

    def add(self, relative: str, expected: str, binding: str, parser: str) -> None:
        relative = Path(relative).as_posix()
        path = self.repo_root / relative
        record = self.records.get(relative)
        if record is None:
            exists = path.is_file()
            observed = file_sha(path) if exists else None
            record = {
                "path": relative,
                "parser": parser,
                "exists": exists,
                "bytes": path.stat().st_size if exists else None,
                "sha256": observed,
                "expected_sha256": expected,
                "expected_hash_conflict": False,
                "bindings": [],
            }
            self.records[relative] = record
        elif record["expected_sha256"] != expected:
            record["expected_hash_conflict"] = True
        if binding not in record["bindings"]:
            record["bindings"].append(binding)

    def finalize(self) -> list[dict[str, Any]]:
        result = []
        for relative in sorted(self.records):
            record = copy.deepcopy(self.records[relative])
            record["bindings"].sort()
            record["match"] = (
                record["exists"]
                and not record["expected_hash_conflict"]
                and record["sha256"] == record["expected_sha256"]
            )
            result.append(record)
        return result


def compute_changed(previous: bytes, current: bytes) -> dict[str, Any]:
    changed_byte_count = 0
    changed_pixel_count = 0
    xs: list[int] = []
    ys: list[int] = []
    for index, (left, right) in enumerate(zip(previous, current)):
        delta = left ^ right
        if delta == 0:
            continue
        changed_byte_count += 1
        changed_pixel_count += delta.bit_count()
        y = index // 25
        x_byte = index % 25
        for bit in range(8):
            if delta & (1 << (7 - bit)):
                xs.append(x_byte * 8 + bit)
                ys.append(y)
    if not xs:
        return {
            "changed_byte_count": 0,
            "changed_pixel_count": 0,
            "bounds": None,
            "window": None,
            "payload": b"",
        }
    bounds = {
        "x_min": min(xs),
        "y_min": min(ys),
        "x_max": max(xs),
        "y_max": max(ys),
        "width": max(xs) - min(xs) + 1,
        "height": max(ys) - min(ys) + 1,
    }
    x_byte_start = bounds["x_min"] // 8
    x_byte_end = bounds["x_max"] // 8
    row_bytes = x_byte_end - x_byte_start + 1
    rows = bounds["height"]
    payload = b"".join(
        current[y * 25 + x_byte_start : y * 25 + x_byte_end + 1]
        for y in range(bounds["y_min"], bounds["y_max"] + 1)
    )
    window = {
        "x_byte_start": x_byte_start,
        "x_byte_end": x_byte_end,
        "x_pixel_start": x_byte_start * 8,
        "x_pixel_end": x_byte_end * 8 + 7,
        "y_start": bounds["y_min"],
        "y_end": bounds["y_max"],
        "row_bytes": row_bytes,
        "rows": rows,
        "payload_bytes": len(payload),
        "full_frame": len(payload) == EXPECTED_FRAME_BYTES,
    }
    return {
        "changed_byte_count": changed_byte_count,
        "changed_pixel_count": changed_pixel_count,
        "bounds": bounds,
        "window": window,
        "payload": payload,
    }


def collect_error_lists(node: Any) -> int:
    count = 0
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"errors", "failed", "validation_errors"} and value:
                count += len(value) if isinstance(value, list) else 1
            count += collect_error_lists(value)
    elif isinstance(node, list):
        for value in node:
            count += collect_error_lists(value)
    return count


def build_facts(repo_root: Path, fixtures_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ledger = RehashLedger(repo_root)
    for file_id, (relative, expected, parser) in EXPECTED_FILES.items():
        ledger.add(relative, expected, f"primary:{file_id}", parser)

    paths = {
        key: repo_root / relative
        for key, (relative, _expected, _parser) in EXPECTED_FILES.items()
    }
    machine = load_json(paths["machine"])
    measured = load_json(paths["measured_diagnostic"])
    capture = load_json(paths["capture"])
    pointer = load_json(paths["pointer"])
    visual = load_json(paths["visual_contract"])
    transitions = load_json(paths["state_transitions"])
    pack_result = load_json(paths["c_pack_result"])
    pack_manifest = load_json(paths["c_pack_manifest"])
    pack_handoff = load_json(paths["c_pack_handoff"])
    oracle = load_json(paths["expanded_oracle"])
    boundary = load_json(paths["physical_boundary"])
    oracle_result = load_json(paths["expanded_oracle_result"])
    checkonly = load_json(paths["owner_checkonly"])

    capture_root = paths["capture"].parent
    for relative, expected in machine["artifact_file_sha256"]["canonical_capture"].items():
        ledger.add(
            (capture_root / relative).relative_to(repo_root).as_posix(),
            expected,
            "machine:canonical_capture",
            "artifact",
        )
    export_root = paths["visual_contract"].parent
    for relative, expected in machine["artifact_file_sha256"]["canonical_export"].items():
        ledger.add(
            (export_root / relative).relative_to(repo_root).as_posix(),
            expected,
            "machine:canonical_export",
            "artifact",
        )
    for item in capture["source_assets"]:
        ledger.add(
            item["repo_path"],
            item["sha256"],
            "capture:source_asset",
            "source_asset",
        )
    for item in checkonly["readiness"]["identities"]:
        ledger.add(
            item["path"],
            item["expected_sha256"],
            "owner_checkonly:identity",
            "bound_identity",
        )
    for relative, expected in pack_manifest["generated_files"].items():
        ledger.add(
            (export_root / relative).relative_to(repo_root).as_posix(),
            expected,
            "c_pack_manifest:generated_file",
            "generated_c",
        )

    rehash_records = ledger.finalize()
    records_by_path = {item["path"]: item for item in rehash_records}
    files: dict[str, Any] = {}
    for file_id, (relative, expected, parser) in EXPECTED_FILES.items():
        record = records_by_path[Path(relative).as_posix()]
        files[file_id] = {
            "path": record["path"],
            "parser": parser,
            "exists": record["exists"],
            "bytes": record["bytes"],
            "sha256": record["sha256"],
            "expected_sha256": expected,
        }

    machine_artifacts_match = (
        machine["artifacts"]["frames_bin_sha256"] == files["frames"]["sha256"]
        and machine["artifacts"]["visual_contract_sha256"]
        == files["visual_contract"]["sha256"]
        and machine["artifacts"]["state_transitions_sha256"]
        == files["state_transitions"]["sha256"]
        and machine["artifacts"]["capture_manifest_sha256"]
        == files["capture"]["sha256"]
        and machine["fresh_browser_interaction"]["pointer_result_sha256"]
        == files["pointer"]["sha256"]
    )
    pointer_matrix = machine["fresh_browser_interaction"]["pointer_matrix"]
    pointer_matrix_all_true = all(
        pointer_matrix[viewport][kind] is True
        for viewport in ("desktop", "mobile")
        for kind in ("mouse", "touch", "pen")
    )
    route_counts_exact = all(
        machine["routes"][viewport]["menu_entries"] == 1
        and machine["routes"][viewport]["recording_entries"] == 1
        for viewport in ("desktop", "mobile")
    )

    capture_state_errors: list[str] = []
    capture_states = capture["states"]
    for item in capture_states:
        semantic = item["semantic"]
        if semantic["primary_surface_count"] != 1:
            capture_state_errors.append(f"{item['id']}: primary surface count")
        if (
            semantic["expression_face_count"]
            + semantic["exclusive_menu_surface_count"]
            != 1
        ):
            capture_state_errors.append(f"{item['id']}: face/menu exclusivity")
        if semantic["gaze_highlight_count"] > 1:
            capture_state_errors.append(f"{item['id']}: gaze count")
        if semantic["stale_layer_count"] != 0:
            capture_state_errors.append(f"{item['id']}: stale layer")
        if semantic["conflicting_surface_overlap_count"] != 0:
            capture_state_errors.append(f"{item['id']}: overlap")
    capture_by_viewport: dict[str, dict[str, dict[str, Any]]] = {
        "desktop": {},
        "mobile": {},
    }
    for item in capture_states:
        viewport = item["png"].split("/")[1]
        capture_by_viewport[viewport][item["id"]] = item
    capture_returns_equal = all(
        capture_by_viewport[viewport]["centered_rest"]["png_sha256"]
        == capture_by_viewport[viewport]["menu_return_rest"]["png_sha256"]
        == capture_by_viewport[viewport]["recording_return_rest"]["png_sha256"]
        for viewport in ("desktop", "mobile")
    )
    hold_regressions = capture["capture"]["hold_feedback_binding"][
        "real_pointer_regressions"
    ]
    hold_exact = (
        len(hold_regressions) == 2
        and all(
            item["real_stationary_pointer_hold"] is True
            and item["resulting_mode"] == "menu"
            and item["menu_entries"] == 1
            and item["recording_entries"] == 0
            and item["route_exactly_once"] is True
            for item in hold_regressions
        )
    )

    expected_scenarios = {
        "mouse_single",
        "touch_single",
        "pen_single",
        "touch_double",
        "mouse_drag",
        "touch_drag",
        "pen_drag",
        "mouse_hold",
        "pointercancel",
        "lostpointercapture",
        "blur",
    }
    pointer_scenario_keys_exact = all(
        set(pointer["scenarios"][viewport]) == expected_scenarios
        for viewport in ("desktop", "mobile")
    )
    pointer_layout_exact = all(
        pointer["layout"][viewport]["center_delta_px"] == 0
        and pointer["layout"][viewport]["story_below_screen"] is True
        and not pointer["layout"][viewport]["errors"]
        and all(
            item["visible"] is False
            for item in pointer["layout"][viewport]["debug"]
        )
        for viewport in ("desktop", "mobile")
    )

    combined_frames = paths["frames"].read_bytes()
    visual_frames = visual["frames"]
    frame_bytes_by_id: dict[str, bytes] = {}
    frame_errors: list[str] = []
    for index, item in enumerate(visual_frames):
        raw_path = export_root / item["raw_file"]
        raw = raw_path.read_bytes()
        frame_bytes_by_id[item["id"]] = raw
        combined_slice = combined_frames[
            index * EXPECTED_FRAME_BYTES : (index + 1) * EXPECTED_FRAME_BYTES
        ]
        if item["byte_offset"] != index * EXPECTED_FRAME_BYTES:
            frame_errors.append(f"{item['id']}: byte offset")
        if item["byte_length"] != EXPECTED_FRAME_BYTES:
            frame_errors.append(f"{item['id']}: byte length")
        if len(raw) != EXPECTED_FRAME_BYTES:
            frame_errors.append(f"{item['id']}: raw length")
        if sha256(raw) != item["raw_sha256"]:
            frame_errors.append(f"{item['id']}: raw SHA")
        if raw != combined_slice:
            frame_errors.append(f"{item['id']}: combined slice")
        bounds = item["black_bounds_inclusive"]
        if bounds is not None and not (
            0 <= bounds[0] <= bounds[2] < 200
            and 0 <= bounds[1] <= bounds[3] < 200
        ):
            frame_errors.append(f"{item['id']}: black bounds")
        if item["primary_surface_count"] != 1:
            frame_errors.append(f"{item['id']}: primary surface")
        if item["expression_face_count"] + item["exclusive_menu_surface_count"] != 1:
            frame_errors.append(f"{item['id']}: exclusive surface")
        if item["gaze_highlight_count"] > 1:
            frame_errors.append(f"{item['id']}: gaze/highlight")
        if (
            item["stale_layer_count"] != 0
            or item["clipping_policy_violation_count"] != 0
            or item["conflicting_surface_overlap_count"] != 0
        ):
            frame_errors.append(f"{item['id']}: stale/clipping/overlap")
        allowed = set(item["policy_derived"]["edge_contact_policy"]["allowed_sides"])
        touched = set()
        if bounds is not None:
            if bounds[0] == 0:
                touched.add("left")
            if bounds[2] == 199:
                touched.add("right")
            if bounds[1] == 0:
                touched.add("top")
            if bounds[3] == 199:
                touched.add("bottom")
        if touched - allowed:
            frame_errors.append(f"{item['id']}: illegal edge contact")
    visual_ids = [item["id"] for item in visual_frames]
    return_pixels_equal = (
        frame_bytes_by_id["centered_rest"]
        == frame_bytes_by_id["menu_return_rest"]
        == frame_bytes_by_id["recording_return_rest"]
    )

    header = paths["c_pack_header"].read_text(encoding="ascii")
    source = paths["c_pack_source"].read_text(encoding="ascii")
    macro_values = {
        name: int(value)
        for name, value in re.findall(
            r"^#define\s+(COMPANION_VISUAL_(?:WIDTH|HEIGHT|STRIDE_BYTES|"
            r"FRAME_BYTES|STATE_COUNT|UNIQUE_FRAME_COUNT|PAYLOAD_BYTES|"
            r"TRANSITION_COUNT))\s+(\d+)u$",
            header,
            re.MULTILINE,
        )
    }
    payload_block = parse_c_block(
        source,
        "const uint8_t companion_visual_unique_frame_payload"
        "[COMPANION_VISUAL_PAYLOAD_BYTES]",
    )
    c_payload = bytes(
        int(value, 16)
        for value in re.findall(r"\b0x([0-9A-F]{2})\b", payload_block)
    )
    offsets = parse_unsigned_values(
        parse_c_block(
            source,
            "const uint32_t companion_visual_unique_frame_offsets"
            "[COMPANION_VISUAL_UNIQUE_FRAME_COUNT]",
        )
    )
    state_to_unique = parse_unsigned_values(
        parse_c_block(
            source,
            "const uint8_t companion_visual_state_to_unique_frame"
            "[COMPANION_VISUAL_STATE_COUNT]",
        )
    )
    state_enum_match = re.search(
        r"typedef enum \{\s*(.*?)\s*\} companion_visual_state_t;",
        header,
        re.DOTALL,
    )
    parsed_state_enums = (
        [
            (name, int(index))
            for name, index in re.findall(
                r"\b(COMPANION_VISUAL_STATE_[A-Z0-9_]+)\s*=\s*(\d+),",
                state_enum_match.group(1),
            )
        ]
        if state_enum_match
        else []
    )
    pack_states = pack_manifest["states"]
    reconstructed_count = 0
    alias_valid = True
    for state, visual_frame, unique_index in zip(
        pack_states, visual_frames, state_to_unique
    ):
        start = offsets[unique_index] if unique_index < len(offsets) else len(c_payload)
        reconstructed = c_payload[start : start + EXPECTED_FRAME_BYTES]
        if reconstructed == frame_bytes_by_id[visual_frame["id"]]:
            if sha256(reconstructed) == state["frame_sha256"]:
                reconstructed_count += 1
    for left_index, left in enumerate(pack_states):
        for right in pack_states[left_index + 1 :]:
            if (
                left["frame_sha256"] == right["frame_sha256"]
            ) != (
                left["unique_frame_index"] == right["unique_frame_index"]
            ):
                alias_valid = False
    transition_ids = [str(value) for value in transitions["states"]]
    transition_targets_exist = all(
        state in transition_ids
        for item in transitions["transitions"]
        for state in (
            transition_states(item, "from") + transition_states(item, "to")
        )
    )
    c_pack_direct_errors = []
    if macro_values != {
        "COMPANION_VISUAL_WIDTH": 200,
        "COMPANION_VISUAL_HEIGHT": 200,
        "COMPANION_VISUAL_STRIDE_BYTES": 25,
        "COMPANION_VISUAL_FRAME_BYTES": 5000,
        "COMPANION_VISUAL_STATE_COUNT": 17,
        "COMPANION_VISUAL_UNIQUE_FRAME_COUNT": 13,
        "COMPANION_VISUAL_PAYLOAD_BYTES": 65000,
        "COMPANION_VISUAL_TRANSITION_COUNT": 21,
    }:
        c_pack_direct_errors.append("C capacity macros")
    if "#define COMPANION_VISUAL_ASSET_PACK_ENABLE 0" not in header:
        c_pack_direct_errors.append("default-off macro")
    if parsed_state_enums != [
        (item["c_enum"], item["index"]) for item in pack_states
    ]:
        c_pack_direct_errors.append("state enum identity")
    if len(c_payload) != EXPECTED_PAYLOAD_BYTES:
        c_pack_direct_errors.append("C payload length")
    if sha256(c_payload) != pack_manifest["capacity"]["payload_sha256"]:
        c_pack_direct_errors.append("C payload SHA")
    if offsets != [index * EXPECTED_FRAME_BYTES for index in range(13)]:
        c_pack_direct_errors.append("C offsets")
    if state_to_unique != [
        item["unique_frame_index"] for item in pack_states
    ]:
        c_pack_direct_errors.append("state mapping")
    if reconstructed_count != EXPECTED_STATE_COUNT:
        c_pack_direct_errors.append("frame reconstruction")
    if not alias_valid:
        c_pack_direct_errors.append("alias semantics")
    if re.search(r"\b(?:malloc|calloc|realloc|free)\s*\(", header + "\n" + source):
        c_pack_direct_errors.append("dynamic allocation")
    if not transition_targets_exist:
        c_pack_direct_errors.append("transition target")

    oracle_errors: list[str] = []
    expected_pairs: list[tuple[int, int, str, str, dict[str, Any]]] = []
    for transition_index, item in enumerate(transitions["transitions"]):
        pair_index = 0
        for from_state in transition_states(item, "from"):
            for to_state in transition_states(item, "to"):
                expected_pairs.append(
                    (transition_index, pair_index, from_state, to_state, item)
                )
                pair_index += 1
    oracle_pairs = oracle["pairs"]
    if len(expected_pairs) != len(oracle_pairs):
        oracle_errors.append("expanded pair cardinality")
    noop_count = 0
    full_frame_count = 0
    menu_full_frame_count = 0
    nonmenu_full_frame_count = 0
    for expected, pair in zip(expected_pairs, oracle_pairs):
        transition_index, pair_index, from_state, to_state, transition = expected
        previous = frame_bytes_by_id[from_state]
        current = frame_bytes_by_id[to_state]
        computed = compute_changed(previous, current)
        pixel_noop = computed["bounds"] is None
        if pixel_noop:
            noop_count += 1
        full_frame = (
            computed["window"] is not None
            and computed["window"]["full_frame"] is True
        )
        if full_frame:
            full_frame_count += 1
            if pair["menu_related"]:
                menu_full_frame_count += 1
            else:
                nonmenu_full_frame_count += 1
        expected_from_mask = sum(
            1 << transition_ids.index(value)
            for value in transition_states(transition, "from")
        )
        expected_to_mask = sum(
            1 << transition_ids.index(value)
            for value in transition_states(transition, "to")
        )
        comparisons = (
            pair["transition_index"] == transition_index,
            pair["transition_pair_index"] == pair_index,
            pair["from_state"] == from_state,
            pair["to_state"] == to_state,
            pair["from_mask"] == expected_from_mask,
            pair["to_mask"] == expected_to_mask,
            pair["event"] == transition["event"],
            pair["guard"] == transition.get("guard", "always"),
            pair["effect"] == transition["effect"],
            pair["previous_frame_bytes"] == EXPECTED_FRAME_BYTES,
            pair["current_frame_bytes"] == EXPECTED_FRAME_BYTES,
            pair["previous_frame_sha256"] == sha256(previous),
            pair["current_frame_sha256"] == sha256(current),
            pair["changed_pixel_count"] == computed["changed_pixel_count"],
            pair["changed_byte_count"] == computed["changed_byte_count"],
            pair["changed_pixel_bounds"] == computed["bounds"],
            pair["transfer_window"] == computed["window"],
            pair["pixel_noop"] is pixel_noop,
            pair["current_slice"]["payload_bytes"] == len(computed["payload"]),
            pair["current_slice"]["sha256"] == sha256(computed["payload"]),
            pair["current_slice"]["hex"] == computed["payload"].hex().upper(),
            pair["outside_unchanged_oracle"]["outside_window_changed_byte_count"]
            == 0,
            pair["outside_unchanged_oracle"]["outside_window_changed_pixel_count"]
            == 0,
            pair["outside_unchanged_oracle"]["outside_window_unchanged"] is True,
            pair["outside_unchanged_oracle"]["reconstructed_current_byte_equal"]
            is True,
            pair["outside_unchanged_oracle"]["reconstructed_current_sha256"]
            == sha256(current),
            pair["full_frame_policy"]["payload_is_5000_bytes"] is full_frame,
            pair["full_frame_policy"]["legal"] is True,
            not full_frame or pair["menu_related"] is True,
        )
        if not all(comparisons):
            oracle_errors.append(f"{pair.get('id', 'unknown')}: direct oracle mismatch")
    oracle_ids_unique = len({item["id"] for item in oracle_pairs}) == len(oracle_pairs)

    browser_guards = boundary["browser_only_not_for_physical_firmware"]
    physical_guards = boundary["physical_comp_req_472_mapping"]
    guards_separated = (
        browser_guards["double_tap_gap_ms"] == 350
        and browser_guards["double_tap_move_px"] == 32
        and browser_guards["hold_menu_ms"] == 700
        and browser_guards["drag_move_px"] == 44
        and browser_guards["must_not_be_copied_to_physical_adapter"] is True
        and physical_guards["double_tap_gap_ms"] == 650
        and physical_guards["double_tap_move_px_max"] == 40
        and physical_guards["hold_feedback_ms"] == 650
        and physical_guards["menu_entry_ms"] == 3000
        and (
            browser_guards["double_tap_gap_ms"],
            browser_guards["double_tap_move_px"],
            browser_guards["hold_menu_ms"],
        )
        != (
            physical_guards["double_tap_gap_ms"],
            physical_guards["double_tap_move_px_max"],
            physical_guards["menu_entry_ms"],
        )
    )
    boundary_pixels_match = (
        boundary["shared_contract"]["state_count"] == EXPECTED_STATE_COUNT
        and boundary["shared_contract"]["state_ids"] == visual_ids
        and boundary["shared_contract"]["pixels"]["frames_bin_sha256"]
        == files["frames"]["sha256"]
        and boundary["shared_contract"]["pixels"]["visual_contract_sha256"]
        == files["visual_contract"]["sha256"]
        and boundary["shared_contract"]["pixels"]["expanded_window_oracle_sha256"]
        == files["expanded_oracle"]["sha256"]
    )

    runner_text = paths["owner_runner"].read_text(encoding="utf-8")
    supervisor_text = paths["owner_supervisor"].read_text(encoding="utf-8")
    check_marker = runner_text.find('if ($CheckOnly) {')
    check_return = runner_text.find("    return", check_marker)
    side_effect_offsets = [
        runner_text.find(token, check_return)
        for token in ("Invoke-WebRequest", "Start-Process", "operator-prompt")
    ]
    checkonly_early_return = (
        check_marker >= 0
        and check_return > check_marker
        and all(offset > check_return for offset in side_effect_offsets)
    )
    cleanup_tokens = (
        'if ($serverStarted -and $null -ne $serverProcess)',
        'if ($serverProcess.Id -ne $serverPid)',
        "Stop-Process -Id $serverPid -Force",
        "$serverProcess.WaitForExit(5000)",
        "Write-PromptFaultArtifact",
        "owner-review-fault-",
        "finally",
    )
    runner_cleanup_exact = all(token in runner_text for token in cleanup_tokens)
    supervisor_default_off = all(
        token in supervisor_text
        for token in (
            "choose exactly one of -CheckOnly or -Execute",
            "Refusing Execute until the owner explicitly starts browser acceptance",
            "CheckOnly side-effect counter is not zero",
            "owner-review.supervisor.lock",
        )
    )
    readiness = checkonly["readiness"]
    nested_counters = readiness["counters"]
    top_counters = checkonly["counters"]
    checkonly_counters_zero = all(
        nested_counters[key] == 0
        for key in (
            "process",
            "browser",
            "popup",
            "hardware",
            "write",
            "server_probe",
            "network_request",
            "owner_result",
        )
    ) and all(
        top_counters[key] == 0
        for key in ("process", "browser", "popup", "hardware", "write")
    )
    prompt_contract = readiness["prompt_contract"]
    prompt_contract_exact = (
        prompt_contract["instance_count"] == 1
        and prompt_contract["buttons"] == ["\u901a\u8fc7", "\u5931\u8d25"]
        and prompt_contract["note_allowed"] is True
    )
    identity_matches = (
        len(readiness["identities"]) == 14
        and all(
            item["exists"] is True
            and item["match"] is True
            and item["observed_sha256"] == item["expected_sha256"]
            for item in readiness["identities"]
        )
    )
    owner_artifact_names = (
        "owner-review.json",
        "owner-review.raw.json",
        "owner-review.note.txt",
        ".owner-review.prompt-active.lock",
        "owner-review.supervisor.lock",
    )
    owner_artifacts = [
        (repo_root / VALIDATION_DIR / name)
        for name in owner_artifact_names
        if (repo_root / VALIDATION_DIR / name).exists()
    ]
    owner_artifacts.extend(
        sorted((repo_root / VALIDATION_DIR).glob("owner-review-fault-*.json"))
    )

    protected_bytes = paths["protected_owner_acceptance"].read_bytes()
    protected_text = protected_bytes.decode("utf-8")
    try:
        json.loads(protected_text)
        protected_json_parseable = True
    except json.JSONDecodeError:
        protected_json_parseable = False
    protected_note_valid = (
        len(protected_bytes) == 55
        and len(protected_text.splitlines()) == 1
        and "\u622a\u65ad" in protected_text
        and not protected_json_parseable
    )

    fixture_document = load_json(fixtures_path)
    fixture_canonical = (
        fixture_document.get("schema")
        == "companion.upper-machine-ready-negative-fixtures.v1"
        and fixture_document.get("bound_files_mutated") is False
        and fixture_document.get("mutations") == EXPECTED_MUTATIONS
    )

    rehash_mismatches = sum(not item["match"] for item in rehash_records)
    facts: dict[str, Any] = {
        "files": files,
        "rehash": {
            "file_count": len(rehash_records),
            "mismatch_count": rehash_mismatches,
        },
        "machine": {
            "status": machine["status"],
            "all_checks_true": all_true(machine["checks"]),
            "failed_count": len(machine["failed"]),
            "page_sha256": machine["source"]["page_sha256"],
            "fresh_passed": machine["fresh_browser_interaction"]["passed"],
            "fresh_total": machine["fresh_browser_interaction"]["total"],
            "pointer_matrix_all_true": pointer_matrix_all_true,
            "route_counts_exact": route_counts_exact,
            "frames": machine["counts"]["frames"],
            "states": machine["counts"]["states"],
            "transitions": machine["counts"]["transitions"],
            "http_404": machine["counts"]["http_404"],
            "stale": machine["counts"]["stale"],
            "clipping_policy_violation": machine["counts"][
                "clipping_policy_violation"
            ],
            "overlap": machine["counts"]["overlap"],
            "artifacts_match": machine_artifacts_match,
            "boundary_counters_zero": all(
                value == 0 for value in machine["boundaries"].values()
            ),
            "measured_status": measured["status"],
            "measured_parse_errors": collect_error_lists(measured),
        },
        "capture": {
            "status": capture["status"],
            "page_sha256": capture["source"]["page_sha256"],
            "url": capture["source"]["url"],
            "dimensions": capture["capture"]["dimensions"],
            "state_count": capture["capture"]["state_count"],
            "viewport_count": capture["capture"]["viewport_count"],
            "rendered_frame_count": capture["capture"]["rendered_frame_count"],
            "state_records": len(capture_states),
            "checks_passed": capture["checks"]["passed"],
            "checks_total": capture["checks"]["total"],
            "check_items_all_true": all(
                item["pass"] is True for item in capture["checks"]["items"]
            ),
            "route_activation_exact": (
                capture["checks"]["route_activation"]["menu_per_viewport"] == 1
                and capture["checks"]["route_activation"][
                    "recording_per_viewport"
                ]
                == 1
            ),
            "http_404": capture["checks"]["http_404_count"],
            "stale_count": capture["checks"]["stale_layer_count"],
            "overlap_count": capture["checks"][
                "conflicting_surface_overlap_count"
            ],
            "semantic_errors": len(capture_state_errors),
            "returns_equal_rest": capture_returns_equal,
            "real_hold_exact": hold_exact,
            "errors": len(capture["errors"]),
            "gesture_constants": capture["source"]["gesture_constants"],
        },
        "pointer": {
            "status": pointer["status"],
            "page_sha256": pointer["page_sha256"],
            "url": pointer["url"],
            "layout_exact": pointer_layout_exact,
            "scenario_keys_exact": pointer_scenario_keys_exact,
            "scenario_error_count": collect_error_lists(pointer["scenarios"]),
            "negative_all_true": all_true(pointer["negatives"]),
            "top_error_count": len(pointer["errors"]),
        },
        "frames": {
            "status": visual["status"],
            "page_sha256": visual["source"]["page_sha256"],
            "frame_count": visual["frame_count"],
            "frame_records": len(visual_frames),
            "frame_bytes": visual["format"]["frame_bytes"],
            "combined_bytes": len(combined_frames),
            "combined_sha256": sha256(combined_frames),
            "ids_unique": len(set(visual_ids)) == EXPECTED_STATE_COUNT,
            "direct_error_count": len(frame_errors),
            "return_pixels_equal": return_pixels_equal,
            "measured_stale": visual["invariants"]["measured"][
                "stale_layer_count"
            ],
            "measured_overlap": visual["invariants"]["measured"][
                "conflicting_surface_overlap_count"
            ],
            "policy_clipping_violation": visual["invariants"]["policy_derived"][
                "clipping_violation_count"
            ],
        },
        "c_pack": {
            "manifest_status": pack_manifest["status"],
            "result_status": pack_result["status"],
            "result_all_checks_true": all_true(pack_result["checks"]),
            "result_error_count": len(pack_result["errors"]),
            "default_off": (
                pack_manifest["default_off"]["default"] == 0
                and pack_manifest["default_off"]["app_or_build_wiring_changed"]
                is False
            ),
            "state_count": pack_manifest["capacity"]["state_count"],
            "unique_frame_count": pack_manifest["capacity"][
                "unique_frame_count"
            ],
            "payload_bytes": len(c_payload),
            "manifest_payload_bytes": pack_manifest["capacity"][
                "packed_payload_bytes"
            ],
            "payload_budget_bytes": pack_manifest["capacity"][
                "payload_budget_bytes"
            ],
            "dynamic_allocation": pack_manifest["capacity"][
                "dynamic_allocation"
            ],
            "transition_count": len(pack_manifest["transitions"]),
            "state_ids_match": (
                [item["id"] for item in pack_states]
                == visual_ids
                == transition_ids
            ),
            "reconstructed_count": reconstructed_count,
            "alias_valid": alias_valid,
            "direct_error_count": len(c_pack_direct_errors),
            "compile_return_codes": [
                item["return_code"] for item in pack_result["compile"]["results"]
            ],
            "deterministic_zero_diff": (
                pack_result["deterministic_rerun"]["result"] == "0 diff"
                and all(
                    item["byte_equal"] is True
                    for item in pack_result["deterministic_rerun"]["files"]
                )
            ),
            "handoff_default_off": (
                pack_handoff["status"] == "PASS"
                and pack_handoff["integration_authorized"] is False
                and pack_handoff["default_off_macro"]
                == "COMPANION_VISUAL_ASSET_PACK_ENABLE"
            ),
        },
        "oracle": {
            "status": oracle["status"],
            "machine_status": oracle_result["status"],
            "machine_all_checks_true": all_true(oracle_result["checks"]),
            "machine_validation_errors": len(
                oracle_result["validation_errors"]
            ),
            "state_count": oracle["state_count"],
            "transition_mask_count": oracle["transition_mask_count"],
            "pair_count": len(oracle_pairs),
            "declared_pair_count": oracle["expanded_pair_count"],
            "ids_unique": oracle_ids_unique,
            "pixel_noop_pair_count": noop_count,
            "full_frame_pair_count": full_frame_count,
            "menu_full_frame_pair_count": menu_full_frame_count,
            "nonmenu_full_frame_pair_count": nonmenu_full_frame_count,
            "direct_error_count": len(oracle_errors),
            "machine_mutations": oracle_result["mutation_negatives"]["result"],
            "deterministic_zero_diff": (
                oracle_result["deterministic_rerun"]["result"] == "0 diff"
                and all(
                    item["byte_equal"] is True
                    for item in oracle_result["deterministic_rerun"]["files"]
                )
            ),
            "side_effect_counters_zero": all(
                value == 0
                for value in oracle_result["side_effect_counters"].values()
            ),
        },
        "physical_boundary": {
            "status": boundary["status"],
            "default_off": boundary["default_off"],
            "integration_authorized": boundary["integration_authorized"],
            "shared_pixels_match": boundary_pixels_match,
            "guards_separated": guards_separated,
            "browser_guards": {
                "double_tap_gap_ms": browser_guards["double_tap_gap_ms"],
                "double_tap_move_px": browser_guards["double_tap_move_px"],
                "hold_menu_ms": browser_guards["hold_menu_ms"],
                "drag_move_px": browser_guards["drag_move_px"],
            },
            "physical_guards": {
                "double_tap_gap_ms": physical_guards["double_tap_gap_ms"],
                "double_tap_move_px_max": physical_guards[
                    "double_tap_move_px_max"
                ],
                "hold_feedback_ms": physical_guards["hold_feedback_ms"],
                "menu_entry_ms": physical_guards["menu_entry_ms"],
            },
        },
        "owner_review": {
            "status": checkonly["status"],
            "mode": checkonly["mode"],
            "default_off": checkonly["default_off"],
            "execute_performed": checkonly["execute_performed"],
            "owner_result_written": checkonly["owner_result_written"],
            "identity_count": len(readiness["identities"]),
            "identity_matches": identity_matches,
            "checkonly_counters_zero": checkonly_counters_zero,
            "prompt_contract_exact": prompt_contract_exact,
            "canonical_aiw_invoked": readiness["canonical_aiw"]["invoked"],
            "url": readiness["url"]["value"],
            "url_string_only": readiness["url"]["string_match_only"],
            "network_checked": readiness["url"]["network_checked"],
            "server_checked": readiness["url"]["server_checked"],
            "checkonly_early_return": checkonly_early_return,
            "runner_cleanup_exact_pid_bounded": runner_cleanup_exact,
            "supervisor_default_off": supervisor_default_off,
            "owner_result_count": len(owner_artifacts),
        },
        "protected_owner_acceptance": {
            "declared_extension": ".json",
            "observed_content_type": "raw_owner_note_utf8_text",
            "json_parseable": protected_json_parseable,
            "utf8_bytes": len(protected_bytes),
            "utf8_line_count": len(protected_text.splitlines()),
            "contains_truncation_term": "\u622a\u65ad" in protected_text,
            "parsed_as_registry_raw_owner_note": protected_note_valid,
        },
        "fixtures": {
            "path": fixtures_path.relative_to(repo_root).as_posix(),
            "sha256": file_sha(fixtures_path),
            "count": len(fixture_document.get("mutations", [])),
            "canonical": fixture_canonical,
        },
        "side_effects": {
            "execute": 1 if checkonly["execute_performed"] else 0,
            "process": nested_counters["process"],
            "browser": nested_counters["browser"],
            "prompt": nested_counters["popup"]
            + (1 if readiness["canonical_aiw"]["invoked"] else 0),
            "server": nested_counters["server_probe"]
            + nested_counters["network_request"],
            "hardware": nested_counters["hardware"],
            "production": 0,
            "owner_result": len(owner_artifacts),
            "product_write": 0,
        },
    }
    return facts, rehash_records


def run_checks(facts: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for file_id, (_relative, expected, _parser) in EXPECTED_FILES.items():
        item = facts["files"][file_id]
        checks[f"file_hash.{file_id}"] = (
            item["exists"] is True and item["sha256"] == expected
        )
    checks["rehash.all_bound_files"] = (
        facts["rehash"]["file_count"] >= len(EXPECTED_FILES)
        and facts["rehash"]["mismatch_count"] == 0
    )
    machine = facts["machine"]
    checks["machine.structure"] = (
        machine["status"] == "PASS"
        and machine["all_checks_true"]
        and machine["failed_count"] == 0
        and machine["page_sha256"] == EXPECTED_FILES["page"][1]
        and machine["fresh_passed"] == machine["fresh_total"]
        and machine["fresh_total"] >= 20
        and machine["pointer_matrix_all_true"]
        and machine["route_counts_exact"]
        and machine["frames"] == 17
        and machine["states"] == 17
        and machine["transitions"] == 21
        and machine["http_404"] == 0
        and machine["stale"] == 0
        and machine["clipping_policy_violation"] == 0
        and machine["overlap"] == 0
        and machine["artifacts_match"]
        and machine["boundary_counters_zero"]
        and machine["measured_status"] == "PASS"
        and machine["measured_parse_errors"] == 0
    )
    capture = facts["capture"]
    checks["capture.structure"] = (
        capture["status"] == "PASS"
        and capture["page_sha256"] == EXPECTED_FILES["page"][1]
        and capture["url"] == EXPECTED_URL
        and capture["dimensions"] == [200, 200]
        and capture["state_count"] == 17
        and capture["viewport_count"] == 2
        and capture["rendered_frame_count"] == 34
        and capture["state_records"] == 34
        and capture["checks_passed"] == capture["checks_total"] == 54
        and capture["check_items_all_true"]
        and capture["route_activation_exact"]
        and capture["http_404"] == 0
        and capture["stale_count"] == 0
        and capture["overlap_count"] == 0
        and capture["semantic_errors"] == 0
        and capture["returns_equal_rest"]
        and capture["real_hold_exact"]
        and capture["errors"] == 0
        and capture["gesture_constants"]
        == {
            "menu_hold_ms": 700,
            "double_tap_gap_ms": 350,
            "double_tap_move_px": 32,
            "drag_move_px": 44,
        }
    )
    pointer = facts["pointer"]
    checks["pointer.structure"] = (
        pointer["status"] == "PASS"
        and pointer["page_sha256"] == EXPECTED_FILES["page"][1]
        and pointer["url"] == EXPECTED_URL
        and pointer["layout_exact"]
        and pointer["scenario_keys_exact"]
        and pointer["scenario_error_count"] == 0
        and pointer["negative_all_true"]
        and pointer["top_error_count"] == 0
    )
    frames = facts["frames"]
    checks["frames.structure"] = (
        frames["status"] == "PASS"
        and frames["page_sha256"] == EXPECTED_FILES["page"][1]
        and frames["frame_count"] == EXPECTED_STATE_COUNT
        and frames["frame_records"] == EXPECTED_STATE_COUNT
        and frames["frame_bytes"] == EXPECTED_FRAME_BYTES
        and frames["combined_bytes"]
        == EXPECTED_STATE_COUNT * EXPECTED_FRAME_BYTES
        and frames["combined_sha256"] == EXPECTED_FILES["frames"][1]
        and frames["ids_unique"]
        and frames["direct_error_count"] == 0
        and frames["return_pixels_equal"]
        and frames["measured_stale"] == 0
        and frames["measured_overlap"] == 0
        and frames["policy_clipping_violation"] == 0
    )
    pack = facts["c_pack"]
    checks["c_pack.structure"] = (
        pack["manifest_status"] == "PASS"
        and pack["result_status"] == "PASS"
        and pack["result_all_checks_true"]
        and pack["result_error_count"] == 0
        and pack["default_off"]
        and pack["state_count"] == EXPECTED_STATE_COUNT
        and pack["unique_frame_count"] == EXPECTED_UNIQUE_FRAME_COUNT
        and pack["payload_bytes"] == EXPECTED_PAYLOAD_BYTES
        and pack["manifest_payload_bytes"] == EXPECTED_PAYLOAD_BYTES
        and pack["payload_budget_bytes"] == 85000
        and pack["dynamic_allocation"] is False
        and pack["transition_count"] == 21
        and pack["state_ids_match"]
        and pack["reconstructed_count"] == EXPECTED_STATE_COUNT
        and pack["alias_valid"]
        and pack["direct_error_count"] == 0
        and pack["compile_return_codes"] == [0, 0]
        and pack["deterministic_zero_diff"]
        and pack["handoff_default_off"] is True
    )
    oracle = facts["oracle"]
    checks["oracle.structure"] = (
        oracle["status"] == "PASS"
        and oracle["machine_status"] == "PASS"
        and oracle["machine_all_checks_true"]
        and oracle["machine_validation_errors"] == 0
        and oracle["state_count"] == EXPECTED_STATE_COUNT
        and oracle["transition_mask_count"] == 21
        and oracle["pair_count"] == EXPECTED_PAIR_COUNT
        and oracle["declared_pair_count"] == EXPECTED_PAIR_COUNT
        and oracle["ids_unique"]
        and oracle["pixel_noop_pair_count"] == EXPECTED_NOOP_COUNT
        and oracle["full_frame_pair_count"] == EXPECTED_MENU_FULL_FRAME_COUNT
        and oracle["menu_full_frame_pair_count"]
        == EXPECTED_MENU_FULL_FRAME_COUNT
        and oracle["nonmenu_full_frame_pair_count"] == 0
        and oracle["direct_error_count"] == 0
        and oracle["machine_mutations"] == "5/5"
        and oracle["deterministic_zero_diff"]
        and oracle["side_effect_counters_zero"]
    )
    boundary = facts["physical_boundary"]
    checks["physical_boundary.structure"] = (
        boundary["status"] == "PASS_BOUNDARY_ONLY_NOT_INTEGRATED"
        and boundary["default_off"] is True
        and boundary["integration_authorized"] is False
        and boundary["shared_pixels_match"]
        and boundary["guards_separated"]
        and boundary["browser_guards"]
        == {
            "double_tap_gap_ms": 350,
            "double_tap_move_px": 32,
            "hold_menu_ms": 700,
            "drag_move_px": 44,
        }
        and boundary["physical_guards"]
        == {
            "double_tap_gap_ms": 650,
            "double_tap_move_px_max": 40,
            "hold_feedback_ms": 650,
            "menu_entry_ms": 3000,
        }
    )
    owner = facts["owner_review"]
    checks["owner_review.checkonly"] = (
        owner["status"]
        == "PASS_READY_FOR_OWNER_BROWSER_REVIEW_CHECKONLY_NO_EXECUTE"
        and owner["mode"] == "CheckOnly"
        and owner["default_off"] is True
        and owner["execute_performed"] is False
        and owner["owner_result_written"] is False
        and owner["identity_count"] == 14
        and owner["identity_matches"]
        and owner["checkonly_counters_zero"]
        and owner["prompt_contract_exact"]
        and owner["canonical_aiw_invoked"] is False
        and owner["url"] == EXPECTED_URL
        and owner["url_string_only"] is True
        and owner["network_checked"] is False
        and owner["server_checked"] is False
        and owner["checkonly_early_return"]
        and owner["runner_cleanup_exact_pid_bounded"]
        and owner["supervisor_default_off"]
    )
    checks["owner_review.result_absent"] = owner["owner_result_count"] == 0
    protected = facts["protected_owner_acceptance"]
    checks["protected_owner_acceptance.structure"] = (
        protected["declared_extension"] == ".json"
        and protected["observed_content_type"] == "raw_owner_note_utf8_text"
        and protected["json_parseable"] is False
        and protected["utf8_bytes"] == 55
        and protected["utf8_line_count"] == 1
        and protected["contains_truncation_term"] is True
        and protected["parsed_as_registry_raw_owner_note"] is True
    )
    checks["fixtures.canonical"] = (
        facts["fixtures"]["canonical"]
        and facts["fixtures"]["count"] == len(EXPECTED_MUTATIONS)
    )
    checks["side_effects.zero"] = all(
        value == 0 for value in facts["side_effects"].values()
    )
    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--negative-output", type=Path)
    return parser.parse_args()


def rooted(repo_root: Path, value: Path | None, default: Path) -> Path:
    path = value if value is not None else default
    return path.resolve() if path.is_absolute() else (repo_root / path).resolve()


def main() -> int:
    args = parse_args()
    inferred_root = Path(__file__).resolve().parents[2]
    repo_root = (args.repo_root or inferred_root).resolve()
    output_path = rooted(
        repo_root,
        args.output,
        VALIDATION_DIR / "UPPER_MACHINE_READY.json",
    )
    fixtures_path = rooted(
        repo_root,
        args.fixtures,
        VALIDATION_DIR / "upper-machine-ready-negative-fixtures.json",
    )
    negative_output_path = rooted(
        repo_root,
        args.negative_output,
        VALIDATION_DIR / "upper-machine-ready-negative-result.json",
    )

    facts, rehash_records = build_facts(repo_root, fixtures_path)
    checks = run_checks(facts)
    failed = [name for name, passed in checks.items() if not passed]

    negative_results = []
    for fixture in EXPECTED_MUTATIONS:
        mutated = copy.deepcopy(facts)
        set_dotted(mutated, fixture["target"], fixture["value"])
        mutated_checks = run_checks(mutated)
        expected_check = fixture["expected_check"]
        observed_failed = [
            name for name, passed in mutated_checks.items() if not passed
        ]
        fail_closed = (
            expected_check in mutated_checks
            and mutated_checks[expected_check] is False
            and bool(observed_failed)
        )
        negative_results.append(
            {
                "id": fixture["id"],
                "binding_class": fixture["binding_class"],
                "target": fixture["target"],
                "expected_check": expected_check,
                "observed_failed_checks": observed_failed,
                "fail_closed": fail_closed,
                "bound_files_mutated": False,
            }
        )
    negative_passed = sum(item["fail_closed"] for item in negative_results)
    all_negative_pass = negative_passed == len(EXPECTED_MUTATIONS)
    verifier_relative = Path(__file__).resolve().relative_to(repo_root).as_posix()
    verifier_sha = file_sha(Path(__file__).resolve())

    status = (
        "UPPER_MACHINE_READY"
        if not failed and all_negative_pass
        else "NO_GO_UPPER_MACHINE_NOT_READY"
    )
    upper_artifact = {
        "schema": "companion.upper-machine-ready.v1",
        "requirement": "COMP-REQ-467/471/472",
        "status": status,
        "scope": "offline_upper_art_browser_export_only",
        "default_off": True,
        "integration_authorized": False,
        "verifier": {
            "path": verifier_relative,
            "sha256": verifier_sha,
            "mode": "offline_fail_closed",
        },
        "bound_file_rehash": {
            "count": len(rehash_records),
            "mismatch_count": facts["rehash"]["mismatch_count"],
            "records": rehash_records,
        },
        "computed": {
            "machine": facts["machine"],
            "capture": facts["capture"],
            "pointer": facts["pointer"],
            "frames": facts["frames"],
            "c_asset_pack": facts["c_pack"],
            "expanded_window_oracle": facts["oracle"],
            "physical_consumer_boundary": facts["physical_boundary"],
            "owner_review_checkonly": facts["owner_review"],
            "protected_owner_acceptance": facts[
                "protected_owner_acceptance"
            ],
        },
        "checks": checks,
        "failed": failed,
        "external_mutation_fixtures": {
            "path": facts["fixtures"]["path"],
            "sha256": facts["fixtures"]["sha256"],
            "result": f"{negative_passed}/{len(EXPECTED_MUTATIONS)}",
            "all_fail_closed": all_negative_pass,
            "bound_files_mutated": False,
            "items": negative_results,
        },
        "side_effect_counters": {
            **facts["side_effects"],
            "evidence_artifact_write": 2,
            "evidence_artifact_write_excluded_from_product_write": True,
        },
        "owner_boundary": {
            "owner_result_exists": False,
            "execute_authorized": False,
            "operator_prompt_invoked": False,
            "server_or_browser_started": False,
        },
        "remaining_gates": [
            "COMP-REQ-471 browser owner review has not been executed; owner-review.json must remain absent until an explicit owner start.",
            "COMP-REQ-472 physical consumer integration and physical timing validation remain outside this upper-only artifact.",
            "No production, lower-driver, Platform, firmware build wiring, hardware, popup, Execute, or push authorization is granted.",
        ],
    }
    upper_bytes = canonical_bytes(upper_artifact)
    upper_sha = sha256(upper_bytes)
    negative_artifact = {
        "schema": "companion.upper-machine-ready-negative-result.v1",
        "requirement": "COMP-REQ-467/471/472",
        "status": "PASS" if all_negative_pass else "NO_GO",
        "verifier_path": verifier_relative,
        "verifier_sha256": verifier_sha,
        "fixture_manifest_path": facts["fixtures"]["path"],
        "fixture_manifest_sha256": facts["fixtures"]["sha256"],
        "upper_machine_ready_path": output_path.relative_to(repo_root).as_posix(),
        "upper_machine_ready_sha256": upper_sha,
        "result": f"{negative_passed}/{len(EXPECTED_MUTATIONS)}",
        "bound_files_mutated": False,
        "items": negative_results,
        "side_effect_counters": {
            "execute": 0,
            "process": 0,
            "browser": 0,
            "prompt": 0,
            "server": 0,
            "hardware": 0,
            "production": 0,
            "owner_result": 0,
            "product_write": 0,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(upper_bytes)
    negative_output_path.write_bytes(canonical_bytes(negative_artifact))
    print(
        json.dumps(
            {
                "status": status,
                "checks": f"{len(checks) - len(failed)}/{len(checks)}",
                "negative_fixtures": (
                    f"{negative_passed}/{len(EXPECTED_MUTATIONS)}"
                ),
                "upper_machine_ready_sha256": upper_sha,
                "verifier_sha256": verifier_sha,
            },
            sort_keys=True,
        )
    )
    return 0 if status == "UPPER_MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
