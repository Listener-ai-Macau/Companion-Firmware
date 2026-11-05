"""Run only remaining hardware checks under one lease, then restore the actual product."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OWNER = "01a11ba8-9629-7350-976b-fd50a1045a76"
COMMANDS = ("IMU_SELF_TEST", "TOUCH_RESET_PATH", "CLOCKS")
AVAILABLE_COMMANDS = (*COMMANDS, "IMU_INTERRUPT_PATH")
AVAILABLE_COMMANDS += ("TCA_RESET_PATH", "INTERNAL_REFERENCE", "RELATIVE_CLOCKS", "RTC_STOP_WAKE", "IMU_STOP_WAKE")


def now():
    return datetime.now().isoformat(timespec="milliseconds")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commands", nargs="+", choices=AVAILABLE_COMMANDS, default=list(COMMANDS))
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    board = ROOT.parent / "docs/board_operations.md"
    build = json.loads(args.build.read_text(encoding="utf-8-sig"))
    result = {"result": "PREPARING", "startedAtLocal": now(), "sourceCommit": args.source_commit,
              "diagnosticPackageSha256": build["imageSha256"], "commands": args.commands,
              "steps": [], "normalFlashWrites": False, "norCommands": False, "optionByteWrites": False,
              "scope": "REMAINING_BASIC_HARDWARE_NOT_PRODUCT_ACCEPTANCE"}
    row = (f"- **占用中**：Companion 硬件功能检查（{OWNER}，{now()}，peripheral-ram-diag/{out.name}）。"
           f"仅执行未覆盖硬件路径{','.join(args.commands)}；按实际完整结果逐项继续。"
           "正常身份/空闲/DMA保护加载SRAM，不重跑已过五点/按键/NOR/双麦/扬声器。TCA_RESET_PATH短暂复位8口默认再还原；不独立切P4/P7或采外部ADC，不查充电，不写Flash/NOR/NVM/OB，结束恢复实际正式程序并关闭接口。")
    leased = loaded = False

    def section(text):
        return text.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]

    def save():
        (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def check_lease():
        active = [line for line in section(board.read_text(encoding="utf-8-sig")).splitlines() if "**占用中**" in line]
        if active != [row]:
            raise RuntimeError("Unique remaining-hardware lease changed")

    def child(script, argv, folder, timeout):
        check_lease()
        with (out / f"{folder}-stdout.log").open("wb") as stdout, (out / f"{folder}-stderr.log").open("wb") as stderr:
            p = subprocess.run([sys.executable, str(ROOT / "tools" / script), *argv, "--output", str(out / folder)],
                               cwd=ROOT, stdout=stdout, stderr=stderr, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
        path = out / folder / "result.json"
        receipt = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {"result": "NO_CHILD_RECEIPT"}
        receipt["processExitCode"] = p.returncode
        return receipt

    try:
        if build.get("variant") != "REMAINING_HARDWARE_ONLY":
            raise RuntimeError("Not the focused remaining-hardware image")
        text = board.read_text(encoding="utf-8-sig")
        if any("**占用中**" in line for line in section(text).splitlines()):
            result["result"] = "BOARD_OCCUPIED_NO_INTERFACE_OPENED"; return
        if board.read_text(encoding="utf-8-sig") != text:
            raise RuntimeError("Board record changed before acquisition")
        board.write_text(text.replace("## 当前占用", "## 当前占用\n\n" + row, 1), encoding="utf-8-sig"); leased = True
        result["load"] = child("load_wba_peripheral_diag.py", ["--build", str(args.build.resolve())], "load", 70)
        loaded = bool(result["load"].get("sramDiagnosticRunning")); save()
        if not loaded:
            raise RuntimeError("Guarded SRAM entry failed; no remaining hardware command was issued")
        for command in args.commands:
            result["result"] = "RUNNING_" + command; save(); print(result["result"], flush=True)
            receipt = child("capture_wba_peripheral_diag.py", ["--command", command, "--lead-in-seconds", "5" if command == "IMU_SELF_TEST" else "0"], command.lower(), 30)
            raw_path = out / command.lower() / "uart.log"
            proof = {"command": command, "capture": str(raw_path.parent / "result.json"), "receipt": receipt,
                     "uartSha256": hashlib.sha256(raw_path.read_bytes()).hexdigest() if raw_path.exists() else None}
            records = receipt.get("analysis", {}).get("records", [])
            qualified = receipt.get("processExitCode") == 0
            if command == "IMU_SELF_TEST":
                axes = [r for r in records if "sensor" in r and "axis" in r and "delta" in r]
                qualified = qualified and {(r["sensor"], r["axis"]) for r in axes} == {(s, str(a)) for s in ("xl", "gy") for a in range(3)}
                qualified = qualified and all(int(r["min"]) <= int(r["delta"]) <= int(r["max"]) for r in axes)
                qualified = qualified and len([r for r in records if r.get("phase") in ("run52", "idle12_5", "resume52") and r.get("ok") == "1"]) == 3
            elif command == "IMU_INTERRUPT_PATH":
                cycles = [r for r in records if "assert_before_read" in r]
                summaries = [r for r in records if "isolated_path" in r]
                qualified = qualified and len(cycles) == 3 and all(r.get("ok") == "1" and r.get("only_p3_input_changed") == "1" and r.get("io_registers_unchanged") == "1" for r in cycles)
                qualified = qualified and len(summaries) == 1 and summaries[0].get("cycles") == "3" and all(summaries[0].get(k) == "1" for k in ("isolated_path", "stopped", "final_registers_unchanged", "final_pc13"))
            elif command == "TOUCH_RESET_PATH":
                summaries = [r for r in records if "nack_count" in r]
                qualified = qualified and len(summaries) == 1 and summaries[0].get("nack_count") == "3"
                qualified = qualified and all(summaries[0].get(k) == "1" for k in ("baseline", "asserted", "released", "recovered", "p1_levels", "other_bits_unchanged", "latch_restored"))
            elif command == "TCA_RESET_PATH":
                summaries = [r for r in records if "defaults_ok" in r]
                qualified = qualified and len(summaries) == 1 and all(summaries[0].get(k) == "1" for k in ("saved", "initial_nondefault", "defaults_ok", "restored"))
            elif command == "INTERNAL_REFERENCE":
                samples = [r for r in records if "factory_raw" in r]
                summaries = [r for r in records if "minimum_mv" in r]
                qualified = qualified and len(samples) == 32 and all(r.get("valid") == "1" and r.get("adc_error") == "0" for r in samples)
                qualified = qualified and len(summaries) == 1 and summaries[0].get("samples") == "32" and all(summaries[0].get(k) == "1" for k in ("p7_off", "registers_unchanged")) and summaries[0].get("adc_busy") == "0"
            elif command == "RELATIVE_CLOCKS":
                ratios = [r for r in records if "hse_cycles" in r]
                qualified = qualified and len(ratios) == 3 and all(r.get("observed") == "1" and int(r.get("hse_cycles", 0)) > 0 for r in ratios)
            elif command in ("RTC_STOP_WAKE", "IMU_STOP_WAKE"):
                cycles = [r for r in records if "stop_flag" in r]
                summaries = [r for r in records if "rtc_configuration_restored" in r]
                qualified = qualified and len(cycles) == 3 and all(r.get("ok") == "1" and r.get("stop_flag") == "1" for r in cycles)
                qualified = qualified and len(summaries) == 1 and summaries[0].get("cycles") == "3" and all(summaries[0].get(k) == "1" for k in ("imu_stopped", "timer_disabled", "rtc_configuration_restored", "hsi_restored", "debug_restored"))
            else:
                steps = [r for r in records if "rtc_delta" in r]
                qualified = qualified and len(steps) == 3 and all(r.get("valid") == "1" and int(r["rtc_delta"]) > 0 for r in steps)
            proof["qualifiedForThisScope"] = qualified; result["steps"].append(proof); save()
            if not qualified:
                raise RuntimeError(command + " did not qualify; preserve the failure before another check")
        result["result"] = "PASS_REMAINING_BASIC_IMU_SELF_TEST_TOUCH_RESET_LSE_RTC" if set(args.commands) == set(COMMANDS) else "PASS_SELECTED_REMAINING_HARDWARE_SCOPE"
    except Exception as error:
        result.update(result="REMAINING_HARDWARE_CHECK_INCOMPLETE", error=repr(error))
    finally:
        if loaded:
            try:
                result["restore"] = child("capture_wba_peripheral_diag.py", ["--command", "RESET", "--lead-in-seconds", "0"], "restore", 20)
                result["productRestored"] = result["restore"].get("result") == "PRODUCT_UART_IDENTITY_RESTORED_PERIPHERAL_QUALIFICATION_UNCHANGED"
                if not result["productRestored"]:
                    result["resultBeforeRestoreFailure"] = result["result"]; result["result"] = "PRODUCT_RESTORE_UNCONFIRMED_AFTER_HARDWARE_CHECK"
            except Exception as error:
                result.update(restoreError=repr(error), productRestored=False, result="PRODUCT_RESTORE_UNCONFIRMED_AFTER_HARDWARE_CHECK")
        if leased:
            text = board.read_text(encoding="utf-8-sig")
            if row in text and board.read_text(encoding="utf-8-sig") == text:
                replacement = row.replace("**占用中**", "**已释放**", 1) + f"；{now()}实际UART/SWD及子进程已关闭，无BLE；正式恢复={result.get('productRestored')}，结果{result['result']}，证据Companion-Firmware/{out.relative_to(ROOT).as_posix()}。"
                board.write_text(text.replace(row, replacement, 1), encoding="utf-8-sig"); result["leaseReleased"] = True
        result.update(finishedAtLocal=now(), interfacesClosed=True); save()
        print(json.dumps({k: result.get(k) for k in ("result", "error", "productRestored", "leaseReleased")}), flush=True)


if __name__ == "__main__":
    main()
