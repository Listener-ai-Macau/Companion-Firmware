#!/usr/bin/env python3
"""Persist active WB55 CEMP runtime serial evidence as an inspectable logbook."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATE = current_candidate()
RUN_ROOT = CANDIDATE.run_root
RUN_REPORT = RUN_ROOT / "runtime-recheck-run.json"
LOG_VERDICT = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logs.json"
PROMOTION = ROOT / "docs/validation/companion-screen-wb55-runtime-promotion.json"
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logbook.json"
DEFAULT_MD = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logbook.md"
SCHEMA_ID = "companion.screen.wb55_runtime_recheck_logbook.v1"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log_entry(label: str) -> tuple[dict[str, Any], str]:
    directory = RUN_ROOT / label
    raw = directory / "nucleo-serial-raw.log"
    summary = directory / "nucleo-serial-summary.json"
    raw_text = raw.read_text(encoding="utf-8", errors="replace") if raw.exists() else ""
    summary_data = read_json(summary) if summary.exists() else {}
    return (
        {
            "label": label,
            "raw_log": rel(raw),
            "raw_log_exists": raw.exists(),
            "raw_log_bytes": raw.stat().st_size if raw.exists() else 0,
            "raw_log_sha256": sha256(raw) if raw.exists() else None,
            "summary_json": rel(summary),
            "summary_json_exists": summary.exists(),
            "summary_status": summary_data.get("status"),
            "serial_bytes_read": summary_data.get("bytes_read"),
            "capture_seconds": summary_data.get("seconds"),
            "port": summary_data.get("port"),
            "errors": summary_data.get("errors", []),
        },
        raw_text,
    )


def build_logbook() -> tuple[dict[str, Any], dict[str, str]]:
    run = read_json(RUN_REPORT) if RUN_REPORT.exists() else {}
    verdict = read_json(LOG_VERDICT) if LOG_VERDICT.exists() else {}
    promotion = read_json(PROMOTION) if PROMOTION.exists() else {}
    provision, provision_text = log_entry("provision")
    normal, normal_text = log_entry("normal")
    successful_steps = all(
        step.get("status") == "PASS" for step in run.get("results", []) if isinstance(step, dict)
    ) and len(run.get("results", [])) == 4
    status = "PASS" if (
        run.get("status") == "PASS"
        and run.get("normal_firmware_restored") is True
        and successful_steps
        and provision.get("summary_status") == "PASS"
        and normal.get("summary_status") == "PASS"
        and verdict.get("status") == "PASS"
        and promotion.get("status") == "APPLIED"
    ) else "INCOMPLETE"
    return (
        {
            "schema_id": SCHEMA_ID,
            "status": status,
            "target": "NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U",
            "source_run_report": rel(RUN_REPORT),
            "source_log_verdict": rel(LOG_VERDICT),
            "source_promotion": rel(PROMOTION),
            "run": {
                "status": run.get("status"),
                "generated_at": run.get("generated_at"),
                "completed_at": run.get("completed_at"),
                "normal_firmware_restored": run.get("normal_firmware_restored"),
                "resource": run.get("resource"),
                "steps": run.get("results", []),
            },
            "log_verdict_status": verdict.get("status"),
            "promotion_status": promotion.get("status"),
            "serial_logs": {"provision": provision, "normal": normal},
            "retention": {
                "raw_log_policy": "The full captured serial text is embedded in the companion Markdown logbook and remains available at the source paths.",
                "integrity_policy": "Each raw log is recorded with byte count and SHA-256 so copied evidence can be matched to the original capture.",
            },
        },
        {"provision": provision_text, "normal": normal_text},
    )


def render_markdown(logbook: dict[str, Any], raw_texts: dict[str, str]) -> str:
    lines = [
        f"# WB55 Rev{CANDIDATE.revision} Runtime Recheck Logbook",
        "",
        f"- Status: `{logbook['status']}`",
        f"- Target: `{logbook['target']}`",
        f"- Run completed: `{logbook['run'].get('completed_at')}`",
        f"- Normal firmware restored: `{logbook['run'].get('normal_firmware_restored')}`",
        f"- Log verdict: `{logbook.get('log_verdict_status')}`",
        f"- Promotion: `{logbook.get('promotion_status')}`",
        "",
        "## Serial Capture Index",
        "",
        "| Capture | Port | Serial bytes | Raw bytes | SHA-256 | Summary |",
        "|---|---:|---:|---:|---|---|",
    ]
    for label in ("provision", "normal"):
        entry = logbook["serial_logs"][label]
        lines.append(
            f"| `{label}` | `{entry.get('port')}` | `{entry.get('serial_bytes_read')}` | "
            f"`{entry.get('raw_log_bytes')}` | `{entry.get('raw_log_sha256')}` | `{entry.get('summary_status')}` |"
        )
    lines.extend(["", "## Run Steps", "", "| Step | Result | Started | Ended |", "|---|---|---|---|"])
    for step in logbook["run"].get("steps", []):
        lines.append(
            f"| `{step.get('id')}` | `{step.get('status')}` | `{step.get('started_at')}` | `{step.get('ended_at')}` |"
        )
    for label in ("provision", "normal"):
        lines.extend([
            "",
            f"## {label.title()} Serial Raw Log",
            "",
            "```text",
            raw_texts[label].rstrip(),
            "```",
        ])
    return "\n".join(lines) + "\n"


def verify(logbook: dict[str, Any], require_pass: bool) -> list[str]:
    errors: list[str] = []
    if logbook.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    status = logbook.get("status")
    if status not in {"PASS", "INCOMPLETE"}:
        errors.append("runtime logbook has an unknown evidence status")
    if require_pass and status != "PASS":
        errors.append("runtime logbook requires a completed PASS run")
    if status != "PASS":
        return errors
    if logbook.get("run", {}).get("normal_firmware_restored") is not True:
        errors.append("normal firmware must be restored")
    for label in ("provision", "normal"):
        entry = logbook.get("serial_logs", {}).get(label, {})
        if entry.get("raw_log_exists") is not True or entry.get("summary_json_exists") is not True:
            errors.append(f"{label} raw and summary logs must exist")
        if entry.get("summary_status") != "PASS" or not isinstance(entry.get("serial_bytes_read"), int) or entry["serial_bytes_read"] <= 0:
            errors.append(f"{label} serial capture must be nonempty PASS")
        if not isinstance(entry.get("raw_log_sha256"), str) or len(entry["raw_log_sha256"]) != 64:
            errors.append(f"{label} raw log must have a SHA-256")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--require-pass", action="store_true", help="Require captured runtime logs and applied promotion.")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    output_json = args.json if args.json.is_absolute() else ROOT / args.json
    output_md = args.markdown if args.markdown.is_absolute() else ROOT / args.markdown
    logbook, raw_texts = build_logbook()
    errors = verify(logbook, bool(args.require_pass))
    rendered_json = json.dumps(logbook, indent=2, sort_keys=True) + "\n"
    rendered_md = render_markdown(logbook, raw_texts)
    if args.write and not errors:
        output_json.write_text(rendered_json, encoding="utf-8")
        output_md.write_text(rendered_md, encoding="utf-8")
    elif not args.write:
        if not output_json.exists() or output_json.read_text(encoding="utf-8") != rendered_json:
            errors.append(f"stale {rel(output_json)}; rerun with --write")
        if not output_md.exists() or output_md.read_text(encoding="utf-8") != rendered_md:
            errors.append(f"stale {rel(output_md)}; rerun with --write")
    if errors:
        print("FAIL: WB55 runtime logbook verification failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 runtime logbook verified -> {rel(output_json)}, {rel(output_md)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
