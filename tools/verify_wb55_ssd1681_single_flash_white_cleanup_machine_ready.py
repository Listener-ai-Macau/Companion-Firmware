"""Final offline-only binding for COMP-REQ-409; no authorization is produced."""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
RESTORE = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
FILES = {
    "driver": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
    "hex": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_single_flash_white_cleanup/Companion_Nucleo_WB55RG_Ssd1681SingleFlashWhiteCleanup.hex",
    "elf": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_single_flash_white_cleanup/Companion_Nucleo_WB55RG_Ssd1681SingleFlashWhiteCleanup.elf",
    "runner": ROOT / "tools/run_wb55_ssd1681_single_flash_white_cleanup.ps1",
    "launcher": ROOT / "tools/start_wb55_ssd1681_single_flash_white_cleanup.ps1",
    "parser": ROOT / "tools/verify_wb55_ssd1681_single_flash_white_cleanup_log.py",
    "static": ROOT / "tools/verify_wb55_ssd1681_single_flash_white_cleanup_static.py",
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def main() -> int:
    static = subprocess.run(["python", str(FILES["static"])], cwd=ROOT, capture_output=True, text=True)
    parser = subprocess.run(["python", str(FILES["parser"])], cwd=ROOT, capture_output=True, text=True)
    if static.returncode or parser.returncode:
        raise SystemExit("static/parser failed")
    check_root = ROOT / ".cache/validation/wb55-ssd1681-single-flash-white-cleanup-checkonly-20260723-r2"
    check = json.loads((check_root / "checkonly.json").read_text(encoding="utf-8-sig"))
    counters = ("hardware_contact", "programmer", "serial", "write", "reset", "refresh", "popup", "retry", "authorization", "claim_only", "execute")
    if any(check.get(key) != 0 for key in counters):
        raise SystemExit("CheckOnly contacted hardware or exposed authorization")
    hashes = {name: sha(path) for name, path in FILES.items()}
    result = {
        "status": "MACHINE_READY",
        "requirement": "COMP-REQ-409",
        "offline_only": True,
        "authorization_created": False,
        "build_recipe": "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -EpaperSsd1681SingleFlashWhiteCleanupDiagnostic -Optimization O2 -Force",
        "driver_hashes": hashes,
        "checkonly_root": str(check_root.relative_to(ROOT)).replace("\\", "/"),
        "checkonly_counters": {key: check[key] for key in counters},
        "protected_acceptance_sha256": PROTECTED,
        "restore_application_sha256": RESTORE,
        "candidate": {"window": "logical_x0-24,logical_y0-199/controller_y199-0", "reset": "10ms low + 10ms high + ready", "frame_bytes": 5000, "plane24": 5000, "plane26": 5000, "control": "0xFF", "activation": 1, "busy_waits": 1, "forbidden": ["0x12", "0x01", "0x11", "0x18", "0x05 border", "0xF7", "0x32", "custom LUT", "second activation", "retry", "maintenance"]},
        "physical_visual_flash_count": "UNPROVEN_OWNER_HARDWARE_ACCEPTANCE_REQUIRED",
        "negative_fixtures": "parser and static self-tests PASS",
        "r6_movement": "unchanged source signature; no 0x24/0xCF/0x20/BUSY movement edits",
    }
    out = ROOT / "docs/validation/companion-ssd1681-single-flash-white-cleanup-machine-ready-20260723.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
