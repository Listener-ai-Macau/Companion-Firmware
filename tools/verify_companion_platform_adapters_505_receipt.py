import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess

PIN = "d311af3db60e118a6d2c6e68873b2d00f2647a96"
SCHEMA = "companion.platform_adapters.comp_req_531.receipt.v1"
MANIFEST_PATH = "docs/validation/companion-platform-adapters-531-manifest.json"
VERIFIER_PATH = "tools/verify_companion_platform_integration_fresh.py"
VALIDATOR_PATH = "tools/verify_companion_platform_adapters_505_receipt.py"
NEGATIVE_NAMES = (
    "wrong_evidence_head", "zero_verifier_blob", "changed_verifier_blob",
    "unbound_copied_path", "changed_run_byte", "changed_source_blob",
    "changed_manifest_blob", "changed_validator_blob", "malformed_receipt",
    "parser_bypass_invalid_payload", "host_failure", "side_effect", "opened_gate",
)
TRACE = (
    "settings-abi sizeof=10 payload_a=10 payload_b=10 parse_a=0 parse_b=0",
    "legacy-collision a=3439285753 b=3439285753 opdiff=1 keydiff=1",
    "after-collision callbacks=2 mutations=2",
    "ordered_trace=begin>callback>mutation>readback>terminal",
)
ROOT = Path(__file__).resolve().parents[1]


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest().upper()


def digest(path):
    return digest_bytes(path.read_bytes())


def blob(commit, path):
    r = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        raise ValueError(f"missing git blob: {commit}:{path}")
    return r.stdout


def file_record(path):
    data = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(data), "sha256": digest_bytes(data)}


def run_files(root):
    return [file_record(p) for p in sorted(root.iterdir()) if p.is_file()]


def relative_file_map(run):
    root = Path(run["root"]).resolve()
    return {str(Path(item["path"]).resolve().relative_to(root)): item for item in run["files"]}


def expected_from_receipt(receipt):
    return {k: receipt[k] for k in (
        "evidence_head", "source_commit", "verifier_commit", "manifest_commit",
        "manifest_sha256", "verifier_blob_sha256")}


def artifact_ok(artifact, stdout, expected):
    checks = artifact.get("checks", {})
    effects = artifact.get("side_effects", {})
    gates = artifact.get("physical_gates", {})
    return (
        artifact.get("status") == "MACHINE_READY"
        and artifact.get("evidence_head") == expected["evidence_head"]
        and artifact.get("verifier_blob_sha256") == expected["verifier_blob_sha256"]
        and artifact.get("validated_source_commit") == expected["source_commit"]
        and artifact.get("verifier_commit") == expected["verifier_commit"]
        and artifact.get("manifest_commit") == expected["manifest_commit"]
        and artifact.get("manifest_sha256") == expected["manifest_sha256"]
        and artifact.get("platform_pin") == PIN
        and artifact.get("host_runner", {}).get("exit") == 0
        and checks and all(checks.values())
        and effects and all(v == 0 for v in effects.values())
        and gates and all(v == "CLOSED_NOT_AUTHORIZED" for v in gates.values())
        and all(t in stdout for t in TRACE)
    )


def validate(receipt, repo=ROOT, overrides=None, immutable=None):
    overrides = overrides or {}
    expected_receipt = immutable if immutable is not None else receipt
    try:
        if receipt.get("schema") != SCHEMA or expected_receipt.get("schema") != SCHEMA:
            return False
        if receipt.get("platform_pin") != PIN or expected_receipt.get("platform_pin") != PIN:
            return False
        if immutable is not None and receipt != immutable:
            return False
        expected = expected_from_receipt(expected_receipt)
        if subprocess.run(["git", "cat-file", "-e", expected["evidence_head"]], cwd=repo).returncode != 0:
            return False
        if receipt.get("negative_contract") != list(NEGATIVE_NAMES):
            return False
        for item in expected_receipt.get("repo_blobs", []):
            data = overrides.get(("repo", item["commit"], item["path"]), blob(item["commit"], item["path"]))
            if len(data) != item["bytes"] or digest_bytes(data) != item["sha256"]:
                return False
        runs = expected_receipt.get("runs", [])
        if len(runs) != 2 or Path(runs[0]["root"]).resolve() == Path(runs[1]["root"]).resolve():
            return False
        if set(relative_file_map(runs[0])) != set(relative_file_map(runs[1])):
            return False
        for run in runs:
            for item in run["files"]:
                p = Path(item["path"])
                data = overrides.get(("file", item["path"]), p.read_bytes() if p.is_file() else None)
                if data is None or len(data) != item["bytes"] or digest_bytes(data) != item["sha256"]:
                    return False
            artifact_item = next((x for x in run["files"] if x["path"].endswith("machine-ready.json")), None)
            stdout_item = next((x for x in run["files"] if x["path"].endswith("host.stdout.txt")), None)
            if artifact_item is None or stdout_item is None:
                return False
            artifact_data = overrides.get(("file", artifact_item["path"]), Path(artifact_item["path"]).read_bytes())
            stdout_data = overrides.get(("file", stdout_item["path"]), Path(stdout_item["path"]).read_bytes())
            if not artifact_ok(json.loads(artifact_data.decode("utf-8")), stdout_data.decode("utf-8"), expected):
                return False
        for item in expected_receipt.get("build_files", []):
            p = Path(item["path"])
            data = overrides.get(("file", item["path"]), p.read_bytes() if p.is_file() else None)
            if data is None or len(data) != item["bytes"] or digest_bytes(data) != item["sha256"]:
                return False
        return True
    except (KeyError, OSError, ValueError, UnicodeError, json.JSONDecodeError):
        return False


