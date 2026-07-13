#!/usr/bin/env python3
"""Read the active external CEMP candidate for WB55 runtime evidence tools."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


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
