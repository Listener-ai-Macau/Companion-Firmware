#!/usr/bin/env python3
"""Stage a generated expression storyboard without changing the active CEMP pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw, ImageOps


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_LAYOUT = ROOT / "docs/art/iterations/companion-pet-interaction-v1/storyboard-import-v3.json"
DEFAULT_OUT_DIR = ROOT / ".cache/validation/generated-expression-storyboard-v3/pbm"
DEFAULT_REPORT = ROOT / ".cache/validation/generated-expression-storyboard-v3/import-report.json"
DEFAULT_PREVIEW = ROOT / ".cache/validation/generated-expression-storyboard-v3/review.png"


@dataclass(frozen=True)
class Profile:
    width: int
    height: int
    asset_suffix: str
    max_face_width: int
    max_face_height: int
    top_inset_px: int


@dataclass(frozen=True)
class Crop:
    width_ratio: float
    height_ratio: float
    row_center_y: tuple[float, ...]


@dataclass(frozen=True)
class Quality:
    threshold: int
    min_ink_pixels: int
    max_ink_pixels: int
    require_edge_clear: bool


@dataclass(frozen=True)
class Cell:
    state_id: str
    row: int
    column: int
    asset_file: str


@dataclass(frozen=True)
class Layout:
    path: pathlib.Path
    iteration_id: str
    source: pathlib.Path
    source_sha256: str
    profile: Profile
    columns: int
    rows: int
    crop: Crop
    quality: Quality
    cells: tuple[Cell, ...]


def relative(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require_int(value: object, name: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def require_ratio(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 < float(value) < 1.0:
        raise ValueError(f"{name} must be a number in (0, 1)")
    return float(value)


def require_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def require_relative_file(value: object, name: str) -> pathlib.Path:
    text = require_string(value, name)
    path = pathlib.PurePosixPath(text.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or path.name != text.replace("\\", "/").split("/")[-1]:
        raise ValueError(f"{name} must be a simple relative filename")
    return pathlib.Path(path.name)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_layout(path: pathlib.Path) -> Layout:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "companion.expression_storyboard_import_layout.v1":
        raise ValueError("unsupported storyboard import layout schema")
    iteration_id = require_string(data.get("iteration_id"), "iteration_id")
    source_text = require_string(data.get("source"), "source")
    source_path = (ROOT / source_text).resolve()
    if not source_path.is_file() or ROOT not in source_path.parents:
        raise ValueError("source must resolve to a repository file")
    source_sha256 = require_string(data.get("source_sha256"), "source_sha256").lower()
    if len(source_sha256) != 64 or any(char not in "0123456789abcdef" for char in source_sha256):
        raise ValueError("source_sha256 must be a lowercase SHA-256 hex string")

    profile_data = data.get("profile")
    if not isinstance(profile_data, dict):
        raise ValueError("profile must be an object")
    profile = Profile(
        width=require_int(profile_data.get("width"), "profile.width", 1, 4096),
        height=require_int(profile_data.get("height"), "profile.height", 1, 4096),
        asset_suffix=require_string(profile_data.get("asset_suffix"), "profile.asset_suffix"),
        max_face_width=require_int(profile_data.get("max_face_width"), "profile.max_face_width", 1, 4096),
        max_face_height=require_int(profile_data.get("max_face_height"), "profile.max_face_height", 1, 4096),
        top_inset_px=require_int(profile_data.get("top_inset_px"), "profile.top_inset_px", 0, 4095),
    )
    if profile.max_face_width > profile.width or profile.max_face_height > profile.height:
        raise ValueError("profile face bounds must fit the canvas")

    grid_data = data.get("grid")
    if not isinstance(grid_data, dict):
        raise ValueError("grid must be an object")
    columns = require_int(grid_data.get("columns"), "grid.columns", 1, 16)
    rows = require_int(grid_data.get("rows"), "grid.rows", 1, 16)

    crop_data = data.get("crop")
    if not isinstance(crop_data, dict):
        raise ValueError("crop must be an object")
    centers = crop_data.get("row_center_y")
    if not isinstance(centers, list) or len(centers) != rows:
        raise ValueError("crop.row_center_y must provide one normalized center per row")
    crop = Crop(
        width_ratio=require_ratio(crop_data.get("width_ratio"), "crop.width_ratio"),
        height_ratio=require_ratio(crop_data.get("height_ratio"), "crop.height_ratio"),
        row_center_y=tuple(require_ratio(value, "crop.row_center_y") for value in centers),
    )

    quality_data = data.get("quality")
    if not isinstance(quality_data, dict):
        raise ValueError("quality must be an object")
    quality = Quality(
        threshold=require_int(quality_data.get("threshold"), "quality.threshold", 1, 254),
        min_ink_pixels=require_int(quality_data.get("min_ink_pixels"), "quality.min_ink_pixels", 1, 40000),
        max_ink_pixels=require_int(quality_data.get("max_ink_pixels"), "quality.max_ink_pixels", 1, 40000),
        require_edge_clear=quality_data.get("require_edge_clear") is True,
    )
    if quality.min_ink_pixels > quality.max_ink_pixels:
        raise ValueError("quality ink bounds are inverted")

    raw_cells = data.get("cells")
    if not isinstance(raw_cells, list) or len(raw_cells) != columns * rows:
        raise ValueError("cells must describe every grid position exactly once")
    cells: list[Cell] = []
    state_ids: set[str] = set()
    asset_files: set[pathlib.Path] = set()
    positions: set[tuple[int, int]] = set()
    for index, raw_cell in enumerate(raw_cells):
        if not isinstance(raw_cell, dict):
            raise ValueError(f"cells[{index}] must be an object")
        cell = Cell(
            state_id=require_string(raw_cell.get("state_id"), f"cells[{index}].state_id"),
            row=require_int(raw_cell.get("row"), f"cells[{index}].row", 0, rows - 1),
            column=require_int(raw_cell.get("column"), f"cells[{index}].column", 0, columns - 1),
            asset_file=require_relative_file(raw_cell.get("asset_file"), f"cells[{index}].asset_file").as_posix(),
        )
        if not cell.asset_file.endswith(".pbm"):
            raise ValueError(f"cells[{index}].asset_file must use .pbm")
        position = (cell.row, cell.column)
        if cell.state_id in state_ids or pathlib.Path(cell.asset_file) in asset_files or position in positions:
            raise ValueError("cell state IDs, output files, and positions must be unique")
        state_ids.add(cell.state_id)
        asset_files.add(pathlib.Path(cell.asset_file))
        positions.add(position)
        cells.append(cell)
    return Layout(path.resolve(), iteration_id, source_path, source_sha256, profile, columns, rows, crop, quality, tuple(cells))


def crop_box(source: Image.Image, layout: Layout, cell: Cell) -> tuple[int, int, int, int]:
    width, height = source.size
    center_x = width * ((cell.column + 0.5) / layout.columns)
    center_y = height * layout.crop.row_center_y[cell.row]
    crop_width = width * layout.crop.width_ratio
    crop_height = height * layout.crop.height_ratio
    left = max(0, round(center_x - crop_width / 2))
    top = max(0, round(center_y - crop_height / 2))
    right = min(width, round(center_x + crop_width / 2))
    bottom = min(height, round(center_y + crop_height / 2))
    if left >= right or top >= bottom:
        raise ValueError(f"invalid crop box for {cell.state_id}")
    return (left, top, right, bottom)


def render_cell(source: Image.Image, layout: Layout, cell: Cell) -> tuple[Image.Image, Image.Image]:
    crop = ImageOps.autocontrast(source.crop(crop_box(source, layout, cell)))
    crop.thumbnail(
        (layout.profile.max_face_width, layout.profile.max_face_height),
        Image.Resampling.LANCZOS,
    )
    reference = Image.new("L", (layout.profile.width, layout.profile.height), 255)
    reference.paste(crop, ((layout.profile.width - crop.width) // 2, layout.profile.top_inset_px))
    bitmap = reference.point(lambda pixel: 0 if pixel < layout.quality.threshold else 255, "1")
    return reference, bitmap


def black_metrics(image: Image.Image) -> tuple[int, tuple[int, int, int, int] | None, int]:
    bitmap = image.convert("1")
    pixels = bitmap.load()
    xs: list[int] = []
    ys: list[int] = []
    edge_ink = 0
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            if pixels[x, y] == 0:
                xs.append(x)
                ys.append(y)
                if x == 0 or y == 0 or x == bitmap.width - 1 or y == bitmap.height - 1:
                    edge_ink += 1
    if not xs:
        return 0, None, edge_ink
    return len(xs), (min(xs), min(ys), max(xs), max(ys)), edge_ink


def quality_result(image: Image.Image, layout: Layout, cell: Cell, source: Image.Image) -> dict[str, Any]:
    ink, bbox, edge_ink = black_metrics(image)
    checks = {
        "visible_ink": ink >= layout.quality.min_ink_pixels,
        "not_overfilled": ink <= layout.quality.max_ink_pixels,
        "edge_clear": not layout.quality.require_edge_clear or edge_ink == 0,
    }
    return {
        "state_id": cell.state_id,
        "asset_file": cell.asset_file,
        "source_crop_box": list(crop_box(source, layout, cell)),
        "ink_pixels": ink,
        "ink_bbox": list(bbox) if bbox is not None else None,
        "edge_ink_pixels": edge_ink,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def build_review(frames: list[tuple[Cell, Image.Image, Image.Image]], layout: Layout, output: pathlib.Path) -> str:
    cell_width = 260
    cell_height = 250
    review = Image.new("RGB", (cell_width * layout.columns, cell_height * layout.rows), "white")
    draw = ImageDraw.Draw(review)
    for cell, reference, bitmap in frames:
        left = cell.column * cell_width
        top = cell.row * cell_height
        scale = min(102 / layout.profile.width, 102 / layout.profile.height)
        size = (max(1, round(layout.profile.width * scale)), max(1, round(layout.profile.height * scale)))
        ref_thumb = reference.convert("RGB").resize(size, Image.Resampling.LANCZOS)
        pbm_thumb = bitmap.convert("RGB").resize(size, Image.Resampling.NEAREST)
        ref_x = left + 12 + (108 - ref_thumb.width) // 2
        pbm_x = left + 140 + (108 - pbm_thumb.width) // 2
        ref_y = top + 30 + (108 - ref_thumb.height) // 2
        pbm_y = top + 30 + (108 - pbm_thumb.height) // 2
        review.paste(ref_thumb, (ref_x, ref_y))
        review.paste(pbm_thumb, (pbm_x, pbm_y))
        draw.rectangle((left + 12, top + 30, left + 119, top + 137), outline="black")
        draw.rectangle((left + 140, top + 30, left + 247, top + 137), outline="black")
        draw.text((left + 47, top + 10), "REF", fill="black")
        draw.text((left + 174, top + 10), "PBM", fill="black")
        draw.text((left + 12, top + 157), cell.state_id.upper(), fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    review.save(output)
    return relative(output)


def stage(layout: Layout, out_dir: pathlib.Path, preview: pathlib.Path) -> dict[str, Any]:
    source_hash = sha256(layout.source)
    if source_hash != layout.source_sha256:
        raise ValueError("source SHA-256 differs from the layout record")
    source = Image.open(layout.source).convert("L")
    frames: list[tuple[Cell, Image.Image, Image.Image]] = []
    metrics: list[dict[str, Any]] = []
    outputs: list[str] = []
    for cell in layout.cells:
        reference, bitmap = render_cell(source, layout, cell)
        destination = out_dir / cell.asset_file
        destination.parent.mkdir(parents=True, exist_ok=True)
        bitmap.save(destination)
        frames.append((cell, reference, bitmap))
        metrics.append(quality_result(bitmap, layout, cell, source))
        outputs.append(relative(destination))
    status = "PASS" if all(metric["status"] == "PASS" for metric in metrics) else "FAIL"
    return {
        "schema": "companion.generated_expression_storyboard_import.v1",
        "status": status,
        "candidate_only": True,
        "cemp_manifest_changed": False,
        "iteration_id": layout.iteration_id,
        "layout": relative(layout.path),
        "source": relative(layout.source),
        "source_sha256": source_hash,
        "source_size": {"width": source.width, "height": source.height},
        "profile": {
            "width": layout.profile.width,
            "height": layout.profile.height,
            "asset_suffix": layout.profile.asset_suffix,
        },
        "review_rule": "Compare every REF/PBM pair with the generated sheet before accepting a CEMP import; do not activate candidate art based only on this machine report.",
        "outputs": outputs,
        "quality": metrics,
        "review_preview": build_review(frames, layout, preview),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=pathlib.Path, default=DEFAULT_LAYOUT)
    parser.add_argument("--out-dir", type=pathlib.Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--preview", type=pathlib.Path, default=DEFAULT_PREVIEW)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        layout = parse_layout(args.layout.resolve())
        report = stage(layout, args.out_dir.resolve(), args.preview.resolve())
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: staged {len(report['outputs'])} candidate storyboard frames")
    print(f"REPORT: {relative(args.report)}")
    print(f"REVIEW: {report['review_preview']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
