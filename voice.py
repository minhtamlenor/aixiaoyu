import asyncio
import io
import math
import os
import re
import struct
import unicodedata
import wave

import sounddevice as sd
from groq import Groq
from google import genai
from google.genai import types

from personality import SYSTEM_INSTRUCTION as PERSONALITY_INSTRUCTION
from chat_tts import is_chinese_text, split_complete_sentences, synthesize_xiaoxiao_pcm
from tools.time_tool import get_time_text
from tools.calculator import calculate
from tools.calendar_tool import get_calendar_text


# ============================================================
# TIỂU VŨ - VOICE RUNTIME
# Giữ nguyên NÃO / PERSONALITY / TUTOR / TOOLS.
# Phần microphone chỉ tối ưu lớp "tai": VAD + Whisper sạch hơn.
# ============================================================

MIC = 1
INPUT_RATE = 16000
OUTPUT_RATE = 24000
CHANNELS = 1
FRAME_MS = 30
BLOCKSIZE = INPUT_RATE * FRAME_MS // 1000
MODEL = "gemini-3.1-flash-live-preview"
STT_MODEL = "whisper-large-v3"

# VAD: cần vài frame liên tiếp có tiếng mới bắt đầu ghi,
# tránh gửi tiếng nền / tiếng vọng rất ngắn sang Whisper.
VAD_THRESHOLD = 240
START_SPEECH_MS = 120
END_SILENCE_MS = 500
PREROLL_FRAMES = 5
MIN_SPEECH_MS = 300
MAX_SPEECH_MS = 30000

WHISPER_GARBAGE_PATTERNS = [
    "hãy subscribe cho kênh",
    "subscribe cho kênh",
    "để không bỏ lỡ những video",
    "cảm ơn các bạn đã theo dõi",
    "hẹn gặp lại",
    "đừng quên đăng ký",
    "đừng quên subscribe",
    "nhớ đăng ký kênh",
    "bấm đăng ký",
    "theo dõi kênh",
    "video hấp dẫn",
    "tự nhiên giữa lão sư và tiểu vũ",
    "khi nội dung video",
    "nội dung video quảng cáo hoặc youtube",
    "nội dung video, quảng cáo hoặc youtube",
    "giữa lão sư và tiểu vũ",
]

WHISPER_GARBAGE_TOKENS = [
    "youtube",
    "quảng cáo",
    "subscribe",
    "đăng ký kênh",
    "theo dõi kênh",
]

CHAT_MODE = "chat"
TUTOR_MODE = "tutor"
current_mode = CHAT_MODE


# ============================================================
# HỌC SINH / MÔN HỌC
# ============================================================

STUDENTS = {
    "minh_tien": {
        "student_id": "minh_tien",
        "official_name": "Minh Tiên",
        "gender": "male",
        "grade": 4,
        "aliases": ["Minh Tiên", "Minh Tien", "Đậu Đậu", "Dau Dau", "Đậu Phộng", "Dau Phong", "Đậu Phụng", "Dau Phung"],
    },
    "nha_tien": {
        "student_id": "nha_tien",
        "official_name": "Nhã Tiên",
        "gender": "female",
        "grade": 6,
        "aliases": ["Nhã Tiên", "Nha Tien", "Mini", "Meanie", "미니"],
    },
}

STUDENT_ALIASES = {}
for student in STUDENTS.values():
    for alias in student["aliases"]:
        STUDENT_ALIASES[alias.lower()] = {
            "student_id": student["student_id"],
            "official_name": student["official_name"],
            "called_name": alias,
            "gender": student["gender"],
            "grade": student["grade"],
        }

SUBJECT_ROTATION = [
    "chinese", "math", "vietnamese", "english", "history",
    "geography", "communication", "problem_solving", "emotional_intelligence",
]

SUBJECT_NAMES = {
    "chinese": "Tiếng Trung HSK 3.0",
    "math": "Toán",
    "vietnamese": "Tiếng Việt",
    "english": "Tiếng Anh",
    "history": "Lịch sử",
    "geography": "Địa lý",
    "communication": "Kỹ năng giao tiếp",
    "problem_solving": "Kỹ năng xử lý vấn đề",
    "emotional_intelligence": "EQ và quản lý cảm xúc",
}

