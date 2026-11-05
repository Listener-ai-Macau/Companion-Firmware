"""Complete missing IMU gravity-face coverage with a slow, visible operator window."""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import serial
from serial.tools import list_ports
from capture_wba_peripheral_diag import analyze, values
from peripheral_diag_uart import send_line, write_json_atomic as write_json
from imu_operator_feedback import face, live_feedback, parse_live_sample

ROOT = Path(__file__).resolve().parents[1]
OWNER = "01a11ba8-9629-7350-976b-fd50a1045a76"
UID = "180010000d50335754363720"
SN = "004400403532510B31333430"


def now():
    return datetime.now().isoformat(timespec="milliseconds")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--auto-start", action="store_true", help="Agent starts after the actual window is shown; never records an Owner click")
    parser.add_argument("--prior-capture", type=Path, help="Reuse valid static faces from the same UID and unchanged IMU driver")
    args = parser.parse_args()
    build_path = args.build.resolve()
    build = json.loads(build_path.read_text(encoding="utf-8-sig"))
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    board = ROOT.parent / "docs/board_operations.md"
    row = (f"- **占用中**：Companion 硬件功能检查（{OWNER}，{now()}，peripheral-ram-diag/{out.name}）。"
           "仅补齐IMU静置六面；窗口等待Owner开始时不占板，开始后受保护加载SRAM诊断并连续采集，无Owner操作倒计时。"
           "旧三轴转动/NOR/按键/屏幕/双麦不重跑，不查充电或写Flash/NOR/NVM/OB；结束STOP、恢复实际产品并关闭接口。")
    result = {"result": "PREPARING", "startedAtLocal": now(), "scope": "IMU_MISSING_SIX_GRAVITY_FACES_ONLY",
              "build": str(build_path), "packageSha256": build["imageSha256"], "boardUid": UID,
              "operatorDeadline": None, "internalFlashWrites": False, "samples": 0,
              "facesHeldAtLeast1500Ms": {}, "physicalQualification": "NOT_OBSERVED"}
    state = {"uiKind": "imu", "title": "Companion 外设检查 — 惯性传感器", "heading": "惯性传感器：转动有实时反馈，停稳才记录方向",
             "phase": "preparing", "status": "正在准备", "color": "orange", "canStart": False,
             "canRespond": False, "showNoSound": False, "startLabel": "开始六面检查", "passLabel": "六面操作完成",
             "failLabel": "姿态没有变化", "live": "", "imuVisual": None,
             "instructions": "点开始后，将屏幕朝上、朝下，再把左、右、上、下四个边分别朝上。\n每换一个面静置约2秒，等窗口进度增加再换下一个；不需要赶时间。",
             "details": f"包：{build_path}\nbin SHA256：{build['imageSha256']}\nUID：{UID}\n结果：{out}\n数值和通信正确性由agent核对。"}
    leased = loaded = armed = restore_attempted = False
    popup = link = None
    raw = bytearray(); pending = bytearray()
    current_face = None; hold_start = previous_ms = None; held = {}; last_ui = 0.
    latest_sample = None; last_sample_at = None
    result["hostSources"] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__), ROOT / "tools/imu_operator_feedback.py", ROOT / "tools/show_wba_peripheral_operator.ps1",
                  ROOT / "tools/peripheral_diag_uart.py")
    }
    prior_raw = b""
    if args.prior_capture:
        prior_dir = args.prior_capture.resolve()
        prior = json.loads((prior_dir / "result.json").read_text(encoding="utf-8-sig"))
        prior_build = json.loads(Path(prior["build"]).read_text(encoding="utf-8-sig"))
        imu_driver_key = "app\\companion_pendant\\imu\\lsm6dso.c"
        statuses = prior.get("finalImuStatus", [])
        if (prior.get("boardUid") != UID or prior_build["sources"].get(imu_driver_key) != build["sources"].get(imu_driver_key)
                or prior.get("imuStop", {}).get("result") != "STOPPED" or not statuses
                or not all(s.get("errors") == "0" and s.get("io_errors") == "0" for s in statuses)):
            raise RuntimeError("Prior IMU capture does not qualify for reuse")
        prior_raw = (prior_dir / "uart.log").read_bytes()
        held = {k: {**v, "source": str(prior_dir / "uart.log")}
                for k, v in prior.get("facesHeldAtLeast1500Ms", {}).items()
                if k in ("x+", "x-", "y+", "y-", "z+", "z-") and v.get("holdMs", 0) >= 1500}
        result["priorCapture"] = {"result": str(prior_dir / "result.json"), "uartSha256": hashlib.sha256(prior_raw).hexdigest(),
                                  "reusedFaces": sorted(held), "priorStageResult": prior["result"],
                                  "reuseBasis": "Same physical UID, unchanged IMU driver and units, complete STOP with zero sensor/IO errors"}
        result["facesHeldAtLeast1500Ms"] = held.copy()
        state.update(startLabel="开始补剩余方向", live=f"已保留 {len(held)} / 6 个方向，尚未开始新采集。",
                     instructions="上次平放的方向已保留，不需要重复绕轴转动。\n这次把屏幕朝上、朝下，再把四个边依次朝上。\n圆点即时反馈倾斜；看到“已记录”后再换面，没有操作倒计时。")

    def section(text):
        return text.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]

    def save():
        write_json(out / "result.json", result); write_json(out / "ui-state.json", state)

    def check_lease():
        active = [l for l in section(board.read_text(encoding="utf-8-sig")).splitlines() if "**占用中**" in l]
        if active != [row]:
            raise RuntimeError("Own unique IMU lease changed")

    def acquire():
        nonlocal leased
        while popup.poll() is None and not any(a["action"] == "close" for a in actions()):
            text = board.read_text(encoding="utf-8-sig")
            if not any("**占用中**" in l for l in section(text).splitlines()):
                if board.read_text(encoding="utf-8-sig") != text:
                    continue
                board.write_text(text.replace("## 当前占用", "## 当前占用\n\n" + row, 1), encoding="utf-8-sig")
                leased = True; result["boardAcquiredAtLocal"] = now(); check_lease(); return
            state.update(status="等待另一项板端操作结束，尚未开始采集", color="orange"); save(); time.sleep(1)
        raise RuntimeError("IMU cancelled while waiting for board access")

    def child(script, extra, folder, timeout):
        check_lease()
        with (out / f"{folder}-stdout.log").open("wb") as stdout, (out / f"{folder}-stderr.log").open("wb") as stderr:
            p = subprocess.run([sys.executable, str(ROOT / "tools" / script), *extra, "--output", str(out / folder)],
                               cwd=ROOT, stdout=stdout, stderr=stderr, timeout=timeout,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        path = out / folder / "result.json"
        receipt = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {"result": "NO_CHILD_RESULT"}
        receipt["processExitCode"] = p.returncode
        return receipt

    def actions():
        p = out / "operator-actions.jsonl"
        if not p.exists():
            return []
        return [json.loads(l) for l in p.read_text(encoding="utf-8-sig").splitlines(keepends=True) if l.endswith("\n")]

    def read_lines():
        chunk = link.read(max(1, link.in_waiting)); raw.extend(chunk); pending.extend(chunk)
        lines = []
        while b"\n" in pending:
            line, _, rest = pending.partition(b"\n"); pending[:] = rest
            lines.append(line.decode("ascii", errors="replace").strip())
        return lines

    def transact(command, expected, timeout=4.):
        check_lease(); send_line(link, command)
        end = time.monotonic() + timeout
        found = []
        while time.monotonic() < end:
            for line in read_lines():
                found.append(line)
                if line.startswith(f"END test={expected} "):
                    return values(line), found
        raise RuntimeError(f"No complete {expected} response; raw stream preserved")

    def stop_and_restore():
        nonlocal link, armed, loaded, restore_attempted
        if link is not None:
            try:
                if armed:
                    receipt, lines = transact("IMU_STOP", "IMU_STOP")
                    result["imuStop"] = receipt
                    result["finalImuStatus"] = [values(l) for l in lines if l.startswith("IMU_STATUS ")]
                    if receipt.get("result") != "STOPPED":
                        raise RuntimeError("IMU stop reported a device failure")
                    armed = False
            except Exception as error:
                result["imuStopError"] = repr(error)
            finally:
                link.close(); link = None
        if loaded and not restore_attempted:
            restore_attempted = True
            ports = [p.device for p in list_ports.comports() if p.serial_number == SN]
            if len(ports) != 1:
                result.update(productRestored=False, restoreDeferredReason="FIXED_V3_UART_UNAVAILABLE_NO_RESET_SENT")
                return
            receipt = child("capture_wba_peripheral_diag.py", ["--command", "RESET", "--lead-in-seconds", "0"], "restore", 15)
            result["restore"] = receipt
            result["productRestored"] = receipt.get("result") == "PRODUCT_UART_IDENTITY_RESTORED_PERIPHERAL_QUALIFICATION_UNCHANGED"
            loaded = False

    def release():
        nonlocal leased
        if not leased:
            return
        text = board.read_text(encoding="utf-8-sig")
        active = [l for l in section(text).splitlines() if "**占用中**" in l]
        if active == [row] and board.read_text(encoding="utf-8-sig") == text:
            replacement = row.replace("**占用中**", "**已释放**", 1) + (
                f"；{now()} 自身UART/SWD/加载子进程实际关闭，无BLE；STOP及正式程序恢复和六面原始证据见Companion-Firmware/{out.relative_to(ROOT).as_posix()}。")
            board.write_text(text.replace(row, replacement, 1), encoding="utf-8-sig")
            leased = False; result["leaseReleased"] = True

    try:
        state.update(phase="ready", status="已准备好：方便时点开始", color="green", canStart=True); save()
        shell = shutil.which("pwsh") or shutil.which("powershell")
        with (out / "popup-stdout.log").open("wb") as stdout, (out / "popup-stderr.log").open("wb") as stderr:
            popup = subprocess.Popen([shell, "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File",
                                      str(ROOT / "tools/show_wba_peripheral_operator.ps1"), "-SessionDirectory", str(out)],
                                     cwd=ROOT, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 15
        while not (out / "popup-ready.json").exists():
            if popup.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("Physical IMU operator window did not show")
            time.sleep(.1)
        result.update(result="IMU_READY_WAITING_OWNER_START_NO_BOARD_ACCESS", popupPid=popup.pid); save()
        print(json.dumps({"result": result["result"], "output": str(out), "popupPid": popup.pid}), flush=True)
        action = None
        if args.auto_start:
            action = {"action": "start", "actor": "agent", "atLocal": now(),
                      "authorization": "Owner requested the next peripheral hardware check", "method": "AUTO_START_AFTER_WINDOW_SHOWN"}
        else:
            while popup.poll() is None:
                action = next((a for a in actions() if a["action"] in ("start", "close")), None)
                if action:
                    break
                time.sleep(.2)
        if not action or action["action"] != "start":
            result["result"] = "IMU_CANCELLED_BEFORE_CAPTURE"
        else:
            result["captureStart"] = action
            if action.get("actor") != "agent":
                result["ownerStart"] = action
            state.update(phase="preparing", canStart=False, status="正在连接主板，采集开始后再转动", color="orange"); save()
            acquire()
            receipt = child("load_wba_peripheral_diag.py", ["--build", str(build_path)], "load", 70)
            result["load"] = receipt; loaded = bool(receipt.get("sramDiagnosticRunning"))
            if not loaded:
                raise RuntimeError("Guarded SRAM diagnostic did not start; IMU not armed")
            check_lease()
            link = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=1)
            ports = [p.device for p in list_ports.comports() if p.serial_number == SN]
            if len(ports) != 1:
                raise RuntimeError("Fixed V3 UART association is not unique")
            link.dtr = False; link.rts = False; link.port = ports[0]; link.open()
            send_line(link, ""); send_line(link, "HELLO"); hello = None
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and hello is None:
                for line in read_lines():
                    if line.startswith("HELLO "):
                        hello = values(line)
            if not hello or hello.get("uid") != UID or hello.get("target_ok") != "1":
                raise RuntimeError("Diagnostic identity did not match before IMU ARM")
            result["hello"] = hello
            arm, _ = transact("IMU_ARM", "IMU_ARM")
            if arm.get("result") != "ARMED_AWAITING_OPERATOR":
                raise RuntimeError("IMU did not arm")
            armed = True; result.update(result="IMU_SIX_FACE_CAPTURE_RUNNING", armedAtLocal=now())
            state.update(phase="capturing", status="正在同步观察：补剩余静置方向" if held else "正在同步观察：先把屏幕朝上静置",
                         live=f"已稳定记录 {len(held)} / 6 个方向。每换一个方向静置约2秒。", color="green", canStart=False); save()
            print(json.dumps({"result": result["result"], "output": str(out)}), flush=True)
            while popup.poll() is None and len(held) < 6:
                check_lease()
                if any(a["action"] == "close" for a in actions()):
                    break
                for line in read_lines():
                    if line.startswith("END test=IMU_LIVE "):
                        raise RuntimeError("IMU reported a live I/O failure")
                    if not line.startswith("IMU_LIVE "):
                        continue
                    try:
                        sample = parse_live_sample(line)
                    except ValueError as error:
                        result["invalidUartRecord"] = {"line": line, "atLocal": now(), "error": str(error)}
                        current_face = None; hold_start = previous_ms = None
                        raise RuntimeError("IMU_UART_RECORD_INCOMPLETE; raw record preserved, no malformed sample counted") from error
                    result["samples"] += 1
                    latest_sample = sample; last_sample_at = time.monotonic()
                    found = face(sample); ms = int(sample["ms"])
                    if found != current_face or previous_ms is None or not 0 < ms - previous_ms < 80:
                        current_face = found; hold_start = ms
                    if found and found not in held and hold_start is not None and ms - hold_start >= 1500:
                        held[found] = {"fromMs": hold_start, "toMs": ms, "holdMs": ms - hold_start}
                    previous_ms = ms
                if time.monotonic() - last_ui > .25:
                    last_ui = time.monotonic(); result["facesHeldAtLeast1500Ms"] = held.copy()
                    if latest_sample and last_sample_at is not None and last_ui - last_sample_at < 1.:
                        state.update(live_feedback(latest_sample, held, current_face, hold_start))
                    else:
                        state.update(status="等待新的板端数据，请先停稳", color="orange", imuVisual=None,
                                     live=f"已保留 {len(held)} / 6 个方向；暂时没有新数据，不显示旧姿态为实时反馈。")
                    save(); (out / "uart.log").write_bytes(raw)
            result["facesHeldAtLeast1500Ms"] = held.copy()
            state.update(phase="restoring", canStart=False, canRespond=False, imuVisual=None,
                         status="采集已结束，正在恢复正常程序", live="操作和原始数据已收到，不需要再点确认。"); save()
            stop_and_restore(); release()
            converted = (prior_raw + b"\n" + bytes(raw)).replace(b"IMU_LIVE ms=", b"IMU ms=")
            result["analysisSources"] = ([str(args.prior_capture.resolve() / "uart.log")] if args.prior_capture else []) + [str(out / "uart.log")]
            result["analysis"] = analyze(converted, "IMU", out)
            statuses = result.get("finalImuStatus", [])
            no_errors = bool(statuses) and all(s.get("errors") == "0" and s.get("io_errors") == "0" for s in statuses)
            covered = len(held) == 6 and result["analysis"].get("sixGravityFacesObserved") is True
            result.update(result="IMU_SIX_GRAVITY_FACES_CAPTURED" if covered and no_errors else
                          "IMU_SIX_FACE_COVERAGE_INCOMPLETE_ZERO_IO_ERRORS" if no_errors else "IMU_SENSOR_OR_IO_ERROR",
                          physicalQualification="SIX_STATIC_GRAVITY_RESPONSES_OBSERVED" if covered and no_errors else "NOT_QUALIFIED")
            state.update(phase="review", canRespond=True, color="green" if covered and no_errors else "red",
                         status="六个面的姿态变化已记录，实板已恢复" if covered and no_errors else "这次未收齐六面，原始数据已保留",
                         live="如果你完成了窗口里的动作，请点【六面操作完成】；数值由我判断。" if result.get("productRestored") else
                         "板端恢复尚未确认，已保存现场；请先保持板子平放和接线稳定。")
            save(); print(json.dumps({"result": result["result"], "output": str(out)}), flush=True)
            action = None
            while True:
                action = next((a for a in reversed(actions()) if a["action"] in ("pass", "fail", "skip", "close")), None)
                if action or popup.poll() is not None:
                    break
                time.sleep(.2)
            result["ownerAction"] = action
            if covered and no_errors and action and action["action"] == "pass":
                result["result"] = "PASS_IMU_SIX_STATIC_GRAVITY_FACES"
            elif action and action["action"] == "fail":
                result["result"] = "OWNER_OBSERVED_IMU_RESPONSE_FAILURE"
            state.update(phase="finished", canRespond=False, imuVisual=None,
                         status="这一项已保存，由我继续核对", live="采集已结束，正常程序已恢复；关窗不计作验收通过。")
            write_json(out / "owner-result.json", result)
            (out / "owner-result.txt").write_text(result["result"] + "\n" + json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as error:
        result.update(result="IMU_STAGE_FAILED", error=repr(error), traceback=traceback.format_exc())
        state.update(phase="unavailable", color="red", canStart=False, canRespond=False, imuVisual=None,
                     status="采集连接中断，原始数据已保留", live="请保持板子平放和接线稳定；已观察到的姿态变化会保留，由我核对恢复状态。")
    finally:
        try:
            stop_and_restore()
        except Exception as error:
            result["restoreError"] = repr(error)
        if link is not None:
            link.close(); link = None
        release(); result.update(finishedAtLocal=now(), uartClosed=True, debugProcessesClosed=True, operatorActions=actions())
        (out / "uart.log").write_bytes(raw); save()
        if (out / "owner-result.json").exists():
            write_json(out / "owner-result.json", result)
            (out / "owner-result.txt").write_text(result["result"] + "\n" + json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"result": result["result"], "output": str(out), "error": result.get("error"),
                          "productRestored": result.get("productRestored"), "leaseReleased": result.get("leaseReleased")}), flush=True)


if __name__ == "__main__":
    main()
