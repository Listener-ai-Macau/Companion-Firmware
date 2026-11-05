#!/usr/bin/env python3
"""Rebuild the retained V45 expression frames from their registered masks.

This is a host-side art inspection helper.  It deliberately consumes the V22
face registry and the V45 special-component registry rather than segmenting a
rendered face with rectangular crops.  The default reconstruction is expected
to be byte-identical to the 50 V45 expression-track PBMs.

The small API is also useful to an art review builder:

    authority = load_authority(repo_root)
    frame = render_step(authority, step)                 # exact V45 placement
    frame = render_step(authority, step, face_offset=(2, 0))

``face_offset`` moves only registered facial anatomy.  Eye ink, highlights and
sparkles move together, and their original masks are never resized.  Emotional
ornaments (question mark, exclamation mark, sleep Z and playful accent) remain
independent and may be moved with ``ornament_offset`` or omitted for a separate
placement pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


WIDTH = 200
HEIGHT = 200

PROFILE = Path(
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/target-score-attempt-01/v45-wb55-target-profile-plan.json"
)
V22_LAYOUT = Path(
    "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-"
    "separation-source/candidate/target-rig-attempt-01/"
    "v22-emotion-separation-target-rig-layout.json"
)
V45_LAYOUT = Path(
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/v45-special-component-layout.json"
)
REFERENCE_DIR = Path(
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01"
)
COMPONENT_PLAN_DIR = Path(
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "r7-locked-v9-export-20260723/component-plans"
)

# These registered masks communicate emotion but are not facial anatomy.
# They stay independent when a face is translated to correct its anchor.
V45_EMOTIONAL_ORNAMENT_IDS = frozenset(
    {
        512,
        513,
        514,  # curious question mark
        521,
        522,
        523,  # alert exclamation mark
        594,
        595,
        596,  # sleepy Z sequence
    }
)
V22_ORNAMENT_ROLES = frozenset({"accent"})
CANONICAL_NOSE_ORIGIN = (94, 121)


@dataclass(frozen=True)
class Component:
    component_id: int
    name: str
    role: str
    base_x: int
    base_y: int
    z_index: int
    composite_op: str
    width: int
    height: int
    pixels: frozenset[tuple[int, int]]
    source_pack: str

    @property
    def is_ornament(self) -> bool:
        return self.component_id in V45_EMOTIONAL_ORNAMENT_IDS or self.role in V22_ORNAMENT_ROLES

    @property
    def is_face(self) -> bool:
        return not self.is_ornament


@dataclass(frozen=True)
class Authority:
    repo_root: Path
    profile: Mapping[str, Any]
    components: Mapping[tuple[str, int], Component]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_pbm(path: Path) -> tuple[int, int, frozenset[tuple[int, int]]]:
    """Read a binary P4 PBM and return its black-pixel coordinates."""

    data = path.read_bytes()
    tokens: list[bytes] = []
    cursor = 0
    while len(tokens) < 3:
        while cursor < len(data) and chr(data[cursor]).isspace():
            cursor += 1
        if cursor < len(data) and data[cursor] == ord("#"):
            while cursor < len(data) and data[cursor] not in (10, 13):
                cursor += 1
            continue
        start = cursor
        while cursor < len(data) and not chr(data[cursor]).isspace():
            cursor += 1
        tokens.append(data[start:cursor])
    if tokens[0] != b"P4":
        raise ValueError(f"{path}: expected binary P4 PBM")
    width, height = int(tokens[1]), int(tokens[2])
    if cursor >= len(data) or not chr(data[cursor]).isspace():
        raise ValueError(f"{path}: PBM header has no raster separator")
    # P4 has one whitespace separator after height.  Do not skip arbitrary
    # whitespace here: the first binary raster byte may itself be 0x0a/0x20.
    if data[cursor] == 13 and cursor + 1 < len(data) and data[cursor + 1] == 10:
        cursor += 2
    else:
        cursor += 1
    stride = (width + 7) // 8
    raster = data[cursor:]
    if len(raster) != stride * height:
        raise ValueError(f"{path}: raster is {len(raster)} bytes, expected {stride * height}")
    pixels = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if raster[y * stride + x // 8] & (0x80 >> (x & 7))
    }
    return width, height, frozenset(pixels)


def write_pbm(pixels: Iterable[tuple[int, int]], width: int = WIDTH, height: int = HEIGHT) -> bytes:
    """Encode black-pixel coordinates as a canonical binary P4 PBM."""

    stride = (width + 7) // 8
    raster = bytearray(stride * height)
    for x, y in pixels:
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"pixel outside {width}x{height}: {(x, y)}")
        raster[y * stride + x // 8] |= 0x80 >> (x & 7)
    return f"P4\n{width} {height}\n".encode("ascii") + bytes(raster)


def _component(repo_root: Path, item: Mapping[str, Any], source_pack: str) -> Component:
    width, height, pixels = read_pbm(repo_root / item["mask"])
    declared = item.get("mask_size", [item.get("width"), item.get("height")])
    if [width, height] != list(declared):
        raise ValueError(f"component {item['component_id']} mask dimensions disagree with registry")
    return Component(
        component_id=int(item["component_id"]),
        name=str(item["name"]),
        role=str(item.get("role") or "special"),
        base_x=int(item["base_position"][0]),
        base_y=int(item["base_position"][1]),
        z_index=int(item["z_index"]),
        composite_op=str(item["composite_op"]),
        width=width,
        height=height,
        pixels=pixels,
        source_pack=source_pack,
    )


def load_authority(repo_root: Path | str) -> Authority:
    repo_root = Path(repo_root).resolve()
    profile = _read_json(repo_root / PROFILE)
    v22 = _read_json(repo_root / V22_LAYOUT)
    v45 = _read_json(repo_root / V45_LAYOUT)
    components: dict[tuple[str, int], Component] = {}
    for item in v22["components"]:
        component = _component(repo_root, item, "v22_face")
        components[("v22_face", component.component_id)] = component
    for item in v45["components"]:
        component = _component(repo_root, item, "v45_special_source")
        components[("v45_special_source", component.component_id)] = component
    return Authority(repo_root=repo_root, profile=profile, components=components)


def classify_layers(authority: Authority, step: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    """Split one profile step into registered face and emotional ornaments."""

    result: dict[str, list[Mapping[str, Any]]] = {"face": [], "ornament": []}
    for layer in step["layers"]:
        component = authority.components[(str(layer["pack"]), int(layer["component_id"]))]
        result["ornament" if component.is_ornament else "face"].append(layer)
    return result


def render_step(
    authority: Authority,
    step: Mapping[str, Any],
    *,
    face_offset: tuple[int, int] = (0, 0),
    ornament_offset: tuple[int, int] = (0, 0),
    include_face: bool = True,
    include_ornaments: bool = True,
    canvas_offset: tuple[int, int] = (0, 0),
) -> frozenset[tuple[int, int]]:
    """Render one profile step without scaling or synthesizing any mask."""

    ordered: list[tuple[int, int, Mapping[str, Any], Component]] = []
    for order, layer in enumerate(step["layers"]):
        component = authority.components[(str(layer["pack"]), int(layer["component_id"]))]
        if (component.is_face and not include_face) or (component.is_ornament and not include_ornaments):
            continue
        ordered.append((component.z_index, order, layer, component))
    ink: set[tuple[int, int]] = set()
    for _, _, layer, component in sorted(ordered):
        group_offset = ornament_offset if component.is_ornament else face_offset
        x0 = component.base_x + int(layer["offset"][0]) + group_offset[0] + canvas_offset[0]
        y0 = component.base_y + int(layer["offset"][1]) + group_offset[1] + canvas_offset[1]
        placed = {(x0 + x, y0 + y) for x, y in component.pixels}
        if any(x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT for x, y in placed):
            raise ValueError(f"component {component.component_id} leaves the 200x200 canvas")
        if component.composite_op == "ink":
            ink.update(placed)
        elif component.composite_op == "erase":
            ink.difference_update(placed)
        else:
            raise ValueError(f"component {component.component_id}: unknown operation {component.composite_op}")
    return frozenset(ink)


def load_component_plan(
    authority: Authority, track: str, index: int, cue: str
) -> Mapping[str, Any]:
    """Load the locked R7 plan which records V45's per-frame normalization."""

    path = authority.repo_root / COMPONENT_PLAN_DIR / track / f"{index:02d}-{cue}.json"
    plan = _read_json(path)
    if plan["story"] != track or int(plan["index"]) != index or plan["cue"] != cue:
        raise ValueError(f"{path}: plan identity does not match requested frame")
    return plan


