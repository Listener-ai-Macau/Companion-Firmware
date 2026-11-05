#!/usr/bin/env python3
"""Capture a local webcam photo for panel visual-evidence preflight.

This tool proves the camera capture path only. It must not be used as a real
e-paper refresh claim unless the panel evidence record is separately filled and
validated.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
import time
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_ID = "companion.pendant.panel_visual_camera_preflight.v1"


def repo_rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_summary(path: pathlib.Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_no_go(args: argparse.Namespace, summary_path: pathlib.Path, reason: str, attempts: list[dict[str, Any]]) -> int:
    summary = {
        "schema_id": SCHEMA_ID,
        "status": "NO_GO",
        "generated_at": utc_now(),
        "target": args.target,
        "claim_scope": "camera_capture_preflight_only_no_panel_refresh",
        "panel_gate_must_remain": "DEFERRED_HARDWARE",
        "reason": reason,
        "attempts": attempts,
    }
    write_summary(summary_path, summary)
    print(f"NO_GO: {reason} -> {repo_rel(summary_path)}")
    return 2


def import_cv2() -> Any:
    try:
        import cv2  # type: ignore

        return cv2
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(f"OpenCV unavailable: {type(exc).__name__}: {exc}") from exc


def capture_frame(
    cv2: Any,
    camera_index: int,
    backend: int,
    warmup_frames: int,
    warmup_delay_ms: int,
) -> tuple[bool, Any, str]:
    cap = cv2.VideoCapture(camera_index, backend)
    if not cap.isOpened():
        cap.release()
        return False, None, "not_opened"

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    frame = None
    ok = False
    for _ in range(max(1, warmup_frames)):
        ok, frame = cap.read()
        if not ok:
            break
        if warmup_delay_ms > 0:
            time.sleep(warmup_delay_ms / 1000.0)
    cap.release()

    if not ok or frame is None:
        return False, None, "read_failed"
    return True, frame, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-root", type=pathlib.Path, default=None)
    parser.add_argument("--target", choices=("WB55", "WBA55", "WBA65"), default="WB55")
    parser.add_argument("--camera-index", type=int, default=None)
    parser.add_argument("--max-index", type=int, default=4)
    parser.add_argument("--warmup-frames", type=int, default=8)
    parser.add_argument("--warmup-delay-ms", type=int, default=30)
    parser.add_argument("--image-name", default="camera_preflight.jpg")
    parser.add_argument("--summary-name", default="camera_preflight.json")
    parser.add_argument("--min-width", type=int, default=320)
    parser.add_argument("--min-height", type=int, default=240)
    parser.add_argument("--min-mean-luma", type=float, default=2.0)
    parser.add_argument("--min-std-luma", type=float, default=1.0)
    args = parser.parse_args()

    if args.session_root is None:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        args.session_root = REPO_ROOT / ".cache" / "validation" / f"companion-panel-visual-camera-preflight-{stamp}"

    session_root = args.session_root
    visual_dir = session_root / "visual"
    visual_dir.mkdir(parents=True, exist_ok=True)
    output_path = visual_dir / args.image_name
    summary_path = visual_dir / args.summary_name

    attempts: list[dict[str, Any]] = []
    try:
        cv2 = import_cv2()
    except RuntimeError as exc:
        return make_no_go(args, summary_path, str(exc), attempts)

    backends = []
    if hasattr(cv2, "CAP_DSHOW"):
        backends.append(("CAP_DSHOW", cv2.CAP_DSHOW))
    if hasattr(cv2, "CAP_MSMF"):
        backends.append(("CAP_MSMF", cv2.CAP_MSMF))
    backends.append(("CAP_ANY", cv2.CAP_ANY))

    camera_indexes = [args.camera_index] if args.camera_index is not None else list(range(max(0, args.max_index) + 1))

    selected: dict[str, Any] | None = None
    selected_frame = None
    for index in camera_indexes:
        for backend_name, backend in backends:
            ok, frame, reason = capture_frame(
                cv2,
                int(index),
                int(backend),
                args.warmup_frames,
                max(0, args.warmup_delay_ms),
            )
            attempt = {
                "camera_index": int(index),
                "backend": backend_name,
                "opened_and_read": bool(ok),
                "reason": reason,
            }
            attempts.append(attempt)
            if ok:
                selected = attempt
                selected_frame = frame
                break
        if selected is not None:
            break

    if selected is None or selected_frame is None:
        return make_no_go(args, summary_path, "no_camera_frame_captured", attempts)

    height, width = selected_frame.shape[:2]
    gray = cv2.cvtColor(selected_frame, cv2.COLOR_BGR2GRAY)
    mean_luma = float(gray.mean())
    std_luma = float(gray.std())
    checks = {
        "min_width": width >= args.min_width,
        "min_height": height >= args.min_height,
        "min_mean_luma": mean_luma >= args.min_mean_luma,
        "min_std_luma": std_luma >= args.min_std_luma,
    }

    if not all(checks.values()):
        return make_no_go(
            args,
            summary_path,
            "captured_frame_failed_quality_checks",
            attempts
            + [
                {
                    "frame_width": width,
                    "frame_height": height,
                    "mean_luma": round(mean_luma, 3),
                    "std_luma": round(std_luma, 3),
                    "checks": checks,
                }
            ],
        )

    if not cv2.imwrite(str(output_path), selected_frame):
        return make_no_go(args, summary_path, "failed_to_write_image", attempts)

    size_bytes = output_path.stat().st_size
    summary = {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "generated_at": utc_now(),
        "target": args.target,
        "claim_scope": "camera_capture_preflight_only_no_panel_refresh",
        "panel_gate_must_remain": "DEFERRED_HARDWARE",
        "session_root": repo_rel(session_root),
        "visual_dir": repo_rel(visual_dir),
        "image_path": repo_rel(output_path),
        "image_sha256": sha256_file(output_path),
        "image_size_bytes": size_bytes,
        "frame_width": width,
        "frame_height": height,
        "mean_luma": round(mean_luma, 3),
        "std_luma": round(std_luma, 3),
        "checks": checks,
        "selected_camera": selected,
        "attempts": attempts,
        "next_use": "copy or replace this preflight image with before/during/after real panel photos during hardware acceptance",
    }
    write_summary(summary_path, summary)
    print(f"PASS: camera visual preflight -> {repo_rel(summary_path)}")
    print(f"image={repo_rel(output_path)} sha256={summary['image_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