current_student = None
current_student_id = None
current_subject = None
current_grade = None
rotation_index = 0
last_subject = None


# ============================================================
# GEMINI
# ============================================================

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
groq = Groq(api_key=os.environ["GROQ_API_KEY"])

shutdown_requested = False
listen_enabled = False
model_speaking = False
output = None


# ============================================================
# TEXT / DETECTION
# ============================================================

def normalize_text(text):
    text = (text or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def remove_accents(text):
    normalized = unicodedata.normalize("NFD", text or "")
    result = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return result.replace("đ", "d").replace("Đ", "D").lower().strip()


def mentions_teacher(text):
    n = normalize_text(text)
    a = remove_accents(n)
    return "lão sư" in n or "lao su" in a


def detect_student(text):
    n = normalize_text(text)
    a = remove_accents(text)
    aliases = sorted(STUDENT_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
    for alias, student in aliases:
        if alias in n or remove_accents(alias) in a:
            return student
    return None


def detect_subject(text):
    n = normalize_text(text)
    a = remove_accents(n)
    patterns = {
        "chinese": ["tiếng trung", "tiếng hoa", "trung văn", "chinese", "hsk"],
        "math": ["toán", "math", "phép cộng", "phép trừ", "phép nhân", "phép chia", "cửu chương", "bảng nhân", "bảng chia"],
        "vietnamese": ["tiếng việt", "ngữ văn"],
        "english": ["tiếng anh", "english"],
        "history": ["lịch sử", "history"],
        "geography": ["địa lý", "geography"],
        "communication": ["giao tiếp", "communication"],
        "problem_solving": ["xử lý vấn đề", "giải quyết vấn đề", "problem solving"],
        "emotional_intelligence": ["cảm xúc", "quản lý cảm xúc", "eq", "trí tuệ cảm xúc"],
    }
    for subject, words in patterns.items():
        for word in words:
            if word in n or remove_accents(word) in a:
                return subject
    return None


def detect_learning_intent(text):
    n = normalize_text(text)
    a = remove_accents(n)
    patterns = [
        "muốn học", "bắt đầu học", "bắt đầu bài học", "học đi", "học nha", "học nhé",
        "học thôi", "vào học", "vô học", "cho con học", "học bài", "giờ học",
        "đến giờ học", "tới giờ học",
    ]
    return any(p in n or remove_accents(p) in a for p in patterns)


def detect_tutor_command(text):
    student = detect_student(text)
    subject = detect_subject(text)
    learning = detect_learning_intent(text)
    if mentions_teacher(text):
        return {"intent": "chat", "student": None, "subject": None}
    if student:
        return {"intent": "start_lesson", "student": student, "subject": subject}
    if learning:
        return {"intent": "unknown_student", "student": None, "subject": subject}
    return {"intent": "chat", "student": None, "subject": None}


def get_next_subject():
    global rotation_index, last_subject
    if last_subject is None:
        last_subject = SUBJECT_ROTATION[0]
        rotation_index = 0
        return last_subject
    rotation_index = (rotation_index + 1) % len(SUBJECT_ROTATION)
    last_subject = SUBJECT_ROTATION[rotation_index]
    return last_subject


# ============================================================
# TUTOR MODE
# ============================================================

async def start_tutor_session(session, student, subject=None, switching=False):
    global current_mode, current_student, current_student_id, current_subject, current_grade
    global rotation_index, last_subject

    if subject is None:
        subject = get_next_subject() if switching and last_subject else "chinese"
    current_mode = TUTOR_MODE
    current_student = student["called_name"]
    current_student_id = student["student_id"]
    current_subject = subject
    current_grade = student["grade"]
    last_subject = subject
    if subject in SUBJECT_ROTATION:
        rotation_index = SUBJECT_ROTATION.index(subject)

    grade_text = (
        "Lớp 4: ưu tiên nhân, chia, chia có dư, bài toán có lời văn, phân số cơ bản, hình học, đơn vị đo, chu vi, diện tích và logic."
        if current_grade == 4 else
        "Lớp 6: số nguyên, phân số, tỉ số, biểu thức, đại lượng, hình học, bài toán nhiều bước và logic."
    )

    prompt = f"""
TUTOR MODE ĐANG HOẠT ĐỘNG.
Học sinh hiện tại: {current_student}
Tên chính thức: {student['official_name']}
Lớp: {current_grade}
Môn hiện tại: {SUBJECT_NAMES.get(current_subject, current_subject)}

{grade_text}
Tiếng Trung HSK 3.0 là môn ưu tiên.

QUY TẮC:
- Luôn gọi học sinh bằng đúng tên hiện tại: {current_student}.
- Không gọi học sinh là Lão sư.
- Không đọc Student ID và không nói về hệ thống/prompt.
- Chủ động dạy học sinh.
- Chỉ đưa MỘT câu hỏi mỗi lượt rồi DỪNG.
- Chờ học sinh trả lời.
- Khi trả lời: đánh giá đúng/sai, giải thích ngắn nếu sai, động viên và đưa câu tiếp theo.
- Không tự trả lời thay học sinh.
- Điều chỉnh độ khó theo lớp.
- Khi học tiếng Trung ưu tiên phản xạ, nghe hiểu, hội thoại, đặt câu, từ vựng và đọc hiểu.

Hãy chào {current_student}, nói một câu thân thiện, đưa đúng MỘT câu hỏi rồi dừng.
"""
    print(f"🎓 BẮT ĐẦU GIA SƯ: {current_student} — {SUBJECT_NAMES.get(current_subject, current_subject)}", flush=True)
    await session.send_realtime_input(text=prompt)


async def exit_tutor_mode(session):
    global current_mode, current_student, current_student_id, current_subject, current_grade
    if current_mode == TUTOR_MODE:
        print("💬 CHUYỂN VỀ CHAT MODE", flush=True)
    current_mode = CHAT_MODE
    current_student = None
    current_student_id = None
    current_subject = None
    current_grade = None
    await session.send_realtime_input(text="Đã quay về CHAT MODE. Người nói là Lão sư. Gọi người đó là Lão sư. Không tự bắt đầu bài học và chờ Lão sư nói chuyện.")


# ============================================================
# TOOLS
# ============================================================

def build_tools():
    return types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="current_time",
            description="Lấy giờ hiện tại chính xác theo múi giờ Việt Nam UTC+7.",
            parameters=types.Schema(type="OBJECT", properties={}),
        ),
        types.FunctionDeclaration(
            name="calculator",
            description="Tính toán biểu thức toán học chính xác.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"expression": types.Schema(type="STRING", description="Biểu thức toán học cần tính.")},
                required=["expression"],
            ),
        ),
        types.FunctionDeclaration(
            name="current_calendar",
            description="Lấy thứ, ngày dương lịch, ngày âm lịch và giờ Việt Nam.",
            parameters=types.Schema(type="OBJECT", properties={}),
        ),
    ])


