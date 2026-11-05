"""Present actual IMU movement and static-face progress without a board handle."""
from __future__ import annotations

import math


def parse_live_sample(line):
    sample = dict(word.split("=", 1) for word in line.split()[1:] if "=" in word)
    required = ("ms", "ax", "ay", "az", "gx", "gy", "gz", "temp_x10", "io", "int")
    missing = [key for key in required if key not in sample]
    if not line.startswith("IMU_LIVE ") or missing:
        raise ValueError("Incomplete IMU UART record; missing=" + ",".join(missing))
    try:
        for key in required:
            int(sample[key], 16 if key == "io" else 10)
    except ValueError as error:
        raise ValueError("Invalid numeric IMU UART record") from error
    return sample


def face(sample):
    acceleration = [int(sample[k]) for k in ("ax", "ay", "az")]
    norm = math.sqrt(sum(a * a for a in acceleration))
    major = max(range(3), key=lambda k: abs(acceleration[k]))
    if (850 <= norm <= 1150 and max(abs(int(sample[k])) for k in ("gx", "gy", "gz")) < 8000
            and all(abs(a) < 300 for k, a in enumerate(acceleration) if k != major)):
        return "xyz"[major] + ("+" if acceleration[major] > 0 else "-")
    return None


def live_feedback(sample, held, current_face, hold_start):
    acceleration = [int(sample[k]) for k in ("ax", "ay", "az")]
    norm = math.sqrt(sum(a * a for a in acceleration))
    moving = max(abs(int(sample[k])) for k in ("gx", "gy", "gz")) >= 8000
    hold_ms = max(0, int(sample["ms"]) - hold_start) if current_face and hold_start is not None else 0
    tilt = math.degrees(math.acos(min(1., max(abs(a) for a in acceleration) / norm))) if norm else None
    recorded = current_face in held if current_face else False
    if moving:
        status = "转动正在响应：停稳后再记录方向"
        cue = "先把屏幕或一个边朝上，停稳约2秒。"
    elif current_face and recorded:
        status = "这个方向已记录，请换一个面"
        cue = "已经做过的方向不会重复增加进度。"
    elif current_face:
        status = "方向已对正，请保持不动"
        cue = f"停稳进度：{min(hold_ms, 1500) / 1000:.1f} / 1.5 秒"
    elif 850 <= norm <= 1150:
        status = "当前是斜放：传感器仍在正常反馈"
        cue = f"离最近的平放方向约 {tilt:.0f}°，请把一个面放平或一个边立正。"
    else:
        status = "姿态正在变化：先轻轻放稳"
        cue = "平放或立正后，保持约2秒再换面。"
    return {
        "status": status,
        "live": f"{cue}\n已记录 {len(held)} / 6 个方向；右侧圆点随实际倾斜变化。",
        "color": "green",
        "imuVisual": {
            "moving": moving, "gravityX": acceleration[0] / norm if norm else 0.,
            "gravityY": acceleration[1] / norm if norm else 0.,
            "sampleMs": int(sample["ms"]), "tiltDegrees": round(tilt, 1) if tilt is not None else None,
            "holdPercent": 100 if recorded else min(100, hold_ms * 100 // 1500),
            "heldCount": len(held), "caption": "正在转动" if moving else "姿态实时反馈",
        },
    }
