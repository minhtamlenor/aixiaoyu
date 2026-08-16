import asyncio
import io
import math
import os
import struct
import wave

import sounddevice as sd
from groq import Groq
from google import genai
from google.genai import types


# ============================================================
# TIỂU VŨ VOICE
# Tai  = Groq Whisper
# Não  = Gemini Live
# Miệng = Gemini Live native AUDIO
# ============================================================

MIC = 1
INPUT_RATE = 16000
OUTPUT_RATE = 24000
CHANNELS = 1
FRAME_MS = 30
BLOCKSIZE = INPUT_RATE * FRAME_MS // 1000
MODEL = "gemini-3.1-flash-live-preview"
STT_MODEL = "whisper-large-v3-turbo"
STT_LANGUAGE = "vi"
VAD_THRESHOLD = 180
END_SILENCE_MS = 1200
MIN_SPEECH_MS = 180
MAX_SPEECH_MS = 45000

CHAT_MODE = "chat"
TUTOR_MODE = "tutor"
CURRENT_MODE = CHAT_MODE

TUTOR_TRIGGERS = [
    "mini muốn học", "mini muon hoc",
    "đậu phộng muốn học", "dậu phộng muốn học", "dau phong muon hoc",
    "mini học", "mini hoc", "đậu phộng học", "dau phong hoc",
    "cho mini học", "cho đậu phộng học",
    "bắt đầu học", "bat dau hoc", "vào học", "vao hoc", "học đi", "hoc di",
]

SYSTEM_INSTRUCTION = """
Bạn là Tiểu Vũ.
Bạn là một cô gái Việt Nam thân thiện, dễ thương, tự nhiên, hơi tinh nghịch và gần gũi.
Bạn đang trò chuyện với Lão sư.

QUY TẮC:
- Không tự nói thay người dùng.
- Không tự đóng vai học sinh.
- Không tự hỏi rồi tự trả lời.
- Không tự tạo câu trả lời của Mini.
- Chỉ trả lời khi có lời nói của người dùng hoặc chương trình gia sư yêu cầu đọc câu hỏi.

CHAT MODE:
- Nói chuyện tự nhiên với Lão sư.
- Có thể trả lời và đùa vui.
- Không tự tạo hội thoại.

TUTOR MODE:
- Đang dạy Mini.
- Chờ chương trình cung cấp câu hỏi hoặc phản hồi.
- Không tự quyết định đáp án, điểm số hay câu hỏi tiếp theo.

XƯNG HÔ:
Người dùng là Minh Tâm, nam. Gọi là “Lão sư”.
Tiểu Vũ là nữ, giọng thân mật, tự nhiên, miền Nam Việt Nam.
Không gọi Minh Tâm là bà, chị, cô, nàng, mẹ.

Nói ngắn gọn, tự nhiên, không độc thoại.
"""

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
groq = Groq(api_key=os.environ["GROQ_API_KEY"])

listen_enabled = False
model_speaking = False
shutdown_requested = False


def normalize_text(text: str) -> str:
    return (
        (text or "")
        .strip()
        .lower()
        .replace(".", "")
        .replace(",", "")
        .replace("!", "")
        .replace("?", "")
    )


def is_tutor_trigger(text: str) -> bool:
    clean = normalize_text(text)
    return any(trigger in clean for trigger in TUTOR_TRIGGERS)


def pcm_to_wav(pcm: bytes) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(INPUT_RATE)
        wf.writeframes(pcm)
    return out.getvalue()


def rms(pcm: bytes) -> float:
    if not pcm:
        return 0.0
    count = len(pcm) // 2
    if not count:
        return 0.0
    samples = struct.unpack(f"<{count}h", pcm)
    return math.sqrt(sum(x * x for x in samples) / count)


def transcribe(pcm: bytes) -> str:
    result = groq.audio.transcriptions.create(
        file=("xiaoyu.wav", pcm_to_wav(pcm)),
        model=STT_MODEL,
        language=STT_LANGUAGE,
        response_format="json",
        temperature=0.0,
    )
    return (getattr(result, "text", "") or "").strip()


async def send_text(session, text: str):
    await session.send_realtime_input(text=text)


