#!/usr/bin/env python3
"""Independently verify the generated COMP-REQ-471 C asset pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


EXPECTED_STATE_COUNT = 17
EXPECTED_WIDTH = 200
EXPECTED_HEIGHT = 200
EXPECTED_STRIDE = 25
EXPECTED_FRAME_BYTES = 5000
PAYLOAD_BUDGET = 85000
ENABLE_MACRO = "COMPANION_VISUAL_ASSET_PACK_ENABLE"
GENERATED_FILES = (
    "companion_visual_asset_pack.h",
    "companion_visual_asset_pack.c",
    "c-asset-pack-manifest.json",
    "c-asset-pack-handoff.json",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def c_token(value: str) -> str:
    operator_tokens = (
        (">=", "_GE_"),
        ("<=", "_LE_"),
        ("!=", "_NE_"),
        ("==", "_EQ_"),
        (">", "_GT_"),
        ("<", "_LT_"),
    )
    expanded = value
    for operator, replacement in operator_tokens:
        expanded = expanded.replace(operator, replacement)
    token = re.sub(r"[^A-Za-z0-9]+", "_", expanded).strip("_").upper()
    if not token or token[0].isdigit():
        raise ValueError(f"cannot form C token from {value!r}")
    return token


def parse_block(text: str, declaration: str) -> str:
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


def transition_states(item: dict[str, Any], key: str) -> list[str]:
    if key in item:
        return [item[key]]
    any_key = f"{key}_any"
    if any_key in item:
        return list(item[any_key])
    raise ValueError(f"transition lacks {key}/{any_key}: {item}")


def expected_mask(states: list[str], state_index: dict[str, int]) -> int:
    result = 0
    for state in states:
        if state not in state_index:
            raise ValueError(f"transition references unknown state: {state}")
        result |= 1 << state_index[state]
    return result


def compiler_run(
    compiler: Path,
    source: Path,
    include_dir: Path,
    output: Path,
    enabled: bool,
) -> dict[str, Any]:
    command = [
        str(compiler),
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-ffreestanding",
        "-fno-common",
    ]
    if enabled:
        command.append(f"-D{ENABLE_MACRO}=1")
    command.extend(
        [
            "-I",
            str(include_dir),
            "-c",
            str(source),
            "-o",
            str(output),
        ]
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "mode": "enabled" if enabled else "default_off",
        "command": command,
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "object_file": str(output),
        "object_sha256": file_sha(output) if completed.returncode == 0 and output.exists() else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", required=True, type=Path)
    parser.add_argument("--rerun-pack-dir", required=True, type=Path)
    parser.add_argument("--compiler", required=True, type=Path)
    parser.add_argument("--object-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    pack_dir = args.pack_dir.resolve()
    rerun_dir = args.rerun_pack_dir.resolve()
    compiler = args.compiler.resolve()
    object_dir = args.object_dir.resolve()
    output_path = args.output.resolve()
    object_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = pack_dir / "c-asset-pack-manifest.json"
    contract_path = pack_dir / "visual-contract.json"
    transitions_path = pack_dir / "state-transitions.json"
    header_path = pack_dir / "companion_visual_asset_pack.h"
    source_path = pack_dir / "companion_visual_asset_pack.c"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    transition_source = json.loads(transitions_path.read_text(encoding="utf-8"))
    header = header_path.read_text(encoding="ascii")
    source = source_path.read_text(encoding="ascii")

    checks: dict[str, bool] = {}
    errors: list[str] = []

    def check(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(f"{name}: {detail}")

    source_hashes = manifest["source"]
    check(
        "source_visual_contract_sha",
        source_hashes["visual_contract_sha256"] == file_sha(contract_path),
        "visual-contract.json differs from generator input identity",
    )
    check(
        "source_transition_sha",
        source_hashes["state_transitions_sha256"] == file_sha(transitions_path),
        "state-transitions.json differs from generator input identity",
    )

    states = manifest["states"]
    state_ids = [item["id"] for item in states]
    state_index = {state_id: index for index, state_id in enumerate(state_ids)}
    contract_states = contract["frames"]
    contract_ids = [item["id"] for item in contract_states]
    check(
        "state_count",
        len(states) == EXPECTED_STATE_COUNT
        and manifest["capacity"]["state_count"] == EXPECTED_STATE_COUNT,
        "state count is not fixed at 17",
    )
    check(
        "state_identity_unique",
        len(set(state_ids)) == EXPECTED_STATE_COUNT and state_ids == contract_ids,
        "state identity or source ordering was lost",
    )

    state_enum_match = re.search(
        r"typedef enum \{\s*(.*?)\s*\} companion_visual_state_t;",
        header,
        re.DOTALL,
    )
    if not state_enum_match:
        raise ValueError("cannot parse companion_visual_state_t")
    parsed_state_enums = [
        (name, int(index))
        for name, index in re.findall(
            r"\b(COMPANION_VISUAL_STATE_[A-Z0-9_]+)\s*=\s*(\d+),",
            state_enum_match.group(1),
        )
    ]
    expected_state_enums = [(item["c_enum"], item["index"]) for item in states]
    check(
        "state_enum_identity",
        parsed_state_enums == expected_state_enums,
        "C state enum does not preserve all 17 ordered state identities",
    )

    macro_values = {
        name: int(value)
        for name, value in re.findall(
            r"^#define\s+(COMPANION_VISUAL_(?:WIDTH|HEIGHT|STRIDE_BYTES|FRAME_BYTES|"
            r"STATE_COUNT|UNIQUE_FRAME_COUNT|PAYLOAD_BYTES|TRANSITION_COUNT))\s+(\d+)u$",
            header,
            re.MULTILINE,
        )
    }
    expected_macros = {
        "COMPANION_VISUAL_WIDTH": EXPECTED_WIDTH,
        "COMPANION_VISUAL_HEIGHT": EXPECTED_HEIGHT,
        "COMPANION_VISUAL_STRIDE_BYTES": EXPECTED_STRIDE,
        "COMPANION_VISUAL_FRAME_BYTES": EXPECTED_FRAME_BYTES,
        "COMPANION_VISUAL_STATE_COUNT": EXPECTED_STATE_COUNT,
        "COMPANION_VISUAL_UNIQUE_FRAME_COUNT": manifest["capacity"]["unique_frame_count"],
        "COMPANION_VISUAL_PAYLOAD_BYTES": manifest["capacity"]["packed_payload_bytes"],
        "COMPANION_VISUAL_TRANSITION_COUNT": len(manifest["transitions"]),
    }
    check(
        "fixed_geometry_and_capacity_macros",
        macro_values == expected_macros,
        "generated C geometry or capacity macros differ from manifest",
    )

    payload_block = parse_block(
        source,
        "const uint8_t companion_visual_unique_frame_payload"
        "[COMPANION_VISUAL_PAYLOAD_BYTES]",
    )
    payload = bytes(int(value, 16) for value in re.findall(r"\b0x([0-9A-F]{2})\b", payload_block))
    offset_block = parse_block(
        source,
        "const uint32_t companion_visual_unique_frame_offsets"
        "[COMPANION_VISUAL_UNIQUE_FRAME_COUNT]",
    )
    offsets = parse_unsigned_values(offset_block)
    map_block = parse_block(
        source,
        "const uint8_t companion_visual_state_to_unique_frame"
        "[COMPANION_VISUAL_STATE_COUNT]",
    )
    state_to_unique = parse_unsigned_values(map_block)

    descriptor_block = parse_block(
        source,
        "const companion_visual_state_descriptor_t companion_visual_state_descriptors"
        "[COMPANION_VISUAL_STATE_COUNT]",
    )
    descriptors = [
        {
            "unique_frame_index": int(unique_index),
            "width": int(width),
            "height": int(height),
            "stride_bytes": int(stride),
            "orientation_token": orientation,
        }
        for unique_index, width, height, stride, orientation in re.findall(
            r"\{\s*(\d+)u,\s*(\d+)u,\s*(\d+)u,\s*(\d+)u,\s*"
            r"(COMPANION_VISUAL_ORIENTATION_[A-Z0-9_]+)\s*\},",
            descriptor_block,
        )
    ]
    expected_descriptors = [
        {
            "unique_frame_index": item["unique_frame_index"],
            "width": EXPECTED_WIDTH,
            "height": EXPECTED_HEIGHT,
            "stride_bytes": EXPECTED_STRIDE,
            "orientation_token": "COMPANION_VISUAL_ORIENTATION_"
            + c_token(item["orientation"]["semantic"]),
        }
        for item in states
    ]
    check(
        "state_descriptor_geometry_orientation",
        descriptors == expected_descriptors,
        "state descriptor geometry, orientation, or frame mapping differs",
    )

    sha_block = parse_block(
        source,
        "const char companion_visual_state_sha256"
        "[COMPANION_VISUAL_STATE_COUNT][65]",
    )
    parsed_state_shas = re.findall(r'"([0-9A-F]{64})"', sha_block)
    check(
        "state_sha_table",
        parsed_state_shas == [item["frame_sha256"] for item in states],
        "C state SHA table differs from source state identities",
    )

    unique_frames = manifest["unique_frames"]
    expected_offsets = [item["offset"] for item in unique_frames]
    check(
        "payload_capacity",
        len(payload) == manifest["capacity"]["packed_payload_bytes"]
        and len(payload) <= PAYLOAD_BUDGET
        and sha256(payload) == manifest["capacity"]["payload_sha256"],
        "parsed C payload length, budget, or SHA differs",
    )
    check(
        "fixed_unique_offsets",
        offsets == expected_offsets
        and all(
            offset == index * EXPECTED_FRAME_BYTES for index, offset in enumerate(offsets)
        ),
        "unique frame offsets are not fixed contiguous 5000-byte slots",
    )
    check(
        "state_unique_map",
        state_to_unique == [item["unique_frame_index"] for item in states],
        "C state-to-unique-frame map differs from manifest",
    )

    reconstructed: list[dict[str, Any]] = []
    successful_reconstruction = 0
    for state, contract_state, unique_index in zip(states, contract_states, state_to_unique):
        start = offsets[unique_index] if unique_index < len(offsets) else len(payload)
        reconstructed_frame = payload[start : start + EXPECTED_FRAME_BYTES]
        original_frame = (pack_dir / contract_state["raw_file"]).read_bytes()
        byte_equal = reconstructed_frame == original_frame
        reconstructed_sha = sha256(reconstructed_frame)
        sha_equal = (
            reconstructed_sha == state["frame_sha256"] == contract_state["raw_sha256"]
        )
        if byte_equal and sha_equal:
            successful_reconstruction += 1
        reconstructed.append(
            {
                "state_index": state["index"],
                "state_id": state["id"],
                "unique_frame_index": unique_index,
                "source_file": contract_state["raw_file"],
                "source_sha256": contract_state["raw_sha256"],
                "reconstructed_sha256": reconstructed_sha,
                "byte_equal": byte_equal,
                "sha_equal": sha_equal,
            }
        )
    check(
        "frame_reconstruction",
        successful_reconstruction == EXPECTED_STATE_COUNT,
        f"only {successful_reconstruction}/{EXPECTED_STATE_COUNT} states reconstructed",
    )

    alias_relation_valid = True
    for left_index, left in enumerate(states):
        for right in states[left_index + 1 :]:
            same_sha = left["frame_sha256"] == right["frame_sha256"]
            same_unique = left["unique_frame_index"] == right["unique_frame_index"]
            if same_sha != same_unique:
                alias_relation_valid = False
    check(
        "no_stale_alias_semantics",
        alias_relation_valid
        and len(state_ids) == len(state_to_unique) == EXPECTED_STATE_COUNT,
        "pixel sharing does not exactly match SHA equality or state identity was dropped",
    )

    manifest_transitions = manifest["transitions"]
    source_transitions = transition_source["transitions"]
    transition_targets_exist = len(manifest_transitions) == len(source_transitions)
    expected_transition_rows = []
    for generated, original in zip(manifest_transitions, source_transitions):
        from_states = transition_states(original, "from")
        to_states = transition_states(original, "to")
        from_mask = expected_mask(from_states, state_index)
        to_mask = expected_mask(to_states, state_index)
        expected_transition_rows.append(
            {
                "from_mask": from_mask,
                "to_mask": to_mask,
                "event_token": "COMPANION_VISUAL_EVENT_" + c_token(original["event"]),
                "guard_token": "COMPANION_VISUAL_GUARD_"
                + c_token(original.get("guard", "always")),
                "effect_token": "COMPANION_VISUAL_EFFECT_" + c_token(original["effect"]),
            }
        )
        if (
            generated["from_states"] != from_states
            or generated["to_states"] != to_states
            or generated["from_mask"] != from_mask
            or generated["to_mask"] != to_mask
            or not set(from_states + to_states).issubset(state_index)
        ):
            transition_targets_exist = False
    check(
        "transition_targets_exist",
        transition_targets_exist,
        "one or more transition source/target states or masks differ",
    )

    transition_block = parse_block(
        source,
        "const companion_visual_transition_t companion_visual_transition_table"
        "[COMPANION_VISUAL_TRANSITION_COUNT]",
    )
    parsed_transition_rows = [
        {
            "from_mask": int(from_mask, 16),
            "to_mask": int(to_mask, 16),
            "event_token": event,
            "guard_token": guard,
            "effect_token": effect,
        }
        for from_mask, to_mask, event, guard, effect in re.findall(
            r"\{\s*UINT32_C\(0x([0-9A-F]{8})\),\s*"
            r"UINT32_C\(0x([0-9A-F]{8})\),\s*"
            r"(COMPANION_VISUAL_EVENT_[A-Z0-9_]+),\s*"
            r"(COMPANION_VISUAL_GUARD_[A-Z0-9_]+),\s*"
            r"(COMPANION_VISUAL_EFFECT_[A-Z0-9_]+)\s*\},",
            transition_block,
        )
    ]
    check(
        "transition_c_table",
        parsed_transition_rows == expected_transition_rows,
        "generated C transition table differs from source transitions",
    )

    default_off_pattern = (
        rf"#ifndef {ENABLE_MACRO}\s*"
        rf"#define {ENABLE_MACRO} 0\s*"
        r"#endif"
    )
    check(
        "default_off",
        bool(re.search(default_off_pattern, header))
        and f"#if {ENABLE_MACRO}" in header
        and f"#if {ENABLE_MACRO}" in source,
        "asset pack is not compile-time default-off",
    )
    dynamic_allocation_pattern = r"\b(?:malloc|calloc|realloc|free)\s*\("
    check(
        "no_dynamic_allocation",
        not re.search(dynamic_allocation_pattern, header + "\n" + source)
        and manifest["capacity"]["allocation"] == "static_const"
        and manifest["capacity"]["dynamic_allocation"] is False,
        "dynamic allocation or non-static capacity was detected",
    )

    deterministic_files: list[dict[str, Any]] = []
    deterministic_equal = True
    for name in GENERATED_FILES:
        canonical_path = pack_dir / name
        rerun_path = rerun_dir / name
        canonical_bytes = canonical_path.read_bytes()
        rerun_bytes = rerun_path.read_bytes()
        byte_equal = canonical_bytes == rerun_bytes
        deterministic_equal &= byte_equal
        deterministic_files.append(
            {
                "file": name,
                "canonical_sha256": sha256(canonical_bytes),
                "rerun_sha256": sha256(rerun_bytes),
                "byte_equal": byte_equal,
            }
        )
    check(
        "deterministic_rerun",
        deterministic_equal,
        "one or more generated files differ on the second run",
    )

    if not compiler.is_file():
        raise FileNotFoundError(f"compiler not found: {compiler}")
    disabled_compile = compiler_run(
        compiler,
        source_path,
        pack_dir,
        object_dir / "companion_visual_asset_pack.default-off.o",
        enabled=False,
    )
    enabled_compile = compiler_run(
        compiler,
        source_path,
        pack_dir,
        object_dir / "companion_visual_asset_pack.enabled.o",
        enabled=True,
    )
    compile_results = [disabled_compile, enabled_compile]
    check(
        "compile_ready_default_off_and_enabled",
        all(item["return_code"] == 0 for item in compile_results),
        "ARM GCC failed in default-off or enabled mode",
    )

    result = {
        "schema": "companion.visual-c-asset-pack-machine-result.v1",
        "requirement": "COMP-REQ-467/471",
        "status": "PASS" if not errors else "NO_GO",
        "checks": checks,
        "errors": errors,
        "source": {
            "visual_contract": {
                "file": str(contract_path),
                "sha256": file_sha(contract_path),
            },
            "state_transitions": {
                "file": str(transitions_path),
                "sha256": file_sha(transitions_path),
            },
        },
        "capacity": {
            "state_count": len(states),
            "unique_frame_count": len(unique_frames),
            "frame_bytes": EXPECTED_FRAME_BYTES,
            "packed_payload_bytes": len(payload),
            "payload_budget_bytes": PAYLOAD_BUDGET,
            "capacity_fixed": checks["fixed_geometry_and_capacity_macros"],
            "dynamic_allocation": False,
        },
        "frame_reconstruction": {
            "passed": successful_reconstruction,
            "expected": EXPECTED_STATE_COUNT,
            "result": f"{successful_reconstruction}/{EXPECTED_STATE_COUNT}",
            "states": reconstructed,
        },
        "alias_semantics": {
            "same_pixels_may_share_storage": True,
            "state_identity_count": len(state_ids),
            "state_to_unique_mapping_count": len(state_to_unique),
            "no_stale_alias_semantics": checks["no_stale_alias_semantics"],
        },
        "transitions": {
            "count": len(parsed_transition_rows),
            "all_targets_exist": checks["transition_targets_exist"],
            "c_table_matches": checks["transition_c_table"],
        },
        "deterministic_rerun": {
            "result": "0 diff" if deterministic_equal else "DIFF",
            "files": deterministic_files,
        },
        "compile": {
            "compiler": str(compiler),
            "compiler_sha256": file_sha(compiler),
            "results": compile_results,
        },
        "artifact_sha256": {
            name: file_sha(pack_dir / name) for name in GENERATED_FILES
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=True, indent=2) + "\n",
        encoding="ascii",
        newline="\n",
    )
    print(json.dumps({"status": result["status"], "checks": checks, "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
