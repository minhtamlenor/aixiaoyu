# ============================================================
# TIỂU VŨ - VOICE I/O
# Tai  = Groq Whisper (free tier)
# Não  = Gemini Live + personality + tutor/lesson flow
# Miệng = Gemini Live native AUDIO output
# ============================================================

import asyncio
import math
import os
import struct
from collections import deque

import sounddevice as sd
from groq import Groq
from google.genai import types

import live_voice as brain

SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_MS = 30
FRAME_BYTES = SAMPLE_RATE * FRAME_MS // 1000 * 2
PREROLL_MS = 240
END_SILENCE_MS = 720
MIN_SPEECH_MS = 180
MAX_UTTERANCE_MS = 15000
VAD_RMS_THRESHOLD = 420
STT_MODEL = "whisper-large-v3-turbo"
STT_LANGUAGE = "vi"


def _groq_client():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("Chưa có GROQ_API_KEY. Hãy đặt biến môi trường GROQ_API_KEY trước khi chạy.")
    return Groq(api_key=key)


def _pcm_to_wav(pcm: bytes) -> bytes:
    import io
    import wave
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)
    return output.getvalue()


def _transcribe_blocking(audio: bytes) -> str:
    result = _groq_client().audio.transcriptions.create(
        file=("xiaoyu.wav", _pcm_to_wav(audio)),
        model=STT_MODEL,
        language=STT_LANGUAGE,
        response_format="json",
        temperature=0.0,
    )
    return (getattr(result, "text", "") or "").strip()


async def transcribe(audio: bytes) -> str:
    if not audio:
        return ""
    try:
        text = await asyncio.to_thread(_transcribe_blocking, audio)
        if text:
            print("📝 GROQ WHISPER:", repr(text), flush=True)
        return text
    except Exception as exc:
        print("⚠️ STT Groq lỗi:", repr(exc), flush=True)
        return ""


async def send_user_text_to_gemini(session, text):
    """Gửi một câu đã được Groq STT chốt thành một turn hoàn chỉnh.

    Không gửi bằng realtime_input(text=...) ở đây: với kiến trúc external STT
    + manual VAD, đường đó có thể để turn ở trạng thái chưa hoàn tất. Dùng
    client-content với turn_complete=True để Gemini phát AUDIO ngay.
    """
    await session.send_client_content(
        turns=types.Content(
            role="user",
            parts=[types.Part(text=text)],
        ),
        turn_complete=True,
    )


async def deliver_text_to_brain(session, text):
    text = (text or "").strip()
    if not text:
        return

    if brain.detect_farewell(text):
        await brain.process_user_text(session, text)
        return

    command = brain.detect_tutor_command(text)
    handled_by_controller = command["intent"] != "chat"
    lesson_answer = bool(
        brain.tutor_mode
        and brain.lesson_session
        and brain.lesson_waiting_for_answer
    )

    await brain.process_user_text(session, text)

    # Tutor/lesson controller đã tự gửi prompt vào Gemini.
    if handled_by_controller or lesson_answer:
        return

    try:
        await send_user_text_to_gemini(session, text)
        print("📨 Đã gửi turn hoàn chỉnh vào Gemini.", flush=True)
    except Exception as exc:
        print("⚠️ Gửi turn text vào Gemini lỗi:", repr(exc), flush=True)


def _is_speech(frame: bytes) -> bool:
    if not frame:
        return False
    try:
        sample_count = len(frame) // 2
        if sample_count <= 0:
            return False
        samples = struct.unpack(f"<{sample_count}h", frame)
        mean_square = sum(sample * sample for sample in samples) / sample_count
        return math.sqrt(mean_square) >= VAD_RMS_THRESHOLD
    except Exception:
        return False


async def microphone_loop(audio_queue):
    loop = asyncio.get_running_loop()
    preroll = deque(maxlen=max(1, PREROLL_MS // FRAME_MS))

    def enqueue(data):
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
        data = bytes(indata)
        if len(data) != FRAME_BYTES:
            return
        try:
            loop.call_soon_threadsafe(enqueue, data)
        except RuntimeError:
            pass

    device_info = sd.query_devices(brain.MIC, "input")
    print(f"🎙️ MIC device {brain.MIC}: {device_info['name']}", flush=True)
    print(f"🎙️ MIC channels={CHANNELS} rate={SAMPLE_RATE} frame={FRAME_MS}ms", flush=True)

    with sd.RawInputStream(
        device=brain.MIC,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=SAMPLE_RATE * FRAME_MS // 1000,
        callback=callback,
    ):
        print("🎤 Tai Tiểu Vũ sẵn sàng.", flush=True)
        print("⏳ Chờ Tiểu Vũ nói xong rồi bắt đầu nghe.", flush=True)

        speech = bytearray()
        speech_started = False
        speech_ms = 0
        silence_ms = 0

        while not brain.shutdown_requested:
            frame = await audio_queue.get()

            if brain.model_speaking:
                preroll.clear()
                speech.clear()
                speech_started = False
                speech_ms = 0
                silence_ms = 0
                continue

            is_speech = _is_speech(frame)
            preroll.append(frame)

            if not speech_started:
                if not is_speech:
                    continue
                speech_started = True
                speech = bytearray(b"".join(preroll))
                speech_ms = len(preroll) * FRAME_MS
                silence_ms = 0
                print("🟢 MIC: bắt đầu nghe", flush=True)
                continue

            speech.extend(frame)
            speech_ms += FRAME_MS
            if is_speech:
                silence_ms = 0
            else:
                silence_ms += FRAME_MS

            if silence_ms >= END_SILENCE_MS or speech_ms >= MAX_UTTERANCE_MS:
                if speech_ms >= MIN_SPEECH_MS:
                    yield bytes(speech)
                speech.clear()
                preroll.clear()
                speech_started = False
                speech_ms = 0
                silence_ms = 0
                print("🔴 MIC: kết thúc câu", flush=True)


async def start_voice_io():
    _groq_client()

    brain.shutdown_requested = False
    brain.listen_ready = True
    brain.model_speaking = False
    brain.startup_greeting_sent = False

    config = brain.build_live_config()

    async with brain.client.aio.live.connect(
        model=brain.MODEL,
        config=config,
    ) as session:
        print("✅ Gemini brain connected", flush=True)
        print("👂 Tai: Groq Whisper", flush=True)
        print("🧠 Não: Gemini + personality + tutor/lesson flow", flush=True)
        print("👄 Miệng: Gemini Live native AUDIO — 24 kHz", flush=True)

        audio_queue = asyncio.Queue(maxsize=120)

        async def audio_worker():
            async for utterance in microphone_loop(audio_queue):
                text = await transcribe(utterance)
                if not text:
                    continue
                print("👤 Lão sư:", text, flush=True)
                await deliver_text_to_brain(session, text)

        receive_task = asyncio.create_task(brain.receive_loop(session))
        mic_task = asyncio.create_task(audio_worker())

        await asyncio.sleep(0.25)
        await brain.send_startup_greeting(session)

        try:
            await asyncio.gather(receive_task, mic_task)
        finally:
            brain.shutdown_requested = True
            for task in (receive_task, mic_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(receive_task, mic_task, return_exceptions=True)


def cleanup_voice_io():
    brain.shutdown_requested = True
    brain.listen_ready = False
    try:
        brain.clear_speaker_queue()
    except Exception:
        pass
    try:
        brain.close_speaker()
    except Exception:
        pass
    brain.cleanup()
