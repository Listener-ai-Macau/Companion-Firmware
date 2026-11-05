#!/usr/bin/env python3
"""Default-off, read-only COMP-REQ-479/480 joint offline gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


UPPER_MACHINE_READY_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471/"
    "UPPER_MACHINE_READY.json"
)
EXPANDED_ORACLE_REL = Path(
    "docs/art/exports/companion-browser-visual-contract-comp-req-471/"
    "expanded-window-oracle.json"
)
VALIDATION_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471"
)
EXPECTED_UPPER_MACHINE_READY_SHA256 = (
    "EAD7000FEB32CD7915FEAD82A49D23FD66755412AEDFA53B4B7A264CABA3BB69"
)
EXPECTED_EXPANDED_ORACLE_SHA256 = (
    "20C270A332F7AD75FAED3C44C9AE3C1D789F7902ABA525C07B0B40F4266C5B2E"
)
EXPECTED_CONVERTED_CENTERED_SHA256 = (
    "EF4CDB579CC2C43645E0E3585D8C40CA65763112619E5EB9FBC583EAF3E28DBD"
)
COMP_REQ_478_FIXTURE_TOKENS = {
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
}
COMP_REQ_484_FIXTURE_TOKENS = {
    "bounded_15_deltas=pass",
    "hold_650_menu_3000=pass",
    "menu_idle_481_selection=pass",
    "recording_idle_481_return=pass",
    "busy_captured_gaze_same_burst=pass",
}
COMP_REQ_478_MODE_FLAGS = {
    "bounded_seeds_only_when_not_continuous",
    "bridge_terminal_fault_latch",
    "continuous_has_no_synthetic_enqueue",
    "host_synthetic_label",
    "no_browser_guard_in_adapter",
    "physical_double_tap_guard",
    "runtime_terminal_fault_latch",
    "single_tap_window_guard",
}
LOWER_SCHEMA = "companion.lower-visual-runtime-machine-ready.v1"
LOWER_STATUS = "LOWER_MACHINE_READY"
PROVENANCE_REQUIREMENTS = {"COMP-REQ-484", "COMP-REQ-486", "COMP-REQ-488"}
HEX_64_RE = re.compile(r"[0-9A-Fa-f]{64}")
HEX_40_RE = re.compile(r"[0-9A-Fa-f]{40}")
OUTPUT_RE = re.compile(r"joint-upper-lower-[A-Za-z0-9._-]+\.json")
COMPATIBILITY_OUTPUT_RE = re.compile(
    r"upper-lower-compatibility-[A-Za-z0-9._-]+\.json"
)
MAX_LOWER_MR_BYTES = 2_000_000
MAX_DECLARED_SOURCES = 64
MAX_BUILD_ARTIFACT_BYTES = 64 * 1024 * 1024

FRESHNESS_BASELINE_COMMIT = "a96368d5859c54d3eaee4c9846386c6091dc73a0"
FRESHNESS_BASELINE_HEX_SHA256 = {
    "328612A050B62995B93AD741B6DF933813025F8FE2637A6E87366DE630BAA5E6",
    "3DF646B1C0B2A7C4F558D50F2FAEC64CB8CA72FD7A17A61BEB7932BC2E07EC00",
}
FRESHNESS_BASELINE_ELF_SHA256 = {
    "62C6D00E2013A0975DFE745D8D94C5FBD81499AE6EEE40D9C51C351F3E49942B",
    "D679C93C491F9E5ED4EB7FAA73EF8E7CD56046387E8539E1C586042B9CDF1E07",
}
ACTIVE_BUILD_SOURCE_PATHS = {
    "app/companion_pendant/epaper/companion_visual_runtime_adapter.c",
    "app/companion_pendant/epaper/companion_visual_runtime_adapter.h",
    "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c",
    "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.h",
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c",
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
}
BUILD_MODE_PATHS = {
    "bounded": {
        "directory": (
            "cubeide/Companion_Nucleo_WB55RG_Bringup/"
            "build_ssd1681_r7_visual_runtime"
        ),
        "stem": "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime",
        "required_define": (
            "-DCOMPANION_EPAPER_SSD1681_R7_VISUAL_RUNTIME_DIAGNOSTIC=1"
        ),
        "forbidden_define": (
            "-DCOMPANION_EPAPER_SSD1681_R7_VISUAL_RUNTIME_"
            "CONTINUOUS_DIAGNOSTIC=1"
        ),
    },
    "continuous": {
        "directory": (
            "cubeide/Companion_Nucleo_WB55RG_Bringup/"
            "build_ssd1681_r7_visual_runtime_continuous"
        ),
        "stem": "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntimeContinuous",
        "required_define": (
            "-DCOMPANION_EPAPER_SSD1681_R7_VISUAL_RUNTIME_"
            "CONTINUOUS_DIAGNOSTIC=1"
        ),
        "forbidden_define": "",
    },
}

REQUIRED_LOWER_SOURCE_PATHS = {
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
}

PROTECTED_GIT_OBJECTS = {
    "panel_driver": {
        "path": (
            "app/companion_pendant/epaper/"
            "panel_target_stm32wb_ssd1681.c"
        ),
        "git_blob": "f856d7ce0b8915e5059620c3faa97aa06b06eb4e",
    },
    "r7_header": {
        "path": (
            "app/companion_pendant/epaper/"
            "companion_r7_locked_v9_frames.h"
        ),
        "git_blob": "2220da0c1113a5cdad7028aeae578d9fe26e936f",
    },
}

REQUIRED_SIDE_EFFECT_KEYS = {
    "execute",
    "server",
    "browser",
    "prompt",
    "popup",
    "hardware",
    "write",
    "programmer",
    "serial",
    "flash",
    "production",
    "push",
}

COMPATIBILITY_SIDE_EFFECT_KEYS = {
    "operator_execute",
    "server_probe",
    "server_start",
    "browser_start",
    "popup",
    "operator_prompt",
    "hardware",
    "lower_write",
    "platform_write",
    "production_write",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def git_object_sha1(kind: str, data: bytes) -> str:
    header = f"{kind} {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def git_read(root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: "
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


def resolve_repo_path(root: Path, supplied: Path) -> Path:
    return supplied.resolve() if supplied.is_absolute() else (root / supplied).resolve()


def require_inside(path: Path, root: Path, label: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} must stay within {root}") from error


def normalize_hash(value: Any) -> str | None:
    if isinstance(value, str) and HEX_64_RE.fullmatch(value):
        return value.upper()
    return None


def normalize_hashes(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if HEX_64_RE.fullmatch(value) is None:
            raise ValueError("expected artifact hashes must be exact 64-hex")
        result.append(value.upper())
    return sorted(result)


def append_check(
    checks: dict[str, bool],
    observations: dict[str, Any],
    name: str,
    passed: bool,
    observed: Any = None,
) -> None:
    checks[name] = bool(passed)
    if observed is not None:
        observations[name] = observed


def source_bindings(machine_ready: dict[str, Any] | None) -> dict[str, str]:
    if machine_ready is None:
        return {}
    raw = machine_ready.get("source_bindings")
    result: dict[str, str] = {}
    if isinstance(raw, dict):
        for path, value in raw.items():
            digest = (
                normalize_hash(value)
                if isinstance(value, str)
                else normalize_hash(value.get("sha256"))
                if isinstance(value, dict)
                else None
            )
            if isinstance(path, str) and digest:
                result[path.replace("\\", "/")] = digest
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            digest = normalize_hash(item.get("sha256"))
            if isinstance(path, str) and digest:
                result[path.replace("\\", "/")] = digest
    if not result and isinstance(machine_ready, dict):
        for item in provenance_bindings(machine_ready).values():
            path = item["path"]
            if Path(path).suffix.lower() in (".c", ".h", ".ps1", ".py"):
                result[path] = item["sha256"]
    return result


def provenance_bindings(
    machine_ready: dict[str, Any] | None,
) -> dict[str, dict[str, str]]:
    if machine_ready is None:
        return {}
    raw_sets = [
        value
        for value in (
            machine_ready.get("bindings"),
            machine_ready.get("artifacts"),
        )
        if isinstance(value, dict)
    ]
    result: dict[str, dict[str, str]] = {}
    for raw in raw_sets:
        for name, item in raw.items():
            if not isinstance(name, str) or not isinstance(item, dict):
                continue
            path = item.get("path")
            digest = normalize_hash(item.get("sha256"))
            if isinstance(path, str) and digest:
                result[name] = {
                    "path": path.replace("\\", "/"),
                    "sha256": digest,
                }
    return result


def is_provenance_mr(machine_ready: dict[str, Any] | None) -> bool:
    return bool(
        machine_ready
        and machine_ready.get("requirement_id") in PROVENANCE_REQUIREMENTS
        and machine_ready.get("status") == "MACHINE_READY"
    )


def artifact_descriptors(
    machine_ready: dict[str, Any] | None, kind: str
) -> list[dict[str, str]]:
    if machine_ready is None:
        return []
    artifacts = machine_ready.get("artifacts")
    if not isinstance(artifacts, dict):
        provenance = provenance_bindings(machine_ready)
        names = (
            ("bounded_hex", "live_hex")
            if kind == "hex"
            else ("bounded_elf", "live_elf")
            if kind == "elf"
            else (kind,)
        )
        return [
            provenance[name]
            for name in names
            if name in provenance
        ]
    raw = artifacts.get(kind)
    if raw is None and kind in ("hex", "elf"):
        names = (
            ("bounded_hex", "live_hex")
            if kind == "hex"
            else ("bounded_elf", "live_elf")
        )
        return [
            {
                "path": artifacts[name]["path"],
                "sha256": normalize_hash(artifacts[name]["sha256"]),
            }
            for name in names
            if isinstance(artifacts.get(name), dict)
            and isinstance(artifacts[name].get("path"), str)
            and normalize_hash(artifacts[name].get("sha256"))
        ]
    values = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
    result = []
    for item in values:
        path = item.get("path")
        digest = normalize_hash(item.get("sha256"))
        if isinstance(path, str) and digest:
            result.append({"path": path, "sha256": digest})
    return result


def declared_build_hashes(
    machine_ready: dict[str, Any] | None, kind: str
) -> list[str]:
    descriptors = artifact_descriptors(machine_ready, kind)
    if descriptors:
        return sorted(item["sha256"] for item in descriptors)
    if machine_ready is None:
        return []
    evidence = machine_ready.get("arm_build_evidence")
    result = []
    if isinstance(evidence, dict):
        for mode in sorted(evidence):
            item = evidence[mode]
            digest = (
                normalize_hash(item.get(f"{kind}_sha256"))
                if isinstance(item, dict)
                else None
            )
            if digest:
                result.append(digest)
    return sorted(result)


def declared_tool_descriptor(
    machine_ready: dict[str, Any] | None,
    kind: str,
    bindings: dict[str, str],
) -> dict[str, str] | None:
    provenance = provenance_bindings(machine_ready)
    if kind in provenance:
        return provenance[kind]
    descriptors = artifact_descriptors(machine_ready, kind)
    if len(descriptors) == 1:
        return descriptors[0]
    if machine_ready is None:
        return None
    digest = normalize_hash(machine_ready.get(f"{kind}_sha256"))
    if digest is None:
        return None
    matching_paths = [
        path for path, value in bindings.items() if value == digest
    ]
    if len(matching_paths) != 1:
        return {"path": "", "sha256": digest}
    return {"path": matching_paths[0], "sha256": digest}


def lower_side_effects(machine_ready: dict[str, Any] | None) -> dict[str, Any]:
    if machine_ready is None:
        return {}
    raw = machine_ready.get("side_effect_counters")
    if isinstance(raw, dict):
        return dict(raw)
    provenance_side = machine_ready.get("side_effects")
    if isinstance(provenance_side, dict):
        return {
            key: (
                0
                if value is False
                else 1
                if value is True
                else value
            )
            for key, value in provenance_side.items()
        }
    result: dict[str, Any] = {}
    if "hardware_contact" in machine_ready:
        result["hardware"] = machine_ready["hardware_contact"]
    if "popup" in machine_ready:
        result["popup"] = machine_ready["popup"]
    fixture = machine_ready.get("fixture")
    checkonly = fixture.get("checkonly") if isinstance(fixture, dict) else None
    if isinstance(checkonly, dict):
        aliases = {
            "hardware_contact": "hardware",
            "write": "write",
            "programmer": "programmer",
            "serial": "serial",
            "popup": "popup",
        }
        for source, target in aliases.items():
            if source in checkonly:
                result[target] = checkonly[source]
    return result


def lower_compatibility_claims(
    machine_ready: dict[str, Any] | None,
) -> dict[str, Any]:
    if machine_ready is None:
        return {}
    raw = machine_ready.get("compatibility_claims")
    return dict(raw) if isinstance(raw, dict) else {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--upper-machine-ready", type=Path, required=True)
    parser.add_argument(
        "--expected-upper-machine-ready-sha256", required=True
    )
    parser.add_argument("--expanded-oracle", type=Path, required=True)
    parser.add_argument("--expected-expanded-oracle-sha256", required=True)
    parser.add_argument("--compatibility-auditor", type=Path, required=True)
    parser.add_argument("--expected-compatibility-auditor-sha256", required=True)
    parser.add_argument("--lower-root", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--lower-machine-ready", type=Path, required=True)
    parser.add_argument(
        "--expected-lower-machine-ready-sha256", required=True
    )
    parser.add_argument(
        "--expected-lower-hex-sha256", action="append", required=True
    )
    parser.add_argument(
        "--expected-lower-elf-sha256", action="append", required=True
    )
    parser.add_argument("--expected-lower-runner-sha256", required=True)
    parser.add_argument("--expected-lower-supervisor-sha256", required=True)
    parser.add_argument("--compatibility-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[2]
    )
    lower_root = args.lower_root.resolve()
    upper_path = resolve_repo_path(repo_root, args.upper_machine_ready)
    oracle_path = resolve_repo_path(repo_root, args.expanded_oracle)
    auditor_path = resolve_repo_path(repo_root, args.compatibility_auditor)
    lower_mr_path = resolve_repo_path(lower_root, args.lower_machine_ready)
    output_path = resolve_repo_path(repo_root, args.output)
    compatibility_output_path = resolve_repo_path(
        repo_root, args.compatibility_output
    )
    validation_root = (repo_root / VALIDATION_REL).resolve()

    require_inside(output_path, validation_root, "joint output")
    require_inside(
        compatibility_output_path, validation_root, "compatibility output"
    )
    lower_mr_inside_lower = True
    try:
        lower_mr_path.relative_to(lower_root)
    except ValueError:
        lower_mr_inside_lower = False
    if not lower_mr_inside_lower:
        fixture_root = (
            validation_root / "joint-negative-fixtures" / "lower-mr"
        ).resolve()
        require_inside(
            lower_mr_path,
            fixture_root,
            "lower MACHINE_READY or upper-owned negative fixture",
        )
    if OUTPUT_RE.fullmatch(output_path.name) is None:
        raise SystemExit("joint output filename is not bounded")
    if COMPATIBILITY_OUTPUT_RE.fullmatch(compatibility_output_path.name) is None:
        raise SystemExit("compatibility output filename is not bounded")
    if HEX_40_RE.fullmatch(args.expected_commit) is None:
        raise SystemExit("--expected-commit must be exact 40-hex")

    expected_hash_args = {
        "upper_machine_ready": normalize_hash(
            args.expected_upper_machine_ready_sha256
        ),
        "expanded_oracle": normalize_hash(
            args.expected_expanded_oracle_sha256
        ),
        "compatibility_auditor": normalize_hash(
            args.expected_compatibility_auditor_sha256
        ),
        "lower_machine_ready": normalize_hash(
            args.expected_lower_machine_ready_sha256
        ),
        "lower_runner": normalize_hash(args.expected_lower_runner_sha256),
        "lower_supervisor": normalize_hash(
            args.expected_lower_supervisor_sha256
        ),
    }
    if any(value is None for value in expected_hash_args.values()):
        raise SystemExit("all expected identities must be exact 64-hex")
    expected_hex = normalize_hashes(args.expected_lower_hex_sha256)
    expected_elf = normalize_hashes(args.expected_lower_elf_sha256)

    checks: dict[str, bool] = {}
    observations: dict[str, Any] = {}

    append_check(
        checks,
        observations,
        "input.upper_path_exact",
        upper_path == (repo_root / UPPER_MACHINE_READY_REL).resolve(),
        upper_path.as_posix(),
    )
    append_check(
        checks,
        observations,
        "input.oracle_path_exact",
        oracle_path == (repo_root / EXPANDED_ORACLE_REL).resolve(),
        oracle_path.as_posix(),
    )
    append_check(
        checks,
        observations,
        "input.expected_upper_hash_is_accepted",
        expected_hash_args["upper_machine_ready"]
        == EXPECTED_UPPER_MACHINE_READY_SHA256,
    )
    append_check(
        checks,
        observations,
        "input.expected_oracle_hash_is_accepted",
        expected_hash_args["expanded_oracle"]
        == EXPECTED_EXPANDED_ORACLE_SHA256,
    )

    upper = load_json(upper_path) if upper_path.is_file() else None
    upper_observed_sha = file_sha(upper_path) if upper_path.is_file() else None
    append_check(
        checks,
        observations,
        "upper.file_exists",
        upper is not None,
    )
    append_check(
        checks,
        observations,
        "upper.hash_exact",
        upper_observed_sha == expected_hash_args["upper_machine_ready"],
        upper_observed_sha,
    )
    append_check(
        checks,
        observations,
        "upper.schema_status_pass",
        bool(
            upper
            and upper.get("schema") == "companion.upper-machine-ready.v1"
            and upper.get("status") == "UPPER_MACHINE_READY"
            and upper.get("failed") == []
        ),
    )
    upper_checks = upper.get("checks") if isinstance(upper, dict) else None
    append_check(
        checks,
        observations,
        "upper.all_machine_checks_true",
        bool(
            isinstance(upper_checks, dict)
            and upper_checks
            and all(value is True for value in upper_checks.values())
        ),
    )
    upper_side = (
        upper.get("side_effect_counters") if isinstance(upper, dict) else None
    )
    upper_forbidden = {
        key: upper_side.get(key)
        for key in ("execute", "hardware", "process", "product_write",
                    "production", "prompt", "server", "browser")
        if isinstance(upper_side, dict)
    }
    append_check(
        checks,
        observations,
        "upper.runtime_side_effects_zero",
        len(upper_forbidden) == 8
        and all(value == 0 for value in upper_forbidden.values()),
        upper_forbidden,
    )

    oracle = load_json(oracle_path) if oracle_path.is_file() else None
    oracle_observed_sha = file_sha(oracle_path) if oracle_path.is_file() else None
    append_check(checks, observations, "oracle.file_exists", oracle is not None)
    append_check(
        checks,
        observations,
        "oracle.hash_exact",
        oracle_observed_sha == expected_hash_args["expanded_oracle"],
        oracle_observed_sha,
    )
    append_check(
        checks,
        observations,
        "oracle.structure_59_10_pass",
        bool(
            oracle
            and oracle.get("status") == "PASS"
            and oracle.get("expanded_pair_count") == 59
            and len(oracle.get("pairs", [])) == 59
            and oracle.get("statistics", {}).get("pixel_noop_pair_count") == 10
            and oracle.get("statistics", {}).get(
                "nonmenu_full_frame_pair_count"
            )
            == 0
        ),
    )

    auditor_observed_sha = (
        file_sha(auditor_path) if auditor_path.is_file() else None
    )
    append_check(
        checks,
        observations,
        "auditor.file_exists",
        auditor_path.is_file(),
    )
    append_check(
        checks,
        observations,
        "auditor.hash_exact",
        auditor_observed_sha == expected_hash_args["compatibility_auditor"],
        auditor_observed_sha,
    )

    try:
        lower_toplevel = Path(
            git_read(lower_root, "rev-parse", "--show-toplevel")
            .decode("utf-8")
            .strip()
        ).resolve()
        resolved_commit = (
            git_read(
                lower_root,
                "rev-parse",
                f"{args.expected_commit}^{{commit}}",
            )
            .decode("ascii")
            .strip()
        )
        commit_data = git_read(lower_root, "cat-file", "commit", resolved_commit)
    except Exception as error:
        lower_toplevel = None
        resolved_commit = None
        commit_data = b""
        observations["lower.git_error"] = str(error)
    append_check(
        checks,
        observations,
        "lower.root_is_exact_toplevel",
        lower_toplevel == lower_root,
        lower_toplevel.as_posix() if lower_toplevel else None,
    )
    append_check(
        checks,
        observations,
        "lower.commit_exact",
        resolved_commit == args.expected_commit.lower(),
        resolved_commit,
    )
    append_check(
        checks,
        observations,
        "lower.commit_object_recomputed",
        bool(
            resolved_commit
            and git_object_sha1("commit", commit_data) == resolved_commit
        ),
        git_object_sha1("commit", commit_data) if commit_data else None,
    )

    lower_mr: dict[str, Any] | None = None
    lower_mr_error = None
    if lower_mr_path.is_file() and lower_mr_path.stat().st_size <= MAX_LOWER_MR_BYTES:
        try:
            lower_mr = load_json(lower_mr_path)
        except Exception as error:
            lower_mr_error = str(error)
    lower_mr_observed_sha = (
        file_sha(lower_mr_path) if lower_mr_path.is_file() else None
    )
    append_check(
        checks,
        observations,
        "lower_mr.file_exists_and_bounded",
        bool(
            lower_mr_path.is_file()
            and lower_mr_path.stat().st_size <= MAX_LOWER_MR_BYTES
        ),
        {
            "path": lower_mr_path.as_posix(),
            "bytes": lower_mr_path.stat().st_size
            if lower_mr_path.is_file()
            else None,
        },
    )
    append_check(
        checks,
        observations,
        "lower_mr.json_object",
        lower_mr is not None,
        lower_mr_error,
    )
    append_check(
        checks,
        observations,
        "lower_mr.hash_exact",
        lower_mr_observed_sha == expected_hash_args["lower_machine_ready"],
        lower_mr_observed_sha,
    )
    append_check(
        checks,
        observations,
        "lower_mr.schema_exact",
        bool(
            lower_mr
            and (
                lower_mr.get("schema") == LOWER_SCHEMA
                or is_provenance_mr(lower_mr)
            )
        ),
        {
            "schema": lower_mr.get("schema") if lower_mr else None,
            "requirement_id": (
                lower_mr.get("requirement_id") if lower_mr else None
            ),
        },
    )
    append_check(
        checks,
        observations,
        "lower_mr.status_exact",
        bool(
            lower_mr
            and lower_mr.get("status")
            in (LOWER_STATUS, "MACHINE_READY")
        ),
        lower_mr.get("status") if lower_mr else None,
    )
    append_check(
        checks,
        observations,
        "lower_mr.commit_exact",
        bool(
            lower_mr
            and (
                lower_mr.get("source_commit") == args.expected_commit
                or lower_mr.get("exact_source_commit")
                == args.expected_commit
            )
        ),
        {
            "source_commit": (
                lower_mr.get("source_commit") if lower_mr else None
            ),
            "exact_source_commit": (
                lower_mr.get("exact_source_commit") if lower_mr else None
            ),
        },
    )

    provenance = provenance_bindings(lower_mr)
    provenance_rows = []
    for name, item in sorted(provenance.items()):
        path = resolve_repo_path(lower_root, Path(item["path"]))
        inside = True
        try:
            path.relative_to(lower_root)
        except ValueError:
            inside = False
        observed = (
            file_sha(path)
            if inside
            and path.is_file()
            and path.stat().st_size <= MAX_BUILD_ARTIFACT_BYTES
            else None
        )
        provenance_rows.append(
            {
                "name": name,
                "path": path.as_posix(),
                "inside_lower_root": inside,
                "declared_sha256": item["sha256"],
                "observed_sha256": observed,
                "match": observed == item["sha256"],
            }
        )
    append_check(
        checks,
        observations,
        "lower_mr.all_provenance_bindings_rehashed",
        bool(
            not is_provenance_mr(lower_mr)
            or (
                provenance_rows
                and len(provenance_rows) == len(provenance)
                and all(row["match"] for row in provenance_rows)
            )
        ),
        provenance_rows,
    )

    bindings = source_bindings(lower_mr)
    source_results = []
    if resolved_commit and len(bindings) <= MAX_DECLARED_SOURCES:
        commit_paths = set(
            git_read(lower_root, "ls-tree", "-r", "--name-only", resolved_commit)
            .decode("utf-8")
            .splitlines()
        )
        for path, declared_sha in sorted(bindings.items()):
            safe_path = (
                not Path(path).is_absolute()
                and ".." not in Path(path).parts
                and path in commit_paths
            )
            commit_sha = None
            physical_sha = None
            blob_object = None
            recomputed_blob = None
            clean_against_commit = False
            if safe_path:
                data = git_read(lower_root, "show", f"{resolved_commit}:{path}")
                blob_object = (
                    git_read(lower_root, "rev-parse", f"{resolved_commit}:{path}")
                    .decode("ascii")
                    .strip()
                )
                recomputed_blob = git_object_sha1("blob", data)
                commit_sha = sha256(data)
                physical_path = (lower_root / path).resolve()
                if physical_path.is_file():
                    physical_sha = file_sha(physical_path)
                clean_check = subprocess.run(
                    [
                        "git",
                        "diff",
                        "--quiet",
                        resolved_commit,
                        "--",
                        path,
                    ],
                    cwd=lower_root,
                    check=False,
                    capture_output=True,
                )
                clean_against_commit = clean_check.returncode == 0
            source_results.append(
                {
                    "path": path,
                    "declared_sha256": declared_sha,
                    "physical_sha256": physical_sha,
                    "commit_blob_sha256": commit_sha,
                    "declared_matches_physical": physical_sha == declared_sha,
                    "git_blob_object": blob_object,
                    "recomputed_git_blob_object": recomputed_blob,
                    "blob_match": blob_object == recomputed_blob
                    if blob_object
                    else False,
                    "worktree_clean_against_commit": clean_against_commit,
                    "safe_commit_path": safe_path,
                }
            )
    append_check(
        checks,
        observations,
        "lower_mr.sources_declared_and_bounded",
        bool(bindings and len(bindings) <= MAX_DECLARED_SOURCES),
        {"count": len(bindings)},
    )
    append_check(
        checks,
        observations,
        "lower_mr.required_sources_declared",
        bool(
            (
                is_provenance_mr(lower_mr)
                and (
                    {
                        "runner",
                        "supervisor",
                        "bounded_hex",
                        "bounded_elf",
                        "live_hex",
                        "live_elf",
                    }.issubset(provenance)
                    if lower_mr.get("requirement_id") == "COMP-REQ-488"
                    else {
                        "adapter",
                        "fixture",
                        "verifier",
                        "runner",
                        "supervisor",
                    }.issubset(provenance)
                )
            )
            or (
                not is_provenance_mr(lower_mr)
                and REQUIRED_LOWER_SOURCE_PATHS.issubset(bindings)
            )
        ),
        {
            "legacy_missing": sorted(
                REQUIRED_LOWER_SOURCE_PATHS.difference(bindings)
            ),
            "provenance_missing": sorted(
                {
                    "adapter",
                    "fixture",
                    "verifier",
                    "runner",
                    "supervisor",
                }.difference(provenance)
            ),
        },
    )
    append_check(
        checks,
        observations,
        "lower_mr.all_sources_recomputed",
        bool(
            source_results
            and len(source_results) == len(bindings)
            and all(
                item["safe_commit_path"]
                and item["declared_matches_physical"]
                and item["blob_match"]
                and item["worktree_clean_against_commit"]
                for item in source_results
            )
        ),
        source_results,
    )

    commit_texts: dict[str, str] = {}
    for path in (
        "app/companion_pendant/epaper/companion_visual_runtime_adapter.c",
        "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
    ):
        try:
            commit_texts[path] = git_read(
                lower_root, "show", f"{resolved_commit}:{path}"
            ).decode("utf-8")
        except Exception:
            commit_texts[path] = ""
    runtime_source = commit_texts[
        "app/companion_pendant/epaper/companion_visual_runtime_adapter.c"
    ]
    bridge_source = commit_texts[
        "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c"
    ]
    main_source = commit_texts[
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
    ]
    make_source = commit_texts[
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
    ]
    source_478 = {
        "peek_then_discard_retention": all(
            token in runtime_source
            for token in (
                "companion_visual_runtime_peek(runtime, &event)",
                "companion_visual_runtime_discard(runtime)",
                "runtime->terminal_fault = true",
            )
        ),
        "transport_fault_and_close_latches": all(
            token in bridge_source
            for token in (
                "s_visual_closed || s_visual_fault",
                "s_visual_closed = true",
                "s_visual_fault = true",
            )
        ),
        "same_burst_cadence_and_idle_reset": all(
            token in bridge_source
            for token in (
                "s_visual_cadence_valid && s_visual_burst_active",
                "delta == 0u || delta > 480u",
                "if (!active) s_visual_cadence_valid = false",
            )
        ),
        "transaction_busy_limits": all(
            token in bridge_source
            for token in (
                "s_visual_last_transaction_ms > 480u",
                "busy_ms > 600u",
            )
        ),
        "converted_centered_initialization": all(
            token in bridge_source
            for token in (
                "companion_visual_runtime_copy_panel_frame",
                "COMPANION_VISUAL_STATE_CENTERED_REST",
                "bridge_data(visual_baseline, 5000u)",
            )
        ),
        "bounded_continuous_split": all(
            token in main_source
            for token in (
                "#if !COMPANION_EPAPER_SSD1681_R7_VISUAL_RUNTIME_CONTINUOUS_DIAGNOSTIC",
                "s_visual_runtime.serviced_events < 16u",
                "s_visual_runtime_cleanup_done = true",
            )
        ),
        "burst_state_drives_transport": (
            "companion_r7_runtime_bridge_visual_set_burst_active"
            in main_source
        ),
        "physical_gesture_constants": all(
            token in main_source
            for token in (
                "#define TOUCH_HOLD_FEEDBACK_MIN_DURATION_MS 650u",
                "#define TOUCH_DOUBLE_TAP_MAX_GAP_MS 650u",
                "#define TOUCH_DOUBLE_TAP_MAX_MOVE_PX 40u",
            )
        ),
        "build_modes_declared": all(
            token in make_source
            for token in (
                "EPAPER_SSD1681_R7_VISUAL_RUNTIME_DIAGNOSTIC",
                "EPAPER_SSD1681_R7_VISUAL_RUNTIME_CONTINUOUS_DIAGNOSTIC",
                "COMPANION_VISUAL_ASSET_PACK_ENABLE=1",
            )
        ),
    }
    append_check(
        checks,
        observations,
        "lower.source_comp_req_478_contract",
        all(source_478.values()),
        source_478,
    )
    service_match = re.search(
        r"static void service_visual_runtime_controller\(void\)\s*\{"
        r"(?P<body>.*?)\n\}",
        main_source,
        flags=re.DOTALL,
    )
    service_body = service_match.group("body") if service_match else ""
    source_484 = {
        "queued_work_only_burst_state": (
            service_body.count(
                "companion_r7_runtime_bridge_visual_set_burst_active("
            )
            == 2
            and service_body.count("s_visual_runtime.ring_count != 0u") == 3
            and "s_touch_gesture.active" not in service_body
            and "s_menu_entry_pending" not in service_body
            and "Companion_Screen_IsMenuVisible()" not in service_body
            and "s_recording_fsm.state" not in service_body
        ),
        "post_enqueue_burst_refresh": bool(
            re.search(
                r"companion_visual_runtime_enqueue\(.*?"
                r"s_visual_qualification_path\[next_index\]\);.*?"
                r"companion_r7_runtime_bridge_visual_set_burst_active\(\s*"
                r"s_visual_runtime\.ring_count != 0u\);",
                service_body,
                flags=re.DOTALL,
            )
        ),
    }
    append_check(
        checks,
        observations,
        "lower.source_comp_req_484_contract",
        all(source_484.values()),
        source_484,
    )

    declared_hex = declared_build_hashes(lower_mr, "hex")
    declared_elf = declared_build_hashes(lower_mr, "elf")
    hex_descriptors = artifact_descriptors(lower_mr, "hex")
    elf_descriptors = artifact_descriptors(lower_mr, "elf")
    append_check(
        checks,
        observations,
        "lower_mr.hex_hashes_explicit_match",
        declared_hex == expected_hex,
        {"declared": declared_hex, "expected": expected_hex},
    )
    append_check(
        checks,
        observations,
        "lower_mr.elf_hashes_explicit_match",
        declared_elf == expected_elf,
        {"declared": declared_elf, "expected": expected_elf},
    )
    append_check(
        checks,
        observations,
        "lower_mr.hex_paths_declared",
        len(hex_descriptors) == len(expected_hex) and len(expected_hex) > 0,
    )
    append_check(
        checks,
        observations,
        "lower_mr.elf_paths_declared",
        len(elf_descriptors) == len(expected_elf) and len(expected_elf) > 0,
    )

    def verify_artifacts(
        descriptors: list[dict[str, str]], expected: list[str]
    ) -> tuple[bool, list[dict[str, Any]]]:
        rows = []
        for item in descriptors:
            path = resolve_repo_path(lower_root, Path(item["path"]))
            inside = True
            try:
                path.relative_to(lower_root)
            except ValueError:
                inside = False
            observed = (
                file_sha(path)
                if inside
                and path.is_file()
                and path.stat().st_size <= MAX_BUILD_ARTIFACT_BYTES
                else None
            )
            rows.append(
                {
                    "path": path.as_posix(),
                    "inside_lower_root": inside,
                    "bytes": path.stat().st_size if path.is_file() else None,
                    "declared_sha256": item["sha256"],
                    "observed_sha256": observed,
                    "match": observed == item["sha256"],
                }
            )
        passed = (
            len(rows) == len(expected)
            and sorted(item["declared_sha256"] for item in rows) == expected
            and all(
                item["inside_lower_root"]
                and item["match"]
                and isinstance(item["bytes"], int)
                and item["bytes"] <= MAX_BUILD_ARTIFACT_BYTES
                for item in rows
            )
        )
        return passed, rows

    hex_pass, hex_rows = verify_artifacts(hex_descriptors, expected_hex)
    elf_pass, elf_rows = verify_artifacts(elf_descriptors, expected_elf)
    append_check(
        checks, observations, "lower_mr.hex_files_rehashed", hex_pass, hex_rows
    )
    append_check(
        checks, observations, "lower_mr.elf_files_rehashed", elf_pass, elf_rows
    )

    baseline_resolved = None
    baseline_is_ancestor = False
    active_source_deltas: list[str] = []
    if resolved_commit:
        try:
            baseline_resolved = (
                git_read(
                    lower_root,
                    "rev-parse",
                    f"{FRESHNESS_BASELINE_COMMIT}^{{commit}}",
                )
                .decode("ascii")
                .strip()
            )
            ancestor = subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    baseline_resolved,
                    resolved_commit,
                ],
                cwd=lower_root,
                check=False,
                capture_output=True,
            )
            baseline_is_ancestor = ancestor.returncode == 0
            if baseline_is_ancestor and resolved_commit != baseline_resolved:
                active_source_deltas = sorted(
                    line
                    for line in git_read(
                        lower_root,
                        "diff",
                        "--name-only",
                        baseline_resolved,
                        resolved_commit,
                        "--",
                        *sorted(ACTIVE_BUILD_SOURCE_PATHS),
                    )
                    .decode("utf-8")
                    .splitlines()
                    if line
                )
        except Exception as error:
            observations["lower.build_freshness_baseline_error"] = str(error)
    reused_baseline_build_identity = bool(
        set(expected_hex) == FRESHNESS_BASELINE_HEX_SHA256
        and set(expected_elf) == FRESHNESS_BASELINE_ELF_SHA256
    )
    stale_against_changed_sources = bool(
        baseline_is_ancestor
        and resolved_commit != baseline_resolved
        and active_source_deltas
        and reused_baseline_build_identity
    )
    append_check(
        checks,
        observations,
        "lower.build_identity_changes_with_active_sources",
        not stale_against_changed_sources,
        {
            "baseline_commit": FRESHNESS_BASELINE_COMMIT,
            "baseline_resolved": baseline_resolved,
            "baseline_is_ancestor": baseline_is_ancestor,
            "active_source_deltas": active_source_deltas,
            "expected_hex_sha256": expected_hex,
            "expected_elf_sha256": expected_elf,
            "reused_baseline_build_identity": reused_baseline_build_identity,
            "stale_against_changed_sources": stale_against_changed_sources,
        },
    )

    build_logs = (
        lower_mr.get("build_logs") if isinstance(lower_mr, dict) else None
    )
    provenance_build = (
        lower_mr.get("builds")
        if is_provenance_mr(lower_mr)
        else None
    )
    provenance_log_paths = (
        provenance_build.get("logs")
        if isinstance(provenance_build, dict)
        else None
    )
    arm_build = (
        lower_mr.get("arm_build_evidence")
        if isinstance(lower_mr, dict)
        else None
    )
    main_physical = (
        lower_root
        / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
    )
    main_physical_sha = (
        file_sha(main_physical) if main_physical.is_file() else None
    )
    main_physical_mtime = (
        main_physical.stat().st_mtime_ns if main_physical.is_file() else None
    )
    build_freshness_rows: dict[str, Any] = {}
    build_freshness_ok = True
    build_logs_ok = True
    for mode, policy in BUILD_MODE_PATHS.items():
        build_dir = lower_root / policy["directory"]
        object_path = build_dir / "main.o"
        elf_path = build_dir / f"{policy['stem']}.elf"
        hex_path = build_dir / f"{policy['stem']}.hex"
        mode_evidence = (
            arm_build.get(mode) if isinstance(arm_build, dict) else None
        )
        declared_mode_elf = (
            normalize_hash(mode_evidence.get("elf_sha256"))
            if isinstance(mode_evidence, dict)
            else provenance.get(
                "bounded_elf" if mode == "bounded" else "live_elf",
                {},
            ).get("sha256")
        )
        declared_mode_hex = (
            normalize_hash(mode_evidence.get("hex_sha256"))
            if isinstance(mode_evidence, dict)
            else provenance.get(
                "bounded_hex" if mode == "bounded" else "live_hex",
                {},
            ).get("sha256")
        )
        log_descriptor = (
            build_logs.get(mode) if isinstance(build_logs, dict) else None
        )
        provenance_log_name = (
            "bounded_log" if mode == "bounded" else "live_log"
        )
        if log_descriptor is None and provenance_log_name in provenance:
            log_descriptor = provenance[provenance_log_name]
        if log_descriptor is None and isinstance(provenance_log_paths, list):
            mode_prefix = "bounded-" if mode == "bounded" else "live-"
            matching_logs = [
                value
                for value in provenance_log_paths
                if isinstance(value, str)
                and Path(value).name.startswith(mode_prefix)
            ]
            if matching_logs:
                selected_log = sorted(matching_logs)[-1]
                matching_binding = next(
                    (
                        item
                        for item in provenance.values()
                        if item["path"] == selected_log.replace("\\", "/")
                    ),
                    None,
                )
                log_descriptor = {
                    "path": selected_log,
                    "sha256": (
                        matching_binding.get("sha256")
                        if matching_binding
                        else None
                    ),
                }
        log_path_value = (
            log_descriptor.get("path")
            if isinstance(log_descriptor, dict)
            else None
        )
        log_path = (
            resolve_repo_path(lower_root, Path(log_path_value))
            if isinstance(log_path_value, str)
            else None
        )
        expected_log_path = (
            resolve_repo_path(lower_root, Path(log_path_value))
            if is_provenance_mr(lower_mr)
            and isinstance(log_path_value, str)
            else (
                lower_root / f".cache/comp472-arm-{mode}.log"
            ).resolve()
        )
        log_inside = False
        if log_path is not None:
            try:
                log_path.relative_to(lower_root)
                log_inside = True
            except ValueError:
                pass
        log_text = (
            log_path.read_text(encoding="utf-8", errors="replace")
            if log_inside and log_path.is_file()
            else ""
        )
        compile_marker = (
            f'-c "Core/Src/main.c" -o '
            f'"{Path(policy["directory"]).name}/main.o"'
        )
        link_marker = f'-o "{Path(policy["directory"]).name}/{policy["stem"]}.elf"'
        hex_marker = (
            f'"{Path(policy["directory"]).name}/{policy["stem"]}.elf" '
            f'"{Path(policy["directory"]).name}/{policy["stem"]}.hex"'
        )
        compile_index = log_text.find(compile_marker)
        link_index = log_text.find(link_marker)
        hex_index = log_text.find(hex_marker)
        forbidden_define_absent = bool(
            not policy["forbidden_define"]
            or policy["forbidden_define"] not in (
                log_text[compile_index:link_index]
                if 0 <= compile_index < link_index
                else ""
            )
        )
        paths = {
            "main_object": object_path,
            "elf": elf_path,
            "hex": hex_path,
        }
        physical = {
            name: {
                "path": path.as_posix(),
                "exists": path.is_file(),
                "sha256": file_sha(path) if path.is_file() else None,
                "mtime_ns": path.stat().st_mtime_ns if path.is_file() else None,
            }
            for name, path in paths.items()
        }
        object_mtime = physical["main_object"]["mtime_ns"]
        elf_mtime = physical["elf"]["mtime_ns"]
        hex_mtime = physical["hex"]["mtime_ns"]
        log_mtime = (
            log_path.stat().st_mtime_ns
            if log_path is not None and log_path.is_file()
            else None
        )
        source_object_output_order = bool(
            main_physical_mtime is not None
            and object_mtime is not None
            and elf_mtime is not None
            and hex_mtime is not None
            and log_mtime is not None
            and main_physical_mtime <= object_mtime <= elf_mtime <= hex_mtime
            and hex_mtime <= log_mtime
        )
        mode_hashes_match = bool(
            physical["elf"]["sha256"] == declared_mode_elf
            and physical["hex"]["sha256"] == declared_mode_hex
            and declared_mode_elf in expected_elf
            and declared_mode_hex in expected_hex
        )
        declared_log_sha = (
            normalize_hash(log_descriptor.get("sha256"))
            if isinstance(log_descriptor, dict)
            else None
        )
        log_hash_matches = bool(
            log_path is not None
            and log_path.is_file()
            and file_sha(log_path) == declared_log_sha
        )
        log_complete = bool(
            log_path == expected_log_path
            and log_inside
            and log_hash_matches
            and 0 <= compile_index < link_index < hex_index
            and policy["required_define"]
            in log_text[compile_index:link_index]
            and forbidden_define_absent
            and "make: Leaving directory" in log_text[hex_index:]
        )
        row_ok = bool(
            all(item["exists"] for item in physical.values())
            and mode_hashes_match
            and source_object_output_order
            and log_complete
        )
        build_freshness_ok = build_freshness_ok and row_ok
        build_logs_ok = build_logs_ok and log_complete
        build_freshness_rows[mode] = {
            "source": {
                "path": main_physical.as_posix(),
                "sha256": main_physical_sha,
                "mtime_ns": main_physical_mtime,
                "matches_commit_binding": (
                    main_physical_sha
                    == bindings.get(
                        "cubeide/Companion_Nucleo_WB55RG_Bringup/"
                        "Core/Src/main.c"
                    )
                ),
            },
            "physical": physical,
            "declared": {
                "elf_sha256": declared_mode_elf,
                "hex_sha256": declared_mode_hex,
            },
            "build_log": {
                "path": log_path.as_posix() if log_path else None,
                "expected_path": expected_log_path.as_posix(),
                "declared_sha256": declared_log_sha,
                "observed_sha256": (
                    file_sha(log_path)
                    if log_path is not None and log_path.is_file()
                    else None
                ),
                "mtime_ns": log_mtime,
                "hash_matches": log_hash_matches,
                "compile_index": compile_index,
                "link_index": link_index,
                "hex_index": hex_index,
                "required_define_present": (
                    policy["required_define"]
                    in (
                        log_text[compile_index:link_index]
                        if 0 <= compile_index < link_index
                        else ""
                    )
                ),
                "forbidden_define_absent": forbidden_define_absent,
                "complete": log_complete,
            },
            "source_object_output_log_order": source_object_output_order,
            "physical_hashes_match_claim": mode_hashes_match,
            "pass": row_ok,
        }
    append_check(
        checks,
        observations,
        "lower_mr.build_logs_rehashed_and_complete",
        build_logs_ok,
        build_freshness_rows,
    )
    append_check(
        checks,
        observations,
        "lower.build_outputs_fresh_and_rehashed",
        build_freshness_ok,
        build_freshness_rows,
    )

    runner_descriptor = declared_tool_descriptor(lower_mr, "runner", bindings)
    supervisor_descriptor = declared_tool_descriptor(
        lower_mr, "supervisor", bindings
    )

    def verify_tool(
        descriptor: dict[str, str] | None, expected: str | None
    ) -> tuple[bool, dict[str, Any]]:
        if descriptor is None or not descriptor.get("path"):
            return False, {
                "descriptor": descriptor,
                "expected_sha256": expected,
                "observed_sha256": None,
            }
        path = resolve_repo_path(lower_root, Path(descriptor["path"]))
        inside = True
        try:
            path.relative_to(lower_root)
        except ValueError:
            inside = False
        observed = file_sha(path) if inside and path.is_file() else None
        declared = descriptor["sha256"]
        return (
            bool(observed and observed == declared == expected),
            {
                "path": path.as_posix(),
                "inside_lower_root": inside,
                "declared_sha256": declared,
                "expected_sha256": expected,
                "observed_sha256": observed,
            },
        )

    runner_pass, runner_row = verify_tool(
        runner_descriptor, expected_hash_args["lower_runner"]
    )
    supervisor_pass, supervisor_row = verify_tool(
        supervisor_descriptor, expected_hash_args["lower_supervisor"]
    )
    append_check(
        checks,
        observations,
        "lower_mr.runner_rehashed",
        runner_pass,
        runner_row,
    )
    append_check(
        checks,
        observations,
        "lower_mr.supervisor_rehashed",
        supervisor_pass,
        supervisor_row,
    )

    timing = lower_mr.get("timing") if isinstance(lower_mr, dict) else None
    timing_values = (
        {
            "transaction_ms": timing.get("transaction_ms"),
            "cadence_ms": timing.get("cadence_ms"),
            "busy_ms": timing.get("busy_ms"),
        }
        if isinstance(timing, dict)
        else {}
    )
    append_check(
        checks,
        observations,
        "lower_mr.timing_within_limits",
        bool(
            (
                len(timing_values) == 3
                and all(
                    isinstance(value, (int, float))
                    for value in timing_values.values()
                )
                and timing_values["transaction_ms"] <= 480
                and timing_values["cadence_ms"] <= 480
                and timing_values["busy_ms"] <= 600
                and timing.get("within_limits") is True
            )
            or (
                is_provenance_mr(lower_mr)
                and isinstance(lower_mr.get("bounds"), dict)
                and lower_mr["bounds"].get("transaction_max_ms") == 480
                and lower_mr["bounds"].get("cadence") == "1..480"
                and lower_mr["bounds"].get("busy_max_ms") == 600
                and lower_mr["bounds"].get("retry") == 0
                and lower_mr["bounds"].get("physical_timing")
                == "unproven"
            )
        ),
        {
            "measured": timing_values,
            "fixed_bounds": (
                lower_mr.get("bounds")
                if isinstance(lower_mr, dict)
                else None
            ),
        },
    )

    mode_and_fault = (
        lower_mr.get("mode_and_fault_evidence")
        if isinstance(lower_mr, dict)
        else None
    )
    mode_flag_values = {
        name: mode_and_fault.get(name)
        if isinstance(mode_and_fault, dict)
        else None
        for name in sorted(COMP_REQ_478_MODE_FLAGS)
    }
    append_check(
        checks,
        observations,
        "lower_mr.comp_req_478_mode_fault_claims",
        bool(
            is_provenance_mr(lower_mr)
            or all(value is True for value in mode_flag_values.values())
        ),
        mode_flag_values,
    )

    arm_evidence = (
        lower_mr.get("arm_build_evidence")
        if isinstance(lower_mr, dict)
        else None
    )
    provenance_modes = (
        lower_mr.get("modes")
        if is_provenance_mr(lower_mr)
        and isinstance(lower_mr.get("modes"), dict)
        else None
    )
    mode_values = {}
    for name in ("bounded", "continuous"):
        row = arm_evidence.get(name) if isinstance(arm_evidence, dict) else None
        provenance_mode_key = (
            "bounded_mode" if name == "bounded" else "live_mode"
        )
        provenance_mode = (
            provenance_modes.get(
                "bounded" if name == "bounded" else "live"
            )
            if isinstance(provenance_modes, dict)
            else provenance_build.get(provenance_mode_key)
            if isinstance(provenance_build, dict)
            else None
        )
        provenance_mode_build = (
            provenance_build.get(
                "bounded" if name == "bounded" else "live"
            )
            if isinstance(provenance_build, dict)
            else None
        )
        mode_values[name] = {
            "proven": (
                row.get("visual_runtime_mode_proven")
                if isinstance(row, dict)
                else bool(
                    (
                        isinstance(provenance_build, dict)
                        and provenance_build.get("optimization") == "O2"
                        and provenance_build.get("all_byte_identical") is True
                        and provenance_build.get(
                            "bounded_force_runs"
                            if name == "bounded"
                            else "live_force_runs"
                        )
                        == 2
                    )
                    or (
                        isinstance(provenance_mode_build, dict)
                        and provenance_mode_build.get("optimization") == "O2"
                        and provenance_mode_build.get("fresh") is True
                        and provenance_mode_build.get("runs") == 2
                    )
                )
            ),
            "value": (
                row.get("visual_runtime_mode_value")
                if isinstance(row, dict)
                else provenance_mode
            ),
        }
    append_check(
        checks,
        observations,
        "lower_mr.arm_modes_exact_0_1",
        bool(
            mode_values["bounded"]["proven"] is True
            and mode_values["bounded"]["value"] == 0
            and mode_values["continuous"]["proven"] is True
            and mode_values["continuous"]["value"] == 1
        ),
        mode_values,
    )

    fixture = (
        lower_mr.get("fixture") if isinstance(lower_mr, dict) else None
    )
    fixture_stdout = (
        fixture.get("stdout") if isinstance(fixture, dict) else None
    )
    fixture_checkonly = (
        fixture.get("checkonly") if isinstance(fixture, dict) else None
    )
    fixture_tokens_478 = {
        token: bool(
            isinstance(fixture_stdout, str) and token in fixture_stdout
        )
        for token in sorted(COMP_REQ_478_FIXTURE_TOKENS)
    }
    fixture_tokens_484 = {
        token: bool(
            isinstance(fixture_stdout, str) and token in fixture_stdout
        )
        for token in sorted(COMP_REQ_484_FIXTURE_TOKENS)
    }
    append_check(
        checks,
        observations,
        "lower_mr.comp_req_478_fixture_contract",
        bool(
            is_provenance_mr(lower_mr)
            or (
                isinstance(fixture, dict)
                and fixture.get("status") == "PASS"
                and isinstance(fixture_checkonly, dict)
                and fixture_checkonly.get("retry") == 0
                and all(fixture_tokens_478.values())
            )
        ),
        {
            "tokens": fixture_tokens_478,
            "retry": fixture_checkonly.get("retry")
            if isinstance(fixture_checkonly, dict)
            else None,
        },
    )
    append_check(
        checks,
        observations,
        "lower_mr.comp_req_484_fixture_contract",
        bool(
            is_provenance_mr(lower_mr)
            or (
                isinstance(fixture, dict)
                and fixture.get("status") == "PASS"
                and isinstance(fixture_checkonly, dict)
                and fixture_checkonly.get("retry") == 0
                and all(fixture_tokens_484.values())
            )
        ),
        {
            "tokens": fixture_tokens_484,
            "retry": fixture_checkonly.get("retry")
            if isinstance(fixture_checkonly, dict)
            else None,
        },
    )
    negative_486 = (
        lower_mr.get("negative_fixtures")
        if isinstance(lower_mr, dict)
        else None
    )
    required_486 = {
        "unsupported_transition_build_window": "pass",
        "invalid_current_state": "pass",
        "build_failure_first_fail": "pass",
        "terminal_latched": "pass",
        "retained_event": "pass",
        "second_service_no_lookup_build_transport": "pass",
        "failed_events_unchanged": "pass",
        "activation_unchanged": "pass",
        "ring_unchanged": "pass",
        "retry": "0",
        "zero_commands": "pass",
    }
    observed_486 = {
        key: negative_486.get(key)
        if isinstance(negative_486, dict)
        else None
        for key in sorted(required_486)
    }
    append_check(
        checks,
        observations,
        "lower_mr.comp_req_486_negative_contract",
        bool(
            not (
                isinstance(lower_mr, dict)
                and lower_mr.get("requirement_id") == "COMP-REQ-486"
            )
            or observed_486 == required_486
        ),
        observed_486,
    )
    tamper_488 = (
        lower_mr.get("tamper_negatives")
        if isinstance(lower_mr, dict)
        else None
    )
    required_tamper_488 = {
        "busy_601",
        "cadence_0",
        "cadence_481",
        "driver_physical",
        "forged_physical_timing",
        "hardware_contact_1",
        "header_blob",
        "missing_hex",
        "retry_1",
        "superseded_sha",
        "transaction_481",
        "wrong_artifact_path",
    }
    append_check(
        checks,
        observations,
        "lower_mr.comp_req_488_tamper_claims_complete",
        bool(
            not (
                isinstance(lower_mr, dict)
                and lower_mr.get("requirement_id") == "COMP-REQ-488"
            )
            or (
                isinstance(tamper_488, dict)
                and required_tamper_488.issubset(tamper_488)
                and all(
                    tamper_488.get(key) is True
                    for key in required_tamper_488
                )
            )
        ),
        {
            "required": sorted(required_tamper_488),
            "observed": tamper_488,
            "authoritative": False,
        },
    )
    provenance_contract = (
        lower_mr.get("contract") if isinstance(lower_mr, dict) else None
    )
    provenance_checkonly = (
        provenance_contract.get("checkonly")
        if isinstance(provenance_contract, dict)
        else lower_mr.get("checkonly")
        if isinstance(lower_mr, dict)
        and isinstance(lower_mr.get("checkonly"), dict)
        else None
    )
    append_check(
        checks,
        observations,
        "lower_mr.checkonly_zero",
        bool(
            not is_provenance_mr(lower_mr)
            or (
                isinstance(provenance_checkonly, dict)
                and provenance_checkonly
                and all(value == 0 for value in provenance_checkonly.values())
            )
        ),
        provenance_checkonly,
    )
    provenance_bounds = (
        lower_mr.get("bounds")
        if isinstance(lower_mr, dict)
        and isinstance(lower_mr.get("bounds"), dict)
        else None
    )
    fixed_contract_observed = {
        "states": (
            provenance_contract.get("states")
            if isinstance(provenance_contract, dict)
            else None
        ),
        "transition_rows": (
            provenance_contract.get("transition_rows")
            if isinstance(provenance_contract, dict)
            else None
        ),
        "expanded_pairs": (
            provenance_contract.get("expanded_pairs")
            if isinstance(provenance_contract, dict)
            else None
        ),
        "pixel_noops": (
            provenance_contract.get("pixel_noops")
            if isinstance(provenance_contract, dict)
            else None
        ),
        "polarity": (
            provenance_contract.get("polarity")
            if isinstance(provenance_contract, dict)
            else None
        ),
        "baseline_panel": (
            provenance_contract.get("baseline_panel")
            if isinstance(provenance_contract, dict)
            else None
        ),
        "cleanup": (
            provenance_contract.get("cleanup")
            if isinstance(provenance_contract, dict)
            else None
        ),
        "transaction_max_ms": (
            provenance_contract.get("transaction_max_ms")
            if isinstance(provenance_contract, dict)
            else provenance_bounds.get("transaction_max_ms")
            if isinstance(provenance_bounds, dict)
            else None
        ),
        "cadence": (
            provenance_contract.get("cadence")
            if isinstance(provenance_contract, dict)
            else provenance_bounds.get("cadence")
            if isinstance(provenance_bounds, dict)
            else None
        ),
        "busy_max_ms": (
            provenance_contract.get("busy_max_ms")
            if isinstance(provenance_contract, dict)
            else provenance_bounds.get("busy_max_ms")
            if isinstance(provenance_bounds, dict)
            else None
        ),
        "physical_timing": (
            provenance_contract.get("physical_timing")
            if isinstance(provenance_contract, dict)
            else provenance_bounds.get("physical_timing")
            if isinstance(provenance_bounds, dict)
            else None
        ),
        "retry": (
            provenance_bounds.get("retry")
            if isinstance(provenance_bounds, dict)
            else provenance_checkonly.get("retry")
            if isinstance(provenance_checkonly, dict)
            else None
        ),
    }
    fixed_contract_expected = {
        "states": 17,
        "transition_rows": 21,
        "expanded_pairs": 59,
        "pixel_noops": 10,
        "polarity": "logical_black1_panel_white1",
        "baseline_panel": EXPECTED_CONVERTED_CENTERED_SHA256,
        "cleanup": "single_flash_white",
        "transaction_max_ms": 480,
        "cadence": "1..480",
        "busy_max_ms": 600,
        "physical_timing": "unproven",
        "retry": 0,
    }
    fixed_contract_fields = (
        {
            key: fixed_contract_observed[key]
            for key in (
                "transaction_max_ms",
                "cadence",
                "busy_max_ms",
                "physical_timing",
                "retry",
            )
        }
        if isinstance(lower_mr, dict)
        and lower_mr.get("requirement_id") == "COMP-REQ-488"
        else fixed_contract_observed
    )
    fixed_contract_comparison = (
        {
            key: fixed_contract_expected[key]
            for key in fixed_contract_fields
        }
    )
    append_check(
        checks,
        observations,
        "lower_mr.provenance_contract_fixed_values",
        bool(
            not is_provenance_mr(lower_mr)
            or fixed_contract_fields == fixed_contract_comparison
        ),
        {
            "expected": fixed_contract_comparison,
            "observed": fixed_contract_fields,
        },
    )

    protected_rows = {}
    protected_ok = True
    protected_declared = (
        lower_mr.get("protected_git_blobs")
        if isinstance(lower_mr, dict)
        else None
    )
    protected_observed = (
        lower_mr.get("protected_observed")
        if isinstance(lower_mr, dict)
        else None
    )
    provenance_protected = (
        lower_mr.get("protected")
        if is_provenance_mr(lower_mr)
        and isinstance(lower_mr.get("protected"), dict)
        else lower_mr.get("protected_hashes")
        if is_provenance_mr(lower_mr)
        and isinstance(lower_mr.get("protected_hashes"), dict)
        else None
    )
    if isinstance(provenance_protected, dict):
        protected_declared = {
            "panel_driver": provenance_protected.get(
                "panel_driver_blob",
                provenance_protected.get(
                    "panel_driver_git_blob",
                    provenance_protected.get("driver_blob"),
                ),
            ),
            "r7_header": provenance_protected.get(
                "r7_header_blob",
                provenance_protected.get(
                    "r7_header_git_blob",
                    provenance_protected.get("header_blob"),
                ),
            ),
        }
        protected_observed = {
            "git_blobs": dict(protected_declared),
            "physical_sha256": {
                "panel_driver": provenance_protected.get(
                    "panel_driver",
                    provenance_protected.get(
                        "panel_driver_physical",
                        provenance_protected.get("driver_physical"),
                    ),
                ),
                "r7_header": provenance_protected.get(
                    "r7_header",
                    provenance_protected.get(
                        "r7_header_physical",
                        provenance_protected.get("header_physical"),
                    ),
                ),
            },
        }
    for name, policy in PROTECTED_GIT_OBJECTS.items():
        data = b""
        object_id = None
        if resolved_commit:
            try:
                data = git_read(
                    lower_root, "show", f"{resolved_commit}:{policy['path']}"
                )
                object_id = (
                    git_read(
                        lower_root,
                        "rev-parse",
                        f"{resolved_commit}:{policy['path']}",
                    )
                    .decode("ascii")
                    .strip()
                )
            except Exception:
                pass
        declared_object = (
            protected_declared.get(name)
            if isinstance(protected_declared, dict)
            else None
        )
        observed_object = (
            protected_observed.get("git_blobs", {}).get(name)
            if isinstance(protected_observed, dict)
            and isinstance(protected_observed.get("git_blobs"), dict)
            else None
        )
        declared_physical = (
            protected_observed.get("physical_sha256", {}).get(name)
            if isinstance(protected_observed, dict)
            and isinstance(protected_observed.get("physical_sha256"), dict)
            else None
        )
        physical_path = (lower_root / policy["path"]).resolve()
        physical_sha = file_sha(physical_path) if physical_path.is_file() else None
        clean_check = (
            subprocess.run(
                [
                    "git",
                    "diff",
                    "--quiet",
                    resolved_commit,
                    "--",
                    policy["path"],
                ],
                cwd=lower_root,
                check=False,
                capture_output=True,
            )
            if resolved_commit
            else None
        )
        row_ok = bool(
            object_id
            and object_id == policy["git_blob"]
            and git_object_sha1("blob", data) == object_id
            and declared_object == object_id
            and observed_object == object_id
            and normalize_hash(declared_physical) == physical_sha
            and clean_check is not None
            and clean_check.returncode == 0
        )
        protected_rows[name] = {
            "path": policy["path"],
            "expected_git_blob": policy["git_blob"],
            "observed_git_blob": object_id,
            "declared_git_blob": declared_object,
            "declared_observed_git_blob": observed_object,
            "declared_physical_sha256": normalize_hash(declared_physical),
            "physical_sha256": physical_sha,
            "commit_blob_sha256": sha256(data) if data else None,
            "worktree_clean_against_commit": bool(
                clean_check is not None and clean_check.returncode == 0
            ),
            "pass": row_ok,
        }
        protected_ok = protected_ok and row_ok
    append_check(
        checks,
        observations,
        "lower_mr.protected_hashes_exact",
        protected_ok,
        protected_rows,
    )

    claims = lower_compatibility_claims(lower_mr)
    append_check(
        checks,
        observations,
        "lower_mr.compatibility_claims_complete",
        bool(
            is_provenance_mr(lower_mr)
            or (
                claims.get("events_realizable") == 21
                and claims.get("pairs_realizable") == 59
                and claims.get("semantic_noops_realizable") == 10
                and claims.get("polarity_bridge") is True
                and claims.get("terminal_retention") is True
                and claims.get("qualification_valid") is True
                and claims.get("converted_centered_sha256")
                == EXPECTED_CONVERTED_CENTERED_SHA256
            )
        ),
        claims,
    )

    lower_side = lower_side_effects(lower_mr)
    missing_side_keys = sorted(REQUIRED_SIDE_EFFECT_KEYS.difference(lower_side))
    nonzero_side = {
        key: value
        for key, value in lower_side.items()
        if key in REQUIRED_SIDE_EFFECT_KEYS and value != 0
    }
    append_check(
        checks,
        observations,
        "lower_mr.side_effect_contract_complete",
        bool(
            not missing_side_keys
            or (
                is_provenance_mr(lower_mr)
                and {
                    "hardware_contact",
                    "popup",
                    "programmer",
                    "refresh",
                    "reset",
                    "retry",
                    "serial",
                    "write",
                }.issubset(lower_side)
            )
        ),
        {"missing_legacy_keys": missing_side_keys},
    )
    append_check(
        checks,
        observations,
        "lower_mr.side_effects_zero",
        bool(
            not nonzero_side
            and (
                all(
                    lower_side.get(key) == 0
                    for key in REQUIRED_SIDE_EFFECT_KEYS
                )
                or (
                    is_provenance_mr(lower_mr)
                    and lower_side
                    and all(value == 0 for value in lower_side.values())
                )
            )
        ),
        {"nonzero": nonzero_side, "observed": lower_side},
    )

    foundational = all(
        checks.get(name, False)
        for name in (
            "input.upper_path_exact",
            "input.oracle_path_exact",
            "upper.hash_exact",
            "oracle.hash_exact",
            "auditor.file_exists",
            "auditor.hash_exact",
            "lower.root_is_exact_toplevel",
            "lower.commit_exact",
            "lower.commit_object_recomputed",
        )
    )
    compatibility_process: dict[str, Any] = {
        "invoked": False,
        "return_code": None,
        "stdout": "",
        "stderr": "",
    }
    compatibility: dict[str, Any] | None = None
    compatibility_sha = None
    if foundational:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(auditor_path),
                "--comparison-mode",
                "--repo-root",
                str(repo_root),
                "--lower-root",
                str(lower_root),
                "--expected-commit",
                args.expected_commit,
                "--output",
                str(compatibility_output_path),
            ],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        compatibility_process = {
            "invoked": True,
            "return_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        if compatibility_output_path.is_file():
            compatibility = load_json(compatibility_output_path)
            compatibility_sha = file_sha(compatibility_output_path)

    append_check(
        checks,
        observations,
        "compatibility.invoked",
        compatibility_process["invoked"],
    )
    append_check(
        checks,
        observations,
        "compatibility.artifact_parsed",
        compatibility is not None,
        compatibility_sha,
    )
    compatibility_summary = (
        compatibility.get("summary") if isinstance(compatibility, dict) else None
    )
    compatibility_generator = (
        compatibility.get("generator")
        if isinstance(compatibility, dict)
        else None
    )
    compatibility_side = (
        compatibility.get("side_effect_counters")
        if isinstance(compatibility, dict)
        else None
    )
    compatibility_nonzero_side = {
        key: compatibility_side.get(key)
        for key in COMPATIBILITY_SIDE_EFFECT_KEYS
        if isinstance(compatibility_side, dict)
        and compatibility_side.get(key) != 0
    }
    append_check(
        checks,
        observations,
        "compatibility.subprocess_consistent",
        bool(
            compatibility
            and (
                (
                    compatibility_process["return_code"] == 0
                    and compatibility.get("status")
                    == "PASS_UPPER_LOWER_COMPATIBLE"
                )
                or (
                    compatibility_process["return_code"] == 1
                    and str(compatibility.get("status", "")).startswith("NO_GO")
                )
            )
            and compatibility_generator.get("sha256")
            == expected_hash_args["compatibility_auditor"]
            and compatibility.get("lower_binding", {}).get("resolved_commit")
            == args.expected_commit
            and compatibility.get("mode") == "comparison"
        ),
        compatibility_process,
    )
    append_check(
        checks,
        observations,
        "compatibility.full_21_59_10",
        bool(
            compatibility
            and compatibility.get("status") == "PASS_UPPER_LOWER_COMPATIBLE"
            and compatibility_summary.get("events", {}).get("realizable") == 21
            and compatibility_summary.get("pairs", {}).get("realizable") == 59
            and compatibility_summary.get("pairs", {}).get(
                "semantic_noop_realizable"
            )
            == 10
            and compatibility_summary.get("comparison_complete") is True
        ),
        compatibility_summary,
    )
    append_check(
        checks,
        observations,
        "compatibility.polarity_terminal_qualification",
        bool(
            compatibility_summary
            and compatibility_summary.get("polarity_bridge_realizable") is True
            and compatibility_summary.get("terminal_retention") is True
            and compatibility_summary.get("qualification_valid") is True
            and compatibility.get("polarity_contract", {}).get(
                "observed_converted_centered_sha256"
            )
            == EXPECTED_CONVERTED_CENTERED_SHA256
        ),
    )
    append_check(
        checks,
        observations,
        "compatibility.side_effects_zero",
        bool(
            isinstance(compatibility_side, dict)
            and not compatibility_nonzero_side
            and all(
                compatibility_side.get(key) == 0
                for key in COMPATIBILITY_SIDE_EFFECT_KEYS
            )
        ),
        compatibility_nonzero_side,
    )
    append_check(
        checks,
        observations,
        "lower_claims_match_observed_compatibility",
        bool(
            (
                is_provenance_mr(lower_mr)
                and compatibility_summary is not None
            )
            or (
                claims
                and compatibility_summary
                and claims.get("events_realizable")
                == compatibility_summary.get("events", {}).get("realizable")
                and claims.get("pairs_realizable")
                == compatibility_summary.get("pairs", {}).get("realizable")
                and claims.get("semantic_noops_realizable")
                == compatibility_summary.get("pairs", {}).get(
                    "semantic_noop_realizable"
                )
                and claims.get("polarity_bridge")
                == compatibility_summary.get("polarity_bridge_realizable")
                and claims.get("terminal_retention")
                == compatibility_summary.get("terminal_retention")
                and claims.get("qualification_valid")
                == compatibility_summary.get("qualification_valid")
            )
        ),
    )

    failed_checks = sorted(name for name, passed in checks.items() if not passed)
    status = "JOINT_READY" if not failed_checks else "NO_GO"
    artifact = {
        "schema": "companion.joint-upper-lower-offline-gate.v1",
        "requirements": [
            "COMP-REQ-479",
            "COMP-REQ-480",
            "COMP-REQ-484",
            "COMP-REQ-486",
            "COMP-REQ-488",
        ],
        "status": status,
        "default_off": True,
        "scope": "upper_owned_read_only_joint_gate",
        "inputs": {
            "upper_machine_ready": {
                "path": upper_path.as_posix(),
                "expected_sha256": expected_hash_args["upper_machine_ready"],
                "observed_sha256": upper_observed_sha,
            },
            "expanded_oracle": {
                "path": oracle_path.as_posix(),
                "expected_sha256": expected_hash_args["expanded_oracle"],
                "observed_sha256": oracle_observed_sha,
            },
            "compatibility_auditor": {
                "path": auditor_path.as_posix(),
                "expected_sha256": expected_hash_args[
                    "compatibility_auditor"
                ],
                "observed_sha256": auditor_observed_sha,
            },
            "lower": {
                "root": lower_root.as_posix(),
                "expected_commit": args.expected_commit,
                "resolved_commit": resolved_commit,
                "machine_ready_path": lower_mr_path.as_posix(),
                "expected_machine_ready_sha256": expected_hash_args[
                    "lower_machine_ready"
                ],
                "observed_machine_ready_sha256": lower_mr_observed_sha,
                "expected_hex_sha256": expected_hex,
                "expected_elf_sha256": expected_elf,
                "expected_runner_sha256": expected_hash_args["lower_runner"],
                "expected_supervisor_sha256": expected_hash_args[
                    "lower_supervisor"
                ],
            },
        },
        "lower_machine_ready_contract": {
            "schema": LOWER_SCHEMA,
            "status": LOWER_STATUS,
            "required_source_paths": sorted(REQUIRED_LOWER_SOURCE_PATHS),
            "artifact_descriptors": (
                "artifacts.hex[]/elf[]/runner/supervisor require path+sha256"
            ),
            "timing_limits_ms": {
                "transaction": 480,
                "cadence": 480,
                "busy": 600,
            },
            "comp_req_478": {
                "mode_values": {"bounded": 0, "continuous": 1},
                "mode_and_fault_flags": sorted(COMP_REQ_478_MODE_FLAGS),
                "fixture_tokens": sorted(COMP_REQ_478_FIXTURE_TOKENS),
                "source_contract_required": True,
            },
            "comp_req_484": {
                "fixture_tokens": sorted(COMP_REQ_484_FIXTURE_TOKENS),
                "source_contract_required": True,
                "active_build_source_paths": sorted(
                    ACTIVE_BUILD_SOURCE_PATHS
                ),
                "freshness_baseline_commit": FRESHNESS_BASELINE_COMMIT,
                "source_object_elf_hex_log_order_required": True,
            },
            "comp_req_486_488": {
                "pretransport_failure_terminal_latch_required": True,
                "provenance_contract_fixed_values": (
                    fixed_contract_expected
                ),
                "protected_hashes_recomputed_from_commit_and_worktree": True,
                "candidate_self_report_is_not_authoritative": True,
            },
            "compatibility_counts": {
                "events": 21,
                "pairs": 59,
                "semantic_noops": 10,
            },
            "required_side_effect_keys": sorted(REQUIRED_SIDE_EFFECT_KEYS),
        },
        "checks": checks,
        "observations": observations,
        "compatibility": {
            "artifact_path": compatibility_output_path.as_posix(),
            "artifact_sha256": compatibility_sha,
            "process": compatibility_process,
            "status": compatibility.get("status") if compatibility else None,
            "summary": compatibility_summary,
        },
        "failed_checks": failed_checks,
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
            "read_only_compatibility_subprocess": (
                1 if compatibility_process["invoked"] else 0
            ),
            "upper_evidence_write": 2
            if compatibility_process["invoked"]
            else 1,
        },
        "generator": {
            "path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "sha256": file_sha(Path(__file__).resolve()),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(artifact))
    print(
        json.dumps(
            {
                "status": status,
                "failed_check_count": len(failed_checks),
                "compatibility_status": artifact["compatibility"]["status"],
                "artifact_sha256": file_sha(output_path),
            },
            sort_keys=True,
        )
    )
    return 0 if status == "JOINT_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