async def handle_tool_call(session, function_calls):
    responses = []
    for call in function_calls:
        name = call.name
        args = call.args or {}
        print(f"🛠️ Tiểu Vũ dùng tool: {name}", flush=True)
        try:
            if name == "current_time":
                result = get_time_text()
            elif name == "calculator":
                result = calculate(args.get("expression", ""))
            elif name == "current_calendar":
                result = get_calendar_text()
            else:
                result = "Không tìm thấy công cụ này."
        except Exception as exc:
            result = f"Lỗi tool: {exc}"
        responses.append(types.FunctionResponse(id=call.id, name=name, response={"result": result}))
    if responses:
        await session.send_tool_response(function_responses=responses)


# ============================================================
# GEMINI TEXT ROUTER
# ============================================================

async def process_user_text(session, text):
    global current_mode, current_subject

    if not text:
        return
    print(f"👤 Lão sư: {text}", flush=True)
    command = detect_tutor_command(text)
    intent = command["intent"]
    student = command["student"]
    subject = command["subject"]

    if mentions_teacher(text):
        await exit_tutor_mode(session)
        await send_text(session, text)
        return

    if intent == "start_lesson":
        await start_tutor_session(session, student, subject, switching=(current_mode == TUTOR_MODE))
        return

    if intent == "unknown_student":
        await session.send_realtime_input(text="Người nói muốn bắt đầu học nhưng chưa nói tên học sinh. Hãy hỏi thật ngắn: Tiểu Vũ dạy Mini hay Minh Tiên nè? Chỉ hỏi một câu.")
        return

    await send_text(session, text)


