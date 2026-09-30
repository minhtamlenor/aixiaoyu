#!/usr/bin/env python3
"""
小雨 Chinese STT Diagnostic
===========================

Standalone diagnostic tool. It does NOT import or modify the main Xiaoyu
voice runtime.

Purpose:
  1. Record short Mandarin sentences from the selected microphone.
  2. Send each clip to the same Groq Whisper model used by voice.py.
  3. Force language=zh so we can measure Mandarin recognition separately
     from the main chat-mode auto-detection/fallback logic.
  4. Print the transcript and basic Whisper quality metrics.

Usage:
    python tools/test_chinese_stt.py

Optional:
    python tools/test_chinese_stt.py --mic 1
    python tools/test_chinese_stt.py --model whisper-large-v3-turbo
    python tools/test_chinese_stt.py --threshold 240

Environment:
    GROQ_API_KEY must be set.

The script uses the existing project dependencies:
    sounddevice
    groq
    python-dotenv (optional)
"""

from __future__ import annotations

import argparse
import io
import math
import os
import struct
import sys
import time
import wave
from pathlib import Path

try:
    import sounddevice as sd
except ImportError:
    print("ERROR: thiếu sounddevice. Chạy: pip install sounddevice", flush=True)
    raise

try:
    from groq import Groq
except ImportError:
    print("ERROR: thiếu groq. Chạy: pip install groq", flush=True)
    raise

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass


INPUT_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 512
FRAME_MS = BLOCKSIZE / INPUT_RATE * 1000

DEFAULT_MODEL = "whisper-large-v3-turbo"
DEFAULT_THRESHOLD = 240.0
DEFAULT_START_MS = 120
DEFAULT_END_SILENCE_MS = 750
DEFAULT_PREROLL_FRAMES = 5
DEFAULT_MIN_SPEECH_MS = 250
DEFAULT_MAX_SPEECH_MS = 12000

TEST_SENTENCES = [
    ("你好。", "nǐ hǎo", "Xin chào"),
    ("你叫什么名字？", "nǐ jiào shénme míngzi", "Bạn tên là gì?"),
    ("我叫小明。", "wǒ jiào Xiǎomíng", "Tôi tên là Tiểu Minh."),
    ("今天星期几？", "jīntiān xīngqī jǐ", "Hôm nay là thứ mấy?"),
    ("我想学习中文。", "wǒ xiǎng xuéxí Zhōngwén", "Tôi muốn học tiếng Trung."),
    ("你喜欢喝咖啡吗？", "nǐ xǐhuan hē kāfēi ma", "Bạn có thích uống cà phê không?"),
    ("我昨天没有上班。", "wǒ zuótiān méiyǒu shàngbān", "Hôm qua tôi không đi làm."),
    ("我现在有一点困。", "wǒ xiànzài yǒu yìdiǎn kùn", "Bây giờ tôi hơi buồn ngủ."),
    ("我们今天学习第一课。", "wǒmen jīntiān xuéxí dì yī kè", "Hôm nay chúng ta học bài 1."),
    ("小雨，你听得懂我说话吗？", "Xiǎoyǔ, nǐ tīng de dǒng wǒ shuōhuà ma", "Tiểu Vũ, bạn có hiểu tôi nói không?"),
]


def rms(pcm: bytes) -> float:
    if not pcm:
        return 0.0
    count = len(pcm) // 2
    if count <= 0:
        return 0.0
    samples = struct.unpack(f"<{count}h", pcm)
    return math.sqrt(sum(x * x for x in samples) / count)


def pcm_to_wav(pcm: bytes) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(INPUT_RATE)
        wf.writeframes(pcm)
    return out.getvalue()


def trim_silence(pcm: bytes, threshold: float) -> bytes:
    if not pcm:
        return pcm

    frame_bytes = BLOCKSIZE * 2
    frames = [
        pcm[i:i + frame_bytes]
        for i in range(0, len(pcm), frame_bytes)
        if pcm[i:i + frame_bytes]
    ]
    active = [rms(frame) >= threshold for frame in frames]

    if not any(active):
        return b""

    first = next(i for i, value in enumerate(active) if value)
    last = len(active) - 1 - next(
        i for i, value in enumerate(reversed(active)) if value
    )

    first = max(0, first - 1)
    last = min(len(frames) - 1, last + 1)

    return b"".join(frames[first:last + 1])


