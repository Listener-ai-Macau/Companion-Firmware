"""ExpressionV1 policy for Companion screen state decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .card_renderer import EXPRESSION_COPY, EXPRESSION_KINDS, CardModel


LOW_BATTERY_PERCENT = 20
LOW_BATTERY_MILLIVOLTS = 3600
BATTERY_RECOVERED_PERCENT = 25
BATTERY_RECOVERED_MILLIVOLTS = 3600
OTA_LOW_BATTERY_BLOCKER_BIT = 3
RECORDING_ERROR_FLAG = 0x80
RECORDING_STATE_IDLE = 0
RECORDING_STATE_PENDING_START = 1
RECORDING_STATE_RECORDING = 2
RECORDING_STATE_STOPPING = 3
RECORDING_STATE_CANCELED = 4
RECORDING_STATE_TRANSFER_READY = 5
RECORDING_STATE_TRANSFER_ACTIVE = 6
RECORDING_STATE_TRANSFERRED = 7
RECORDING_STATE_ERROR_RECOVERY = 8
SCREEN_SETTINGS_QUIET_HOURS_FLAG = 0x0001
SCREEN_SETTINGS_MAX_BRIGHTNESS = 100
MINUTES_PER_DAY = 24 * 60

EXPRESSION_PRIORITIES = {
    "error": 100,
    "recording": 90,
    "low_battery": 80,
    "speaking": 70,
    "listening": 60,
    "thinking": 50,
    "sync_complete": 40,
    "happy": 30,
    "idle": 20,
    "sleepy": 10,
}

EVENT_EXPRESSION_MAP = {
    "wake_word.detected": ("listening", "wake word detected"),
    "wake_word.armed": ("idle", "wake word armed"),
    "wake_word.disabled": ("sleepy", "wake word disabled"),
    "speaker.prompt": ("speaking", "speaker prompt requested"),
    "speaker.result": ("happy", "speaker prompt completed"),
    "meeting.start": ("recording", "meeting capture started"),
    "meeting.stop": ("thinking", "meeting capture stopped; processing"),
    "meeting.finalize": ("sync_complete", "meeting artifact finalized"),
    "recording_fsm.start_request": ("recording", "recording start requested"),
    "recording_fsm.stop_request": ("thinking", "recording stop requested"),
    "recording_fsm.cancel_request": ("idle", "recording cancel requested"),
    "recording_fsm.transition": ("recording", "recording state transition"),
    "recording_fsm.session_finished": ("sync_complete", "recording stored for sync"),
    "recording_fsm.recovery": ("idle", "recording path recovered"),
    "e_paper.render_request": ("thinking", "display render requested"),
    "e_paper.update_result": ("happy", "display update completed"),
}


@dataclass(frozen=True)
class ExpressionDecision:
    expression: str
    source: str
    reason: str
    priority: int
    title: str
    body: str
    footer: str
    request_id: int = 0
    card_slot: int = 0
    display_flags: int = 0

    def as_card(self, card_id: str = "expression_policy") -> CardModel:
        return CardModel(
            card_id=card_id,
            card_type="expression",
            state=self.expression,
            title=self.title,
            body=self.body,
            footer=self.footer,
            request_id=self.request_id,
            card_slot=self.card_slot,
            display_flags=self.display_flags,
        )

    def as_manifest(self) -> dict[str, Any]:
        return asdict(self)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _section(snapshot: dict[str, Any], *names: str) -> dict[str, Any]:
    for name in names:
        value = snapshot.get(name)
        if isinstance(value, dict):
            return value
    return {}


def _decision(
    expression: str,
    source: str,
    reason: str,
    body: str | None = None,
    request_id: int = 0,
    card_slot: int = 0,
    display_flags: int = 0,
) -> ExpressionDecision:
    if expression not in EXPRESSION_KINDS:
        raise ValueError(f"unsupported expression: {expression}")
    title, default_body, footer = EXPRESSION_COPY[expression]
    return ExpressionDecision(
        expression=expression,
        source=source,
        reason=reason,
        priority=EXPRESSION_PRIORITIES[expression],
        title=title,
        body=body or default_body,
        footer=footer,
        request_id=request_id,
        card_slot=card_slot,
        display_flags=display_flags,
    )


def _choose(candidates: list[ExpressionDecision]) -> ExpressionDecision:
    if not candidates:
        return _decision("idle", "default", "no active screen signal")
    return max(candidates, key=lambda item: item.priority)


def is_low_battery(battery: dict[str, Any]) -> bool:
    percent = _as_int(battery.get("percent"), 101)
    millivolts = _as_int(battery.get("millivolts"), 5000)
    charger_present = _as_int(battery.get("charger_present"), 0) != 0
    return percent <= LOW_BATTERY_PERCENT or (millivolts < LOW_BATTERY_MILLIVOLTS and not charger_present)


def is_battery_recovered(battery: dict[str, Any]) -> bool:
    percent = _as_int(battery.get("percent"), -1)
    millivolts = _as_int(battery.get("millivolts"), 0)
    charger_present = _as_int(battery.get("charger_present"), 0) != 0
    return percent >= BATTERY_RECOVERED_PERCENT or (
        charger_present and millivolts >= BATTERY_RECOVERED_MILLIVOLTS
    )


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "active"}
    return _as_int(value, 0) != 0


def _minute_of_day(value: Any) -> int | None:
    minute = _as_int(value, -1)
    if minute < 0:
        return None
    return minute % MINUTES_PER_DAY


def is_quiet_hours_active(settings: dict[str, Any]) -> bool:
    if _as_bool(settings.get("quiet_hours_active")):
        return True
    flags = _as_int(settings.get("flags"), 0)
    if (flags & SCREEN_SETTINGS_QUIET_HOURS_FLAG) != 0:
        return True

    local_minute = _minute_of_day(settings.get("local_minute", settings.get("minute_of_day")))
    start = _minute_of_day(settings.get("quiet_hours_start_min", settings.get("quiet_hours_start")))
    end = _minute_of_day(settings.get("quiet_hours_end_min", settings.get("quiet_hours_end")))
    if local_minute is None or start is None or end is None or start == end:
        return False
    if start < end:
        return start <= local_minute < end
    return local_minute >= start or local_minute < end


def screen_settings_wants_sleepy(settings: dict[str, Any]) -> bool:
    if not settings:
        return False
    brightness = _as_int(settings.get("display_brightness"), SCREEN_SETTINGS_MAX_BRIGHTNESS)
    return brightness <= 0 or is_quiet_hours_active(settings)


def expression_from_status(snapshot: dict[str, Any]) -> ExpressionDecision:
    """Pick the visible ExpressionV1 face from a BLE/status snapshot."""

    candidates: list[ExpressionDecision] = []

    device = _section(snapshot, "device_status", "device")
    fault_bitmap = _as_int(device.get("fault_bitmap"), 0)
    active_mode = _as_int(device.get("active_mode"), 2)
    if fault_bitmap != 0:
        candidates.append(_decision("error", "device_status", f"fault_bitmap=0x{fault_bitmap:x}"))
    elif active_mode == 0:
        candidates.append(_decision("sleepy", "device_status", "device has no active link"))
    elif active_mode == 1:
        candidates.append(_decision("recording", "device_status", "audio stream mode is active"))

    settings = _section(snapshot, "settings", "screen_settings")
    if screen_settings_wants_sleepy(settings):
        candidates.append(_decision("sleepy", "settings", "quiet hours or display-off screen setting is active"))

    card_status = _section(snapshot, "e_paper_card_status", "card_status")
    card_error = _as_int(card_status.get("last_error"), 0)
    render_state = _as_int(card_status.get("render_state"), 0)
    if card_error != 0 or render_state >= 3:
        candidates.append(_decision("error", "e_paper_card_status", "display render failed"))

    battery = _section(snapshot, "battery_charge", "battery")
    if battery and is_low_battery(battery):
        candidates.append(_decision("low_battery", "battery_charge", "battery is below expression threshold"))

    ota = _section(snapshot, "ota_readiness")
    blocker_bitmap = _as_int(ota.get("blocker_bitmap"), 0)
    active_blockers = set(str(item) for item in ota.get("active_blockers", [])) if isinstance(ota.get("active_blockers"), list) else set()
    if "low_battery" in active_blockers or blocker_bitmap & (1 << OTA_LOW_BATTERY_BLOCKER_BIT):
        candidates.append(_decision("low_battery", "ota_readiness", "OTA low-battery blocker is active"))
    elif blocker_bitmap != 0:
        candidates.append(_decision("error", "ota_readiness", f"OTA blockers active: 0x{blocker_bitmap:x}"))

    recording_control = _section(snapshot, "recording_control")
    recording_command = _as_int(recording_control.get("command"), 0)
    recording_flags = _as_int(recording_control.get("privacy_flags"), 0)
    if recording_flags & RECORDING_ERROR_FLAG:
        candidates.append(_decision("error", "recording_control", "recording control returned error"))
    elif recording_command == 1:
        candidates.append(_decision("recording", "recording_control", "recording start accepted"))
    elif recording_command == 2:
        candidates.append(_decision("thinking", "recording_control", "recording stop accepted"))
    elif recording_command == 3:
        candidates.append(_decision("idle", "recording_control", "recording cancelled"))

    recording_status = _section(snapshot, "recording_status", "recording_fsm")
    recording_state = _as_int(recording_status.get("state"), RECORDING_STATE_IDLE)
    if recording_state in {RECORDING_STATE_PENDING_START, RECORDING_STATE_RECORDING}:
        candidates.append(_decision("recording", "recording_status", "recording state is active"))
    elif recording_state == RECORDING_STATE_STOPPING:
        candidates.append(_decision("thinking", "recording_status", "recording is stopping"))
    elif recording_state == RECORDING_STATE_CANCELED:
        candidates.append(_decision("idle", "recording_status", "recording was canceled"))
    elif recording_state in {
        RECORDING_STATE_TRANSFER_READY,
        RECORDING_STATE_TRANSFER_ACTIVE,
        RECORDING_STATE_TRANSFERRED,
    }:
        candidates.append(_decision("sync_complete", "recording_status", "recording is stored or syncing"))
    elif recording_state == RECORDING_STATE_ERROR_RECOVERY:
        candidates.append(_decision("error", "recording_status", "recording path is recovering from an error"))

    meeting = _section(snapshot, "meeting_status", "meeting")
    meeting_error = _as_int(meeting.get("last_error"), 0)
    meeting_state = _as_int(meeting.get("state"), 0)
    meeting_sync = _as_int(meeting.get("sync_state"), 0)
    meeting_summary = _as_int(meeting.get("summary_state"), 0)
    if meeting_error != 0:
        candidates.append(_decision("error", "meeting_status", "meeting status has last_error"))
    elif meeting_state == 1:
        candidates.append(_decision("recording", "meeting_status", "meeting is recording"))
    elif meeting_state == 2 or meeting_sync == 1:
        candidates.append(_decision("sync_complete", "meeting_status", "meeting sync is complete"))
    elif meeting_summary == 1:
        candidates.append(_decision("thinking", "meeting_status", "meeting summary is pending"))

    speaker = _section(snapshot, "speaker_status", "speaker")
    speaker_error = _as_int(speaker.get("last_error"), 0)
    speaker_state = _as_int(speaker.get("state"), 0)
    if speaker_error != 0:
        candidates.append(_decision("error", "speaker_status", "speaker status has last_error"))
    elif speaker_state == 2:
        candidates.append(_decision("speaking", "speaker_status", "speaker prompt accepted"))

    wake = _section(snapshot, "wake_word_status", "wake_word")
    wake_error = _as_int(wake.get("last_error"), 0)
    wake_event = _as_int(wake.get("last_event"), 0)
    wake_armed = _as_int(wake.get("armed"), 0)
    wake_engine = _as_int(wake.get("engine_state"), 0)
    if wake_error != 0:
        candidates.append(_decision("error", "wake_word_status", "wake word status has last_error"))
    elif wake_event == 2:
        candidates.append(_decision("listening", "wake_word_status", "wake word detected"))
    elif wake_armed != 0 or wake_engine == 1:
        candidates.append(_decision("idle", "wake_word_status", "wake word is armed"))

    return _choose(candidates)


def expression_from_event(event_name: str, payload: dict[str, Any] | None = None) -> ExpressionDecision:
    """Map a diagnostic or host event name into an ExpressionV1 face."""

    payload = payload or {}
    event = event_name.strip().lower()
    if event == "battery_charging.sample" and is_low_battery(payload):
        return _decision("low_battery", event, "battery sample crossed low threshold")
    if event == "battery_charging.sample" and is_battery_recovered(payload):
        return _decision("idle", event, "battery sample recovered above expression threshold")
    if event == "e_paper.update_result" and _as_int(payload.get("last_error", payload.get("arg1")), 0) != 0:
        return _decision("error", event, "display update returned an error")
    if event.endswith(".rejected") or event.endswith(".error") or event.startswith("errors."):
        return _decision("error", event, "event is an error or rejection")

    mapped = EVENT_EXPRESSION_MAP.get(event)
    if mapped is None:
        return _decision("idle", event or "event", "event has no expression override")
    expression, reason = mapped
    return _decision(expression, event, reason)


def policy_fixture_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "status_idle_wake_armed",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "wake_word_status": {"armed": 1, "engine_state": 1}},
            "expected_expression": "idle",
        },
        {
            "case_id": "status_sleepy_no_link",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 0}},
            "expected_expression": "sleepy",
        },
        {
            "case_id": "status_device_fault",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 1, "fault_bitmap": 1}},
            "expected_expression": "error",
        },
        {
            "case_id": "status_quiet_hours_sleepy",
            "input_type": "status",
            "input": {
                "device_status": {"active_mode": 2},
                "settings": {"quiet_hours_start_min": 1320, "quiet_hours_end_min": 420, "local_minute": 30},
            },
            "expected_expression": "sleepy",
        },
        {
            "case_id": "status_display_off_sleepy",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "settings": {"display_brightness": 0}},
            "expected_expression": "sleepy",
        },
        {
            "case_id": "status_quiet_hours_recording_visible",
            "input_type": "status",
            "input": {
                "device_status": {"active_mode": 2},
                "settings": {"quiet_hours_active": True, "display_brightness": 0},
                "recording_control": {"command": 1, "privacy_flags": 0},
            },
            "expected_expression": "recording",
        },
        {
            "case_id": "status_wake_detected",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "wake_word_status": {"armed": 1, "last_event": 2}},
            "expected_expression": "listening",
        },
        {
            "case_id": "status_speaker_prompt",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "speaker_status": {"state": 2, "last_error": 0}},
            "expected_expression": "speaking",
        },
        {
            "case_id": "status_meeting_recording",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "meeting_status": {"state": 1, "last_error": 0}},
            "expected_expression": "recording",
        },
        {
            "case_id": "status_recording_fsm_active",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "recording_status": {"state": RECORDING_STATE_RECORDING}},
            "expected_expression": "recording",
        },
        {
            "case_id": "status_recording_fsm_stopping",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "recording_status": {"state": RECORDING_STATE_STOPPING}},
            "expected_expression": "thinking",
        },
        {
            "case_id": "status_recording_fsm_transfer_ready",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "recording_status": {"state": RECORDING_STATE_TRANSFER_READY}},
            "expected_expression": "sync_complete",
        },
        {
            "case_id": "status_recording_fsm_error_recovery",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "recording_status": {"state": RECORDING_STATE_ERROR_RECOVERY}},
            "expected_expression": "error",
        },
        {
            "case_id": "status_meeting_sync_complete",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "meeting_status": {"state": 2, "sync_state": 1}},
            "expected_expression": "sync_complete",
        },
        {
            "case_id": "status_meeting_summary_pending",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "meeting_status": {"state": 0, "summary_state": 1, "sync_state": 0}},
            "expected_expression": "thinking",
        },
        {
            "case_id": "status_meeting_error",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "meeting_status": {"state": 1, "last_error": 2}},
            "expected_expression": "error",
        },
        {
            "case_id": "status_low_battery",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "battery_charge": {"percent": 12, "millivolts": 3520, "charger_present": 0}},
            "expected_expression": "low_battery",
        },
        {
            "case_id": "event_battery_recovered",
            "input_type": "event",
            "event_name": "battery_charging.sample",
            "input": {"percent": 27, "millivolts": 3650, "charger_present": 0},
            "expected_expression": "idle",
        },
        {
            "case_id": "event_battery_near_threshold_no_recovery",
            "input_type": "event",
            "event_name": "battery_charging.sample",
            "input": {"percent": 22, "millivolts": 3650, "charger_present": 0},
            "expected_expression": "idle",
        },
        {
            "case_id": "status_ota_low_battery_blocker",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "ota_readiness": {"blocker_bitmap": 1 << OTA_LOW_BATTERY_BLOCKER_BIT}},
            "expected_expression": "low_battery",
        },
        {
            "case_id": "status_ota_wrong_board_blocker",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "ota_readiness": {"blocker_bitmap": 1 << 4}},
            "expected_expression": "error",
        },
        {
            "case_id": "status_display_error",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "e_paper_card_status": {"render_state": 3, "last_error": 2}},
            "expected_expression": "error",
        },
        {
            "case_id": "status_speaker_error",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "speaker_status": {"state": 2, "last_error": 2}},
            "expected_expression": "error",
        },
        {
            "case_id": "status_wake_error",
            "input_type": "status",
            "input": {"device_status": {"active_mode": 2}, "wake_word_status": {"last_error": 2}},
            "expected_expression": "error",
        },
        {
            "case_id": "event_meeting_stop_processing",
            "input_type": "event",
            "event_name": "meeting.stop",
            "input": {"arg0": 1},
            "expected_expression": "thinking",
        },
        {
            "case_id": "event_speaker_result_happy",
            "input_type": "event",
            "event_name": "speaker.result",
            "input": {"arg0": 1},
            "expected_expression": "happy",
        },
    ]


def decide_policy_case(case: dict[str, Any]) -> ExpressionDecision:
    if case.get("input_type") == "event":
        return expression_from_event(str(case.get("event_name", "")), dict(case.get("input", {})))
    return expression_from_status(dict(case.get("input", {})))