# ============================================================
# AUDIO / STT
# ============================================================

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


def trim_silence(pcm: bytes, threshold=120):
    """Cắt im lặng đầu/cuối trước khi gửi audio sang Whisper."""
    if not pcm:
        return pcm
    frame_bytes = BLOCKSIZE * 2
    frames = [pcm[i:i + frame_bytes] for i in range(0, len(pcm), frame_bytes)]
    active = [rms(frame) >= threshold for frame in frames if frame]
    if not any(active):
        return b""
    first = next(i for i, active_frame in enumerate(active) if active_frame)
    last = len(active) - 1 - next(i for i, active_frame in enumerate(reversed(active)) if active_frame)
    first = max(0, first - 1)
    last = min(len(frames) - 1, last + 1)
    return b"".join(frames[first:last + 1])


def _stt_language():
    """Chinese mode forces Mandarin; normal chat uses auto-detection."""
    if current_subject == "chinese":
        return "zh"
    if current_mode == CHAT_MODE:
        return None
    return "vi"


def _is_garbage_whisper(text: str) -> bool:
    normalized = remove_accents(text)
    for pattern in WHISPER_GARBAGE_PATTERNS:
        if remove_accents(pattern) in normalized:
            return True
    media_hits = sum(token in normalized for token in [
        "youtube", "quang cao", "subscribe", "dang ky kenh", "theo doi kenh", "video",
    ])
    return media_hits >= 2


