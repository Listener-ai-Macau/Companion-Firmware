#!/usr/bin/env python3
"""Bind current LP entry to the sealed 2026-08-07 Owner-PASS F7 baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
BASELINE = (
    ROOT / ".cache/validation/screen-freeze-fix-20260806"
    / "baseline-lp-enter-clean-screen-20260807/baseline.json"
)
OWNER = BASELINE.parent / "evidence/owner-result.txt"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def extract(source: str, name: str) -> str:
    match = re.search(rf"(?:static )?[^\n]+ {re.escape(name)}\(", source)
    if match is None:
        raise ValueError(f"missing function {name}")
    body = source.find("{", match.start())
    depth = 0
    for index in range(body, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start() : index + 1]
    raise ValueError(f"unterminated function {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", required=True, type=pathlib.Path)
    args = parser.parse_args()
    source = DRIVER.read_text(encoding="utf-8")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8-sig"))
    owner = json.loads(OWNER.read_text(encoding="utf-8-sig"))
    landing = extract(source, "ssd1681_lifecycle_lp_enter_freeze_clean")
    product = extract(source, "ssd1681_accepted_cached_mode2_product_refresh")
    sleep = extract(
        source, "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep"
    )

    strong_start = product.index("if (strong_idle_enter_refresh) {")
    boundary_start = product.index(
        "} else if (first_frame || visible_full_refresh || maintenance_refresh)",
        strong_start,
    )
    strong = product[strong_start:boundary_start]

    checks = {
        "sealed_baseline_is_owner_pass": (
            baseline.get("status") == "OWNER_PASS_SEALED"
            and baseline.get("id") == "baseline-lp-enter-clean-screen-20260807"
            and owner.get("selection") == "通过"
            and owner.get("path") == "f7_white_basemap_then_target"
            and owner.get("bin_sha256")
            == "C09538DC11D95C6ECC6D84C25910DC20EB232E1476E0ADDD5071A41A0BC33DDD"
        ),
        "lp_has_exact_two_f7_activations": (
            landing.count("ssd1681_lp_current_only_full(") == 2
            and "report->activation_count = 2u;" in landing
        ),
        "first_f7_rebuilds_dual_white_basemap": (
            "memset(s_frame, 0xFFu, SSD1681_FRAME_BYTES);" in landing
            and "s_frame, &window, &total_busy_ms, 0xF7u, true, false" in landing
            and "planes=0x24+0x26=white" in landing
        ),
        "second_f7_is_white_to_sleepy": (
            "s_blink_closed_frame, &window, &total_busy_ms" in landing
            and "0xF7u, false, false" in landing
            and "old_plane=white" in landing
        ),
        "target_rebaseline_has_no_third_activation": (
            landing.count("ssd1681_write_plane_region(") == 2
            and "0x26u, s_blink_closed_frame" in landing
            and "0x24u, s_blink_closed_frame" in landing
            and "post_sync_bytes = 2u * SSD1681_FRAME_BYTES" in landing
        ),
        "mode2_rearm_and_awake_hold_match_pass": (
            "ssd1681_accepted_mode2_rearm(NULL)" in landing
            and "s_lp_hold_awake_after_clean_enter = true;" in landing
            and "skipped=owner_pass_f7_white_basemap" in sleep
            and "return true;" in sleep
        ),
        "only_lp_strong_uses_sealed_landing": (
            strong.count("ssd1681_lifecycle_lp_enter_freeze_clean(") == 1
            and "ssd1681_lifecycle_mode2_fast_full_activation(" not in strong
            and "ssd1681_lifecycle_lp_enter_inv_f7" not in strong
        ),
        "ordinary_life_does_not_auto_full": (
            "automatic_life_maintenance = false;" in product
            and "Ordinary product partial: single 0xCF path" in product
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema_id": "companion.comp775.lp_owner_pass_f7.static.v1",
        "status": "PASS_STATIC_OWNER_F7_RESTORED" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "driver": {"path": str(DRIVER), "sha256": digest(DRIVER)},
        "baseline": {"path": str(BASELINE), "sha256": digest(BASELINE)},
        "owner_result": {"path": str(OWNER), "sha256": digest(OWNER)},
        "claim_scope": "sealed LP topology only; current binary and glass unproven",
    }
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if failures:
        print("FAIL: " + ", ".join(failures), file=sys.stderr)
        return 1
    print("PASS: sealed Owner-PASS F7 LP topology restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
