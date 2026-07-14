#!/usr/bin/env python3
"""Read the active external CEMP candidate for WB55 runtime evidence tools."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MENU_EVIDENCE = ROOT / "docs" / "validation" / "companion-screen-bilingual-menu-wb55.json"


@dataclass(frozen=True)
class ScreenRuntimeCandidate:
    revision: int
    total_bytes: int
    pack_crc32: str
    runtime_status: str
    clips: int
    frames: int

    @property
    def pending_status(self) -> str:
        return f"REVISION_{self.revision}_RUNTIME_RECHECK_PENDING"

    @property
    def pass_status(self) -> str:
        return f"REVISION_{self.revision}_RUNTIME_PASS_HUMAN_VISUAL_PENDING"

    @property
    def run_root(self) -> Path:
        return ROOT / ".cache" / "validation" / f"rev{self.revision}-runtime-current"

    @property
    def recovery_root(self) -> Path:
        return ROOT / ".cache" / "validation" / f"rev{self.revision}-runtime-recovery-selftest"

    @property
    def common_markers(self) -> tuple[str, ...]:
        return (
            "mount=ok",
            f"revision={self.revision}",
            f"clips={self.clips} frames={self.frames}",
            "expression_renderer=external_pack",
            "source=external_flash",
            "pet_behavior_selftest=pass failure_code=0",
            "touch-health] detected=1 identity=1 addr=0x38",
            f"queue_generation revision={self.revision}",
            "coherent_generation=1",
            "generation_switches=",
            "last_stale_discarded=",
            "refresh mode=full",
            "complete=1",
        )


def _resolve_evidence_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def _display_evidence_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def evaluate_runtime_evidence_durability(
    candidate: ScreenRuntimeCandidate,
    runtime: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Verify the raw artifacts behind a promoted WB55 runtime summary."""
    failures: list[str] = []
    checked_paths: dict[str, str] = {}
    status = str(runtime.get("status", ""))
    if status != candidate.pass_status:
        failures.append(f"runtime_status_not_promoted:{status or 'missing'}")

    raw_logs: list[str] = []
    summary_keys = ("provision_capture_summary", "normal_capture_summary")
    raw_keys = ("provision_raw_log", "normal_raw_log")
    for key in (*summary_keys, *raw_keys):
        path = _resolve_evidence_path(root, runtime.get(key))
        if path is None:
            failures.append(f"missing_path_field:{key}")
            continue
        checked_paths[key] = _display_evidence_path(root, path)
        if not path.is_file():
            failures.append(f"missing_file:{key}")
            continue
        if key in summary_keys:
            try:
                summary = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                failures.append(f"invalid_summary:{key}")
                continue
            if summary.get("status") != "PASS":
                failures.append(f"summary_not_pass:{key}")
        else:
            try:
                raw_logs.append(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                failures.append(f"unreadable_log:{key}")

    combined_logs = "\n".join(raw_logs)
    missing_markers = [
        marker
        for marker in runtime.get("required_runtime_markers", [])
        if not isinstance(marker, str) or marker not in combined_logs
    ]
    failures.extend(f"missing_marker:{marker}" for marker in missing_markers)

    run_report_path = root / ".cache" / "validation" / (
        f"rev{candidate.revision}-runtime-current"
    ) / "runtime-recheck-run.json"
    checked_paths["run_report"] = _display_evidence_path(root, run_report_path)
    if not run_report_path.is_file():
        failures.append("missing_file:run_report")
    else:
        try:
            run_report = json.loads(run_report_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            failures.append("invalid_run_report")
        else:
            if run_report.get("status") != "PASS":
                failures.append("run_report_not_pass")
            if run_report.get("normal_firmware_restored") is not True:
                failures.append("normal_firmware_not_restored")
            result_status = {
                str(item.get("id")): str(item.get("status"))
                for item in run_report.get("results", [])
                if isinstance(item, dict)
            }
            for step_id in (
                "flash_provision",
                "capture_provision",
                "flash_normal",
                "capture_normal",
            ):
                if result_status.get(step_id) != "PASS":
                    failures.append(f"run_step_not_pass:{step_id}")

    return {
        "schema_id": "companion.screen.runtime_evidence_durability.v1",
        "status": "PASS" if not failures else "NO_GO_MISSING_DURABLE_RUNTIME_EVIDENCE",
        "candidate_revision": candidate.revision,
        "candidate_crc32": candidate.pack_crc32,
        "runtime_status": status,
        "checked_paths": checked_paths,
        "failures": failures,
        "durable": not failures,
    }


def current_candidate() -> ScreenRuntimeCandidate:
    data = json.loads(MENU_EVIDENCE.read_text(encoding="utf-8"))
    resource = data.get("resource_pack", {})
    runtime = data.get("runtime_evidence", {})
    candidate = ScreenRuntimeCandidate(
        revision=int(resource.get("revision", 0)),
        total_bytes=int(resource.get("total_bytes", 0)),
        pack_crc32=str(resource.get("pack_crc32", "")),
        runtime_status=str(runtime.get("status", "")),
        clips=int(resource.get("clips", 0)),
        frames=int(resource.get("frames", 0)),
    )
    if candidate.revision <= 0:
        raise ValueError("active CEMP revision must be positive")
    if candidate.total_bytes <= 0:
        raise ValueError("active CEMP size must be positive")
    if len(candidate.pack_crc32) != 10 or not candidate.pack_crc32.startswith("0x"):
        raise ValueError("active CEMP CRC must be an 8-digit hexadecimal value")
    if candidate.clips <= 0 or candidate.frames <= 0:
        raise ValueError("active CEMP must contain clips and frames")
    if candidate.runtime_status not in {candidate.pending_status, candidate.pass_status}:
        raise ValueError("active CEMP runtime status must be pending or promoted")
    return candidate


def current_runtime_evidence_durability() -> dict[str, Any]:
    menu = json.loads(MENU_EVIDENCE.read_text(encoding="utf-8"))
    return evaluate_runtime_evidence_durability(
        current_candidate(),
        menu.get("runtime_evidence", {}),
    )