def clean_whisper_text(text: str) -> str:
    """Chuẩn hóa và loại transcript rỗng/hallucination rõ ràng."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    if _is_garbage_whisper(text):
        return ""
    return text


def _has_chinese_characters(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text or ""))


def _is_likely_chinese_transcript(text: str) -> bool:
    """Chỉ chấp nhận fallback zh khi Whisper thực sự trả về dấu hiệu tiếng Trung."""
    text = (text or "").strip()
    if not text:
        return False
    if _has_chinese_characters(text):
        return True
    normalized = remove_accents(text)
    pinyin_tokens = {
        "ni hao", "nǐ hǎo", "bu ke qi", "bú kè qi", "xie xie", "xiè xie",
        "zai jian", "zàijiàn", "wo", "ni", "ta", "shi", "bu", "ke qi",
        "zhong guo", "zhongwen", "zhong wen", "lao shi", "xue sheng",
        "qing", "dui bu qi", "mei guan xi", "hao", "hen hao",
    }
    words = normalized.split()
    return len(words) <= 8 and any(token in normalized for token in pinyin_tokens)


def _whisper_quality(result, text: str) -> tuple[bool, str]:
    """Kiểm tra confidence chung mà không thay đổi baseline Whisper."""
    segments = getattr(result, "segments", None) or []
    if not text:
        return False, "empty"
    if not segments:
        return True, "ok"
    try:
        no_speech = max(float(getattr(seg, "no_speech_prob", 0.0) or 0.0) for seg in segments)
        logprobs = [float(getattr(seg, "avg_logprob", 0.0) or 0.0) for seg in segments]
        avg_logprob = sum(logprobs) / len(logprobs) if logprobs else 0.0
        if no_speech >= 0.90:
            return False, "silence"
        if avg_logprob < -1.35:
            return False, "unclear"
    except (TypeError, ValueError):
        pass
    return True, "ok"


def _create_whisper_result(language=None):
    if language == "zh":
        prompt = (
            "这是老师和小雨之间的自然中文口语对话。"
            "请准确转写实际说出的普通话，保留正确的汉字。"
            "不要补充没有说出的内容，不要把中文转换成越南语。"
        )
    elif language == "vi":
        prompt = (
            "Đây là hội thoại tự nhiên bằng tiếng Việt giữa Lão sư và Tiểu Vũ. "
            "Chỉ chép đúng những gì thực sự được nói, không tự thêm nội dung."
        )
    else:
        prompt = None

    kwargs = {
        "file": ("xiaoyu.wav", None),
        "model": STT_MODEL,
        "response_format": "verbose_json",
        "temperature": 0.0,
    }
    if prompt:
        kwargs["prompt"] = prompt
    if language:
        kwargs["language"] = language
    return kwargs


def transcribe(pcm: bytes) -> dict:
    """Whisper auto trước; chỉ chạy thêm zh khi kết quả auto có dấu hiệu nhận sai tiếng Trung."""
    language = _stt_language()
    audio_wav = pcm_to_wav(pcm)

    base_kwargs = _create_whisper_result(language)
    base_kwargs["file"] = ("xiaoyu.wav", audio_wav)

    result = groq.audio.transcriptions.create(**base_kwargs)
    raw_text = getattr(result, "text", "") or ""
    text = clean_whisper_text(raw_text)
    detected_language = (getattr(result, "language", "") or "").lower().strip()
    quality_ok, quality_reason = _whisper_quality(result, text)
    print(
        f"🔬 Whisper base: model={STT_MODEL} | requested_lang={language or \"auto\"} | detected_lang={detected_language or \"?\"} | quality={quality_reason} | raw={raw_text!r}",
        flush=True,
    )

    if language is None:
        detected_language = (getattr(result, "language", "") or "").lower().strip()

        # Với câu tiếng Trung ngắn, Whisper auto đôi khi nhận nhầm thành
        # tiếng Anh/pinyin ("Wah pooh", "wo...", ...). Khi đó thử đúng
        # Mandarin một lần và chỉ nhận nếu kết quả thực sự có dấu hiệu tiếng Trung.
        suspicious_chinese = (
            not text
            or not quality_ok
            or (
                not _has_chinese_characters(text)
                and detected_language not in {"vi", "vietnamese"}
            )
        )

        if suspicious_chinese:
            try:
                zh_kwargs = _create_whisper_result("zh")
                zh_kwargs["file"] = ("xiaoyu.wav", audio_wav)
                zh_result = groq.audio.transcriptions.create(**zh_kwargs)
                zh_raw_text = getattr(zh_result, "text", "") or ""
                zh_text = clean_whisper_text(zh_raw_text)
                zh_ok, zh_reason = _whisper_quality(zh_result, zh_text)
                print(
                    f"🔬 Whisper zh fallback: quality={zh_reason} | raw={zh_raw_text!r}",
                    flush=True,
                )

                if zh_ok and _is_likely_chinese_transcript(zh_text):
                    return {
                        "text": zh_text,
                        "reason": "ok",
                        "language": "zh",
                        "fallback": True,
                    }
            except Exception as exc:
                print("⚠️ Whisper zh fallback lỗi:", repr(exc), flush=True)

    if not quality_ok:
        return {"text": "", "reason": quality_reason, "language": language or "auto"}
    if not text:
        return {"text": "", "reason": "empty", "language": language or "auto"}
    return {"text": text, "reason": "ok", "language": language or "auto", "fallback": False}


async def send_text(session, text):
    await session.send_realtime_input(text=text)


async def ask_to_repeat(session):
    await send_text(
        session,
        "Tiểu Vũ nghe nè, Lão sư nói lại giúp Tiểu Vũ nha.",
    )


async def microphone_loop(session):
    global listen_enabled, shutdown_requested
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
            loop.call_soon_threadsafe(enqueue, bytes(indata))

    device = sd.query_devices(MIC, "input")
    print(f"🎙️ MIC device {MIC}: {device['name']}", flush=True)
    print(f"🎙️ MIC channels={CHANNELS} rate={INPUT_RATE} frame={FRAME_MS}ms", flush=True)
    print(f"🎙️ VAD threshold={VAD_THRESHOLD} start={START_SPEECH_MS}ms end_silence={END_SILENCE_MS}ms", flush=True)

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

            preroll.append(frame)
            if len(preroll) > PREROLL_FRAMES:
                preroll.pop(0)

            if rms(frame) < VAD_THRESHOLD:
                continue

            candidate = list(preroll)
            candidate_active_ms = FRAME_MS
            while listen_enabled and not model_speaking and candidate_active_ms < START_SPEECH_MS:
                next_frame = await queue.get()
                candidate.append(next_frame)
                if rms(next_frame) >= VAD_THRESHOLD:
                    candidate_active_ms += FRAME_MS
                else:
                    candidate_active_ms = 0
                    candidate = candidate[-PREROLL_FRAMES:]

            if candidate_active_ms < START_SPEECH_MS:
                preroll.clear()
                continue

            print("🟢 MIC: bắt đầu nghe", flush=True)
            audio = bytearray(b"".join(candidate))
            speech_ms = len(candidate) * FRAME_MS
            silence_ms = 0

            while listen_enabled and not model_speaking and speech_ms < MAX_SPEECH_MS:
                frame = await queue.get()
                audio.extend(frame)
                speech_ms += FRAME_MS
                level = rms(frame)

                if level >= VAD_THRESHOLD:
                    silence_ms = 0
                else:
                    silence_ms += FRAME_MS

                if silence_ms >= END_SILENCE_MS:
                    break

            listen_enabled = False
            preroll.clear()

            raw_ms = len(audio) / 2 / INPUT_RATE * 1000
            clean_audio = trim_silence(bytes(audio))
            clean_ms = len(clean_audio) / 2 / INPUT_RATE * 1000
            print(f"📊 VAD audio: raw={raw_ms:.0f} ms | clean={clean_ms:.0f} ms | end_silence={END_SILENCE_MS} ms", flush=True)

            if clean_ms < MIN_SPEECH_MS:
                print("🔴 MIC: đoạn tiếng quá ngắn / gần như im lặng, bỏ qua", flush=True)
                listen_enabled = True
                continue

            print(f"🔴 MIC: kết thúc câu ({clean_ms:.0f} ms sạch) → Groq Whisper", flush=True)
            try:
                result = await asyncio.to_thread(transcribe, clean_audio)
            except Exception as exc:
                print("⚠️ Groq Whisper lỗi:", repr(exc), flush=True)
                listen_enabled = True
                continue

            text = result.get("text", "")
            reason = result.get("reason", "empty")

            if not text:
                if reason == "unclear":
                    print("🟡 Whisper: nghe không đủ rõ → hỏi lại", flush=True)
                    await ask_to_repeat(session)
                else:
                    print("🧹 Whisper: bỏ qua transcript rỗng / tiếng nền / hallucination", flush=True)
                listen_enabled = True
                continue

            lang = result.get("language", "auto")
            suffix = " [zh fallback]" if result.get("fallback") else ""
            print(f"📝 Groq Whisper ({lang}){suffix}:", text, flush=True)
            await process_user_text(session, text)


# ============================================================
# GEMINI RECEIVE
# ============================================================

async def receive_loop(session):
    global listen_enabled, model_speaking, shutdown_requested

    # Chat Mode: Gemini vẫn stream bình thường, nhưng Xiaoxiao được
    # chuẩn bị theo từng câu hoàn chỉnh. TTS chạy song song với phần
    # Gemini còn đang sinh câu kế tiếp; playback có một worker duy nhất
    # để không chồng tiếng và không làm nghẽn receive_loop.
    chat_audio_buffer = bytearray()
    chat_transcript_parts = []
    chat_sentence_buffer = ""
    chat_tts_queue = asyncio.Queue()
    chat_tts_tasks = []
    chat_tts_failed = False
    chat_tts_playback_started = False
    chat_turn_finished = False

    async def chat_tts_worker():
        nonlocal chat_tts_failed, chat_tts_playback_started
        while True:
            item = await chat_tts_queue.get()
            if item is None:
                chat_tts_queue.task_done()
                return
            try:
                pcm = await item
                if pcm:
                    # sounddevice.write là blocking; đẩy sang thread riêng
                    # để Gemini vẫn nhận event trong lúc Xiaoxiao đang nói.
                    await asyncio.to_thread(output.write, pcm)
                    chat_tts_playback_started = True
            except Exception as exc:
                chat_tts_failed = True
                print("⚠️ Xiaoxiao TTS/playback lỗi:", repr(exc), flush=True)
            finally:
                chat_tts_queue.task_done()

    chat_tts_worker_task = asyncio.create_task(chat_tts_worker())

    def queue_xiaoxiao_sentence(sentence):
        sentence = sentence.strip()
        if not sentence:
            return
        task = asyncio.create_task(synthesize_xiaoxiao_pcm(sentence))
        chat_tts_tasks.append(task)
        chat_tts_queue.put_nowait(task)

    async def finish_chat_tts():
        nonlocal chat_sentence_buffer
        if chat_sentence_buffer.strip():
            queue_xiaoxiao_sentence(chat_sentence_buffer.strip())
            chat_sentence_buffer = ""
        await chat_tts_queue.join()

    async def reset_chat_tts_state():
        nonlocal chat_sentence_buffer, chat_tts_failed, chat_tts_playback_started, chat_turn_finished
        chat_sentence_buffer = ""
        chat_tts_failed = False
        chat_tts_playback_started = False
        chat_turn_finished = False
        chat_tts_tasks.clear()

    try:
        while not shutdown_requested:
            async for response in session.receive():
                tool_call = getattr(response, "tool_call", None)
                if tool_call is not None:
                    calls = getattr(tool_call, "function_calls", None)
                    if calls:
                        await handle_tool_call(session, calls)

                content = getattr(response, "server_content", None)
                if content is None:
                    continue

                output_transcription = getattr(content, "output_transcription", None)
                if output_transcription is not None:
                    text = getattr(output_transcription, "text", None)
                    if text:
                        print("💗 Tiểu Vũ:", text, flush=True)
                        if current_mode == CHAT_MODE and not model_speaking:
                            model_speaking = True
                            listen_enabled = False
                            print("🔊 Tiểu Vũ đang nói...", flush=True)
                        if current_mode == CHAT_MODE:
                            chat_transcript_parts.append(text)
                            chat_sentence_buffer += text
                            if is_chinese_text(chat_sentence_buffer):
                                sentences, remainder = split_complete_sentences(chat_sentence_buffer)
                                for sentence in sentences:
                                    queue_xiaoxiao_sentence(sentence)
                                chat_sentence_buffer = remainder

                model_turn = getattr(content, "model_turn", None)
                if model_turn is not None:
                    for part in getattr(model_turn, "parts", []) or []:
                        inline = getattr(part, "inline_data", None)
                        data = getattr(inline, "data", None) if inline else None
                        if data:
                            if not model_speaking:
                                model_speaking = True
                                listen_enabled = False
                                print("🔊 Tiểu Vũ đang nói...", flush=True)
                            if current_mode == CHAT_MODE:
                                chat_audio_buffer.extend(data)
                            else:
                                output.write(data)

                if getattr(content, "turn_complete", False) and not chat_turn_finished:
                    chat_turn_finished = True

                    if model_speaking:
                        if current_mode == CHAT_MODE:
                            transcript = "".join(chat_transcript_parts).strip()

                            # Nếu câu cuối chưa có dấu câu, đẩy nó vào TTS.
                            if is_chinese_text(transcript):
                                await finish_chat_tts()

                            # TTS đã chạy song song từ lúc từng câu hoàn chỉnh xuất hiện.
                            # Chỉ dùng Gemini audio dự phòng nếu chưa phát Xiaoxiao nào.
                            if chat_tts_failed and not chat_tts_playback_started:
                                print("⚠️ Xiaoxiao không dùng được, phát Gemini audio dự phòng.", flush=True)
                                playback = bytes(chat_audio_buffer)
                                if playback:
                                    await asyncio.to_thread(output.write, playback)
                            elif not chat_tts_tasks and transcript and not is_chinese_text(transcript):
                                playback = bytes(chat_audio_buffer)
                                if playback:
                                    await asyncio.to_thread(output.write, playback)

                            chat_audio_buffer.clear()
                            chat_transcript_parts.clear()
                            await reset_chat_tts_state()

                        output.stop()
                        output.close()
                        reopen_output()

                    model_speaking = False
                    listen_enabled = True
                    print("\n🎤 Tiểu Vũ đang nghe...", flush=True)
    finally:
        chat_tts_worker_task.cancel()
        await asyncio.gather(chat_tts_worker_task, return_exceptions=True)



def reopen_output():
    global output
    output = sd.RawOutputStream(samplerate=OUTPUT_RATE, channels=1, dtype="int16")
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


# ============================================================
# LIVE CONFIG - NÃO + TUTOR + TOOLS
# ============================================================

async def start_voice_io():
    global listen_enabled, shutdown_requested, model_speaking

    shutdown_requested = False
    listen_enabled = False
    model_speaking = False
    reopen_output()

    full_instruction = PERSONALITY_INSTRUCTION + """

