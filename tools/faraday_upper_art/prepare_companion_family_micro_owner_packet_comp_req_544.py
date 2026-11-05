#!/usr/bin/env python3
"""Bind the offline COMP-REQ-544 machine evidence without opening a prompt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "docs/validation/companion-browser-family-micro-choreography-comp-req-544"


def digest(path: Path) -> str:
    value = path.read_bytes()
    if path.suffix.lower() in {".html", ".json", ".mjs", ".py", ".ps1"}:
        value = value.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(value).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=(VALIDATION / "owner-review-packet.json").as_posix())
    args = parser.parse_args()
    paths = {
        "machine": VALIDATION / "MACHINE_READY.json",
        "focused": VALIDATION / "focused-smoke-result.json",
        "clock": VALIDATION / "full-family-real-clock-result.json",
        "blink": VALIDATION / "blink-cadence-result.json",
        "parity": VALIDATION / "parity-verifier-result.json",
        "device_pack": VALIDATION / "device-pack/visual-frame-manifest.json",
        "candidate": ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html",
    }
    machine = json.loads(paths["machine"].read_text(encoding="utf-8"))
    if machine.get("status") != "MACHINE_READY" or machine.get("owner_gate") != "PENDING":
        raise SystemExit("MACHINE_READY is not eligible")
    bindings = [{"id": name, "path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": digest(path)} for name, path in paths.items()]
    result = {
        "schema": "companion.family-micro-owner-review-packet.comp-req-544.v1",
        "status": "READY_DEFAULT_OFF",
        "requirement": "COMP-REQ-544",
        "machine_ready_sha256": digest(paths["machine"]),
        "candidate_sha256": digest(paths["candidate"]),
        "owner_gate": "PENDING",
        "execute_authorized": False,
        "bindings": bindings,
        "human_boundary": "本轮不打开人工验收窗；仅 owner 后续明确授权时才可观察。",
        "physical_gates": {"hardware": False, "flash": False, "production": False},
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    output.write_bytes(payload)
    print(json.dumps({"status": result["status"], "output": str(output.relative_to(ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(payload).hexdigest().upper()}, sort_keys=True))


if __name__ == "__main__":
    main()
