#!/usr/bin/env python3
"""Deterministic negative validation for the COMP-REQ-479 joint gate."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


VALIDATION_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471"
)
UPPER_MR_REL = VALIDATION_REL / "UPPER_MACHINE_READY.json"
ORACLE_REL = Path(
    "docs/art/exports/companion-browser-visual-contract-comp-req-471/"
    "expanded-window-oracle.json"
)
UPPER_MR_SHA = (
    "EAD7000FEB32CD7915FEAD82A49D23FD66755412AEDFA53B4B7A264CABA3BB69"
)
ORACLE_SHA = (
    "20C270A332F7AD75FAED3C44C9AE3C1D789F7902ABA525C07B0B40F4266C5B2E"
)
LEGACY_C173 = "c1733e4e40bb3374b4ee2ec81a7057eb90a03c10"
LEGACY_C692 = "c692339edb3182f30e651161afdc48885cea2ef4"
COMP_REQ_488_4DD = "4ddf9709034d307b333510c27e3e0a45c7ed6d15"
LEGACY_B9 = "b9a2c5aea409cdcd3a88afdc19373ef6f3dd4160"
LEGACY_F142 = "f14254b1e535f94a4fe0bb1223e26cfe66638ca8"
LEGACY_A963 = "a96368d5859c54d3eaee4c9846386c6091dc73a0"
STALE_43B = "43b55379455408994257eaf55e1d3acee95efb58"
D660_MR_REL = Path(
    ".cache/validation/comp-req-484-deterministic-lower/MACHINE_READY.json"
)
D660_MR_SHA = (
    "D660B2FA5AC2F918143EC4FE52D24C32A3B0DE796FB4ED4E48B213A14A0896A9"
)
D660_RUNNER_SHA = (
    "959727E4556FD314083174E6D8B1D8E8E4F335A12EBF254CA3D05EABB8A5711E"
)
D660_SUPERVISOR_SHA = (
    "AB75942496AFDBDE20D810066A752C7D66CAFC658625BA21603543D9E0893F44"
)
STALE_A963_HEX = [
    "328612A050B62995B93AD741B6DF933813025F8FE2637A6E87366DE630BAA5E6",
    "3DF646B1C0B2A7C4F558D50F2FAEC64CB8CA72FD7A17A61BEB7932BC2E07EC00",
]
STALE_A963_ELF = [
    "62C6D00E2013A0975DFE745D8D94C5FBD81499AE6EEE40D9C51C351F3E49942B",
    "D679C93C491F9E5ED4EB7FAA73EF8E7CD56046387E8539E1C586042B9CDF1E07",
]
ZERO_SHA = "0" * 64
COMP_REQ_478_FIXTURE_TOKENS = (
    "bounded_16_cleanup_closed=pass",
    "live_cleanup_closed=pass",
    "post_cleanup_zero_commands=pass",
    "post_cleanup_event_retained=pass",
    "idle_new_burst=pass",
    "cadence_negative_0=pass",
    "cadence_negative_481=pass",
    "transaction_negative_481=pass",
    "busy_negative_601=pass",
    "command_stage_failures=pass",
    "second_service_activation_unchanged=pass",
    "retry=0",
    "physical_mapping=650/40/650/3000",
    "timing=host_synthetic",
    "physical_timing=unproven",
    "bounded_15_deltas=pass",
    "hold_650_menu_3000=pass",
    "menu_idle_481_selection=pass",
    "recording_idle_481_return=pass",
    "busy_captured_gaze_same_burst=pass",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def full_compatibility_ready(
    events: int,
    pairs: int,
    semantic_noops: int,
    polarity_bridge: bool,
) -> bool:
    return bool(
        events == 21
        and pairs == 59
        and semantic_noops == 10
        and polarity_bridge
    )


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def declared_path_bindings(machine_ready: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    legacy = machine_ready.get("source_bindings")
    if isinstance(legacy, dict):
        for path, value in legacy.items():
            digest = (
                value.get("sha256") if isinstance(value, dict) else value
            )
            if isinstance(path, str) and isinstance(digest, str):
                result[path.replace("\\", "/")] = digest.upper()
    for provenance in (
        machine_ready.get("bindings"),
        machine_ready.get("artifacts"),
    ):
        if isinstance(provenance, dict):
            for value in provenance.values():
                if not isinstance(value, dict):
                    continue
                path = value.get("path")
                digest = value.get("sha256")
                if isinstance(path, str) and isinstance(digest, str):
                    result[path.replace("\\", "/")] = digest.upper()
    return result


def lower_status(root: Path) -> str:
    completed = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
            "--ignore-submodules=all",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip())
    return completed.stdout.replace("\r\n", "\n")


def lower_snapshot(root: Path, machine_ready: Path) -> dict[str, Any]:
    status = lower_status(root)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    diff = subprocess.run(
        [
            "git",
            "diff",
            "--no-ext-diff",
            "--binary",
            "--ignore-submodules=all",
            "--",
            ".",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    artifacts = {
        "hex": discover_artifacts(root, ".hex"),
        "elf": discover_artifacts(root, ".elf"),
    }
    return {
        "head": head,
        "tracked_status_sha256": sha256(status.encode("utf-8")),
        "tracked_diff_sha256": sha256(diff),
        "machine_ready_sha256": file_sha(machine_ready),
        "build_artifacts": artifacts,
    }


def discover_artifacts(lower_root: Path, suffix: str) -> list[dict[str, str]]:
    build_root = lower_root / "cubeide/Companion_Nucleo_WB55RG_Bringup"
    candidates = sorted(
        path
        for path in build_root.rglob(f"*{suffix}")
        if "visual_runtime" in path.as_posix()
    )
    if len(candidates) > 128:
        raise ValueError(f"too many {suffix} candidates")
    rows = [
        {
            "path": path.relative_to(lower_root).as_posix(),
            "sha256": file_sha(path),
        }
        for path in candidates
        if path.is_file() and path.stat().st_size <= 64 * 1024 * 1024
    ]
    if len(rows) != 2:
        raise ValueError(f"expected exactly two current {suffix} artifacts")
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--compatibility-auditor", type=Path, required=True)
    parser.add_argument("--expected-compatibility-auditor-sha256", required=True)
    parser.add_argument("--lower-root", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--lower-machine-ready", type=Path, required=True)
    parser.add_argument("--expected-lower-machine-ready-sha256", required=True)
    parser.add_argument(
        "--expected-lower-hex-sha256", action="append", required=True
    )
    parser.add_argument(
        "--expected-lower-elf-sha256", action="append", required=True
    )
    parser.add_argument("--expected-lower-runner-sha256", required=True)
    parser.add_argument("--catalog-output", type=Path, required=True)
    parser.add_argument("--result-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[2]
    )
    lower_root = args.lower_root.resolve()
    runner = (
        args.runner.resolve()
        if args.runner.is_absolute()
        else (repo_root / args.runner).resolve()
    )
    auditor = (
        args.compatibility_auditor.resolve()
        if args.compatibility_auditor.is_absolute()
        else (repo_root / args.compatibility_auditor).resolve()
    )
    lower_mr = (
        args.lower_machine_ready.resolve()
        if args.lower_machine_ready.is_absolute()
        else (lower_root / args.lower_machine_ready).resolve()
    )
    catalog_output = (
        args.catalog_output.resolve()
        if args.catalog_output.is_absolute()
        else (repo_root / args.catalog_output).resolve()
    )
    result_output = (
        args.result_output.resolve()
        if args.result_output.is_absolute()
        else (repo_root / args.result_output).resolve()
    )
    validation_root = (repo_root / VALIDATION_REL).resolve()
    for path in (catalog_output, result_output):
        path.relative_to(validation_root)
    if file_sha(runner) != args.expected_runner_sha256.upper():
        raise SystemExit("joint runner hash mismatch")
    if file_sha(auditor) != args.expected_compatibility_auditor_sha256.upper():
        raise SystemExit("compatibility auditor hash mismatch")
    observed_lower_mr_sha = file_sha(lower_mr)
    claimed_lower_mr_sha = args.expected_lower_machine_ready_sha256.upper()
    claimed_lower_mr_match = observed_lower_mr_sha == claimed_lower_mr_sha

    expected_hex = sorted(value.upper() for value in args.expected_lower_hex_sha256)
    expected_elf = sorted(value.upper() for value in args.expected_lower_elf_sha256)
    actual_mr = load_json(lower_mr)
    bindings = declared_path_bindings(actual_mr)
    provenance = (
        actual_mr.get("bindings")
        if isinstance(actual_mr.get("bindings"), dict)
        else actual_mr.get("artifacts")
    )
    explicit_supervisor = (
        provenance.get("supervisor")
        if isinstance(provenance, dict)
        and isinstance(provenance.get("supervisor"), dict)
        else None
    )
    explicit_runner = (
        provenance.get("runner")
        if isinstance(provenance, dict)
        and isinstance(provenance.get("runner"), dict)
        else None
    )
    supervisor_candidates = (
        [
            (
                explicit_supervisor.get("path"),
                str(explicit_supervisor.get("sha256", "")).upper(),
            )
        ]
        if explicit_supervisor
        else sorted(
            (path, digest)
            for path, digest in bindings.items()
            if Path(path).name == "verify_comp_req_472_visual_runtime.py"
        )
    )
    runner_candidates = (
        [
            (
                explicit_runner.get("path"),
                str(explicit_runner.get("sha256", "")).upper(),
            )
        ]
        if explicit_runner
        else sorted(
            (path, digest)
            for path, digest in bindings.items()
            if "run_" in Path(path).name.lower()
            and Path(path).suffix.lower() in (".ps1", ".py")
        )
    )
    if len(supervisor_candidates) != 1 or len(runner_candidates) != 1:
        raise SystemExit("actual lower runner/supervisor binding is ambiguous")
    supervisor_path, supervisor_sha = supervisor_candidates[0]
    runner_path, observed_runner_sha = runner_candidates[0]
    if observed_runner_sha != args.expected_lower_runner_sha256.upper():
        raise SystemExit("actual lower runner binding mismatch")

    synthetic = copy.deepcopy(actual_mr)
    synthetic["schema"] = "companion.lower-visual-runtime-machine-ready.v1"
    synthetic["status"] = "LOWER_MACHINE_READY"
    synthetic["source_commit"] = args.expected_commit
    required_source_paths = (
        "app/companion_pendant/epaper/companion_visual_runtime_adapter.c",
        "app/companion_pendant/epaper/companion_visual_runtime_adapter.h",
        "app/companion_pendant/epaper/panel_target_stm32wb.c",
        "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c",
        "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.h",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
        "tools/comp_req_472_visual_runtime_fixture.c",
        "tools/run_comp_req_472_visual_runtime_fixture.ps1",
        "tools/verify_comp_req_472_visual_runtime.py",
    )
    synthetic["source_bindings"] = {
        path: file_sha(lower_root / path)
        for path in required_source_paths
        if (lower_root / path).is_file()
    }
    synthetic_hex_descriptors = discover_artifacts(lower_root, ".hex")
    synthetic_elf_descriptors = discover_artifacts(lower_root, ".elf")
    synthetic_hex = sorted(
        item["sha256"] for item in synthetic_hex_descriptors
    )
    synthetic_elf = sorted(
        item["sha256"] for item in synthetic_elf_descriptors
    )
    synthetic["artifacts"] = {
        "hex": synthetic_hex_descriptors,
        "elf": synthetic_elf_descriptors,
        "runner": {
            "path": runner_path,
            "sha256": args.expected_lower_runner_sha256.upper(),
        },
        "supervisor": {
            "path": supervisor_path,
            "sha256": supervisor_sha,
        },
    }
    synthetic["runner_sha256"] = args.expected_lower_runner_sha256.upper()
    synthetic["supervisor_sha256"] = supervisor_sha
    synthetic["compatibility_claims"] = {
        "events_realizable": 21,
        "pairs_realizable": 59,
        "semantic_noops_realizable": 10,
        "polarity_bridge": True,
        "terminal_retention": True,
        "qualification_valid": True,
        "converted_centered_sha256": (
            "EF4CDB579CC2C43645E0E3585D8C40CA65763112619E5EB9FBC583EAF3E28DBD"
        ),
    }
    synthetic["side_effect_counters"] = {
        "execute": 0,
        "server": 0,
        "browser": 0,
        "prompt": 0,
        "popup": 0,
        "hardware": 0,
        "write": 0,
        "programmer": 0,
        "serial": 0,
        "flash": 0,
        "production": 0,
        "push": 0,
    }
    synthetic["source_bindings"][
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
    ] = file_sha(
        lower_root
        / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
    )
    mode_and_fault = synthetic.setdefault("mode_and_fault_evidence", {})
    for name in (
        "bounded_seeds_only_when_not_continuous",
        "bridge_terminal_fault_latch",
        "continuous_has_no_synthetic_enqueue",
        "host_synthetic_label",
        "no_browser_guard_in_adapter",
        "physical_double_tap_guard",
        "runtime_terminal_fault_latch",
        "single_tap_window_guard",
    ):
        mode_and_fault[name] = True
    arm_evidence = synthetic.setdefault("arm_build_evidence", {})
    arm_evidence.setdefault("bounded", {})
    arm_evidence.setdefault("continuous", {})
    arm_evidence["bounded"]["elf_sha256"] = next(
        item["sha256"]
        for item in synthetic_elf_descriptors
        if "continuous" not in item["path"]
    )
    arm_evidence["bounded"]["hex_sha256"] = next(
        item["sha256"]
        for item in synthetic_hex_descriptors
        if "continuous" not in item["path"]
    )
    arm_evidence["continuous"]["elf_sha256"] = next(
        item["sha256"]
        for item in synthetic_elf_descriptors
        if "continuous" in item["path"]
    )
    arm_evidence["continuous"]["hex_sha256"] = next(
        item["sha256"]
        for item in synthetic_hex_descriptors
        if "continuous" in item["path"]
    )
    arm_evidence["bounded"][
        "visual_runtime_mode_proven"
    ] = True
    arm_evidence["bounded"][
        "visual_runtime_mode_value"
    ] = 0
    arm_evidence["continuous"][
        "visual_runtime_mode_proven"
    ] = True
    arm_evidence["continuous"][
        "visual_runtime_mode_value"
    ] = 1
    synthetic.setdefault(
        "timing",
        {
            "activation_ms": 1,
            "transaction_ms": 2,
            "busy_ms": 2,
            "cadence_ms": 12,
            "within_limits": True,
        },
    )
    synthetic_fixture = synthetic.setdefault("fixture", {})
    synthetic_fixture["status"] = "PASS"
    synthetic_fixture.setdefault("checkonly", {})["retry"] = 0
    synthetic_fixture["stdout"] = (
        str(synthetic_fixture.get("stdout", ""))
        + "\n"
        + " ".join(COMP_REQ_478_FIXTURE_TOKENS)
    )
    protected_physical = synthetic.setdefault("protected_observed", {}).setdefault(
        "physical_sha256", {}
    )
    protected_physical["panel_driver"] = file_sha(
        lower_root
        / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    )
    protected_physical["r7_header"] = file_sha(
        lower_root
        / "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h"
    )
    synthetic["protected_git_blobs"] = {
        "panel_driver": "f856d7ce0b8915e5059620c3faa97aa06b06eb4e",
        "r7_header": "2220da0c1113a5cdad7028aeae578d9fe26e936f",
    }

    fixture_root = validation_root / "joint-negative-fixtures"
    mr_root = fixture_root / "lower-mr"
    output_root = fixture_root / "outputs"
    compatibility_root = fixture_root / "compatibility"
    for path in (mr_root, output_root, compatibility_root):
        path.mkdir(parents=True, exist_ok=True)

    fixture_mrs: dict[str, Path] = {}

    def write_fixture(name: str, value: dict[str, Any]) -> Path:
        path = mr_root / f"{name}.json"
        path.write_bytes(canonical_bytes(value))
        fixture_mrs[name] = path
        return path

    synthetic_path = write_fixture("synthetic-b9-pass-claim", synthetic)
    source_drift = copy.deepcopy(synthetic)
    source_drift["source_bindings"][
        "app/companion_pendant/epaper/companion_visual_runtime_adapter.c"
    ] = ZERO_SHA
    source_drift_path = write_fixture("source-hash-drift", source_drift)
    artifact_drift = copy.deepcopy(synthetic)
    artifact_drift["artifacts"]["hex"][0]["sha256"] = ZERO_SHA
    artifact_drift_path = write_fixture("artifact-hash-drift", artifact_drift)
    schema_drift = copy.deepcopy(synthetic)
    schema_drift["schema"] = "companion.lower-visual-runtime-machine-ready.v0"
    schema_drift_path = write_fixture("schema-drift", schema_drift)
    timing_protected_drift = copy.deepcopy(synthetic)
    timing_protected_drift["timing"]["transaction_ms"] = 481
    timing_protected_drift["timing"]["within_limits"] = False
    timing_protected_drift["protected_observed"]["physical_sha256"][
        "panel_driver"
    ] = ZERO_SHA
    timing_protected_path = write_fixture(
        "timing-protected-drift", timing_protected_drift
    )
    nonzero_side = copy.deepcopy(synthetic)
    nonzero_side["side_effect_counters"]["hardware"] = 1
    nonzero_side_path = write_fixture("nonzero-side-effect", nonzero_side)
    comp478_drift = copy.deepcopy(synthetic)
    comp478_drift["arm_build_evidence"]["bounded"][
        "visual_runtime_mode_value"
    ] = 1
    comp478_drift["fixture"]["stdout"] = comp478_drift["fixture"][
        "stdout"
    ].replace("post_cleanup_event_retained=pass", "")
    comp478_drift_path = write_fixture("comp-req-478-drift", comp478_drift)
    comp484_drift = copy.deepcopy(synthetic)
    comp484_drift["fixture"]["stdout"] = comp484_drift["fixture"][
        "stdout"
    ].replace("bounded_15_deltas=pass", "")
    comp484_drift_path = write_fixture("comp-req-484-drift", comp484_drift)
    missing_dependency = copy.deepcopy(synthetic)
    missing_dependency["source_bindings"].pop(
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c",
        None,
    )
    missing_dependency_path = write_fixture(
        "missing-dependency-binding", missing_dependency
    )
    forged_provenance_timing = copy.deepcopy(actual_mr)
    if isinstance(forged_provenance_timing.get("bounds"), dict):
        forged_provenance_timing["bounds"]["transaction_max_ms"] = 481
    else:
        forged_provenance_timing.setdefault("contract", {})[
            "transaction_max_ms"
        ] = 481
    forged_provenance_timing_path = write_fixture(
        "forged-provenance-timing", forged_provenance_timing
    )
    forged_provenance_protected = copy.deepcopy(actual_mr)
    protected_key = (
        "protected"
        if isinstance(forged_provenance_protected.get("protected"), dict)
        else "protected_hashes"
    )
    forged_provenance_protected.setdefault(protected_key, {})[
        "panel_driver"
    ] = ZERO_SHA
    forged_provenance_protected_path = write_fixture(
        "forged-provenance-protected", forged_provenance_protected
    )

    missing_path = mr_root / "missing-lower-machine-ready.json"
    d660_path = lower_root / D660_MR_REL
    fixtures = [
        {
            "id": "missing_lower_mr",
            "commit": args.expected_commit,
            "mr": missing_path,
            "mr_sha": ZERO_SHA,
            "hex": [ZERO_SHA],
            "elf": [ZERO_SHA],
            "runner": ZERO_SHA,
            "supervisor": ZERO_SHA,
            "expected_failed": ["lower_mr.file_exists_and_bounded"],
        },
        {
            "id": "legacy_c173",
            "commit": LEGACY_C173,
            "mr": missing_path,
            "mr_sha": ZERO_SHA,
            "hex": [ZERO_SHA],
            "elf": [ZERO_SHA],
            "runner": ZERO_SHA,
            "supervisor": ZERO_SHA,
            "expected_failed": ["compatibility.full_21_59_10"],
        },
        {
            "id": "legacy_c692",
            "commit": LEGACY_C692,
            "mr": missing_path,
            "mr_sha": ZERO_SHA,
            "hex": [ZERO_SHA],
            "elf": [ZERO_SHA],
            "runner": ZERO_SHA,
            "supervisor": ZERO_SHA,
            "expected_failed": ["compatibility.full_21_59_10"],
        },
        {
            "id": "legacy_b9",
            "commit": LEGACY_B9,
            "mr": missing_path,
            "mr_sha": ZERO_SHA,
            "hex": [ZERO_SHA],
            "elf": [ZERO_SHA],
            "runner": ZERO_SHA,
            "supervisor": ZERO_SHA,
            "expected_failed": ["compatibility.full_21_59_10"],
        },
        {
            "id": "legacy_f142",
            "commit": LEGACY_F142,
            "mr": missing_path,
            "mr_sha": ZERO_SHA,
            "hex": [ZERO_SHA],
            "elf": [ZERO_SHA],
            "runner": ZERO_SHA,
            "supervisor": ZERO_SHA,
            "expected_failed": ["compatibility.full_21_59_10"],
        },
        {
            "id": "legacy_a963",
            "commit": LEGACY_A963,
            "mr": missing_path,
            "mr_sha": ZERO_SHA,
            "hex": [ZERO_SHA],
            "elf": [ZERO_SHA],
            "runner": ZERO_SHA,
            "supervisor": ZERO_SHA,
            "expected_failed": ["compatibility.full_21_59_10"],
        },
        {
            "id": "comp_req_488_4dd_call_edge_gaps",
            "commit": COMP_REQ_488_4DD,
            "mr": missing_path,
            "mr_sha": ZERO_SHA,
            "hex": [ZERO_SHA],
            "elf": [ZERO_SHA],
            "runner": ZERO_SHA,
            "supervisor": ZERO_SHA,
            "expected_failed": ["compatibility.full_21_59_10"],
            "expected_compatibility": {
                "status": "NO_GO_UPPER_LOWER_EVENT_PATH_GAPS",
                "events_realizable": 17,
                "events_missing": 3,
                "events_ambiguous": 1,
                "pairs_realizable": 51,
                "noops_realizable": 8,
                "polarity_bridge": True,
                "event_gaps": [
                    "early_up_cancel_blur_or_drag",
                    "pointer_drag_center",
                    "pointer_move",
                    "select_ui_assets",
                ],
                "representative_pairs": {
                    "T05-P00-gaze_left--gaze_left": True,
                    "T05-P01-gaze_left--gaze_up": True,
                    "T05-P04-gaze_left--gaze_center": False,
                },
                "pointer_move_directional_realizable": 20,
                "pointer_move_center_missing": 5,
                "missing_pair_ids": [
                    "T04-P00-centered_rest--gaze_center",
                    "T05-P04-gaze_left--gaze_center",
                    "T05-P09-gaze_up--gaze_center",
                    "T05-P14-gaze_right--gaze_center",
                    "T05-P19-gaze_down--gaze_center",
                    "T05-P24-gaze_center--gaze_center",
                    "T10-P00-hold_feedback_50--centered_rest",
                    "T17-P00-menu_device--menu_device_ui_assets",
                ],
            },
        },
        {
            "id": "stale_a963_build_identity_after_active_source_change",
            "commit": STALE_43B,
            "mr": missing_path,
            "mr_sha": ZERO_SHA,
            "hex": STALE_A963_HEX,
            "elf": STALE_A963_ELF,
            "runner": ZERO_SHA,
            "supervisor": ZERO_SHA,
            "expected_failed": [
                "lower.build_identity_changes_with_active_sources",
            ],
        },
        {
            "id": "d660_comp_req_486_pretransport_terminal_latch",
            "commit": STALE_43B,
            "mr": d660_path,
            "mr_sha": D660_MR_SHA,
            "hex": [
                "4048852151FB396C314C7F96BFD45F59CA5C1D24BD103AD0701864459A6AF1F2",
                "944E173BEBF7B7121E54B94FD84F52ECCBFDC2AF3CE7F4FAE22B678E7F2C60C9",
            ],
            "elf": [
                "73DEF0522ACB9A7AB1AF07FBEF5DC5CDA223B7E590CD36973423C9C6F4265A16",
                "F635691C4189AFC655F5D9837318BE76C2EC29A08686E1024246F3576D7A5156",
            ],
            "runner": D660_RUNNER_SHA,
            "supervisor": D660_SUPERVISOR_SHA,
            "expected_failed": [
                "compatibility.polarity_terminal_qualification",
            ],
        },
        {
            "id": "lower_mr_hash_drift",
            "commit": args.expected_commit,
            "mr": lower_mr,
            "mr_sha": ZERO_SHA,
            "hex": expected_hex,
            "elf": expected_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": ZERO_SHA,
            "expected_failed": ["lower_mr.hash_exact"],
        },
        {
            "id": "forged_pass_counts",
            "commit": args.expected_commit,
            "mr": synthetic_path,
            "mr_sha": file_sha(synthetic_path),
            "hex": synthetic_hex,
            "elf": synthetic_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": [
                "compatibility.full_21_59_10",
                "lower_claims_match_observed_compatibility",
            ],
        },
        {
            "id": "source_hash_drift",
            "commit": args.expected_commit,
            "mr": source_drift_path,
            "mr_sha": file_sha(source_drift_path),
            "hex": synthetic_hex,
            "elf": synthetic_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": ["lower_mr.all_sources_recomputed"],
        },
        {
            "id": "artifact_hash_drift",
            "commit": args.expected_commit,
            "mr": artifact_drift_path,
            "mr_sha": file_sha(artifact_drift_path),
            "hex": synthetic_hex,
            "elf": synthetic_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": ["lower_mr.hex_hashes_explicit_match"],
        },
        {
            "id": "schema_drift",
            "commit": args.expected_commit,
            "mr": schema_drift_path,
            "mr_sha": file_sha(schema_drift_path),
            "hex": synthetic_hex,
            "elf": synthetic_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": ["lower_mr.schema_exact"],
        },
        {
            "id": "timing_protected_drift",
            "commit": args.expected_commit,
            "mr": timing_protected_path,
            "mr_sha": file_sha(timing_protected_path),
            "hex": synthetic_hex,
            "elf": synthetic_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": [
                "lower_mr.timing_within_limits",
                "lower_mr.protected_hashes_exact",
            ],
        },
        {
            "id": "nonzero_side_effect",
            "commit": args.expected_commit,
            "mr": nonzero_side_path,
            "mr_sha": file_sha(nonzero_side_path),
            "hex": synthetic_hex,
            "elf": synthetic_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": ["lower_mr.side_effects_zero"],
        },
        {
            "id": "comp_req_478_drift",
            "commit": args.expected_commit,
            "mr": comp478_drift_path,
            "mr_sha": file_sha(comp478_drift_path),
            "hex": synthetic_hex,
            "elf": synthetic_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": [
                "lower_mr.arm_modes_exact_0_1",
                "lower_mr.comp_req_478_fixture_contract",
            ],
        },
        {
            "id": "comp_req_484_drift",
            "commit": args.expected_commit,
            "mr": comp484_drift_path,
            "mr_sha": file_sha(comp484_drift_path),
            "hex": synthetic_hex,
            "elf": synthetic_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": [
                "lower_mr.comp_req_484_fixture_contract",
            ],
        },
        {
            "id": "missing_dependency_binding",
            "commit": args.expected_commit,
            "mr": missing_dependency_path,
            "mr_sha": file_sha(missing_dependency_path),
            "hex": synthetic_hex,
            "elf": synthetic_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": [
                "lower_mr.required_sources_declared",
            ],
        },
        {
            "id": "forged_provenance_timing",
            "commit": args.expected_commit,
            "mr": forged_provenance_timing_path,
            "mr_sha": file_sha(forged_provenance_timing_path),
            "hex": expected_hex,
            "elf": expected_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": [
                "lower_mr.provenance_contract_fixed_values",
            ],
        },
        {
            "id": "forged_provenance_protected",
            "commit": args.expected_commit,
            "mr": forged_provenance_protected_path,
            "mr_sha": file_sha(forged_provenance_protected_path),
            "hex": expected_hex,
            "elf": expected_elf,
            "runner": args.expected_lower_runner_sha256.upper(),
            "supervisor": supervisor_sha,
            "expected_failed": [
                "lower_mr.protected_hashes_exact",
            ],
        },
    ]

    catalog = {
        "schema": "companion.joint-offline-negative-fixtures.v1",
        "requirements": [
            "COMP-REQ-479",
            "COMP-REQ-480",
            "COMP-REQ-484",
            "COMP-REQ-486",
            "COMP-REQ-488",
        ],
        "runner": {
            "path": runner.relative_to(repo_root).as_posix(),
            "sha256": file_sha(runner),
        },
        "compatibility_auditor": {
            "path": auditor.relative_to(repo_root).as_posix(),
            "sha256": file_sha(auditor),
        },
        "lower": {
            "root": lower_root.as_posix(),
            "commit": args.expected_commit,
            "actual_machine_ready": lower_mr.as_posix(),
            "claimed_machine_ready_sha256": claimed_lower_mr_sha,
            "observed_machine_ready_sha256": observed_lower_mr_sha,
            "claimed_machine_ready_match": claimed_lower_mr_match,
        },
        "fixtures": [
            {
                "id": item["id"],
                "commit": item["commit"],
                "machine_ready_path": item["mr"].as_posix(),
                "machine_ready_sha256": item["mr_sha"],
                "expected_failed_checks": item["expected_failed"],
            }
            for item in fixtures
        ],
    }
    catalog_output.parent.mkdir(parents=True, exist_ok=True)
    catalog_output.write_bytes(canonical_bytes(catalog))

    snapshot_before = lower_snapshot(lower_root, lower_mr)

    def run_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
        output_path = output_root / f"joint-upper-lower-{fixture['id']}.json"
        compatibility_path = (
            compatibility_root
            / f"upper-lower-compatibility-{fixture['id']}.json"
        )
        command = [
            sys.executable,
            "-B",
            str(runner),
            "--repo-root",
            str(repo_root),
            "--upper-machine-ready",
            str(repo_root / UPPER_MR_REL),
            "--expected-upper-machine-ready-sha256",
            UPPER_MR_SHA,
            "--expanded-oracle",
            str(repo_root / ORACLE_REL),
            "--expected-expanded-oracle-sha256",
            ORACLE_SHA,
            "--compatibility-auditor",
            str(auditor),
            "--expected-compatibility-auditor-sha256",
            file_sha(auditor),
            "--lower-root",
            str(lower_root),
            "--expected-commit",
            fixture["commit"],
            "--lower-machine-ready",
            str(fixture["mr"]),
            "--expected-lower-machine-ready-sha256",
            fixture["mr_sha"],
            "--expected-lower-runner-sha256",
            fixture["runner"],
            "--expected-lower-supervisor-sha256",
            fixture["supervisor"],
            "--compatibility-output",
            str(compatibility_path),
            "--output",
            str(output_path),
        ]
        for digest in fixture["hex"]:
            command.extend(["--expected-lower-hex-sha256", digest])
        for digest in fixture["elf"]:
            command.extend(["--expected-lower-elf-sha256", digest])

        run_rows = []
        for _ in range(2):
            completed = subprocess.run(
                command,
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
                timeout=90,
            )
            artifact = load_json(output_path) if output_path.is_file() else None
            run_rows.append(
                {
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout.strip(),
                    "stderr": completed.stderr.strip(),
                    "artifact_sha256": file_sha(output_path)
                    if output_path.is_file()
                    else None,
                    "status": artifact.get("status") if artifact else None,
                    "failed_checks": artifact.get("failed_checks")
                    if artifact
                    else None,
                }
            )
        failed_checks = set(run_rows[1]["failed_checks"] or [])
        deterministic = (
            run_rows[0]["artifact_sha256"] == run_rows[1]["artifact_sha256"]
        )
        expected_failures = set(fixture["expected_failed"]).issubset(
            failed_checks
        )
        expected_compatibility = fixture.get("expected_compatibility")
        compatibility = (
            load_json(compatibility_path)
            if compatibility_path.is_file()
            else None
        )
        compatibility_summary = (
            compatibility.get("summary", {})
            if isinstance(compatibility, dict)
            else {}
        )
        compatibility_gap_names = sorted(
            row["event"]
            for row in compatibility.get("event_compatibility", [])
            if row.get("mapping_status") != "mapped"
        ) if isinstance(compatibility, dict) else []
        pair_by_id = {
            row["id"]: row
            for row in compatibility.get("pair_compatibility", [])
        } if isinstance(compatibility, dict) else {}
        pointer_move_pairs = [
            row
            for row in pair_by_id.values()
            if row.get("event") == "pointer_move"
        ]
        pointer_move_directional = [
            row
            for row in pointer_move_pairs
            if row.get("to_state")
            in {"gaze_left", "gaze_up", "gaze_right", "gaze_down"}
        ]
        pointer_move_center = [
            row
            for row in pointer_move_pairs
            if row.get("to_state") == "gaze_center"
        ]
        missing_pair_ids = sorted(
            pair_id
            for pair_id, row in pair_by_id.items()
            if row.get("realizable_lower_path") is not True
        )
        compatibility_regression_match = bool(
            expected_compatibility is None
            or (
                compatibility.get("status")
                == expected_compatibility["status"]
                and compatibility_summary.get("events", {}).get("realizable")
                == expected_compatibility["events_realizable"]
                and compatibility_summary.get("events", {}).get(
                    "mapping_missing"
                )
                == expected_compatibility["events_missing"]
                and compatibility_summary.get("events", {}).get(
                    "mapping_ambiguous"
                )
                == expected_compatibility["events_ambiguous"]
                and compatibility_summary.get("pairs", {}).get("realizable")
                == expected_compatibility["pairs_realizable"]
                and compatibility_summary.get("pairs", {}).get(
                    "semantic_noop_realizable"
                )
                == expected_compatibility["noops_realizable"]
                and compatibility_summary.get("polarity_bridge_realizable")
                is expected_compatibility["polarity_bridge"]
                and compatibility_gap_names
                == expected_compatibility["event_gaps"]
                and all(
                    pair_by_id.get(pair_id, {}).get("realizable_lower_path")
                    is expected
                    for pair_id, expected in expected_compatibility[
                        "representative_pairs"
                    ].items()
                )
                and sum(
                    row.get("realizable_lower_path") is True
                    for row in pointer_move_directional
                )
                == expected_compatibility[
                    "pointer_move_directional_realizable"
                ]
                and sum(
                    row.get("realizable_lower_path") is not True
                    for row in pointer_move_center
                )
                == expected_compatibility["pointer_move_center_missing"]
                and missing_pair_ids
                == expected_compatibility["missing_pair_ids"]
            )
        )
        passed = bool(
            deterministic
            and expected_failures
            and compatibility_regression_match
            and all(row["exit_code"] == 1 for row in run_rows)
            and all(row["status"] == "NO_GO" for row in run_rows)
        )
        return {
            "id": fixture["id"],
            "status": "PASS_NEGATIVE" if passed else "FAIL_NEGATIVE",
            "deterministic_two_runs": deterministic,
            "expected_failed_checks_observed": expected_failures,
            "compatibility_regression_match": compatibility_regression_match,
            "run_1": run_rows[0],
            "run_2": run_rows[1],
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(run_fixture, fixtures))
    snapshot_after = lower_snapshot(lower_root, lower_mr)
    lower_unchanged = snapshot_before == snapshot_after
    count_gate_mutation_matrix = [
        {
            "id": "control_all_counts_and_polarity",
            "events": 21,
            "pairs": 59,
            "semantic_noops": 10,
            "polarity_bridge": True,
            "expected_ready": True,
        },
        {
            "id": "missing_one_event_with_polarity",
            "events": 20,
            "pairs": 59,
            "semantic_noops": 10,
            "polarity_bridge": True,
            "expected_ready": False,
        },
        {
            "id": "missing_one_pair_with_polarity",
            "events": 21,
            "pairs": 58,
            "semantic_noops": 10,
            "polarity_bridge": True,
            "expected_ready": False,
        },
        {
            "id": "missing_one_noop_with_polarity",
            "events": 21,
            "pairs": 59,
            "semantic_noops": 9,
            "polarity_bridge": True,
            "expected_ready": False,
        },
        {
            "id": "missing_polarity_with_full_counts",
            "events": 21,
            "pairs": 59,
            "semantic_noops": 10,
            "polarity_bridge": False,
            "expected_ready": False,
        },
    ]
    for row in count_gate_mutation_matrix:
        row["observed_ready"] = full_compatibility_ready(
            row["events"],
            row["pairs"],
            row["semantic_noops"],
            row["polarity_bridge"],
        )
        row["pass"] = row["observed_ready"] is row["expected_ready"]
    exact_4dd_result = next(
        (
            item
            for item in results
            if item["id"] == "comp_req_488_4dd_call_edge_gaps"
        ),
        None,
    )
    polarity_isolation_pass = bool(
        exact_4dd_result
        and exact_4dd_result["status"] == "PASS_NEGATIVE"
        and exact_4dd_result["compatibility_regression_match"]
    )
    auditor_contract_negatives_pass = bool(
        polarity_isolation_pass
        and all(row["pass"] for row in count_gate_mutation_matrix)
    )
    all_pass = bool(
        lower_unchanged
        and auditor_contract_negatives_pass
        and all(item["status"] == "PASS_NEGATIVE" for item in results)
    )
    result = {
        "schema": "companion.joint-offline-negative-result.v1",
        "requirements": [
            "COMP-REQ-479",
            "COMP-REQ-480",
            "COMP-REQ-484",
            "COMP-REQ-486",
            "COMP-REQ-488",
        ],
        "status": "PASS_NEGATIVE_FIXTURES" if all_pass else "NO_GO_VALIDATOR",
        "catalog": {
            "path": catalog_output.relative_to(repo_root).as_posix(),
            "sha256": file_sha(catalog_output),
        },
        "summary": {
            "fixture_count": len(results),
            "negative_pass_count": sum(
                item["status"] == "PASS_NEGATIVE" for item in results
            ),
            "all_two_run_byte_stable": all(
                item["deterministic_two_runs"] for item in results
            ),
            "lower_tracked_status_unchanged": lower_unchanged,
            "joint_ready_count": 0,
            "claimed_lower_machine_ready_match": claimed_lower_mr_match,
            "auditor_contract_negatives_pass": (
                auditor_contract_negatives_pass
            ),
        },
        "auditor_contract_negatives": {
            "status": (
                "PASS"
                if auditor_contract_negatives_pass
                else "NO_GO"
            ),
            "polarity_isolation": {
                "status": "PASS" if polarity_isolation_pass else "NO_GO",
                "claim": (
                    "A realizable polarity bridge does not globally promote "
                    "unreachable event or pair mappings."
                ),
                "exact_4dd_expected": {
                    "polarity_bridge": True,
                    "events": "17/21",
                    "pairs": "51/59",
                    "semantic_noops": "8/10",
                    "joint_status": "NO_GO",
                },
            },
            "count_gate_mutation_matrix": count_gate_mutation_matrix,
            "rule": (
                "21/21 events, 59/59 pairs, 10/10 semantic no-ops, and "
                "polarity are independent conjunctive requirements."
            ),
        },
        "lower_read_only_snapshot": {
            "before": snapshot_before,
            "after": snapshot_after,
            "before_sha256": sha256(canonical_bytes(snapshot_before)),
            "after_sha256": sha256(canonical_bytes(snapshot_after)),
            "unchanged": lower_unchanged,
        },
        "results": results,
        "side_effect_counters": {
            "execute": 0,
            "server": 0,
            "browser": 0,
            "prompt": 0,
            "popup": 0,
            "hardware": 0,
            "lower_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "push": 0,
            "upper_fixture_writes": len(fixture_mrs) + len(results) * 2 + 2,
        },
        "generator": {
            "path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "sha256": file_sha(Path(__file__).resolve()),
        },
    }
    result_output.parent.mkdir(parents=True, exist_ok=True)
    result_output.write_bytes(canonical_bytes(result))
    print(
        json.dumps(
            {
                "status": result["status"],
                "fixtures": f"{result['summary']['negative_pass_count']}/"
                f"{result['summary']['fixture_count']}",
                "byte_stable": result["summary"]["all_two_run_byte_stable"],
                "artifact_sha256": file_sha(result_output),
            },
            sort_keys=True,
        )
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
