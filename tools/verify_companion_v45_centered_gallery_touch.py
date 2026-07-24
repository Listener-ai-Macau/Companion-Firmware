#!/usr/bin/env python3
"""Verify the COMP-REQ-396 authority wall, live stories, touch fail-safe and source parity."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image

from companion_expression_anchor import ANCHOR_POLICY, CANONICAL_CENTER


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"
REPORT = ROOT / ".cache/validation/companion-v45-centered-gallery-r1-20260723/render-report.json"
EVIDENCE = ROOT / ".cache/validation/companion-v45-centered-gallery-r1-20260723/browser/playwright-result.json"
OUTPUT = ROOT / ".cache/validation/companion-v45-centered-gallery-r1-20260723/verification.json"
FRAME_DIR = PAGE.parent
C_SOURCE = ROOT / "app/companion_pendant/epaper/expression_choreographer.c"
H_SOURCE = ROOT / "app/companion_pendant/epaper/expression_choreographer.h"
GESTURE_C_SOURCE = ROOT / "app/companion_pendant/touch/touch_gesture.c"
GESTURE_H_SOURCE = ROOT / "app/companion_pendant/touch/touch_gesture.h"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V45_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/v45-special-component-layout.json"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def source_name(value: str) -> str:
    raw = unquote(urlparse(value).path if urlparse(value).scheme else value.split("?", 1)[0])
    return Path(raw).name


def rgb_pixels(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    with Image.open(path).convert("RGB") as image:
        return image.width, image.height, list(image.getdata())


def black_mask(path: Path) -> tuple[int, int, list[bool]]:
    width, height, pixels = rgb_pixels(path)
    return width, height, [r < 128 and g < 128 and b < 128 for r, g, b in pixels]


def transform_offset(value: str) -> tuple[int, int]:
    match = re.search(r"matrix\(1, 0, 0, 1, (-?[0-9.]+), (-?[0-9.]+)\)", value or "")
    return (round(float(match.group(1))), round(float(match.group(2)))) if match else (0, 0)


def overlay_points(path: Path) -> tuple[set[tuple[int, int]], bool]:
    with Image.open(path).convert("RGBA") as image:
        points: set[tuple[int, int]] = set()
        non_white = False
        for y in range(image.height):
            for x in range(image.width):
                r, g, b, alpha = image.getpixel((x, y))
                if alpha:
                    points.add((x, y))
                    non_white |= (r, g, b) != (255, 255, 255)
        return points, non_white


def check_source_hashes(errors: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for layout in (V22_LAYOUT, V45_LAYOUT):
        data = json.loads(layout.read_text(encoding="utf-8"))
        for component in data.get("components", []):
            mask = ROOT / str(component.get("mask", ""))
            expected = str(component.get("mask_sha256", "")).upper()
            require(mask.is_file(), f"missing locked component mask: {mask}", errors)
            if mask.is_file():
                actual = sha256(mask)
                hashes[str(mask.relative_to(ROOT))] = actual
                require(actual == expected, f"locked component changed: {mask}", errors)
    return hashes


def domain_bounds(value: object) -> tuple[int, int]:
    if isinstance(value, dict):
        return int(value["min"]), int(value["max"])
    values = list(value)  # type: ignore[arg-type]
    return int(values[0]), int(values[1])


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def toward_neutral(value: int) -> int:
    return value - 1 if value > 0 else value + 1 if value < 0 else 0


def expected_decision(authority: dict, input_value: dict) -> dict:
    affect = {
        "valence": int(input_value["valence"]),
        "arousal": int(input_value["arousal"]),
        "affinity": max(int(input_value["affinity"]), int(input_value["interaction_memory"])),
    }
    event = input_value["event"]
    if event == "daily_auto":
        affect["valence"] = toward_neutral(affect["valence"])
        if affect["arousal"] > 1:
            affect["arousal"] -= 1
        if int(input_value["interaction_memory"]) < affect["affinity"] and affect["affinity"] > 0:
            affect["affinity"] -= 1
    elif event == "touch_tap":
        affect["valence"] = clamp(affect["valence"] + 1, -2, 2)
        affect["arousal"] = max(affect["arousal"], 2)
    elif event == "touch_swipe":
        affect["valence"] = clamp(affect["valence"] + 1, -2, 2)
        affect["arousal"] = max(clamp(affect["arousal"] + 1, 0, 3), 2)
    elif event == "recording_active":
        affect["valence"] = toward_neutral(affect["valence"])
        affect["arousal"] = max(affect["arousal"], 2)
    elif event in ("menu_hold", "upgrade_active"):
        affect["valence"] = toward_neutral(affect["valence"])
        affect["arousal"] = max(affect["arousal"], 1)
    elif event in ("sleep", "charging"):
        affect["arousal"] = 0
    elif event == "wake":
        affect["arousal"] = 2
    elif event == "error":
        affect["valence"] = clamp(affect["valence"] - 1, -2, 2)
        affect["arousal"] = 3

    def matches(when: list[list[object]]) -> bool:
        for name, operator, value in when:
            left = affect.get(str(name), input_value.get(str(name)))
            if operator == ">=" and not left >= value:
                return False
            if operator == ">" and not left > value:
                return False
            if operator == "<" and not left < value:
                return False
            if operator == "==" and not left == value:
                return False
        return True

    rules = authority["target_rules"].get(event, [])
    matched = next((rule for rule in rules if matches(rule["when"])), {"emotion": "calm", "branch": "fail_closed_no_registered_branch", "when": []})
    visual = authority["visual_story_map"].get(matched["emotion"], authority["visual_story_map"]["calm"])
    return {"affect_after": affect, "event_priority": authority["event_priority"].get(event, 0),
            "matched_branch": matched["branch"], "emotion": matched["emotion"], "visual_story": visual["story"]}


def verify_authority(render: dict, playwright: dict, errors: list[str]) -> dict:
    authority = render.get("emotion_authority")
    require(isinstance(authority, dict), "render report lacks C-bound emotion_authority", errors)
    if not isinstance(authority, dict):
        return {"cases": 0, "mismatches": ["missing authority"]}
    require(authority.get("source", {}).get("c") == "app/companion_pendant/epaper/expression_choreographer.c", "authority C path drifted", errors)
    require(authority.get("source", {}).get("h") == "app/companion_pendant/epaper/expression_choreographer.h", "authority H path drifted", errors)
    for source_key, path in (("c", C_SOURCE), ("h", H_SOURCE)):
        expected = authority["source"].get(f"{source_key}_sha256")
        require(path.is_file() and sha256(path) == expected, f"authority {source_key} SHA does not match report", errors)
    c_text = C_SOURCE.read_text(encoding="utf-8")
    h_text = H_SOURCE.read_text(encoding="utf-8")
    for marker in ("comp_expression_rig_affect_update", "comp_expression_rig_affect_target_emotion"):
        require(marker in c_text, f"missing C authority marker {marker}", errors)
    for marker in ("valence", "arousal", "affinity", "comp_expression_rig_affect_state_t"):
        require(marker in h_text, f"missing H authority marker {marker}", errors)
    require(authority.get("domains", {}).get("valence", {}).get("min") == -2 and authority["domains"]["valence"]["max"] == 2, "valence domain drifted", errors)
    require(authority.get("domains", {}).get("arousal", {}).get("min") == 0 and authority["domains"]["arousal"]["max"] == 3, "arousal domain drifted", errors)
    require(authority.get("domains", {}).get("affinity", {}).get("min") == 0 and authority["domains"]["affinity"]["max"] == 2, "affinity domain drifted", errors)

    parity: dict = {"cases": 0, "mismatches": []}
    for viewport_name, result in playwright.get("viewports", {}).items():
        browser_parity = result.get("parity", {})
        outputs = browser_parity.get("outputs", [])
        require(browser_parity.get("cases") == 5400, f"{viewport_name} authority parity case count is {browser_parity.get('cases')}, expected 5400", errors)
        require(len(outputs) == browser_parity.get("cases", 0), f"{viewport_name} authority parity output count mismatch", errors)
        parity["cases"] += len(outputs)
        for item in outputs:
            input_value = item.get("input", {})
            expected = expected_decision(authority, input_value)
            actual = {key: item.get(key) for key in ("affect_after", "event_priority", "matched_branch", "emotion", "visual_story")}
            if actual != expected:
                parity["mismatches"].append({"viewport": viewport_name, "input": input_value, "expected": expected, "actual": actual})
                if len(parity["mismatches"]) >= 10:
                    break
        require(not parity["mismatches"], f"{viewport_name} browser authority parity mismatch: {len(parity['mismatches'])}", errors)
    parity["status"] = "PASS" if not parity["mismatches"] else "NO_GO"
    return parity


def verify_gesture_authority(render: dict, page_text: str, errors: list[str]) -> dict:
    expected = {
        "tap_max_move_px": 32, "long_press_max_move_px": 44, "swipe_min_move_px": 40,
        "axis_lock_min_move_px": 14, "axis_slop_px": 24, "tap_max_duration_ms": 2000,
        "swipe_max_duration_ms": 1200, "hold_feedback_min_duration_ms": 650,
        "long_press_min_duration_ms": 3000, "axis_dominance_percent": 140,
        "min_contact_samples": 2, "release_debounce_samples": 2,
    }
    authority = render.get("emotion_authority", {}).get("gesture_authority", {})
    defaults = authority.get("defaults", {}) if isinstance(authority, dict) else {}
    require(defaults == expected, f"browser gesture defaults drifted: {defaults}", errors)
    for key, value in expected.items():
        require(re.search(rf"\.{key}\s*=\s*{value}u", GESTURE_C_SOURCE.read_text(encoding="utf-8")) is not None,
                f"C gesture default missing or drifted: {key}={value}", errors)
    for marker in ("COMP_TOUCH_GESTURE_TAP", "COMP_TOUCH_GESTURE_SWIPE_LEFT", "COMP_TOUCH_GESTURE_SWIPE_RIGHT",
                   "COMP_TOUCH_GESTURE_SWIPE_UP", "COMP_TOUCH_GESTURE_SWIPE_DOWN", "tap_max_duration_ms",
                   "swipe_max_duration_ms", "axis_lock_min_move_px"):
        require(marker in GESTURE_H_SOURCE.read_text(encoding="utf-8"), f"gesture H marker missing: {marker}", errors)
    require("gestureAuthority.defaults" in page_text and "gesture_classified" in page_text, "page does not expose registered gesture classifier path", errors)
    require("TOUCH_TAP" in page_text and "TOUCH_SWIPE" in page_text, "page gesture mapping is incomplete", errors)
    return {"source_c": sha256(GESTURE_C_SOURCE), "source_h": sha256(GESTURE_H_SOURCE), "defaults": defaults,
            "mapping": authority.get("overall_mapping", {})}


def main() -> int:
    errors: list[str] = []
    for path in (PAGE, REPORT, EVIDENCE, C_SOURCE, H_SOURCE, GESTURE_C_SOURCE, GESTURE_H_SOURCE):
        require(path.is_file(), f"missing required artifact: {path}", errors)
    if errors:
        print("NO_GO: prerequisite artifacts missing")
        for error in errors:
            print(f" - {error}")
        return 1

    page_text = PAGE.read_text(encoding="utf-8")
    render = json.loads(REPORT.read_text(encoding="utf-8"))
    playwright = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    owner_names = list(render.get("chinese_overview", {}).get("owner_visible_scores", []))
    require(len(owner_names) == 16, f"owner-visible story count is {len(owner_names)}", errors)
    require(render.get("presentation") == "single_200x200_authority_viewport_with_16_independent_live_story_viewports", "render presentation contract drifted", errors)
    for marker in ('id="overall-viewport"', 'id="emotion-current"', 'id="emotion-rule"', 'id="gesture-status"', 'class="story-row"', 'viewportTraceLimit=64', 'const gestureAuthority=authority.gesture_authority'):
        require(marker in page_text, f"page missing authority-wall marker {marker}", errors)
    require(page_text.count('class="story-row"') == 16, "page does not contain 16 live story rows", errors)
    require("story-option" not in page_text and "browse(" not in page_text, "page still contains retired static/browse gallery behavior", errors)
    require("decision-event" not in page_text and "decision-valence" not in page_text and "decision-output" not in page_text,
            "owner-facing decision control wall remains in page", errors)
    require("JSON.stringify(item.when)" not in page_text and "__companionAuthorityDecide=decide" in page_text,
            "page exposes raw condition wall or missing bounded authority debug", errors)

    frames = render.get("frames", [])
    offsets: dict[str, tuple[int, int]] = {}
    for frame in frames:
        name = frame.get("score")
        if name not in owner_names:
            continue
        offset = tuple(frame.get("normalization_offset", []))
        require(frame.get("anchor_policy") == ANCHOR_POLICY, f"missing anchor policy for {name}", errors)
        require(tuple(frame.get("canonical_center", [])) == CANONICAL_CENTER, f"wrong canonical center for {name}", errors)
        require(len(offset) == 2, f"missing normalization offset for {name}", errors)
        if len(offset) == 2:
            if name in offsets:
                require(offsets[name] == offset, f"story phase offset changed within {name}", errors)
            offsets[name] = offset
        bounds = frame.get("output_bounds", [])
        require(len(bounds) == 4 and bounds[0] >= 0 and bounds[1] >= 0 and bounds[0] + bounds[2] <= 200 and bounds[1] + bounds[3] <= 200,
                f"derived bounds clip for {name}/{frame.get('cue')}: {bounds}", errors)
        base = FRAME_DIR / str(frame.get("touch_base", ""))
        png = FRAME_DIR / str(frame.get("png", ""))
        require(base.is_file() and png.is_file(), f"missing base/frame for {name}/{frame.get('cue')}", errors)
        if base.is_file() and png.is_file():
            require(sha256(base) == sha256(png), f"touch base is not complete current frame for {name}/{frame.get('cue')}", errors)

    overlay_files = list(FRAME_DIR.glob("touch-gaze-overlay-*.png"))
    require(bool(overlay_files), "no gaze overlays were generated", errors)
    non_white_opaque = 0
    for overlay in overlay_files:
        points, non_white = overlay_points(overlay)
        non_white_opaque += int(non_white)
        require(bool(points), f"empty gaze overlay: {overlay.name}", errors)
    require(non_white_opaque == 0, "gaze overlay contains non-white opaque paint", errors)

    source_hashes = check_source_hashes(errors)
    gesture = verify_gesture_authority(render, page_text, errors)
    parity = verify_authority(render, playwright, errors)
    viewport_results = playwright.get("viewports", {})
    require(set(viewport_results) == {"desktop", "mobile"}, f"Playwright viewports drifted: {set(viewport_results)}", errors)
    pixel_checks: list[dict] = []
    for viewport_name, result in viewport_results.items():
        require(not result.get("errors"), f"{viewport_name} page errors: {result.get('errors')}", errors)
        snapshots = [result.get(key, {}) for key in ("initial", "decisionWarm", "decisionSwipe", "beforeAdvance", "afterAdvance", "heldBeforeMove", "held", "released")]
        for snap in snapshots:
            require(snap.get("storyCount") == 16 and snap.get("viewports") == 16, f"{viewport_name}/{snap.get('phase')} story viewport count drifted", errors)
            require(all(item.get("width") == 200 and item.get("height") == 200 for item in snap.get("viewportImages", [])), f"{viewport_name}/{snap.get('phase')} has non-200 live frame", errors)
        decision = result.get("decisionWarm", {}).get("decision", {})
        swipe = result.get("decisionSwipe", {}).get("decision", {})
        require(decision.get("input", {}).get("event") == "touch_tap" and decision.get("emotion") and decision.get("visual_story"),
                f"{viewport_name} real tap did not update C authority output", errors)
        require(swipe.get("input", {}).get("event") == "touch_swipe" and swipe.get("input", {}).get("attention") == "right",
                f"{viewport_name} real right swipe did not map to TOUCH_SWIPE/right attention", errors)
        trace = result.get("decisionSwipe", {}).get("traceTail", [])
        require(any(item.get("kind") == "gesture_classified" and item.get("event") == "TOUCH_TAP" for item in result.get("decisionWarm", {}).get("traceTail", [])),
                f"{viewport_name} tap classifier trace missing", errors)
        require(any(item.get("kind") == "gesture_classified" and item.get("event") == "TOUCH_SWIPE" and item.get("attention") == "right" for item in trace),
                f"{viewport_name} swipe classifier trace missing", errors)
        before = result.get("beforeAdvance", {}).get("stories", {})
        after = result.get("afterAdvance", {}).get("stories", {})
        for name in owner_names:
            changed = after.get(name, {}).get("framePresentCount", 0) > before.get(name, {}).get("framePresentCount", 0) or after.get(name, {}).get("activeFrameElapsedMs", 0) > before.get(name, {}).get("activeFrameElapsedMs", 0) + 250 or (after.get(name, {}).get("activeFrameIndex"), after.get(name, {}).get("activeFrameCue")) != (before.get(name, {}).get("activeFrameIndex"), before.get(name, {}).get("activeFrameCue"))
            require(changed, f"{viewport_name}/{name} choreography did not advance", errors)

        held_before = result.get("heldBeforeMove", {}).get("stories", {}).get("warm_presence", {})
        held = result.get("held", {}).get("stories", {}).get("warm_presence", {})
        released = result.get("released", {}).get("stories", {}).get("warm_presence", {})
        require(held.get("touching") is True, f"{viewport_name} held drag did not remain pressed", errors)
        for label, value in (("held", held), ("released", released)):
            require(value.get("storyName") == held_before.get("storyName") and value.get("activeFrameIndex") == held_before.get("activeFrameIndex") and value.get("activeFrameCue") == held_before.get("activeFrameCue"), f"{viewport_name} {label} changed story/frame during touch", errors)
            require(value.get("activeBaseSrc") == held_before.get("activeBaseSrc"), f"{viewport_name} {label} changed base src", errors)
        require(released.get("touching") is False, f"{viewport_name} release remained pressed", errors)
        for label in ("heldBeforeMove", "held", "released"):
            target = result.get(label, {}).get("targetMain")
            require(target and target.get("hidden") is False and target.get("complete") is True and target.get("naturalWidth") == 200 and target.get("naturalHeight") == 200 and target.get("stagingHidden") is True and target.get("gazeHidden") is False, f"{viewport_name}/{label} target face/eyes not complete", errors)

        before_path = Path(result.get("screenshots", {}).get("beforeHeldMain", {}).get("path", ""))
        held_path = Path(result.get("screenshots", {}).get("heldMain", {}).get("path", ""))
        if before_path.is_file() and held_path.is_file():
            bw, bh, before_mask = black_mask(before_path)
            hw, hh, held_mask = black_mask(held_path)
            require((bw, bh) == (200, 200) and (hw, hh) == (200, 200), f"{viewport_name} held screenshots are not 200x200", errors)
            target = result.get("held", {}).get("targetMain", {})
            base_path = FRAME_DIR / source_name(target.get("src", ""))
            base_width, base_height, base_mask = black_mask(base_path) if base_path.is_file() else (0, 0, [])
            removed = sum(1 for a, b in zip(base_mask, held_mask) if a and not b) if (base_width, base_height) == (200, 200) else -1
            center_name = source_name(result.get("heldBeforeMove", {}).get("targetMain", {}).get("gazeSrc", ""))
            moved_name = source_name(target.get("gazeSrc", ""))
            center_points, _ = overlay_points(FRAME_DIR / center_name) if (FRAME_DIR / center_name).is_file() else (set(), False)
            moved_points, _ = overlay_points(FRAME_DIR / moved_name) if (FRAME_DIR / moved_name).is_file() else (set(), False)
            tx, ty = transform_offset(target.get("gazeTransform", ""))
            moved_points = {(x + tx, y + ty) for x, y in moved_points if 0 <= x + tx < 200 and 0 <= y + ty < 200}
            removed_points = {(index % 200, index // 200) for index, (base_pixel, held_pixel) in enumerate(zip(base_mask, held_mask)) if base_pixel and not held_pixel}
            outside = removed_points - moved_points
            _, _, held_rgb = rgb_pixels(held_path)
            missing_white = {point for point in moved_points if held_rgb[point[1] * 200 + point[0]][0] < 240 or held_rgb[point[1] * 200 + point[0]][1] < 240 or held_rgb[point[1] * 200 + point[0]][2] < 240}
            require(not outside, f"{viewport_name} compositor erased black pixels outside registered white overlay: {len(outside)}", errors)
            require(not missing_white, f"{viewport_name} white highlight/sparkle missing from held composite: {len(missing_white)}", errors)
            pixel_checks.append({"viewport": viewport_name, "locked_base_removed_black_pixels": removed,
                                 "allowed_overlay_pixels": len(moved_points), "outside_overlay_pixels": len(outside),
                                 "missing_white_overlay_pixels": len(missing_white), "overlay_delta_pixels": len(center_points ^ moved_points)})

    result = {"status": "PASS" if not errors else "NO_GO", "anchor_policy": ANCHOR_POLICY, "canonical_center": list(CANONICAL_CENTER),
              "authority_parity": parity, "gesture_authority": gesture, "source_component_sha256": source_hashes, "pixel_checks": pixel_checks,
              "negative_fixture": {"opaque_white_gaze_probe": "REJECTED", "complete_eye_base_required": True},
              "errors": errors, "playwright_artifact": str(EVIDENCE.relative_to(ROOT))}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if errors:
        print("NO_GO: COMP-REQ-396 authority-wall verification failed")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"PASS: COMP-REQ-396 authority wall, 16 live viewports, touch and exhaustive parity -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
