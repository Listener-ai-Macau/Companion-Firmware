from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = Path(
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
ORACLE = Path(
    "tools/faraday_upper_art/"
    "verify_companion_browser_recording_temporal_comp_req_518.mjs"
)
VALIDATION = Path(
    "docs/validation/"
    "companion-browser-recording-successor-comp-req-518"
)
PREDECESSOR_COMMIT = "6e6e521fddcdb9a99af0608fa86714df199e6c9c"
PREDECESSOR_PAGE_SHA = (
    "9990C4316AF8F4D656F2C2B057AB789846A10CD21E18367336FC6BD277631EB7"
)
OWNER_BINDINGS = {
    "owner-review.json": (
        "912890518A8C758B915F3DD674372FEBB642EF89996DACF9B1E06A587C519979"
    ),
    "owner-review.raw.json": (
        "50C3563002CF4E81E84EA2344AEE1919D29A4F3854E663966451D602E6CF2DB3"
    ),
    "owner-review.note.txt": (
        "7EB70257593DA06F682A3DDDA54A9D260D4FC514F645237F5CA74B08F8DA61A6"
    ),
}
PROTECTED_LINES = (
    "const touchContract=",
    "function enterIntegratedMenu(",
    "function menuSelect(",
    "function touchCommitPendingSingle(",
    "function touchArmRelease(",
    "function touchConsumeValidPair(",
    "function touchCancel(",
    "function touchPointerDown(",
    "function touchPointerMove(",
    "function touchPointerUp(",
    "function touchPointerCancel(",
)


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def git_text(*args: str) -> str:
    return git(*args).decode("utf-8")


def commit_bytes(commit: str, path: Path) -> bytes:
    return git("show", f"{commit}:{path.as_posix()}")


def selected_lines(source: str) -> dict[str, str]:
    lines = source.splitlines()
    selected: dict[str, str] = {}
    for prefix in PROTECTED_LINES:
        matches = [line for line in lines if line.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f"{prefix}: expected one line, found {len(matches)}")
        selected[prefix] = matches[0]
    return selected


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("ascii")


def checkout_identity(commit_value: bytes, worktree_value: bytes) -> dict:
    variants = {
        "commit_bytes": commit_value,
        "crlf_checkout": commit_value.replace(b"\r\n", b"\n").replace(
            b"\n", b"\r\n"
        ),
    }
    matches = [
        name for name, candidate in variants.items() if candidate == worktree_value
    ]
    return {
        "commit_sha256": sha_bytes(commit_value),
        "matches": matches,
        "worktree_sha256": sha_bytes(worktree_value),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_commit = git_text("rev-parse", args.source_commit).strip()
    if source_commit != args.source_commit:
        raise SystemExit("source commit must be an exact 40-hex identity")
    predecessor_page = commit_bytes(PREDECESSOR_COMMIT, PAGE)
    source_page = commit_bytes(source_commit, PAGE)
    source_oracle = commit_bytes(source_commit, ORACLE)
    worktree_page = ROOT / PAGE
    worktree_oracle = ROOT / ORACLE
    page_checkout = checkout_identity(source_page, worktree_page.read_bytes())
    oracle_checkout = checkout_identity(
        source_oracle, worktree_oracle.read_bytes()
    )
    page_commit_blob = git_text("rev-parse", f"{source_commit}:{PAGE.as_posix()}").strip()
    page_worktree_clean_blob = git_text(
        "hash-object", "--path", PAGE.as_posix(), PAGE.as_posix()
    ).strip()
    oracle_commit_blob = git_text(
        "rev-parse", f"{source_commit}:{ORACLE.as_posix()}"
    ).strip()
    oracle_worktree_clean_blob = git_text(
        "hash-object", "--path", ORACLE.as_posix(), ORACLE.as_posix()
    ).strip()
    before_path = ROOT / VALIDATION / "before-fix/recording-temporal-oracle.json"
    after_path = ROOT / VALIDATION / "after-fix/recording-temporal-oracle.json"
    before = load_json(before_path)
    after = load_json(after_path)
    owner_root = (
        ROOT
        / "docs/validation/"
        "companion-browser-owner-review-ready-comp-req-508"
    )

    predecessor_lines = selected_lines(predecessor_page.decode("utf-8"))
    source_lines = selected_lines(source_page.decode("utf-8"))
    protected_line_checks = {
        prefix: {
            "equal": source_lines[prefix] == predecessor_lines[prefix],
            "sha256": sha_bytes(source_lines[prefix].encode("utf-8")),
        }
        for prefix in PROTECTED_LINES
    }
    checks = {
        "after_oracle_pass": (
            after.get("status") == "PASS"
            and all(after.get("checks", {}).values())
        ),
        "before_oracle_fails_required_defects": (
            before.get("status") == "FAIL_RECORDING_TEMPORAL_VISUAL"
            and before.get("observed_page_sha256") == PREDECESSOR_PAGE_SHA
            and before["checks"]["no_outward_transition_including_wrap"] is False
            and before["checks"]["one_indicator_only_during_recording"] is False
            and before["checks"]["one_stable_listening_face_and_gaze"] is False
            and before["checks"]["stable_listening_phase_contract"] is False
        ),
        "owner_failure_bindings_exact": all(
            (owner_root / name).is_file()
            and sha_file(owner_root / name) == expected
            for name, expected in OWNER_BINDINGS.items()
        ),
        "page_changed_from_failed_predecessor": (
            sha_bytes(source_page) != PREDECESSOR_PAGE_SHA
        ),
        "protected_gesture_menu_tap_lines_unchanged": all(
            row["equal"] for row in protected_line_checks.values()
        ),
        "source_commit_exact": (
            len(source_commit) == 40
            and git_text("cat-file", "-t", source_commit).strip() == "commit"
        ),
        "worktree_matches_source_commit": (
            page_worktree_clean_blob == page_commit_blob
            and oracle_worktree_clean_blob == oracle_commit_blob
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    artifact = {
        "bindings": {
            "after_oracle": {
                "path": after_path.relative_to(ROOT).as_posix(),
                "sha256": sha_file(after_path),
            },
            "before_oracle": {
                "path": before_path.relative_to(ROOT).as_posix(),
                "sha256": sha_file(before_path),
            },
            "owner_failure": {
                name: {
                    "path": (owner_root / name).relative_to(ROOT).as_posix(),
                    "sha256": sha_file(owner_root / name),
                }
                for name in OWNER_BINDINGS
            },
            "page": {
                "checkout_identity": page_checkout,
                "commit_blob": page_commit_blob,
                "commit_sha256": sha_bytes(source_page),
                "git_clean_worktree_blob": page_worktree_clean_blob,
                "path": PAGE.as_posix(),
                "worktree_sha256": sha_file(worktree_page),
            },
            "temporal_oracle": {
                "checkout_identity": oracle_checkout,
                "commit_blob": oracle_commit_blob,
                "commit_sha256": sha_bytes(source_oracle),
                "git_clean_worktree_blob": oracle_worktree_clean_blob,
                "path": ORACLE.as_posix(),
                "worktree_sha256": sha_file(worktree_oracle),
            },
        },
        "checks": checks,
        "failed_checks": failures,
        "owner_boundary": {
            "combined_successor_claimed": False,
            "owner_pass_claimed": False,
            "owner_prompt_invoked": False,
            "remaining_work": "COMP-REQ-521 implementation and combined replay",
        },
        "predecessor": {
            "commit": PREDECESSOR_COMMIT,
            "page_sha256": sha_bytes(predecessor_page),
        },
        "protected_line_checks": protected_line_checks,
        "requirements": ["COMP-REQ-518", "COMP-REQ-520"],
        "schema": "companion.browser-recording-source-bound-intermediate.v1",
        "side_effect_counters": {
            "browser": 0,
            "hardware": 0,
            "owner_prompt": 0,
            "production_write": 0,
            "server_start": 0,
        },
        "source_commit": source_commit,
        "status": (
            "PASS_SOURCE_BOUND_RECORDING_INTERMEDIATE"
            if not failures
            else "NO_GO"
        ),
    }
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT):
        raise SystemExit("output must remain inside repository")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(artifact))
    print(
        json.dumps(
            {
                "failed_checks": failures,
                "output_sha256": sha_file(output),
                "status": artifact["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