def render_expression_frame(
    authority: Authority,
    track: str,
    index: int,
    step: Mapping[str, Any],
    *,
    face_offset: tuple[int, int] = (0, 0),
    ornament_offset: tuple[int, int] = (0, 0),
    include_face: bool = True,
    include_ornaments: bool = True,
) -> frozenset[tuple[int, int]]:
    """Render one canonical V45 frame, including its locked canvas offset."""

    plan = load_component_plan(authority, track, index, str(step["cue"]))
    # The profile and locked export must describe the same registered layers.
    profile_identity = [
        (str(layer["pack"]), int(layer["component_id"]), list(layer["offset"]))
        for layer in step["layers"]
    ]
    plan_identity = [
        (str(layer["pack"]), int(layer["component_id"]), list(layer["offset"]))
        for layer in plan["layers"]
    ]
    if profile_identity != plan_identity:
        raise ValueError(f"{track}/{step['cue']}: profile and locked component plan diverge")
    return render_step(
        authority,
        step,
        face_offset=face_offset,
        ornament_offset=ornament_offset,
        include_face=include_face,
        include_ornaments=include_ornaments,
        canvas_offset=tuple(int(v) for v in plan["normalization_offset"]),
    )


def face_offset_to_nose_origin(
    authority: Authority,
    track: str,
    index: int,
    step: Mapping[str, Any],
    target: tuple[int, int] = CANONICAL_NOSE_ORIGIN,
) -> tuple[int, int]:
    """Return an integer translation that aligns the registered fixed nose.

    The locked R7 export centered the *whole* expression, so question marks,
    exclamation marks and Zs pulled three faces downward.  Using component 4's
    registered origin supplies a stable facial anchor without measuring or
    altering the rendered silhouette.
    """

    nose_layers = [
        layer
        for layer in step["layers"]
        if str(layer["pack"]) == "v22_face" and int(layer["component_id"]) == 4
    ]
    if len(nose_layers) != 1:
        raise ValueError(f"{track}/{step['cue']}: expected one registered fixed nose")
    plan = load_component_plan(authority, track, index, str(step["cue"]))
    nose = authority.components[("v22_face", 4)]
    layer = nose_layers[0]
    current = (
        nose.base_x + int(layer["offset"][0]) + int(plan["normalization_offset"][0]),
        nose.base_y + int(layer["offset"][1]) + int(plan["normalization_offset"][1]),
    )
    return target[0] - current[0], target[1] - current[1]


