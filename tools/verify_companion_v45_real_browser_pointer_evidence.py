#!/usr/bin/env python3
"""Verify r7 real Edge pointer phases with source-backed viewport pixels."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/validation/companion-v45-browser-pointer-fail-safe-20260721.json"
RAW_REPORT = ROOT / ".cache/v45-browser-pointer-fail-safe-playwright.json"
FRAME_DIR = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01"
REVISION = "v45-touch-failsafe-r7-20260721"
BLINK_CUES = {"calm_blink_closing", "calm_blink_closed", "calm_blink_opening"}
SCREENSHOTS = {
    ("single", "press"): "docs/validation/companion-v45-real-browser-touch-press-20260721.png",
    ("single", "drag"): "docs/validation/companion-v45-real-browser-touch-drag-20260721.png",
    ("single", "release"): "docs/validation/companion-v45-real-browser-touch-release-20260721.png",
    ("expanded-first-story", "press"): "docs/validation/companion-v45-expanded-real-browser-touch-press-20260721.png",
    ("expanded-first-story", "drag"): "docs/validation/companion-v45-expanded-real-browser-touch-drag-20260721.png",
    ("expanded-first-story", "release"): "docs/validation/companion-v45-expanded-real-browser-touch-release-20260721.png",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def source_name(url: str) -> str:
    parsed = urlparse(url)
    value = unquote(parsed.path if parsed.scheme else url.split("?", 1)[0])
    return Path(value).name


def source_black_pixels(base_name: str, overlay_name: str) -> int:
    base_path = FRAME_DIR / base_name
    overlay_path = FRAME_DIR / overlay_name
    require(base_path.is_file(), f"primary source image is missing: {base_name}")
    require(overlay_path.is_file(), f"gaze source image is missing: {overlay_name}")
    with Image.open(base_path) as base, Image.open(overlay_path) as overlay:
        require(base.size == (200, 200) and overlay.size == (200, 200),
                "source-backed pointer layers are not native 200x200")
        composite = Image.alpha_composite(base.convert("RGBA"), overlay.convert("RGBA")).convert("RGB")
        return sum(1 for red, green, blue in composite.getdata()
                   if red < 128 and green < 128 and blue < 128)


def phase_state(result: dict, phase: str) -> dict:
    value = result.get(phase)
    require(isinstance(value, dict) and isinstance(value.get("state"), dict),
            f"Playwright phase state is missing: {phase}")
    state = value["state"]
    require(state.get("revision") == REVISION and state.get("page_review") == REVISION,
            f"{phase} did not use the cache-busted r7 page")
    require(state.get("active_frame_cue") not in BLINK_CUES,
            f"{phase} selected a pointer-triggered blink cue: {state.get('active_frame_cue')}")
    require(state.get("primary_hidden") is False and state.get("primary_src"),
            f"{phase} primary expression image is not visible: {state}")
    require(state.get("gaze_hidden_dom") is False and state.get("gaze_src"),
            f"{phase} gaze overlay did not render: {state}")
    return state


def read_playwright_results() -> dict[str, dict]:
    require(RAW_REPORT.is_file(), f"Playwright raw report is missing: {RAW_REPORT}")
    raw = json.loads(RAW_REPORT.read_text(encoding="utf-8"))
    require(raw.get("errors") == [] and raw.get("stats", {}).get("unexpected") == 0 and
            raw.get("stats", {}).get("expected") == 2,
            "Playwright Edge pointer replay did not complete cleanly")
    suites = raw.get("suites", [])
    require(len(suites) == 1 and len(suites[0].get("specs", [])) == 2,
            "Playwright pointer suite coverage drifted")
    results: dict[str, dict] = {}
    for spec in suites[0]["specs"]:
        require(spec.get("ok") is True, f"Playwright spec failed: {spec.get('title')}")
        stdout = spec["tests"][0]["results"][0].get("stdout", [])
        require(stdout and stdout[0].get("text"), f"Playwright spec did not emit phase evidence: {spec.get('title')}")
        evidence = json.loads(stdout[0]["text"])
        results[str(evidence["viewport"])] = evidence
    require(set(results) == {"single", "expanded-first-story"}, "Playwright viewport evidence is incomplete")
    return results


def main() -> int:
    playwright = read_playwright_results()
    screenshot_results = []
    for (viewport, phase), relative in SCREENSHOTS.items():
        path = ROOT / relative
        require(path.is_file(), f"real browser pointer screenshot is missing: {relative}")
        state = phase_state(playwright[viewport], phase)
        with Image.open(path) as opened:
            image = opened.convert("RGB")
            require(image.width >= 200 and image.height >= 200,
                    f"real browser screenshot is smaller than 200x200: {relative}")
            margin = 3 if image.width >= 400 else 2
            viewport_image = image.crop((margin, margin, image.width - margin, image.height - margin))
            black = sum(1 for red, green, blue in viewport_image.getdata()
                        if red < 128 and green < 128 and blue < 128)
            nonwhite = sum(1 for red, green, blue in viewport_image.getdata()
                           if min(red, green, blue) < 250)
            require(black >= 500 and nonwhite >= black and nonwhite < viewport_image.width * viewport_image.height,
                    f"{relative} is blank or pure white: black={black}, nonwhite={nonwhite}")
            base_name = source_name(str(state["primary_src"]))
            overlay_name = source_name(str(state["gaze_src"]))
            expected_black = source_black_pixels(base_name, overlay_name)
            require(expected_black >= 500,
                    f"{relative} does not have a source-backed black face layer: {base_name}/{overlay_name}")
            screenshot_results.append({
                "viewport": viewport,
                "phase": phase,
                "path": relative,
                "width": image.width,
                "height": image.height,
                "viewport_width": viewport_image.width,
                "viewport_height": viewport_image.height,
                "black_pixel_count": black,
                "nonwhite_pixel_count": nonwhite,
                "viewport_area": viewport_image.width * viewport_image.height,
                "black_pixel_ratio": round(black / (viewport_image.width * viewport_image.height), 6),
                "source_primary": base_name,
                "source_gaze_overlay": overlay_name,
                "source_composite_black_pixel_count": expected_black,
                "active_frame_cue": state["active_frame_cue"],
                "active_frame_index": state["active_frame_index"],
                "story_index": state["story_index"],
            })

    for viewport, evidence in playwright.items():
        before = phase_state(evidence, "before")
        press = phase_state(evidence, "press")
        drag = phase_state(evidence, "drag")
        release = phase_state(evidence, "release")
        for phase in ("press", "drag", "release"):
            current = {"press": press, "drag": drag, "release": release}[phase]
            require(current["story_index"] == before["story_index"] and
                    current["active_frame_index"] == before["active_frame_index"] and
                    current["active_frame_cue"] == before["active_frame_cue"] and
                    current["primary_src"] == before["primary_src"],
                    f"{viewport} {phase} changed the frozen story frame or primary face")
        release_events = [item for item in evidence["release"]["trace"] if item.get("kind") == "touch_release"]
        require(release_events and release_events[-1].get("frame_cue") == before["active_frame_cue"] and
                release_events[-1].get("story_index") == before["story_index"] and
                release_events[-1].get("resume_delay_ms", 0) >= 180,
                f"{viewport} release did not resume the current frame with a protected delay")
        require(len({press["gaze_src"], drag["gaze_src"], release["gaze_src"]}) >= 2,
                f"{viewport} press/drag did not produce the registered gaze interaction")

    output = {
        "schema": "companion.v45.real_browser_pointer_fail_safe.v3",
        "status": "PASS_V45_REAL_BROWSER_POINTER_FAIL_SAFE_RUNTIME_INACTIVE",
        "review_revision": REVISION,
        "runner": "Playwright Edge via tools/v45-click.spec.js",
        "raw_report": RAW_REPORT.resolve().relative_to(ROOT).as_posix(),
        "input_sequence": ["fresh_page", "cache_busted_url", "mouse_down", "mouse_drag", "mouse_up"],
        "screen_count": len(screenshot_results),
        "screenshots": screenshot_results,
        "behavior_assertions": {
            "press_drag_release_primary_face_visible": True,
            "press_drag_not_blink_transition": True,
            "release_same_story_and_frame": True,
            "release_resume_delay_ms_at_least": 180,
            "primary_face_resource_frozen_during_touch": True,
            "gaze_overlay_interaction_present": True,
        },
        "runtime_resource_activated": False,
        "non_claims": ["no_lower_driver_change", "no_physical_panel_acceptance", "no_human_acceptance"],
    }
    REPORT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: verified six real-browser r7 200x200 touch screenshots, source pixels, frozen cues and release delay ({REPORT}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