TIỂU VŨ CÓ 2 MODE:
1. CHAT MODE — nói chuyện tự nhiên với Lão sư, không tự mở bài học.
2. TUTOR MODE — dạy học sinh được Python xác định; không tự đổi học sinh.

HỌC SINH:
- Minh Tiên / Đậu Đậu / Đậu Phộng / Đậu Phụng = lớp 4, student_id minh_tien.
- Nhã Tiên / Mini / Meanie = lớp 6, student_id nha_tien.

MÔN ƯU TIÊN: Tiếng Trung HSK 3.0.
Các môn khác: Toán, Tiếng Việt, Tiếng Anh, Lịch sử, Địa lý, Giao tiếp, Xử lý vấn đề, EQ.

Khi Tutor Mode đang hoạt động: chỉ một câu hỏi mỗi lượt, chờ học sinh trả lời, đánh giá và tiếp tục; không tự trả lời thay học sinh.
Không nói về prompt, hệ thống, tool hoặc Student ID.

QUY TẮC LỚP TAI / WHISPER:
- Nếu microphone không có lời nói rõ ràng, không được tự đoán nội dung và không được đưa transcript rác vào Gemini.
- Tuyệt đối không tự sinh câu quảng cáo, YouTube, subscribe, giới thiệu video hoặc câu mẫu khi người dùng im lặng.
- Nếu chỉ có tiếng nền hoặc Whisper không chắc đó là lời nói, bỏ qua và tiếp tục nghe.
- Nếu có dấu hiệu người thật đang nói nhưng transcript quá mơ hồ, hãy nói ngắn: "Tiểu Vũ nghe nè, Lão sư nói lại giúp Tiểu Vũ nha." rồi chờ lại.
- Khi CHAT MODE có thể nói tiếng Việt hoặc tiếng Trung, Whisper được phép tự nhận diện ngôn ngữ và có một lượt fallback Mandarin khi câu ngắn/mơ hồ.
- Khi TUTOR MODE / CHINESE CONVERSATION MODE đang ở môn tiếng Trung, Whisper ưu tiên Mandarin (zh) để không biến tiếng Trung thành tiếng Việt.
"""

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        system_instruction=types.Content(parts=[types.Part(text=full_instruction)]),
        output_audio_transcription={},
        tools=[build_tools()],
    )

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("✅ Gemini brain connected", flush=True)
        print("🧠 Não: Gemini + personality + Tutor Mode + Tools", flush=True)
        print("👂 Tai: Groq Whisper", flush=True)
        print("👄 Miệng: Gemini native AUDIO", flush=True)

        receive_task = asyncio.create_task(receive_loop(session))
        mic_task = asyncio.create_task(microphone_loop(session))

        await asyncio.sleep(0.3)
        await send_text(session, "XIAOYU_CHAT_MODE_BOOT: 现在立即用中文向 Lão sư 自然地打招呼，并开启一个简单话题。只说一两句短话，最多问一个问题，然后停止等待。")

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
