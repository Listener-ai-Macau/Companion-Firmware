import hashlib
import json
import os
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_comp_req_513_recording_trace.ps1"
OUT = Path(os.environ.get(
    "COMP_REQ_515_OUT",
    str(ROOT / ".cache" / "validation" / "comp-req-515-recording-verifier")))
MUTATIONS = ("dispatcher_bypass", "dispatcher_drop", "dispatcher_duplicate",
             "menu_sink_noop", "direct_fsm", "deferred_drop", "supersede",
             "threshold")
MUTATION_REASONS = {
    "dispatcher_bypass": "direct alternate submit edge bypassed shared dispatcher",
    "dispatcher_drop": "eligible decision discarded before dispatcher result",
    "dispatcher_duplicate": "dedupe edge removed; duplicate toggle observed",
    "menu_sink_noop": "menu result sink skipped; observed menu callback missing",
    "direct_fsm": "recording FSM called outside boundary; ordering/count failed",
    "deferred_drop": "queued action enqueue edge dropped; deferred start missing",
    "supersede": "retained action cleared; BUSY ordering failed",
    "threshold": "double-tap recognition window disabled; valid toggle missing",
}
MUTATION_STDOUT = {
    "dispatcher_bypass": "FAIL:board decision dispatch",
    "dispatcher_drop": "FAIL:recording dispatch dropped",
    "dispatcher_duplicate": "FAIL:triple release retoggled",
    "menu_sink_noop": "FAIL:menu sink not observed",
    "direct_fsm": "FAIL:direct FSM outside boundary",
    "deferred_drop": "FAIL:deferred enqueue lost",
    "supersede": "FAIL:supersede retained action lost",
    "threshold": "FAIL:threshold double tap not recognized",
}

def sha(path):
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest().upper()

def blob(path):
    return subprocess.check_output(["git", "hash-object", str(path)],
                                   cwd=ROOT, text=True).strip()

