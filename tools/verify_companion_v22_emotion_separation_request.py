#!/usr/bin/env python3
"""Verify the V22 locked-V9 emotion-separation request before generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
REQUEST = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/"
    "generation-request.json"
)
DEFAULT_WRITE = ROOT / "docs/validation/companion-v22-emotion-separation-request-preflight-20260719.json"
EXPECTED_EMOTIONS = ("calm", "curious", "warm", "playful", "puzzled", "alert")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256,
        "locked V9 source hash drifted")
    references = request.get("reference_images")
    add(errors, isinstance(references, list) and len(references) == 1,
        "V22 must have exactly one visual reference")
    reference = references[0] if isinstance(references, list) and references else {}
    add(errors, isinstance(reference, dict) and reference.get("path") ==
        "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png" and
        reference.get("sha256") == LOCKED_V9_SHA256,
        "V22 must use the locked V9 source as its sole reference")
    emotions = request.get("emotion_contract")
    names = tuple(item.get("name") for item in emotions) if isinstance(emotions, list) and \
        all(isinstance(item, dict) for item in emotions) else ()
    add(errors, names == EXPECTED_EMOTIONS, "V22 emotion contract drifted")
    separation = request.get("separation_contract")
    add(errors, isinstance(separation, dict) and
        "at least two visible component groups" in str(separation.get("pairwise_rule", "")),
        "V22 request lacks the required pairwise component-separation rule")
    prompt = request.get("prompt_delta")
    add(errors, isinstance(prompt, str) and all(name.title() in prompt for name in EXPECTED_EMOTIONS),
        "V22 prompt does not name all six distinct everyday emotions")
    policy = str(request.get("reference_policy", ""))
    add(errors, "V21 is accepted regression evidence only" in policy and "Locked V9 is the only prompt reference" in policy,
        "V22 request does not preserve V21 while keeping V9 as the sole prompt reference")
    negative = request.get("negative_prompt")
    negative_text = " ".join(str(item) for item in negative) if isinstance(negative, list) else ""
    add(errors, "no changed eye type" in negative_text and "no detached giant punctuation" in negative_text,
        "V22 request does not protect V9 eye identity or reject detached punctuation")
    add(errors, request.get("runtime_resource_activated") is False and
        request.get("active_candidate_binding") == "forbidden",
        "V22 request must remain unbound and runtime inactive")
    result = {
        "schema": "companion.v22_emotion_separation_request_preflight.v1",
        "status": "PASS_V22_EMOTION_SEPARATION_REQUEST_PREFLIGHT" if not errors else
                  "FAIL_V22_EMOTION_SEPARATION_REQUEST_PREFLIGHT",
        "request": REQUEST.relative_to(ROOT).as_posix(),
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "emotion_names": list(EXPECTED_EMOTIONS),
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    DEFAULT_WRITE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_WRITE.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V22 emotion-separation request is locked to V9 and remains unbound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
