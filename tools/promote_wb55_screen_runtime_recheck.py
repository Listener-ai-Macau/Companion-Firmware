#!/usr/bin/env python3
"""Promote current WB55 CEMP runtime evidence after both serial logs pass."""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-wb55-runtime-promotion.json"
LOGS_REPORT = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logs.json"
BILINGUAL_MENU = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
RESOURCE_POLICY = ROOT / "docs/validation/companion-screen-resource-memory-policy.json"
TOUCH_PACKET = ROOT / "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json"

CANDIDATE = current_candidate()
PASS_STATUS = CANDIDATE.pass_status
PENDING_STATUS = CANDIDATE.pending_status
SCHEMA_ID = "companion.screen.wb55_runtime_promotion.v1"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def build_plan() -> dict[str, Any]:
    logs = load_json(LOGS_REPORT)
    menu = load_json(BILINGUAL_MENU)
    resource_policy = load_json(RESOURCE_POLICY)
    packet = load_json(TOUCH_PACKET)

    resource = menu.get("resource_pack", {})
    candidate = resource_policy.get("candidate_pack", {})
    provision = logs.get("provision", {})
    normal = logs.get("normal", {})
    logs_pass = logs.get("status") == "PASS"
    applied = (
        menu.get("runtime_evidence", {}).get("status") == PASS_STATUS
        and resource_policy.get("wb55_real_evidence", {}).get("revision") == CANDIDATE.revision
        and resource_policy.get("wb55_real_evidence", {}).get("pack_crc32") == CANDIDATE.pack_crc32
        and packet.get("machine_state", {}).get("runtime_status") == PASS_STATUS
    )

    blockers: list[str] = []
    if logs.get("candidate", {}).get("revision") != CANDIDATE.revision:
        blockers.append("runtime log verifier candidate revision does not match active CEMP")
    if logs.get("candidate", {}).get("total_bytes") != CANDIDATE.total_bytes:
        blockers.append("runtime log verifier candidate size does not match active CEMP")
    if logs.get("candidate", {}).get("pack_crc32") != CANDIDATE.pack_crc32:
        blockers.append("runtime log verifier candidate CRC does not match active CEMP")
    if logs.get("status") != "PASS":
        blockers.append(f"runtime log verifier status is {logs.get('status')!r}, not PASS")
    for label, section in (("provision", provision), ("normal", normal)):
        if section.get("status") != "PASS":
            blockers.append(f"{label} log status is {section.get('status')!r}")

    target_state = {
        "status": PASS_STATUS,
        "revision": CANDIDATE.revision,
        "pack_crc32": CANDIDATE.pack_crc32,
        "total_bytes": CANDIDATE.total_bytes,
        "provision_raw_log": provision.get("raw_log"),
        "provision_capture_summary": provision.get("summary_json"),
        "normal_raw_log": normal.get("raw_log"),
        "normal_capture_summary": normal.get("summary_json"),
    }

    current_state = {
        "menu_runtime_status": menu.get("runtime_evidence", {}).get("status"),
        "resource_policy_wb55_revision": resource_policy.get("wb55_real_evidence", {}).get("revision"),
        "touch_packet_runtime_status": packet.get("machine_state", {}).get("runtime_status"),
    }

    return {
        "schema_id": SCHEMA_ID,
        "status": "APPLIED" if applied else ("READY_TO_APPLY" if logs_pass and not blockers else "NO_GO_LOGS_NOT_PASS"),
        "purpose": f"Machine-only promotion plan after rev{CANDIDATE.revision} provision and normal runtime logs pass.",
        "inputs": {
            "logs_report": rel(LOGS_REPORT),
            "bilingual_menu": rel(BILINGUAL_MENU),
            "resource_policy": rel(RESOURCE_POLICY),
            "touch_packet": rel(TOUCH_PACKET),
        },
        "current_state": current_state,
        "target_state": target_state,
        "blockers": blockers,
        "planned_updates": [
            {
                "path": rel(BILINGUAL_MENU),
                "changes": [
                    f"runtime_evidence.status -> {PASS_STATUS}",
                    f"runtime_evidence provision/normal log paths -> rev{CANDIDATE.revision} log verifier paths",
                    f"runtime_evidence.required_runtime_markers -> revision={CANDIDATE.revision} external_flash marker set",
                ],
            },
            {
                "path": rel(RESOURCE_POLICY),
                "changes": [
                    f"wb55_real_evidence -> rev{CANDIDATE.revision} candidate pack and runtime logs",
                    "candidate_pack.status -> runtime_pass_human_visual_pending",
                ],
            },
            {
                "path": rel(TOUCH_PACKET),
                "changes": [
                    f"machine_state.runtime_status -> {PASS_STATUS}",
                    f"machine_state provision/normal logs -> rev{CANDIDATE.revision} runtime logs",
                ],
            },
        ],
        "post_apply_commands": [
            "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
            "python .\\tools\\promote_wb55_screen_runtime_recheck.py",
            "python .\\tools\\verify_companion_screen_pre_acceptance_health.py --write-fixture",
            "python .\\tools\\verify_companion_screen_goal_audit.py --write",
        ],
    }


