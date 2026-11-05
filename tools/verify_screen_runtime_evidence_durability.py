#!/usr/bin/env python3
"""Guard promoted WB55 screen evidence against missing raw artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

from screen_runtime_candidate import (
    ScreenRuntimeCandidate,
    current_runtime_evidence_durability,
    evaluate_runtime_evidence_durability,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/validation/companion-screen-runtime-evidence-durability.json"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def self_test() -> dict[str, bool]:
    candidate = ScreenRuntimeCandidate(
        revision=53,
        total_bytes=49901,
        pack_crc32="0x2332E300",
        runtime_status="REVISION_53_RUNTIME_PASS_HUMAN_VISUAL_PENDING",
        clips=33,
        frames=75,
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        runtime = {
            "status": candidate.pass_status,
            "provision_capture_summary": "evidence/provision-summary.json",
            "normal_capture_summary": "evidence/normal-summary.json",
            "provision_raw_log": "evidence/provision.log",
            "normal_raw_log": "evidence/normal.log",
            "required_runtime_markers": ["mount=ok", "revision=53"],
        }
        write_json(root / "evidence/provision-summary.json", {"status": "PASS"})
        write_json(root / "evidence/normal-summary.json", {"status": "PASS"})
        (root / "evidence/provision.log").write_text("mount=ok\nrevision=53\n", encoding="utf-8")
        (root / "evidence/normal.log").write_text("mount=ok\nrevision=53\n", encoding="utf-8")
        write_json(
            root / ".cache/validation/rev53-runtime-current/runtime-recheck-run.json",
            {
                "status": "PASS",
                "normal_firmware_restored": True,
                "results": [
                    {"id": step_id, "status": "PASS"}
                    for step_id in (
                        "flash_provision",
                        "capture_provision",
                        "flash_normal",
                        "capture_normal",
                    )
                ],
            },
        )
        complete = evaluate_runtime_evidence_durability(candidate, runtime, root=root)
        (root / "evidence/normal.log").unlink()
        missing = evaluate_runtime_evidence_durability(candidate, runtime, root=root)
    return {
        "complete_artifacts_pass": complete.get("status") == "PASS" and complete.get("durable") is True,
        "missing_raw_log_rejected": (
            missing.get("status") == "NO_GO_MISSING_DURABLE_RUNTIME_EVIDENCE"
            and "missing_file:normal_raw_log" in missing.get("failures", [])
            and missing.get("durable") is False
        ),
    }


def build_report() -> dict[str, object]:
    checks = self_test()
    current = current_runtime_evidence_durability()
    return {
        "schema_id": "companion.screen.runtime_evidence_durability_guard.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "claim_scope": "static_evidence_integrity_guard_no_hardware_claim",
        "current_evidence": current,
        "self_test": checks,
        "policy": {
            "promoted_summary_requires_raw_artifacts": True,
            "missing_artifact_forces_hardware_pending": True,
            "ignored_cache_is_not_durable_acceptance_storage": True,
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    errors: list[str] = []
    if report.get("status") != "PASS":
        errors.append("durability self-test failed")
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not output.is_file():
        errors.append(f"missing {output.relative_to(ROOT).as_posix()}")
    elif output.read_text(encoding="utf-8") != rendered:
        errors.append(f"stale {output.relative_to(ROOT).as_posix()}; rerun with --write")
    if errors:
        print("FAIL: screen runtime evidence durability guard failed", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: screen runtime evidence durability guarded -> {output.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