def list_mics() -> None:
    print("\n🎙️ MICROPHONE DEVICES")
    print("=" * 72)
    for index, device in enumerate(sd.query_devices()):
        if device.get("max_input_channels", 0) > 0:
            print(
                f"[{index}] {device['name']} "
                f"(inputs={device['max_input_channels']}, "
                f"default_sr={device.get('default_samplerate')})"
            )
    print("=" * 72)


def record_until_silence(
    device: int | None,
    threshold: float,
    start_ms: int,
    end_silence_ms: int,
    preroll_frames: int,
    min_speech_ms: int,
    max_speech_ms: int,
) -> bytes:
    import queue

    q: queue.Queue[bytes] = queue.Queue(maxsize=100)
    preroll: list[bytes] = []

    def callback(indata, frames, time_info, status):
        if status:
            print(f"\n⚠️ MIC: {status}", flush=True)
        try:
            q.put_nowait(bytes(indata))
        except queue.Full:
            try:
                q.get_nowait()
            except queue.Empty:
                pass
            try:
                q.put_nowait(bytes(indata))
            except queue.Full:
                pass

    stream_kwargs = dict(
        samplerate=INPUT_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=BLOCKSIZE,
        callback=callback,
    )
    if device is not None:
        stream_kwargs["device"] = device

    with sd.RawInputStream(**stream_kwargs):
        # Wait for speech.
        while True:
            frame = q.get()
            preroll.append(frame)
            if len(preroll) > preroll_frames:
                preroll.pop(0)

            if rms(frame) < threshold:
                continue

            candidate = list(preroll)
            active_ms = FRAME_MS

            while active_ms < start_ms:
                next_frame = q.get()
                candidate.append(next_frame)

                if rms(next_frame) >= threshold:
                    active_ms += FRAME_MS
                else:
                    active_ms = 0
                    candidate = candidate[-preroll_frames:]

            print("\n🟢 Bắt đầu bắt tiếng...", flush=True)

            audio = bytearray(b"".join(candidate))
            speech_ms = len(candidate) * FRAME_MS
            silence_ms = 0

            while speech_ms < max_speech_ms:
                frame = q.get()
                audio.extend(frame)
                speech_ms += FRAME_MS

                if rms(frame) >= threshold:
                    silence_ms = 0
                else:
                    silence_ms += FRAME_MS

                if silence_ms >= end_silence_ms:
                    break

            clean = trim_silence(bytes(audio), threshold)
            clean_ms = len(clean) / 2 / INPUT_RATE * 1000

            print(f"🔴 Kết thúc: {clean_ms:.0f} ms audio sạch", flush=True)

            if clean_ms < min_speech_ms:
                print("🟡 Đoạn nói quá ngắn / gần như im lặng.", flush=True)
                return b""

            return clean


