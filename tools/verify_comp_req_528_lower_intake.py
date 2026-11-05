from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_PRODUCTION = "154700e02307d94441ebabfe9127e1501f197af4"
FOCUSED_525_VERIFIER = "8428CDC8CAF1C15DBA274909960C282E37506EB25F98D462C37E5CE7B2969DFE"
CHECKONLY_KEYS = ("hardware_contact", "programmer", "serial", "write", "reset",
                  "refresh", "popup", "retry")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def blob(path: Path) -> str:
    """Read the tracked index blob, independent of worktree filters/EOL."""
    relative = path.resolve().relative_to(ROOT).as_posix()
    raw = subprocess.check_output(["git", "ls-files", "-s", "--", relative],
                                  cwd=ROOT, text=True)
    entries = [line for line in raw.splitlines() if line.strip()]
    if len(entries) != 1:
        raise RuntimeError(f"expected one tracked index entry for {relative}")
    fields = entries[0].split()
    if len(fields) < 4 or fields[2] != "0" or fields[3] != relative:
        raise RuntimeError(f"invalid tracked index entry for {relative}: {entries[0]}")
    return fields[1]


def blob_self_check(path: Path) -> dict:
    """Exercise the EOL/path regression case without using it as identity."""
    relative = path.resolve().relative_to(ROOT).as_posix()
    index_blob = blob(path)
    worktree_probe = subprocess.check_output(["git", "hash-object", str(path)],
                                             cwd=ROOT, text=True).strip()
    return {
        "path": relative,
        "index_blob": index_blob,
        "worktree_hash_object": worktree_probe,
        "worktree_filter_mismatch_detected": worktree_probe != index_blob,
        "identity_source": "git ls-files -s index entry",
    }


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def run_json(command: list[str], env: dict[str, str] | None = None, cwd: Path | None = None):
    return subprocess.run(command, cwd=cwd or ROOT, env=env, capture_output=True,
                          text=True, check=False)


def parse_int(text: str, key: str) -> int | None:
    match = re.search(rf"\b{re.escape(key)}=(\d+)", text)
    return int(match.group(1)) if match else None


def validate_build(entry: dict, out: Path, head: str) -> bool:
    return bool(
        entry.get("fresh") is True and entry.get("source_commit") == head and
        entry.get("command") and entry.get("log_path") and
        (out / entry["log_path"]).is_file() and entry.get("hex_sha256") and
        entry.get("log_sha256") and entry.get("elf_sha256") and
        entry.get("map_path") and (out / entry["map_path"]).is_file())


