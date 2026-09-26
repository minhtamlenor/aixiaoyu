"""Optional Xiaoxiao TTS adapter for Chinese Chat Mode.

Uses the same Microsoft Edge neural voice as Xiang Xiang HSK:
zh-CN-XiaoxiaoNeural. The existing Gemini audio path remains the fallback.
"""
import asyncio
import shutil
import tempfile
from pathlib import Path

import edge_tts


VOICE = "zh-CN-XiaoxiaoNeural"


def is_chinese_text(text: str) -> bool:
    """Return True when the response is predominantly Chinese, not Vietnamese."""
    if not text:
        return False
    hanzi = sum(1 for char in text if "\u3400" <= char <= "\u9fff")
    latin = sum(1 for char in text if ("a" <= char.lower() <= "z"))
    return hanzi > 0 and hanzi >= latin


async def synthesize_xiaoxiao_pcm(text: str) -> bytes:
    """Synthesize Mandarin to mono 24 kHz signed 16-bit PCM for sounddevice."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Không tìm thấy ffmpeg trong PATH; sẽ dùng audio Gemini dự phòng.")

    with tempfile.TemporaryDirectory(prefix="xiaoyu-xiaoxiao-") as folder:
        mp3_path = Path(folder) / "xiaoxiao.mp3"
        communicate = edge_tts.Communicate(
            text,
            VOICE,
            rate="-5%",
            volume="+0%",
        )
        await asyncio.wait_for(communicate.save(str(mp3_path)), timeout=35)

        process = await asyncio.create_subprocess_exec(
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(mp3_path),
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "24000",
            "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=25)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError("FFmpeg chuyển audio Xiaoxiao quá thời gian.")

        if process.returncode != 0 or not stdout:
            detail = stderr.decode("utf-8", errors="replace")[-1000:]
            raise RuntimeError(f"FFmpeg không giải mã được audio Xiaoxiao: {detail}")

        return stdout
