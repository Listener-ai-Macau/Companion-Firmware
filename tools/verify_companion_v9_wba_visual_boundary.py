#!/usr/bin/env python3
"""Keep WBA target adapters compatible with the current v9-only visual boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
V9_LOCK = ROOT / "docs/art/iterations/companion-pet-expression-v9/baseline-lock.json"
VISUAL_READY = ROOT / "docs/validation/companion-ui-visual-acceptance-readiness-20260717.json"
SPECIAL_MAPPING = ROOT / "docs/art/iterations/companion-pet-special-states-v1/pending-source-mapping.json"
WBA_ASSETS = ROOT / "app/companion_pendant/epaper/screen_assets_stm32wba.c"
WBA_PANEL = ROOT / "app/companion_pendant/epaper/panel_target_stm32wba.c"
WBA_TOUCH = ROOT / "app/companion_pendant/touch/touch_target_stm32wba_ft6336.c"
WBA_SPI_NOR = ROOT / "app/companion_pendant/storage/spi_nor_stm32wba.c"
OUTPUT = ROOT / "docs/validation/companion-v9-wba-visual-boundary-20260717.json"
V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
FORBIDDEN_VISUAL_TOKENS = (
    "expression_assets_200x200",
    "genref_sheet_12_inner_faces_v5",
    "emote_matrix_white_200x200",
    "legacy_cemp",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def verify() -> dict[str, object]:
    errors: list[str] = []
    lock = json.loads(V9_LOCK.read_text(encoding="utf-8"))
    readiness = json.loads(VISUAL_READY.read_text(encoding="utf-8"))
    mapping = json.loads(SPECIAL_MAPPING.read_text(encoding="utf-8"))
    source = ROOT / lock.get("accepted_source", {}).get("path", "")
    if lock.get("status") != "OWNER_APPROVED_SOURCE_LOCKED_MACHINE_RENDER_AUTHORIZED":
        errors.append("v9 baseline lock is not owner approved")
    if lock.get("accepted_source", {}).get("sha256", "").upper() != V9_SHA256:
        errors.append("v9 baseline lock hash drifted")
    if not source.is_file() or sha256(source) != V9_SHA256:
        errors.append("v9 baseline source hash drifted")
    if readiness.get("status") != "PASS_READY_FOR_SEQUENTIAL_OWNER_REVIEW":
        errors.append("current v9 menu and special sources are not ready for owner review")
    if mapping.get("status") != "PENDING_OWNER_VISUAL_DECISION_NO_RUNTIME_ACTIVATION":
        errors.append("pending special source mapping is not fail-closed")

    wba_sources = (WBA_ASSETS, WBA_PANEL, WBA_TOUCH, WBA_SPI_NOR)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in wba_sources)
    for token in FORBIDDEN_VISUAL_TOKENS:
        if token.lower() in combined.lower():
            errors.append(f"WBA target code must not import retired visual token {token}")
    if "COMP_ASSET_STORAGE_EXTERNAL_NOR" not in WBA_ASSETS.read_text(encoding="utf-8"):
        errors.append("WBA assets adapter must retain external NOR storage binding")
    if "NOR_CMD_READ_DATA 0x03u" not in WBA_SPI_NOR.read_text(encoding="utf-8"):
        errors.append("WBA storage adapter must retain ordinary 1-1-1 SPI NOR read transport")

    return {
        "schema": "companion.v9_wba_visual_boundary.v1",
        "status": "PASS_V9_WBA_VISUAL_BOUNDARY_PENDING_OWNER" if not errors else "FAIL",
        "active_visual_baseline": {
            "path": V9_LOCK.relative_to(ROOT).as_posix(),
            "source_sha256": V9_SHA256,
            "owner_approved": True,
        },
        "pending_visual_sources": {
            "menu_and_special_readiness": VISUAL_READY.relative_to(ROOT).as_posix(),
            "special_mapping": SPECIAL_MAPPING.relative_to(ROOT).as_posix(),
            "owner_decisions_required": 3,
        },
        "wba_resource_boundary": {
            "storage": "external CEMP through callback-only external NOR adapter",
            "transport": "ordinary 1-1-1 SPI NOR",
            "retired_visual_tokens_forbidden": list(FORBIDDEN_VISUAL_TOKENS),
            "runtime_activation_allowed": False,
            "panel_parity_claimed": False,
        },
        "errors": errors,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the visual-boundary evidence JSON.")
    args = parser.parse_args(argv)
    result = verify()
    if args.write:
        OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if result["errors"]:
        for error in result["errors"]:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: WBA target adapters retain the v9-only external-resource visual boundary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
