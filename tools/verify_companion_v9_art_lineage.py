#!/usr/bin/env python3
"""Verify the locked V9 art parent and incremental extension lineage."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs/art/iterations/companion-pet-expression-v9/art-direction-contract-v1.json"
LINEAGE_PATH = ROOT / "docs/art/iterations/companion-pet-expression-v9/art-lineage-v1.json"
V9_REQUEST_PATH = ROOT / "docs/art/iterations/companion-pet-expression-v9/generation-request.json"
V9_SOURCE_PATH = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
PRODUCT_REQUIREMENTS_PATH = ROOT / "docs/companion_product_requirements.md"
PROTECTED_ACCEPTANCE_PATH = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-art-lineage-machine-20260718.json"
LOCKED_V9_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED_ACCEPTANCE_HASH = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
V1_ID = "companion-pet-expression-v9-extension-v1-20260718"
V2_ID = "companion-pet-expression-v9-extension-v2-20260718"
V3_ID = "companion-pet-expression-v9-extension-v3-daily-eye-proof-20260718"
V4_ID = "companion-pet-expression-v9-extension-v4-emotion-transition-anchors-20260718"
V5_ID = "companion-pet-expression-v9-extension-v5-emotion-anchors-direction-repair-20260718"
V6_ID = "companion-pet-expression-v9-extension-v6-down-gaze-compact-reflection-20260718"
V7_ID = "companion-pet-expression-v9-extension-v7-daily-direction-strip-20260718"
V8_ID = "companion-pet-expression-v9-extension-v8-emotion-anchor-panel-20260718"
V9_ID = "companion-pet-expression-v9-extension-v9-expanded-daily-direction-strip-20260718"
V10_ID = "companion-pet-expression-v9-extension-v10-expanded-emotion-panel-20260718"
V11_ID = "companion-pet-expression-v9-extension-v11-secondary-detail-kit-20260718"


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def is_repo_relative(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        (ROOT / value).resolve().relative_to(ROOT)
    except ValueError:
        return False
    return True


def reference_is_locked_v9(reference: object) -> bool:
    return isinstance(reference, dict) and reference.get("path") == rel(V9_SOURCE_PATH) and \
        str(reference.get("sha256", "")).upper() == LOCKED_V9_HASH


def validate_extension_request(
    request: dict[str, Any],
    errors: list[str],
    context: str,
    require_generated_output: bool,
    preflight: bool,
    strict_eye_language: bool,
) -> None:
    for field in ("iteration_id", "prompt", "negative_constraints", "planned_generated_output", "post_generation_gate"):
        add(errors, bool(request.get(field)), f"{context} is missing {field}")
    add(errors, isinstance(request.get("negative_constraints"), list) and bool(request.get("negative_constraints")),
        f"{context} negative constraints are missing")
    add(errors, is_repo_relative(request.get("planned_generated_output")),
        f"{context} planned output escapes the repository")
    add(errors, str(request.get("candidate_scope", "")).startswith("supplemental_component_source"),
        f"{context} is not limited to supplemental source components")
    source_art_type = request.get("source_art_type", "face_anchor")
    add(errors, source_art_type in ("face_anchor", "detail_component_kit"),
        f"{context} has an unsupported source art type")
    target_profile = request.get("target_profile")
    add(errors, isinstance(target_profile, dict) and target_profile.get("runtime_status") ==
        "inactive_pending_component_export_machine_checks_and_owner_review",
        f"{context} is not explicitly runtime inactive")

    references = request.get("source_references")
    locked_references = [reference for reference in references if reference_is_locked_v9(reference)] \
        if isinstance(references, list) else []
    add(errors, len(locked_references) == 1, f"{context} does not name the locked V9 source exactly once")
    if isinstance(references, list):
        for reference in references:
            if reference_is_locked_v9(reference):
                continue
            role = str(reference.get("role", "")).lower() if isinstance(reference, dict) else ""
            add(errors, "reject" in role and ("do not" in role or "never" in role),
                f"{context} permits a non-V9 image reference")
    else:
        errors.append(f"{context} source references are malformed")

    prompt = str(request.get("prompt", "")).lower()
    negative = " ".join(str(item).lower() for item in request.get("negative_constraints", [])
        if isinstance(item, str))
    if strict_eye_language and source_art_type == "face_anchor":
        policy = f"{prompt} {negative}"
        add(errors, "solid" in prompt and "black" in prompt and "oval" in prompt and "eye" in prompt,
            f"{context} prompt does not preserve the solid black V9 eye-body gate")
        add(errors, "sclera" in policy and "ring" in policy and "drooping" in policy,
            f"{context} prompt does not explicitly reject V1/V2 eye regressions")
        required_cells = request.get("required_cells")
        includes_sleep = isinstance(required_cells, list) and any(
            "sleep" in str(cell).lower() for cell in required_cells
        )
        if includes_sleep:
            add(errors, "moon" in prompt and "no moon" in prompt,
                f"{context} prompt does not preserve the sleep-without-moon constraint")
        add(errors, "charging" in negative and "error" in negative,
            f"{context} negative constraints do not preserve charging/error fail-closed behavior")
    if source_art_type == "detail_component_kit":
        policy = f"{prompt} {negative}"
        add(errors, "no face" in policy and "no eye" in policy and "cat" in policy,
            f"{context} detail kit does not explicitly exclude face, eye, and cat regressions")

    output = request.get("generated_output")
    if require_generated_output:
        add(errors, isinstance(output, dict), f"{context} generated output record is missing")
        if isinstance(output, dict):
            output_path = output.get("path")
            add(errors, output_path == request.get("planned_generated_output") and is_repo_relative(output_path),
                f"{context} generated output path drifted")
            path = ROOT / str(output_path)
            add(errors, path.is_file() and str(output.get("sha256", "")).upper() == sha256(path),
                f"{context} generated output hash drifted")
    elif preflight:
        add(errors, output is None, f"{context} preflight request already contains generated output")


def verify_repository() -> dict[str, Any]:
    errors: list[str] = []
    contract = load_json(CONTRACT_PATH)
    lineage = load_json(LINEAGE_PATH)
    v9_request = load_json(V9_REQUEST_PATH)

    add(errors, contract.get("schema") == "companion.v9_art_direction_contract.v1" and
        contract.get("status") == "active" and contract.get("product_requirement") == "COMP-REQ-118",
        "V9 art direction contract is missing or inactive")
    locked_parent = contract.get("locked_visual_parent")
    add(errors, isinstance(locked_parent, dict) and locked_parent.get("path") == rel(V9_SOURCE_PATH) and
        str(locked_parent.get("sha256", "")).upper() == LOCKED_V9_HASH and
        locked_parent.get("mutation") == "forbidden" and locked_parent.get("replacement") == "forbidden",
        "art direction contract no longer locks the original V9 image")
    add(errors, V9_SOURCE_PATH.is_file() and sha256(V9_SOURCE_PATH) == LOCKED_V9_HASH,
        "locked V9 image hash drifted")
    add(errors, v9_request.get("status") == "OWNER_APPROVED_BASELINE_LOCKED" and
        isinstance(v9_request.get("generated_output"), dict) and
        str(v9_request["generated_output"].get("sha256", "")).upper() == LOCKED_V9_HASH,
        "original V9 generation request no longer identifies the locked baseline")

    requirement_text = PRODUCT_REQUIREMENTS_PATH.read_text(encoding="utf-8")
    for requirement in ("COMP-REQ-116", "COMP-REQ-117", "COMP-REQ-118", "COMP-REQ-119"):
        add(errors, requirement in requirement_text, f"product registry is missing {requirement}")
    add(errors, PROTECTED_ACCEPTANCE_PATH.is_file() and sha256(PROTECTED_ACCEPTANCE_PATH) == PROTECTED_ACCEPTANCE_HASH,
        "protected owner acceptance artifact hash drifted")

    identity = contract.get("identity_mother_prompt")
    locked_id = identity.get("iteration_id") if isinstance(identity, dict) else None
    add(errors, lineage.get("schema") == "companion.v9_art_lineage.v1" and
        lineage.get("contract") == rel(CONTRACT_PATH) and lineage.get("locked_parent_iteration") == locked_id,
        "art lineage is not bound to the V9 contract")
    items = lineage.get("iterations")
    add(errors, isinstance(items, list), "art lineage iterations are malformed")
    records = {item.get("iteration_id"): item for item in items if isinstance(item, dict)} if isinstance(items, list) else {}
    locked_record = records.get(locked_id)
    add(errors, isinstance(locked_record, dict) and locked_record.get("status") == "accepted_locked_parent" and
        locked_record.get("output") == rel(V9_SOURCE_PATH) and
        str(locked_record.get("output_sha256", "")).upper() == LOCKED_V9_HASH,
        "art lineage locked parent record drifted")

    expected = {
        V1_ID: ("rejected_owner_eye_geometry", "REJECTED_OWNER_EYE_GEOMETRY_V1_20260718"),
        V2_ID: ("rejected_machine_open_eye_identity", "REJECTED_MACHINE_OPEN_EYE_IDENTITY_V2_20260718"),
    }
    for iteration_id, (lineage_status, request_status) in expected.items():
        record = records.get(iteration_id)
        add(errors, isinstance(record, dict), f"missing lineage record for {iteration_id}")
        if not isinstance(record, dict):
            continue
        add(errors, record.get("kind") == "extension_candidate" and record.get("render_parent_iteration") == locked_id and
            record.get("status") == lineage_status and record.get("eligible_as_visual_reference") is False and
            record.get("eligible_for_component_export") is False,
            f"{iteration_id} has an invalid eligibility or parent state")
        request_path_value = record.get("generation_request")
        add(errors, is_repo_relative(request_path_value), f"{iteration_id} generation request path escapes repository")
        if not is_repo_relative(request_path_value):
            continue
        request_path = ROOT / str(request_path_value)
        add(errors, request_path.is_file(), f"missing generation request for {iteration_id}")
        if not request_path.is_file():
            continue
        request = load_json(request_path)
        add(errors, request.get("iteration_id") == iteration_id and request.get("status") == request_status,
            f"{iteration_id} request status or identifier drifted")
        validate_extension_request(
            request,
            errors,
            iteration_id,
            require_generated_output=True,
            preflight=False,
            strict_eye_language=iteration_id == V2_ID,
        )
        output = request.get("generated_output")
        if isinstance(output, dict):
            add(errors, record.get("output") == output.get("path") and
                str(record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                f"{iteration_id} lineage/output record drifted")

    v2_record = records.get(V2_ID)
    if isinstance(v2_record, dict):
        add(errors, v2_record.get("rejected_predecessor") == V1_ID,
            "V2 does not name rejected V1 as failure evidence")

    v3_record = records.get(V3_ID)
    add(errors, isinstance(v3_record, dict), "missing lineage record for the V3 daily eye proof")
    if isinstance(v3_record, dict):
        allowed_v3_states = {
            "machine_contract_pass_pending_owner_review": "MACHINE_ART_DIRECTION_PASS_PENDING_OWNER_REVIEW",
            "rejected_machine_daily_attention_readability": "REJECTED_MACHINE_DAILY_ATTENTION_READABILITY_V3_20260718",
            "rejected_machine_open_eye_identity": "REJECTED_MACHINE_OPEN_EYE_IDENTITY_V3_20260718",
            "rejected_owner_preview_direction": "REJECTED_OWNER_PREVIEW_DIRECTION_V3_20260718",
        }
        v3_status = v3_record.get("status")
        add(errors, v3_record.get("kind") == "extension_candidate" and
            v3_record.get("render_parent_iteration") == locked_id and
            v3_record.get("eligible_as_visual_reference") is False and
            v3_record.get("eligible_for_component_export") is False and
            v3_status in allowed_v3_states,
            "V3 daily eye proof has invalid lineage state or eligibility")
        v3_request_path_value = v3_record.get("generation_request")
        add(errors, is_repo_relative(v3_request_path_value), "V3 generation request path escapes repository")
        if is_repo_relative(v3_request_path_value):
            v3_request_path = ROOT / str(v3_request_path_value)
            add(errors, v3_request_path.is_file(), "missing V3 generation request")
            if v3_request_path.is_file():
                v3_request = load_json(v3_request_path)
                expected_request_status = allowed_v3_states.get(v3_status)
                add(errors, v3_request.get("iteration_id") == V3_ID and
                    v3_request.get("status") == expected_request_status,
                    "V3 request identifier or status drifted")
                validate_extension_request(
                    v3_request,
                    errors,
                    V3_ID,
                    require_generated_output=True,
                    preflight=False,
                    strict_eye_language=True,
                )
                output = v3_request.get("generated_output")
                if isinstance(output, dict):
                    add(errors, output.get("status") == v3_status and
                        v3_record.get("output") == output.get("path") and
                        str(v3_record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                        "V3 output and lineage status drifted")
                    eye_report_value = output.get("open_eye_identity_report")
                    attention_report_value = output.get("daily_attention_readability_report")
                    for report_value, label in ((eye_report_value, "open-eye"),
                                                (attention_report_value, "daily-attention")):
                        add(errors, is_repo_relative(report_value) and (ROOT / str(report_value)).is_file(),
                            f"missing V3 {label} report")
                    if is_repo_relative(eye_report_value) and (ROOT / str(eye_report_value)).is_file():
                        eye_report = load_json(ROOT / str(eye_report_value))
                        expected_eye_status = "FAIL_OPEN_EYE_IDENTITY_GATE" if \
                            v3_status == "rejected_machine_open_eye_identity" else "PASS_OPEN_EYE_IDENTITY_GATE"
                        add(errors, eye_report.get("status") == expected_eye_status and
                            eye_report.get("candidate_sha256") == output.get("sha256"),
                            "V3 open-eye evidence disagrees with its lineage state")
                    if is_repo_relative(attention_report_value) and (ROOT / str(attention_report_value)).is_file():
                        attention_report = load_json(ROOT / str(attention_report_value))
                        expected_attention_status = "FAIL_DAILY_ATTENTION_PROOF_GATE" if \
                            v3_status == "rejected_machine_daily_attention_readability" else "PASS_DAILY_ATTENTION_PROOF_GATE"
                        add(errors, attention_report.get("status") == expected_attention_status and
                            attention_report.get("candidate_sha256") == output.get("sha256"),
                            "V3 attention evidence disagrees with its lineage state")

    v4_record = records.get(V4_ID)
    add(errors, isinstance(v4_record, dict), "missing lineage record for the V4 emotion anchors")
    if isinstance(v4_record, dict):
        allowed_v4_states = {
            "machine_contract_pass_pending_owner_review": "MACHINE_ART_DIRECTION_PASS_PENDING_OWNER_REVIEW",
            "rejected_machine_open_eye_identity": "REJECTED_MACHINE_OPEN_EYE_IDENTITY_V4_20260718",
            "rejected_machine_daily_attention_readability": "REJECTED_MACHINE_DAILY_ATTENTION_READABILITY_V4_20260718",
            "rejected_machine_emotion_anchor_diversity": "REJECTED_MACHINE_EMOTION_ANCHOR_DIVERSITY_V4_20260718",
        }
        v4_status = v4_record.get("status")
        add(errors, v4_record.get("kind") == "extension_candidate" and
            v4_record.get("render_parent_iteration") == locked_id and
            v4_record.get("eligible_as_visual_reference") is False and
            v4_record.get("eligible_for_component_export") is False and
            v4_status in allowed_v4_states,
            "V4 emotion anchors have invalid lineage state or eligibility")
        v4_request_path_value = v4_record.get("generation_request")
        add(errors, is_repo_relative(v4_request_path_value), "V4 generation request path escapes repository")
        if is_repo_relative(v4_request_path_value):
            v4_request_path = ROOT / str(v4_request_path_value)
            add(errors, v4_request_path.is_file(), "missing V4 generation request")
            if v4_request_path.is_file():
                v4_request = load_json(v4_request_path)
                expected_request_status = allowed_v4_states.get(v4_status)
                add(errors, v4_request.get("iteration_id") == V4_ID and
                    v4_request.get("status") == expected_request_status,
                    "V4 request identifier or status drifted")
                validate_extension_request(
                    v4_request,
                    errors,
                    V4_ID,
                    require_generated_output=True,
                    preflight=False,
                    strict_eye_language=True,
                )
                output = v4_request.get("generated_output")
                if isinstance(output, dict):
                    add(errors, output.get("status") == v4_status and
                        v4_record.get("output") == output.get("path") and
                        str(v4_record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                        "V4 output and lineage status drifted")
                    reports = (
                        ("open_eye_identity_report", "open-eye"),
                        ("daily_attention_readability_report", "daily-attention"),
                        ("emotion_transition_anchor_report", "emotion-anchor"),
                    )
                    for property_name, label in reports:
                        report_value = output.get(property_name)
                        add(errors, is_repo_relative(report_value) and (ROOT / str(report_value)).is_file(),
                            f"missing V4 {label} report")
                    checks = (
                        ("open_eye_identity_report", "FAIL_OPEN_EYE_IDENTITY_GATE" if
                         v4_status == "rejected_machine_open_eye_identity" else "PASS_OPEN_EYE_IDENTITY_GATE"),
                        ("daily_attention_readability_report", "FAIL_DAILY_ATTENTION_PROOF_GATE" if
                         v4_status == "rejected_machine_daily_attention_readability" else "PASS_DAILY_ATTENTION_PROOF_GATE"),
                        ("emotion_transition_anchor_report", "FAIL_EMOTION_TRANSITION_ANCHOR_GATE" if
                         v4_status == "rejected_machine_emotion_anchor_diversity" else "PASS_EMOTION_TRANSITION_ANCHOR_GATE"),
                    )
                    for property_name, expected_status in checks:
                        report_value = output.get(property_name)
                        if is_repo_relative(report_value) and (ROOT / str(report_value)).is_file():
                            report = load_json(ROOT / str(report_value))
                            add(errors, report.get("status") == expected_status and
                                report.get("candidate_sha256") == output.get("sha256"),
                                f"V4 {property_name} evidence disagrees with its lineage state")

    v5_record = records.get(V5_ID)
    add(errors, isinstance(v5_record, dict), "missing lineage record for the V5 direction-repair anchors")
    if isinstance(v5_record, dict):
        allowed_v5_states = {
            "machine_contract_pass_pending_owner_review": "MACHINE_ART_DIRECTION_PASS_PENDING_OWNER_REVIEW",
            "rejected_machine_open_eye_identity": "REJECTED_MACHINE_OPEN_EYE_IDENTITY_V5_20260718",
            "rejected_machine_daily_attention_readability": "REJECTED_MACHINE_DAILY_ATTENTION_READABILITY_V5_20260718",
            "rejected_machine_emotion_anchor_diversity": "REJECTED_MACHINE_EMOTION_ANCHOR_DIVERSITY_V5_20260718",
        }
        expected_v5_reports = {
            "machine_contract_pass_pending_owner_review": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
                "PASS_EMOTION_TRANSITION_ANCHOR_GATE",
            ),
            "rejected_machine_open_eye_identity": (
                "FAIL_OPEN_EYE_IDENTITY_GATE",
                "FAIL_DAILY_ATTENTION_PROOF_GATE",
                "FAIL_EMOTION_TRANSITION_ANCHOR_GATE",
            ),
            "rejected_machine_daily_attention_readability": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "FAIL_DAILY_ATTENTION_PROOF_GATE",
                "PASS_EMOTION_TRANSITION_ANCHOR_GATE",
            ),
            "rejected_machine_emotion_anchor_diversity": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
                "FAIL_EMOTION_TRANSITION_ANCHOR_GATE",
            ),
        }
        v5_status = v5_record.get("status")
        add(errors, v5_record.get("kind") == "extension_candidate" and
            v5_record.get("render_parent_iteration") == locked_id and
            v5_record.get("eligible_as_visual_reference") is False and
            v5_record.get("eligible_for_component_export") is False and
            v5_status in allowed_v5_states,
            "V5 direction-repair anchors have invalid lineage state or eligibility")
        v5_request_path_value = v5_record.get("generation_request")
        add(errors, is_repo_relative(v5_request_path_value), "V5 generation request path escapes repository")
        if is_repo_relative(v5_request_path_value):
            v5_request_path = ROOT / str(v5_request_path_value)
            add(errors, v5_request_path.is_file(), "missing V5 generation request")
            if v5_request_path.is_file():
                v5_request = load_json(v5_request_path)
                expected_request_status = allowed_v5_states.get(v5_status)
                add(errors, v5_request.get("iteration_id") == V5_ID and
                    v5_request.get("status") == expected_request_status,
                    "V5 request identifier or status drifted")
                validate_extension_request(
                    v5_request,
                    errors,
                    V5_ID,
                    require_generated_output=True,
                    preflight=False,
                    strict_eye_language=True,
                )
                output = v5_request.get("generated_output")
                if isinstance(output, dict):
                    add(errors, output.get("status") == v5_status and
                        v5_record.get("output") == output.get("path") and
                        str(v5_record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                        "V5 output and lineage status drifted")
                    report_properties = (
                        "open_eye_identity_report",
                        "daily_attention_readability_report",
                        "emotion_transition_anchor_report",
                    )
                    expected_reports = expected_v5_reports.get(v5_status, ())
                    for property_name, expected_status in zip(report_properties, expected_reports):
                        report_value = output.get(property_name)
                        add(errors, is_repo_relative(report_value) and (ROOT / str(report_value)).is_file(),
                            f"missing V5 {property_name} report")
                        if is_repo_relative(report_value) and (ROOT / str(report_value)).is_file():
                            report = load_json(ROOT / str(report_value))
                            add(errors, report.get("status") == expected_status and
                                report.get("candidate_sha256") == output.get("sha256"),
                                f"V5 {property_name} evidence disagrees with its lineage state")

    v6_record = records.get(V6_ID)
    add(errors, isinstance(v6_record, dict), "missing lineage record for the V6 down-reflection repair")
    if isinstance(v6_record, dict):
        allowed_v6_states = {
            "machine_contract_pass_pending_owner_review": "MACHINE_ART_DIRECTION_PASS_PENDING_OWNER_REVIEW",
            "rejected_machine_open_eye_identity": "REJECTED_MACHINE_OPEN_EYE_IDENTITY_V6_20260718",
            "rejected_machine_daily_attention_readability": "REJECTED_MACHINE_DAILY_ATTENTION_READABILITY_V6_20260718",
            "rejected_machine_emotion_anchor_diversity": "REJECTED_MACHINE_EMOTION_ANCHOR_DIVERSITY_V6_20260718",
            "rejected_machine_daily_attention_and_sleep_rest": "REJECTED_MACHINE_DAILY_ATTENTION_AND_SLEEP_REST_V6_20260718",
        }
        expected_v6_reports = {
            "machine_contract_pass_pending_owner_review": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
                "PASS_EMOTION_TRANSITION_ANCHOR_GATE",
            ),
            "rejected_machine_open_eye_identity": (
                "FAIL_OPEN_EYE_IDENTITY_GATE",
                "FAIL_DAILY_ATTENTION_PROOF_GATE",
                "FAIL_EMOTION_TRANSITION_ANCHOR_GATE",
            ),
            "rejected_machine_daily_attention_readability": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "FAIL_DAILY_ATTENTION_PROOF_GATE",
                "PASS_EMOTION_TRANSITION_ANCHOR_GATE",
            ),
            "rejected_machine_emotion_anchor_diversity": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
                "FAIL_EMOTION_TRANSITION_ANCHOR_GATE",
            ),
            "rejected_machine_daily_attention_and_sleep_rest": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "FAIL_DAILY_ATTENTION_PROOF_GATE",
                "FAIL_EMOTION_TRANSITION_ANCHOR_GATE",
            ),
        }
        v6_status = v6_record.get("status")
        add(errors, v6_record.get("kind") == "extension_candidate" and
            v6_record.get("render_parent_iteration") == locked_id and
            v6_record.get("eligible_as_visual_reference") is False and
            v6_record.get("eligible_for_component_export") is False and
            v6_status in allowed_v6_states,
            "V6 down-reflection repair has invalid lineage state or eligibility")
        v6_request_path_value = v6_record.get("generation_request")
        add(errors, is_repo_relative(v6_request_path_value), "V6 generation request path escapes repository")
        if is_repo_relative(v6_request_path_value):
            v6_request_path = ROOT / str(v6_request_path_value)
            add(errors, v6_request_path.is_file(), "missing V6 generation request")
            if v6_request_path.is_file():
                v6_request = load_json(v6_request_path)
                expected_request_status = allowed_v6_states.get(v6_status)
                add(errors, v6_request.get("iteration_id") == V6_ID and
                    v6_request.get("status") == expected_request_status,
                    "V6 request identifier or status drifted")
                validate_extension_request(
                    v6_request,
                    errors,
                    V6_ID,
                    require_generated_output=True,
                    preflight=False,
                    strict_eye_language=True,
                )
                output = v6_request.get("generated_output")
                if isinstance(output, dict):
                    add(errors, output.get("status") == v6_status and
                        v6_record.get("output") == output.get("path") and
                        str(v6_record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                        "V6 output and lineage status drifted")
                    report_properties = (
                        "open_eye_identity_report",
                        "daily_attention_readability_report",
                        "emotion_transition_anchor_report",
                    )
                    expected_reports = expected_v6_reports.get(v6_status, ())
                    for property_name, expected_status in zip(report_properties, expected_reports):
                        report_value = output.get(property_name)
                        add(errors, is_repo_relative(report_value) and (ROOT / str(report_value)).is_file(),
                            f"missing V6 {property_name} report")
                        if is_repo_relative(report_value) and (ROOT / str(report_value)).is_file():
                            report = load_json(ROOT / str(report_value))
                            add(errors, report.get("status") == expected_status and
                                report.get("candidate_sha256") == output.get("sha256"),
                                f"V6 {property_name} evidence disagrees with its lineage state")

    v7_record = records.get(V7_ID)
    add(errors, isinstance(v7_record, dict), "missing lineage record for the V7 Daily direction strip")
    if isinstance(v7_record, dict):
        allowed_v7_states = {
            "machine_daily_source_pass_pending_complementary_emotion_bundle":
                "MACHINE_DAILY_SOURCE_PASS_PENDING_COMPLEMENTARY_EMOTION_BUNDLE_V7_20260718",
            "machine_complete_source_bundle_pass_pending_owner_review":
                "MACHINE_COMPLETE_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW_V7_20260718",
            "rejected_owner_emotion_repertoire": "REJECTED_OWNER_EMOTION_REPERTOIRE_V7_20260718",
            "rejected_machine_open_eye_identity": "REJECTED_MACHINE_OPEN_EYE_IDENTITY_V7_20260718",
            "rejected_machine_daily_attention_readability":
                "REJECTED_MACHINE_DAILY_ATTENTION_READABILITY_V7_20260718",
        }
        expected_v7_reports = {
            "machine_daily_source_pass_pending_complementary_emotion_bundle": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
            ),
            "machine_complete_source_bundle_pass_pending_owner_review": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
            ),
            "rejected_owner_emotion_repertoire": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
            ),
            "rejected_machine_open_eye_identity": (
                "FAIL_OPEN_EYE_IDENTITY_GATE",
                "FAIL_DAILY_ATTENTION_PROOF_GATE",
            ),
            "rejected_machine_daily_attention_readability": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "FAIL_DAILY_ATTENTION_PROOF_GATE",
            ),
        }
        v7_status = v7_record.get("status")
        add(errors, v7_record.get("kind") == "extension_candidate" and
            v7_record.get("render_parent_iteration") == locked_id and
            v7_record.get("eligible_as_visual_reference") is False and
            v7_record.get("eligible_for_component_export") is False and
            v7_status in allowed_v7_states,
            "V7 Daily direction strip has invalid lineage state or eligibility")
        v7_request_path_value = v7_record.get("generation_request")
        add(errors, is_repo_relative(v7_request_path_value), "V7 generation request path escapes repository")
        if is_repo_relative(v7_request_path_value):
            v7_request_path = ROOT / str(v7_request_path_value)
            add(errors, v7_request_path.is_file(), "missing V7 generation request")
            if v7_request_path.is_file():
                v7_request = load_json(v7_request_path)
                expected_request_status = allowed_v7_states.get(v7_status)
                add(errors, v7_request.get("iteration_id") == V7_ID and
                    v7_request.get("status") == expected_request_status,
                    "V7 request identifier or status drifted")
                validate_extension_request(
                    v7_request,
                    errors,
                    V7_ID,
                    require_generated_output=True,
                    preflight=False,
                    strict_eye_language=True,
                )
                output = v7_request.get("generated_output")
                if isinstance(output, dict):
                    add(errors, output.get("status") == v7_status and
                        v7_record.get("output") == output.get("path") and
                        str(v7_record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                        "V7 output and lineage status drifted")
                    report_properties = (
                        "open_eye_identity_report",
                        "daily_attention_readability_report",
                    )
                    expected_reports = expected_v7_reports.get(v7_status, ())
                    for property_name, expected_status in zip(report_properties, expected_reports):
                        report_value = output.get(property_name)
                        add(errors, is_repo_relative(report_value) and (ROOT / str(report_value)).is_file(),
                            f"missing V7 {property_name} report")
                        if is_repo_relative(report_value) and (ROOT / str(report_value)).is_file():
                            report = load_json(ROOT / str(report_value))
                            add(errors, report.get("status") == expected_status and
                                report.get("candidate_sha256") == output.get("sha256"),
                                f"V7 {property_name} evidence disagrees with its lineage state")
                    bundle_report_value = output.get("source_bundle_machine_report")
                    if v7_status == "machine_complete_source_bundle_pass_pending_owner_review":
                        add(errors, is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file(),
                            "missing V7 complete source-bundle report")
                        if is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file():
                            bundle_report = load_json(ROOT / str(bundle_report_value))
                            add(errors, bundle_report.get("status") == "PASS_COMPLETE_EXPRESSION_SOURCE_BUNDLE_GATE",
                                "V7 source-bundle report is not machine-passing")
                    if v7_status == "rejected_owner_emotion_repertoire":
                        review_value = output.get("owner_review_result")
                        add(errors, is_repo_relative(review_value) and (ROOT / str(review_value)).is_file(),
                            "missing V7 owner-rejection result")
                        if is_repo_relative(review_value) and (ROOT / str(review_value)).is_file():
                            review = load_json(ROOT / str(review_value))
                            add(errors, review.get("selected") == "需修改" and
                                bool(str(review.get("text", "")).strip()),
                                "V7 owner-rejection result does not record insufficient emotion repertoire")

    v8_record = records.get(V8_ID)
    add(errors, isinstance(v8_record, dict), "missing lineage record for the V8 emotion-anchor panel")
    if isinstance(v8_record, dict):
        allowed_v8_states = {
            "machine_complete_source_bundle_pass_pending_owner_review":
                "MACHINE_COMPLETE_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW_V8_20260718",
            "rejected_owner_emotion_repertoire": "REJECTED_OWNER_EMOTION_REPERTOIRE_V8_20260718",
            "rejected_machine_open_eye_identity": "REJECTED_MACHINE_OPEN_EYE_IDENTITY_V8_20260718",
            "rejected_machine_emotion_anchor_panel":
                "REJECTED_MACHINE_EMOTION_ANCHOR_PANEL_V8_20260718",
        }
        expected_v8_reports = {
            "machine_complete_source_bundle_pass_pending_owner_review": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_EMOTION_ANCHOR_PANEL_GATE",
            ),
            "rejected_owner_emotion_repertoire": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_EMOTION_ANCHOR_PANEL_GATE",
            ),
            "rejected_machine_open_eye_identity": (
                "FAIL_OPEN_EYE_IDENTITY_GATE",
                "FAIL_EMOTION_ANCHOR_PANEL_GATE",
            ),
            "rejected_machine_emotion_anchor_panel": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "FAIL_EMOTION_ANCHOR_PANEL_GATE",
            ),
        }
        v8_status = v8_record.get("status")
        add(errors, v8_record.get("kind") == "extension_candidate" and
            v8_record.get("render_parent_iteration") == locked_id and
            v8_record.get("paired_daily_source_iteration") == V7_ID and
            v8_record.get("eligible_as_visual_reference") is False and
            v8_record.get("eligible_for_component_export") is False and
            v8_status in allowed_v8_states,
            "V8 emotion-anchor panel has invalid lineage state or eligibility")
        v8_request_path_value = v8_record.get("generation_request")
        add(errors, is_repo_relative(v8_request_path_value), "V8 generation request path escapes repository")
        if is_repo_relative(v8_request_path_value):
            v8_request_path = ROOT / str(v8_request_path_value)
            add(errors, v8_request_path.is_file(), "missing V8 generation request")
            if v8_request_path.is_file():
                v8_request = load_json(v8_request_path)
                expected_request_status = allowed_v8_states.get(v8_status)
                add(errors, v8_request.get("iteration_id") == V8_ID and
                    v8_request.get("status") == expected_request_status and
                    v8_request.get("paired_daily_source_iteration") == V7_ID,
                    "V8 request identifier, status, or daily pairing drifted")
                validate_extension_request(
                    v8_request,
                    errors,
                    V8_ID,
                    require_generated_output=True,
                    preflight=False,
                    strict_eye_language=True,
                )
                output = v8_request.get("generated_output")
                if isinstance(output, dict):
                    add(errors, output.get("status") == v8_status and
                        v8_record.get("output") == output.get("path") and
                        str(v8_record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                        "V8 output and lineage status drifted")
                    report_properties = (
                        "open_eye_identity_report",
                        "emotion_anchor_panel_report",
                    )
                    expected_reports = expected_v8_reports.get(v8_status, ())
                    for property_name, expected_status in zip(report_properties, expected_reports):
                        report_value = output.get(property_name)
                        add(errors, is_repo_relative(report_value) and (ROOT / str(report_value)).is_file(),
                            f"missing V8 {property_name} report")
                        if is_repo_relative(report_value) and (ROOT / str(report_value)).is_file():
                            report = load_json(ROOT / str(report_value))
                            add(errors, report.get("status") == expected_status and
                                report.get("candidate_sha256") == output.get("sha256"),
                                f"V8 {property_name} evidence disagrees with its lineage state")
                    if v8_status == "machine_complete_source_bundle_pass_pending_owner_review":
                        manifest_value = output.get("source_bundle_manifest")
                        bundle_report_value = output.get("source_bundle_machine_report")
                        add(errors, is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file(),
                            "missing V8 complete source-bundle manifest")
                        add(errors, is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file(),
                            "missing V8 complete source-bundle report")
                        if is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file():
                            manifest = load_json(ROOT / str(manifest_value))
                            add(errors, manifest.get("status") ==
                                "MACHINE_COMPLETE_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW" and
                                manifest.get("machine_report") == bundle_report_value,
                                "V8 source-bundle manifest status drifted")
                        if is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file():
                            bundle_report = load_json(ROOT / str(bundle_report_value))
                            add(errors, bundle_report.get("status") == "PASS_COMPLETE_EXPRESSION_SOURCE_BUNDLE_GATE",
                                "V8 source-bundle report is not machine-passing")
                    if v8_status == "rejected_owner_emotion_repertoire":
                        review_value = output.get("owner_review_result")
                        manifest_value = output.get("source_bundle_manifest")
                        add(errors, is_repo_relative(review_value) and (ROOT / str(review_value)).is_file(),
                            "missing V8 owner-rejection result")
                        if is_repo_relative(review_value) and (ROOT / str(review_value)).is_file():
                            review = load_json(ROOT / str(review_value))
                            add(errors, review.get("selected") == "需修改" and
                                bool(str(review.get("text", "")).strip()),
                                "V8 owner-rejection result does not record insufficient emotion repertoire")
                        add(errors, is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file(),
                            "missing rejected V8 source-bundle manifest")
                        if is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file():
                            manifest = load_json(ROOT / str(manifest_value))
                            add(errors, manifest.get("status") == "REJECTED_OWNER_EMOTION_REPERTOIRE" and
                                manifest.get("owner_review_result") == review_value,
                                "V8 rejected source-bundle manifest status drifted")

    v9_record = records.get(V9_ID)
    add(errors, isinstance(v9_record, dict), "missing lineage record for the V9 expanded Daily strip")
    if isinstance(v9_record, dict):
        allowed_v9_states = {
            "machine_daily_source_pass_pending_expanded_emotion_panel":
                "MACHINE_DAILY_SOURCE_PASS_PENDING_EXPANDED_EMOTION_PANEL_V9_20260718",
            "machine_core_sixteen_source_bundle_pass_pending_detail_kit":
                "MACHINE_CORE_SIXTEEN_SOURCE_BUNDLE_PASS_PENDING_DETAIL_KIT_V9_20260718",
            "machine_full_source_bundle_pass_pending_owner_review":
                "MACHINE_FULL_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW_V9_20260718",
            "approved_owner_full_source_bundle": "APPROVED_OWNER_FULL_SOURCE_BUNDLE_V9_20260718",
            "machine_expanded_source_bundle_pass_pending_owner_review":
                "MACHINE_EXPANDED_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW_V9_20260718",
            "rejected_machine_open_eye_identity": "REJECTED_MACHINE_OPEN_EYE_IDENTITY_V9_20260718",
            "rejected_machine_daily_attention_readability":
                "REJECTED_MACHINE_DAILY_ATTENTION_READABILITY_V9_20260718",
            "rejected_owner_emotion_repertoire": "REJECTED_OWNER_EMOTION_REPERTOIRE_V9_20260718",
        }
        expected_v9_reports = {
            "machine_daily_source_pass_pending_expanded_emotion_panel": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
            ),
            "machine_core_sixteen_source_bundle_pass_pending_detail_kit": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
            ),
            "machine_full_source_bundle_pass_pending_owner_review": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
            ),
            "approved_owner_full_source_bundle": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
            ),
            "machine_expanded_source_bundle_pass_pending_owner_review": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
            ),
            "rejected_machine_open_eye_identity": (
                "FAIL_OPEN_EYE_IDENTITY_GATE",
                "FAIL_DAILY_ATTENTION_PROOF_GATE",
            ),
            "rejected_machine_daily_attention_readability": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "FAIL_DAILY_ATTENTION_PROOF_GATE",
            ),
            "rejected_owner_emotion_repertoire": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_DAILY_ATTENTION_PROOF_GATE",
            ),
        }
        v9_status = v9_record.get("status")
        add(errors, v9_record.get("kind") == "extension_candidate" and
            v9_record.get("render_parent_iteration") == locked_id and
            v9_record.get("eligible_as_visual_reference") is False and
            v9_record.get("eligible_for_component_export") is
            (v9_status == "approved_owner_full_source_bundle") and
            v9_status in allowed_v9_states,
            "V9 expanded Daily strip has invalid lineage state or eligibility")
        v9_request_path_value = v9_record.get("generation_request")
        add(errors, is_repo_relative(v9_request_path_value), "V9 generation request path escapes repository")
        if is_repo_relative(v9_request_path_value):
            v9_request_path = ROOT / str(v9_request_path_value)
            add(errors, v9_request_path.is_file(), "missing V9 generation request")
            if v9_request_path.is_file():
                v9_request = load_json(v9_request_path)
                expected_request_status = allowed_v9_states.get(v9_status)
                add(errors, v9_request.get("iteration_id") == V9_ID and
                    v9_request.get("status") == expected_request_status,
                    "V9 request identifier or status drifted")
                validate_extension_request(
                    v9_request,
                    errors,
                    V9_ID,
                    require_generated_output=True,
                    preflight=False,
                    strict_eye_language=True,
                )
                output = v9_request.get("generated_output")
                if isinstance(output, dict):
                    add(errors, output.get("status") == v9_status and
                        v9_record.get("output") == output.get("path") and
                        str(v9_record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                        "V9 output and lineage status drifted")
                    report_properties = (
                        "open_eye_identity_report",
                        "daily_attention_readability_report",
                    )
                    expected_reports = expected_v9_reports.get(v9_status, ())
                    for property_name, expected_status in zip(report_properties, expected_reports):
                        report_value = output.get(property_name)
                        add(errors, is_repo_relative(report_value) and (ROOT / str(report_value)).is_file(),
                            f"missing V9 {property_name} report")
                        if is_repo_relative(report_value) and (ROOT / str(report_value)).is_file():
                            report = load_json(ROOT / str(report_value))
                            add(errors, report.get("status") == expected_status and
                                report.get("candidate_sha256") == output.get("sha256"),
                                f"V9 {property_name} evidence disagrees with its lineage state")
                    if v9_status == "approved_owner_full_source_bundle":
                        review_value = output.get("owner_review_result")
                        add(errors, is_repo_relative(review_value) and (ROOT / str(review_value)).is_file(),
                            "missing V9 owner-approval result")
                        if is_repo_relative(review_value) and (ROOT / str(review_value)).is_file():
                            review = load_json(ROOT / str(review_value))
                            add(errors, review.get("selected") == "通过",
                                "V9 owner-approval result is not a pass")

    v10_record = records.get(V10_ID)
    add(errors, isinstance(v10_record, dict), "missing lineage record for the V10 expanded emotion panel")
    if isinstance(v10_record, dict):
        allowed_v10_states = {
            "machine_core_sixteen_source_bundle_pass_pending_detail_kit":
                "MACHINE_CORE_SIXTEEN_SOURCE_BUNDLE_PASS_PENDING_DETAIL_KIT_V10_20260718",
            "machine_full_source_bundle_pass_pending_owner_review":
                "MACHINE_FULL_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW_V10_20260718",
            "approved_owner_full_source_bundle": "APPROVED_OWNER_FULL_SOURCE_BUNDLE_V10_20260718",
            "rejected_machine_open_eye_identity": "REJECTED_MACHINE_OPEN_EYE_IDENTITY_V10_20260718",
            "rejected_machine_expanded_emotion_panel":
                "REJECTED_MACHINE_EXPANDED_EMOTION_PANEL_V10_20260718",
            "rejected_owner_emotion_repertoire": "REJECTED_OWNER_EMOTION_REPERTOIRE_V10_20260718",
        }
        expected_v10_reports = {
            "machine_core_sixteen_source_bundle_pass_pending_detail_kit": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_EXPANDED_EMOTION_PANEL_GATE",
            ),
            "machine_full_source_bundle_pass_pending_owner_review": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_EXPANDED_EMOTION_PANEL_GATE",
            ),
            "approved_owner_full_source_bundle": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_EXPANDED_EMOTION_PANEL_GATE",
            ),
            "rejected_machine_open_eye_identity": (
                "FAIL_OPEN_EYE_IDENTITY_GATE",
                "FAIL_EXPANDED_EMOTION_PANEL_GATE",
            ),
            "rejected_machine_expanded_emotion_panel": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "FAIL_EXPANDED_EMOTION_PANEL_GATE",
            ),
            "rejected_owner_emotion_repertoire": (
                "PASS_OPEN_EYE_IDENTITY_GATE",
                "PASS_EXPANDED_EMOTION_PANEL_GATE",
            ),
        }
        v10_status = v10_record.get("status")
        add(errors, v10_record.get("kind") == "extension_candidate" and
            v10_record.get("render_parent_iteration") == locked_id and
            v10_record.get("paired_daily_source_iteration") == V9_ID and
            v10_record.get("eligible_as_visual_reference") is False and
            v10_record.get("eligible_for_component_export") is
            (v10_status == "approved_owner_full_source_bundle") and
            v10_status in allowed_v10_states,
            "V10 expanded emotion panel has invalid lineage state or eligibility")
        v10_request_path_value = v10_record.get("generation_request")
        add(errors, is_repo_relative(v10_request_path_value), "V10 generation request path escapes repository")
        if is_repo_relative(v10_request_path_value):
            v10_request_path = ROOT / str(v10_request_path_value)
            add(errors, v10_request_path.is_file(), "missing V10 generation request")
            if v10_request_path.is_file():
                v10_request = load_json(v10_request_path)
                expected_request_status = allowed_v10_states.get(v10_status)
                add(errors, v10_request.get("iteration_id") == V10_ID and
                    v10_request.get("status") == expected_request_status and
                    v10_request.get("paired_daily_source_iteration") == V9_ID,
                    "V10 request identifier, status, or Daily pairing drifted")
                validate_extension_request(
                    v10_request,
                    errors,
                    V10_ID,
                    require_generated_output=True,
                    preflight=False,
                    strict_eye_language=True,
                )
                output = v10_request.get("generated_output")
                if isinstance(output, dict):
                    add(errors, output.get("status") == v10_status and
                        v10_record.get("output") == output.get("path") and
                        str(v10_record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                        "V10 output and lineage status drifted")
                    report_properties = (
                        "open_eye_identity_report",
                        "expanded_emotion_panel_report",
                    )
                    expected_reports = expected_v10_reports.get(v10_status, ())
                    for property_name, expected_status in zip(report_properties, expected_reports):
                        report_value = output.get(property_name)
                        add(errors, is_repo_relative(report_value) and (ROOT / str(report_value)).is_file(),
                            f"missing V10 {property_name} report")
                        if is_repo_relative(report_value) and (ROOT / str(report_value)).is_file():
                            report = load_json(ROOT / str(report_value))
                            add(errors, report.get("status") == expected_status and
                                report.get("candidate_sha256") == output.get("sha256"),
                                f"V10 {property_name} evidence disagrees with its lineage state")
                    if v10_status == "machine_core_sixteen_source_bundle_pass_pending_detail_kit":
                        manifest_value = output.get("expanded_source_bundle_manifest")
                        bundle_report_value = output.get("expanded_source_bundle_machine_report")
                        add(errors, is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file(),
                            "missing V10 core source-bundle manifest")
                        add(errors, is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file(),
                            "missing V10 core source-bundle report")
                        if is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file():
                            manifest = load_json(ROOT / str(manifest_value))
                            add(errors, manifest.get("status") ==
                                "MACHINE_CORE_SIXTEEN_SOURCE_BUNDLE_PASS_PENDING_DETAIL_KIT" and
                                manifest.get("machine_report") == bundle_report_value,
                                "V10 core source-bundle manifest status drifted")
                        if is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file():
                            bundle_report = load_json(ROOT / str(bundle_report_value))
                            add(errors, bundle_report.get("status") == "PASS_EXPANDED_EXPRESSION_SOURCE_BUNDLE_GATE",
                                "V10 core source-bundle report is not machine-passing")
                    if v10_status == "machine_full_source_bundle_pass_pending_owner_review":
                        manifest_value = output.get("full_source_bundle_manifest")
                        bundle_report_value = output.get("full_source_bundle_machine_report")
                        add(errors, is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file(),
                            "missing V10 full source-bundle manifest")
                        add(errors, is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file(),
                            "missing V10 full source-bundle report")
                        if is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file():
                            manifest = load_json(ROOT / str(manifest_value))
                            add(errors, manifest.get("status") ==
                                "MACHINE_FULL_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW" and
                                manifest.get("machine_report") == bundle_report_value,
                                "V10 full source-bundle manifest status drifted")
                        if is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file():
                            bundle_report = load_json(ROOT / str(bundle_report_value))
                            add(errors, bundle_report.get("status") == "PASS_FULL_EXPRESSION_SOURCE_BUNDLE_GATE",
                                "V10 full source-bundle report is not machine-passing")
                    if v10_status == "approved_owner_full_source_bundle":
                        review_value = output.get("owner_review_result")
                        manifest_value = output.get("full_source_bundle_manifest")
                        add(errors, is_repo_relative(review_value) and (ROOT / str(review_value)).is_file(),
                            "missing V10 owner-approval result")
                        if is_repo_relative(review_value) and (ROOT / str(review_value)).is_file():
                            review = load_json(ROOT / str(review_value))
                            add(errors, review.get("selected") == "通过",
                                "V10 owner-approval result is not a pass")
                        add(errors, is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file(),
                            "missing approved V10 full source-bundle manifest")
                        if is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file():
                            manifest = load_json(ROOT / str(manifest_value))
                            add(errors, manifest.get("status") ==
                                "APPROVED_OWNER_FULL_SOURCE_BUNDLE_COMPONENT_EXPORT_ALLOWED_RUNTIME_INACTIVE" and
                                manifest.get("component_export_eligible") is True and
                                manifest.get("runtime_resource_activated") is False and
                                manifest.get("owner_review_result") == review_value,
                                "V10 approved full source-bundle manifest status drifted")

    v11_record = records.get(V11_ID)
    add(errors, isinstance(v11_record, dict), "missing lineage record for the V11 secondary detail kit")
    if isinstance(v11_record, dict):
        allowed_v11_states = {
            "machine_full_source_bundle_pass_pending_owner_review":
                "MACHINE_FULL_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW_V11_20260718",
            "approved_owner_full_source_bundle": "APPROVED_OWNER_FULL_SOURCE_BUNDLE_V11_20260718",
            "rejected_machine_detail_component_kit":
                "REJECTED_MACHINE_DETAIL_COMPONENT_KIT_V11_20260718",
            "rejected_owner_detail_vocabulary": "REJECTED_OWNER_DETAIL_VOCABULARY_V11_20260718",
        }
        expected_v11_reports = {
            "machine_full_source_bundle_pass_pending_owner_review": "PASS_DETAIL_COMPONENT_KIT_GATE",
            "approved_owner_full_source_bundle": "PASS_DETAIL_COMPONENT_KIT_GATE",
            "rejected_machine_detail_component_kit": "FAIL_DETAIL_COMPONENT_KIT_GATE",
            "rejected_owner_detail_vocabulary": "PASS_DETAIL_COMPONENT_KIT_GATE",
        }
        v11_status = v11_record.get("status")
        add(errors, v11_record.get("kind") == "extension_candidate" and
            v11_record.get("render_parent_iteration") == locked_id and
            v11_record.get("eligible_as_visual_reference") is False and
            v11_record.get("eligible_for_component_export") is
            (v11_status == "approved_owner_full_source_bundle") and
            v11_status in allowed_v11_states,
            "V11 secondary detail kit has invalid lineage state or eligibility")
        v11_request_path_value = v11_record.get("generation_request")
        add(errors, is_repo_relative(v11_request_path_value), "V11 generation request path escapes repository")
        if is_repo_relative(v11_request_path_value):
            v11_request_path = ROOT / str(v11_request_path_value)
            add(errors, v11_request_path.is_file(), "missing V11 generation request")
            if v11_request_path.is_file():
                v11_request = load_json(v11_request_path)
                expected_request_status = allowed_v11_states.get(v11_status)
                add(errors, v11_request.get("iteration_id") == V11_ID and
                    v11_request.get("status") == expected_request_status and
                    v11_request.get("source_art_type") == "detail_component_kit",
                    "V11 request identifier, status, or source type drifted")
                validate_extension_request(
                    v11_request,
                    errors,
                    V11_ID,
                    require_generated_output=True,
                    preflight=False,
                    strict_eye_language=True,
                )
                output = v11_request.get("generated_output")
                if isinstance(output, dict):
                    add(errors, output.get("status") == v11_status and
                        v11_record.get("output") == output.get("path") and
                        str(v11_record.get("output_sha256", "")).upper() == str(output.get("sha256", "")).upper(),
                        "V11 output and lineage status drifted")
                    detail_report_value = output.get("detail_component_kit_report")
                    expected_detail_status = expected_v11_reports.get(v11_status)
                    add(errors, is_repo_relative(detail_report_value) and (ROOT / str(detail_report_value)).is_file(),
                        "missing V11 detail-component report")
                    if is_repo_relative(detail_report_value) and (ROOT / str(detail_report_value)).is_file():
                        detail_report = load_json(ROOT / str(detail_report_value))
                        add(errors, detail_report.get("status") == expected_detail_status and
                            detail_report.get("candidate_sha256") == output.get("sha256"),
                            "V11 detail-component evidence disagrees with its lineage state")
                    if v11_status == "machine_full_source_bundle_pass_pending_owner_review":
                        manifest_value = output.get("full_source_bundle_manifest")
                        bundle_report_value = output.get("full_source_bundle_machine_report")
                        add(errors, is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file(),
                            "missing V11 full source-bundle manifest")
                        add(errors, is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file(),
                            "missing V11 full source-bundle report")
                        if is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file():
                            manifest = load_json(ROOT / str(manifest_value))
                            add(errors, manifest.get("status") ==
                                "MACHINE_FULL_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW" and
                                manifest.get("machine_report") == bundle_report_value,
                                "V11 full source-bundle manifest status drifted")
                        if is_repo_relative(bundle_report_value) and (ROOT / str(bundle_report_value)).is_file():
                            bundle_report = load_json(ROOT / str(bundle_report_value))
                            add(errors, bundle_report.get("status") == "PASS_FULL_EXPRESSION_SOURCE_BUNDLE_GATE",
                                "V11 full source-bundle report is not machine-passing")
                    if v11_status == "approved_owner_full_source_bundle":
                        review_value = output.get("owner_review_result")
                        manifest_value = output.get("full_source_bundle_manifest")
                        add(errors, is_repo_relative(review_value) and (ROOT / str(review_value)).is_file(),
                            "missing V11 owner-approval result")
                        if is_repo_relative(review_value) and (ROOT / str(review_value)).is_file():
                            review = load_json(ROOT / str(review_value))
                            add(errors, review.get("selected") == "通过",
                                "V11 owner-approval result is not a pass")
                        add(errors, is_repo_relative(manifest_value) and (ROOT / str(manifest_value)).is_file(),
                            "missing approved V11 full source-bundle manifest")

    return {
        "schema": "companion.v9_art_lineage_machine.v1",
        "status": "PASS_ART_LINEAGE" if not errors else "FAIL_ART_LINEAGE",
        "contract": rel(CONTRACT_PATH),
        "lineage": rel(LINEAGE_PATH),
        "locked_v9_sha256": LOCKED_V9_HASH,
        "protected_owner_acceptance_sha256": PROTECTED_ACCEPTANCE_HASH,
        "runtime_resource_activated": False,
        "eligible_extension_component_exports": [],
        "errors": errors,
    }


def verify_preflight(request_path: pathlib.Path) -> dict[str, Any]:
    errors: list[str] = []
    lineage = load_json(LINEAGE_PATH)
    request = load_json(request_path)
    validate_extension_request(
        request,
        errors,
        rel(request_path),
        require_generated_output=False,
        preflight=True,
        strict_eye_language=True,
    )
    iteration_id = request.get("iteration_id")
    records = {
        item.get("iteration_id"): item for item in lineage.get("iterations", [])
        if isinstance(item, dict)
    }
    record = records.get(iteration_id)
    add(errors, isinstance(record, dict) and record.get("kind") == "extension_candidate" and
        record.get("render_parent_iteration") == lineage.get("locked_parent_iteration") and
        record.get("status") == "prompt_versioned" and
        record.get("eligible_as_visual_reference") is False and
        record.get("eligible_for_component_export") is False,
        "preflight request is not a versioned, inactive candidate in the V9 lineage")
    if isinstance(record, dict):
        add(errors, record.get("generation_request") == rel(request_path) and "output" not in record and
            "output_sha256" not in record,
            "preflight lineage record already carries generated output")
    return {
        "schema": "companion.v9_art_lineage_preflight.v1",
        "status": "PASS_ART_LINEAGE_PREFLIGHT" if not errors else "FAIL_ART_LINEAGE_PREFLIGHT",
        "request": rel(request_path),
        "iteration_id": iteration_id,
        "locked_v9_sha256": LOCKED_V9_HASH,
        "runtime_resource_activated": False,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight-request", type=pathlib.Path,
        help="Verify a versioned future request before image generation.")
    group.add_argument("--repository", action="store_true", help="Verify the recorded V9 art lineage (default).")
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    args = parser.parse_args()
    try:
        result = verify_preflight(args.preflight_request.resolve()) if args.preflight_request else verify_repository()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not str(result["status"]).startswith("PASS_"):
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
