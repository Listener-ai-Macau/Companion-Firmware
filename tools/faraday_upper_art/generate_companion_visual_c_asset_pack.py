#!/usr/bin/env python3
"""Generate a deterministic, default-off C asset pack from COMP-REQ-471."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


STATE_COUNT = 17
FRAME_WIDTH = 200
FRAME_HEIGHT = 200
FRAME_STRIDE = 25
FRAME_BYTES = 5000
PAYLOAD_BUDGET = 85000
ENABLE_MACRO = "COMPANION_VISUAL_ASSET_PACK_ENABLE"
PREFIX = "COMPANION_VISUAL"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii", newline="\n")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=True, indent=2) + "\n")


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


def enum_lines(prefix: str, values: list[str], count_name: str) -> list[str]:
    lines = [f"  {prefix}_{c_token(value)} = {index}," for index, value in enumerate(values)]
    lines.append(f"  {prefix}_{count_name} = {len(values)}")
    return lines


def bytes_initializer(payload: bytes, width: int = 16) -> str:
    lines = []
    for offset in range(0, len(payload), width):
        chunk = payload[offset : offset + width]
        lines.append("  " + ", ".join(f"0x{value:02X}" for value in chunk) + ",")
    return "\n".join(lines)


def integer_initializer(values: list[int], width: int = 12) -> str:
    lines = []
    for offset in range(0, len(values), width):
        chunk = values[offset : offset + width]
        lines.append("  " + ", ".join(f"{value}u" for value in chunk) + ",")
    return "\n".join(lines)


def ordered_unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def transition_states(item: dict[str, Any], key: str) -> list[str]:
    direct = item.get(key)
    many = item.get(f"{key}_any")
    if direct is not None:
        return [direct]
    if many is not None:
        return list(many)
    raise ValueError(f"transition lacks {key}/{key}_any: {item}")


def state_mask(states: list[str], state_index: dict[str, int]) -> int:
    mask = 0
    for state in states:
        if state not in state_index:
            raise ValueError(f"transition references unknown state: {state}")
        mask |= 1 << state_index[state]
    if mask == 0:
        raise ValueError("transition state mask may not be empty")
    return mask


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    input_dir = args.input.resolve()
    output_dir = args.output.resolve()
    contract_path = input_dir / "visual-contract.json"
    transitions_path = input_dir / "state-transitions.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    transition_source = json.loads(transitions_path.read_text(encoding="utf-8"))

    fmt = contract["format"]
    if (
        contract["frame_count"] != STATE_COUNT
        or fmt["width"] != FRAME_WIDTH
        or fmt["height"] != FRAME_HEIGHT
        or fmt["row_stride_bytes"] != FRAME_STRIDE
        or fmt["frame_bytes"] != FRAME_BYTES
        or fmt["bits_per_pixel"] != 1
    ):
        raise ValueError("source visual contract geometry/count changed")

    states = contract["frames"]
    state_ids = [item["id"] for item in states]
    if len(state_ids) != STATE_COUNT or len(set(state_ids)) != STATE_COUNT:
        raise ValueError("state identities are not exactly 17 unique values")
    state_index = {state_id: index for index, state_id in enumerate(state_ids)}

    raw_frames: list[bytes] = []
    unique_frames: list[bytes] = []
    unique_shas: list[str] = []
    state_to_unique: list[int] = []
    unique_states: list[list[str]] = []
    for state in states:
        raw_path = input_dir / state["raw_file"]
        raw = raw_path.read_bytes()
        if len(raw) != FRAME_BYTES or sha256(raw) != state["raw_sha256"]:
            raise ValueError(f"source frame identity changed: {state['id']}")
        raw_frames.append(raw)
        frame_sha = state["raw_sha256"]
        if frame_sha in unique_shas:
            unique_index = unique_shas.index(frame_sha)
            if unique_frames[unique_index] != raw:
                raise ValueError(f"SHA collision for state {state['id']}")
            unique_states[unique_index].append(state["id"])
        else:
            unique_index = len(unique_frames)
            unique_frames.append(raw)
            unique_shas.append(frame_sha)
            unique_states.append([state["id"]])
        state_to_unique.append(unique_index)

    unique_payload = b"".join(unique_frames)
    unique_offsets = [index * FRAME_BYTES for index in range(len(unique_frames))]
    if len(unique_payload) > PAYLOAD_BUDGET:
        raise ValueError("deduplicated payload exceeds 85000-byte budget")

    transition_items = transition_source["transitions"]
    events = ordered_unique([item["event"] for item in transition_items])
    guards = ordered_unique([item.get("guard", "always") for item in transition_items])
    effects = ordered_unique([item["effect"] for item in transition_items])
    transitions = []
    for index, item in enumerate(transition_items):
        from_states = transition_states(item, "from")
        to_states = transition_states(item, "to")
        transitions.append(
            {
                "index": index,
                "from_states": from_states,
                "to_states": to_states,
                "from_mask": state_mask(from_states, state_index),
                "to_mask": state_mask(to_states, state_index),
                "event": item["event"],
                "event_index": events.index(item["event"]),
                "guard": item.get("guard", "always"),
                "guard_index": guards.index(item.get("guard", "always")),
                "effect": item["effect"],
                "effect_index": effects.index(item["effect"]),
            }
        )

    orientation_values = ordered_unique([item["orientation"]["semantic"] for item in states])
    header_name = "companion_visual_asset_pack.h"
    source_name = "companion_visual_asset_pack.c"
    manifest_name = "c-asset-pack-manifest.json"
    handoff_name = "c-asset-pack-handoff.json"

    header = f"""#ifndef COMPANION_VISUAL_ASSET_PACK_H
