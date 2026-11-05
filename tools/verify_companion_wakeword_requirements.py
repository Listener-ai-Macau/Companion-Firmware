#!/usr/bin/env python3
"""Keep the Companion local wake-word requirement boundary explicit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "docs" / "companion_wakeword_requirements.md"
PLAN = ROOT / "docs" / "companion_screen_project_plan.md"
MEMORY_POLICY = ROOT / "docs" / "companion_resource_memory_policy.md"
OTA_CONTRACT = ROOT / "docs" / "companion_ota_component_contract.json"
FIXTURE = ROOT / "docs" / "validation" / "companion-wakeword-requirements.json"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()

    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    memory_policy = MEMORY_POLICY.read_text(encoding="utf-8")
    ota_contract = json.loads(OTA_CONTRACT.read_text(encoding="utf-8"))
    errors: list[str] = []

    required_anchors = [
        "当前 WB55 只有",
        "不是**真实关键词识别",
        "PCM16",
        "16 kHz",
        "VAD",
        "portable KWS engine",
        "RAM-only pre-roll",
        "privacy_blocked",
        "model_assets",
        "OTA 传输、刷写或真机 OTA 验收",
        "STM32Cube AI",
        "WBA55/WBA65",
        "false accept rate",
        "false reject rate",
    ]
    for anchor in required_anchors:
        require(anchor in requirements, f"wake-word requirement missing: {anchor}", errors)

    require("SCR-18" in plan, "project plan does not register SCR-18", errors)
    require("model_assets" in memory_policy, "external model policy drifted", errors)

    components = {component["kind"]: component for component in ota_contract["components"]}
    model = components.get("model_assets")
    require(model is not None, "OTA contract lacks model_assets component", errors)
    if model is not None:
        require(model.get("storage") == "external_nor", "model_assets must stay external", errors)
        require(
            model.get("activation") == "atomic_boot_meta_a_b_after_full_verification",
            "model_assets activation must remain atomic",
            errors,
        )

    result = {
        "schema_id": "companion.wakeword.requirements.v1",
        "status": "PASS" if not errors else "FAIL",
        "implementation_status": "planned_real_kws; current_gatt_control_and_simulation_only",
        "audio_contract": "PCM16 mono 16 kHz fixed timestamped frames",
        "runtime_architecture": "PDM/DMA adapter -> normalize -> VAD -> portable KWS -> debounce/cooldown -> RAM pre-roll -> recording/ASR",
        "storage": {
            "engine_code": "internal_flash",
            "replaceable_models": "external_nor model_assets",
            "persistent_audio": "external_nor recording_cache only after approved recording flow",
        },
        "ota_status": "requirements_only; implementation frozen pending Listener/Denzic platform gate",
        "portability": "WB55/WBA target audio adapters share HAL-free PCM/KWS core",
        "errors": errors,
    }

    if args.write_fixture:
        FIXTURE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
