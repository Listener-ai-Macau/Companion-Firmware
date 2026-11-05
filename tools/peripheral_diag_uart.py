"""Bounded diagnostic console commands and atomic operator-state updates."""
import json
from pathlib import Path
import time


def send_line(link, text: str) -> None:
    data = (text + "\n").encode("ascii")
    if len(data) > 64 or "\r" in text or "\n" in text:
        raise ValueError("Invalid diagnostic command line")
    for byte in data:
        link.write(bytes([byte]))
        link.flush()
        time.sleep(.003)


def write_json_atomic(path: Path, value) -> None:
    """Keep the old complete state until replacement, tolerating short Windows reads."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    deadline = time.monotonic() + .5
    while True:
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.02)