#define COMPANION_VISUAL_ASSET_PACK_H

#include <stddef.h>
#include <stdint.h>

#ifndef {ENABLE_MACRO}
#define {ENABLE_MACRO} 0
#endif

#define {PREFIX}_WIDTH 200u
#define {PREFIX}_HEIGHT 200u
#define {PREFIX}_STRIDE_BYTES 25u
#define {PREFIX}_FRAME_BYTES 5000u
#define {PREFIX}_STATE_COUNT 17u
#define {PREFIX}_UNIQUE_FRAME_COUNT {len(unique_frames)}u
#define {PREFIX}_PAYLOAD_BYTES {len(unique_payload)}u
#define {PREFIX}_TRANSITION_COUNT {len(transitions)}u
#define {PREFIX}_STATE_MASK_ALL UINT32_C(0x{(1 << STATE_COUNT) - 1:08X})

typedef enum {{
{chr(10).join(enum_lines(f"{PREFIX}_STATE", state_ids, "ENUM_COUNT"))}
}} companion_visual_state_t;

typedef enum {{
{chr(10).join(enum_lines(f"{PREFIX}_ORIENTATION", orientation_values, "COUNT"))}
}} companion_visual_orientation_t;

typedef enum {{
{chr(10).join(enum_lines(f"{PREFIX}_EVENT", events, "COUNT"))}
}} companion_visual_event_t;

typedef enum {{
{chr(10).join(enum_lines(f"{PREFIX}_GUARD", guards, "COUNT"))}
}} companion_visual_guard_t;

typedef enum {{
{chr(10).join(enum_lines(f"{PREFIX}_EFFECT", effects, "COUNT"))}
}} companion_visual_effect_t;

typedef struct {{
  uint8_t unique_frame_index;
  uint16_t width;
  uint16_t height;
  uint16_t stride_bytes;
  companion_visual_orientation_t orientation;
}} companion_visual_state_descriptor_t;

typedef struct {{
  uint32_t from_state_mask;
  uint32_t to_state_mask;
  companion_visual_event_t event;
  companion_visual_guard_t guard;
  companion_visual_effect_t effect;
}} companion_visual_transition_t;

