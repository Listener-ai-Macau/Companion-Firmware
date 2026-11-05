#!/usr/bin/env python3
"""HOST_ONLY interoperability test for WUM1 signing and portable parsing."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache/wba-update-manifest-host"
UPDATE = ROOT / "app/companion_pendant/update"
TOOL = ROOT / "tools/sign_wba_update_manifest.py"
SRC = [UPDATE / "tests/test_wba_update_manifest.c",
       UPDATE / "wba_update_manifest_wire.c", UPDATE / "wba_update_p256.c",
       UPDATE / "wba_update_service.c",
       ROOT / "third_party/denzic-platform/ota/embedded/c/src/denzic_ota_v1.c"]
INC = [UPDATE, ROOT / "third_party/denzic-platform/ota/embedded/c/include"]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)


def compile_test(exe: pathlib.Path) -> subprocess.CompletedProcess[str]:
    cc = shutil.which("clang") or shutil.which("gcc")
    if cc:
        return run([cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                    *sum((["-I", str(x)] for x in INC), []), *map(str, SRC),
                    "-o", str(exe)])
    vc = pathlib.Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat")
    if os.name != "nt" or not vc.exists():
        raise RuntimeError("C compiler unavailable")
    command = ("cl.exe /nologo /Brepro /TC /std:c11 /O2 /W4 /WX /wd4295 "
               + " ".join(f'/I"{x}"' for x in INC) + " "
               + " ".join(f'"{x}"' for x in SRC)
               + f' /Fe:"{exe}" /link /OPT:REF /INCREMENTAL:NO')
    script = OUT / "build.cmd"
    script.write_text(f'@call "{vc}" >nul\n{command}\n', encoding="ascii")
    return run([os.environ.get("ComSpec", "cmd.exe"), "/d", "/c", str(script)])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    keys = OUT / "dev-key"
    if keys.exists():
        keys.resolve().relative_to(OUT.resolve())
        shutil.rmtree(keys)
    generated = run([sys.executable, str(TOOL), "generate-dev-key",
                     "--output-dir", str(keys)])
    payload = OUT / "candidate.bin"
    image = bytearray((index * 29 + 11) & 0xFF for index in range(8192))
    struct.pack_into("<II", image, 0, 0x20020000, 0x08008101)
    payload.write_bytes(image)
    wire = OUT / "candidate.wum"
    header = OUT / "dev_trust_anchor.h"
    signed = run([sys.executable, str(TOOL), "sign", "--payload", str(payload),
                  "--private-key", str(keys / "wba-update-dev-private.pem"),
                  "--output", str(wire), "--public-header", str(header),
                  "--target", "firmware", "--target-family", "0x57424155",
                  "--board-target", "0x56313100", "--component-version", "22",
                  "--minimum-app-version", "21", "--maximum-app-version", "21",
                  "--key-id", "0xD3E00001"])
    verified = run([sys.executable, str(TOOL), "verify", "--manifest", str(wire),
                    "--public-key", str(keys / "wba-update-dev-public.pem")])
    raw = wire.read_bytes()
    private_key = serialization.load_pem_private_key(
        (keys / "wba-update-dev-private.pem").read_bytes(), password=None)
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()
    public_raw = public_numbers.x.to_bytes(32, "big") + public_numbers.y.to_bytes(32, "big")
    (OUT / "public.xy").write_bytes(public_raw)
    digest = hashlib.sha256(raw[:76]).digest()
    (OUT / "signed.digest").write_bytes(digest)
    # Independent cryptography verification of raw r||s.
    public_key.verify(encode_dss_signature(int.from_bytes(raw[76:108], "big"),
                                           int.from_bytes(raw[108:140], "big")),
                      raw[:76], ec.ECDSA(hashes.SHA256()))
    outside = run([sys.executable, str(TOOL), "generate-dev-key",
                   "--output-dir", str(ROOT / "forbidden-dev-key")])
    # Real resource deliveries contain the entire 2MiB partition. Keep the
    # firmware limit separate, and reject even one byte beyond the UI region.
    ui_payload=OUT/"ui-partition.bin";ui_payload.write_bytes(bytes([255])*0x200000)
    ui_wire=OUT/"ui.wum"
    def sign_size(target,extra=()):
        return run([sys.executable,str(TOOL),"sign","--payload",str(ui_payload),
            "--private-key",str(keys/"wba-update-dev-private.pem"),"--output",str(ui_wire),
            "--target",target,"--target-family","0x57424155","--board-target","0x56313100",
            "--component-version","22","--key-id","0xD3E00001",*extra])
    ui_signed=sign_size("ui-assets")
    ui_verified=run([sys.executable,str(TOOL),"verify","--manifest",str(ui_wire),
        "--public-key",str(keys/"wba-update-dev-public.pem")])
    ui_raw=ui_wire.read_bytes()
    ui_matches=struct.unpack_from('<H',ui_raw,6)[0]==2 and struct.unpack_from('<I',ui_raw,28)[0]==0x200000 and ui_raw[36:68]==hashlib.sha256(ui_payload.read_bytes()).digest()
    wrong_format=sign_size('ui-assets',('--format-version','1'))
    firmware_oversize=sign_size("firmware")
    with ui_payload.open('ab') as stream:stream.write(b'\x00')
    ui_oversize=sign_size("ui-assets")
    exe = OUT / ("test_wba_update_manifest.exe" if os.name == "nt" else "test_wba_update_manifest")
    build = compile_test(exe)
    native = run([str(exe), str(wire), str(OUT / "public.xy"),
                  str(OUT / "signed.digest")]) if build.returncode == 0 else None
    ok = (generated.returncode == signed.returncode == verified.returncode == 0 and
          outside.returncode != 0 and native is not None and native.returncode == 0 and
          b"PRIVATE KEY" not in header.read_bytes() and len(raw) == 144 and
          ui_signed.returncode==ui_verified.returncode==0 and ui_matches and
          firmware_oversize.returncode!=0 and ui_oversize.returncode!=0 and wrong_format.returncode!=0)
    result = {
        "schema": "companion.wba_update_manifest.host.v1",
        "status": "PASS" if ok else "NO_GO",
        "host_only": True,
        "hardware_contact": False,
        "real_p256_cryptography_verify": verified.returncode == 0,
        "dev_key_cache_only": outside.returncode != 0,
        "wire_bytes": len(raw),
        "full_ui_partition_signed_and_verified":ui_signed.returncode==ui_verified.returncode==0 and ui_matches,
        "target_size_limits_enforced":firmware_oversize.returncode!=0 and ui_oversize.returncode!=0,
        "ui_format_matches_device_contract":ui_matches and wrong_format.returncode!=0,
        "compile_exit": build.returncode,
        "run_exit": None if native is None else native.returncode,
        "stdout": "" if native is None else native.stdout,
        "stderr": generated.stderr + signed.stderr + verified.stderr + build.stdout + build.stderr + ("" if native is None else native.stderr),
        "sources": {str(x.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(x.read_bytes()).hexdigest() for x in [*SRC, TOOL, pathlib.Path(__file__)]},
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print(result["stderr"], end="")
        return 1
    print(native.stdout.strip())
    print(verified.stdout.strip())
    print(OUT / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
