"""Run one interactive key inspection with a live native operator window.

The window is started separately and its PID is in session.json. Each Connect
click authorizes one guarded connection attempt. Only a ready capture enables
physical key instructions; failed connections never become key-failure evidence.
"""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import serial
from serial.tools import list_ports
from capture_wba_peripheral_diag import ROOT, SN, UID, values
from diagnose_wba_uart import parse_frames

OWNER = "01a11ba8-9629-7350-976b-fd50a1045a76"


def now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    args = parser.parse_args()
    out = args.session.resolve()
    metadata = read_json(out / "session.json")
    if not metadata or not (out / "popup-ready.json").is_file():
        raise RuntimeError("Visible operator window has not started")
    build_path = Path(metadata["build"])
    ui_path = out / "ui-state.json"
    board = ROOT.parent / "docs/board_operations.md"
    state = read_json(ui_path)
    capture = None
    live = None
    attempt = 0
    action_offset = 0
    owner_action = None
    current_lease_token = ""
    phase = "preparing"
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]

    def ui_alive() -> bool:
        handle = kernel.OpenProcess(0x1000, False, int(metadata["popupPid"]))
        if not handle:
            return False
        code = wintypes.DWORD()
        try:
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)

    def update(new_phase: str, status: str, color="orange", **extra) -> None:
        nonlocal phase
        phase = new_phase
        state.update(phase=phase, status=status, color=color, updatedAtLocal=now(), **extra)
        write_json(ui_path, state)

    def active_rows(text: str) -> list[str]:
        section = text.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]
        return [line for line in section.splitlines() if "**占用中**" in line]

    def acquire(token: str) -> None:
        nonlocal current_lease_token
        text = board.read_text(encoding="utf-8-sig")
        active = active_rows(text)
        if active:
            raise RuntimeError("实板正由其他阶段占用，请等待释放：" + active[0])
        row = (f"- **占用中**：Companion 硬件功能检查（{OWNER}，{now()}，"
               f"peripheral-ram-diag/{out.name}/{token}）。Owner要求原生弹窗同步监控，只检查按键；"
               "有效身份/实际采集运行后才提示按，保留旧ARM事件。窗口完成或停止后关闭句柄并恢复正式产品。")
        board.write_text(text.replace("## 当前占用\n", "## 当前占用\n\n" + row + "\n", 1), encoding="utf-8-sig")
        current_lease_token = token

    def release(note: str) -> None:
        text = board.read_text(encoding="utf-8-sig")
        owned = [line for line in active_rows(text) if OWNER in line and out.name in line
                 and current_lease_token in line]
        if len(owned) == 1:
            replacement = owned[0].replace("**占用中**", "**已释放**", 1)
            replacement += "；" + now() + " " + note + "；证据 " + out.relative_to(ROOT.parent).as_posix() + "。"
            board.write_text(text.replace(owned[0], replacement, 1), encoding="utf-8-sig")

    def run_tool(name: str, arguments: list[str], folder: Path) -> subprocess.CompletedProcess:
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "host-stdout.log").open("wb") as stdout, (folder / "host-stderr.log").open("wb") as stderr:
            return subprocess.run([sys.executable, str(ROOT / "tools" / name), *arguments],
                                  cwd=ROOT, stdout=stdout, stderr=stderr)

    def entry(folder: Path) -> dict:
        raw = bytearray()
        result = {"startedAtLocal": now(), "peripheralCommandsIssued": 0, "resetIssued": False}
        try:
            ports = [p.device for p in list_ports.comports() if p.serial_number == SN]
            if len(ports) != 1:
                raise RuntimeError("固定V3串口映射不唯一")
            link = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=1,
                                 rtscts=False, dsrdtr=False, xonxoff=False)
            link.dtr = link.rts = False
            link.port = ports[0]
            with link:
                link.write(b"\nHELLO\n?\n")
                link.flush()
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    raw.extend(link.read(min(max(link.in_waiting, 1), 4096)))
                    for line in raw.decode("ascii", errors="replace").splitlines():
                        marker = "HELLO id=COMP_PERIPH_RAM_V1 "
                        if marker in line:
                            hello = values(line[line.index(marker):])
                            if (hello.get("uid") != UID or hello.get("device") != "492"
                                    or hello.get("flash_kib") != "512" or hello.get("target_ok") != "1"):
                                raise RuntimeError("诊断目标身份不符")
                            result.update(result="DIAGNOSTIC_AVAILABLE", hello=hello)
                            return result
                    frames, _ = parse_frames(bytes(raw))
                    if frames:
                        identity = frames[-1]["sections"]["ID"]
                        if identity["uid"] != UID or identity["ui"] != 67:
                            raise RuntimeError("正式产品目标身份不符")
                        result.update(result="PRODUCT_AVAILABLE", snapshot=frames[-1])
                        return result
            result["result"] = "NO_TARGET_RESPONSE"
            return result
        finally:
            result.update(uartClosed=True, uartBytes=len(raw), finishedAtLocal=now())
            (folder / "entry-uart.log").write_bytes(raw)
            write_json(folder / "entry.json", result)

    def counts(report: dict) -> tuple[int, int, str, str]:
        baseline = report.get("baselineKeyStatus", {})
        status = report.get("lastKeyStatus", {})
        baseline_events = int(baseline.get("events", 0))
        fresh = [e for e in report.get("events", []) if int(e["index"]) >= baseline_events]
        presses = max(0, int(status.get("presses", 0)) - int(baseline.get("presses", 0)),
                      sum(int(e["pressed"]) == 1 for e in fresh))
        releases = max(0, int(status.get("releases", 0)) - int(baseline.get("releases", 0)),
                       sum(int(e["pressed"]) == 0 for e in fresh))
        pressed = fresh[-1]["pressed"] == "1" if fresh else status.get("stable") == "0"
        last = fresh[-1]["hostReceivedAtLocal"] if fresh else "尚未收到本轮变化"
        return presses, releases, "按下" if pressed else "松开", last

    def save_owner(result: str, report: dict | None = None) -> None:
        actions_file = out / "operator-actions.jsonl"
        actions = [json.loads(line) for line in actions_file.read_text(encoding="utf-8-sig").splitlines()
                   if line.strip()] if actions_file.exists() else []
        evidence = {"result": result, "atLocal": now(), "ownerAction": owner_action,
                    "operatorActions": actions,
                    "capture": report, "build": str(build_path), "boardUid": UID,
                    "packageSha256": read_json(build_path, {}).get("imageSha256"),
                    "session": str(out)}
        write_json(out / "owner-result.json", evidence)
        (out / "owner-result.txt").write_text(result + "\n" + json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def restore() -> None:
        # Only after a completed KEY_STOP. The live tool has closed UART and the
        # lease stays with this stage until the normal product identity returns.
        folder = out / f"return-product-{attempt:02d}"
        run_tool("capture_wba_peripheral_diag.py", ["--command", "RESET", "--lead-in-seconds", "0",
                 "--output", str(folder / "capture")], folder)
        restored = read_json(folder / "capture/result.json", {})
        state["productRestored"] = restored.get("result") == "PRODUCT_UART_IDENTITY_RESTORED_PERIPHERAL_QUALIFICATION_UNCHANGED"

    def connect_once() -> None:
        nonlocal capture, live, attempt, build_path
        if capture is not None:
            return
        attempt += 1
        folder = out / f"attempt-{attempt:02d}"
        folder.mkdir()
        live = folder / (out.name + f"-live-{attempt:02d}")
        update("connecting", "正在连接主板，请先不要按键", canConnect=False, canFinish=False,
               canReportProblem=False, presses=0, releases=0, keyState="等待有效数据", lastEvent="尚未收到")
        try:
            acquire(live.name)
            current = entry(folder)
            if not ui_alive():
                release("窗口已关闭，UART已实际关闭，无SWD/BLE或写板")
                return
            if current["result"] == "NO_TARGET_RESPONSE":
                raise RuntimeError("主板没有回应，尚未启动采集。供电/连接恢复后再点重试。")
            if current["result"] == "PRODUCT_AVAILABLE":
                update("preparing", "主板已回应，正在准备按键采集，请先不要按", canConnect=False)
                build = read_json(build_path)
                if (not build or any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha
                                     for name, sha in build["sources"].items())):
                    candidate = folder / "ram-diag"
                    run_tool("build_wba_peripheral_diag.py", ["--output", str(candidate)], folder / "build-host")
                    build_path = candidate / "build.json"
                    if read_json(build_path, {}).get("result") != "BUILT_NOT_RUN":
                        raise RuntimeError("按键检测程序构建未完成，未写板")
                load = folder / "ram-load"
                run_tool("load_wba_peripheral_diag.py", ["--build", str(build_path), "--output", str(load)], folder / "load-host")
                receipt = read_json(load / "result.json", {})
                if receipt.get("result") != "SRAM_DIAGNOSTIC_RUNNING_PERIPHERALS_UNTESTED":
                    raise RuntimeError("按键检测未能在主板上启动，当前不能操作；详细原文已保存")
            if not ui_alive():
                restore()
                release("窗口关闭，准备进程均退出；恢复结果见本目录，所有实际句柄已关闭")
                return
            state["details"] = ("本次只检查实体按键。\n诊断包：" + str(build_path)
                                + "\nbin SHA256：" + read_json(build_path, {}).get("imageSha256", "未知")
                                + "\nUID：" + UID + "\n结果目录：" + str(out)
                                + "\n身份仅用于追溯，无需据此判断是否通过。")
            log = (folder / "live-stdout.log").open("wb")
            err = (folder / "live-stderr.log").open("wb")
            try:
                capture = subprocess.Popen([sys.executable, str(ROOT / "tools/capture_wba_key_live.py"),
                                            "--output", str(live)], cwd=ROOT, stdout=log, stderr=err)
            finally:
                log.close(); err.close()
            update("preparing", "正在确认持续采集已启动，请稍候", canConnect=False, canFinish=False)
        except Exception as error:
            release("本次连接/准备已结束，实际UART/准备进程已关闭；未判按键好坏")
            update("unavailable", str(error), "red", canConnect=True, canFinish=False,
                   canReportProblem=False, instructions="先不用按键。待主板供电和调试连接恢复后，点击左下方重试；每次点击只尝试一次。")
            save_owner("UNDETERMINED_CAPTURE_NOT_STARTED")
            print("KEY_POPUP_TARGET_UNAVAILABLE " + str(error), flush=True)

    def finish(action: dict, closing=False) -> None:
        nonlocal capture, owner_action
        owner_action = action
        update("finishing", "正在保存并核对本轮记录", canConnect=False, canFinish=False, canReportProblem=False)
        report = read_json(live / "result.json", {}) if live else {}
        if capture is not None:
            if capture.poll() is None:
                (live / "stop.request").write_text("operator finished\n", encoding="utf-8")
                try:
                    capture.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    capture.terminate()
                    capture.wait(timeout=5)
            report = read_json(live / "result.json", report)
            capture = None
        normal_stop = report.get("result") == "KEY_LIVE_CAPTURE_STOPPED_OWNER_ACTION_REVIEW_REQUIRED"
        presses, releases, key_state, last = counts(report)
        status = report.get("lastKeyStatus", {})
        baseline = report.get("baselineKeyStatus", {})
        passed = (action.get("action") == "done" and normal_stop and presses >= 3
                  and releases >= 3 and presses == releases and status.get("stable") == "1"
                  and baseline.get("stable") == "1")
        result = ("PASS_KEY_THREE_PRESS_RELEASE" if passed else
                  "CANCELLED_BY_OPERATOR" if closing else
                  "FAILED_KEY_RESPONSE_REQUIRES_DEBUG" if normal_stop else
                  "UNDETERMINED_CAPTURE_INTERRUPTED")
        save_owner(result, report)
        if normal_stop:
            restore()
        release("采集/准备/恢复进程已退出，UART/SWD句柄实际关闭，无BLE；正式产品恢复结果见记录")
        update("finished" if normal_stop else "interrupted",
               "通过：已记录三次完整按下和松开" if passed else
               "本轮已保存：需要继续定位按键响应" if normal_stop else
               "状态查询超时；已收到的按键记录已保存" if report.get("failureKind") == "RESPONSE_TIMEOUT" else
               "采集未完成，本轮结果未能判定；已收到的记录已保存",
               "green" if passed else "red", presses=presses, releases=releases,
               keyState=key_state, lastEvent=last, canConnect=not normal_stop and not closing,
               canFinish=False, canReportProblem=False,
               instructions="本项结果和反馈已保存。请保留当前接线；关闭窗口后，我再处理这一项的结果。")
        print("KEY_POPUP_OWNER_RESULT " + result, flush=True)

    try:
        if ui_alive():
            connect_once()
        while ui_alive():
            action_file = out / "operator-actions.jsonl"
            text = action_file.read_text(encoding="utf-8-sig") if action_file.exists() else ""
            lines = text.splitlines(keepends=True)
            complete = [line for line in lines if line.endswith("\n")]
            for line in complete[action_offset:]:
                action = json.loads(line)
                if action["action"] == "connect" and capture is None and phase in ("unavailable", "interrupted"):
                    connect_once()
                elif action["action"] in ("done", "problem"):
                    finish(action)
                elif action["action"] == "close":
                    if capture is not None:
                        finish(action, closing=True)
                    else:
                        release("窗口已关闭，无实际句柄")
            action_offset = len(complete)
            if capture is not None:
                report = read_json(live / "result.json", {})
                if capture.poll() is not None:
                    capture = None
                    release("持续采集已结束，实际UART已关闭，目标状态未知，未判按键通过")
                    save_owner("UNDETERMINED_CAPTURE_INTERRUPTED", report)
                    update("interrupted", "状态查询超时，请先不用按键；已有按键记录已保存" if report.get("failureKind") == "RESPONSE_TIMEOUT" else
                           "采集程序已停止，请先不用按键；已有数据已保存", "red",
                           canConnect=True, canFinish=True, canReportProblem=True)
                    print("KEY_POPUP_CAPTURE_INTERRUPTED", flush=True)
                elif report.get("result") == "KEY_LIVE_CAPTURE_ARMED_AWAITING_OPERATOR":
                    presses, releases, key_state, last = counts(report)
                    last_response = datetime.fromisoformat(report["lastResponsiveAtLocal"])
                    fresh = (datetime.now() - last_response).total_seconds() < 4
                    update("capturing", "正在采集：现在可以短按实体键 3 次" if fresh else "正在等待状态回答，请暂停按键；已有数据已保存",
                           "green" if fresh else "red", presses=presses, releases=releases,
                           keyState=key_state, lastEvent=last, canConnect=False, canFinish=True,
                           canReportProblem=True,
                           instructions="短按并完全松开 3 次，每次间隔约 1～2 秒；完成后点“我已按完”。没有倒计时。")
            time.sleep(.15)
    finally:
        actions_file = out / "operator-actions.jsonl"
        final_actions = [json.loads(line) for line in actions_file.read_text(encoding="utf-8-sig").splitlines()
                         if line.strip()] if actions_file.exists() else []
        close_action = next((action for action in reversed(final_actions) if action.get("action") == "close"), None)
        if capture is not None:
            finish(close_action or {"action": "close", "atLocal": now(), "note": "窗口或监控进程结束"}, closing=True)
        else:
            release("窗口监控已结束，实际句柄均已关闭")
            saved = read_json(out / "owner-result.json")
            if saved:
                saved.update(operatorActions=final_actions, windowClosedAtLocal=close_action.get("atLocal") if close_action else None)
                write_json(out / "owner-result.json", saved)
                (out / "owner-result.txt").write_text(saved["result"] + "\n" + json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_json(out / "monitor-ended.json", {"atLocal": now(), "phase": phase, "hardwareHandlesClosed": True})


if __name__ == "__main__":
    main()
