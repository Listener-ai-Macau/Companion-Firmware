import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "d311af3db60e118a6d2c6e68873b2d00f2647a96"
OUT = ROOT / "docs" / "validation" / "companion-platform-adapters-machine-ready.json"
FILES = [
    "app/companion_pendant/platform/companion_platform_adapters.h",
    "app/companion_pendant/platform/companion_platform_adapters.c",
    "tools/fixtures/companion_platform_adapters_test.c",
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(*args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def main() -> int:
    head = run("git", "rev-parse", "HEAD").stdout.strip()
    link = run("git", "ls-tree", "HEAD", "third_party/denzic-platform").stdout.strip()
    status_lines = [
        line for line in run("git", "status", "--porcelain").stdout.splitlines()
        if line[3:].replace('\\', '/') != "docs/validation/companion-platform-adapters-machine-ready.json"
    ]
    status = "\n".join(status_lines)
    source_files = {p: sha(ROOT / p) for p in FILES if (ROOT / p).is_file()}
    compiler = next((x for x in ("arm-none-eabi-gcc", "gcc", "clang", "cl") if shutil.which(x)), None)
    checks = {
        "git_clean_before_commit": status == "",
        "platform_pin": link.endswith(PIN + "\tthird_party/denzic-platform"),
        "fixed_capacity_symbols": all(
            token in (ROOT / FILES[0]).read_text(encoding="utf-8")
            for token in ("COMPANION_PLATFORM_TRACE_CAPACITY", "COMPANION_PLATFORM_DIAG_EVENT_CAPACITY")
        ),
        "no_apply_default": "r.apply_requested = false" in (ROOT / FILES[1]).read_text(encoding="utf-8"),
        "no_forbidden_tree_edits": not any(
            p.startswith(("cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c", "app/companion_pendant/epaper/", "app/companion_pendant/touch/"))
            for p in status.splitlines()
        ),
        "host_compiler_available": compiler is not None,
        "isolated_o2_wb55_ble_link": False,
        "source_hex_elf_available": False,
    }
    artifact = {
        "schema": "companion.platform_adapters.machine_ready.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "commit": head,
        "platform_pin": PIN,
        "gitlink": link,
        "source_sha256": source_files,
        "runner": "tools/fixtures/companion_platform_adapters_test.c",
        "runner_sha256": sha(ROOT / "tools/fixtures/companion_platform_adapters_test.c"),
        "checks": checks,
        "compiler": compiler,
        "side_effects": {"hardware": 0, "ble_write": 0, "ota_transfer": 0, "ota_apply": 0, "popup": 0, "push": 0},
        "physical_gates": {"execute": "OPEN", "hardware": "OPEN", "real_ble": "OPEN", "ota_transfer_apply": "OPEN"},
        "note": "C compile-only evidence is available; complete O2 WB55/BLE link and source/HEX/ELF evidence remain open.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2))
    return 0 if artifact["status"] == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