#if {ENABLE_MACRO}
extern const uint8_t companion_visual_unique_frame_payload[{PREFIX}_PAYLOAD_BYTES];
extern const uint32_t companion_visual_unique_frame_offsets[{PREFIX}_UNIQUE_FRAME_COUNT];
extern const uint8_t companion_visual_state_to_unique_frame[{PREFIX}_STATE_COUNT];
extern const companion_visual_state_descriptor_t companion_visual_state_descriptors[{PREFIX}_STATE_COUNT];
extern const char companion_visual_state_sha256[{PREFIX}_STATE_COUNT][65];
extern const companion_visual_transition_t companion_visual_transition_table[{PREFIX}_TRANSITION_COUNT];

const uint8_t *companion_visual_frame_for_state(companion_visual_state_t state);
size_t companion_visual_frame_size_for_state(companion_visual_state_t state);
#endif

#endif
"""

    descriptor_lines = []
    sha_lines = []
    for state, unique_index in zip(states, state_to_unique):
        orientation = f"{PREFIX}_ORIENTATION_{c_token(state['orientation']['semantic'])}"
        descriptor_lines.append(
            f"  {{ {unique_index}u, {FRAME_WIDTH}u, {FRAME_HEIGHT}u, {FRAME_STRIDE}u, {orientation} }},"
        )
        sha_lines.append(f'  "{state["raw_sha256"]}",')

    transition_lines = []
    for item in transitions:
        transition_lines.append(
            "  { "
            f"UINT32_C(0x{item['from_mask']:08X}), UINT32_C(0x{item['to_mask']:08X}), "
            f"{PREFIX}_EVENT_{c_token(item['event'])}, "
            f"{PREFIX}_GUARD_{c_token(item['guard'])}, "
            f"{PREFIX}_EFFECT_{c_token(item['effect'])} "
            "},"
        )

    source = f"""#include "{header_name}"

#if {ENABLE_MACRO}
const uint8_t companion_visual_unique_frame_payload[{PREFIX}_PAYLOAD_BYTES] = {{
{bytes_initializer(unique_payload)}
}};

const uint32_t companion_visual_unique_frame_offsets[{PREFIX}_UNIQUE_FRAME_COUNT] = {{
{integer_initializer(unique_offsets)}
}};

const uint8_t companion_visual_state_to_unique_frame[{PREFIX}_STATE_COUNT] = {{
{integer_initializer(state_to_unique)}
}};

const companion_visual_state_descriptor_t companion_visual_state_descriptors[{PREFIX}_STATE_COUNT] = {{
{chr(10).join(descriptor_lines)}
}};

const char companion_visual_state_sha256[{PREFIX}_STATE_COUNT][65] = {{
{chr(10).join(sha_lines)}
}};

const companion_visual_transition_t companion_visual_transition_table[{PREFIX}_TRANSITION_COUNT] = {{
{chr(10).join(transition_lines)}
}};

const uint8_t *companion_visual_frame_for_state(companion_visual_state_t state) {{
  uint32_t state_index = (uint32_t)state;
  uint8_t unique_index;
  if (state_index >= {PREFIX}_STATE_COUNT) {{
    return NULL;
  }}
  unique_index = companion_visual_state_to_unique_frame[state_index];
  return &companion_visual_unique_frame_payload[
      companion_visual_unique_frame_offsets[unique_index]];
}}