async def microphone_loop(session):
    global listen_enabled, shutdown_requested, CURRENT_MODE

    loop = asyncio.get_running_loop()
    queue = asyncio.Queue(maxsize=100)
    preroll = []

    def enqueue(data: bytes):
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(data)
        except asyncio.QueueFull:
            pass

    def callback(indata, frames, time_info, status):
        if status:
            print("MIC:", status, flush=True)
        if listen_enabled and not model_speaking:
            # RawInputStream supplies a cffi buffer, not a numpy array.
            # Convert it directly to bytes and schedule the normal queue
            # callback on the asyncio event loop thread.
            data = bytes(indata)
            loop.call_soon_threadsafe(enqueue, data)

    device = sd.query_devices(MIC, "input")
    print(f"🎙️ MIC device {MIC}: {device['name']}", flush=True)
    print(f"🎙️ MIC channels={CHANNELS} rate={INPUT_RATE} frame={FRAME_MS}ms", flush=True)
    print(f"🎙️ VAD threshold={VAD_THRESHOLD} RMS", flush=True)

    with sd.RawInputStream(
        device=MIC,
        samplerate=INPUT_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=BLOCKSIZE,
        callback=callback,
    ):
        while not shutdown_requested:
            frame = await queue.get()
            if not listen_enabled or model_speaking:
                preroll.clear()
                continue

            level = rms(frame)
            preroll.append(frame)
            if len(preroll) > 10:
                preroll.pop(0)

            if level < VAD_THRESHOLD:
                continue

            print("🟢 MIC: bắt đầu nghe", flush=True)
            audio = bytearray(b"".join(preroll))
            speech_ms = len(preroll) * FRAME_MS
            silence_ms = 0

            while listen_enabled and not model_speaking and speech_ms < MAX_SPEECH_MS:
                frame = await queue.get()
                audio.extend(frame)
                speech_ms += FRAME_MS
                if rms(frame) >= VAD_THRESHOLD:
                    silence_ms = 0
                else:
                    silence_ms += FRAME_MS
                if silence_ms >= END_SILENCE_MS:
                    break

            listen_enabled = False
            preroll.clear()

            if speech_ms < MIN_SPEECH_MS:
                print("🔴 MIC: câu quá ngắn, bỏ qua", flush=True)
                listen_enabled = True
                continue

            print(f"🔴 MIC: kết thúc câu ({speech_ms} ms) → Groq Whisper", flush=True)
            try:
                text = await asyncio.to_thread(transcribe, bytes(audio))
            except Exception as exc:
                print("⚠️ Groq Whisper lỗi:", repr(exc), flush=True)
                listen_enabled = True
                continue

            if not text:
                print("📝 Groq Whisper: không nhận được text", flush=True)
                listen_enabled = True
                continue

            print("📝 Groq Whisper:", text, flush=True)
            print("👤 Lão sư:", text, flush=True)

            if CURRENT_MODE == CHAT_MODE and is_tutor_trigger(text):
                CURRENT_MODE = TUTOR_MODE
                print("🎓 CHUYỂN SANG CHẾ ĐỘ GIA SƯ", flush=True)

            try:
                await send_text(session, text)
                print("📨 TEXT → GEMINI: đã gửi", flush=True)
            except Exception as exc:
                print("⚠️ Gemini nhận text lỗi:", repr(exc), flush=True)
                listen_enabled = True


async def receive_loop(session):
    global listen_enabled, model_speaking, shutdown_requested

    while not shutdown_requested:
        async for response in session.receive():
            if response.server_content is None:
                continue

            content = response.server_content

            if content.output_transcription:
                text = content.output_transcription.text
                if text:
                    print("💗 Tiểu Vũ:", text, flush=True)

            if content.model_turn:
                for part in content.model_turn.parts:
                    if part.inline_data and part.inline_data.data:
                        if not model_speaking:
                            model_speaking = True
                            listen_enabled = False
                            print("🔊 Tiểu Vũ đang nói...", flush=True)
                        audio = part.inline_data.data
                        output.write(audio)

            if content.turn_complete:
                if model_speaking:
                    output.stop()
                    output.close()
                    reopen_output()
                model_speaking = False
                listen_enabled = True
                print("\n🎤 Tiểu Vũ đang nghe...", flush=True)


output = None


def reopen_output():
    global output
    output = sd.RawOutputStream(
        samplerate=OUTPUT_RATE,
        channels=1,
        dtype="int16",
    )
    output.start()


def cleanup():
    global shutdown_requested, listen_enabled, output
    shutdown_requested = True
    listen_enabled = False
    if output is not None:
        try:
            output.stop()
            output.close()
        except Exception:
            pass
        output = None


async def start_voice_io():
    global output, listen_enabled, shutdown_requested, model_speaking

    shutdown_requested = False
    listen_enabled = False
    model_speaking = False
    reopen_output()

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part(text=SYSTEM_INSTRUCTION)]
        ),
        output_audio_transcription={},
    )

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("✅ Gemini brain connected", flush=True)
        print("👂 Tai: Groq Whisper", flush=True)
        print("🧠 Não: Gemini + personality + tutor mode", flush=True)
        print("👄 Miệng: Gemini Live native AUDIO — 24 kHz", flush=True)

        receive_task = asyncio.create_task(receive_loop(session))
        mic_task = asyncio.create_task(microphone_loop(session))

        await asyncio.sleep(0.3)
        await send_text(
            session,
            "Chào Lão sư thật ngắn gọn và tự nhiên. Không hỏi câu hỏi mới.",
        )

        try:
            await asyncio.gather(receive_task, mic_task)
        finally:
            shutdown_requested = True
            receive_task.cancel()
            mic_task.cancel()
            await asyncio.gather(receive_task, mic_task, return_exceptions=True)


def start():
    try:
        asyncio.run(start_voice_io())
    except KeyboardInterrupt:
        print("\n👋 Tiểu Vũ đã tắt.")
    finally:
        cleanup()


if __name__ == "__main__":
    start()
