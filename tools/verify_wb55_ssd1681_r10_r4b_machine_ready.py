#!/usr/bin/env python3
"""Generate the narrow offline R4b MACHINE_READY manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    build = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r10_ball"
    paths = {
        "elf": build / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.elf",
        "hex": build / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.hex",
        "parser": ROOT / "tools/verify_wb55_ssd1681_r10_ball_log.py",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1",
        "driver": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
        "focused": ROOT / "tools/verify_wb55_ssd1681_r10_r4b_telemetry.py",
        "work_package": ROOT / "docs/validation/companion-ssd1681-r10-r4b-corridor-telemetry-repair-work-package-20260722.md",
    }
    out = ROOT / "docs/validation/companion-ssd1681-r10-r4b-corridor-telemetry-repair-machine-ready-20260722.json"
    artifact = {"driver": sha(paths["driver"]), "elf": sha(paths["elf"]), "hex": sha(paths["hex"]), "parser_sha256": sha(paths["parser"]), "monitor": sha(paths["monitor"]), "launcher": sha(paths["launcher"]), "runner": sha(paths["runner"]), "supervisor": sha(paths["supervisor"])}
    payload = [
        "51CFA32FECE0135F38198DA2529E7C6A0C1F53747984D55705077B7F6920CC76",
        "51ECCB35B2C3D9CA78D193482D623F0809D1F094D0804E10ABE677C11D0BC930",
        "B96DFF5E9B1B552B49C7B3A0DE5228A2761319007565E807B610785A5D7B1B06",
        "82D7C8ED67824AEDF8DD7E0DE02B5C7D375A5F11AD9731B24C87E063221416BB",
        "933CD8FFC54D7BB04C3EB45460303613D3860EADDC959A5D117196ED4B467862",
        "5740CC300E6C89757B0588D495F2C2943917933FCBC9190B5432E9D126F160F8",
    ]
    manifest = {
        "schema_id": "companion.wb55.ssd1681.r10_r4b_corridor_telemetry.machine_ready.v1",
        "status": "MACHINE_READY_R10_R4B_TELEMETRY_REPAIR_OFFLINE_ONLY",
        "authority": "COMP-REQ-339",
        "hardware_contact": 0,
        "execute_authorized": False,
        "authorization_created": False,
        "artifacts": artifact,
        "protected": {"lut_sha256": "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD", "tail_hex": "221741A83258", "restore_application_sha256": "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"},
        "r4_disposition": {"authorization_consumed": True, "output_root": ".cache/validation/wb55-r10-r4-corridor-execute-20260722-r1", "postclean": "PASS", "restore_sha256": "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C", "normal_resume": "PASS", "retry_count": 0, "status": "MACHINE_NO_GO_TELEMETRY_PERSISTENCE", "qualification_frames": 16, "busy_min_ms": 597, "busy_max_ms": 599, "loop_first_rejected": 1, "popup_invoked": False, "visual_verdict": None, "prior_machine_ready_sha256": "F17405FC6FA233B7C1FAF0022C208833B75EB3A5B01E3A7F0C01FCCB84BFA6FF"},
        "r4b_repair": {"driver_sha256": sha(paths["driver"]), "position_keyed_fixed_corridor_payload_hashes": payload, "focused_regression_sha256": sha(paths["focused"]), "focused_evidence": {"status": "PASS_R10_R4B_TELEMETRY_REPAIR_FOCUSED", "outcomes": {"corrected_schema_v3_loop_iteration_1": "PASS", "stale_captured_shape": "REJECTED", "only_two_hash_corrections": "PASS", "additional_mutation": "REJECTED"}}, "work_package_sha256": sha(paths["work_package"]), "cached_checkonly_reused_by_sha": True, "unchanged_host_hashes_reused": True},
    }
    canonical = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if out.exists():
        if out.read_bytes() != canonical:
            raise RuntimeError("Existing R4b MACHINE_READY differs from generator canonical bytes.")
        action = "VERIFIED_EXISTING"
    else:
        out.write_bytes(canonical)
        action = "WROTE_ONCE"
    print(json.dumps({"status": manifest["status"], "action": action, "path": str(out), "sha256": sha(out), "artifacts": artifact, "focused_evidence": manifest["r4b_repair"]["focused_evidence"], "lut_sha256": manifest["protected"]["lut_sha256"], "hardware_contact": 0, "execute_authorized": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