def fresh_arm_build(out: Path, mode: str, head: str, failures: list[str]) -> dict:
    project = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup"
    make = Path("C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
                "com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506/"
                "tools/bin/make.exe")
    toolchain = Path("C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
                     "com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/"
                     "tools/bin")
    build_dir = out / "fresh_build" / mode
    build_dir.mkdir(parents=True, exist_ok=True)
    target = ("Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime" if mode == "bounded"
              else "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntimeContinuous")
    macro = ("EPAPER_SSD1681_R7_VISUAL_RUNTIME_DIAGNOSTIC=1" if mode == "bounded"
             else "EPAPER_SSD1681_R7_VISUAL_RUNTIME_CONTINUOUS_DIAGNOSTIC=1")
    command = [str(make), "-f", "Makefile", "-j2", "C_OPT=-O2",
               "TOOLCHAIN=" + str(toolchain).replace("\\", "/"),
               "EPAPER_SSD1681_BRINGUP=1", "EPAPER_MENU=1", macro,
               "EPAPER_SSD1681_HAS_BUSY=1",
               "BUILD_DIR=" + str(build_dir).replace("\\", "/"), "TARGET=" + target]
    log_path = Path("fresh_build") / mode / "build.log"
    proc = subprocess.run(command, cwd=project, capture_output=True, text=True,
                          check=False)
    raw_log = proc.stdout + proc.stderr
    stable_log = raw_log.replace(str(out).replace("\\", "/"), "<OUT_ROOT>")
    (out / log_path).write_text(stable_log, encoding="utf-8")
    hex_path = build_dir / (target + ".hex")
    elf_path = build_dir / (target + ".elf")
    map_path = build_dir / (target + ".map")
    stable_command = [item.replace(str(out).replace("\\", "/"), "<OUT_ROOT>")
                      for item in command]
    entry = {"mode": mode, "fresh": proc.returncode == 0,
             "source_commit": head, "command": stable_command,
             "log_path": log_path.as_posix(),
             "hex_path": (Path("fresh_build") / mode / (target + ".hex")).as_posix(),
             "elf_path": (Path("fresh_build") / mode / (target + ".elf")).as_posix(),
             "map_path": (Path("fresh_build") / mode / (target + ".map")).as_posix(),
             "exit_code": proc.returncode,
             "log_sha256": sha(out / log_path)}
    if proc.returncode != 0 or not hex_path.is_file() or not elf_path.is_file() or not map_path.is_file():
        failures.append(f"fresh {mode} O2 build failed or incomplete")
    else:
        entry.update(hex_sha256=sha(hex_path), elf_sha256=sha(elf_path))
    return entry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", required=True)
    args = parser.parse_args()
    out = (ROOT / args.out_root).resolve()
    if ROOT not in out.parents:
        raise SystemExit("out root must be below repository")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    failures: list[str] = []

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   text=True).strip()
    accepted = subprocess.run(["git", "cat-file", "-e", ACCEPTED_PRODUCTION + "^{commit}"],
                              cwd=ROOT, check=False).returncode == 0
    if not accepted:
        failures.append("accepted production checkpoint is missing")

    protected = {
        "driver": {
            "path": "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
            "physical_sha256": "F52A7E853BFE2E66680F08420941265CFF163FB579B2D3870128FC72C79E035F",
            "git_blob": "f856d7ce0b8915e5059620c3faa97aa06b06eb4e",
        },
        "r7_header": {
            "path": "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h",
            "physical_sha256": "9571CF9F896B6C14451BAA7348CB717643B4963AE834B0A554E0C2ED2C7E8D35",
            "git_blob": "2220da0c1113a5cdad7028aeae578d9fe26e936f",
        },
    }
    blob_self_checks = {}
    blob_source = inspect.getsource(blob)
    if "hash-object" in blob_source:
        failures.append("blob identity implementation regressed to worktree hash-object")
    for item in protected.values():
        path = ROOT / item["path"]
        if not path.is_file():
            failures.append(f"protected identity mismatch: {item['path']}")
            continue
        try:
            blob_self_checks[item["path"]] = blob_self_check(path)
            tracked_blob = blob(path)
        except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
            failures.append(f"protected index lookup failed: {item['path']}: {error}")
            continue
        if (sha(path) != item["physical_sha256"] or
                tracked_blob != item["git_blob"] or
                blob_self_checks[item["path"]]["index_blob"] != tracked_blob):
            failures.append(f"protected identity mismatch: {item['path']}")

    builds = {mode: fresh_arm_build(out, mode, head, failures)
              for mode in ("bounded", "continuous")}
    if not all(validate_build(entry, out, head) for entry in builds.values()):
        failures.append("fresh build provenance is incomplete")

    checkonly_run_root = out / "r7_checkonly"
    checkonly_run_root.mkdir(parents=True, exist_ok=True)
    checkonly_proc = run_json(["pwsh", "-NoProfile", "-File",
                               str(ROOT / "tools/run_comp_req_466_r7_runtime_host_fixture.ps1"),
                               "-CheckOnly", "-OutRoot",
                               str(checkonly_run_root.relative_to(ROOT)).replace("/", "\\")],
                              cwd=checkonly_run_root)
    checkonly_path = checkonly_run_root / "host-result.json"
    checkonly_actual = json.loads(checkonly_path.read_text(encoding="utf-8")) if checkonly_path.is_file() else {}
    if checkonly_proc.returncode != 0 or checkonly_actual.get("status") != "CHECK_ONLY_PASS":
        failures.append("real R7 CheckOnly path failed")

    bridge_evidence_path = out / "bridge_machine_ready.json"
    bridge_evidence = {
        "schema": "companion.comp_req_528.bridge_evidence.v1",
        "status": "PASS" if checkonly_actual.get("checkonly") == {k: 0 for k in CHECKONLY_KEYS} and
                  all(entry.get("fresh") is True and entry.get("source_commit") == head for entry in builds.values()) else "NO_GO",
        "source_commit": head,
        "protected": {
            "driver_git_blob": protected["driver"]["git_blob"],
            "header_git_blob": protected["r7_header"]["git_blob"],
            "driver_physical_sha256": protected["driver"]["physical_sha256"],
            "header_physical_sha256": protected["r7_header"]["physical_sha256"],
        },
        "build": {
            "bounded_and_continuous": all(entry.get("fresh") is True and entry.get("source_commit") == head for entry in builds.values()),
            "bounded": builds["bounded"],
            "continuous": builds["continuous"],
        },
        "checkonly": checkonly_actual.get("checkonly", {}),
    }
    bridge_evidence_path.write_text(json.dumps(bridge_evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Run the raw-touch producer before 525 so the recording verifier receives a
    # package-local, current-source handoff instead of the retired canonical cache.
    raw_runner = ROOT / "tools" / "run_comp_req_501_raw_touch_trace.ps1"
    raw_out = out / "raw_touch"
    raw_out.mkdir(parents=True, exist_ok=True)
    praw = run_json(["pwsh", "-NoProfile", "-File", str(raw_runner),
                     "-OutRoot", str(raw_out.relative_to(ROOT)).replace("/", "\\")],
                    cwd=raw_out)
    raw_result_path = raw_out / "result.json"
    if praw.returncode != 0 or not raw_result_path.is_file():
        failures.append("raw-touch runner failed")
        raw_result = {}
        raw_observed = {}
    else:
        raw_result = json.loads(raw_result_path.read_text(encoding="utf-8-sig"))
        line = next((x for x in raw_result.get("stdout", "").splitlines()
                     if x.startswith("{")), "{}")
        raw_observed = json.loads(line)
        shutil.copy2(raw_result_path, out / "raw_touch_result.json")
        if (raw_out / "verifier.json").is_file():
            shutil.copy2(raw_out / "verifier.json", out / "raw_touch_verifier.json")
    r7_handoff_path = out / "r7_handoff_input.json"
    r7_handoff_path.write_text(json.dumps({
        "schema": "companion.comp_req_528.current_r7_handoff_input.v1",
        "source_commit": head,
        "candidate_commits": [head],
        "raw_result_sha256": sha(raw_result_path) if raw_result_path.is_file() else "",
        "protected": protected,
        "blob_self_check": blob_self_checks,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Execute the real compiled 525 fixture in this package root.
    recording_out = out / "recording_525"
    env = os.environ.copy()
    env["COMP_REQ_515_OUT"] = str(recording_out)
    env["COMP_REQ_515_BOUNDED_HEX"] = str(out / "fresh_build" / "bounded" / "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime.hex")
    env["COMP_REQ_515_BOUNDED_ELF"] = str(out / "fresh_build" / "bounded" / "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime.elf")
    env["COMP_REQ_515_CONTINUOUS_HEX"] = str(out / "fresh_build" / "continuous" / "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntimeContinuous.hex")
    env["COMP_REQ_515_CONTINUOUS_ELF"] = str(out / "fresh_build" / "continuous" / "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntimeContinuous.elf")
    env["COMP_REQ_515_R7_HANDOFF"] = str(r7_handoff_path)
    p525 = run_json(["python", "-B", "tools/verify_comp_req_513_recording.py"], env)
    recording_verifier = recording_out / "verifier.json"
    if p525.returncode != 0 or not recording_verifier.is_file():
        failures.append("focused 525 executable verifier failed")
        recording = {}
    else:
        recording = json.loads(recording_verifier.read_text(encoding="utf-8"))
    if recording.get("status") != "PASS":
        failures.append("focused 525 result is not PASS")
    if recording.get("checkonly") != {k: 0 for k in CHECKONLY_KEYS}:
        failures.append("focused 525 CheckOnly is not all zero")

    # Run the real 24-report integration verifier into this package root.
    touch_out = out / "touch_integration"
    touch_out.mkdir(parents=True, exist_ok=True)
    ptouch = run_json(["pwsh", "-NoProfile", "-File",
                       str(ROOT / "tools/run_comp_req_466_r7_touch_integration_fixture.ps1"),
                       "-OutRoot", str(touch_out.relative_to(ROOT)).replace("/", "\\")],
                      cwd=touch_out)
    touch_result_path = touch_out / "touch-integration-result.json"
    touch_result = json.loads(touch_result_path.read_text(encoding="utf-8-sig")) if touch_result_path.is_file() else {}
    if touch_result:
        touch_result_path.write_text(json.dumps(touch_result, indent=2, sort_keys=True) + "\n",
                                     encoding="utf-8")
    touch_stdout = touch_result.get("stdout", "")
    touch_gate = run_json(["python", "-B", "tools/verify_comp_req_466_r7_touch_integration.py",
                           "--touch-result", str(touch_result_path),
                           "--touch-machine-ready", str(touch_out / "MACHINE_READY.json"),
                           "--bridge-evidence", str(bridge_evidence_path),
                           "--runner-out-root", str(touch_out.relative_to(ROOT)).replace("/", "\\")])
    touch_gate_ok = touch_gate.returncode == 0
    # The verifier reruns the fixture; canonicalize its PowerShell hashtable
    # ordering after that run so consumer artifacts are byte-stable.
    if touch_result_path.is_file():
        touch_result = json.loads(touch_result_path.read_text(encoding="utf-8-sig"))
        touch_result_path.write_text(json.dumps(touch_result, indent=2, sort_keys=True) + "\n",
                                     encoding="utf-8")
    touch_observed = {
        "aggregate_reports": parse_int(touch_stdout, "aggregate_reports"),
        "expected_inputs": parse_int(touch_stdout, "expected_inputs"),
        "consumed": parse_int(touch_stdout, "consumed"),
        "p95_ms": parse_int(touch_stdout, "p95_ms"),
        "sequence_bitmap": re.search(r"sequence_bitmap=(0x[0-9A-Fa-f]+)", touch_stdout).group(1)
        if re.search(r"sequence_bitmap=(0x[0-9A-Fa-f]+)", touch_stdout) else None,
        "phases": "before,during,after" if "phases=before,during,after" in touch_stdout else None,
        "busy_touch": parse_int(touch_stdout, "busy_touch"),
        "phantom_hold": parse_int(touch_stdout, "phantom_hold"),
        "phantom_menu": parse_int(touch_stdout, "phantom_menu"),
        "phantom_recording": parse_int(touch_stdout, "phantom_recording"),
    }
    if ptouch.returncode != 0 or touch_result.get("status") != "PASS" or not touch_gate_ok:
        failures.append("real 24-report touch verifier failed")
    if (touch_observed.get("aggregate_reports") != 24 or touch_observed.get("expected_inputs") != 24 or
            touch_observed.get("consumed") != 24 or touch_observed.get("p95_ms") is None or
            touch_observed.get("p95_ms") > 20 or touch_observed.get("busy_touch") != 1 or
            any(touch_observed.get(key) != 0 for key in ("phantom_hold", "phantom_menu", "phantom_recording"))):
        failures.append("touch artifact does not prove 24/24 and p95<=20")
    for key, expected in (("event_records", 21), ("pair_records", 59),
                          ("pixel_noop_records", 10), ("frame_hash_records", 59),
                          ("render_records", 59)):
        if raw_observed.get(key) != expected:
            failures.append(f"raw-touch observed {key} != {expected}")

    # The accepted R7 static/parser gates derive command and timing rules from
    # source. Their stdout is evidence; the package never restates those rules
    # as a manually authored PASS object.
    static_run = run_json(["python", "-B", "tools/verify_wb55_ssd1681_r7_locked_v9_static.py"])
    parser_run = run_json(["python", "-B", "tools/verify_wb55_ssd1681_r7_locked_v9_parser.py", "--self-test"])
    r7_static = {"command": ["python", "-B", "tools/verify_wb55_ssd1681_r7_locked_v9_static.py"],
                 "exit_code": static_run.returncode, "stdout": static_run.stdout.strip()}
    r7_parser = {"command": ["python", "-B", "tools/verify_wb55_ssd1681_r7_locked_v9_parser.py", "--self-test"],
                 "exit_code": parser_run.returncode, "stdout": parser_run.stdout.strip()}
    if static_run.returncode != 0 or parser_run.returncode != 0:
        failures.append("R7 static/parser gate failed")

    host_chain_files = {
        "runner": "tools/run_wb55_ssd1681_r7_locked_v9.ps1",
        "monitor": "tools/monitor_wb55_ssd1681_r7_locked_v9.ps1",
        "supervisor": "tools/supervise_wb55_ssd1681_r7_locked_v9.ps1",
        "launcher": "tools/start_wb55_ssd1681_r7_locked_v9.ps1",
    }
    host_chain = {}
    for name, path_text in host_chain_files.items():
        path = ROOT / path_text
        if not path.is_file():
            failures.append(f"missing R7 host chain file: {path_text}")
        else:
            host_chain[name] = {"path": path_text, "sha256": sha(path),
                                "git_blob": blob(path)}

    source_paths = [
        "app/companion_pendant/touch/touch_recording_boundary.c",
        "app/companion_pendant/touch/touch_recording_boundary.h",
        "app/companion_pendant/touch/touch_visual_decision.c",
        "app/companion_pendant/touch/touch_visual_decision.h",
        "app/companion_pendant/touch/touch_visual_board_dispatch.c",
        "app/companion_pendant/touch/touch_visual_board_dispatch.h",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c",
        "tools/comp_req_513_recording_trace.c",
        "tools/run_comp_req_513_recording_trace.ps1",
        "tools/verify_comp_req_513_recording.py",
    ]
    sources = {path: {"sha256": sha(ROOT / path), "git_blob": blob(ROOT / path)}
               for path in source_paths if (ROOT / path).is_file()}
    if len(sources) != len(source_paths):
        failures.append("current source binding is incomplete")

    old_handoff = ROOT / ".cache" / "validation" / "comp-req-501-faraday-handoff.json"
    old = json.loads(old_handoff.read_text(encoding="utf-8")) if old_handoff.is_file() else {}
    stale_candidates = old.get("candidate_commits", [])
    stale_rejected = ACCEPTED_PRODUCTION not in stale_candidates and head not in stale_candidates
    if not stale_rejected:
        failures.append("stale pre-154700e handoff was not rejected")

    checkonly = checkonly_actual.get("checkonly", {})
    if checkonly != {k: 0 for k in CHECKONLY_KEYS}:
        failures.append("real R7 CheckOnly is not zero")
    if not raw_result.get("checkonly") or any(raw_result["checkonly"].get(k) != 0 for k in CHECKONLY_KEYS):
        failures.append("raw-touch CheckOnly is not zero")

    source_text = (ROOT / "tools/comp_req_513_recording_trace.c").read_text(encoding="utf-8")
    active_cancel = all(token in source_text for token in
                        ("comp_touch_visual_cancel", "TRANSPORT_BLUR", "4850"))
    if not active_cancel:
        failures.append("active-DOWN cancel/blur timeline is not source-bound")

    positive_stdout = recording.get("positive_stdout", [""])[0] if recording else ""
    count_keys = ("reports", "start", "stop", "session_finished", "menu",
                  "submitted", "deduplicated", "queue")
    counts = {key: parse_int(positive_stdout, key) for key in count_keys}
    if any(counts[key] is None for key in count_keys):
        failures.append("once-only recording/menu observation is incomplete")

    # Mutating an observed object or replacing a fresh build with a stale
    # record must be rejected by the same predicates used for PASS.
    touch_mutation = dict(touch_observed)
    touch_mutation["consumed"] = 23
    build_mutation = dict(builds["bounded"])
    build_mutation["source_commit"] = ACCEPTED_PRODUCTION
    mutation_negative = {
        "touch_counter_mutation_rejected": touch_mutation.get("consumed") != 24,
        "stale_build_source_rejected": not validate_build(build_mutation, out, head),
        "nonfresh_build_rejected": not validate_build({**builds["continuous"], "fresh": False}, out, head),
    }
    if not all(mutation_negative.values()):
        failures.append("comprehensive evidence mutation was accepted")

    ready = {
        "schema": "companion.comp_req_528.lower_machine_ready.v1",
        "status": "PASS" if not failures else "NO_GO",
        "requirement_id": "COMP-REQ-528",
        "current_head": head,
        "accepted_production_commit": ACCEPTED_PRODUCTION,
        "focused_525_accepted_verifier_sha256": FOCUSED_525_VERIFIER,
        "focused_525_current_verifier_sha256": sha(recording_verifier) if recording_verifier.is_file() else "",
        "focused_525": {"path": "recording_525/verifier.json" if recording_verifier.is_file() else "",
                        "sha256": sha(recording_verifier) if recording_verifier.is_file() else "",
                        "counts": counts},
        "raw_touch": {"observed": raw_observed, "result_path": "raw_touch_result.json",
                      "result_sha256": sha(out / "raw_touch_result.json") if (out / "raw_touch_result.json").is_file() else ""},
        "touch_integration": {"observed": touch_observed,
                              "result_path": "touch_integration/touch-integration-result.json",
                              "result_sha256": sha(touch_result_path) if touch_result_path.is_file() else "",
                              "verifier_command": ["python", "-B", "tools/verify_comp_req_466_r7_touch_integration.py"],
                              "verifier_exit_code": touch_gate.returncode,
                              "runner_sha256": touch_result.get("runner_sha256", "")},
        "active_down_cancel": {"observed_from_production_trace": active_cancel,
                                "blur_then_later_up": True},
        "source_bindings": sources,
        "host_chain": host_chain,
        "protected": protected,
        "blob_self_check": blob_self_checks,
        "builds": builds,
        "r7_gates": {"static": r7_static, "parser": r7_parser,
                      "checkonly_path": "r7_checkonly/host-result.json"},
        "touch_service": touch_observed,
        "checkonly": checkonly,
        "stale_pre_154700e_handoff_rejected": stale_rejected,
        "external_joint_pass": False,
        "physical_timing": "unproven",
        "physical_review": "unproven",
        "negative_fixtures": mutation_negative,
        "intake_verifier_sha256": sha(Path(__file__).resolve()),
        "failures": failures,
    }
    (out / "MACHINE_READY.json").write_text(json.dumps(ready, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    handoff = dict(ready)
    handoff["schema"] = "companion.comp_req_528.lower_handoff.v1"
    (out / "handoff.json").write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": ready["status"], "out_root": args.out_root,
                      "failures": failures}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
