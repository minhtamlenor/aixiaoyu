"""
Isolated Gemini Live microphone test.

This does NOT import live_voice.py and does not modify the Tiểu Vũ runtime.
It tests only:
    sounddevice microphone -> PCM 16 kHz mono -> Gemini Live -> input transcript

Run from repository root:
    python tools\test_live_mic.py

Speak clearly for several seconds after the test connects.
Press Ctrl+C to stop.
"""

from __future__ import annotations

import asyncio
import os

import sounddevice as sd
from google import genai
from google.genai import types


MODEL = "gemini-3.1-flash-live-preview"
INPUT_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 640
MIC = 1


async def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Chưa tìm thấy GEMINI_API_KEY.")

    client = genai.Client(api_key=api_key)

    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        input_audio_transcription={},
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                prefix_padding_ms=100,
                silence_duration_ms=500,
            )
        ),
        system_instruction=types.Content(
            parts=[
                types.Part(
                    text=(
                        "Bạn chỉ dùng phiên này để kiểm tra microphone. "
                        "Không cần trả lời dài. Khi nhận được tiếng nói, "
                        "hãy chờ input transcription; không chủ động nói."
                    )
                )
            ]
        ),
    )

    loop = asyncio.get_running_loop()
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=20)
    stopped = False

    def enqueue(data: bytes) -> None:
        if stopped:
            return
        try:
            audio_queue.put_nowait(data)
        except asyncio.QueueFull:
            try:
                audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                audio_queue.put_nowait(data)
            except asyncio.QueueFull:
                pass

    def callback(indata, frames, time_info, status):
        if status:
            print("MIC:", status, flush=True)
        loop.call_soon_threadsafe(enqueue, indata.tobytes())

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("✅ Gemini Live test connected", flush=True)
        print("🎤 Nói rõ vào microphone trong 5–10 giây...", flush=True)
        print("   Ví dụ: Tiểu Vũ ơi, Lão sư Minh Tâm đây.", flush=True)

        async def sender() -> None:
            sent = 0
            while not stopped:
                data = await audio_queue.get()
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=data,
                        mime_type="audio/pcm;rate=16000",
                    )
                )
                sent += len(data)
                if sent >= 32000:
                    print(f"🎤 MIC → Gemini: {sent} bytes", flush=True)
                    sent = 0

        async def receiver() -> None:
            async for response in session.receive():
                server = getattr(response, "server_content", None)
                if not server:
                    continue

                transcript = getattr(
                    getattr(server, "input_transcription", None),
                    "text",
                    None,
                )
                if transcript:
                    print(
                        f"📝 INPUT TRANSCRIPT: {transcript!r}",
                        flush=True,
                    )

                if getattr(server, "turn_complete", False):
                    print("🎤 TURN COMPLETE", flush=True)

        with sd.InputStream(
            device=MIC,
            samplerate=INPUT_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCKSIZE,
            callback=callback,
        ):
            sender_task = asyncio.create_task(sender())
            receiver_task = asyncio.create_task(receiver())
            try:
                await asyncio.sleep(15)
            finally:
                stopped = True
                sender_task.cancel()
                receiver_task.cancel()
                await asyncio.gather(
                    sender_task,
                    receiver_task,
                    return_exceptions=True,
                )

    print("\n✅ Kết thúc microphone test.", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng test.", flush=True)
