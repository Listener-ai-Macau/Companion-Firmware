"""Check the IMU window against preserved board samples; never opens a board interface."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

from imu_operator_feedback import face, live_feedback
from peripheral_diag_uart import write_json_atomic

ROOT = Path(__file__).resolve().parents[1]


def samples(path):
    return [dict(word.split("=", 1) for word in line.split()[1:] if "=" in word)
            for line in path.read_text(encoding="ascii", errors="replace").splitlines()
            if line.startswith("IMU_LIVE ")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--prior-capture", type=Path, required=True)
    parser.add_argument("--before-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    live_path = args.capture.resolve() / "uart.log"
    prior_path = args.prior_capture.resolve() / "uart.log"
    actual = samples(live_path); prior = samples(prior_path)
    tree = ast.parse(args.before_source.read_text(encoding="utf-8-sig"))
    old_face = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "face")
    namespace = {"math": math}
    exec(compile(ast.Module(body=[old_face], type_ignores=[]), str(args.before_source), "exec"), namespace)
    assert actual and prior
    assert all(face(s) == namespace["face"](s) for s in actual + prior), "Static-face classifier changed"
    motion = max(actual, key=lambda s: max(abs(int(s[k])) for k in ("gx", "gy", "gz")))
    tilted = next(s for s in reversed(actual) if face(s) is None and max(abs(int(s[k])) for k in ("gx", "gy", "gz")) < 8000)
    run = []; previous = None; found = None
    for s in prior:
        f = face(s); ms = int(s["ms"])
        if not f or f != found or previous is None or not 0 < ms - previous < 80:
            run = []
        found = f; previous = ms
        if f:
            run.append(s)
            if ms - int(run[0]["ms"]) >= 1600:
                break
    assert run and int(run[-1]["ms"]) - int(run[0]["ms"]) >= 1500
    first_ms = int(run[0]["ms"])
    mid = next(s for s in run if int(s["ms"]) - first_ms >= 700)
    known = {"z-": {"source": str(prior_path)}}
    cases = [
        ("moving", motion, known, face(motion), int(motion["ms"])),
        ("tilted", tilted, known, None, int(tilted["ms"])),
        ("hold", mid, {}, face(mid), first_ms),
        ("recorded", run[-1], {face(run[-1]): {}}, face(run[-1]), first_ms),
    ]
    expected = {name: live_feedback(s, held, f, start) for name, s, held, f, start in cases}
    assert expected["moving"]["imuVisual"]["moving"] is True
    assert "斜放" in expected["tilted"]["status"]
    assert 0 < expected["hold"]["imuVisual"]["holdPercent"] < 100
    assert expected["recorded"]["imuVisual"]["holdPercent"] == 100
    state = {"uiKind": "imu", "title": "Companion 工具修复检查 — 历史数据回放",
             "heading": "窗口修复检查：历史数据回放，无需你操作",
             "instructions": "正在回放刚才的实板数据，依次查看转动、斜放、停稳和已记录提示。\n这个窗口不连接实板，不记录硬件验收通过，稍后自动关闭。",
             "phase": "replay", "canStart": False, "canRespond": False, "showNoSound": False,
             "startLabel": "无需操作", "passLabel": "历史数据", "failLabel": "无需判断",
             "details": f"HOST_UI_REPLAY_NO_BOARD_ACCESS\n新采集：{live_path}\n旧静置数据：{prior_path}"}
    state.update(expected["moving"], renderReceipt="moving")
    write_json_atomic(out / "ui-state.json", state)
    shell = shutil.which("pwsh") or shutil.which("powershell")
    with (out / "stdout.log").open("wb") as stdout, (out / "stderr.log").open("wb") as stderr:
        popup = subprocess.Popen([shell, "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File",
                                  str(ROOT / "tools/show_wba_peripheral_operator.ps1"), "-SessionDirectory", str(out), "-ReplayForAgent"],
                                 cwd=ROOT, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for name, *_ in cases:
                state.update(expected[name], renderReceipt=name)
                write_json_atomic(out / "ui-state.json", state)
                deadline = time.monotonic() + 12
                path = out / f"render-{name}.json"
                while not path.exists():
                    if popup.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError(f"Native window did not render {name}; inspect preserved stderr/render-errors")
                    time.sleep(.1)
                rendered = json.loads(path.read_text(encoding="utf-8-sig"))
                assert rendered["imuLayout"] and rendered["poseVisible"]
                assert rendered["status"] == expected[name]["status"]
                assert rendered["holdValue"] == expected[name]["imuVisual"]["holdPercent"]
                assert (out / f"render-{name}.png").exists()
                time.sleep(.35)
        finally:
            state.update(phase="replay_finished", renderReceipt=None)
            write_json_atomic(out / "ui-state.json", state)
            try:
                popup.wait(timeout=4)
            except subprocess.TimeoutExpired:
                popup.terminate(); popup.wait(timeout=4)
    assert popup.returncode == 0
    assert not (out / "render-errors.log").exists()
    ranges = {k: {"min": min(int(s[k]) for s in actual), "max": max(int(s[k]) for s in actual)}
              for k in ("ax", "ay", "az", "gx", "gy", "gz")}
    result = {"result": "PASS_HOST_IMU_FEEDBACK_REPLAY_ONLY", "finishedAtLocal": datetime.now().isoformat(timespec="milliseconds"),
              "boardAccess": False, "newPhysicalQualification": False,
              "actualSamples": len(actual), "priorSamples": len(prior), "classifierUnchanged": True,
              "captureSha256": hashlib.sha256(live_path.read_bytes()).hexdigest(),
              "priorSha256": hashlib.sha256(prior_path.read_bytes()).hexdigest(), "actualAxisRanges": ranges,
              "nativeWindowCases": expected,
              "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (Path(__file__), ROOT / "tools/imu_operator_feedback.py", ROOT / "tools/show_wba_peripheral_operator.ps1")}}
    write_json_atomic(out / "result.json", result)
    print(json.dumps({"result": result["result"], "output": str(out), "axisRanges": ranges}))


if __name__ == "__main__":
    main()
