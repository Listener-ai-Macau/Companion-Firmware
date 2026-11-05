"""Load a guarded diagnostic, let the owner start one sound check, retain evidence."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from peripheral_diag_uart import write_json_atomic as write_json

ROOT = Path(__file__).resolve().parents[1]
OWNER = "01a11ba8-9629-7350-976b-fd50a1045a76"


def now():
    return datetime.now().isoformat(timespec="milliseconds")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("tones", "speech"), default="tones")
    parser.add_argument("--speech-gain", type=int, choices=(64, 128, 256, 512), default=256)
    args = parser.parse_args()
    speech = args.mode == "speech"
    build_path = args.build.resolve()
    build = json.loads(build_path.read_text(encoding="utf-8-sig"))
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    board = ROOT.parent / "docs/board_operations.md"
    row = (f"- **占用中**：Companion 硬件功能检查（{OWNER}，{now()}，peripheral-ram-diag/{out.name}）。"
           f"只检查扬声器{'语音可懂度' if speech else '基础出声'}；受保护加载SRAM诊断，Owner在原生窗口自行点播放，记录DMA/P6/三路引脚及FS估计和真实听感。"
           "不ARM按键、不查充电、不写Flash/NOR/NVM/OB，不启动其他外设；结束恢复实际产品并关闭接口。")
    result = {"result": "PREPARING", "startedAtLocal": now(), "scope": "SPEAKER_ONLY",
              "build": str(build_path), "packageSha256": build["imageSha256"],
              "boardUid": build["requiredUid"], "operatorDeadline": None,
              "physicalQualification": "NOT_OBSERVED", "audioMode": args.mode, "speechPcmGain": args.speech_gain if speech else None, "internalFlashWrites": False,
              "uartClosed": True, "debugProcessesClosed": True}
    state = {"title": "Companion 外设检查 — 扬声器", "heading": "扬声器：点播放后，听三个由低到高的短音",
             "phase": "preparing", "status": "正在准备检测程序", "color": "orange",
             "instructions": "本次只听主板扬声器。准备好后点【播放三个音】，播放结束后再选择听到的情况。",
             "live": "", "startLabel": "播放三个音", "passLabel": "三声都清楚", "failLabel": "缺音／破音",
             "canStart": False, "canRespond": False, "showNoSound": True,
             "details": f"包：{build_path}\nbin SHA256：{build['imageSha256']}\nUID：{build['requiredUid']}\n结果：{out}\n以上仅为追溯资料，无需据此判断通过。"}
    if speech:
        state.update(heading="扬声器：点播放后，听一句中文语音", instructions="主板将说：你好，这是声音测试。\n这次已调整数字音量。点【播放一句话】，听完后选择是否清楚、有无断续或破音。",
                     startLabel="播放一句话", passLabel="语音清楚", failLabel="听不清／破音")
        if build.get("variant") == "VOICE_NATIVE_16K_16BIT_ONE_DMA":
            state.update(instructions="主板将说：你好，这是声音测试。\n这次使用16kHz／16位语音，整句连续播放。点【播放一句话】，听完后选择是否清楚，有无断续或破音。")
    leased = False
    loaded = False
    popup = None

    def save():
        write_json(out / "result.json", result)
        write_json(out / "ui-state.json", state)

    def section(text):
        return text.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]

    def check_lease():
        lines = [l for l in section(board.read_text(encoding="utf-8-sig")).splitlines() if "**占用中**" in l]
        if lines != [row]:
            raise RuntimeError("Own unique speaker stage lease changed")

    def release():
        nonlocal leased
        if not leased:
            return
        text = board.read_text(encoding="utf-8-sig")
        active = [l for l in section(text).splitlines() if "**占用中**" in l]
        if active == [row] and board.read_text(encoding="utf-8-sig") == text:
            replacement = row.replace("**占用中**", "**已释放**", 1) + (
                f"；{now()} 所有自身UART/SWD及板端命令子进程实际关闭，无BLE；"
                f"正式程序恢复见Companion-Firmware/{out.relative_to(ROOT).as_posix()}/restore/result.json，听感与原始数据保留在本目录。")
            board.write_text(text.replace(row, replacement, 1), encoding="utf-8-sig")
            leased = False
            result["leaseReleased"] = True
        else:
            result["leaseReleaseError"] = "Shared record changed; own stage requires explicit release"

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
        path = out / "operator-actions.jsonl"
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8-sig")
        return [json.loads(line) for line in text.splitlines(keepends=True) if line.endswith("\n")]

    def restore():
        nonlocal loaded
        if not loaded:
            return
        receipt = child("capture_wba_peripheral_diag.py", ["--command", "RESET", "--lead-in-seconds", "0"], "restore", 15)
        result["restore"] = receipt
        result["productRestored"] = receipt.get("result") == "PRODUCT_UART_IDENTITY_RESTORED_PERIPHERAL_QUALIFICATION_UNCHANGED"
        loaded = False

    try:
        text = board.read_text(encoding="utf-8-sig")
        if any("**占用中**" in l for l in section(text).splitlines()):
            raise RuntimeError("Board occupied; no hardware opened")
        if board.read_text(encoding="utf-8-sig") != text:
            raise RuntimeError("Shared record changed before acquisition")
        board.write_text(text.replace("## 当前占用", "## 当前占用\n\n" + row, 1), encoding="utf-8-sig")
        leased = True
        save()
        receipt = child("load_wba_peripheral_diag.py", ["--build", str(build_path)], "load", 70)
        result["load"] = receipt
        loaded = bool(receipt.get("sramDiagnosticRunning"))
        if not loaded:
            raise RuntimeError("Guarded SRAM diagnostic did not start; no sound command issued")
        state.update(phase="ready", status="已准备好：你现在可以点播放", color="green", canStart=True)
        save()
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            raise RuntimeError("PowerShell unavailable")
        with (out / "popup-stdout.log").open("wb") as stdout, (out / "popup-stderr.log").open("wb") as stderr:
            popup = subprocess.Popen([shell, "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File",
                                      str(ROOT / "tools/show_wba_peripheral_operator.ps1"), "-SessionDirectory", str(out)],
                                     cwd=ROOT, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        result["popupPid"] = popup.pid
        shown_deadline = time.monotonic() + 15
        while not (out / "popup-ready.json").exists():
            if popup.poll() is not None or time.monotonic() > shown_deadline:
                raise RuntimeError("Physical operator window did not show")
            time.sleep(.1)
        result["result"] = "SPEAKER_READY_WAITING_OWNER_START"
        save()
        print(json.dumps({"result": result["result"], "output": str(out), "popupPid": popup.pid}, ensure_ascii=False), flush=True)
        action = None
        while popup.poll() is None:
            action = next((a for a in actions() if a["action"] in ("start", "close")), None)
            if action:
                break
            time.sleep(.2)
        if action is None or action["action"] != "start":
            result["result"] = "CANCELLED_BEFORE_PLAYBACK"
        else:
            result["ownerStart"] = action
            state.update(phase="playing", status="正在播放：请听主板说话" if speech else "正在播放：请听主板发出的三个短音", color="green", canStart=False)
            save()
            capture = child("capture_wba_peripheral_diag.py", ["--command", f"SPEAKER_SPEECH_G{args.speech_gain}" if speech else "SPEAKER", "--lead-in-seconds", "0"], "sound", 70)
            result["capture"] = capture
            state.update(phase="review", status="播放阶段已结束：请选择实际听到的情况", color="orange", canRespond=True,
                         live="请按你的听感选择；日志和信号状态由我核对。")
            save()
            restore()
            release()
            result["result"] = "SPEAKER_PLAYBACK_ENDED_OWNER_RESULT_PENDING"
            save()
            print(json.dumps({"result": result["result"], "output": str(out), "productRestored": result.get("productRestored")}, ensure_ascii=False), flush=True)
            while popup.poll() is None:
                action = next((a for a in actions() if a["action"] in ("pass", "fail", "no_sound", "skip", "close")), None)
                if action:
                    break
                time.sleep(.2)
            result["ownerAction"] = action
            answer = action.get("action") if action else "close"
            if answer == "no_sound":
                result.update(result="FAIL_SPEAKER_NO_SOUND", physicalQualification="OWNER_OBSERVED_NO_SOUND")
            elif answer == "fail":
                note = action.get("note", "") if action else ""
                result.update(result="FAIL_SPEAKER_VOLUME_TOO_LOW" if any(x in note for x in ("太小", "很小", "音量小")) else "FAIL_SPEAKER_MISSING_TONE_OR_DISTORTION",
                              physicalQualification="OWNER_OBSERVED_AUDIO_FAILURE")
            elif answer == "pass" and capture.get("result") == "DIAGNOSTIC_RESPONSE_CAPTURED_PHYSICAL_QUALIFICATION_PENDING":
                result.update(result="PASS_SPEAKER_BASIC_INTELLIGIBLE_SPEECH" if speech else "PASS_SPEAKER_BASIC_AUDIBLE_THREE_TONES",
                              physicalQualification="OWNER_HEARD_PHRASE_CLEAR" if speech else "OWNER_HEARD_ALL_THREE_CLEAR")
            elif answer == "pass":
                result.update(result="OWNER_HEARD_AUDIO_DEVICE_COMPLETION_NOT_QUALIFIED",
                              physicalQualification="OWNER_HEARD_PHRASE_CLEAR" if speech else "OWNER_HEARD_ALL_THREE_CLEAR")
            else:
                result.update(result="SPEAKER_NOT_OBSERVED", physicalQualification="NOT_ACCEPTED")
            write_json(out / "owner-result.json", result)
            (out / "owner-result.txt").write_text(result["result"] + "\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            state.update(phase="finished", status="你的反馈已保存，这一项由我继续核对", color="green" if result["result"].startswith("PASS_") else "red", canRespond=False)
    except Exception as error:
        result.update(result="SPEAKER_STAGE_FAILED", error=repr(error))
        state.update(phase="unavailable", status="本次没有完成检查，已保留失败现场", color="red", canStart=False, canRespond=False)
    finally:
        try:
            restore()
        except Exception as error:
            result["restoreError"] = repr(error)
        release()
        result.update(finishedAtLocal=now(), uartClosed=True, debugProcessesClosed=True, operatorActions=actions())
        save()
        if (out / "owner-result.json").exists():
            write_json(out / "owner-result.json", result)
            (out / "owner-result.txt").write_text(result["result"] + "\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"result": result["result"], "output": str(out), "error": result.get("error"),
                          "productRestored": result.get("productRestored"), "leaseReleased": result.get("leaseReleased")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