def nearest_clear_ornament_offset(
    authority: Authority,
    track: str,
    index: int,
    step: Mapping[str, Any],
    *,
    face_offset: tuple[int, int] = (0, 0),
    minimum_y: int = 16,
    search_radius: int = 16,
) -> tuple[int, int] | None:
    """Find the smallest no-overlap nudge for this step's own ornament ink."""

    face = render_expression_frame(
        authority, track, index, step, face_offset=face_offset, include_ornaments=False
    )
    candidates = [
        (dx, dy)
        for dy in range(-search_radius, search_radius + 1)
        for dx in range(-search_radius, search_radius + 1)
    ]
    candidates.sort(key=lambda p: (abs(p[0]) + abs(p[1]), max(abs(p[0]), abs(p[1])), p[1], p[0]))
    for offset in candidates:
        ornament = render_expression_frame(
            authority,
            track,
            index,
            step,
            ornament_offset=offset,
            include_face=False,
        )
        if not ornament:
            return (0, 0)
        if min(y for _, y in ornament) >= minimum_y and not face.intersection(ornament):
            return offset
    return None


def expression_steps(authority: Authority) -> Iterable[tuple[str, int, Mapping[str, Any]]]:
    """Yield the 10 five-stage presence tracks (50 authored frames)."""

    for track in authority.profile["expression_tracks"]:
        # The five attention demonstrations are runtime gaze tests rather than
        # the ten retained family performances requested by the art workflow.
        if str(track["name"]).startswith("daily_attention_"):
            continue
        for index, step in enumerate(track["steps"]):
            yield str(track["name"]), index, step


def verify_expression_reconstruction(authority: Authority) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    checked = 0
    for track, index, step in expression_steps(authority):
        expected_path = authority.repo_root / REFERENCE_DIR / f"{track}-{index:02d}-{step['cue']}.pbm"
        expected_bytes = expected_path.read_bytes()
        actual_pixels = render_expression_frame(authority, track, index, step)
        actual_bytes = write_pbm(actual_pixels)
        checked += 1
        if actual_bytes != expected_bytes:
            _, _, expected_pixels = read_pbm(expected_path)
            mismatches.append(
                {
                    "track": track,
                    "index": index,
                    "cue": step["cue"],
                    "different_pixels": len(actual_pixels.symmetric_difference(expected_pixels)),
                    "expected_sha256": hashlib.sha256(expected_bytes).hexdigest(),
                    "actual_sha256": hashlib.sha256(actual_bytes).hexdigest(),
                }
            )
    return {
        "result": "PASS_COMPONENT_RECONSTRUCTION" if not mismatches else "FAIL_COMPONENT_RECONSTRUCTION",
        "claim": "HOST_REGISTERED_MASK_RECONSTRUCTION_ONLY",
        "frames_checked": checked,
        "mismatches": mismatches,
        "face_policy": "registered anatomy masks only; zero scaling; eye ink/highlight/sparkle move together",
        "ornament_policy": "question, exclamation, sleep Z, and playful accent remain independent",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--verify", action="store_true", help="compare all 50 expression frames to V45 PBMs")
    args = parser.parse_args()
    authority = load_authority(args.repo_root)
    result = verify_expression_reconstruction(authority) if args.verify else {
        "result": "READY",
        "expression_frames": sum(1 for _ in expression_steps(authority)),
        "components": len(authority.components),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] in {"READY", "PASS_COMPONENT_RECONSTRUCTION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
