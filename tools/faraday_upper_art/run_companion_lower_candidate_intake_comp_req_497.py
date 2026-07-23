#!/usr/bin/env python3
"""Read-only, fail-closed lower candidate intake for COMP-REQ-497."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


UPPER_BASELINE_COMMIT = "c677deef3d94190e16a08fb83cf45d4bb7d820a5"
LOWER_BASELINE_COMMIT = "4ddf9709034d307b333510c27e3e0a45c7ed6d15"
LOWER_BASELINE_MR_SHA = (
    "8BD2C5F3F9CEFD4794DEC29C6C244A66C0A7F99D495E9A221465019C355FB04F"
)
UPPER_BASELINE_BINDINGS = {
    (
        "tools/faraday_upper_art/"
        "audit_companion_upper_lower_compatibility_comp_req_474.py"
    ): "4A8A23D8E72D5B04290E5788B9486F540E41722AFB40A1C7C5C795BED5A168D7",
    (
        "tools/faraday_upper_art/"
        "run_companion_joint_offline_gate_comp_req_479.py"
    ): "9FFE3A8E140791309C73CCF39A0BD0B63CC22387440E519F949BBCDBEB3C4948",
    (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "auditor-main-review-provenance.json"
    ): "86B97DAAEBD9DEEE76DDF2DBFCDAA61727E72127C6EE2D5F2B729C2243473BDD",
}
VALIDATION_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471"
)
SUCCESSOR_SCHEMA = "companion.comp-req-497.candidate-intake.v1"
REQUIRED_SOURCE_ROLES = {
    "main_dispatch",
    "gaze_controller",
    "hold_cancel_controller",
    "menu_controller",
    "visual_runtime",
}
REQUIRED_SIDE_EFFECT_KEYS = {
    "execute",
    "server",
    "browser",
    "prompt",
    "popup",
    "hardware",
    "write",
    "programmer",
    "serial",
    "flash",
    "production",
    "push",
}
FORBIDDEN_AGGREGATE_KEYS = {
    "aggregate_totals",
    "events_realizable",
    "faraday_pairs",
    "mapping_rows",
    "no_op_rows",
    "pairs_realizable",
    "semantic_noops_realizable",
}
FORBIDDEN_AGGREGATE_TOKENS = {"21/21", "59/59", "10/10"}
STALE_UPPER_ARTIFACT_HASHES = {
    "F6504C998C5127355DA63C28B8910D8126650D6319779A95C4DEC604B1779104",
    "E4C6302D1E6C3EFBC7E0E262F40C6C06D95269A700BE63AF1A990F21C5FC4C4A",
    "00C16B47870D6B6DFE4B8C60408AADBBFE4548015EFE788BD72625C2C25A2080",
}
DIRECT_EVENT_TOKENS = {
    "COMPANION_VISUAL_EVENT_POINTER_DRAG_CENTER",
    "COMPANION_VISUAL_EVENT_EARLY_UP_CANCEL_BLUR_OR_DRAG",
    "COMPANION_VISUAL_EVENT_SELECT_UI_ASSETS",
}
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
SHA_RE = re.compile(r"[0-9A-Fa-f]{64}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def normalize_rel(path: str) -> str:
    normalized = path.replace("\\", "/")
    candidate = Path(normalized)
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or normalized.startswith("/")
        or normalized == ""
    ):
        raise ValueError(f"invalid repository-relative path: {path}")
    return normalized


def parse_binding(value: str) -> dict[str, str]:
    if "=" not in value:
        raise ValueError("binding must be PATH=SHA256")
    path, digest = value.rsplit("=", 1)
    if SHA_RE.fullmatch(digest) is None:
        raise ValueError(f"invalid SHA-256 in binding: {value}")
    return {"path": normalize_rel(path), "sha256": digest.upper()}


class GitReader:
    def __init__(self, root: Path):
        self.root = root
        self.command_count = 0

    def run(self, *args: str, text: bool = False) -> bytes | str:
        self.command_count += 1
        completed = subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.decode("utf-8", errors="replace").strip()
            )
        if text:
            return completed.stdout.decode("utf-8").replace("\r\n", "\n")
        return completed.stdout

    def commit(self, value: str) -> str:
        return str(self.run("rev-parse", f"{value}^{{commit}}", text=True)).strip()

    def show(self, commit: str, path: str) -> bytes:
        return bytes(self.run("show", f"{commit}:{normalize_rel(path)}"))

    def head(self) -> str:
        return str(self.run("rev-parse", "HEAD", text=True)).strip()

    def tracked_status(self) -> str:
        return str(
            self.run(
                "status",
                "--porcelain=v1",
                "--untracked-files=no",
                "--ignore-submodules=all",
                text=True,
            )
        )

    def changed_paths(self, base: str, commit: str) -> list[str]:
        output = str(
            self.run(
                "diff",
                "--name-only",
                "--no-renames",
                f"{base}..{commit}",
                text=True,
            )
        )
        return sorted(line for line in output.splitlines() if line)


def collect_declared_identities(value: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    if isinstance(value, dict):
        path = value.get("path")
        digest = value.get("sha256")
        if isinstance(path, str) and isinstance(digest, str):
            try:
                result.add((normalize_rel(path), digest.upper()))
            except ValueError:
                pass
        for child in value.values():
            result.update(collect_declared_identities(child))
    elif isinstance(value, list):
        for child in value:
            result.update(collect_declared_identities(child))
    return result


def aggregate_claims(value: Any, pointer: str = "") -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_pointer = f"{pointer}/{key}"
            if key in FORBIDDEN_AGGREGATE_KEYS:
                claims.append(
                    {
                        "json_pointer": child_pointer,
                        "reason": "forbidden_aggregate_key",
                    }
                )
            claims.extend(aggregate_claims(child, child_pointer))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            claims.extend(aggregate_claims(child, f"{pointer}/{index}"))
    elif isinstance(value, str):
        for token in sorted(FORBIDDEN_AGGREGATE_TOKENS):
            if token in value:
                claims.append(
                    {
                        "json_pointer": pointer,
                        "reason": f"forbidden_aggregate_token:{token}",
                    }
                )
    return claims


def git_identity(
    git: GitReader,
    commit: str,
    binding: dict[str, str],
) -> dict[str, Any]:
    try:
        content = git.show(commit, binding["path"])
        observed = sha256(content)
        return {
            **binding,
            "observed_sha256": observed,
            "bytes": len(content),
            "match": observed == binding["sha256"],
        }
    except Exception as exc:
        return {
            **binding,
            "observed_sha256": None,
            "bytes": None,
            "match": False,
            "error": str(exc),
        }


def upper_baseline_identities(
    git: GitReader,
) -> list[dict[str, Any]]:
    return [
        git_identity(
            git,
            UPPER_BASELINE_COMMIT,
            {"path": path, "sha256": digest},
        )
        for path, digest in sorted(UPPER_BASELINE_BINDINGS.items())
    ]


def changed_fixture_injections(
    git: GitReader,
    base_commit: str,
    candidate_commit: str,
) -> list[dict[str, Any]]:
    rows = []
    for path in git.changed_paths(base_commit, candidate_commit):
        normalized = path.replace("\\", "/")
        if not normalized.startswith(("tools/", "tests/")):
            continue
        if Path(normalized).suffix.lower() not in {
            ".c",
            ".cc",
            ".cpp",
            ".h",
            ".py",
            ".ps1",
        }:
            continue
        try:
            source = git.show(candidate_commit, normalized).decode(
                "utf-8", errors="replace"
            )
        except Exception:
            continue
        events = sorted(token for token in DIRECT_EVENT_TOKENS if token in source)
        direct_call = "companion_visual_runtime_enqueue_visual_event" in source
        if direct_call and events:
            rows.append(
                {
                    "path": normalized,
                    "direct_call": (
                        "companion_visual_runtime_enqueue_visual_event"
                    ),
                    "event_tokens": events,
                    "sha256": sha256(source.encode("utf-8")),
                }
            )
    return rows


def simplify_event_records(
    compatibility: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not compatibility:
        return []
    return sorted(
        [
            {
                "event": row.get("event"),
                "from_states": row.get("from_states"),
                "to_states": row.get("to_states"),
                "mapping_status": row.get("mapping_status"),
                "realizable_lower_path": row.get("realizable_lower_path"),
            }
            for row in compatibility.get("event_compatibility", [])
        ],
        key=lambda row: str(row["event"]),
    )


def simplify_pair_records(
    compatibility: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not compatibility:
        return []
    return sorted(
        [
            {
                "id": row.get("id"),
                "event": row.get("event"),
                "from_state": row.get("from_state"),
                "to_state": row.get("to_state"),
                "pixel_noop": row.get("pixel_noop"),
                "realizable_lower_path": row.get("realizable_lower_path"),
            }
            for row in compatibility.get("pair_compatibility", [])
        ],
        key=lambda row: str(row["id"]),
    )


def simplify_noop_records(
    pair_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "event": row["event"],
            "from_state": row["from_state"],
            "to_state": row["to_state"],
            "realizable_lower_path": row["realizable_lower_path"],
        }
        for row in pair_records
        if row["pixel_noop"] is True
    ]


def normalize_supplied_records(
    value: Any,
    fields: tuple[str, ...],
    sort_key: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return []
        rows.append({field: item.get(field) for field in fields})
    return sorted(rows, key=lambda row: str(row.get(sort_key)))


def successor_gate_checks(observations: dict[str, Any]) -> dict[str, bool]:
    required = (
        "upper_baseline_exact",
        "lower_commit_exact",
        "successor_not_baseline",
        "successor_mr_not_baseline",
        "successor_has_no_stale_upper_hash",
        "lower_head_exact",
        "lower_worktree_clean",
        "mr_hash_exact",
        "mr_source_commit_exact",
        "mr_schema_exact",
        "runner_identity_exact",
        "supervisor_identity_exact",
        "tool_identities_exact",
        "tool_identities_declared",
        "source_roles_complete",
        "source_blobs_exact",
        "production_source_changed",
        "direct_fixture_injection_absent",
        "aggregate_claims_absent",
        "event_records_exact",
        "pair_records_exact",
        "noop_records_exact",
        "compatibility_commit_exact",
        "compatibility_status_pass",
        "compatibility_events_21",
        "compatibility_pairs_59",
        "compatibility_noops_10",
        "compatibility_polarity_terminal_qualification",
        "compatibility_side_effects_zero",
        "mr_side_effects_zero",
    )
    return {
        name: observations.get(name) is True
        for name in required
    }


def side_effects_zero(value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and set(value) >= REQUIRED_SIDE_EFFECT_KEYS
        and all(value.get(key) == 0 for key in REQUIRED_SIDE_EFFECT_KEYS)
    )


def run_compatibility(
    repo_root: Path,
    auditor: Path,
    lower_root: Path,
    expected_commit: str,
    output: Path,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-B",
        str(auditor),
        "--repo-root",
        str(repo_root),
        "--lower-root",
        str(lower_root),
        "--expected-commit",
        expected_commit,
        "--output",
        str(output),
        "--comparison-mode",
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    artifact = load_json(output) if output.is_file() else None
    return {
        "command": command,
        "return_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "artifact": artifact,
        "artifact_sha256": file_sha(output) if output.is_file() else None,
        "consistent": bool(
            artifact
            and (
                (
                    completed.returncode == 0
                    and artifact.get("status")
                    == "PASS_UPPER_LOWER_COMPATIBLE"
                )
                or (
                    completed.returncode == 1
                    and str(artifact.get("status", "")).startswith("NO_GO")
                )
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("baseline-no-go", "successor"),
        required=True,
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--lower-root", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--lower-machine-ready", type=Path, required=True)
    parser.add_argument(
        "--expected-lower-machine-ready-sha256",
        required=True,
    )
    parser.add_argument("--runner-binding", required=True)
    parser.add_argument("--supervisor-binding", required=True)
    parser.add_argument(
        "--tool-binding",
        action="append",
        default=[],
        required=True,
    )
    parser.add_argument("--compatibility-auditor", type=Path, required=True)
    parser.add_argument(
        "--expected-compatibility-auditor-sha256",
        required=True,
    )
    parser.add_argument("--compatibility-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    lower_root = args.lower_root.resolve()
    mr_path = args.lower_machine_ready.resolve()
    auditor = (
        args.compatibility_auditor.resolve()
        if args.compatibility_auditor.is_absolute()
        else (repo_root / args.compatibility_auditor).resolve()
    )
    compatibility_output = (
        args.compatibility_output.resolve()
        if args.compatibility_output.is_absolute()
        else (repo_root / args.compatibility_output).resolve()
    )
    output_path = (
        args.output.resolve()
        if args.output.is_absolute()
        else (repo_root / args.output).resolve()
    )
    validation_root = (repo_root / VALIDATION_REL).resolve()
    compatibility_output.relative_to(validation_root)
    output_path.relative_to(validation_root)

    if COMMIT_RE.fullmatch(args.expected_commit) is None:
        raise SystemExit("expected commit must be exact lowercase 40-hex")
    if (
        SHA_RE.fullmatch(args.expected_lower_machine_ready_sha256)
        is None
    ):
        raise SystemExit("lower MACHINE_READY SHA must be exact 64-hex")
    runner_binding = parse_binding(args.runner_binding)
    supervisor_binding = parse_binding(args.supervisor_binding)
    tool_bindings = [parse_binding(value) for value in args.tool_binding]
    if not tool_bindings:
        raise SystemExit("at least one exact lower tool binding is required")

    upper_git = GitReader(repo_root)
    lower_git = GitReader(lower_root)
    errors: list[str] = []
    checks: dict[str, bool] = {}
    observations: dict[str, Any] = {}

    upper_identities = upper_baseline_identities(upper_git)
    checks["upper_baseline_exact"] = bool(
        upper_git.commit(UPPER_BASELINE_COMMIT) == UPPER_BASELINE_COMMIT
        and all(row["match"] for row in upper_identities)
    )

    try:
        resolved_commit = lower_git.commit(args.expected_commit)
    except Exception as exc:
        resolved_commit = None
        errors.append(f"lower_commit:{exc}")
    checks["lower_commit_exact"] = resolved_commit == args.expected_commit

    observed_mr_sha = file_sha(mr_path) if mr_path.is_file() else None
    checks["mr_hash_exact"] = bool(
        observed_mr_sha
        == args.expected_lower_machine_ready_sha256.upper()
    )
    try:
        mr = load_json(mr_path) if mr_path.is_file() else None
    except Exception as exc:
        mr = None
        errors.append(f"lower_mr:{exc}")

    all_bindings = [runner_binding, supervisor_binding, *tool_bindings]
    tool_identity_rows = (
        [
            git_identity(lower_git, args.expected_commit, binding)
            for binding in all_bindings
        ]
        if resolved_commit
        else []
    )
    checks["runner_identity_exact"] = bool(
        tool_identity_rows and tool_identity_rows[0]["match"]
    )
    checks["supervisor_identity_exact"] = bool(
        len(tool_identity_rows) > 1 and tool_identity_rows[1]["match"]
    )
    checks["tool_identities_exact"] = bool(
        len(tool_identity_rows) == len(all_bindings)
        and all(row["match"] for row in tool_identity_rows[2:])
    )

    declared_identities = collect_declared_identities(mr)
    checks["tool_identities_declared"] = all(
        (binding["path"], binding["sha256"]) in declared_identities
        for binding in all_bindings
    )
    checks["baseline_runner_supervisor_declared"] = all(
        (binding["path"], binding["sha256"]) in declared_identities
        for binding in (runner_binding, supervisor_binding)
    )

    compatibility_result = (
        run_compatibility(
            repo_root,
            auditor,
            lower_root,
            args.expected_commit,
            compatibility_output,
        )
        if (
            resolved_commit
            and auditor.is_file()
            and file_sha(auditor)
            == args.expected_compatibility_auditor_sha256.upper()
        )
        else {
            "command": [],
            "return_code": None,
            "stdout": "",
            "stderr": "auditor identity or lower commit unavailable",
            "artifact": None,
            "artifact_sha256": None,
            "consistent": False,
        }
    )
    compatibility = compatibility_result["artifact"]
    summary = compatibility.get("summary", {}) if compatibility else {}
    event_records = simplify_event_records(compatibility)
    pair_records = simplify_pair_records(compatibility)
    noop_records = simplify_noop_records(pair_records)

    compatibility_side = (
        compatibility.get("side_effect_counters", {})
        if compatibility
        else {}
    )
    compatibility_external_keys = {
        "operator_execute",
        "server_probe",
        "server_start",
        "browser_start",
        "popup",
        "operator_prompt",
        "hardware",
        "lower_write",
        "platform_write",
        "production_write",
    }
    checks["compatibility_commit_exact"] = bool(
        compatibility
        and compatibility.get("lower_binding", {}).get("resolved_commit")
        == args.expected_commit
        and compatibility_result["consistent"]
    )
    checks["compatibility_status_pass"] = bool(
        compatibility
        and compatibility.get("status") == "PASS_UPPER_LOWER_COMPATIBLE"
    )
    checks["compatibility_events_21"] = bool(
        summary.get("events", {}).get("realizable") == 21
        and len(event_records) == 21
    )
    checks["compatibility_pairs_59"] = bool(
        summary.get("pairs", {}).get("realizable") == 59
        and len(pair_records) == 59
    )
    checks["compatibility_noops_10"] = bool(
        summary.get("pairs", {}).get("semantic_noop_realizable") == 10
        and len(noop_records) == 10
    )
    checks["compatibility_polarity_terminal_qualification"] = bool(
        summary.get("polarity_bridge_realizable") is True
        and summary.get("terminal_retention") is True
        and summary.get("qualification_valid") is True
    )
    checks["compatibility_side_effects_zero"] = bool(
        all(compatibility_side.get(key) == 0 for key in compatibility_external_keys)
    )

    candidate_block = (
        mr.get("candidate_intake")
        if isinstance(mr, dict)
        and isinstance(mr.get("candidate_intake"), dict)
        else None
    )
    source_rows: list[dict[str, Any]] = []
    injection_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, str]] = aggregate_claims(mr)

    if args.mode == "baseline-no-go":
        gate_checks = {
            "upper_baseline_exact": checks["upper_baseline_exact"],
            "lower_commit_exact": checks["lower_commit_exact"],
            "mr_hash_exact": checks["mr_hash_exact"],
            "runner_identity_exact": checks["runner_identity_exact"],
            "supervisor_identity_exact": checks[
                "supervisor_identity_exact"
            ],
            "tool_identities_exact": checks["tool_identities_exact"],
            "compatibility_commit_exact": checks[
                "compatibility_commit_exact"
            ],
            "baseline_commit_and_mr_exact": bool(
                args.expected_commit == LOWER_BASELINE_COMMIT
                and observed_mr_sha == LOWER_BASELINE_MR_SHA
            ),
            "baseline_no_go_counts_exact": bool(
                compatibility
                and compatibility.get("status")
                == "NO_GO_UPPER_LOWER_EVENT_PATH_GAPS"
                and summary.get("events", {}).get("realizable") == 17
                and summary.get("pairs", {}).get("realizable") == 51
                and summary.get("pairs", {}).get(
                    "semantic_noop_realizable"
                )
                == 8
                and summary.get("polarity_bridge_realizable") is True
            ),
            "compatibility_side_effects_zero": checks[
                "compatibility_side_effects_zero"
            ],
            "baseline_mr_tool_claims_not_promoted": bool(
                not checks["baseline_runner_supervisor_declared"]
                and checks["runner_identity_exact"]
                and checks["supervisor_identity_exact"]
            ),
        }
        baseline_pass = all(gate_checks.values())
        status = (
            "BASELINE_NO_GO_VERIFIED" if baseline_pass else "NO_GO"
        )
        failed_checks = sorted(
            name for name, passed in gate_checks.items() if not passed
        )
        ready = baseline_pass
    else:
        checks["successor_not_baseline"] = (
            args.expected_commit != LOWER_BASELINE_COMMIT
        )
        checks["successor_mr_not_baseline"] = (
            observed_mr_sha != LOWER_BASELINE_MR_SHA
        )
        serialized_mr = canonical_bytes(mr) if mr is not None else b""
        checks["successor_has_no_stale_upper_hash"] = not any(
            digest.encode("ascii") in serialized_mr
            for digest in STALE_UPPER_ARTIFACT_HASHES
        )
        try:
            lower_head = lower_git.head()
            lower_status = lower_git.tracked_status()
        except Exception as exc:
            lower_head = None
            lower_status = None
            errors.append(f"lower_worktree:{exc}")
        checks["lower_head_exact"] = lower_head == args.expected_commit
        checks["lower_worktree_clean"] = lower_status == ""
        checks["mr_schema_exact"] = bool(
            candidate_block
            and candidate_block.get("schema") == SUCCESSOR_SCHEMA
        )
        checks["mr_source_commit_exact"] = bool(
            candidate_block
            and candidate_block.get("base_commit") == LOWER_BASELINE_COMMIT
            and candidate_block.get("source_commit")
            == args.expected_commit
        )

        production_sources = (
            candidate_block.get("production_sources", [])
            if candidate_block
            else []
        )
        if not isinstance(production_sources, list):
            production_sources = []
        valid_source_rows = [
            row
            for row in production_sources
            if isinstance(row, dict)
            and isinstance(row.get("role"), str)
            and isinstance(row.get("path"), str)
            and isinstance(row.get("sha256"), str)
        ]
        role_rows = {
            row.get("role"): row
            for row in valid_source_rows
        }
        checks["source_roles_complete"] = bool(
            len(production_sources) == len(REQUIRED_SOURCE_ROLES)
            and len(valid_source_rows) == len(REQUIRED_SOURCE_ROLES)
            and len(role_rows) == len(REQUIRED_SOURCE_ROLES)
            and set(role_rows) == REQUIRED_SOURCE_ROLES
            and role_rows["main_dispatch"]["path"].replace("\\", "/").endswith(
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
            )
            and all(
                not row["path"].replace("\\", "/").startswith(
                    ("tools/", "tests/")
                )
                for row in role_rows.values()
            )
        )
        if resolved_commit:
            for role in sorted(role_rows):
                row = role_rows[role]
                try:
                    binding = {
                        "path": normalize_rel(row["path"]),
                        "sha256": str(row["sha256"]).upper(),
                    }
                    source_rows.append(
                        {"role": role, **git_identity(
                            lower_git, args.expected_commit, binding
                        )}
                    )
                except Exception as exc:
                    source_rows.append(
                        {
                            "role": role,
                            "path": row.get("path"),
                            "sha256": row.get("sha256"),
                            "match": False,
                            "error": str(exc),
                        }
                    )
        checks["source_blobs_exact"] = bool(
            len(source_rows) == len(REQUIRED_SOURCE_ROLES)
            and all(row["match"] for row in source_rows)
        )
        try:
            changed_paths = lower_git.changed_paths(
                LOWER_BASELINE_COMMIT, args.expected_commit
            )
            injection_rows = changed_fixture_injections(
                lower_git, LOWER_BASELINE_COMMIT, args.expected_commit
            )
        except Exception as exc:
            changed_paths = []
            errors.append(f"lower_diff:{exc}")
        checks["production_source_changed"] = bool(
            {
                row.get("path", "").replace("\\", "/")
                for row in role_rows.values()
            }
            & set(changed_paths)
        )
        checks["direct_fixture_injection_absent"] = not injection_rows
        checks["aggregate_claims_absent"] = not aggregate_rows

        records = (
            candidate_block.get("records", {})
            if candidate_block
            and isinstance(candidate_block.get("records"), dict)
            else {}
        )
        supplied_events = normalize_supplied_records(
            records.get("event_records"),
            (
                "event",
                "from_states",
                "to_states",
                "mapping_status",
                "realizable_lower_path",
            ),
            "event",
        )
        supplied_pairs = normalize_supplied_records(
            records.get("pair_records"),
            (
                "id",
                "event",
                "from_state",
                "to_state",
                "pixel_noop",
                "realizable_lower_path",
            ),
            "id",
        )
        supplied_noops = normalize_supplied_records(
            records.get("semantic_noop_records"),
            (
                "id",
                "event",
                "from_state",
                "to_state",
                "realizable_lower_path",
            ),
            "id",
        )
        checks["event_records_exact"] = supplied_events == event_records
        checks["pair_records_exact"] = supplied_pairs == pair_records
        checks["noop_records_exact"] = supplied_noops == noop_records

        candidate_tools = (
            candidate_block.get("tool_identities", [])
            if candidate_block
            else []
        )
        candidate_tool_set: set[tuple[str, str]] = set()
        candidate_tool_rows_valid = isinstance(candidate_tools, list)
        if candidate_tool_rows_valid:
            for row in candidate_tools:
                if (
                    not isinstance(row, dict)
                    or not isinstance(row.get("path"), str)
                    or not isinstance(row.get("sha256"), str)
                    or not row.get("path")
                    or SHA_RE.fullmatch(row["sha256"]) is None
                ):
                    candidate_tool_rows_valid = False
                    continue
                try:
                    candidate_tool_set.add(
                        (
                            normalize_rel(row["path"]),
                            row["sha256"].upper(),
                        )
                    )
                except ValueError:
                    candidate_tool_rows_valid = False
        checks["tool_identities_declared"] = all(
            (binding["path"], binding["sha256"]) in candidate_tool_set
            for binding in all_bindings
        ) and candidate_tool_rows_valid
        checks["mr_side_effects_zero"] = bool(
            candidate_block
            and side_effects_zero(candidate_block.get("side_effect_counters"))
        )

        gate_checks = successor_gate_checks(checks)
        failed_checks = sorted(
            name for name, passed in gate_checks.items() if not passed
        )
        ready = not failed_checks and not errors
        status = "SUCCESSOR_INTAKE_READY" if ready else "NO_GO"

    artifact = {
        "schema": "companion.comp-req-497.lower-candidate-intake-result.v1",
        "requirements": ["COMP-REQ-494", "COMP-REQ-497"],
        "status": status,
        "mode": args.mode,
        "default_off": True,
        "upper_baseline": {
            "commit": UPPER_BASELINE_COMMIT,
            "identities": upper_identities,
        },
        "lower_binding": {
            "root": lower_root.as_posix(),
            "expected_commit": args.expected_commit,
            "resolved_commit": resolved_commit,
            "machine_ready_path": mr_path.as_posix(),
            "expected_machine_ready_sha256": (
                args.expected_lower_machine_ready_sha256.upper()
            ),
            "observed_machine_ready_sha256": observed_mr_sha,
            "tool_identities": tool_identity_rows,
            "production_source_identities": source_rows,
        },
        "checks": gate_checks,
        "observations": {
            "errors": errors,
            "aggregate_claims": aggregate_rows,
            "direct_fixture_injections": injection_rows,
            "event_record_count": len(event_records),
            "pair_record_count": len(pair_records),
            "semantic_noop_record_count": len(noop_records),
            "compatibility_status": (
                compatibility.get("status") if compatibility else None
            ),
            "compatibility_summary": summary,
        },
        "compatibility": {
            "path": compatibility_output.relative_to(repo_root).as_posix(),
            "sha256": compatibility_result["artifact_sha256"],
            "process_return_code": compatibility_result["return_code"],
            "process_consistent": compatibility_result["consistent"],
            "process_stdout": compatibility_result["stdout"],
            "process_stderr": compatibility_result["stderr"],
        },
        "failed_checks": failed_checks,
        "successor_contract": {
            "schema": SUCCESSOR_SCHEMA,
            "required_source_roles": sorted(REQUIRED_SOURCE_ROLES),
            "aggregate_claims_forbidden": True,
            "direct_changed_fixture_event_injection_forbidden": True,
            "records_are_recomputed_from_corrected_auditor": True,
            "successor_pass_not_inferred_from_lower_status_or_totals": True,
        },
        "side_effect_counters": {
            "execute": 0,
            "server": 0,
            "browser": 0,
            "prompt": 0,
            "popup": 0,
            "hardware": 0,
            "lower_write": 0,
            "registry_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "push": 0,
            "read_only_git_processes": (
                upper_git.command_count + lower_git.command_count
            ),
            "read_only_auditor_processes": (
                1 if compatibility_result["command"] else 0
            ),
            "upper_artifact_writes": (
                2 if compatibility_result["artifact"] else 1
            ),
        },
        "generator": {
            "path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "sha256": file_sha(Path(__file__).resolve()),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(artifact))
    print(
        json.dumps(
            {
                "status": status,
                "mode": args.mode,
                "failed_check_count": len(failed_checks),
                "artifact_sha256": file_sha(output_path),
            },
            sort_keys=True,
        )
    )
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