def create(ns):
    a = Path(ns.run_a).resolve()
    b = Path(ns.run_b).resolve()
    art = json.loads((a / "machine-ready.json").read_text(encoding="utf-8"))
    art_b = json.loads((b / "machine-ready.json").read_text(encoding="utf-8"))
    if art != art_b:
        raise SystemExit("NO_GO: canonical machine-ready artifacts differ")
    source = art["validated_source_commit"]
    verifier = art["verifier_commit"]
    manifest = art["manifest_commit"]
    repo_blobs = []
    paths = [(source, p) for p in sorted(art["source_sha256"])]
    paths += [(manifest, MANIFEST_PATH), (verifier, VERIFIER_PATH), (ns.validator_commit, VALIDATOR_PATH)]
    for commit, path in paths:
        data = blob(commit, path)
        repo_blobs.append({"commit": commit, "path": path, "bytes": len(data), "sha256": digest_bytes(data)})
    build_files = []
    for path in art["build_outputs_sha256"]:
        build_files.append(file_record(ROOT / path))
    for path in [
        "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/app_ble.o",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/companion_platform_adapters.o",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/companion_product_entry_glue.o",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/companion_product_transport.o",
        "cubeide/Companion_BLE_Audio_Fixture/build/companion_product_entry_glue.o",
        "cubeide/Companion_BLE_Audio_Fixture/build/companion_product_transport.o",
    ]:
        build_files.append(file_record(ROOT / path))
    receipt = {
        "schema": SCHEMA,
        "negative_contract": list(NEGATIVE_NAMES),
        "evidence_head": art["evidence_head"],
        "source_commit": source,
        "verifier_commit": verifier,
        "verifier_blob_sha256": art["verifier_blob_sha256"],
        "manifest_commit": manifest,
        "manifest_sha256": art["manifest_sha256"],
        "validator_commit": ns.validator_commit,
        "validator_blob_sha256": digest_bytes(blob(ns.validator_commit, VALIDATOR_PATH)),
        "platform_pin": PIN,
        "repo_blobs": repo_blobs,
        "runs": [{"root": str(r), "files": run_files(r)} for r in (a, b)],
        "build_files": build_files,
        "host_trace": {"path": str((a / "host.stdout.txt").resolve()), "sha256": digest(a / "host.stdout.txt")},
        "physical_gates": art["physical_gates"],
        "side_effects": art["side_effects"],
    }
    ns.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def negatives(receipt):
    results = {}
    for name, path, value in [
        ("wrong_evidence_head", ("evidence_head",), "0" * 40),
        ("zero_verifier_blob", ("verifier_blob_sha256",), "0" * 64),
        ("changed_verifier_blob", ("verifier_blob_sha256",), "F" * 64),
        ("unbound_copied_path", ("runs", 0, "root"), "C:\\unbound-copy"),
    ]:
        m = copy.deepcopy(receipt)
        t = m
        for k in path[:-1]:
            t = t[k]
        t[path[-1]] = value
        results[name] = not validate(m, immutable=receipt)
    results["malformed_receipt"] = not validate({"schema": SCHEMA}, immutable=receipt)
    run = receipt["runs"][0]
    artifact = next(x for x in run["files"] if x["path"].endswith("machine-ready.json"))
    original = Path(artifact["path"]).read_bytes()
    changed = bytearray(original)
    changed[-2] ^= 1
    results["changed_run_byte"] = not validate(receipt, overrides={("file", artifact["path"]): bytes(changed)})
    host = next(x for x in run["files"] if x["path"].endswith("host.stdout.txt"))
    stdout = Path(host["path"]).read_bytes()
    results["parser_bypass_invalid_payload"] = not validate(
        receipt, overrides={("file", host["path"]): stdout.replace(b"legacy-collision", b"parser-bypassed")})
    for name, field, value in [
        ("host_failure", ("host_runner", "exit"), 1),
        ("side_effect", ("side_effects", "hardware"), 1),
        ("opened_gate", ("physical_gates", "hardware"), "OPEN"),
    ]:
        m = json.loads(original.decode("utf-8"))
        t = m
        for k in field[:-1]:
            t = t[k]
        t[field[-1]] = value
        results[name] = not validate(receipt, overrides={("file", artifact["path"]): json.dumps(m, sort_keys=True).encode()})
    for name, key in [("changed_source_blob", "source_commit"), ("changed_manifest_blob", "manifest_commit"), ("changed_validator_blob", "validator_commit")]:
        item = next((x for x in receipt["repo_blobs"] if x["commit"] == receipt[key]), None)
        results[name] = item is not None and not validate(
            receipt, overrides={("repo", item["commit"], item["path"]): b"tampered"})
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--run-a"); ap.add_argument("--run-b"); ap.add_argument("--validator-commit")
    ap.add_argument("--output", type=Path); ap.add_argument("--receipt", type=Path)
    ap.add_argument("--receipt-commit"); ap.add_argument("--receipt-path", default="docs/validation/companion-platform-adapters-531-receipt.json")
    ap.add_argument("--self-test", action="store_true")
    ns = ap.parse_args()
    if ns.create:
        create(ns)
        return 0
    if not ns.receipt or not ns.receipt_commit:
        raise SystemExit("NO_GO: committed receipt and commit are required")
    canonical = blob(ns.receipt_commit, ns.receipt_path)
    if ns.receipt.read_bytes() != canonical:
        raise SystemExit("NO_GO: receipt bytes differ from git show")
    receipt = json.loads(canonical.decode("utf-8"))
    ok = validate(receipt)
    neg = negatives(receipt) if ns.self_test else {}
    result = {"status": "PASS" if ok and (not ns.self_test or all(neg.values())) else "NO_GO", "baseline": ok, "negatives": neg, "receipt_sha256": digest(ns.receipt)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