def transcribe(client: Groq, pcm: bytes, model: str) -> dict:
    prompt = (
        "这是中文普通话语音识别测试。"
        "只转写说话者实际说出的中文，不要补充内容。"
        "不要生成广告、字幕、YouTube、故事或背景内容。"
        "保持原意，不要翻译成越南语。"
    )

    result = client.audio.transcriptions.create(
        file=("xiaoyu_test.wav", pcm_to_wav(pcm)),
        model=model,
        language="zh",
        response_format="verbose_json",
        temperature=0.0,
        prompt=prompt,
    )

    text = (getattr(result, "text", "") or "").strip()

    segments = getattr(result, "segments", None) or []
    no_speech = None
    avg_logprob = None

    if segments:
        try:
            no_speech = max(
                float(getattr(seg, "no_speech_prob", 0.0) or 0.0)
                for seg in segments
            )
        except (TypeError, ValueError):
            pass

        try:
            values = [
                float(getattr(seg, "avg_logprob", 0.0) or 0.0)
                for seg in segments
            ]
            avg_logprob = sum(values) / len(values)
        except (TypeError, ValueError):
            pass

    return {
        "text": text,
        "no_speech": no_speech,
        "avg_logprob": avg_logprob,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Standalone Chinese STT diagnostic for Xiaoyu."
    )
    parser.add_argument("--mic", type=int, default=None, help="Microphone device index.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Groq Whisper model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"VAD RMS threshold (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument("--list-mics", action="store_true", help="List microphones and exit.")
    args = parser.parse_args()

    if args.list_mics:
        list_mics()
        return 0

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Không tìm thấy GROQ_API_KEY.", flush=True)
        print("Hãy đặt GROQ_API_KEY trong .env hoặc environment.", flush=True)
        return 1

    if args.mic is not None:
        try:
            device = sd.query_devices(args.mic, "input")
        except Exception as exc:
            print(f"❌ Không mở được microphone {args.mic}: {exc}", flush=True)
            return 1
    else:
        device = sd.query_devices(None, "input")
        args.mic = sd.default.device[0]

    print("\n" + "=" * 72)
    print("🧪 XIAOYU — CHINESE STT DIAGNOSTIC")
    print("=" * 72)
    print(f"Model       : {args.model}")
    print(f"Microphone  : [{args.mic}] {device['name']}")
    print(f"Sample rate : {INPUT_RATE} Hz")
    print(f"VAD         : RMS >= {args.threshold}")
    print("STT language: zh (FORCED)")
    print("=" * 72)

    client = Groq(api_key=api_key)

    print(
        "\nMỗi lượt: script tự động nghe. Khi thấy 🟢, hãy đọc câu. "
        "Không cần nhấn Enter.",
        flush=True,
    )
    print("Ctrl+C để dừng.\n", flush=True)

    results = []

    try:
        for index, (expected, pinyin, meaning) in enumerate(TEST_SENTENCES, start=1):
            print("\n" + "-" * 72)
            print(f"TEST {index}/{len(TEST_SENTENCES)}")
            print(f"📖 Câu nên đọc: {expected}")
            print(f"🔤 Pinyin    : {pinyin}")
            print(f"🇻🇳 Nghĩa     : {meaning}")
            print("-" * 72)
            print("🎤 Hãy nói ngay sau khi thấy 🟢 Bắt đầu bắt tiếng...", flush=True)

            started = time.perf_counter()
            pcm = record_until_silence(
                device=args.mic,
                threshold=args.threshold,
                start_ms=DEFAULT_START_MS,
                end_silence_ms=DEFAULT_END_SILENCE_MS,
                preroll_frames=DEFAULT_PREROLL_FRAMES,
                min_speech_ms=DEFAULT_MIN_SPEECH_MS,
                max_speech_ms=DEFAULT_MAX_SPEECH_MS,
            )

            if not pcm:
                results.append({
                    "index": index,
                    "expected": expected,
                    "pinyin": pinyin,
                    "meaning": meaning,
                    "actual": "",
                    "status": "NO AUDIO",
                    "elapsed": time.perf_counter() - started,
                })
                continue

            try:
                data = transcribe(client, pcm, args.model)
            except Exception as exc:
                print(f"❌ Whisper/Groq lỗi: {exc}", flush=True)
                results.append({
                    "index": index,
                    "expected": expected,
                    "actual": "",
                    "status": "API ERROR",
                    "elapsed": time.perf_counter() - started,
                })
                continue

            actual = data["text"]
            status = "OK" if actual else "EMPTY"

            print(f"📝 Whisper: {actual or '(trống)'}", flush=True)
            if data["avg_logprob"] is not None:
                print(f"📊 avg_logprob   : {data['avg_logprob']:.3f}", flush=True)
            if data["no_speech"] is not None:
                print(f"📊 no_speech_prob: {data['no_speech']:.3f}", flush=True)

            results.append({
                "index": index,
                "expected": expected,
                "actual": actual,
                "status": status,
                "avg_logprob": data["avg_logprob"],
                "no_speech": data["no_speech"],
                "elapsed": time.perf_counter() - started,
            })

    except KeyboardInterrupt:
        print("\n\n⏹️ Đã dừng test.", flush=True)

    print("\n\n" + "=" * 72)
    print("📋 KẾT QUẢ")
    print("=" * 72)

    if not results:
        print("Chưa có kết quả.")
        return 0

    for item in results:
        print(f"\n{item['index']:02d}. {item['expected']}")
        print(f"    → {item['actual'] or '(trống)'}")
        print(f"    [{item['status']}]")

    ok = sum(1 for item in results if item["status"] == "OK")
    total = len(results)
    print("\n" + "=" * 72)
    print(f"Nhận được transcript: {ok}/{total}")
    print("=" * 72)
    print(
        "\nNếu nhiều câu sai, hãy gửi nguyên phần KẾT QUẢ cho tôi. "
        "Từ đó tôi sẽ phân biệt được lỗi microphone/VAD/Whisper "
        "trước khi sửa voice.py."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
