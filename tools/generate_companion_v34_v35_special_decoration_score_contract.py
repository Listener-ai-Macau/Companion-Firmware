#!/usr/bin/env python3
"""Generate the source-only score contract for V34/V35 decorations.

This is a plan generator, not a runtime binder.  It combines registered V22
face layers with registered V34/V35 decoration layers; no complete face card
or raster drawing is represented here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPECIAL = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/special-decoration-component-layout.json"
V22 = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
OUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/target-score-attempt-01/special-decoration-score-contract.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    special = json.loads(SPECIAL.read_text(encoding="utf-8"))
    v22 = json.loads(V22.read_text(encoding="utf-8"))
    if special.get("locked_v9_source_sha256") != LOCKED or v22.get("locked_v9_source_sha256") != LOCKED:
        raise ValueError("locked V9 identity drifted")
    components = {entry["name"]: entry for entry in special["components"]}
    bridges = {entry["name"]: entry for entry in v22["bridges"]}

    def face(bridge: str, frame: int) -> list[dict[str, object]]:
        return [{"component_id": layer["component_id"], "offset": layer["offset"], "pack": "v22_face"}
                for layer in bridges[bridge]["frames"][frame]["layers"]]

    # Each item preserves the source decoration cadence while the face moves
    # through the accepted V22 causal component sequence.
    mapping = {
        "recording_input": ("activity", "calm__curious", (0, 1, 2)),
        "bottom_connector_charging": ("activity", "curious__warm", (0, 1, 2)),
        "curious_question": ("entry", "calm__curious", (0, 1, 2)),
        "alert_exclamation": ("entry", "puzzled__alert", (0, 1, 2)),
    }
    scores: dict[str, object] = {}
    for event, (phase, bridge, face_frames) in mapping.items():
        source_steps = special["scores"][event][phase]
        steps = []
        for source_step, face_frame in zip(source_steps, face_frames):
            decoration = []
            for name in source_step["components"]:
                component = components[name]
                decoration.append({"component_id": component["component_id"], "offset": [0, 0],
                                   "pack": "v34_v35_decoration"})
            layers = face(bridge, face_frame) + decoration
            if len(layers) > 16:
                raise ValueError(f"{event} exceeds Rig layer capacity")
            steps.append({"cue": bridges[bridge]["frames"][face_frame]["cue"],
                          "duration_ms": source_step["duration_ms"], "layers": layers})
        scores[event] = {"phase": phase, "prelude_bridge": bridge, "steps": steps,
                         "runtime_binding": "forbidden_until_target_replay_and_owner_review"}
    # Dream-cloud needs the locked V9 sleepy components, which intentionally
    # remain a separate candidate namespace until its profile is generated.
    scores["sleepy_dream_cloud"] = {"runtime_binding": "fail_closed_pending_v9_sleep_profile",
                                     "reason": "V22 has no registered sleepy-eye pose"}
    output = {"schema": "companion.v34_v35_special_decoration_score_contract.v1",
              "status": "CANDIDATE_TARGET_PROFILE_PENDING",
              "locked_v9_source_sha256": LOCKED,
              "runtime_resource_activated": False,
              "active_candidate_binding": "forbidden",
              "sources": {"v22_layout": rel(V22), "v22_layout_sha256": sha256(V22),
                          "special_layout": rel(SPECIAL), "special_layout_sha256": sha256(SPECIAL)},
              "scores": scores,
              "non_claims": ["no_full_face_card", "no_code_drawn_face", "no_special_runtime_binding"]}
    data = (json.dumps(output, indent=2) + "\n").encode("utf-8")
    if args.check:
        if not OUT.is_file() or OUT.read_bytes() != data:
            raise ValueError("generated special score contract drifted")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(data)
    print(f"PASS: special decoration score contract -> {rel(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
