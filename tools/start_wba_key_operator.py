"""Open the physical key window and start its monitor together."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_path = args.build.resolve()
    build = json.loads(build_path.read_text(encoding="utf-8-sig"))
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    state = {
        "phase": "preparing", "status": "正在启动连接和同步监控，请稍候……", "color": "orange",
        "instructions": "等窗口显示绿色【正在采集】后，再短按并完全松开实体键 3 次。每次间隔约 1～2 秒，没有倒计时。",
        "presses": 0, "releases": 0, "keyState": "等待有效数据", "lastEvent": "尚未收到",
        "canConnect": False, "canFinish": False, "canReportProblem": False,
        "details": "诊断包：" + str(build_path) + "\nbin SHA256：" + build.get("imageSha256", "未知")
                   + "\nUID：180010000d50335754363720\n结果目录：" + str(out)
                   + "\n身份仅用于追溯，无需据此判断是否通过。",
    }
    save(out / "ui-state.json", state)
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        raise RuntimeError("PowerShell is unavailable")
    with (out / "popup-stdout.log").open("wb") as stdout, (out / "popup-stderr.log").open("wb") as stderr:
        popup = subprocess.Popen([shell, "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File",
                                  str(ROOT / "tools/show_wba_key_operator.ps1"), "-SessionDirectory", str(out)],
                                 cwd=ROOT, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
    metadata = {"output": str(out), "popupPid": popup.pid, "build": str(build_path)}
    save(out / "session.json", metadata)
    deadline = time.monotonic() + 15
    while not (out / "popup-ready.json").exists():
        if popup.poll() is not None or time.monotonic() >= deadline:
            raise RuntimeError("Operator window did not show; see popup-stderr.log")
        time.sleep(.1)
    with (out / "monitor-stdout.log").open("wb") as stdout, (out / "monitor-stderr.log").open("wb") as stderr:
        monitor = subprocess.Popen([sys.executable, str(ROOT / "tools/run_wba_key_operator.py"), "--session", str(out)],
                                   cwd=ROOT, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
    metadata.update(monitorPid=monitor.pid, startedAtLocal=datetime.now().isoformat(timespec="milliseconds"))
    save(out / "session.json", metadata)
    print(json.dumps(metadata, ensure_ascii=False), flush=True)
    exit_code = monitor.wait()
    if popup.poll() is None:
        state = json.loads((out / "ui-state.json").read_text(encoding="utf-8-sig"))
        state.update(phase="monitor-stopped", status="同步监控已停止，请先不用按键；已有记录已保存", color="red",
                     canConnect=False, canFinish=False, canReportProblem=False)
        save(out / "ui-state.json", state)
    print("KEY_POPUP_MONITOR_ENDED exit=" + str(exit_code), flush=True)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
