#!/usr/bin/env python3
"""Offline fixtures for the COMP-REQ-775 boot-log verifier."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / ".cache/validation/comp-req-775-incremental-sync"
MANIFEST = (
    ARTIFACTS
    / "offline-initial-batched/current-source-pack/source-pack-manifest.json"
)
OFFLINE = ARTIFACTS / "OFFLINE_READY.json"
OUTPUT = ARTIFACTS / "BOOT_LOG_VERIFIER_OFFLINE_READY.json"
VERIFIER = (
    REPO / "tools/faraday_upper_art/verify_comp_req_775_boot_log.py"
)


def load_verifier():
    spec = importlib.util.spec_from_file_location("boot_log_verifier", VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load boot-log verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    verifier = load_verifier()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    offline = json.loads(OFFLINE.read_text(encoding="utf-8"))
    state = next(item for item in manifest["states"] if item["kind"] == "life")
    life = (
        "[screen-life] "
        f"family={state['family']} action={state['life_action']} "
        f"episode={state['action_episode']} phrase={state['phrase']} "
        f"phase={state['phase']} variation={state['variation']} "
        f"dwell_commits={state['dwell_commits']} "
        f"clip=frame_{state['unique_frame_index']:04d} "
        f"frame_index={state['unique_frame_index']}"
    )
    baseline = "\n".join(
        [
            "[boot] Companion NUCLEO-WB55RG bringup",
            "[screen-assets] ui_generation=active generation=1",
            (
                "[screen-assets] policy=comp_req_638_external_cemp "
                "store=ready prefix=read:43454D50 activation=allowed "
                "identity=comp_req_638 mount=ok"
            ),
            (
                "[rec-resource] mount=ok base=0x001DC000 "
                "pack_bytes=133851 g7_bytes=112000 opus_bytes=21723"
            ),
            (
                "[screen-assets] browser_function_timing=ready "
                "charging=3,3,1 recording=1,1,1 speaker=1,1,1 "
                "unit_ms=480"
            ),
            (
                "[screen] initial_generation_refresh state=pending "
                "generation=1 first_visible=full subsequent=partial"
            ),
            life,
            (
                "[screen] initial_generation_refresh state=scheduled "
                "generation=1 request=3758096385 refresh=4"
            ),
            (
                "[epaper] accepted_product_driver request=3758096385 "
                "changed=1 control=0xC7 bytes=5000 transaction_ms=1876 "
                "busy_ms=1730 ready_checks=1 maintenance=0 decision=0 "
                "transport=software_direct_bsrr_diagnostic "
                "has_busy=1 result=1"
            ),
            (
                "[screen] initial_generation_refresh state=committed "
                "generation=1 request=3758096385 refresh=4 bytes=5000"
            ),
            (
                "[epaper] accepted_product_driver request=3758096386 "
                "changed=1 control=0xCF bytes=2772 transaction_ms=248 "
                "busy_ms=235 ready_checks=1 maintenance=0 decision=1 "
                "reason=1 partial_before=0 "
                "transport=software_direct_bsrr_diagnostic "
                "has_busy=1 result=1"
            ),
            *[
                (
                    "[epaper] accepted_product_driver "
                    f"request={3758096387 + partial_before} "
                    "changed=1 control=0xCF bytes=2772 "
                    "transaction_ms=248 busy_ms=235 ready_checks=1 "
                    "maintenance=0 decision=1 reason=1 "
                    f"partial_before={partial_before} "
                    "transport=software_direct_bsrr_diagnostic "
                    "has_busy=1 result=1"
                )
                for partial_before in range(1, 6)
            ],
            "",
        ]
    ).encode()
    ready = verifier.verify(baseline, manifest, offline["page_sha256"])
    windowed = verifier.verify(
        baseline.replace(
            b"control=0xC7 bytes=5000",
            b"control=0xC7 window=0-24,0-199 bytes=5000",
        ).replace(
            b"control=0xCF bytes=2772",
            b"control=0xCF window=0-21,46-171 bytes=2772",
        ),
        manifest,
        offline["page_sha256"],
    )
    stale_preboot = verifier.verify(
        (
            "[screen-life] family=calm action=soften episode=2 "
            "phrase=2 phase=accent variation=2 dwell_commits=3 "
            "clip=frame_0157 frame_index=157\n"
        ).encode()
        + baseline,
        manifest,
        offline["page_sha256"],
    )
    wrong_clip = verifier.verify(
        baseline.replace(b"clip=frame_", b"clip=wrong_"),
        manifest,
        offline["page_sha256"],
    )
    fault = verifier.verify(
        baseline + b"[screen] fault terminal_fault=1\n",
        manifest,
        offline["page_sha256"],
    )
    missing_recording_pack = verifier.verify(
        baseline.replace(
            (
                b"[rec-resource] mount=ok base=0x001DC000 "
                b"pack_bytes=133851 g7_bytes=112000 opus_bytes=21723\n"
            ),
            b"",
        ),
        manifest,
        offline["page_sha256"],
    )
    recovery_before_resource_install = verifier.verify(
        baseline.replace(
            (
                b"[rec-resource] mount=ok base=0x001DC000 "
                b"pack_bytes=133851 g7_bytes=112000 opus_bytes=21723\n"
            ),
            b"",
        ),
        manifest,
        offline["page_sha256"],
        require_recording_resource=False,
    )
    missing_partial = verifier.verify(
        b"\n".join(
            line
            for line in baseline.splitlines()
            if b"control=0xCF" not in line
        )
        + b"\n",
        manifest,
        offline["page_sha256"],
    )
    checks = {
        "valid_log_ready": ready["status"] == "MACHINE_READY",
        "valid_log_all_checks": all(ready["checks"].values()),
        "window_field_log_ready": (
            windowed["status"] == "MACHINE_READY"
            and windowed["home_choreography_refresh"][
                "maximum_partial_before"
            ]
            == 5
        ),
        "preboot_stale_frame_ignored": (
            stale_preboot["status"] == "MACHINE_READY"
            and stale_preboot["first_browser_frame"]
            == ready["first_browser_frame"]
        ),
        "wrong_clip_rejected": (
            wrong_clip["status"] == "FAILED"
            and not wrong_clip["checks"][
                "browser_runtime_first_frame_exact"
            ]
        ),
        "runtime_fault_rejected": (
            fault["status"] == "FAILED"
            and not fault["checks"]["no_runtime_fault"]
        ),
        "missing_recording_resource_pack_rejected": (
            missing_recording_pack["status"] == "FAILED"
            and not missing_recording_pack["checks"][
                "recording_resource_pack_mount_ok"
            ]
        ),
        "registered_recovery_can_precede_resource_install": (
            recovery_before_resource_install["status"] == "MACHINE_READY"
            and recovery_before_resource_install["recording_resource_pack"]
            == {"required": False, "observed": False}
        ),
        "missing_post_boot_partial_rejected": (
            missing_partial["status"] == "FAILED"
            and not missing_partial["checks"][
                "subsequent_choreography_uses_partial_refresh"
            ]
        ),
        "cached_mode2_boot_full_rejected": (
            verifier.verify(
                baseline.replace(b"control=0xC7", b"control=0xFF", 1),
                manifest,
                offline["page_sha256"],
            )["status"]
            == "FAILED"
        ),
        "automatic_home_mode1_maintenance_rejected": (
            verifier.verify(
                baseline
                + (
                    b"[epaper] accepted_product_driver request=3758096400 "
                    b"changed=1 control=0xC7 bytes=5000 "
                    b"transaction_ms=1876 busy_ms=1729 ready_checks=3 "
                    b"maintenance=1 decision=2 reason=4 "
                    b"partial_before=5 "
                    b"transport=software_direct_bsrr_diagnostic "
                    b"has_busy=1 result=1\n"
                ),
                manifest,
                offline["page_sha256"],
            )["status"]
            == "FAILED"
        ),
        "automatic_home_legacy_maintenance_rejected": (
            verifier.verify(
                baseline
                + (
                    b"[epaper] accepted_product_driver request=3758096401 "
                    b"changed=1 control=0xFF bytes=5000 "
                    b"transaction_ms=248 busy_ms=235 ready_checks=1 "
                    b"maintenance=1 decision=2 reason=4 "
                    b"partial_before=6 "
                    b"transport=software_direct_bsrr_diagnostic "
                    b"has_busy=1 result=1\n"
                ),
                manifest,
                offline["page_sha256"],
            )["status"]
            == "FAILED"
        ),
    }
    receipt = {
        "schema": "companion.comp_req_775.boot_log_test.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "checks": checks,
        "valid_first_frame": ready["first_browser_frame"],
        "hardware_contact": 0,
    }
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt["status"] != "MACHINE_READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
