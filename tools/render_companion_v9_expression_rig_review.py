#!/usr/bin/env python3
"""Build the v9 expression Rig owner review artifact.

This compatibility entry point deliberately delegates to the component-layer
dynamic preview.  The former static state-matrix review is retained only as a
machine audit image and must not be written as the owner-facing review page.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from render_companion_v9_expression_rig_dynamic_preview import (  # noqa: E402
    render as render_dynamic_preview,
)
from verify_companion_v9_expression_rig_dynamic_preview import (  # noqa: E402
    DEFAULT_ACCEPTED_BASELINE,
    verify as verify_dynamic_preview,
)


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: pathlib.Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render(report_path: pathlib.Path, *, dynamic_preview_report_path: pathlib.Path,
           distance_report_path: pathlib.Path, render_report_path: pathlib.Path,
           cemp_report_path: pathlib.Path, choreographer_report_path: pathlib.Path,
           artifact_root: pathlib.Path, accepted_baseline_path: pathlib.Path,
           scope: str) -> dict[str, object]:
    dynamic = render_dynamic_preview(
        dynamic_preview_report_path,
        scope,
        render_report_path=render_report_path,
        cemp_report_path=cemp_report_path,
        choreographer_report_path=choreographer_report_path,
        artifact_root=artifact_root,
    )
    distance = verify_dynamic_preview(dynamic_preview_report_path, render_report_path,
                                      accepted_baseline_path)
    write_json(distance_report_path, distance)
    if distance.get("status") != "PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT":
        raise ValueError(f"dynamic preview-distance gate failed: {distance.get('errors')}")

    result = {
        "schema": "companion.v9_expression_rig_review_readiness.v2",
        "status": "PASS_DYNAMIC_REVIEW_READY",
        "review_page": dynamic["owner_review_page"],
        "review_page_sha256": dynamic["owner_review_page_sha256"],
        "dynamic_player": dynamic["review_page"],
        "dynamic_player_sha256": dynamic["review_page_sha256"],
        "animated_preview": dynamic["animated_preview"],
        "animated_preview_sha256": dynamic["animated_preview_sha256"],
        "keyframe_strip": dynamic["keyframe_strip"],
        "keyframe_strip_sha256": dynamic["keyframe_strip_sha256"],
        "component_layer_dir": dynamic["component_layer_dir"],
        "component_layer_count": dynamic["component_layer_count"],
        "dynamic_groups": dynamic["dynamic_groups"],
        "preview_distance_report": rel(distance_report_path),
        "preview_distance_status": distance["status"],
        "source_sha256": dynamic["source_sha256"],
        "runtime_resource_activated": False,
        "physical_epaper_acceptance": False,
        "legacy_static_matrix_owner_review": "rejected_by_COMP_REQ_095",
        "operator_prompt_prerequisite": "Open review_page before launching operator-prompt.",
    }
    write_json(report_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, required=True)
    parser.add_argument("--dynamic-preview-report", type=pathlib.Path, required=True)
    parser.add_argument("--distance-report", type=pathlib.Path, required=True)
    parser.add_argument("--render-report", type=pathlib.Path, required=True)
    parser.add_argument("--cemp-report", type=pathlib.Path, required=True)
    parser.add_argument("--choreographer-report", type=pathlib.Path, required=True)
    parser.add_argument("--artifact-root", type=pathlib.Path, required=True)
    parser.add_argument("--accepted-baseline", type=pathlib.Path, default=DEFAULT_ACCEPTED_BASELINE)
    parser.add_argument("--scope", choices=("daily_focus", "daily_selected_state"), default="daily_focus")
    args = parser.parse_args()
    try:
        result = render(
            args.write.resolve(),
            dynamic_preview_report_path=args.dynamic_preview_report.resolve(),
            distance_report_path=args.distance_report.resolve(),
            render_report_path=args.render_report.resolve(),
            cemp_report_path=args.cemp_report.resolve(),
            choreographer_report_path=args.choreographer_report.resolve(),
            artifact_root=args.artifact_root.resolve(),
            accepted_baseline_path=args.accepted_baseline.resolve(),
            scope=args.scope,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"PASS: dynamic v9 Rig review page ready at {result['review_page']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
