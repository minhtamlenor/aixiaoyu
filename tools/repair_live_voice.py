"""
One-time repair for the local live_voice.py.

This script deliberately rebuilds live_voice.py from origin/main instead of
editing the user's possibly broken local copy. It applies only two targeted
changes:
1. Preserve input transcription when Gemini marks the model response as
   interrupted (do not discard the user's speech).
2. Use the existing Vietnam-time helper for startup/farewell time decisions.

Run from the repository root after `git pull origin main`:
    python tools/repair_live_voice.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "live_voice.py"


def get_origin_version() -> str:
    result = subprocess.run(
        ["git", "show", "origin/main:live_voice.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Không thể sửa {label}: tìm thấy {count} lần, cần đúng 1 lần."
        )
    return text.replace(old, new, 1)


def main() -> None:
    text = get_origin_version()

    # --------------------------------------------------------
    # Vietnam time helper
    # --------------------------------------------------------
    text = replace_once(
        text,
        "from tools.time_tool import get_time_text",
        "from tools.time_tool import get_time_text, get_current_time",
        "import time helper",
    )

    # Startup greeting: use the real Vietnam time helper.
    text = replace_once(
        text,
        '''    hour = datetime.now().hour\n\n    if hour < 7:\n        time_hint = "Đây là buổi sáng sớm."\n    else:\n        time_hint = ""\n''',
        '''    now = get_current_time()\n    hour = now["hour"]\n    time_hint = (\n        f"Hiện tại là {now['spoken_time']}. "\n        f"Đây là {now['period']}."\n    )\n''',
        "startup time",
    )

    # Farewell/night-time decision: same Vietnam time source.
    text = replace_once(
        text,
        "    hour = datetime.now().hour\n\n    if hour >= 21:\n",
        '    hour = get_current_time()["hour"]\n\n    if hour >= 21:\n',
        "farewell time",
    )

    # --------------------------------------------------------
    # Critical Live API bug fix:
    # an interrupted model response can contain the user's new
    # input transcription. The old `continue` discarded it.
    # --------------------------------------------------------
    text = replace_once(
        text,
        '''        if getattr(server, "interrupted", False):\n            print("🛑 Tiểu Vũ bị Lão sư ngắt lời.", flush=True)\n            continue\n\n        input_text = getattr(\n''',
        '''        if getattr(server, "interrupted", False):\n            print("🛑 Tiểu Vũ bị Lão sư ngắt lời.", flush=True)\n            # Do not continue here. Gemini may include the user's\n            # input transcription in the same interrupted response.\n\n        input_text = getattr(\n''',
        "interrupted input handling",
    )

    # Safety check: no conflict markers and valid Python before writing.
    for marker in ("<<<<<<<", "=======", ">>>>>>>"):
        if marker in text:
            raise RuntimeError(f"Phát hiện merge-conflict marker: {marker}")

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8", newline="\n")

    print("✅ Đã tạo lại live_voice.py từ origin/main.")
    print("✅ Đã giữ nguyên framework/personality/lesson flow/audio pipeline.")
    print("✅ Đã sửa lỗi bỏ qua input khi model bị ngắt lời.")
    print("✅ Đã đồng bộ logic giờ với Asia/Ho_Chi_Minh.")
    print("✅ Python syntax: OK")


if __name__ == "__main__":
    main()
