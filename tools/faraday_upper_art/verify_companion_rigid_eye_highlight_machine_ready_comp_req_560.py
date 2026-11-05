#!/usr/bin/env python3
"""Source-bound MACHINE_READY verifier for COMP-REQ-560."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "docs/validation/companion-rigid-eye-highlight-comp-req-560"
PAGE = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
FRAME_HEADER = ROOT / "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h"
OWNER_ACCEPTANCE = (
    ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
)
VERIFIER = Path(__file__).resolve()
NEGATIVE_VERIFIER = (
    ROOT
    / "tools/faraday_upper_art/"
    "test_companion_rigid_eye_highlight_machine_ready_negatives_comp_req_560.py"
)

EXPECTED = {
    "page": "FA10F976507C4372AEC17172367DA4B1663B32396ECBB55ED2E80ECEDCEEA658",
    "driver": "F52A7E853BFE2E66680F08420941265CFF163FB579B2D3870128FC72C79E035F",
    "driver_blob": "f856d7ce0b8915e5059620c3faa97aa06b06eb4e",
    "frame_header": "9571CF9F896B6C14451BAA7348CB717643B4963AE834B0A554E0C2ED2C7E8D35",
    "frame_header_blob": "2220da0c1113a5cdad7028aeae578d9fe26e936f",
    "owner_acceptance": "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def canonical_page_sha() -> str:
    return sha256(PAGE.read_text(encoding="utf-8").replace("\r\n", "\n").encode())


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    row = subprocess.check_output(
        ["git", "ls-files", "-s", "--", rel],
        cwd=ROOT,
        text=True,
    ).strip()
    return row.split()[1] if row else ""


def commit_exists(commit: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def verify(validation: Path = VALIDATION) -> dict:
    failures: list[str] = []

    def require(value: bool, label: str) -> None:
        if not value:
            failures.append(label)

    machine_path = validation / "MACHINE_READY.json"
    rigid_path = validation / "rigid-eye-highlight.json"
    recording_path = validation / "recording-choreography.json"
    interaction_path = validation / "interaction-42/interaction-successor-result.json"
    parity_path = validation / "ten-family-parity.json/visual-frame-manifest.json"
    direction_sheet = validation / "screenshots/contact-sheet.png"
    recording_sheet = validation / "recording-screenshots/idle-recording-contact.png"
    negative_artifact = validation / "machine-negatives.json"
    machine = load(machine_path)
    rigid = load(rigid_path)
    recording = load(recording_path)
    interaction = load(interaction_path)
    parity = load(parity_path)

    require(machine["status"] == "MACHINE_READY_OWNER_PENDING", "machine status")
    require(machine["owner_review"] == "pending", "owner review pending")
    require(machine["owner_prompt_opened"] is False, "owner prompt unopened")
    require(all(commit_exists(item) for item in machine["implementation_commits"]),
            "implementation commits")
    require(canonical_page_sha() == EXPECTED["page"], "page canonical hash")
    require(machine["page_sha256"] == EXPECTED["page"], "machine page hash")

    artifact_paths = {
        "rigid_eye_highlight": rigid_path,
        "recording_choreography": recording_path,
        "interaction_regression": interaction_path,
        "browser_device_parity": parity_path,
    }
    for key, path in artifact_paths.items():
        require(machine[key]["artifact_sha256"] == file_sha(path), f"{key} artifact hash")

    require(rigid["status"] == "PASS", "rigid status")
    require(rigid["page_sha256"] == EXPECTED["page"], "rigid page hash")
    require(rigid["families"] == 10 and rigid["family_checks"] == 60,
            "rigid family coverage")
    require(len(rigid["directions"]) == 5, "rigid direction coverage")
    require(all(row["pass"] for row in rigid["directions"]), "direction passes")
    require(all(row["component_count"] == 4 for row in rigid["directions"]),
            "direction component count")
    require(all(row["paired_clusters"] for row in rigid["directions"]),
            "paired direction clusters")
    require(all(row["rigid_cluster_mismatch"] == 0 for row in rigid["directions"]),
            "rigid geometry")
    require(all(row["relative_vector_mismatch"] == 0 for row in rigid["directions"]),
            "relative geometry")
    require(all(row["boundary_mismatch_pixels"] == 0 for row in rigid["directions"]),
            "boundary inset")
    require(all(row["residual_source_pixels"] == 0 for row in rigid["directions"]),
            "source cleanup")
    require(rigid["unsafe_displacement_clamp"]["clamped"] is True,
            "unsafe clamp")
    require(rigid["unsafe_displacement_clamp"]["fits"] is True,
            "clamped displacement fit")
    require(rigid["contradictory_source_negative_rejected"] is True,
            "contradictory negative")
    require(rigid["closed_eye_cluster_absent"] is True, "closed eye cluster")

    require(recording["status"] == "PASS", "recording status")
    require(recording["page_sha256"] == EXPECTED["page"], "recording page hash")
    require(recording["recording_underlying_face_sequence_equal"] is True,
            "recording face sequence")
    require(recording["recording_live_distinct_face_hashes"] >= 4,
            "recording face choreography")
    require(recording["recording_live_distinct_meter_steps"] >= 6,
            "recording meter choreography")
    require(recording["paired_eye_steps"] == 6, "recording paired eyes")

    require(interaction["status"] == "PASS", "interaction status")
    require(interaction["page_canonical_sha256"] == EXPECTED["page"],
            "interaction page hash")
    require(interaction["combinations"] == 6, "interaction combinations")
    require(interaction["scenarios_pass_under_current_contract"] == 42,
            "interaction scenarios")
    require(interaction["current_recording_entry_contract"] == {
        "face_layers": 1,
        "gaze_layers": 1,
        "removed_top_left_indicator_layers": 0,
        "inward_meter_layers": 1,
        "recording_entries": 1,
        "menu_layers": 0,
        "progress_nodes": 0,
    }, "recording entry contract")
    require(interaction["microphone_requests"] == 0, "microphone requests")
    require(all(value == 0 for value in interaction["side_effects"].values()),
            "interaction side effects")

    require(parity["status"] == "PASS", "parity status")
    require(parity["source"]["page_canonical_sha256"] == EXPECTED["page"],
            "parity page hash")
    require(parity["invariants"]["state_count"] == 111, "parity state count")
    require(parity["invariants"]["unique_frame_count"] == 77,
            "parity unique frames")
    require(parity["invariants"]["browser_to_c_pixel_diff"] == 0,
            "browser C parity")
    require(parity["invariants"]["all_states_are_5000_bytes"] is True,
            "frame byte size")
    require(parity["invariants"]["default_off"] is True, "asset pack default off")

    require(file_sha(direction_sheet) ==
            machine["main_visual_review"]["direction_contact_sheet_sha256"],
            "direction contact sheet")
    require(file_sha(recording_sheet) ==
            machine["main_visual_review"]["idle_recording_contact_sheet_sha256"],
            "recording contact sheet")
    require(file_sha(DRIVER) == EXPECTED["driver"], "protected driver physical")
    require(git_blob(DRIVER) == EXPECTED["driver_blob"], "protected driver blob")
    require(file_sha(FRAME_HEADER) == EXPECTED["frame_header"],
            "protected frame header physical")
    require(git_blob(FRAME_HEADER) == EXPECTED["frame_header_blob"],
            "protected frame header blob")
    require(file_sha(OWNER_ACCEPTANCE) == EXPECTED["owner_acceptance"],
            "protected owner acceptance")
    require(machine["source_bound_verification"]["verifier_sha256"] ==
            file_sha(VERIFIER), "machine verifier hash")
    require(machine["source_bound_verification"]["negative_verifier_sha256"] ==
            file_sha(NEGATIVE_VERIFIER), "negative verifier hash")
    require(machine["source_bound_verification"]["negative_artifact_sha256"] ==
            file_sha(negative_artifact), "negative artifact hash")
    negatives = load(negative_artifact)
    require(negatives["status"] == "PASS" and len(negatives["cases"]) == 5,
            "negative cases")
    require(all(value == 0 for value in machine["checkonly"].values()),
            "machine side effects")

    return {
        "schema": "companion.comp_req_560.machine_ready_verification.v1",
        "status": "PASS" if not failures else "NO_GO",
        "failures": failures,
        "machine_ready_sha256": file_sha(machine_path),
        "page_sha256": canonical_page_sha(),
        "rigid_directions": len(rigid["directions"]),
        "family_checks": rigid["family_checks"],
        "interaction_scenarios": interaction["scenarios_pass_under_current_contract"],
        "parity_states": parity["invariants"]["state_count"],
        "checkonly_all_zero": all(value == 0 for value in machine["checkonly"].values()),
        "owner_prompt_opened": machine["owner_prompt_opened"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--validation-dir")
    args = parser.parse_args()
    validation = (
        (ROOT / args.validation_dir).resolve()
        if args.validation_dir
        else VALIDATION
    )
    result = verify(validation)
    payload = json.dumps(result, indent=2, ensure_ascii=True) + "\n"
    if args.output:
        output = (ROOT / args.output).resolve()
        if ROOT not in output.parents:
            raise SystemExit("output must remain in repository")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
