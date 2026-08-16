# ============================================================
# TIỂU VŨ - VOICE I/O
# Tai = Groq Whisper (free tier)
# Miệng = Microsoft Edge Neural TTS via edge-tts (no API key)
# Não = giữ nguyên live_voice.py / Gemini / personality / tutor
# ============================================================

import asyncio
import os
import subprocess
import time
from collections import deque

import sounddevice as sd
import webrtcvad
from groq import Groq

import live_voice as brain

SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_MS = 30
FRAME_BYTES = SAMPLE_RATE * FRAME_MS // 1000 * 2
VAD_MODE = 2
PREROLL_MS = 240
END_SILENCE_MS = 720
MIN_SPEECH_MS = 180
MAX_UTTERANCE_MS = 15000

STT_MODEL = "whisper-large-v3-turbo"
STT_LANGUAGE = "vi"
TTS_VOICE = "vi-VN-HoaiMyNeural"
TTS_RATE = "+0%"


def _groq_client():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "Chưa có GROQ_API_KEY. Tạo API key Groq ở console.groq.com rồi "
            "đặt biến môi trường GROQ_API_KEY trước khi chạy."
        )
    return Groq(api_key=key)


# ============================================================
# TTS - MIỆNG
# ============================================================
_tts_process = None
_tts_lock = asyncio.Lock()


def _stop_tts_process():
    global _tts_process
    process = _tts_process
    _tts_process = None
    if process is None:
        return
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=0.4)
            except subprocess.TimeoutExpired:
                process.kill()
    except Exception:
        pass


async def speak(text):
    global _tts_process
    text = (text or "").strip()
    if not text:
        return

    async with _tts_lock:
        _stop_tts_process()
        command = [
            "edge-playback",
            "--voice", TTS_VOICE,
            "--rate", TTS_RATE,
            "--text", text,
        ]
        print("🔊 TTS → loa:", text, flush=True)
        process = None
        try:
            _tts_process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            process = _tts_process
            await asyncio.to_thread(process.wait)
            error = ""
            if process.stderr:
                try:
                    error = process.stderr.read().strip()
                except Exception:
                    pass
            if process.returncode not in (0, None) and error:
                print("⚠️ TTS lỗi:", error, flush=True)
        except FileNotFoundError:
            print("⚠️ Không tìm thấy edge-playback. Chạy: pip install edge-tts", flush=True)
        except Exception as exc:
            print("⚠️ TTS lỗi:", repr(exc), flush=True)
        finally:
            if _tts_process is process:
                _tts_process = None


# ============================================================
# STT - TAI
# ============================================================
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
    client = _groq_client()
    wav_bytes = _pcm_to_wav(audio)
    result = client.audio.transcriptions.create(
        file=("xiaoyu.wav", wav_bytes),
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


# ============================================================
# ROUTING: giữ nguyên NÃO GIA SƯ
# ============================================================
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

    if handled_by_controller or lesson_answer:
        return

    try:
        await session.send_realtime_input(text=text)
    except Exception as exc:
        print("⚠️ Gửi text vào Gemini lỗi:", repr(exc), flush=True)


# ============================================================
# MICROPHONE SEGMENTER
# ============================================================
async def microphone_loop(audio_queue):
    loop = asyncio.get_running_loop()
    preroll = deque(maxlen=max(1, PREROLL_MS // FRAME_MS))
    vad = webrtcvad.Vad(VAD_MODE)

    def callback(indata, frames, time_info, status):
        if status:
            print("MIC:", status, flush=True)
        data = bytes(indata)
        if len(data) != FRAME_BYTES:
            return
        try:
            loop.call_soon_threadsafe(audio_queue.put_nowait, data)
        except asyncio.QueueFull:
            pass
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
        print("⏳ Đang chờ Lão sư nói...", flush=True)

        speech = bytearray()
        speech_started = False
        speech_ms = 0
        silence_ms = 0

        while not brain.shutdown_requested:
            frame = await audio_queue.get()

            # Chặn microphone khi miệng đang phát để không thu ngược TTS.
            if brain.model_speaking or _tts_process is not None:
                preroll.clear()
                speech.clear()
                speech_started = False
                speech_ms = 0
                silence_ms = 0
                continue

            is_speech = vad.is_speech(frame, SAMPLE_RATE)
            preroll.append(frame)

            if not speech_started:
                if not is_speech:
                    continue
                speech_started = True
                speech = bytearray(b"".join(preroll))
                speech_ms = len(preroll) * FRAME_MS
                silence_ms = 0
                print("🟢 MIC: bắt đầu nghe", flush=True)
            else:
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


# ============================================================
# GEMINI BRAIN RECEIVE
# ============================================================
async def receive_brain(session, tts_queue):
    output_text = []
    try:
        async for response in session.receive():
            tool = getattr(response, "tool_call", None)
            if tool:
                calls = getattr(tool, "function_calls", None)
                if calls:
                    await brain.handle_tool_call(session, calls)

            server = getattr(response, "server_content", None)
            if server is None:
                continue

            if getattr(server, "interrupted", False):
                print("🛑 Tiểu Vũ bị ngắt.", flush=True)
                output_text.clear()
                _stop_tts_process()

            transcript = getattr(server, "output_transcription", None)
            text = getattr(transcript, "text", None)
            if text:
                chunk = text.strip()
                if chunk:
                    print("💗 Tiểu Vũ:", chunk, flush=True)
                    output_text.append(chunk)

            # Bỏ qua inline_data của Gemini: đây là phần miệng mới.
            if getattr(server, "turn_complete", False):
                final_text = " ".join(output_text).strip()
                output_text.clear()
                if final_text:
                    await tts_queue.put(final_text)
                print("\n🎤 Tiểu Vũ đang nghe...", flush=True)
    finally:
        output_text.clear()


async def tts_worker(tts_queue):
    while not brain.shutdown_requested:
        text = await tts_queue.get()
        if text is None:
            return
        await speak(text)


# ============================================================
# MAIN VOICE LOOP
# ============================================================
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
        print("👄 Miệng: Edge Neural TTS — vi-VN-HoaiMyNeural", flush=True)

        audio_queue = asyncio.Queue(maxsize=120)
        tts_queue = asyncio.Queue(maxsize=8)

        async def audio_worker():
            async for utterance in microphone_loop(audio_queue):
                text = await transcribe(utterance)
                if not text:
                    continue
                print("👤 Lão sư:", text, flush=True)
                _stop_tts_process()
                await deliver_text_to_brain(session, text)

        receive_task = asyncio.create_task(receive_brain(session, tts_queue))
        tts_task = asyncio.create_task(tts_worker(tts_queue))
        mic_task = asyncio.create_task(audio_worker())

        await asyncio.sleep(0.25)
        await brain.send_startup_greeting(session)

        try:
            await asyncio.gather(receive_task, tts_task, mic_task)
        finally:
            brain.shutdown_requested = True
            _stop_tts_process()
            for task in (receive_task, tts_task, mic_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(receive_task, tts_task, mic_task, return_exceptions=True)


def cleanup_voice_io():
    brain.shutdown_requested = True
    _stop_tts_process()
    brain.cleanup()
