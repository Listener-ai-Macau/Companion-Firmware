"""Observe five actual touch positions with a native window and no action deadline."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import traceback
import serial
from serial.tools import list_ports
from capture_wba_peripheral_diag import values
from peripheral_diag_uart import send_line, write_json_atomic

ROOT = Path(__file__).resolve().parents[1]
OWNER = "01a11ba8-9629-7350-976b-fd50a1045a76"
UID = "180010000d50335754363720"
SN = "004400403532510B31333430"
POSITIONS = (("top_left", "左上角"), ("top_right", "右上角"), ("bottom_right", "右下角"),
             ("bottom_left", "左下角"), ("centre", "中心"))


def now():
    return datetime.now().isoformat(timespec="milliseconds")


def coordinate_mapping(steps):
    if len(steps) != 5 or any(not s["contacts"] or not s["released"] for s in steps):
        return {"fiveDeclaredPointsObserved": False}
    points = {s["position"]: {a: statistics.median(int(p[a]) for p in s["contacts"]) for a in ("x", "y")} for s in steps}
    candidates = []
    for horizontal, vertical in (("x", "y"), ("y", "x")):
        tl, tr, br, bl, centre = (points[k] for k in ("top_left", "top_right", "bottom_right", "bottom_left", "centre"))
        widths = (tr[horizontal] - tl[horizontal], br[horizontal] - bl[horizontal])
        heights = (bl[vertical] - tl[vertical], br[vertical] - tr[vertical])
        # Distinct sides, consistent orientation, and a centre inside the rectangle.
        corners = (tl, tr, br, bl)
        if (min(abs(v) for v in widths + heights) >= 30 and widths[0] * widths[1] > 0
                and heights[0] * heights[1] > 0
                and all(min(p[a] for p in corners) < centre[a] < max(p[a] for p in corners) for a in (horizontal, vertical))):
            candidates.append({"horizontalRawAxis": horizontal, "verticalRawAxis": vertical,
                               "horizontalDirection": 1 if widths[0] > 0 else -1,
                               "verticalDirection": 1 if heights[0] > 0 else -1})
    return {"fiveDeclaredPointsObserved": True, "medianRawCoordinates": points,
            "consistentRectangleCandidates": candidates, "coordinateMappingObserved": len(candidates) == 1,
            "calibratedAccuracy": "NOT_MEASURED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_path = args.build.resolve(); build = json.loads(build_path.read_text(encoding="utf-8-sig"))
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    board = ROOT.parent / "docs/board_operations.md"
    row = (f"- **占用中**：Companion 硬件功能检查（{OWNER}，{now()}，peripheral-ram-diag/{out.name}）。"
           "只验触摸10kHz五点实际响应与P0读回；先窗口等待Owner开始，不占板等待。"
           "保护加载SRAM，10/25/10无触摸复位排除启动时长混杂，再持续采集无操作倒计时；"
           "不启动其它外设、不写Flash/NOR/NVM/OB，结束STOP、恢复正式产品并关闭实际接口。")
    result = {"result": "TOUCH_WINDOW_PREPARING_NO_BOARD_ACCESS", "startedAtLocal": now(), "boardUid": UID,
              "build": str(build_path), "packageSha256": build["imageSha256"], "samples": 0, "steps": [],
              "operatorDeadline": None, "internalFlashWrites": False, "physicalQualification": "NOT_OBSERVED"}
    state = {"title": "Companion 外设检查 — 触摸", "heading": "触摸：一次检查一个位置",
             "phase": "ready", "status": "方便时点【开始触摸检查】", "color": "green",
             "canStart": True, "canRespond": False, "canPass": False, "showNoSound": False,
             "startLabel": "开始触摸检查", "passLabel": "这个位置已点完", "failLabel": "触摸没有响应",
             "instructions": "开始后，窗口会依次提示四角和中心。\n每次轻按约1秒，再松手；看到收到触摸后点确认，再做下一个位置。\n不需要赶时间，电脑窗口显示实际采集进度。",
             "live": "尚未采集；现在无需点主板。", "details": f"包：{build_path}\nbin SHA256：{build['imageSha256']}\nUID：{UID}\n结果：{out}"}
    raw = bytearray(); pending = bytearray(); link = popup = None
    loaded = leased = armed = False

    def section(text):
        return text.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]

    def save():
        write_json_atomic(out / "result.json", result); write_json_atomic(out / "ui-state.json", state)

    def actions():
        path = out / "operator-actions.jsonl"
        return ([json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines(keepends=True) if s.endswith("\n")]
                if path.exists() else [])

    def check_lease():
        if [s for s in section(board.read_text(encoding="utf-8-sig")).splitlines() if "**占用中**" in s] != [row]:
            raise RuntimeError("Own unique touch lease changed")

    def acquire():
        nonlocal leased
        while popup.poll() is None and not any(a["action"] == "close" for a in actions()):
            text = board.read_text(encoding="utf-8-sig")
            if not any("**占用中**" in s for s in section(text).splitlines()):
                if board.read_text(encoding="utf-8-sig") != text:
                    continue
                board.write_text(text.replace("## 当前占用", "## 当前占用\n\n" + row, 1), encoding="utf-8-sig")
                leased = True; check_lease(); return
            state.update(status="等待另一项板端操作结束，尚未开始采集", color="orange"); save(); time.sleep(1)
        raise RuntimeError("Touch cancelled while waiting for board access")

    def child(script, arguments, folder, timeout):
        check_lease()
        with (out / f"{folder}-stdout.log").open("wb") as stdout, (out / f"{folder}-stderr.log").open("wb") as stderr:
            proc = subprocess.run([sys.executable, str(ROOT / "tools" / script), *arguments, "--output", str(out / folder)],
                                  cwd=ROOT, stdout=stdout, stderr=stderr, timeout=timeout,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        path = out / folder / "result.json"
        receipt = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {"result": "NO_CHILD_RESULT"}
        receipt["processExitCode"] = proc.returncode; return receipt

    def lines():
        data = link.read(max(1, link.in_waiting)); raw.extend(data); pending.extend(data)
        found = []
        while b"\n" in pending:
            line, _, remaining = pending.partition(b"\n"); pending[:] = remaining
            found.append(line.decode("ascii", errors="replace").strip())
        return found

    def transact(command, expected, timeout=4):
        check_lease(); send_line(link, command); deadline = time.monotonic() + timeout; found = []
        while time.monotonic() < deadline:
            for line in lines():
                found.append(line)
                if line.startswith(f"END test={expected} "):
                    return values(line), found
        raise RuntimeError(f"No complete {expected} response; raw stream preserved")

    def restore():
        nonlocal link, armed, loaded
        if link is not None:
            try:
                if armed:
                    stop, status = transact("TOUCH_STOP", "TOUCH_STOP")
                    result["touchStop"] = stop
                    result["finalTouchStatus"] = [values(s) for s in status if s.startswith("TOUCH_STATUS ")]
                    armed = False
            finally:
                link.close(); link = None
        if loaded:
            receipt = child("capture_wba_peripheral_diag.py", ["--command", "RESET", "--lead-in-seconds", "0"], "restore", 15)
            result["restore"] = receipt
            result["productRestored"] = receipt.get("result") == "PRODUCT_UART_IDENTITY_RESTORED_PERIPHERAL_QUALIFICATION_UNCHANGED"
            loaded = False

    def release():
        nonlocal leased
        if leased:
            text = board.read_text(encoding="utf-8-sig")
            if [s for s in section(text).splitlines() if "**占用中**" in s] == [row] and board.read_text(encoding="utf-8-sig") == text:
                replacement = row.replace("**占用中**", "**已释放**", 1) + f"；{now()} 自身UART/SWD/加载子进程实际关闭，无BLE；五点/频率对照及正式程序恢复见Companion-Firmware/{out.relative_to(ROOT).as_posix()}/result.json。"
                board.write_text(text.replace(row, replacement, 1), encoding="utf-8-sig")
                leased = False; result["leaseReleased"] = True

    try:
        save(); shell = shutil.which("pwsh") or shutil.which("powershell")
        with (out / "popup-stdout.log").open("wb") as stdout, (out / "popup-stderr.log").open("wb") as stderr:
            popup = subprocess.Popen([shell, "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File",
                                      str(ROOT / "tools/show_wba_peripheral_operator.ps1"), "-SessionDirectory", str(out)],
                                     cwd=ROOT, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 15
        while not (out / "popup-ready.json").exists():
            if popup.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("Physical touch window did not show")
            time.sleep(.1)
        result.update(result="TOUCH_WINDOW_WAITING_OWNER_START_NO_BOARD_ACCESS", popupPid=popup.pid); save()
        print(json.dumps({"result": result["result"], "output": str(out), "popupPid": popup.pid}), flush=True)
        action = None
        while popup.poll() is None:
            action = next((a for a in actions() if a["action"] in ("start", "close")), None)
            if action:
                break
            time.sleep(.2)
        if not action or action["action"] != "start":
            result["result"] = "TOUCH_CANCELLED_BEFORE_CAPTURE"; return
        result["ownerStart"] = action
        state.update(phase="preparing", canStart=False, status="正在连接主板，请先不要点触摸面", color="orange"); save()
        acquire()
        receipt = child("load_wba_peripheral_diag.py", ["--build", str(build_path)], "load", 70)
        result["load"] = receipt; loaded = bool(receipt.get("sramDiagnosticRunning"))
        if not loaded:
            raise RuntimeError("Guarded SRAM diagnostic did not start; touch not armed")
        ports = [p.device for p in list_ports.comports() if p.serial_number == SN]
        if len(ports) != 1:
            raise RuntimeError("Fixed V3 UART association is not unique")
        link = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=1)
        link.dtr = False; link.rts = False; link.port = ports[0]; link.open()
        send_line(link, ""); send_line(link, "HELLO"); deadline = time.monotonic() + 3; hello = None
        while time.monotonic() < deadline and hello is None:
            for line in lines():
                if line.startswith("HELLO "):
                    hello = values(line)
        if not hello or hello.get("uid") != UID or hello.get("target_ok") != "1":
            raise RuntimeError("Actual diagnostic identity did not match before touch ARM")
        result["hello"] = hello
        arm, compare = transact("TOUCH_ARM", "TOUCH_ARM", 8)
        result["touchArm"] = arm
        result["readyFrequencyComparison"] = [values(s) for s in compare if s.startswith("TOUCH_READY_COMPARE ")]
        if arm.get("result") != "ARMED_AWAITING_OPERATOR":
            raise RuntimeError("Touch configuration or stable identity failed; physical checks not started")
        armed = True; result.update(result="TOUCH_FIVE_POINT_CAPTURE_RUNNING", armedAtLocal=now())
        print(json.dumps({"result": result["result"], "comparison": result["readyFrequencyComparison"]}), flush=True)
        action_index = len(actions()); last_ui = 0; failed_action = None
        for position, label in POSITIONS:
            step = {"position": position, "cueShownAtLocal": now(), "contacts": [], "released": False, "initialIdleObserved": False}
            result["steps"].append(step)
            state.update(phase="capturing", step=position, canRespond=True, canPass=False, color="green",
                         status=f"现在检查：{label}", instructions=f"请轻按触摸面的【{label}】约1秒，然后松手。\n收到触摸并松手后，点【这个位置已点完】，再做下一个。",
                         live=f"已完成 {len(result['steps'])-1} / 5 个位置。等待本次轻按。")
            save()
            cue_not_before = time.monotonic() + .4
            while popup.poll() is None:
                check_lease()
                for line in lines():
                    if line.startswith("END test=TOUCH_LIVE "):
                        raise RuntimeError("Touch stream stopped on actual I/O or decode failure")
                    if not line.startswith("TOUCH_LIVE "):
                        continue
                    sample = values(line); result["samples"] += 1
                    if int(sample["count"]) == 0:
                        step["initialIdleObserved"] = True
                        if step["contacts"]:
                            step["released"] = True
                    elif step["initialIdleObserved"] and time.monotonic() >= cue_not_before:
                        step["contacts"].append(sample); step["released"] = False
                recent = actions()[action_index:]; action_index += len(recent)
                action = next((a for a in recent if a["action"] in ("pass", "fail", "skip", "close")), None)
                if action:
                    if (action["action"] == "pass" and action.get("stepAtClick") == position
                            and step["contacts"] and step["released"]):
                        step["ownerConfirmedPosition"] = action; break
                    if action["action"] in ("fail", "skip", "close"):
                        failed_action = action; break
                if time.monotonic() - last_ui >= .25:
                    last_ui = time.monotonic()
                    ready = bool(step["contacts"]) and step["released"]
                    state.update(canPass=ready, live=("已收到触摸并观察到松手。请点【这个位置已点完】。" if ready else
                                                     "已收到触摸，请松手。" if step["contacts"] else "正在同步采集，等待这一次轻按。"))
                    save(); (out / "uart.log").write_bytes(raw)
            if failed_action or popup.poll() is not None:
                break
        state.update(phase="restoring", canStart=False, canRespond=False, canPass=False,
                     status="五点采集已结束，正在恢复正常程序", live="操作已收到，不需要再点确认。")
        save()
        restore(); release()
        result["coordinateAnalysis"] = coordinate_mapping(result["steps"])
        statuses = result.get("finalTouchStatus", [])
        no_errors = bool(statuses) and all(s.get("errors") == "0" and s.get("io_errors") == "0" for s in statuses)
        complete = len(result["steps"]) == 5 and all(s.get("ownerConfirmedPosition") for s in result["steps"])
        basic = complete and no_errors and result["coordinateAnalysis"].get("coordinateMappingObserved") is True
        irq_levels = {int(s[k], 16) & 1 for step in result["steps"] for s in step["contacts"] for k in ("io_before", "io_after")}
        result.update(result="PASS_TOUCH_FIVE_POSITION_POLLING_BASIC_AT_10KHZ" if basic else "TOUCH_PHYSICAL_COVERAGE_INCOMPLETE_OR_FAILURE",
                      physicalQualification="BASIC_POLLING_ONLY" if basic else "NOT_QUALIFIED", ownerAction=failed_action,
                      touchIrqQualification="BOTH_P0_LEVELS_DURING_CONTACTS_OBSERVED" if irq_levels == {0, 1} else "P0_TRANSITION_NOT_QUALIFIED")
        state.update(phase="finished", canStart=False, canRespond=False, canPass=False, color="green" if basic else "red",
                     status="五个位置的触摸已记录，主板已恢复正常程序" if basic else "本次没有完成全部五点检查，已保留实际结果",
                     live="这一项结果已保存；你可以关闭窗口。")
    except Exception as error:
        result.update(result="TOUCH_OPERATOR_STAGE_FAILED", error=repr(error), traceback=traceback.format_exc())
        state.update(phase="unavailable", color="red", canStart=False, canRespond=False, canPass=False,
                     status="本次未完成，已保留失败现场", live="我会继续检查实际原因；目前无需继续点触摸面。")
    finally:
        try:
            restore()
        except Exception as error:
            result.update(restoreError=repr(error), restoreTraceback=traceback.format_exc())
        if link is not None:
            link.close(); link = None
        release(); result.update(finishedAtLocal=now(), uartClosed=True, debugProcessesClosed=True, operatorActions=actions())
        (out / "uart.log").write_bytes(raw); save()
        write_json_atomic(out / "owner-result.json", result)
        (out / "owner-result.txt").write_text(result["result"] + "\n" + json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"result": result["result"], "output": str(out), "error": result.get("error"),
                          "productRestored": result.get("productRestored"), "leaseReleased": result.get("leaseReleased")}), flush=True)


if __name__ == "__main__":
    main()