def promote_data() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    logs = load_json(LOGS_REPORT)
    menu = load_json(BILINGUAL_MENU)
    resource_policy = load_json(RESOURCE_POLICY)
    packet = load_json(TOUCH_PACKET)

    resource = menu["resource_pack"]
    provision = logs["provision"]
    normal = logs["normal"]

    menu = copy.deepcopy(menu)
    runtime = menu.setdefault("runtime_evidence", {})
    previous = runtime.get("previous_runtime_proven_revision", {})
    if previous.get("revision") == CANDIDATE.revision:
        previous = {
            "revision": resource_policy.get("wb55_real_evidence", {}).get("revision"),
            "pack_crc32": resource_policy.get("wb55_real_evidence", {}).get("pack_crc32"),
            "provision_raw_log": resource_policy.get("wb55_real_evidence", {}).get("provision_runtime_log"),
            "normal_raw_log": resource_policy.get("wb55_real_evidence", {}).get("normal_runtime_log"),
        }
    runtime.update({
        "status": PASS_STATUS,
        "provision_capture_summary": provision["summary_json"],
        "provision_raw_log": provision["raw_log"],
        "normal_capture_summary": normal["summary_json"],
        "normal_raw_log": normal["raw_log"],
        "operator_prompt_used": False,
        "machine_observation": (
            f"Revision {CANDIDATE.revision} provision and normal runtime logs passed: external ui_assets "
            f"mounted, CEMP revision {CANDIDATE.revision} / CRC {CANDIDATE.pack_crc32} loaded from external_flash, "
            "pet self-test passed, touch identity was detected, and the initial full "
            "refresh completed. Human touch/visual acceptance remains pending."
        ),
        "previous_runtime_proven_revision": previous,
        "required_runtime_markers": [
            "mount=ok",
            f"revision={CANDIDATE.revision}",
            f"clips={CANDIDATE.clips} frames={CANDIDATE.frames}",
            "pet_behavior_selftest=pass failure_code=0",
            "touch-health] detected=1 identity=1 addr=0x38",
            "preview_started name=idle",
            "source=external_flash",
            "refresh mode=full",
            "complete=1",
        ],
    })

    resource_policy = copy.deepcopy(resource_policy)
    wb55 = resource_policy.setdefault("wb55_real_evidence", {})
    wb55.update({
        "pack": resource.get("name"),
        "revision": resource.get("revision"),
        "clips": resource.get("clips"),
        "frames": resource.get("frames"),
        "pack_bytes": resource.get("total_bytes"),
        "pack_crc32": resource.get("pack_crc32"),
        "provision_runtime_log": provision["raw_log"],
        "normal_runtime_log": normal["raw_log"],
        "external_render_log": normal["raw_log"],
        "required_markers": runtime["required_runtime_markers"],
    })
    resource_policy.setdefault("candidate_pack", {})["status"] = "runtime_pass_human_visual_pending"

    packet = copy.deepcopy(packet)
    machine = packet.setdefault("machine_state", {})
    machine.update({
        "normal_firmware_restored": True,
        "normal_log": normal["raw_log"],
        "provision_log": provision["raw_log"],
        "resource_crc32": resource.get("pack_crc32"),
        "resource_revision": resource.get("revision"),
        "resource_total_bytes": resource.get("total_bytes"),
        "runtime_status": PASS_STATUS,
    })
    return menu, resource_policy, packet


def verify_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    target = plan.get("target_state", {})
    if target.get("revision") != CANDIDATE.revision:
        errors.append(f"target revision must be {CANDIDATE.revision}")
    if target.get("total_bytes") != CANDIDATE.total_bytes:
        errors.append(f"target size must be {CANDIDATE.total_bytes}")
    if target.get("pack_crc32") != CANDIDATE.pack_crc32:
        errors.append(f"target CRC must be {CANDIDATE.pack_crc32}")
    if plan.get("status") not in {"READY_TO_APPLY", "NO_GO_LOGS_NOT_PASS", "APPLIED"}:
        errors.append(f"unexpected status {plan.get('status')!r}")
    if plan.get("status") == "READY_TO_APPLY" and plan.get("blockers"):
        errors.append("READY_TO_APPLY must not have blockers")
    if plan.get("status") == "APPLIED" and plan.get("blockers"):
        errors.append("APPLIED must not have blockers")
    if plan.get("status") == "NO_GO_LOGS_NOT_PASS" and not plan.get("blockers"):
        errors.append("NO_GO_LOGS_NOT_PASS must list blockers")
    serialized = json.dumps(plan, ensure_ascii=False)
    for token in (
        PASS_STATUS,
        "runtime_evidence.status",
        "wb55_real_evidence",
        "machine_state.runtime_status",
    ):
        if token not in serialized:
            errors.append(f"promotion plan missing token {token}")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write the promotion readiness report")
    parser.add_argument("--apply", action="store_true", help="apply promotion to evidence files; requires READY_TO_APPLY")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)

    print(
        "BLOCKED: the active Companion Goal prohibits legacy r53 runtime promotion; "
        "v9 remains machine-only and runtime-inactive pending approved visual sources."
    )
    return 2

    output = args.json if args.json.is_absolute() else ROOT / args.json
    plan = build_plan()
    errors = verify_plan(plan)
    rendered = json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if args.apply:
        if plan.get("status") == "APPLIED":
            pass
        elif plan.get("status") != "READY_TO_APPLY":
            errors.append(f"refusing --apply until rev{CANDIDATE.revision} runtime logs verify PASS")
        if not errors and plan.get("status") != "APPLIED":
            menu, resource_policy, packet = promote_data()
            write_json(BILINGUAL_MENU, menu)
            write_json(RESOURCE_POLICY, resource_policy)
            write_json(TOUCH_PACKET, packet)
            plan = build_plan()
            rendered = json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if args.write or args.apply:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not output.exists():
        errors.append(f"missing {rel(output)}")
    elif output.read_text(encoding="utf-8") != rendered:
        errors.append(f"stale {rel(output)}; rerun with --write")

    if errors:
        print("FAIL: WB55 runtime promotion gate failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 runtime promotion gate verified -> {rel(output)} ({plan['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
