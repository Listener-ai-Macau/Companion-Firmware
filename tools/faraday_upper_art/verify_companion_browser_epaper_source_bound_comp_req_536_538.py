#!/usr/bin/env python3
"""Source-bound offline gate for the COMP-REQ-536/537/538 browser successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


SOURCE_COMMIT = "c7e8403cd6744cff135679010ddf9d7e5f0471af"
PAGE_SHA256 = "6176B9B3A7948291F430B5C47EBB5CDB2DA339BEEA86FBD1C72920D74438DD10"
PAGE_PATH = (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
VALIDATION_DIR = (
    "docs/validation/"
    "companion-browser-epaper-parity-successor-comp-req-536-538"
)
EXPORT_DIR = "docs/art/exports/companion-browser-epaper-parity-comp-req-536-538"

# Text identities are canonical LF SHA-256 plus the committed Git blob. Binary
# identities use their byte SHA-256 plus the committed Git blob.
BOUND_FILES = {
    "page": (
        PAGE_PATH,
        PAGE_SHA256,
        "8352264ac8a1359f1c0650f07589e76da1999665",
        True,
    ),
    "focused_tool": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_epaper_accessory_comp_req_536_538.mjs",
        "1C527DAEEF5356670C18FA698B0B3F379FDCC05AC3856CE2B894B9FB51637C1D",
        "fc79959a833b822fd111a3d84b19e95116307798",
        True,
    ),
    "generator": (
        "tools/faraday_upper_art/"
        "generate_companion_browser_epaper_parity_comp_req_536_538.mjs",
        "7083B353A91A3548BA7ACAED231119FB29F59DEEEDFFE4A7CBCDB321EB0E9599",
        "89d744583ef218b92ff216520e7741adae0e2be8",
        True,
    ),
    "replay_tool": (
        "tools/faraday_upper_art/"
        "replay_companion_browser_epaper_accessory_comp_req_536_538.mjs",
        "A63A2F90F4A3A48F37484B3D96CB4AC3FDCF49913CB4FB4AE62B2C5B73DB204F",
        "d98be80640cfbe8a1c75aec708e654ab50923d73",
        True,
    ),
    "parity_tool": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_epaper_parity_comp_req_536_538.py",
        "DBCA696ECC134545CB5627362F5E07B5801810A52496C33C1A48E4EA75F8D683",
        "986628d3a2399f6262972594d2bed72a500d1ad7",
        True,
    ),
    "focused": (
        f"{VALIDATION_DIR}/focused-oracle.json",
        "6F3E806C4703E677DE9E2D108F8D3241546D87D41D05D099731A89BCD1603271",
        "31eb2cdb8f3b28c38efbc7a18ce7381d43c3052c",
        True,
    ),
    "replay": (
        f"{VALIDATION_DIR}/replay-run/browser-replay-result.json",
        "4108424DA67141EA31F7755CF3974CA982093B1D7B1FEE8A8263B25B9CDD5B26",
        "87a035125d16411175f10e1dbf4754db0fee561e",
        True,
    ),
    "pixel": (
        f"{VALIDATION_DIR}/replay-run/pixel-dom-route-artifact.json",
        "C44BB53F2D07BE61D5EE27521E9237412EC1CFADCFEE57D6C9ED3636BEBBBE2F",
        "d7cb8e8bd98ff7c19220abcd559c77d7393c3c7f",
        True,
    ),
    "screenshots": (
        f"{VALIDATION_DIR}/replay-run/screenshot-manifest.json",
        "81C10D5E17A633AC8F2411C82658C3A05F60963BDDBB36D592DADE19C901512C",
        "8381c449e4256a40a97537305eb6bbae83b8e3eb",
        True,
    ),
    "parity": (
        f"{VALIDATION_DIR}/parity-verifier.json",
        "D8CDA1082AC334FB4CEABB097D52EF8D6EFB9374455A8369A6720A848DC2EACB",
        "09738ff0da616d4b6095aa442ca57c7ea8e28630",
        True,
    ),
    "manifest": (
        f"{EXPORT_DIR}/visual-frame-manifest.json",
        "198ED5AFBA59F06BE507E0BC6C1778363DB1E401AF17A8859A2A3D0665DB36DB",
        "a7d5dfb990d5aa864e9bf546bada5b4b7ddcb2ce",
        True,
    ),
    "frames": (
        f"{EXPORT_DIR}/frames.bin",
        "27226B06DDDB5C3614A0575738344CE1DB45CC60C90BE5FA8F32A7EB891DF514",
        "6be109225a5bafff958999aa38fce5574cfee233",
        False,
    ),
    "c_pack": (
        f"{EXPORT_DIR}/companion_browser_epaper_visual_pack.c",
        "BAC08B23D336AEC7E06EFD3BF4C9A82F836433791336486AB9C30CA8E0680E3F",
        "7243e261e1442c323864d71af64cbae5fb16f30d",
        True,
    ),
    "h_pack": (
        f"{EXPORT_DIR}/companion_browser_epaper_visual_pack.h",
        "26073FA87A70E05ECA9EE7146A2656536DE4ECD7BF212A562607820580164CFE",
        "f619712d2e07b4d222a0222c3989cef0a8f8c0dd",
        True,
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_lf(data: bytes) -> bytes:
    normalized = data.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise ValueError("bare carriage return")
    return normalized


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def git_text(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip() if result.returncode == 0 else None


def read(
    root: Path,
    relative: str,
    overlay: dict[str, bytes] | None,
) -> bytes:
    key = relative.replace("\\", "/")
    if overlay is not None and key in overlay:
        return overlay[key]
    return (root / key).read_bytes()


def load_json(
    failures: list[str],
    label: str,
    data: bytes,
) -> dict[str, Any] | None:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}: invalid JSON ({type(exc).__name__})")
        return None
    if not isinstance(value, dict):
        failures.append(f"{label}: root must be an object")
        return None
    return value


def require(
    failures: list[str],
    label: str,
    observed: Any,
    expected: Any,
) -> None:
    if observed != expected:
        failures.append(f"{label}: expected {expected!r}, observed {observed!r}")


def evaluate(
    root: Path,
    *,
    overlay: dict[str, bytes] | None = None,
    source_commit: str = SOURCE_COMMIT,
) -> dict[str, Any]:
    failures: list[str] = []
    identities: list[dict[str, Any]] = []
    exact_commit = git_text(root, "rev-parse", f"{source_commit}^{{commit}}")
    require(failures, "source commit", exact_commit, SOURCE_COMMIT)
    if exact_commit == SOURCE_COMMIT:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", SOURCE_COMMIT, "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
        ).returncode
        require(failures, "source commit ancestry", ancestor, 0)

    for name, (relative, expected_sha, expected_blob, is_text) in BOUND_FILES.items():
        try:
            checkout = read(root, relative, overlay)
            identity = canonical_lf(checkout) if is_text else checkout
            observed_sha = sha256(identity)
        except (OSError, ValueError) as exc:
            failures.append(f"{name}: unreadable ({type(exc).__name__})")
            continue
        observed_blob = git_text(root, "rev-parse", f"{SOURCE_COMMIT}:{relative}")
        if overlay is None:
            worktree_blob = git_text(
                root, "hash-object", "--path", relative, relative
            )
        else:
            worktree_blob = "overlay"
        require(failures, f"{name} sha", observed_sha, expected_sha)
        require(failures, f"{name} committed blob", observed_blob, expected_blob)
        if overlay is None:
            require(failures, f"{name} worktree blob", worktree_blob, expected_blob)
        identities.append(
            {
                "canonical_lf": is_text,
                "git_blob": observed_blob,
                "id": name,
                "path": relative,
                "sha256": observed_sha,
            }
        )

    def artifact(name: str) -> dict[str, Any] | None:
        relative = BOUND_FILES[name][0]
        try:
            return load_json(failures, name, read(root, relative, overlay))
        except OSError as exc:
            failures.append(f"{name}: unreadable ({type(exc).__name__})")
            return None

    focused = artifact("focused")
    replay = artifact("replay")
    pixel = artifact("pixel")
    screenshots = artifact("screenshots")
    parity = artifact("parity")
    manifest = artifact("manifest")

    if focused:
        require(failures, "focused status", focused.get("status"), "PASS")
        require(failures, "focused failed", focused.get("failed"), [])
        checks = focused.get("checks", {})
        require(failures, "focused all checks", all(checks.values()), True)
        require(
            failures,
            "focused page identity",
            focused.get("inputs", {}).get("page_canonical_sha256"),
            PAGE_SHA256,
        )
        idle = focused.get("observed", {}).get("idle", {})
        require(failures, "idle cadence", idle.get("cadence_ms"), 480)
        require(failures, "idle run count", len(idle.get("runs", [])), 2)
        waves = focused.get("observed", {}).get("waves", [])
        require(failures, "wave committed states", len(waves), 4)
        for index, wave in enumerate(waves):
            arcs = wave.get("arcs", [])
            require(failures, f"wave {index} count", len(arcs), 3)
            geometry = {
                (
                    arc.get("geometry", {}).get("height"),
                    arc.get("geometry", {}).get("width"),
                    arc.get("geometry", {}).get("stroke"),
                )
                for arc in arcs
            }
            require(failures, f"wave {index} equal geometry", geometry, {(13, 6, 2)})
            require(failures, f"wave {index} gray", wave.get("gray_pixels"), 0)
        require(
            failures,
            "focused side effects",
            set(focused.get("side_effects", {}).values()),
            {0},
        )

    if replay:
        require(failures, "replay status", replay.get("status"), "PASS")
        require(failures, "replay failed", replay.get("failed"), [])
        require(
            failures,
            "replay page identity",
            replay.get("inputs", {}).get("page_canonical_sha256"),
            PAGE_SHA256,
        )
        counts = replay.get("counts", {})
        for key, expected in {
            "combinations": 6,
            "scenarios": 42,
            "screenshots": 12,
            "errors": 0,
            "microphone_requests": 0,
        }.items():
            require(failures, f"replay {key}", counts.get(key), expected)
        expected_scenarios = {
            "single_tap",
            "drag_replacement",
            "double_tap_entry",
            "recording_single_tap",
            "recording_drag",
            "recording_menu_return",
            "accessory_only_exit",
        }
        rows = replay.get("scenarios", [])
        require(
            failures,
            "replay scenario vocabulary",
            {row.get("name") for row in rows},
            expected_scenarios,
        )
        require(
            failures,
            "replay scenario pass count",
            sum(row.get("pass") is True for row in rows),
            42,
        )
        require(
            failures,
            "replay side effects",
            set(replay.get("side_effects", {}).values()),
            {0},
        )

    if pixel:
        require(failures, "pixel status", pixel.get("status"), "PASS")
        require(failures, "pixel scenarios", pixel.get("scenario_count"), 42)
        require(
            failures,
            "pixel invariants",
            pixel.get("invariants"),
            {
                "accessory_only_exit": True,
                "recording_is_orthogonal": True,
                "single_face_single_gaze": True,
            },
        )

    if screenshots:
        require(failures, "screenshot status", screenshots.get("status"), "PASS")
        rows = screenshots.get("screenshots", [])
        require(failures, "screenshot count", screenshots.get("count"), 12)
        require(failures, "screenshot rows", len(rows), 12)
        for row in rows:
            relative = row.get("path", "")
            try:
                observed = sha256(read(root, relative, overlay))
            except OSError:
                observed = None
            require(
                failures,
                f"screenshot bytes {relative}",
                observed,
                row.get("sha256"),
            )

    if parity:
        require(failures, "parity status", parity.get("status"), "PASS")
        require(failures, "parity failed", parity.get("failed"), [])
        require(
            failures,
            "parity all checks",
            all(parity.get("checks", {}).values()),
            True,
        )
        require(
            failures,
            "parity page identity",
            parity.get("inputs", {}).get("page_canonical_sha256"),
            PAGE_SHA256,
        )
        require(
            failures,
            "parity state count",
            parity.get("observed", {}).get("state_count"),
            71,
        )

    if manifest:
        require(failures, "manifest status", manifest.get("status"), "PASS")
        invariants = manifest.get("invariants", {})
        for key, expected in {
            "state_count": 71,
            "unique_frame_count": 55,
            "emotion_count": 10,
            "recording_composed_emotion_count": 10,
            "cadence_ms": 480,
            "browser_to_c_pixel_diff": 0,
            "default_off": True,
            "device_transform": "identity",
        }.items():
            require(failures, f"manifest {key}", invariants.get(key), expected)
        format_row = manifest.get("format", {})
        require(
            failures,
            "manifest format",
            {
                key: format_row.get(key)
                for key in (
                    "width",
                    "height",
                    "row_stride_bytes",
                    "bits_per_pixel",
                    "black_bit",
                    "white_bit",
                )
            },
            {
                "width": 200,
                "height": 200,
                "row_stride_bytes": 25,
                "bits_per_pixel": 1,
                "black_bit": 1,
                "white_bit": 0,
            },
        )
        states = manifest.get("states", [])
        require(failures, "manifest state rows", len(states), 71)
        for state in states:
            relative = f"{EXPORT_DIR}/{state.get('pbm_file', '')}"
            try:
                observed = sha256(read(root, relative, overlay))
            except OSError:
                observed = None
            require(
                failures,
                f"PBM bytes {state.get('id')}",
                observed,
                state.get("pbm_sha256"),
            )
            require(
                failures,
                f"state pixel diff {state.get('id')}",
                state.get("pixel_diff_after_registered_transform"),
                0,
            )
        for key, relative_name in {
            "frames": "frames.bin",
            "c": "companion_browser_epaper_visual_pack.c",
            "h": "companion_browser_epaper_visual_pack.h",
        }.items():
            file_row = manifest.get("files", {}).get(key, {})
            relative = f"{EXPORT_DIR}/{relative_name}"
            try:
                observed = sha256(
                    canonical_lf(read(root, relative, overlay))
                    if key != "frames"
                    else read(root, relative, overlay)
                )
            except (OSError, ValueError):
                observed = None
            require(failures, f"manifest file {key}", observed, file_row.get("sha256"))

    result = {
        "schema": "companion.browser-epaper-source-bound-machine-ready.v1",
        "requirements": ["COMP-REQ-521", "COMP-REQ-536", "COMP-REQ-537", "COMP-REQ-538"],
        "status": "MACHINE_READY" if not failures else "NO_GO",
        "source_commit": SOURCE_COMMIT,
        "page_canonical_sha256": PAGE_SHA256,
        "identities": identities,
        "checks": {
            "focused_smoke": focused is not None,
            "full_replay_6x7": replay is not None,
            "pixel_dom_route": pixel is not None,
            "screenshots": screenshots is not None,
            "browser_pbm_c_parity": parity is not None and manifest is not None,
            "source_and_git_blob_bound": not any(
                "sha:" in failure or "blob:" in failure for failure in failures
            ),
        },
        "failed_checks": failures,
        "side_effects": {
            "browser": 0,
            "hardware": 0,
            "microphone_request": 0,
            "owner_prompt": 0,
            "production_write": 0,
            "server": 0,
        },
        "owner_gate": "PENDING",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-commit", default=SOURCE_COMMIT)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    result = evaluate(root, source_commit=args.source_commit)
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(result))
    print(
        json.dumps(
            {
                "failed": len(result["failed_checks"]),
                "output": output.relative_to(root).as_posix(),
                "sha256": sha256(output.read_bytes()),
                "status": result["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