def run(name, mutation="none"):
    root = OUT / name
    root.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["pwsh", "-NoProfile", "-File", str(RUNNER),
                        "-OutRoot", str(root.relative_to(ROOT)),
                        "-Mutation", mutation], cwd=OUT,
                       text=True, capture_output=True)
    result = json.loads((root / "result.json").read_text(encoding="utf-8-sig"))
    return p, result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bounded-hex", default=os.environ.get("COMP_REQ_515_BOUNDED_HEX"))
    parser.add_argument("--bounded-elf", default=os.environ.get("COMP_REQ_515_BOUNDED_ELF"))
    parser.add_argument("--continuous-hex", default=os.environ.get("COMP_REQ_515_CONTINUOUS_HEX"))
    parser.add_argument("--continuous-elf", default=os.environ.get("COMP_REQ_515_CONTINUOUS_ELF"))
    parser.add_argument("--r7-handoff", default=os.environ.get("COMP_REQ_515_R7_HANDOFF"))
    args = parser.parse_args()

    def required_artifact(value, fallback):
        path = Path(value) if value else ROOT / fallback
        if not path.is_file():
            raise SystemExit(f"missing build artifact: {path}")
        return path

    bounded_hex = required_artifact(
        args.bounded_hex,
        "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/"
        "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime.hex",
    )
    bounded_elf = required_artifact(
        args.bounded_elf,
        "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/"
        "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime.elf",
    )
    continuous_hex = required_artifact(
        args.continuous_hex,
        "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime_continuous/"
        "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntimeContinuous.hex",
    )
    continuous_elf = required_artifact(
        args.continuous_elf,
        "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime_continuous/"
        "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntimeContinuous.elf",
    )
    r7_handoff = required_artifact(
        args.r7_handoff,
        ".cache/validation/comp-req-501-faraday-handoff.json",
    )

    boundary_text = (ROOT / "app/companion_pendant/touch/touch_recording_boundary.c").read_text()
    board_text = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c").read_text()
    host_text = (ROOT / "tools/comp_req_513_recording_trace.c").read_text()
    if ("sinks.menu(boundary->sinks.context," not in boundary_text or
            "return dispatch_board_visual_decision(decision, menu);" not in board_text or
            "static bool menu_sink(void *context, const comp_touch_visual_decision_t" not in host_text):
        raise SystemExit("menu dispatch contract missing")
    positive = []
    for name in ("positive_a", "positive_b"):
        p, result = run(name)
        if p.returncode or result.get("status") != "PASS":
            raise SystemExit("positive recording trace failed")
        counters = result.get("checkonly", {})
        if any(counters.get(k) != 0 for k in
               ("hardware_contact", "programmer", "serial", "write",
                "reset", "refresh", "popup", "retry")):
            raise SystemExit("nonzero CheckOnly counter")
        positive.append(result)
    negative = {}
    negative_results = {}
    for mutation in MUTATIONS:
        p, result = run("negative_" + mutation, mutation)
        if (p.returncode == 0 or result.get("status") != "NO_GO" or
                not result.get("mutant_source_sha256") or
                not result.get("changed_edge") or
                not result.get("compile_command") or
                not result.get("executable_sha256") or
                result.get("exit_code") == 0):
            raise SystemExit("mutation was not rejected: " + mutation)
        if MUTATION_STDOUT[mutation] not in result.get("stdout", ""):
            raise SystemExit("wrong mutation oracle reason: " + mutation)
        negative[mutation] = result.get("stdout", "")
        negative_results[mutation] = result
    source_mutants = {
        name: {path: digest for path, digest in
               negative_results[name].get("mutant_source_sha256", {}).items()
               if path.lower().endswith(".c")}
        for name in MUTATIONS
    }
    mutant_identities = [
        json.dumps(source_mutants[name], sort_keys=True)
        for name in MUTATIONS
    ]
    if len(set(mutant_identities)) != len(MUTATIONS):
        raise SystemExit("mutant identities are not distinct")
    receipt = {
        "schema": "companion.comp_req_515.recording_integration.v1",
        "status": "PASS",
        "production_boundary": "touch_recording_boundary.c",
        "positive_replays": 2,
        "positive_stdout": [x["stdout"] for x in positive],
        "negative_replays": len(negative),
        "negative_names": list(negative),
        "negative_source_mutants": {
            name: source_mutants[name] for name in MUTATIONS
        },
        "negative_changed_edges": {
            name: negative_results[name].get("changed_edge", "")
            for name in MUTATIONS
        },
        "negative_oracle_reasons": MUTATION_REASONS,
        "negative_stdout_predicates": MUTATION_STDOUT,
        "negative_actual_stdout": {
            name: negative_results[name].get("stdout", "")
            for name in MUTATIONS
        },
        "negative_compile_commands": {
            name: negative_results[name].get("compile_command", "")
            for name in MUTATIONS
        },
        "negative_exit_codes": {
            name: negative_results[name].get("exit_code")
            for name in MUTATIONS
        },
        "negative_executable_sha256": {
            name: negative_results[name].get("executable_sha256", "")
            for name in MUTATIONS
        },
        "runner_sha256": sha(RUNNER),
        "fixture_sha256": sha(ROOT / "tools" / "comp_req_513_recording_trace.c"),
        "boundary_sha256": sha(ROOT / "app/companion_pendant/touch/touch_recording_boundary.c"),
        "gesture_decision_sha256": sha(ROOT / "app/companion_pendant/touch/touch_visual_decision.c"),
        "board_main_sha256": sha(ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"),
        "makefile_sha256": sha(ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"),
        "protected": {
            "driver_physical_sha256": sha(ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"),
            "driver_git_blob": blob(ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"),
            "header_physical_sha256": sha(ROOT / "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h"),
            "header_git_blob": blob(ROOT / "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h"),
        },
        "builds": {
            "bounded_hex": sha(bounded_hex),
            "bounded_elf": sha(bounded_elf),
            "continuous_hex": sha(continuous_hex),
            "continuous_elf": sha(continuous_elf),
        },
        "r7_handoff_sha256": sha(r7_handoff),
        "checkonly": {"hardware_contact": 0, "programmer": 0, "serial": 0,
                      "write": 0, "reset": 0, "refresh": 0, "popup": 0,
                      "retry": 0},
        "external_joint_pass": False,
        "physical_timing": "unproven",
        "menu_dispatch_contract": {
            "shared_boundary": "comp_touch_recording_boundary_dispatch",
            "board_sink": "board_touch_recording_menu_sink",
            "host_sink": "menu_sink",
            "once_only": True,
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "verifier.json").write_text(json.dumps(receipt, indent=2) + "\n",
                                         encoding="utf-8")
    handoff = dict(receipt)
    handoff["schema"] = "companion.comp_req_515.faraday_handoff.v1"
    handoff["external_joint_pass"] = False
    (OUT / "handoff.json").write_text(json.dumps(handoff, indent=2) + "\n",
                                        encoding="utf-8")
    print(json.dumps(receipt, separators=(",", ":")))

if __name__ == "__main__":
    main()