size_t companion_visual_frame_size_for_state(companion_visual_state_t state) {{
  return ((uint32_t)state < {PREFIX}_STATE_COUNT) ? {PREFIX}_FRAME_BYTES : 0u;
}}
#endif
"""

    header_path = output_dir / header_name
    source_path = output_dir / source_name
    write_text(header_path, header)
    write_text(source_path, source)

    unique_entries = []
    for index, (frame_sha, aliases) in enumerate(zip(unique_shas, unique_states)):
        unique_entries.append(
            {
                "index": index,
                "offset": unique_offsets[index],
                "bytes": FRAME_BYTES,
                "sha256": frame_sha,
                "states": aliases,
            }
        )
    state_entries = []
    for index, (state, unique_index) in enumerate(zip(states, state_to_unique)):
        state_entries.append(
            {
                "index": index,
                "id": state["id"],
                "c_enum": f"{PREFIX}_STATE_{c_token(state['id'])}",
                "unique_frame_index": unique_index,
                "frame_sha256": state["raw_sha256"],
                "width": FRAME_WIDTH,
                "height": FRAME_HEIGHT,
                "stride_bytes": FRAME_STRIDE,
                "orientation": state["orientation"],
            }
        )
    manifest = {
        "schema": "companion.visual-c-asset-pack.v1",
        "requirement": "COMP-REQ-467/471",
        "status": "PASS",
        "default_off": {
            "macro": ENABLE_MACRO,
            "default": 0,
            "app_or_build_wiring_changed": False,
        },
        "source": {
            "visual_contract_file": "visual-contract.json",
            "visual_contract_sha256": file_sha(contract_path),
            "state_transitions_file": "state-transitions.json",
            "state_transitions_sha256": file_sha(transitions_path),
            "frames_bin_sha256": contract["combined_sha256"],
        },
        "format": {
            "width": FRAME_WIDTH,
            "height": FRAME_HEIGHT,
            "stride_bytes": FRAME_STRIDE,
            "frame_bytes": FRAME_BYTES,
            "bits_per_pixel": 1,
            "bit_order": fmt["bit_order"],
            "row_order": fmt["row_order"],
        },
        "capacity": {
            "allocation": "static_const",
            "dynamic_allocation": False,
            "state_count": len(states),
            "unique_frame_count": len(unique_frames),
            "unduplicated_payload_bytes": len(raw_frames) * FRAME_BYTES,
            "packed_payload_bytes": len(unique_payload),
            "payload_budget_bytes": PAYLOAD_BUDGET,
            "deduplicated_bytes": len(raw_frames) * FRAME_BYTES - len(unique_payload),
            "within_budget": len(unique_payload) <= PAYLOAD_BUDGET,
            "payload_sha256": sha256(unique_payload),
        },
        "states": state_entries,
        "unique_frames": unique_entries,
        "transitions": transitions,
        "generated_files": {
            header_name: file_sha(header_path),
            source_name: file_sha(source_path),
        },
        "invariants": {
            "state_identity_count": len(state_ids),
            "state_to_unique_mapping_count": len(state_to_unique),
            "same_sha_shares_unique_frame": True,
            "different_sha_never_aliases": True,
            "transition_targets_exist": True,
            "frame_reconstruction_expected": f"{len(states)}/{len(states)}",
        },
    }
    manifest_path = output_dir / manifest_name
    write_json(manifest_path, manifest)

    handoff = {
        "schema": "companion.lower-driver-c-asset-pack-handoff.v1",
        "requirement": "COMP-REQ-467/471",
        "status": "PASS",
        "integration_authorized": False,
        "default_off_macro": ENABLE_MACRO,
        "header": {"file": header_name, "sha256": file_sha(header_path)},
        "source": {"file": source_name, "sha256": file_sha(source_path)},
        "pack_manifest": {"file": manifest_name, "sha256": file_sha(manifest_path)},
        "state_count": len(states),
        "unique_frame_count": len(unique_frames),
        "transition_count": len(transitions),
        "frame_bytes": FRAME_BYTES,
        "payload_bytes": len(unique_payload),
        "payload_budget_bytes": PAYLOAD_BUDGET,
        "consumer_notes": [
            f"define {ENABLE_MACRO}=1 only in a separately authorized lower-driver target",
            "use companion_visual_state_t as the stable state identity",
            "resolve pixels through companion_visual_frame_for_state; identical pixels may share storage",
            "do not modify the generated payload, state map, transition masks, orientation, or geometry",
            "this pack does not modify app build wiring and is not production or hardware authorization",
        ],
    }
    handoff_path = output_dir / handoff_name
    write_json(handoff_path, handoff)

    print(
        json.dumps(
            {
                "status": "PASS",
                "state_count": len(states),
                "unique_frame_count": len(unique_frames),
                "payload_bytes": len(unique_payload),
                "payload_budget_bytes": PAYLOAD_BUDGET,
                "transition_count": len(transitions),
                "header_sha256": file_sha(header_path),
                "source_sha256": file_sha(source_path),
                "manifest_sha256": file_sha(manifest_path),
                "handoff_sha256": file_sha(handoff_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
