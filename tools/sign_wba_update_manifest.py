#!/usr/bin/env python3
"""Create/verify the signed WUM1 envelope consumed before an existing DOV1 OTA.

Development keys live outside rebuildable caches by default.
The private key is never embedded in the envelope, public header, or stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import struct
import sys
import zlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature

ROOT = pathlib.Path(__file__).resolve().parents[1]
WIRE_BYTES = 144
SIGNED_BYTES = 76
TARGETS = {"firmware": 1, "ui-assets": 2}


def number(value: str) -> int:
    result = int(value, 0)
    if not 0 <= result <= 0xFFFFFFFF:
        raise argparse.ArgumentTypeError("value must fit uint32")
    return result


def inside_cache(path: pathlib.Path) -> bool:
    try:
        path.resolve().relative_to((ROOT / ".cache").resolve())
        return True
    except ValueError:
        return False


def public_xy(public_key: ec.EllipticCurvePublicKey) -> bytes:
    numbers = public_key.public_numbers()
    return numbers.x.to_bytes(32, "big") + numbers.y.to_bytes(32, "big")


def signed_prefix(args: argparse.Namespace, payload: bytes) -> bytes:
    digest = hashlib.sha256(payload).digest()
    prefix = bytearray(SIGNED_BYTES)
    struct.pack_into("<4sBBHIIIIIII32sBBHI", prefix, 0, b"WUM1", 1,
                     TARGETS[args.target], args.format_version,
                     args.target_family, args.board_target,
                     args.component_version, args.minimum_app_version,
                     args.maximum_app_version, len(payload),
                     zlib.crc32(payload) & 0xFFFFFFFF, digest,
                     1, 0, 0, args.key_id)
    return bytes(prefix)


def cmd_generate(args: argparse.Namespace) -> int:
    destination = pathlib.Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    private_path = destination / "wba-update-dev-private.pem"
    public_path = destination / "wba-update-dev-public.pem"
    if (private_path.exists() and not args.force):
        raise SystemExit(f"refusing to replace existing key: {private_path}")
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_path.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    try:
        os.chmod(private_path, 0o600)
    except OSError:
        pass
    public_path.write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo))
    marker = destination / "DEV_ONLY.txt"
    marker.write_text("DEV_ONLY OTA signing key. Never use this trust anchor in production.\n",
                      encoding="utf-8")
    print(f"DEV_ONLY keypair created under {destination}")
    print(f"private={private_path.name} public={public_path.name}")
    return 0


def load_private(path: pathlib.Path) -> ec.EllipticCurvePrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
        raise SystemExit("private key must be P-256 (secp256r1)")
    return key


def write_public_header(path: pathlib.Path, key_id: int, xy: bytes, dev_only: bool) -> None:
    values = ",".join(f"0x{x:02x}" for x in xy)
    guard = "COMPANION_WBA_UPDATE_TRUST_ANCHOR_H"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#ifndef {guard}\n#define {guard}\n\n#include <stdint.h>\n\n"
        f"#define COMP_WBA_UPDATE_TRUST_KEY_ID UINT32_C(0x{key_id:08X})\n"
        f"#define COMP_WBA_UPDATE_TRUST_DEV_ONLY {1 if dev_only else 0}\n"
        "static const uint8_t comp_wba_update_trust_public_key_xy[64] = {\n    "
        + values + "\n};\n\n#endif\n", encoding="ascii")


def cmd_sign(args: argparse.Namespace) -> int:
    expected_format = 2 if args.target == 'ui-assets' else 1
    if args.format_version is None:
        args.format_version = expected_format
    if args.format_version != expected_format:
        raise ValueError(f'{args.target} requires format-version {expected_format}')
    payload_path = pathlib.Path(args.payload)
    output = pathlib.Path(args.output)
    private_path = pathlib.Path(args.private_key)
    payload = payload_path.read_bytes()
    # A UI update is the complete external-NOR partition, including both
    # generation roots. The smaller internal application limit cannot be used
    # for a resource payload.
    limit = 0x200000 if args.target == "ui-assets" else 0x0F0000
    if args.target_family == 0x41425743:
        from wba_flash_geometry import MCUS, for_mcu
        geometry = next((for_mcu(mcu) for mcu in MCUS
                         if for_mcu(mcu).board_target == args.board_target), None)
        if geometry is None:
            raise SystemExit('Unknown Companion internal Flash target identity')
        if args.target == 'firmware':
            limit = geometry.app_bytes
        else:
            from wba_resource_geometry import NOR_BYTES, SYSTEM_BYTES, SECTOR_BYTES
            limit = NOR_BYTES - SYSTEM_BYTES - SECTOR_BYTES
    if not payload or len(payload) > limit:
        raise SystemExit(f"{args.target} payload size must be 1..0x{limit:X} bytes")
    if args.key_id == 0:
        raise SystemExit("key-id zero is reserved for 'not configured'")
    private_key = load_private(private_path)
    prefix = signed_prefix(args, payload)
    der = private_key.sign(prefix, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    raw_signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    body = prefix + raw_signature
    wire = body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)
    assert len(wire) == WIRE_BYTES
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(wire)
    pub = public_xy(private_key.public_key())
    dev_only = (private_path.parent / "DEV_ONLY.txt").exists() or private_path.name == "wba-update-dev-private.pem"
    if args.public_header:
        write_public_header(pathlib.Path(args.public_header), args.key_id, pub, dev_only)
    if args.public_xy:
        public_xy_path = pathlib.Path(args.public_xy)
        public_xy_path.parent.mkdir(parents=True, exist_ok=True)
        public_xy_path.write_bytes(pub)
    metadata = {
        "schema": "companion.wba_update_manifest.v1",
        "wire": output.name,
        "wire_bytes": len(wire),
        "signed_bytes": SIGNED_BYTES,
        "target": args.target,
        "target_family": f"0x{args.target_family:08X}",
        "board_target": f"0x{args.board_target:08X}",
        "component_version": args.component_version,
        "size_bytes": len(payload),
        "crc32": f"{zlib.crc32(payload) & 0xFFFFFFFF:08X}",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "key_id": f"0x{args.key_id:08X}",
        "algorithm": "ECDSA_P256_SHA256_RAW_RS",
        "dev_only": dev_only,
    }
    output.with_suffix(output.suffix + ".json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"signed_manifest={output} bytes={len(wire)} key_id=0x{args.key_id:08X} DEV_ONLY={int(dev_only)}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    wire = pathlib.Path(args.manifest).read_bytes()
    if len(wire) != WIRE_BYTES or wire[:4] != b"WUM1":
        raise SystemExit("invalid WUM1 length or magic")
    if zlib.crc32(wire[:140]) & 0xFFFFFFFF != struct.unpack_from("<I", wire, 140)[0]:
        raise SystemExit("invalid WUM1 CRC32")
    public_key = serialization.load_pem_public_key(pathlib.Path(args.public_key).read_bytes())
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(public_key.curve, ec.SECP256R1):
        raise SystemExit("public key must be P-256 (secp256r1)")
    r = int.from_bytes(wire[76:108], "big")
    s = int.from_bytes(wire[108:140], "big")
    try:
        public_key.verify(encode_dss_signature(r, s), wire[:SIGNED_BYTES],
                          ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as error:
        raise SystemExit("invalid WUM1 P-256 signature") from error
    print(f"VERIFIED manifest={args.manifest} key_id=0x{struct.unpack_from('<I', wire, 72)[0]:08X}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate-dev-key")
    generate.add_argument("--output-dir", default=str(pathlib.Path.home()/".denzic"/"keys"/"Companion"/"development"))
    generate.add_argument("--force", action="store_true")
    generate.set_defaults(func=cmd_generate)
    sign = sub.add_parser("sign")
    sign.add_argument("--payload", required=True)
    sign.add_argument("--private-key", required=True)
    sign.add_argument("--output", required=True)
    sign.add_argument("--public-header")
    sign.add_argument("--public-xy", help="write the 64-byte big-endian X||Y public key")
    sign.add_argument("--target", choices=TARGETS, required=True)
    sign.add_argument("--format-version", type=number, help="firmware=1; complete UI partition=2 (target-specific default)")
    sign.add_argument("--target-family", type=number, required=True)
    sign.add_argument("--board-target", type=number, required=True)
    sign.add_argument("--component-version", type=number, required=True)
    sign.add_argument("--minimum-app-version", type=number, default=0)
    sign.add_argument("--maximum-app-version", type=number, default=0xFFFFFFFF)
    sign.add_argument("--key-id", type=number, required=True)
    sign.set_defaults(func=cmd_sign)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--public-key", required=True)
    verify.set_defaults(func=cmd_verify)
    return result


if __name__ == "__main__":
    try:
        arguments = parser().parse_args()
        raise SystemExit(arguments.func(arguments))
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
