#!/usr/bin/env python3
"""Fail-closed COMP-REQ-474/475/476/479 upper-to-lower compatibility audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import deque
from pathlib import Path
from typing import Any


DEFAULT_LOWER_COMMIT = "c692339edb3182f30e651161afdc48885cea2ef4"
LEGACY_NO_GO_COMMIT = "c1733e4e40bb3374b4ee2ec81a7057eb90a03c10"
COMP_REQ_488_DIAGNOSTIC_COMMIT = "4ddf9709034d307b333510c27e3e0a45c7ed6d15"
EXPECTED_CONVERTED_CENTERED_SHA256 = (
    "EF4CDB579CC2C43645E0E3585D8C40CA65763112619E5EB9FBC583EAF3E28DBD"
)
EXPECTED_R7_BASELINE_SHA256 = (
    "679D3E84DE949B9322D43761D09FD5301C87C4F085370D704D2A5CECA54B26D1"
)
VALIDATION_DIR = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471"
)
EXPORT_DIR = Path("docs/art/exports/companion-browser-visual-contract-comp-req-471")
DEFAULT_OUTPUT = VALIDATION_DIR / "upper-lower-compatibility-c692339.json"

MAX_SOURCE_FILES = 64
MAX_SOURCE_BYTES_EACH = 2_000_000
MAX_SOURCE_BYTES_TOTAL = 12_000_000
OUTPUT_NAME_RE = re.compile(r"upper-lower-compatibility-[A-Za-z0-9._-]+\.json")
COMMIT_RE = re.compile(r"[0-9a-fA-F]{40}")

UPPER_BINDINGS = {
    "upper_machine_ready": (
        VALIDATION_DIR / "UPPER_MACHINE_READY.json",
        "EAD7000FEB32CD7915FEAD82A49D23FD66755412AEDFA53B4B7A264CABA3BB69",
    ),
    "owner_review_scope": (
        VALIDATION_DIR / "owner-review-scope.json",
        "245B8BDB94A00A23224CF1E9A7F43CA65936CCC16518D3067D48BD98A5E61D80",
    ),
    "state_transitions": (
        EXPORT_DIR / "state-transitions.json",
        "442F5A9E87988A3F8BE15ECC2A2500CA64537FA2B6DBD96F6FFDDD070DD7F918",
    ),
    "expanded_window_oracle": (
        EXPORT_DIR / "expanded-window-oracle.json",
        "20C270A332F7AD75FAED3C44C9AE3C1D789F7902ABA525C07B0B40F4266C5B2E",
    ),
    "physical_consumer_boundary": (
        EXPORT_DIR / "physical-consumer-boundary.json",
        "FE4D44152F51E0496B3AEF0B0594F557995D09FE31A9148440DA98209D119DDC",
    ),
    "visual_contract": (
        EXPORT_DIR / "visual-contract.json",
        "E5C6B30D8BF317FC8321D82E087D3B46552B4523FD8B67FFF3E6ABA89AAE4260",
    ),
    "frames": (
        EXPORT_DIR / "frames.bin",
        "D4DA2FCA6863C1B8F5DD28D70566712DCD91AB7383CA486735DFD253F7361E6D",
    ),
    "upper_pack_source": (
        EXPORT_DIR / "companion_visual_asset_pack.c",
        "1EE7BD5DDB210A3C3F90ADB607BA317CF2F00127099B876C9DB5948C7A5D03A0",
    ),
    "upper_pack_header": (
        EXPORT_DIR / "companion_visual_asset_pack.h",
        "2180FE281AFF31C8688BCB290740F898CF7E032C90D97FFE679F535689A814F9",
    ),
}

REQUIRED_LOWER_PATHS = {
    "app/companion_pendant/epaper/companion_visual_runtime_adapter.c",
    "app/companion_pendant/epaper/companion_visual_runtime_adapter.h",
    "app/companion_pendant/epaper/companion_visual_asset_pack.c",
    "app/companion_pendant/epaper/companion_visual_asset_pack.h",
    "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h",
    "app/companion_pendant/epaper/panel_target_stm32wb.c",
    "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
    "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c",
    "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.h",
    "app/companion_pendant/touch/touch_gesture.c",
    "app/companion_pendant/touch/touch_gesture.h",
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c",
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
    "tools/comp_req_472_visual_runtime_fixture.c",
    "tools/comp_req_472_visual_runtime_input_manifest.json",
    "tools/verify_comp_req_472_visual_runtime.py",
}

PRODUCTION_PREFIXES = (
    "app/companion_pendant/",
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/",
)

PROCESSING_FUNCTIONS = (
    "companion_visual_runtime_map_touch",
    "companion_visual_runtime_enqueue",
    "companion_visual_runtime_pop",
    "companion_visual_runtime_build_window",
    "companion_visual_runtime_emit_window",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha1_git_object(kind: str, data: bytes) -> str:
    header = f"{kind} {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def load_json_bytes(data: bytes, label: str) -> dict[str, Any]:
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object")
    return value


def load_json(path: Path) -> dict[str, Any]:
    return load_json_bytes(path.read_bytes(), path.as_posix())


def c_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()


def transition_states(item: dict[str, Any], key: str) -> list[str]:
    if key in item:
        return [str(item[key])]
    values = item.get(f"{key}_any")
    if not isinstance(values, list):
        raise ValueError(f"transition lacks {key}/{key}_any")
    return [str(value) for value in values]


def invert(data: bytes) -> bytes:
    return bytes(value ^ 0xFF for value in data)


def slice_window(frame: bytes, window: dict[str, Any]) -> bytes:
    result = bytearray()
    x_start = int(window["x_byte_start"])
    x_end = int(window["x_byte_end"])
    for y in range(int(window["y_start"]), int(window["y_end"]) + 1):
        row = y * 25
        result.extend(frame[row + x_start : row + x_end + 1])
    return bytes(result)


def changed_bounds(previous: bytes, current: bytes) -> dict[str, int] | None:
    points: list[tuple[int, int]] = []
    for offset, (before, after) in enumerate(zip(previous, current)):
        changed = before ^ after
        if changed == 0:
            continue
        y = offset // 25
        byte_x = offset % 25
        for bit in range(8):
            if changed & (0x80 >> bit):
                points.append((byte_x * 8 + bit, y))
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return {
        "x_min": min(xs),
        "y_min": min(ys),
        "x_max": max(xs),
        "y_max": max(ys),
        "width": max(xs) - min(xs) + 1,
        "height": max(ys) - min(ys) + 1,
    }


def window_from_bounds(bounds: dict[str, int] | None) -> dict[str, Any] | None:
    if bounds is None:
        return None
    x_start = bounds["x_min"] // 8
    x_end = bounds["x_max"] // 8
    rows = bounds["y_max"] - bounds["y_min"] + 1
    row_bytes = x_end - x_start + 1
    return {
        "x_byte_start": x_start,
        "x_byte_end": x_end,
        "x_pixel_start": x_start * 8,
        "x_pixel_end": x_end * 8 + 7,
        "y_start": bounds["y_min"],
        "y_end": bounds["y_max"],
        "row_bytes": row_bytes,
        "rows": rows,
        "payload_bytes": row_bytes * rows,
        "full_frame": (
            x_start == 0
            and x_end == 24
            and bounds["y_min"] == 0
            and bounds["y_max"] == 199
        ),
    }


def parse_c_array(text: str, name: str, expected_bytes: int) -> bytes:
    match = re.search(
        rf"\b{re.escape(name)}\s*\[[^\]]+\]\s*=\s*\{{(?P<body>.*?)\}}\s*;",
        text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(f"C array not found: {name}")
    values = bytes(
        int(token, 16)
        for token in re.findall(r"0x([0-9A-Fa-f]{1,2})u?", match.group("body"))
    )
    if len(values) != expected_bytes:
        raise ValueError(
            f"{name} bytes {len(values)} != expected {expected_bytes}"
        )
    return values


def strip_c(text: str) -> str:
    result = list(text)
    index = 0
    state = "normal"
    quote = ""
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if state == "normal":
            if char == "/" and nxt == "/":
                result[index] = result[index + 1] = " "
                state = "line"
                index += 2
                continue
            if char == "/" and nxt == "*":
                result[index] = result[index + 1] = " "
                state = "block"
                index += 2
                continue
            if char in ('"', "'"):
                quote = char
                result[index] = " "
                state = "string"
        elif state == "line":
            if char == "\n":
                state = "normal"
            else:
                result[index] = " "
        elif state == "block":
            if char == "*" and nxt == "/":
                result[index] = result[index + 1] = " "
                state = "normal"
                index += 2
                continue
            if char != "\n":
                result[index] = " "
        elif state == "string":
            if char == "\\" and nxt:
                result[index] = " "
                if nxt != "\n":
                    result[index + 1] = " "
                index += 2
                continue
            if char == quote:
                result[index] = " "
                state = "normal"
            elif char != "\n":
                result[index] = " "
        index += 1
    return "".join(result)


class GitReader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.command_count = 0

    def run(self, *args: str) -> bytes:
        self.command_count += 1
        completed = subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"read-only git failed: git {' '.join(args)}: "
                f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
            )
        return completed.stdout

    def toplevel(self) -> Path:
        return Path(
            self.run("rev-parse", "--show-toplevel").decode("utf-8").strip()
        ).resolve()

    def commit(self, revision: str) -> str:
        return self.run("rev-parse", f"{revision}^{{commit}}").decode().strip()

    def object_type(self, object_id: str) -> str:
        return self.run("cat-file", "-t", object_id).decode().strip()

    def object_data(self, object_id: str) -> bytes:
        return self.run("cat-file", "commit", object_id)

    def paths(self, commit: str) -> list[str]:
        return self.run("ls-tree", "-r", "--name-only", commit).decode().splitlines()

    def blob_id(self, commit: str, path: str) -> str:
        return self.run("rev-parse", f"{commit}:{path}").decode().strip()

    def blob(self, commit: str, path: str) -> bytes:
        return self.run("show", f"{commit}:{path}")


class CCallGraph:
    FUNCTION_RE = re.compile(
        r"(?m)^[ \t]*(?!if\b|for\b|while\b|switch\b)"
        r"(?:(?:static|inline|extern|const|volatile)\s+)*"
        r"(?:struct\s+[A-Za-z_]\w*\s+|enum\s+[A-Za-z_]\w*\s+|"
        r"[A-Za-z_]\w*[ \t\*]+)+"
        r"(?P<name>[A-Za-z_]\w*)[ \t]*"
        r"\((?P<args>[^;{}]*)\)[ \t\r\n]*\{"
    )
    CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")

    def __init__(self, sources: dict[str, str]) -> None:
        self.functions: dict[str, dict[str, Any]] = {}
        self.by_name: dict[str, list[str]] = {}
        self.edges: dict[str, list[dict[str, Any]]] = {}
        for path, original in sources.items():
            if not path.endswith(".c") or not path.startswith(PRODUCTION_PREFIXES):
                continue
            clean = strip_c(original)
            for match in self.FUNCTION_RE.finditer(clean):
                name = match.group("name")
                brace = match.end() - 1
                depth = 1
                cursor = brace + 1
                while cursor < len(clean) and depth:
                    if clean[cursor] == "{":
                        depth += 1
                    elif clean[cursor] == "}":
                        depth -= 1
                    cursor += 1
                if depth:
                    continue
                node = f"{path}::{name}"
                body_start = brace + 1
                body_end = cursor - 1
                self.functions[node] = {
                    "node": node,
                    "name": name,
                    "path": path,
                    "line": original.count("\n", 0, match.start()) + 1,
                    "args": clean[match.start() : brace],
                    "body": original[body_start:body_end],
                    "clean_body": clean[body_start:body_end],
                    "body_offset": body_start,
                    "call_sites": [],
                }
                self.by_name.setdefault(name, []).append(node)
        for node, function in self.functions.items():
            for match in self.CALL_RE.finditer(function["clean_body"]):
                name = match.group(1)
                if name in {"if", "for", "while", "switch", "sizeof", "return"}:
                    continue
                line = (
                    sources[function["path"]].count(
                        "\n", 0, function["body_offset"] + match.start()
                    )
                    + 1
                )
                function["call_sites"].append({"callee_name": name, "line": line})
            self.edges[node] = []
            for call in function["call_sites"]:
                targets = self.by_name.get(call["callee_name"], [])
                same_file = [
                    target
                    for target in targets
                    if self.functions[target]["path"] == function["path"]
                ]
                target = (
                    same_file[0]
                    if len(same_file) == 1
                    else targets[0] if len(targets) == 1 else None
                )
                if target is not None:
                    self.edges[node].append(
                        {
                            "caller": node,
                            "callee": target,
                            "callee_name": call["callee_name"],
                            "path": function["path"],
                            "line": call["line"],
                        }
                    )

    def node(self, name: str) -> str | None:
        nodes = self.by_name.get(name, [])
        return nodes[0] if len(nodes) == 1 else None

    def direct_calls(self, node: str, name: str) -> list[dict[str, Any]]:
        return [
            call
            for call in self.functions[node]["call_sites"]
            if call["callee_name"] == name
        ]

    def path(
        self,
        start: str | None,
        target: str | None,
        excluded_name_fragments: tuple[str, ...] = (),
    ) -> list[str] | None:
        if start is None or target is None:
            return None
        queue: deque[list[str]] = deque([[start]])
        visited = {start}
        while queue:
            current_path = queue.popleft()
            current = current_path[-1]
            if current == target:
                return current_path
            for edge in self.edges.get(current, []):
                nxt = edge["callee"]
                target_name = self.functions[nxt]["name"].lower()
                if (
                    nxt != target
                    and any(
                        fragment.lower() in target_name
                        for fragment in excluded_name_fragments
                    )
                ):
                    continue
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(current_path + [nxt])
        return None

    def path_to_name(
        self,
        start: str | None,
        name: str,
        excluded_name_fragments: tuple[str, ...] = (),
    ) -> list[str] | None:
        candidates = [
            self.path(start, target, excluded_name_fragments)
            for target in self.by_name.get(name, [])
        ]
        candidates = [candidate for candidate in candidates if candidate]
        return min(candidates, key=len) if candidates else None

    def reachable(self, start: str | None) -> set[str]:
        if start is None:
            return set()
        result = {start}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for edge in self.edges.get(node, []):
                if edge["callee"] not in result:
                    result.add(edge["callee"])
                    queue.append(edge["callee"])
        return result

    def serialize_path(self, nodes: list[str] | None) -> dict[str, Any] | None:
        if not nodes:
            return None
        edges = []
        for caller, callee in zip(nodes, nodes[1:]):
            edge = next(
                item for item in self.edges[caller] if item["callee"] == callee
            )
            edges.append(
                {
                    "caller": self.functions[caller]["name"],
                    "callee": self.functions[callee]["name"],
                    "call_site": f"{edge['path']}:{edge['line']}",
                }
            )
        return {
            "simple_non_circular": len(nodes) == len(set(nodes)),
            "nodes": [
                {
                    "function": self.functions[node]["name"],
                    "definition": (
                        f"{self.functions[node]['path']}:"
                        f"{self.functions[node]['line']}"
                    ),
                }
                for node in nodes
            ],
            "edges": edges,
        }


def selected_lower_paths(all_paths: list[str]) -> list[str]:
    selected = set(REQUIRED_LOWER_PATHS)
    for path in all_paths:
        if path.startswith("app/companion_pendant/epaper/") and (
            "companion_visual" in path
            or "r7_runtime_bridge" in path
            or "panel_target_stm32wb" in path
        ):
            if path.endswith((".c", ".h")):
                selected.add(path)
        if path.startswith("app/companion_pendant/touch/touch_gesture"):
            selected.add(path)
    missing = REQUIRED_LOWER_PATHS.difference(all_paths)
    if missing:
        raise ValueError(f"required lower paths missing: {sorted(missing)}")
    result = sorted(selected)
    if len(result) > MAX_SOURCE_FILES:
        raise ValueError(f"source count {len(result)} exceeds {MAX_SOURCE_FILES}")
    return result


def resolve_output(repo_root: Path, supplied: Path | None) -> Path:
    candidate = supplied or DEFAULT_OUTPUT
    result = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()
    validation_root = (repo_root / VALIDATION_DIR).resolve()
    try:
        result.relative_to(validation_root)
    except ValueError as error:
        raise ValueError("output must stay in matching upper validation directory") from error
    if not OUTPUT_NAME_RE.fullmatch(result.name):
        raise ValueError("output filename must match upper-lower-compatibility-*.json")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--lower-root", type=Path)
    parser.add_argument("--expected-commit", default=DEFAULT_LOWER_COMMIT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--comparison-mode", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if COMMIT_RE.fullmatch(args.expected_commit) is None:
        raise SystemExit("--expected-commit must be an exact 40-hex commit")
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[2]
    )
    lower_root = (args.lower_root or repo_root).resolve()
    output_path = resolve_output(repo_root, args.output)

    upper_identities: dict[str, dict[str, Any]] = {}
    for name, (relative, expected) in UPPER_BINDINGS.items():
        observed = file_sha(repo_root / relative)
        upper_identities[name] = {
            "path": relative.as_posix(),
            "expected_sha256": expected,
            "observed_sha256": observed,
            "match": observed == expected,
        }

    upper_ready = load_json(repo_root / UPPER_BINDINGS["upper_machine_ready"][0])
    transitions = load_json(repo_root / UPPER_BINDINGS["state_transitions"][0])
    oracle = load_json(repo_root / UPPER_BINDINGS["expanded_window_oracle"][0])
    boundary = load_json(
        repo_root / UPPER_BINDINGS["physical_consumer_boundary"][0]
    )
    visual_contract = load_json(
        repo_root / UPPER_BINDINGS["visual_contract"][0]
    )
    combined_frames = (repo_root / UPPER_BINDINGS["frames"][0]).read_bytes()

    git = GitReader(lower_root)
    if git.toplevel() != lower_root:
        raise SystemExit("--lower-root must be the exact Git toplevel")
    lower_commit = git.commit(args.expected_commit)
    if lower_commit.lower() != args.expected_commit.lower():
        raise SystemExit("resolved lower commit does not equal --expected-commit")
    if git.object_type(lower_commit) != "commit":
        raise SystemExit("expected lower object is not a commit")
    commit_data = git.object_data(lower_commit)
    commit_recomputed = sha1_git_object("commit", commit_data)

    all_lower_paths = git.paths(lower_commit)
    lower_paths = selected_lower_paths(all_lower_paths)
    lower_blobs: dict[str, bytes] = {}
    lower_sources = []
    total_source_bytes = 0
    for path in lower_paths:
        blob_id = git.blob_id(lower_commit, path)
        data = git.blob(lower_commit, path)
        if len(data) > MAX_SOURCE_BYTES_EACH:
            raise SystemExit(f"lower blob too large: {path}")
        total_source_bytes += len(data)
        if total_source_bytes > MAX_SOURCE_BYTES_TOTAL:
            raise SystemExit("lower source byte total exceeds bound")
        recomputed_blob_id = sha1_git_object("blob", data)
        lower_blobs[path] = data
        lower_sources.append(
            {
                "path": path,
                "bytes": len(data),
                "git_blob_object": blob_id,
                "recomputed_git_blob_object": recomputed_blob_id,
                "git_blob_object_match": blob_id == recomputed_blob_id,
                "sha256": sha256(data),
            }
        )
    source = {
        path: data.decode("utf-8")
        for path, data in lower_blobs.items()
        if path.endswith((".c", ".h"))
    }

    lower_manifest = load_json_bytes(
        lower_blobs["tools/comp_req_472_visual_runtime_input_manifest.json"],
        "lower input manifest",
    )
    state_ids = [str(value) for value in transitions["states"]]
    state_index = {state_id: index for index, state_id in enumerate(state_ids)}
    lower_state_ids = [str(item["id"]) for item in lower_manifest["states"]]
    lower_state_enums = [str(item["c_enum"]) for item in lower_manifest["states"]]
    expected_state_enums = [
        f"COMPANION_VISUAL_STATE_{c_token(state_id)}" for state_id in state_ids
    ]

    upper_transition_rows = []
    for index, item in enumerate(transitions["transitions"]):
        from_states = transition_states(item, "from")
        to_states = transition_states(item, "to")
        upper_transition_rows.append(
            {
                "index": index,
                "from_states": from_states,
                "to_states": to_states,
                "from_mask": sum(1 << state_index[value] for value in from_states),
                "to_mask": sum(1 << state_index[value] for value in to_states),
                "event": item["event"],
                "guard": item.get("guard", "always"),
                "effect": item["effect"],
            }
        )
    lower_transition_rows = [
        {
            key: item[key]
            for key in (
                "index",
                "from_states",
                "to_states",
                "from_mask",
                "to_mask",
                "event",
                "guard",
                "effect",
            )
        }
        for item in lower_manifest["transitions"]
    ]

    frame_by_id: dict[str, bytes] = {}
    converted_frames = []
    for frame in visual_contract["frames"]:
        start = int(frame["byte_offset"])
        length = int(frame["byte_length"])
        logical = combined_frames[start : start + length]
        panel = invert(logical)
        frame_by_id[str(frame["id"])] = logical
        converted_frames.append(
            {
                "state": frame["id"],
                "logical_sha256": sha256(logical),
                "expected_logical_sha256": frame["raw_sha256"],
                "logical_sha_match": sha256(logical) == frame["raw_sha256"],
                "panel_sha256": sha256(panel),
                "bytes": len(panel),
                "conversion": "panel_byte = logical_byte ^ 0xFF",
                "roundtrip_equal": invert(panel) == logical,
            }
        )

    converted_pair_rows = []
    for pair in oracle["pairs"]:
        logical_previous = frame_by_id[pair["from_state"]]
        logical_current = frame_by_id[pair["to_state"]]
        panel_previous = invert(logical_previous)
        panel_current = invert(logical_current)
        logical_bounds = changed_bounds(logical_previous, logical_current)
        panel_bounds = changed_bounds(panel_previous, panel_current)
        upper_window = pair["transfer_window"]
        panel_window = window_from_bounds(panel_bounds)
        window_matches = panel_window == upper_window
        if panel_window is None:
            logical_slice = b""
            panel_slice = b""
            reconstructed = panel_previous
        else:
            if upper_window is None:
                logical_slice = b""
            else:
                logical_slice = slice_window(logical_current, upper_window)
            panel_slice = slice_window(panel_current, panel_window)
            reconstructed_bytes = bytearray(panel_previous)
            x_start = int(panel_window["x_byte_start"])
            x_end = int(panel_window["x_byte_end"])
            row_bytes = x_end - x_start + 1
            cursor = 0
            for y in range(
                int(panel_window["y_start"]), int(panel_window["y_end"]) + 1
            ):
                start = y * 25 + x_start
                reconstructed_bytes[start : start + row_bytes] = panel_slice[
                    cursor : cursor + row_bytes
                ]
                cursor += row_bytes
            reconstructed = bytes(reconstructed_bytes)
        row = {
            "id": pair["id"],
            "event": pair["event"],
            "from_state": pair["from_state"],
            "to_state": pair["to_state"],
            "pixel_noop": pair["pixel_noop"],
            "logical_changed_bounds": logical_bounds,
            "panel_changed_bounds": panel_bounds,
            "bounds_unchanged_by_inversion": logical_bounds == panel_bounds,
            "upper_oracle_window": upper_window,
            "derived_panel_window": panel_window,
            "window_matches_upper_oracle": window_matches,
            "logical_payload_sha256": sha256(logical_slice),
            "expected_logical_payload_sha256": pair["current_slice"]["sha256"],
            "panel_payload_sha256": sha256(panel_slice),
            "panel_payload_bytes": len(panel_slice),
            "panel_payload_is_exact_inversion": panel_slice == invert(logical_slice),
            "outside_unchanged": reconstructed == panel_current,
            "panel_current_sha256": sha256(panel_current),
            "oracle_pass": (
                logical_bounds == panel_bounds
                and window_matches
                and sha256(logical_slice) == pair["current_slice"]["sha256"]
                and panel_slice == invert(logical_slice)
                and reconstructed == panel_current
            ),
        }
        converted_pair_rows.append(row)

    centered_converted_sha = next(
        item["panel_sha256"]
        for item in converted_frames
        if item["state"] == "centered_rest"
    )
    converted_oracle_pass = (
        len(converted_frames) == 17
        and len(converted_pair_rows) == 59
        and sum(item["pixel_noop"] for item in converted_pair_rows) == 10
        and all(item["logical_sha_match"] for item in converted_frames)
        and all(item["roundtrip_equal"] for item in converted_frames)
        and all(item["oracle_pass"] for item in converted_pair_rows)
        and centered_converted_sha == EXPECTED_CONVERTED_CENTERED_SHA256
    )

    graph = CCallGraph(source)
    main_node = graph.node("main")
    service_node = graph.node("companion_visual_runtime_service")
    map_node = graph.node("companion_visual_runtime_map_touch")
    enqueue_node = graph.node("companion_visual_runtime_enqueue")
    pop_node = graph.node("companion_visual_runtime_pop")
    build_node = graph.node("companion_visual_runtime_build_window")
    emit_node = graph.node("companion_visual_runtime_emit_window")
    enqueue_gesture_node = graph.node("companion_visual_runtime_enqueue_gesture")
    enqueue_visual_event_node = graph.node(
        "companion_visual_runtime_enqueue_visual_event"
    )

    gesture_paths = [
        graph.path_to_name(
            main_node,
            "comp_touch_gesture_process",
            excluded_name_fragments=("self_test",),
        ),
        graph.path_to_name(
            main_node,
            "comp_touch_gesture_restart_contact",
            excluded_name_fragments=("self_test",),
        ),
    ]
    gesture_paths = [path for path in gesture_paths if path]
    gesture_path = min(gesture_paths, key=len) if gesture_paths else None
    main_to_service = graph.path(main_node, service_node)
    main_to_enqueue_gesture = graph.path(main_node, enqueue_gesture_node)
    enqueue_gesture_to_map = graph.path(enqueue_gesture_node, map_node)
    enqueue_gesture_to_queue = graph.path(enqueue_gesture_node, enqueue_node)
    main_to_enqueue_visual_event = graph.path(
        main_node, enqueue_visual_event_node
    )
    enqueue_visual_event_to_queue = graph.path(
        enqueue_visual_event_node, enqueue_node
    )

    generic_dispatch_nodes = []
    reachable_from_main = graph.reachable(main_node)
    for node, function in graph.functions.items():
        body = function["clean_body"]
        event_access = bool(
            re.search(r"(?:\.|->)\s*event\b|\bevent\s*==", body)
        )
        table_driven = all(
            token in body
            for token in (
                "companion_visual_transition_table",
                "from_state_mask",
                "to_state_mask",
            )
        )
        queue_path = graph.path(node, enqueue_node)
        if (
            node in reachable_from_main
            and event_access
            and table_driven
            and queue_path is not None
        ):
            generic_dispatch_nodes.append(node)
    generic_dispatch_node = (
        min(
            generic_dispatch_nodes,
            key=lambda node: len(graph.path(main_node, node) or []),
        )
        if generic_dispatch_nodes
        else None
    )

    def ingress_orchestrator(
        target_node: str | None,
    ) -> dict[str, Any] | None:
        if target_node is None:
            return None
        candidates = []
        for node in reachable_from_main:
            function_name = graph.functions[node]["name"].lower()
            if node == main_node or "self_test" in function_name:
                continue
            local_gesture_paths = [
                graph.path_to_name(
                    node,
                    "comp_touch_gesture_process",
                    excluded_name_fragments=("self_test",),
                ),
                graph.path_to_name(
                    node,
                    "comp_touch_gesture_restart_contact",
                    excluded_name_fragments=("self_test",),
                ),
            ]
            local_gesture_paths = [
                path for path in local_gesture_paths if path
            ]
            target_path = graph.path(node, target_node)
            if not local_gesture_paths or target_path is None:
                continue
            local_gesture = min(local_gesture_paths, key=len)
            if len(local_gesture) != len(set(local_gesture)):
                continue
            if len(target_path) != len(set(target_path)):
                continue
            gesture_first_line = (
                next(
                    edge["line"]
                    for edge in graph.edges[node]
                    if edge["callee"] == local_gesture[1]
                )
                if len(local_gesture) > 1
                else graph.functions[node]["line"]
            )
            target_first_line = (
                next(
                    edge["line"]
                    for edge in graph.edges[node]
                    if edge["callee"] == target_path[1]
                )
                if len(target_path) > 1
                else graph.functions[node]["line"]
            )
            candidates.append(
                {
                    "node": node,
                    "gesture_path": local_gesture,
                    "target_path": target_path,
                    "gesture_first_call_line": gesture_first_line,
                    "target_first_call_line": target_first_line,
                    "ordered_or_shared_branch": (
                        local_gesture[1:2] == target_path[1:2]
                        or gesture_first_line <= target_first_line
                    ),
                    "score": len(local_gesture) + len(target_path),
                }
            )
        valid = [
            candidate
            for candidate in candidates
            if candidate["ordered_or_shared_branch"]
        ]
        return min(valid, key=lambda item: item["score"]) if valid else None

    direct_ingress = ingress_orchestrator(enqueue_gesture_node)
    generic_ingress = ingress_orchestrator(generic_dispatch_node)

    service_body = (
        graph.functions[service_node]["clean_body"] if service_node else ""
    )
    service_calls = (
        graph.functions[service_node]["call_sites"] if service_node else []
    )

    def first_call_line(name: str) -> int | None:
        lines = [
            int(item["line"])
            for item in service_calls
            if item["callee_name"] == name
        ]
        return min(lines) if lines else None

    pop_line = first_call_line("companion_visual_runtime_pop")
    peek_line = first_call_line("companion_visual_runtime_peek")
    discard_lines = [
        int(item["line"])
        for item in service_calls
        if item["callee_name"] == "companion_visual_runtime_discard"
        or "commit_pop" in item["callee_name"]
    ]
    build_line = first_call_line("companion_visual_runtime_build_window")
    emit_line = first_call_line("companion_visual_runtime_emit_window")
    legacy_pop_ordered = (
        pop_line is not None
        and build_line is not None
        and emit_line is not None
        and pop_line < build_line < emit_line
    )
    deferred_discard_ordered = bool(
        peek_line is not None
        and build_line is not None
        and emit_line is not None
        and discard_lines
        and peek_line < build_line < emit_line < max(discard_lines)
    )
    service_ordered = legacy_pop_ordered or deferred_discard_ordered
    noop_semantic_commit = bool(
        service_node
        and (
            "memcmp" in service_body
            or "companion_visual_runtime_frames_equal" in service_body
        )
        and re.search(r"\bcurrent_state\s*=", service_body)
        and (
            "companion_visual_runtime_discard" in service_body
            or "companion_visual_runtime_pop" in service_body
        )
    )
    peek_lines = [
        int(item["line"])
        for item in service_calls
        if "peek" in item["callee_name"] or "front" in item["callee_name"]
    ]
    pop_lines = [
        int(item["line"])
        for item in service_calls
        if item["callee_name"] == "companion_visual_runtime_pop"
        or "commit_pop" in item["callee_name"]
        or item["callee_name"] == "companion_visual_runtime_discard"
    ]
    rollback_tokens = (
        "requeue",
        "restore_event",
        "rollback_pop",
        "ring_head--",
        "ring_count++",
    )
    rollback_present = any(token in service_body for token in rollback_tokens)
    build_failure_match = re.search(
        r"if\s*\(\s*!\s*companion_visual_runtime_build_window\s*\("
        r".*?\)\s*\)\s*\{(?P<body>.*?)\}",
        service_body,
        re.DOTALL,
    )
    build_failure_body = (
        build_failure_match.group("body") if build_failure_match else ""
    )
    build_failure_terminal_latched = bool(
        build_failure_body
        and (
            "terminal_fault = true" in build_failure_body
            or "companion_visual_runtime_discard" in build_failure_body
        )
    )
    frame_lookup_failure_match = re.search(
        r"if\s*\(\s*previous\s*==\s*NULL\s*\|\|\s*current\s*==\s*NULL"
        r"\s*\)\s*\{(?P<body>.*?)\}",
        service_body,
        re.DOTALL,
    )
    frame_lookup_failure_body = (
        frame_lookup_failure_match.group("body")
        if frame_lookup_failure_match
        else ""
    )
    frame_lookup_failure_terminal_latched = bool(
        frame_lookup_failure_body
        and (
            "terminal_fault = true" in frame_lookup_failure_body
            or "companion_visual_runtime_discard" in frame_lookup_failure_body
        )
    )
    emit_failure_terminal_latched = bool(
        re.search(
            r"else\s*\{(?P<body>[^{}]*terminal_fault\s*=\s*true[^{}]*)\}",
            service_body,
            re.DOTALL,
        )
    )
    terminal_retention = bool(
        emit_line is not None
        and (
            deferred_discard_ordered
            or rollback_present
        )
        and build_failure_terminal_latched
        and frame_lookup_failure_terminal_latched
        and emit_failure_terminal_latched
    )
    pop_before_emit_terminal_loss = bool(
        pop_line is not None and emit_line is not None and pop_line < emit_line
        and not terminal_retention
    )

    inversion_nodes = []
    for node, function in graph.functions.items():
        body = function["clean_body"]
        bitwise_inversion = bool(
            re.search(r"\^\s*(?:0xFF|UINT8_MAX)", body, re.IGNORECASE)
            or re.search(r"(?<![&|])~\s*(?:\(?\s*)?[A-Za-z_]\w*", body)
        )
        visual_bytes = any(
            token in (function["name"] + " " + body).lower()
            for token in ("visual", "logical", "panel", "frame", "payload")
        )
        if bitwise_inversion and visual_bytes:
            inversion_nodes.append(node)

    service_inversion_candidates = [
        node
        for node in inversion_nodes
        if node == service_node or graph.path(service_node, node) is not None
    ]
    service_inversion_node = (
        min(
            service_inversion_candidates,
            key=lambda node: len(graph.path(service_node, node) or [node]),
        )
        if service_inversion_candidates
        else None
    )
    service_inversion_path = graph.path(service_node, service_inversion_node)
    build_inversion_candidates = [
        node
        for node in inversion_nodes
        if node == build_node or graph.path(build_node, node) is not None
    ]
    build_inversion_node = (
        min(
            build_inversion_candidates,
            key=lambda node: len(graph.path(build_node, node) or [node]),
        )
        if build_inversion_candidates
        else None
    )
    build_inversion_path = graph.path(build_node, build_inversion_node)
    build_body = (
        graph.functions[build_node]["clean_body"] if build_node else ""
    )
    build_converts_diff_and_payload = bool(
        build_inversion_path
        and "window->payload" in build_body
        and re.search(
            r"panel_byte\s*\(\s*previous|"
            r"panel_byte\s*\(\s*current",
            build_body,
        )
    )
    conversion_before_build = False
    if service_node and service_inversion_node and build_line is not None:
        if service_inversion_node == service_node:
            inversion_offset = min(
                [
                    offset
                    for offset in (
                        service_body.find("^ 0xFF"),
                        service_body.find("^0xFF"),
                        service_body.find("~"),
                    )
                    if offset >= 0
                ],
                default=-1,
            )
            build_offset = service_body.find(
                "companion_visual_runtime_build_window"
            )
            conversion_before_build = 0 <= inversion_offset < build_offset
        else:
            conversion_calls = [
                item["line"]
                for item in service_calls
                if item["callee_name"]
                == graph.functions[service_inversion_node]["name"]
            ]
            conversion_before_build = bool(
                conversion_calls and max(conversion_calls) < build_line
            )
    conversion_before_emit = bool(
        build_converts_diff_and_payload
        and build_line is not None
        and emit_line is not None
        and build_line < emit_line
    )
    conversion_before_build = (
        conversion_before_build or build_converts_diff_and_payload
    )

    app_init_node = graph.node("APP_BLE_Init")
    initialization_roots = [
        node for node in (main_node, app_init_node) if node is not None
    ]
    initialization_reachable = set().union(
        *(graph.reachable(node) for node in initialization_roots)
    )
    init_candidates = [
        node
        for node, function in graph.functions.items()
        if "init" in function["name"].lower()
        and node in initialization_reachable
        and (
            "COMPANION_VISUAL_STATE_CENTERED_REST" in function["clean_body"]
            or "companion_visual_frame_for_state" in function["clean_body"]
        )
    ]
    initial_conversion_evidence = None
    for init_node in init_candidates:
        for inversion_node in inversion_nodes:
            inversion_path = graph.path(init_node, inversion_node)
            if inversion_path is None:
                continue
            body = graph.functions[init_node]["clean_body"]
            display_link = any(
                token in body
                for token in (
                    "companion_visual_runtime_emit_window",
                    "companion_r7_runtime_bridge_visual_transport",
                    "0x24",
                )
            ) or graph.path_to_name(
                init_node, "companion_visual_runtime_emit_window"
            )
            if display_link:
                initial_conversion_evidence = {
                    "entry_node": next(
                        (
                            root
                            for root in initialization_roots
                            if graph.path(root, init_node) is not None
                        ),
                        None,
                    ),
                    "init_node": init_node,
                    "inversion_node": inversion_node,
                    "path": inversion_path,
                }
                break
        if initial_conversion_evidence:
            break

    polarity_bridge_realizable = bool(
        service_inversion_node
        and conversion_before_emit
        and initial_conversion_evidence
        and main_to_service
        and service_ordered
    )

    runtime_c_path = (
        "app/companion_pendant/epaper/companion_visual_runtime_adapter.c"
    )
    runtime_c = source[runtime_c_path]
    main_path = "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
    main_c = source[main_path]
    touch_h = source["app/companion_pendant/touch/touch_gesture.h"]

    def direct_case(case: str, target: str) -> bool:
        return bool(
            re.search(
                rf"case\s+{re.escape(case)}\s*:.*?"
                rf"\*visual_state\s*=\s*{re.escape(target)}\s*;\s*return true;",
                runtime_c,
                re.DOTALL,
            )
        )

    direct_touch = {
        "single_tap_commit": direct_case(
            "COMP_TOUCH_GESTURE_TAP",
            "COMPANION_VISUAL_STATE_SINGLE_TAP_RESPONSE",
        ),
        "stationary_pointerdown": direct_case(
            "COMP_TOUCH_GESTURE_HOLD",
            "COMPANION_VISUAL_STATE_HOLD_FEEDBACK_50",
        ),
        "hold_complete": direct_case(
            "COMP_TOUCH_GESTURE_LONG_PRESS",
            "COMPANION_VISUAL_STATE_MENU_ROOTS",
        ),
        "second_short_tap": direct_case(
            "COMP_TOUCH_GESTURE_DOUBLE_TAP",
            "COMPANION_VISUAL_STATE_RECORDING_ENTRY",
        ),
    }
    swipe_cases_present = all(
        f"case COMP_TOUCH_GESTURE_SWIPE_{direction}:" in runtime_c
        for direction in ("LEFT", "UP", "RIGHT", "DOWN")
    )
    swipe_uses_caller_state = (
        swipe_cases_present
        and "*visual_state = gaze_state; return true;" in runtime_c
    )
    continuous_contact_observer = bool(
        graph.path_to_name(main_node, "observe_visual_runtime_contact")
        and "latest_x" in main_c
        and "latest_y" in main_c
        and "companion_visual_runtime_enqueue_gesture" in main_c
    )
    center_enqueue_from_contact = bool(
        re.search(
            r"observe_visual_runtime_contact.*?"
            r"COMPANION_VISUAL_STATE_GAZE_CENTER.*?"
            r"companion_visual_runtime_enqueue",
            main_c,
            re.DOTALL,
        )
    )
    none_maps_rest = direct_case(
        "COMP_TOUCH_GESTURE_NONE",
        "COMPANION_VISUAL_STATE_CENTERED_REST",
    )
    enqueue_none_rejected = bool(
        re.search(
            r"case\s+COMP_TOUCH_GESTURE_NONE\s*:\s*"
            r"(?:default\s*:)?\s*return false",
            runtime_c,
        )
    )

    qualification_all_gaze_16 = bool(
        re.search(
            r"for\s*\([^)]*index\s*=\s*1u[^)]*index\s*<=\s*16u.*?"
            r"companion_visual_runtime_enqueue\s*\(.*?"
            r"COMPANION_VISUAL_RUNTIME_EVENT_GAZE",
            main_c,
            re.DOTALL,
        )
    )
    gaze_coalescing = all(
        token in runtime_c
        for token in (
            "kind == COMPANION_VISUAL_RUNTIME_EVENT_GAZE",
            "runtime->ring[index].state = state",
            "runtime->ring[index].sequence = runtime->next_sequence++",
        )
    )
    qualification_effective_events = (
        1 if qualification_all_gaze_16 and gaze_coalescing else None
    )
    valid_qualification_sequence = bool(
        not qualification_all_gaze_16
        and "qualification" in main_c
        and re.search(
            r"COMPANION_VISUAL_(?:EVENT|RUNTIME_EVENT)_(?!GAZE)",
            main_c,
        )
        and "companion_visual_runtime_enqueue" in main_c
    )

    generic_dispatch = generic_dispatch_node is not None
    direct_pipeline = bool(
        direct_ingress
        and gesture_path
        and main_to_enqueue_gesture
        and enqueue_gesture_to_map
        and enqueue_gesture_to_queue
        and main_to_service
        and service_ordered
    )
    generic_pipeline = bool(
        generic_ingress
        and gesture_path
        and generic_dispatch_node
        and graph.path(main_node, generic_dispatch_node)
        and graph.path(generic_dispatch_node, enqueue_node)
        and main_to_service
        and service_ordered
    )
    visual_event_body = (
        graph.functions[enqueue_visual_event_node]["clean_body"]
        if enqueue_visual_event_node
        else ""
    )

    def visual_event_ingress(event: str) -> list[str] | None:
        if enqueue_visual_event_node is None:
            return None
        token = f"COMPANION_VISUAL_EVENT_{c_token(event)}"
        if re.search(
            rf"case\s+{re.escape(token)}\s*:", visual_event_body
        ) is None:
            return None
        candidates = []
        for node in reachable_from_main:
            if node == enqueue_visual_event_node:
                continue
            function = graph.functions[node]
            if token not in function["clean_body"]:
                continue
            suffix = graph.path(node, enqueue_visual_event_node)
            prefix = graph.path(main_node, node)
            if suffix is None or prefix is None:
                continue
            combined = prefix + suffix[1:]
            if len(combined) == len(set(combined)):
                candidates.append(combined)
        return min(candidates, key=len) if candidates else None

    directional_events = {
        "pointer_drag_left",
        "pointer_drag_up",
        "pointer_drag_right",
        "pointer_drag_down",
    }
    missing_return_events = {
        "pointer_drag_center",
        "pointer_up_or_cancel",
        "early_up_cancel_blur_or_drag",
        "recording_return",
        "select_voice",
        "select_device",
        "select_connection",
        "select_preferences",
        "select_ui_assets",
        "menu_back",
        "menu_return",
        "settle",
    }
    event_pairs: dict[str, list[dict[str, Any]]] = {}
    for pair in oracle["pairs"]:
        event_pairs.setdefault(pair["event"], []).append(pair)

    event_rows = []
    for transition in upper_transition_rows:
        event = transition["event"]
        visual_event_path = visual_event_ingress(event)
        if generic_dispatch:
            mapping_status = "mapped"
            mapping_evidence = "reachable table-driven event dispatcher"
            event_pipeline = generic_pipeline
        elif visual_event_path:
            mapping_status = "mapped"
            mapping_evidence = (
                "reachable event-specific call site enters the bounded visual "
                "event switch and queue"
            )
            event_pipeline = bool(
                enqueue_visual_event_to_queue
                and main_to_service
                and service_ordered
            )
        elif event in direct_touch and direct_touch[event]:
            mapping_status = "mapped"
            mapping_evidence = "direct gesture case selects accepted target"
            event_pipeline = direct_pipeline
        elif (
            event in directional_events
            and swipe_uses_caller_state
            and continuous_contact_observer
        ):
            mapping_status = "mapped"
            mapping_evidence = (
                "reachable live contact observer derives direction and enqueues "
                "the matching caller-supplied gaze state"
            )
            event_pipeline = direct_pipeline
        elif event == "pointer_move" and continuous_contact_observer:
            mapping_status = "ambiguous"
            mapping_evidence = (
                "live directional contact updates exist, but center replacement "
                "is not enqueued when contact returns inside slop"
            )
            event_pipeline = direct_pipeline
        elif event in missing_return_events:
            mapping_status = "missing"
            mapping_evidence = (
                "no reachable event-specific dispatch for accepted center/cancel/"
                "settle/menu/recording return identity"
            )
            event_pipeline = False
        else:
            mapping_status = "missing"
            mapping_evidence = "no reachable accepted semantic event mapping"
            event_pipeline = False
        lower_path_without_polarity = bool(
            mapping_status == "mapped" and event_pipeline
        )
        realizable = bool(
            lower_path_without_polarity
            and polarity_bridge_realizable
            and terminal_retention
        )
        event_rows.append(
            {
                "index": transition["index"],
                "event": event,
                "from_states": transition["from_states"],
                "to_states": transition["to_states"],
                "pair_count": len(event_pairs.get(event, [])),
                "pixel_noop_pair_count": sum(
                    pair["pixel_noop"] for pair in event_pairs.get(event, [])
                ),
                "mapping_status": mapping_status,
                "mapping_evidence": mapping_evidence,
                "event_ingress_path": graph.serialize_path(
                    visual_event_path
                ),
                "call_edge_pipeline_without_polarity": lower_path_without_polarity,
                "polarity_bridge_on_path": polarity_bridge_realizable,
                "terminal_retention_on_path": terminal_retention,
                "realizable_lower_path": realizable,
            }
        )
    event_by_name = {row["event"]: row for row in event_rows}
    required_return_event_gaps = sorted(
        event
        for event in missing_return_events
        if event_by_name[event]["mapping_status"] != "mapped"
    )

    directional_gaze_states = {
        "gaze_left",
        "gaze_up",
        "gaze_right",
        "gaze_down",
    }
    pair_rows = []
    for upper_pair, converted_pair in zip(
        oracle["pairs"], converted_pair_rows
    ):
        no_op = bool(upper_pair["pixel_noop"])
        event_row = event_by_name[upper_pair["event"]]
        pair_pipeline_without_polarity = event_row[
            "call_edge_pipeline_without_polarity"
        ]
        pair_mapping_evidence = event_row["mapping_evidence"]
        if (
            upper_pair["event"] == "pointer_move"
            and continuous_contact_observer
            and direct_pipeline
            and upper_pair["to_state"] in directional_gaze_states
        ):
            pair_pipeline_without_polarity = True
            pair_mapping_evidence = (
                "live contact observer reaches the requested directional gaze; "
                "center-target pairs remain unrealizable"
            )
        pair_rows.append(
            {
                "id": upper_pair["id"],
                "event": upper_pair["event"],
                "from_state": upper_pair["from_state"],
                "to_state": upper_pair["to_state"],
                "pixel_noop": no_op,
                "converted_payload_sha256": converted_pair[
                    "panel_payload_sha256"
                ],
                "converted_payload_oracle_pass": converted_pair["oracle_pass"],
                "semantic_state_commit": noop_semantic_commit if no_op else True,
                "pair_mapping_evidence": pair_mapping_evidence,
                "call_edge_pipeline_without_polarity": (
                    pair_pipeline_without_polarity
                ),
                "polarity_bridge_on_path": polarity_bridge_realizable,
                "terminal_retention_on_path": terminal_retention,
                "realizable_lower_path": bool(
                    pair_pipeline_without_polarity
                    and polarity_bridge_realizable
                    and terminal_retention
                    and converted_pair["oracle_pass"]
                    and (not no_op or noop_semantic_commit)
                ),
            }
        )
    for event_row in event_rows:
        matching_pairs = [
            row for row in pair_rows if row["event"] == event_row["event"]
        ]
        event_row["pair_realizable_count"] = sum(
            row["realizable_lower_path"] for row in matching_pairs
        )
        event_row["pair_total_count"] = len(matching_pairs)

    state_rows = [
        {
            "index": index,
            "state": state_id,
            "lower_id": lower_state_ids[index],
            "lower_enum": lower_state_enums[index],
            "identity_status": (
                "mapped"
                if lower_state_ids[index] == state_id
                and lower_state_enums[index] == expected_state_enums[index]
                else "missing"
            ),
            "converted_frame_sha256": converted_frames[index]["panel_sha256"],
        }
        for index, state_id in enumerate(state_ids)
    ]

    r7_header = source[
        "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h"
    ]
    r7_baseline = parse_c_array(
        r7_header, "companion_r7_locked_v9_baseline_frame", 5000
    )
    centered_logical = frame_by_id["centered_rest"]
    r7_vs_logical_diff_bytes = sum(
        before != after for before, after in zip(r7_baseline, centered_logical)
    )
    bridge_c = source[
        "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c"
    ]
    locked_r7_fallback_present = bool(
        re.search(
            r"companion_r7_runtime_bridge_init.*?"
            r"bridge_data\s*\(\s*companion_r7_locked_v9_baseline_frame",
            bridge_c,
            re.DOTALL,
        )
    )
    initial_uses_converted_centered = bool(
        initial_conversion_evidence
        and re.search(
            r"companion_r7_runtime_bridge_init.*?"
            r"companion_visual_runtime_copy_panel_frame\s*\(\s*"
            r"COMPANION_VISUAL_STATE_CENTERED_REST.*?"
            r"bridge_data\s*\(\s*visual_baseline\s*,\s*5000u\s*\)",
            bridge_c,
            re.DOTALL,
        )
    )
    initial_uses_locked_r7_baseline = bool(
        locked_r7_fallback_present and not initial_uses_converted_centered
    )
    direct_logical_payload_emit = bool(
        "transport(context, 0x24u, window->payload, window->payload_bytes)"
        in runtime_c
        and not service_inversion_node
    )
    panel_source = source[
        "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    ]
    panel_white_one_black_zero = bool(
        "memset(s_frame, 0xFF" in panel_source
        and re.search(r"s_frame\[.*?\]\s*&=\s*\(uint8_t\)~", panel_source, re.DOTALL)
    )

    mapped_events = sum(row["mapping_status"] == "mapped" for row in event_rows)
    ambiguous_events = sum(
        row["mapping_status"] == "ambiguous" for row in event_rows
    )
    missing_events = sum(row["mapping_status"] == "missing" for row in event_rows)
    realizable_events = sum(row["realizable_lower_path"] for row in event_rows)
    realizable_pairs = sum(row["realizable_lower_path"] for row in pair_rows)
    noop_rows = [row for row in pair_rows if row["pixel_noop"]]
    realizable_noops = sum(row["realizable_lower_path"] for row in noop_rows)

    lower_source_by_path = {item["path"]: item for item in lower_sources}
    structural_checks = {
        "upper_hashes_exact": all(
            item["match"] for item in upper_identities.values()
        ),
        "upper_machine_ready_still_pass": (
            upper_ready["status"] == "UPPER_MACHINE_READY"
            and not upper_ready["failed"]
        ),
        "expected_commit_exact": lower_commit.lower()
        == args.expected_commit.lower(),
        "commit_object_recomputed": commit_recomputed == lower_commit,
        "source_bounds_respected": (
            len(lower_sources) <= MAX_SOURCE_FILES
            and total_source_bytes <= MAX_SOURCE_BYTES_TOTAL
            and all(
                item["bytes"] <= MAX_SOURCE_BYTES_EACH for item in lower_sources
            )
        ),
        "all_blob_objects_recomputed": all(
            item["git_blob_object_match"] for item in lower_sources
        ),
        "lower_pack_matches_upper": (
            lower_source_by_path[
                "app/companion_pendant/epaper/companion_visual_asset_pack.c"
            ]["sha256"]
            == UPPER_BINDINGS["upper_pack_source"][1]
            and lower_source_by_path[
                "app/companion_pendant/epaper/companion_visual_asset_pack.h"
            ]["sha256"]
            == UPPER_BINDINGS["upper_pack_header"][1]
        ),
        "state_identity_17_of_17": (
            len(state_rows) == 17
            and all(row["identity_status"] == "mapped" for row in state_rows)
        ),
        "transition_identity_21_of_21": (
            len(upper_transition_rows) == 21
            and lower_transition_rows == upper_transition_rows
        ),
        "upper_oracle_59_pairs_10_noops": (
            len(pair_rows) == 59 and len(noop_rows) == 10
        ),
        "physical_guards_separate": (
            boundary["physical_comp_req_472_mapping"]["double_tap_gap_ms"] == 650
            and boundary["physical_comp_req_472_mapping"][
                "double_tap_move_px_max"
            ]
            == 40
            and boundary["physical_comp_req_472_mapping"]["hold_feedback_ms"]
            == 650
            and boundary["physical_comp_req_472_mapping"]["menu_entry_ms"]
            == 3000
        ),
        "upper_polarity_contract_parsed": (
            visual_contract["format"]["black_bit"] == 1
            and visual_contract["format"]["white_bit"] == 0
        ),
        "panel_polarity_observed": panel_white_one_black_zero,
        "converted_oracle_17_frames_59_pairs": converted_oracle_pass,
        "converted_centered_sha_exact": centered_converted_sha
        == EXPECTED_CONVERTED_CENTERED_SHA256,
        "call_graph_extracted": main_node is not None and len(graph.functions) > 20,
        "call_paths_are_non_circular": all(
            len(path) == len(set(path))
            for path in (
                gesture_path,
                main_to_service,
                main_to_enqueue_gesture,
                enqueue_gesture_to_map,
                enqueue_gesture_to_queue,
                main_to_enqueue_visual_event,
                enqueue_visual_event_to_queue,
            )
            if path
        ),
    }
    audit_errors = [
        name for name, passed in structural_checks.items() if not passed
    ]

    compatibility_blockers = []
    if not polarity_bridge_realizable:
        compatibility_blockers.append(
            "no realizable production logical-to-panel inversion path from "
            "centered initialization and runtime service into build/emit"
        )
    if service_node is None:
        compatibility_blockers.append(
            "no production companion_visual_runtime_service definition is "
            "available to realize queue/pop/build/emit"
        )
    if initial_uses_locked_r7_baseline:
        compatibility_blockers.append(
            "visual initialization displays locked R7 baseline instead of "
            "converted accepted centered_rest"
        )
    if direct_logical_payload_emit:
        compatibility_blockers.append(
            "0x24 transport receives logical upper payload bytes without inversion"
        )
    if qualification_all_gaze_16 and gaze_coalescing:
        compatibility_blockers.append(
            "bounded qualification enqueues 16 GAZE events into a coalescing "
            "queue and therefore qualifies only one effective event"
        )
    if not valid_qualification_sequence:
        compatibility_blockers.append(
            "no valid 16-event declared-transition qualification sequence"
        )
    if pop_before_emit_terminal_loss:
        compatibility_blockers.append(
            "service pops before build/emit and has no fail-path rollback, so "
            "failed output loses menu/recording terminal events"
        )
    if not build_failure_terminal_latched:
        compatibility_blockers.append(
            "pre-transport build-window failure retains the event without a "
            "terminal latch or discard, so service can repeat the same build"
        )
    if not frame_lookup_failure_terminal_latched:
        compatibility_blockers.append(
            "pre-transport frame lookup failure retains the event without a "
            "terminal latch or discard"
        )
    if missing_events or ambiguous_events:
        compatibility_blockers.append(
            f"{missing_events} missing and {ambiguous_events} ambiguous accepted "
            "event mappings include center/cancel/settle/menu/recording returns"
        )
    if realizable_events != 21:
        compatibility_blockers.append(
            f"only {realizable_events}/21 event rows have complete call-edge paths"
        )
    if realizable_pairs != 59:
        compatibility_blockers.append(
            f"only {realizable_pairs}/59 converted pairs are lower-realizable"
        )
    if realizable_noops != 10:
        compatibility_blockers.append(
            f"only {realizable_noops}/10 semantic pixel no-ops are lower-realizable"
        )

    comparison_complete = bool(
        not audit_errors
        and not compatibility_blockers
        and realizable_events == 21
        and realizable_pairs == 59
        and realizable_noops == 10
        and polarity_bridge_realizable
        and terminal_retention
        and valid_qualification_sequence
    )
    if audit_errors:
        status = "NO_GO_AUDIT_INTEGRITY"
    elif comparison_complete:
        status = "PASS_UPPER_LOWER_COMPATIBLE"
    elif (
        polarity_bridge_realizable
        and terminal_retention
        and valid_qualification_sequence
    ):
        status = "NO_GO_UPPER_LOWER_EVENT_PATH_GAPS"
    else:
        status = "NO_GO_UPPER_LOWER_POLARITY_EVENT_TERMINAL_GAPS"
    c692_expected_failure = bool(
        lower_commit == DEFAULT_LOWER_COMMIT
        and status == "NO_GO_UPPER_LOWER_POLARITY_EVENT_TERMINAL_GAPS"
        and centered_converted_sha == EXPECTED_CONVERTED_CENTERED_SHA256
        and qualification_effective_events == 1
        and initial_uses_locked_r7_baseline
        and direct_logical_payload_emit
        and pop_before_emit_terminal_loss
        and not polarity_bridge_realizable
        and required_return_event_gaps == sorted(missing_return_events)
        and realizable_events == 0
        and realizable_pairs == 0
    )
    c173_failure_preserved = (
        None
        if lower_commit != LEGACY_NO_GO_COMMIT
        else status != "PASS_UPPER_LOWER_COMPATIBLE"
    )

    artifact = {
        "schema": "companion.upper-lower-compatibility-audit.v3",
        "requirements": [
            "COMP-REQ-474",
            "COMP-REQ-475",
            "COMP-REQ-476",
            "COMP-REQ-479",
            "COMP-REQ-486",
            "COMP-REQ-488",
        ],
        "status": status,
        "mode": "comparison" if args.comparison_mode else "default_audit",
        "comparison_exit_contract": (
            "exit 0 only when events=21/21, pairs=59/59, semantic_noops=10/10, "
            "polarity conversion, valid qualification, and terminal retention pass"
        ),
        "argument_bounds": {
            "lower_root": "exact Git toplevel",
            "expected_commit": "exact 40-hex commit",
            "output_directory": VALIDATION_DIR.as_posix(),
            "output_name_pattern": OUTPUT_NAME_RE.pattern,
            "max_source_files": MAX_SOURCE_FILES,
            "max_source_bytes_each": MAX_SOURCE_BYTES_EACH,
            "max_source_bytes_total": MAX_SOURCE_BYTES_TOTAL,
        },
        "upper_bindings": upper_identities,
        "lower_binding": {
            "lower_root": (
                "."
                if lower_root == repo_root
                else lower_root.as_posix()
            ),
            "expected_commit": args.expected_commit.lower(),
            "resolved_commit": lower_commit,
            "commit_object": {
                "bytes": len(commit_data),
                "recomputed_git_sha1": commit_recomputed,
                "matches_resolved_commit": commit_recomputed == lower_commit,
                "payload_sha256": sha256(commit_data),
            },
            "source_count": len(lower_sources),
            "source_bytes_total": total_source_bytes,
            "source_blobs": lower_sources,
        },
        "polarity_contract": {
            "upper": {
                "black_bit": visual_contract["format"]["black_bit"],
                "white_bit": visual_contract["format"]["white_bit"],
                "source": UPPER_BINDINGS["visual_contract"][0].as_posix(),
            },
            "panel": {
                "white_bit": 1,
                "black_bit": 0,
                "observed_from_source": panel_white_one_black_zero,
                "source": (
                    "app/companion_pendant/epaper/"
                    "panel_target_stm32wb_ssd1681.c"
                ),
            },
            "required_conversion": "panel_byte = logical_byte ^ 0xFF",
            "expected_converted_centered_sha256": (
                EXPECTED_CONVERTED_CENTERED_SHA256
            ),
            "observed_converted_centered_sha256": centered_converted_sha,
            "converted_centered_exact": centered_converted_sha
            == EXPECTED_CONVERTED_CENTERED_SHA256,
            "runtime_bridge": {
                "inversion_function_candidates": [
                    {
                        "function": graph.functions[node]["name"],
                        "definition": (
                            f"{graph.functions[node]['path']}:"
                            f"{graph.functions[node]['line']}"
                        ),
                    }
                    for node in inversion_nodes
                ],
                "service_inversion_path": graph.serialize_path(
                    service_inversion_path
                ),
                "build_inversion_path": graph.serialize_path(
                    build_inversion_path
                ),
                "build_converts_diff_and_payload": (
                    build_converts_diff_and_payload
                ),
                "conversion_before_build": conversion_before_build,
                "conversion_before_emit": conversion_before_emit,
                "initial_centered_conversion_path": (
                    graph.serialize_path(initial_conversion_evidence["path"])
                    if initial_conversion_evidence
                    else None
                ),
                "initialization_entry_path": (
                    graph.serialize_path(
                        graph.path(
                            initial_conversion_evidence["entry_node"],
                            initial_conversion_evidence["init_node"],
                        )
                    )
                    if initial_conversion_evidence
                    and initial_conversion_evidence["entry_node"]
                    else None
                ),
                "realizable": polarity_bridge_realizable,
                "direct_logical_payload_emit": direct_logical_payload_emit,
            },
            "current_initial_frame": {
                "locked_r7_baseline_sha256": sha256(r7_baseline),
                "expected_locked_r7_baseline_sha256": EXPECTED_R7_BASELINE_SHA256,
                "locked_baseline_hash_match": sha256(r7_baseline)
                == EXPECTED_R7_BASELINE_SHA256,
                "upper_centered_logical_sha256": sha256(centered_logical),
                "locked_vs_upper_logical_different_bytes": (
                    r7_vs_logical_diff_bytes
                ),
                "locked_r7_fallback_present": locked_r7_fallback_present,
                "initial_uses_converted_centered": (
                    initial_uses_converted_centered
                ),
                "initial_uses_locked_r7_baseline": (
                    initial_uses_locked_r7_baseline
                ),
            },
        },
        "converted_payload_oracle": {
            "derivation": (
                "independent bytewise inversion of accepted upper frames; "
                "lower source declarations are not used"
            ),
            "frame_count": len(converted_frames),
            "pair_count": len(converted_pair_rows),
            "pixel_noop_pair_count": sum(
                item["pixel_noop"] for item in converted_pair_rows
            ),
            "status": "PASS" if converted_oracle_pass else "NO_GO",
            "frames": converted_frames,
            "pairs": converted_pair_rows,
        },
        "call_graph": {
            "production_sources_only": True,
            "fixture_nodes_excluded": True,
            "function_count": len(graph.functions),
            "edge_count": sum(len(edges) for edges in graph.edges.values()),
            "main_to_gesture": graph.serialize_path(gesture_path),
            "main_to_enqueue_gesture": graph.serialize_path(
                main_to_enqueue_gesture
            ),
            "enqueue_gesture_to_map": graph.serialize_path(
                enqueue_gesture_to_map
            ),
            "enqueue_gesture_to_queue": graph.serialize_path(
                enqueue_gesture_to_queue
            ),
            "main_to_enqueue_visual_event": graph.serialize_path(
                main_to_enqueue_visual_event
            ),
            "enqueue_visual_event_to_queue": graph.serialize_path(
                enqueue_visual_event_to_queue
            ),
            "main_to_service": graph.serialize_path(main_to_service),
            "app_init_to_centered_conversion": (
                graph.serialize_path(
                    graph.path(
                        initial_conversion_evidence["entry_node"],
                        initial_conversion_evidence["inversion_node"],
                    )
                )
                if initial_conversion_evidence
                and initial_conversion_evidence["entry_node"]
                else None
            ),
            "direct_event_ingress_orchestrator": (
                {
                    "function": graph.functions[direct_ingress["node"]]["name"],
                    "definition": (
                        f"{graph.functions[direct_ingress['node']]['path']}:"
                        f"{graph.functions[direct_ingress['node']]['line']}"
                    ),
                    "gesture_path": graph.serialize_path(
                        direct_ingress["gesture_path"]
                    ),
                    "enqueue_gesture_path": graph.serialize_path(
                        direct_ingress["target_path"]
                    ),
                    "gesture_first_call_line": direct_ingress[
                        "gesture_first_call_line"
                    ],
                    "enqueue_first_call_line": direct_ingress[
                        "target_first_call_line"
                    ],
                    "ordered_or_shared_branch": direct_ingress[
                        "ordered_or_shared_branch"
                    ],
                }
                if direct_ingress
                else None
            ),
            "generic_event_ingress_orchestrator": (
                {
                    "function": graph.functions[generic_ingress["node"]]["name"],
                    "gesture_path": graph.serialize_path(
                        generic_ingress["gesture_path"]
                    ),
                    "dispatch_path": graph.serialize_path(
                        generic_ingress["target_path"]
                    ),
                    "ordered_or_shared_branch": generic_ingress[
                        "ordered_or_shared_branch"
                    ],
                }
                if generic_ingress
                else None
            ),
            "generic_dispatch": (
                {
                    "function": graph.functions[generic_dispatch_node]["name"],
                    "main_path": graph.serialize_path(
                        graph.path(main_node, generic_dispatch_node)
                    ),
                    "queue_path": graph.serialize_path(
                        graph.path(generic_dispatch_node, enqueue_node)
                    ),
                }
                if generic_dispatch_node
                else None
            ),
            "service_order": {
                "function": (
                    graph.functions[service_node]["name"] if service_node else None
                ),
                "pop_call_line": pop_line,
                "peek_call_line": peek_line,
                "discard_call_lines": discard_lines,
                "build_call_line": build_line,
                "emit_call_line": emit_line,
                "ordered_pop_build_emit": service_ordered,
                "legacy_pop_ordered": legacy_pop_ordered,
                "deferred_discard_ordered": deferred_discard_ordered,
                "terminal_retention": terminal_retention,
                "pretransport_build_failure_terminal_latched": (
                    build_failure_terminal_latched
                ),
                "pretransport_frame_lookup_failure_terminal_latched": (
                    frame_lookup_failure_terminal_latched
                ),
                "emit_failure_terminal_latched": (
                    emit_failure_terminal_latched
                ),
                "pop_before_emit_terminal_loss": pop_before_emit_terminal_loss,
                "rollback_present": rollback_present,
                "noop_semantic_commit": noop_semantic_commit,
            },
        },
        "qualification": {
            "requested_event_count": 16,
            "all_enqueued_as_gaze": qualification_all_gaze_16,
            "gaze_queue_coalescing": gaze_coalescing,
            "effective_event_count": qualification_effective_events,
            "valid_declared_transition_sequence": valid_qualification_sequence,
        },
        "c692_regression_findings": {
            "expected_only_for_commit": DEFAULT_LOWER_COMMIT,
            "required_center_cancel_settle_menu_recording_return_events": sorted(
                missing_return_events
            ),
            "observed_mapping_gaps": required_return_event_gaps,
            "all_required_gaps_observed": required_return_event_gaps
            == sorted(missing_return_events),
            "qualification_16_gaze_effective_one": (
                qualification_effective_events == 1
            ),
            "pop_before_emit_terminal_loss": pop_before_emit_terminal_loss,
            "pretransport_build_failure_terminal_latched": (
                build_failure_terminal_latched
            ),
            "pretransport_frame_lookup_failure_terminal_latched": (
                frame_lookup_failure_terminal_latched
            ),
            "emit_failure_terminal_latched": emit_failure_terminal_latched,
            "logical_payload_sent_without_inversion": direct_logical_payload_emit,
        },
        "root_cause_diagnostic": {
            "applies_to_commit": (
                lower_commit == COMP_REQ_488_DIAGNOSTIC_COMMIT
            ),
            "lower_mr_schema_or_claims_consumed": False,
            "mr_schema_change_can_affect_compatibility_result": False,
            "legacy_c692_qualification_tokens_affect_event_mapping": False,
            "pre_fix_false_negative": {
                "cause": (
                    "initialization reachability considered only main; the "
                    "Cube MX_APPE_Init asynchronous boundary kept APP_BLE_Init "
                    "outside that source-only reachability set"
                ),
                "corrected_production_entry": (
                    "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/"
                    "app_ble.c:592 APP_BLE_Init"
                ),
                "converted_centered_source_chain": (
                    "APP_BLE_Init:592 -> companion_epaper_panel_stm32wb_init:"
                    "19 -> companion_r7_runtime_bridge_init:330 -> "
                    "companion_visual_runtime_copy_panel_frame:43 -> "
                    "panel_byte:38"
                ),
            },
            "lower_self_test_scope": {
                "semantic_adapter_rows": (
                    "tools/comp_req_472_visual_runtime_fixture.c:237"
                ),
                "expanded_pair_window_loop": (
                    "tools/comp_req_472_visual_runtime_fixture.c:584"
                ),
                "limitation": (
                    "fixture proves adapter acceptance and window/payload "
                    "construction, not production input-to-event call sites"
                ),
            },
            "production_mapping_gaps": [
                {
                    "event": row["event"],
                    "status": row["mapping_status"],
                    "evidence": row["mapping_evidence"],
                }
                for row in event_rows
                if row["mapping_status"] != "mapped"
            ],
            "representative_pairs": [
                row
                for row in pair_rows
                if row["id"]
                in {
                    "T00-P00-centered_rest--gaze_left",
                    "T04-P00-centered_rest--gaze_center",
                    "T05-P00-gaze_left--gaze_left",
                    "T05-P01-gaze_left--gaze_up",
                    "T05-P04-gaze_left--gaze_center",
                    "T06-P04-gaze_center--centered_rest",
                    "T17-P00-menu_device--menu_device_ui_assets",
                }
            ],
        },
        "summary": {
            "states": {
                "total": len(state_rows),
                "identity_mapped": sum(
                    row["identity_status"] == "mapped" for row in state_rows
                ),
            },
            "events": {
                "total": len(event_rows),
                "mapping_mapped": mapped_events,
                "mapping_ambiguous": ambiguous_events,
                "mapping_missing": missing_events,
                "realizable": realizable_events,
            },
            "pairs": {
                "total": len(pair_rows),
                "pixel_noop": len(noop_rows),
                "realizable": realizable_pairs,
                "semantic_noop_realizable": realizable_noops,
            },
            "polarity_bridge_realizable": polarity_bridge_realizable,
            "terminal_retention": terminal_retention,
            "pretransport_build_failure_terminal_latched": (
                build_failure_terminal_latched
            ),
            "pretransport_frame_lookup_failure_terminal_latched": (
                frame_lookup_failure_terminal_latched
            ),
            "emit_failure_terminal_latched": emit_failure_terminal_latched,
            "qualification_valid": valid_qualification_sequence,
            "comparison_complete": comparison_complete,
            "c692_expected_no_go_signature": c692_expected_failure,
            "c173_no_go_preserved_when_selected": c173_failure_preserved,
        },
        "state_compatibility": state_rows,
        "event_compatibility": event_rows,
        "pair_compatibility": pair_rows,
        "structural_checks": structural_checks,
        "audit_errors": audit_errors,
        "compatibility_blockers": compatibility_blockers,
        "side_effect_counters": {
            "operator_execute": 0,
            "server_probe": 0,
            "server_start": 0,
            "browser_start": 0,
            "popup": 0,
            "operator_prompt": 0,
            "hardware": 0,
            "lower_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "read_only_git_processes": git.command_count,
            "upper_evidence_write": 1,
        },
        "generator": {
            "path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "sha256": file_sha(Path(__file__).resolve()),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(artifact))
    print(
        json.dumps(
            {
                "status": status,
                "mode": artifact["mode"],
                "events_realizable": f"{realizable_events}/21",
                "pairs_realizable": f"{realizable_pairs}/59",
                "noops_realizable": f"{realizable_noops}/10",
                "polarity_bridge": polarity_bridge_realizable,
                "terminal_retention": terminal_retention,
                "qualification_valid": valid_qualification_sequence,
                "c692_expected_no_go_signature": c692_expected_failure,
                "artifact_sha256": file_sha(output_path),
            },
            sort_keys=True,
        )
    )
    return 0 if comparison_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
