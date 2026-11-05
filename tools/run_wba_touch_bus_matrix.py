"""Locate touch NACKs with one frequency/transaction matrix and a reset comparison."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import traceback
from peripheral_diag_uart import write_json_atomic

ROOT = Path(__file__).resolve().parents[1]
OWNER = "01a11ba8-9629-7350-976b-fd50a1045a76"


def now():
    return datetime.now().isoformat(timespec="milliseconds")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build = args.build.resolve(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    board = ROOT.parent / "docs/board_operations.md"
    row = (f"- **占用中**：Companion 硬件功能检查（{OWNER}，{now()}，peripheral-ram-diag/{out.name}）。"
           "定位触摸持续NACK；受保护SRAM诊断，100/50/25/10kHz及RepeatedSTART/STOP读对照，复位释放等350ms。"
           "先保留不复位矩阵，只有真实失败才一次10ms TP_RST脉冲对照；不动屏幕RES/P4/P7，不查充电，不写Flash/NOR/NVM/OB，结束恢复正式产品并关闭接口。")
    result = {"result": "PREPARING", "startedAtLocal": now(), "scope": "TOUCH_I2C_FREQUENCY_AND_TRANSACTION_COMPARISON",
              "build": str(build), "internalFlashWrites": False, "physicalTouchQualification": "NOT_RUN"}
    leased = loaded = False

    def section(text):
        return text.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]

    def save():
        write_json_atomic(out / "result.json", result)

    def check_lease():
        active = [l for l in section(board.read_text(encoding="utf-8-sig")).splitlines() if "**占用中**" in l]
        if active != [row]:
            raise RuntimeError("Own unique touch lease changed")

    def child(script, extra, folder, timeout):
        check_lease()
        with (out / f"{folder}-stdout.log").open("wb") as stdout, (out / f"{folder}-stderr.log").open("wb") as stderr:
            p = subprocess.run([sys.executable, str(ROOT / "tools" / script), *extra, "--output", str(out / folder)],
                               cwd=ROOT, stdout=stdout, stderr=stderr, timeout=timeout,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        path = out / folder / "result.json"
        r = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {"result": "NO_CHILD_RESULT"}
        r["processExitCode"] = p.returncode
        return r

    def stable_rows(receipt):
        return [r for r in receipt.get("analysis", {}).get("busMatrix", [])
                if r.get("ok") == "32" and r.get("failed") == "0"
                and r.get("id_a3") == "64" and r.get("fw_a6") == "01" and r.get("id_a8") == "11"]

    def restore():
        nonlocal loaded
        if loaded:
            r = child("capture_wba_peripheral_diag.py", ["--command", "RESET", "--lead-in-seconds", "0"], "restore", 15)
            result["restore"] = r
            result["productRestored"] = r.get("result") == "PRODUCT_UART_IDENTITY_RESTORED_PERIPHERAL_QUALIFICATION_UNCHANGED"
            loaded = False

    try:
        text = board.read_text(encoding="utf-8-sig")
        if any("**占用中**" in l for l in section(text).splitlines()):
            raise RuntimeError("Board occupied; no hardware opened")
        if board.read_text(encoding="utf-8-sig") != text:
            raise RuntimeError("Shared record changed before acquisition")
        board.write_text(text.replace("## 当前占用", "## 当前占用\n\n" + row, 1), encoding="utf-8-sig"); leased = True
        save()
        r = child("load_wba_peripheral_diag.py", ["--build", str(build)], "load", 70)
        result["load"] = r; loaded = bool(r.get("sramDiagnosticRunning"))
        if not loaded:
            raise RuntimeError("Guarded diagnostic did not start; touch commands not issued")
        first = child("capture_wba_peripheral_diag.py", ["--command", "TOUCH_MATRIX", "--lead-in-seconds", "0"], "without-reset", 70)
        result["withoutReset"] = first; result["stableWithoutReset"] = stable_rows(first); save()
        print(json.dumps({"stage": "WITHOUT_RESET", "stableRows": result["stableWithoutReset"],
                          "matrix": first.get("analysis", {}).get("busMatrix", [])}), flush=True)
        rows = first.get("analysis", {}).get("busMatrix", [])
        if len(rows) == 8 and len(result["stableWithoutReset"]) < 8:
            result["resetComparisonReason"] = "Actual NACK/invalid round observed after 350ms settle; one reset compares retained FT6336U state with a fresh reset release."
            second = child("capture_wba_peripheral_diag.py", ["--command", "TOUCH_MATRIX_RESET", "--lead-in-seconds", "0"], "one-reset", 70)
            result["withOneReset"] = second; result["stableWithOneReset"] = stable_rows(second); save()
            print(json.dumps({"stage": "ONE_RESET", "stableRows": result["stableWithOneReset"],
                              "matrix": second.get("analysis", {}).get("busMatrix", [])}), flush=True)
        candidates = result["stableWithoutReset"] + result.get("stableWithOneReset", [])
        result["workingBusCandidates"] = candidates
        result["result"] = "TOUCH_STABLE_BUS_CANDIDATE_PHYSICAL_GESTURES_PENDING" if candidates else "TOUCH_NO_STABLE_BUS_MODE_CAUSE_UNRESOLVED"
        if not rows:
            result["result"] = "TOUCH_MATRIX_NOT_COMPLETED"
        restore()
    except Exception as error:
        result.update(result="TOUCH_MATRIX_STAGE_FAILED", error=repr(error), traceback=traceback.format_exc())
    finally:
        try:
            restore()
        except Exception as error:
            result["restoreError"] = repr(error)
        result.update(finishedAtLocal=now(), uartClosed=True, debugProcessesClosed=True)
        if leased:
            text = board.read_text(encoding="utf-8-sig")
            active = [l for l in section(text).splitlines() if "**占用中**" in l]
            if active == [row] and board.read_text(encoding="utf-8-sig") == text:
                replacement = row.replace("**占用中**", "**已释放**", 1) + (
                    f"；{now()} 自身UART/SWD及命令子进程实际关闭，无BLE；矩阵及正式程序恢复见Companion-Firmware/{out.relative_to(ROOT).as_posix()}/result.json。")
                board.write_text(text.replace(row, replacement, 1), encoding="utf-8-sig")
                result["leaseReleased"] = True
        save()
        print(json.dumps({"result": result["result"], "output": str(out), "error": result.get("error"),
                          "productRestored": result.get("productRestored"), "leaseReleased": result.get("leaseReleased")}), flush=True)


if __name__ == "__main__":
    main()
