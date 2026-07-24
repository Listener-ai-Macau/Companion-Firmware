#!/usr/bin/env python3
"""Fail-closed offline MACHINE_READY gate for COMP-REQ-544."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "docs/validation/companion-browser-family-micro-choreography-comp-req-544"
PAGE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"
GENERATOR = ROOT / "tools/faraday_upper_art/apply_companion_family_micro_choreography_comp_req_540.mjs"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def canonical_bytes(path: Path) -> bytes:
    value = path.read_bytes()
    if path.suffix.lower() in {".html", ".json", ".mjs", ".py", ".ps1"}:
        value = value.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    return value


def load(name: str) -> dict:
    return json.loads((VALIDATION / name).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", default=(VALIDATION / "MACHINE_READY.json").as_posix())
    args = parser.parse_args()
    focused = load("focused-smoke-result.json")
    clock = load("full-family-real-clock-result.json")
    blink = load("blink-cadence-result.json")
    parity = load("parity-verifier-result.json")
    page_text = canonical_bytes(PAGE).decode("utf-8")
    page_sha = sha256_bytes(canonical_bytes(PAGE))
    plans = focused.get("families", [])
    checks = {
        "focused_pass": focused.get("status") == "PASS",
        "focused_ten_families": len(focused.get("selected_families", [])) == 10,
        "focused_interruption": focused.get("checks", {}).get("interruption_exact_baseline_return") is True,
        "clock_pass": clock.get("status") == "PASS",
        "clock_120_cadences": clock.get("real_clock_cadences") == 120,
        "clock_ten_families": len(clock.get("selected_families", [])) == 10,
        "clock_bounded_unchanged": clock.get("checks", {}).get("real_clock_max_unchanged_two_slots") is True,
        "clock_deterministic": clock.get("checks", {}).get("real_clock_two_runs_identical") is True,
        "clock_baseline_return": clock.get("checks", {}).get("real_clock_exact_baseline_return") is True,
        "blink_pass": blink.get("status") == "PASS",
        "blink_sparse": blink.get("checks", {}).get("sparse_interval_ge_8000") is True,
        "blink_duration": blink.get("checks", {}).get("duration_1440_to_1920") is True,
        "blink_interruption": blink.get("checks", {}).get("interruption_defers_once") is True,
        "parity_pass": parity.get("status") == "PASS",
        "source_split_timelines": "blinkTimelineState" in page_text and "scheduleBlinkTimeline" in page_text,
        "source_hold_mapping": "holdIndex=activeIndex>=0?activeIndex" in page_text,
        "source_no_css_random": '"css_interpolation":"none"' in page_text and '"random_choice":false' in page_text,
        "source_no_lower_contact": "hardware_contact" not in page_text,
        "all_plan_samples": len(plans) == 10 and all(len(item.get("phases", [])) >= 6 for item in plans),
    }
    bound = {
        "page": {"path": str(PAGE.relative_to(ROOT)).replace("\\", "/"), "sha256": page_sha},
        "generator": {"path": str(GENERATOR.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_bytes(canonical_bytes(GENERATOR))},
        "evidence": {name: {"path": f"docs/validation/companion-browser-family-micro-choreography-comp-req-544/{name}", "sha256": sha256_bytes(canonical_bytes(VALIDATION / name))} for name in ["focused-smoke-result.json", "full-family-real-clock-result.json", "blink-cadence-result.json", "parity-verifier-result.json"]},
    }
    result = {
        "schema": "companion.family-micro-machine-ready.comp-req-544.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "owner_gate": "PENDING",
        "requirement": "COMP-REQ-544",
        "source_commit": args.source_commit,
        "checks": checks,
        "bound": bound,
        "side_effects": {"hardware_contact": 0, "write": 0, "popup": 0, "owner_prompt": 0, "microphone_permission_request": 0},
        "non_goals": ["hardware", "lower", "touch", "Platform", "vendor", "production", "owner_window"],
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    output.write_bytes(payload)
    print(json.dumps({"status": result["status"], "output": str(output.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_bytes(payload)}, sort_keys=True))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
