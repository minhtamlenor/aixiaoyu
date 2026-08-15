"""
One-time repair for the local live_voice.py.

The script rebuilds live_voice.py from origin/main and applies only targeted
Live API fixes. It never copies from the user's experimental local version.

Fixes:
1. Do not discard input transcription when Gemini marks a model response
   interrupted (barge-in).
2. Explicitly enable automatic VAD with conservative speech-start and
   speech-end settings.
3. Keep input/output audio transcription enabled.
4. Use the existing Vietnam-time helper for startup/farewell decisions.

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

    text = replace_once(
        text,
        '''    hour = datetime.now().hour\n\n    if hour < 7:\n        time_hint = "Đây là buổi sáng sớm."\n    else:\n        time_hint = ""\n''',
        '''    now = get_current_time()\n    hour = now["hour"]\n    time_hint = (\n        f"Hiện tại là {now['spoken_time']}. "\n        f"Đây là {now['period']}."\n    )\n''',
        "startup time",
    )

    text = replace_once(
        text,
        "    hour = datetime.now().hour\n\n    if hour >= 21:\n",
        '    hour = get_current_time()["hour"]\n\n    if hour >= 21:\n',
        "farewell time",
    )

    # --------------------------------------------------------
    # Critical Live API barge-in fix.
    # --------------------------------------------------------
    text = replace_once(
        text,
        '''        if getattr(server, "interrupted", False):\n            print("🛑 Tiểu Vũ bị Lão sư ngắt lời.", flush=True)\n            continue\n\n        input_text = getattr(\n''',
        '''        if getattr(server, "interrupted", False):\n            print("🛑 Tiểu Vũ bị Lão sư ngắt lời.", flush=True)\n            # Do not continue here. The same server_content can carry the\n            # user's input transcription after a barge-in.\n\n        input_text = getattr(\n''',
        "interrupted input handling",
    )

    # --------------------------------------------------------
    # Explicit automatic VAD.
    # This follows Google's Live API configuration instead of relying on
    # implicit defaults. The values are intentionally modest so normal speech
    # is detected without making the assistant trigger on tiny noise bursts.
    # --------------------------------------------------------
    text = replace_once(
        text,
        '''        tools=[tools],\n        input_audio_transcription={},\n        output_audio_transcription={},\n    )\n''',
        '''        tools=[tools],\n        input_audio_transcription={},\n        output_audio_transcription={},\n        realtime_input_config=types.RealtimeInputConfig(\n            automatic_activity_detection=types.AutomaticActivityDetection(\n                disabled=False,\n                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,\n                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,\n                prefix_padding_ms=20,\n                silence_duration_ms=100,\n            )\n        ),\n    )\n''',
        "automatic VAD",
    )

    # Safety check: reject actual conflict markers, not a bare separator line.
    if "<<<<<<< " in text or ">>>>>>> " in text:
        raise RuntimeError("Phát hiện merge-conflict marker trong origin/main")

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8", newline="\n")

    print("✅ Đã tạo lại live_voice.py từ origin/main.")
    print("✅ Giữ nguyên personality / Chat Mode / Tutor Mode / lesson flow.")
    print("✅ Đã sửa barge-in để không bỏ qua input của Lão sư.")
    print("✅ Đã bật explicit automatic VAD theo Live API.")
    print("✅ Đã giữ input/output audio transcription.")
    print("✅ Đã đồng bộ giờ Asia/Ho_Chi_Minh.")
    print("✅ Python syntax: OK")


if __name__ == "__main__":
    main()
