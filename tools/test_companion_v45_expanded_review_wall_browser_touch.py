#!/usr/bin/env python3
"""Exercise the V45 expanded wall's mouse path inside a real Edge page."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/expanded-review-wall-01/index.html"
REPORT = ROOT / "docs/validation/companion-v45-expanded-review-wall-browser-touch-20260721.json"
CAPTURE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/expanded-review-wall-01/browser-touch-r1.png"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, default=PREVIEW)
    parser.add_argument("--write", type=Path, default=REPORT)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    args = parser.parse_args()
    preview = args.preview if args.preview.is_absolute() else ROOT / args.preview
    output = args.write if args.write.is_absolute() else ROOT / args.write
    capture = args.capture if args.capture.is_absolute() else ROOT / args.capture
    require(preview.is_file(), f"missing preview: {preview}")
    require(EDGE.is_file(), f"missing Edge: {EDGE}")
    source = preview.read_text(encoding="utf-8")
    require("mousedown" in source and "mousemove" in source and "mouseup" in source,
            "preview has no explicit mouse path")
    probe = r"""
<script>
window.setTimeout(() => {
  const stage = document.querySelector('.epaper-screen');
  const frame = document.querySelector('.frame');
  const gaze = document.querySelector('.gaze');
  const status = document.querySelector('.status');
  const rect = stage.getBoundingClientRect();
  const point = (x, y) => ({bubbles:true, cancelable:true, button:0, clientX:rect.left + rect.width*x, clientY:rect.top + rect.height*y});
  const interact = () => {
    stage.dispatchEvent(new MouseEvent('mousedown', point(.5, .5)));
    stage.dispatchEvent(new MouseEvent('mousemove', point(.82, .28)));
    window.setTimeout(() => {
    const during = {src:frame.src, hidden:frame.hidden, complete:frame.complete, natural_width:frame.naturalWidth,
      gaze_hidden:gaze.hidden, gaze_complete:gaze.complete, gaze_natural_width:gaze.naturalWidth, status:status.textContent};
    stage.dispatchEvent(new MouseEvent('mouseup', point(.82, .28)));
    window.setTimeout(() => {
      const after = {src:frame.src, hidden:frame.hidden, complete:frame.complete, natural_width:frame.naturalWidth,
        gaze_hidden:gaze.hidden, gaze_complete:gaze.complete, gaze_natural_width:gaze.naturalWidth, status:status.textContent};
      const result = {during, after, story_count:document.querySelectorAll('.story').length,
        viewport_count:document.querySelectorAll('[data-canvas="200x200"]').length};
      const node = document.createElement('pre');
      node.id = 'v45-browser-touch-result';
      node.textContent = JSON.stringify(result);
      document.body.appendChild(node);
    }, 450);
    }, 450);
  };
  const waitForVisibleFrame = (deadline) => {
    if (!frame.hidden && frame.complete && frame.naturalWidth === 200) { interact(); return; }
    if (performance.now() >= deadline) { interact(); return; }
    window.setTimeout(() => waitForVisibleFrame(deadline), 50);
  };
  waitForVisibleFrame(performance.now() + 4000);
}, 800);
</script>
"""
    cache_root = ROOT / ".cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="companion-v45-browser-touch-", dir=cache_root) as temp:
        test_page = preview.with_name(".v45-browser-touch-test.html")
        test_page.write_text(source.replace("</body>", probe + "</body>"), encoding="utf-8")
        temp_dir = Path(temp)
        profile = temp_dir / "profile"
        capture.parent.mkdir(parents=True, exist_ok=True)
        capture.unlink(missing_ok=True)
        command = [
            str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--allow-file-access-from-files", "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=6200", "--window-size=1200,6000",
            f"--user-data-dir={profile}", f"--screenshot={capture}",
            "file:///" + str(test_page).replace("\\", "/"),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        require(completed.returncode == 0, f"Edge browser replay failed: {completed.stderr[-500:]}")
        dump = subprocess.run(command[:-2] + ["--dump-dom", command[-1]],
                              capture_output=True, text=True, timeout=30, check=False)
        require(dump.returncode == 0, f"Edge DOM replay failed: {dump.stderr[-500:]}")
        test_page.unlink(missing_ok=True)
    marker = '<pre id="v45-browser-touch-result">'
    start = dump.stdout.find(marker)
    require(start >= 0, "browser replay did not emit its result marker")
    start += len(marker)
    end = dump.stdout.find("</pre>", start)
    require(end > start, "browser replay result is incomplete")
    result = json.loads(html.unescape(dump.stdout[start:end]))
    for phase in ("during", "after"):
        state = result[phase]
        require(state["hidden"] is False and state["complete"] is True and state["natural_width"] == 200,
                f"primary expression frame was not visible during browser mouse {phase}: {state}")
    during = result["during"]
    require(during["gaze_hidden"] is False and during["gaze_complete"] is True and during["gaze_natural_width"] == 200,
            f"registered gaze overlay did not load during browser mouse hold: {during}")
    require(result["story_count"] == 16 and result["viewport_count"] == 16,
            "browser replay wall coverage drifted")
    report = {
        "schema": "companion.v45_expanded_review_wall_browser_touch.v1",
        "status": "PASS_V45_REAL_EDGE_MOUSE_FRAME_REMAINS_VISIBLE",
        "preview": preview.resolve().relative_to(ROOT).as_posix(),
        "capture": capture.resolve().relative_to(ROOT).as_posix(),
        "event_sequence": ["mousedown", "mousemove", "mouseup"],
        "assertions": result,
        "runtime_resource_activated": False,
        "non_claims": ["no_lower_driver_change", "no_physical_panel_acceptance", "no_human_acceptance"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    require(capture.is_file() and capture.stat().st_size > 10000, "browser touch capture is missing or blank")
    print(f"PASS: real Edge mouse replay kept the V45 primary expression visible ({output}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
