"""Load the independent peripheral diagnostic into CE SRAM after live idle guards.

No internal Flash, NVM, NOR, option-byte or cloud writes. Normal use requires a
matching idle UART snapshot. A separate boot-only mode accepts a live repeated
early-boot scene and requires the installed image to match before loading SRAM.
Both modes still require actual debug access, correct UID, and inactive DMA.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import threading
import time

import serial
from serial.tools import list_ports

from diagnose_wba_uart import parse_frames
from provision_wba_v11 import probe_lock

ROOT = Path(__file__).resolve().parents[1]
SN = "004400403532510B31333430"
UID = "180010000d50335754363720"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True, help="SRAM diagnostic build.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--owner", default="01a11ba8-9629-7350-976b-fd50a1045a76")
    parser.add_argument("--boot-loop-only", action="store_true",
                        help="Diagnose peripherals without app startup; requires live repeated BOOT0/jump_app and --installed-image")
    parser.add_argument("--installed-image", type=Path,
                        help="Known installed boot+app binary; mandatory in boot-only mode, compared below pairing NVM")
    args = parser.parse_args()
    if args.boot_loop_only and args.installed_image is None:
        parser.error("Boot-only diagnostics require the exact known installed boot+app binary")
    build_path = args.build.resolve(); build = json.loads(build_path.read_text(encoding="utf-8"))
    image = (build_path.parent / build["image"]).resolve()
    if image.parent != build_path.parent or build["result"] != "BUILT_NOT_RUN":
        raise RuntimeError("Unexpected diagnostic build receipt or path")
    data = image.read_bytes()
    if (hashlib.sha256(data).hexdigest() != build["imageSha256"] or build["loadAddress"] != 0x20000000
            or not 8 <= len(data) < 0x1A000 or build["initialSp"] != 0x20020000
            or build["requiredUid"] != UID or build["requiredProbe"] != SN
            or not 0x20000000 <= build["entryAddress"] < 0x20000000 + len(data)):
        raise RuntimeError("Diagnostic identity, geometry or image mismatch")
    # A later product edit cannot silently change this frozen diagnostic.
    for name, expected in build["sources"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Diagnostic source changed since build: " + name)
    if hashlib.sha256((ROOT / "platform/stm32wba55_companion_v11/peripheral_diag/ram.ld").read_bytes()).hexdigest() != build["linkerSha256"]:
        raise RuntimeError("Diagnostic linker changed since build")
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    result = {"result": "PREFLIGHT", "startedAtLocal": datetime.now().isoformat(),
              "requiredUid": UID, "probeSerial": SN, "diagnosticSha256": build["imageSha256"],
              "sramLoadStarted": False, "sramDiagnosticRunning": False, "internalFlashWrites": False,
              "norCommandsIssued": False, "optionByteWrites": False, "uartClosed": True,
              "debugProcessClosed": True, "hardwareAcceptance": "NOT_RUN"}
    result["bootLoopOnlyMode"] = args.boot_loop_only
    installed_guard = ""
    if args.boot_loop_only:
        installed = args.installed_image.resolve().read_bytes()
        if not 0x8008 <= len(installed) <= 0x7C000:
            raise RuntimeError("Installed image exceeds boot/app extent or omits application vectors")
        padded = out / "expected-installed-below-nvm.bin"
        padded.write_bytes(installed + b"\xff" * (0x7C000 - len(installed)))
        result["expectedInstalledSha256"] = hashlib.sha256(installed).hexdigest()
        installed_guard = f"    verify_image {{{padded.as_posix()}}} 0x08000000 bin\n"
    link = None; stop = threading.Event(); reader = None; raw = bytearray(); api_log = ""

    def lease() -> None:
        s = (ROOT.parent / "docs/board_operations.md").read_text(encoding="utf-8-sig")
        section = s.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]
        active = [r for r in section.splitlines() if "**占用中**" in r]
        if len(active) != 1 or args.owner not in active[0] or "peripheral-ram-diag" not in active[0]:
            raise RuntimeError("Unique peripheral-ram-diag lease is absent or changed")

    def save() -> None:
        (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def capture() -> None:
        assert link is not None
        try:
            with (out / "diagnostic-uart.log").open("wb") as log:
                while not stop.is_set():
                    chunk = link.read(min(max(link.in_waiting, 1), 4096))
                    raw.extend(chunk); log.write(chunk); log.flush()
                    for line in bytes(raw).decode("ascii", errors="replace").splitlines():
                        # The paused product may leave an unfinished UART line.
                        # Match the complete diagnostic marker, not a line boundary.
                        marker = "HELLO id=COMP_PERIPH_RAM_V1 "
                        offset = line.find(marker)
                        if offset < 0:
                            continue
                        line = line[offset:]
                        fields = dict(t.split("=", 1) for t in line.split()[1:] if "=" in t)
                        if (fields.get("id") == "COMP_PERIPH_RAM_V1" and fields.get("uid") == UID
                                and fields.get("target_ok") == "1" and fields.get("flash_kib") == "512"
                                and fields.get("device") == "492"):
                            (out / "diagnostic-hello.ok").write_text(line + "\n", encoding="ascii")
                            result["hello"] = fields
                    if len(raw) > 2 * 1024 * 1024:
                        raise RuntimeError("Diagnostic UART exceeded its bound")
        except Exception as e:
            result["uartReaderError"] = repr(e)

    try:
        lease(); save()
        ports = [p.device for p in list_ports.comports() if p.serial_number == SN]
        if len(ports) != 1:
            raise RuntimeError("Fixed V3 UART mapping is not unique")
        link = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=1)
        link.dtr = link.rts = False; link.port = ports[0]
        link.open(); result["uartClosed"] = False
        lease(); link.write(b"?"); link.flush()
        before = bytearray(); until = time.monotonic() + 8
        frames = []
        while time.monotonic() < until:
            before.extend(link.read(min(max(link.in_waiting, 1), 4096)))
            frames, _ = parse_frames(bytes(before))
            if frames:
                break
        (out / "before-uart.log").write_bytes(before)
        if args.boot_loop_only:
            counts = {name: before.count(f"BOOT0 phase={name}".encode("ascii")) for name in
                      ("early_init", "watchdog_ready", "storage_hardware_ready", "jump_app")}
            if frames or b"BOOT1" in before or b"DIAG1" in before or min(counts.values()) < 5:
                raise RuntimeError("Live scene is not the explicit app-not-started boot cycle; use normal idle guards")
            result["bootPhaseCounts"] = counts
        else:
            if not frames:
                raise RuntimeError("No complete normal product snapshot; do not connect debug or load SRAM")
            snapshot = frames[-1]; s = snapshot["sections"]
            if (s["ID"]["uid"] != UID or s["ID"]["ui"] != 67 or s["AUDIO"]["mic_run"] != 0
                    or s["BLE"]["linked"] != 0 or s["STORAGE"]["rec_state"] not in (1, 6)
                    or s["STORAGE"]["rec_fault"] != 0 or s["STORAGE"]["recording_ready"] != 1
                    or int(s["POWER"]["sleep_block"], 16) & sum(1 << b for b in (0, 1, 8, 11, 12, 13, 14))):
                raise RuntimeError("Product identity or live operation guard rejected diagnostic loading")
            result["productSnapshot"] = snapshot
        save()
        executable = shutil.which("openocd")
        if not executable:
            raise RuntimeError("OpenOCD is missing")
        scripts = Path(executable).parent.parent / "openocd/scripts"
        if not (scripts / "interface/stlink.cfg").is_file():
            raise RuntimeError("Bundled OpenOCD ST-Link scripts missing")
        cfg = out / "load-sram.cfg"
        # RM0493 section 43.4: AP0 is the system debug port, while AP1 gives
        # Cortex-M33 and system memory access. Do not source stm32wbax.cfg:
        # its bundled examine/reset hooks use different DBGMCU addresses.
        tcl = '''gdb port disabled
tcl port disabled
telnet port disabled
source [find interface/stlink.cfg]
transport select swd
adapter serial @SN@
adapter speed 1000
reset_config none
swd newdap companion cpu -expected-id 0x6ba02477
dap create companion.dap -chain-position companion.cpu
target create companion.cpu cortex_m -endian little -dap companion.dap -ap-num 1
cortex_m reset_config sysresetreq
set frozen 0
set halted 0
set loaded 0
set launched 0
set outcome [catch {
    init
    if {([lindex [read_memory 0xE0044000 32 1] 0] & 0xfff) != 0x492} {error "Device ID mismatch"}
    if {[lindex [read_memory 0x0BF907A0 16 1] 0] != 512} {error "Flash geometry mismatch"}
    if {([lindex [read_memory 0x40022040 32 1] 0] & 0x80000000) != 0} {error "TZEN differs from qualification target"}
    set expected {@UID@}
    for {set repeat 0} {$repeat < 2} {incr repeat} {
        set actual [read_memory 0x0BF90700 8 12]
        for {set i 0} {$i < 12} {incr i} {
            if {[lindex $actual $i] != [lindex $expected $i]} {error "UID mismatch"}
        }
    }
    echo IDENTITY_VERIFIED
    set freeze_original [lindex [read_memory 0xE0044008 32 1] 0]
    mww 0xE0044008 [expr {$freeze_original | 0x1000}]
    set frozen 1
    set halted 1
    echo TARGET_HALT_REQUESTED
    halt
    wait_halt 1000
    echo TARGET_HALT_CONFIRMED
    dump_image {@BEFORE@} 0x08000000 0x80000
@INSTALLED_GUARD@
    # Confirm all GPDMA channels are disabled before overwriting SRAM.
    # A normal DIAG snapshot established mic/playback/transfer/update idle.
    # Pinned STM32WBA55 CMSIS: CCR = GPDMA1_NS + 0x64 + channel * 0x80.
    for {set channel 0} {$channel < 8} {incr channel} {
        set ccr [expr {0x40020064 + $channel * 0x80}]
        if {([lindex [read_memory $ccr 32 1] 0] & 1) != 0} {error "DMA channel still enabled"}
    }
    echo SRAM_LOAD_BEGIN
    set loaded 1
    load_image {@IMAGE@} 0x20000000 bin
    verify_image {@IMAGE@} 0x20000000 bin
    dump_image {@AFTER@} 0x08000000 0x80000
    verify_image {@BEFORE@} 0x08000000 bin
    reg primask 1
    reg control 0
    reg msp 0x20020000
    reg xpsr 0x01000000
    mww 0xE0044008 $freeze_original
    set frozen 0
    resume @ENTRY@
    set halted 0
    set launched 1
    for {set wait 0} {$wait < 80 && ![file exists {@HELLO@}]} {incr wait} {sleep 50}
    if {![file exists {@HELLO@}]} {error "SRAM diagnostic HELLO not observed"}
    echo SRAM_DIAGNOSTIC_HELLO_CONFIRMED
} message]
if {$frozen} {catch {mww 0xE0044008 $freeze_original}}
if {$outcome} {
    echo "DIAGNOSTIC_LOAD_FAILED: $message"
    if {$loaded} {
        if {[catch {reset run} recovery]} {echo "PRODUCT_RESET_FAILED: $recovery"} else {echo PRODUCT_RESET_REQUESTED}
    } elseif {$halted} {catch {resume}}
    shutdown error
} else {shutdown}
'''
        replacements = {"@SN@": SN, "@UID@": " ".join(str(b) for b in bytes.fromhex(UID)),
                        "@BEFORE@": (out / "before-internal.bin").as_posix(),
                        "@AFTER@": (out / "after-internal.bin").as_posix(),
                        "@IMAGE@": image.as_posix(), "@ENTRY@": hex(build["entryAddress"]),
                        "@HELLO@": (out / "diagnostic-hello.ok").as_posix(),
                        "@INSTALLED_GUARD@": installed_guard}
        for token, value in replacements.items():
            tcl = tcl.replace(token, value)
        cfg.write_text(tcl, encoding="ascii")
        with probe_lock(SN):
            lease()
            reader = threading.Thread(target=capture); reader.start()
            result["debugProcessClosed"] = False; save()
            try:
                p = subprocess.run([executable, "-s", str(scripts), "-f", str(cfg)],
                                   capture_output=True, text=True, timeout=45)
                api_log = p.stdout + p.stderr; result["openocdExitCode"] = p.returncode
            except subprocess.TimeoutExpired as e:
                api_log = ((e.stdout or b"") + (e.stderr or b"")).decode("utf-8", errors="replace")
                raise RuntimeError("Bounded loader timed out; program was killed; target state requires recovery")
            finally:
                result["debugProcessClosed"] = True
                result["sramLoadStarted"] = "SRAM_LOAD_BEGIN" in api_log
                result["productResetRequestedOnFailure"] = "PRODUCT_RESET_REQUESTED" in api_log
                (out / "openocd.log").write_text(api_log, encoding="utf-8")
        stop.set(); reader.join(timeout=2)
        if result.get("openocdExitCode") != 0 or "SRAM_DIAGNOSTIC_HELLO_CONFIRMED" not in api_log:
            raise RuntimeError("SRAM load or live diagnostic identity confirmation failed")
        before_internal = (out / "before-internal.bin").read_bytes()
        after_internal = (out / "after-internal.bin").read_bytes()
        if len(before_internal) != 0x80000 or before_internal != after_internal:
            raise RuntimeError("Internal Flash/NVM before/after comparison differs")
        result.update(result="SRAM_DIAGNOSTIC_RUNNING_PERIPHERALS_UNTESTED", sramDiagnosticRunning=True,
                      internalFlashAndNvmUnchanged=True,
                      internalSha256=hashlib.sha256(before_internal).hexdigest())
    except Exception as e:
        result.update(result="SRAM_DIAGNOSTIC_NOT_CONFIRMED", error=repr(e))
    finally:
        stop.set()
        if reader is not None:
            reader.join(timeout=2)
        if link is not None and link.is_open:
            link.close()
        result.update(uartClosed=True, finishedAtLocal=datetime.now().isoformat())
        save(); print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    raise SystemExit(0 if result["sramDiagnosticRunning"] else 1)


if __name__ == "__main__":
    main()
