# ============================================================
# TIỂU VŨ - LIVE VOICE
# REBUILT VOICE TRANSPORT
# CHAT MODE + TUTOR MODE
# ============================================================
import asyncio
import math
import re
import unicodedata
from array import array
from collections import deque
from datetime import datetime

import sounddevice as sd
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, MODEL, MIC, INPUT_RATE, OUTPUT_RATE, CHANNELS, BLOCKSIZE
from personality import SYSTEM_INSTRUCTION
from tools.time_tool import get_time_text
from tools.calculator import calculate
from tools.calendar_tool import get_calendar_text
from tutor.lesson_flow import (
    start_lesson,
    next_lesson_question,
    answer_current_question,
    build_question_speech,
    build_answer_speech,
)

client = genai.Client(api_key=GEMINI_API_KEY)

# ============================================================
# RUNTIME STATE
# ============================================================
speaker_stream = None
speaker_queue = None
speaker_task = None
speaker_generation = 0
model_speaking = False
listen_ready = False
shutdown_requested = False
startup_greeting_sent = False
command_suppressed_until = 0.0

# Tutor state
tutor_mode = False
current_student = None
current_student_id = None
current_subject = None
current_grade = None
lesson_session = None
lesson_waiting_for_answer = False
rotation_index = 0
last_subject = None

# ============================================================
# STUDENTS / SUBJECTS
# ============================================================
STUDENTS = {
    "minh_tien": {
        "student_id": "minh_tien",
        "official_name": "Minh Tiên",
        "gender": "male",
        "grade": 4,
        "aliases": [
            "Minh Tiên", "Minh Tien", "Đậu Đậu", "Dau Dau",
            "Đậu Phộng", "Dau Phong", "Đậu Phụng", "Dau Phung",
            "Đầu Đầu", "Đầu Phòng",
        ],
    },
    "nha_tien": {
        "student_id": "nha_tien",
        "official_name": "Nhã Tiên",
        "gender": "female",
        "grade": 6,
        "aliases": ["Nhã Tiên", "Nha Tien", "Mini", "mini", "Meanie", "Mi Ni", "米妮", "미니"],
    },
}
CANONICAL_STUDENT_NAMES = {"minh_tien": "Đậu Đậu", "nha_tien": "Mini"}
STUDENT_ALIASES = {}
for student_id, student in STUDENTS.items():
    for alias in student["aliases"]:
        STUDENT_ALIASES[alias.lower().strip()] = {
            "student_id": student_id,
            "official_name": student["official_name"],
            "called_name": alias.strip(),
            "gender": student["gender"],
            "grade": student["grade"],
        }

SUBJECT_PATTERNS = {
    "chinese": ["tiếng trung", "tieng trung", "tiếng hoa", "hsk", "chinese"],
    "math": ["toán", "toan", "math", "phép cộng", "phép trừ", "phép nhân", "phép chia", "nhân", "chia", "cửu chương"],
    "vietnamese": ["tiếng việt", "ngữ văn"],
    "english": ["tiếng anh", "english"],
    "history": ["lịch sử", "history"],
    "geography": ["địa lý", "geography"],
    "eq": ["giao tiếp", "communication", "eq"],
    "problem_solving": ["xử lý vấn đề", "giải quyết vấn đề", "problem solving"],
    "emotional_management": ["cảm xúc", "quản lý cảm xúc", "emotional management"],
}
SUBJECT_ROTATION = ["chinese", "math", "vietnamese", "english", "history", "geography", "eq", "problem_solving", "emotional_management"]
SUBJECT_NAMES = {
    "chinese": "Tiếng Trung HSK 3.0",
    "math": "Toán",
    "vietnamese": "Tiếng Việt",
    "english": "Tiếng Anh",
    "history": "Lịch sử",
    "geography": "Địa lý",
    "eq": "Kỹ năng EQ và giao tiếp",
    "problem_solving": "Kỹ năng giải quyết vấn đề",
    "emotional_management": "Quản lý cảm xúc",
}
MINH_TIEN_PATTERNS = ["đậu đậu", "đầu đầu", "dau dau", "daudau", "đậuđậu", "đậu phộng", "đầu phòng", "dau phong", "đậu phụng", "đầu phụng", "dau phung"]
NHA_TIEN_PATTERNS = ["mini", "mi ni", "meanie", "me ni"]
LEARNING_PATTERNS = ["muốn học", "bắt đầu học", "học đi", "học nha", "học nhé", "học thôi", "vào học", "cho con học", "học bài", "giờ học"]
FAREWELL_PATTERNS = ["tạm biệt", "tam biet", "dừng phiên", "dung phien", "dừng chat", "dung chat", "nghỉ nhé", "nghi nhe", "ngủ thôi", "ngu thoi"]

# ============================================================
# TEXT / COMMAND HELPERS
# ============================================================
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"[.,!?;:，。！？；：]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def remove_accents(text):
    if not isinstance(text, str):
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn").lower().strip()


def compact_text(text):
    return re.sub(r"\s+", "", normalize_text(text))


def alias_matches(alias, text):
    normalized = normalize_text(text)
    no_accent = remove_accents(normalized)
    alias_normalized = normalize_text(alias)
    alias_no_accent = remove_accents(alias_normalized)
    return alias_normalized in normalized or alias_no_accent in no_accent


def detect_student(text):
    normalized = normalize_text(text)
    compact = compact_text(text)
    no_accent = remove_accents(text)
    for alias, student in sorted(STUDENT_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias_matches(alias, text):
            print(f"🔎 Nhận diện: {CANONICAL_STUDENT_NAMES.get(student['student_id'], student['official_name'])}", flush=True)
            return student
    for pattern in MINH_TIEN_PATTERNS:
        p = normalize_text(pattern)
        if p in normalized or remove_accents(p) in no_accent or compact_text(p) in compact:
            return STUDENT_ALIASES["đậu đậu"]
    for pattern in NHA_TIEN_PATTERNS:
        p = normalize_text(pattern)
        if p in normalized or remove_accents(p) in no_accent:
            return STUDENT_ALIASES["mini"]
    return None


def detect_subject(text):
    normalized = normalize_text(text)
    no_accent = remove_accents(text)
    for subject, words in SUBJECT_PATTERNS.items():
        for word in words:
            if word in normalized or remove_accents(word) in no_accent:
                return subject
    return None


def detect_learning_intent(text):
    normalized = normalize_text(text)
    no_accent = remove_accents(text)
    return any(p in normalized or remove_accents(p) in no_accent for p in LEARNING_PATTERNS)


def detect_farewell(text):
    normalized = normalize_text(text)
    no_accent = remove_accents(text)
    return any(p in normalized or remove_accents(p) in no_accent for p in FAREWELL_PATTERNS)


def detect_tutor_command(text):
    student = detect_student(text)
    subject = detect_subject(text)
    learning = detect_learning_intent(text)
    if student and learning:
        return {"intent": "start_lesson", "student": student, "subject": subject}
    if student:
        return {"intent": "switch_student", "student": student, "subject": subject}
    if learning:
        return {"intent": "unknown_student", "student": None, "subject": subject}
    return {"intent": "chat", "student": None, "subject": None}


def choose_subject(subject=None):
    global rotation_index, last_subject
    if subject in SUBJECT_NAMES:
        last_subject = subject
        return subject
    if last_subject in SUBJECT_ROTATION:
        rotation_index = (SUBJECT_ROTATION.index(last_subject) + 1) % len(SUBJECT_ROTATION)
    selected = SUBJECT_ROTATION[rotation_index % len(SUBJECT_ROTATION)]
    rotation_index = (rotation_index + 1) % len(SUBJECT_ROTATION)
    last_subject = selected
    return selected


def get_level_instruction(grade):
    if grade == 4:
        return "HỌC SINH LỚP 4.\nTOÁN: nhân, chia, chia có dư, bài toán lời văn, phân số, chu vi, diện tích, logic.\nTIẾNG TRUNG: HSK 3.0, từ vựng, nghe hiểu, phản xạ, hội thoại."
    return "HỌC SINH LỚP 6.\nTOÁN: số nguyên, phân số, biểu thức, hình học, logic.\nTIẾNG TRUNG: HSK 3.0, tăng vốn từ, nghe hiểu, hội thoại, đọc hiểu."

# ============================================================
# GEMINI COMMANDS / TUTOR
# ============================================================
async def send_text_command(session, text, suppress_seconds=2):
    global command_suppressed_until
    command_suppressed_until = asyncio.get_running_loop().time() + suppress_seconds
    try:
        await session.send_realtime_input(text=text)
        return True
    except Exception as e:
        print("⚠️ Command lỗi:", repr(e), flush=True)
        return False


async def send_startup_greeting(session):
    global startup_greeting_sent, command_suppressed_until
    if startup_greeting_sent:
        return
    hour = datetime.now().hour
    time_hint = "Đây là buổi sáng sớm." if hour < 7 else ""
    startup_greeting_sent = True
    prompt = f"""Tiểu Vũ vừa kết nối với Lão sư Minh Tâm.\n{time_hint}\nHãy chủ động mở đầu cuộc trò chuyện bằng một lời chào tự nhiên, thân thiện, vui vẻ đúng tính cách Tiểu Vũ trong personality.py. Nếu là trước 07:00, chào buổi sáng Lão sư. Có thể hỏi thăm Lão sư một câu ngắn. Không nói về hệ thống, Python, prompt hay chế độ kỹ thuật. Sau lời chào hãy chờ Lão sư nói."""
    try:
        command_suppressed_until = 0.0
        await session.send_realtime_input(text=prompt)
    except Exception as e:
        startup_greeting_sent = False
        print("⚠️ Startup greeting lỗi:", repr(e), flush=True)


async def start_voice_lesson(student, subject=None):
    global lesson_session, lesson_waiting_for_answer
    subject_id = choose_subject(subject)
    lesson = start_lesson(
        student_id=student["student_id"],
        subject_id=subject_id,
        nickname=CANONICAL_STUDENT_NAMES.get(student["student_id"], student["official_name"]),
    )
    lesson_session = lesson["session"]
    lesson_waiting_for_answer = bool(lesson.get("waiting_for_answer"))
    return build_question_speech(lesson_session, lesson.get("question"))


async def process_lesson_answer(session, text):
    global lesson_waiting_for_answer
    if not lesson_session or not lesson_waiting_for_answer:
        return False
    try:
        result = answer_current_question(lesson_session, text)
        feedback = build_answer_speech(lesson_session, result["result"])
        next_question = next_lesson_question(lesson_session)
        lesson_waiting_for_answer = True
        next_speech = build_question_speech(lesson_session, next_question)
        await send_text_command(
            session,
            f"""Đây là kết quả từ lesson flow:\n{feedback}\n\nSau đó hỏi ngay câu tiếp theo:\n{next_speech}\n\nGiữ giọng cô gia sư thân thiện, khích lệ. Không nói về hệ thống. Không đổi học sinh hoặc môn.""",
            2,
        )
        return True
    except Exception as e:
        print("⚠️ Lesson flow lỗi:", repr(e), flush=True)
        return False


async def start_tutor_session(session, student, subject=None):
    global tutor_mode, current_student, current_student_id, current_subject, current_grade, lesson_session, lesson_waiting_for_answer
    if not student:
        return
    student_id = student["student_id"]
    called_name = CANONICAL_STUDENT_NAMES.get(student_id, student["official_name"])
    grade = student["grade"]
    selected_subject = choose_subject(subject)
    tutor_mode = True
    current_student = called_name
    current_student_id = student_id
    current_subject = selected_subject
    current_grade = grade
    lesson_session = None
    lesson_waiting_for_answer = False
    print(); print("🎓 BẮT ĐẦU HỌC", flush=True); print("👤", current_student, flush=True); print("📚", SUBJECT_NAMES[selected_subject], flush=True)
    try:
        question_speech = await start_voice_lesson(student, selected_subject)
        await send_text_command(
            session,
            f"""TUTOR MODE.\nPython đã xác định học sinh: {current_student}\nMôn hiện tại: {SUBJECT_NAMES[selected_subject]}\nLesson flow đã tạo câu hỏi đầu tiên:\n{question_speech}\nHãy chào {current_student} thật tự nhiên, sau đó đọc đúng câu hỏi trên. Không tự đổi học sinh, không tự đổi môn, không thêm câu hỏi ngoài lesson flow. Sau khi hỏi xong, chờ học sinh trả lời.""",
            3,
        )
        return
    except Exception as e:
        print("⚠️ Không khởi động được lesson flow:", repr(e), flush=True)
    await send_text_command(
        session,
        f"""TUTOR MODE.\nHọc sinh: {current_student}\nLớp: {grade}\nMôn: {SUBJECT_NAMES[selected_subject]}\n{get_level_instruction(grade)}\nChỉ gọi học sinh là {current_student}. Không tự đổi môn hoặc học sinh. Mỗi lần chỉ hỏi một câu. Chào học sinh và đưa một câu hỏi.""",
        3,
    )


async def exit_tutor_mode(session):
    global tutor_mode, current_student, current_student_id, current_subject, current_grade, lesson_session, lesson_waiting_for_answer
    tutor_mode = False
    current_student = None
    current_student_id = None
    current_subject = None
    current_grade = None
    lesson_session = None
    lesson_waiting_for_answer = False
    await send_text_command(session, "CHAT MODE. Người nói là Lão sư Minh Tâm. Không tự chuyển sang Tutor Mode. Chờ Lão sư nói tiếp.", 1)


async def process_user_text(session, text):
    global current_subject
    if not text:
        return
    text = text.strip()
    if not text:
        return
    if asyncio.get_running_loop().time() < command_suppressed_until:
        print("🔇 Bỏ qua tiếng của Tiểu Vũ:", text, flush=True)
        return
    print("\n👤 Người nói:", text, flush=True)
    if detect_farewell(text):
        await exit_tutor_mode(session)
        return
    command = detect_tutor_command(text)
    intent = command["intent"]
    student = command["student"]
    subject = command["subject"]
    if intent == "start_lesson":
        if tutor_mode and current_student_id == student["student_id"]:
            return
        await start_tutor_session(session, student, subject)
        return
    if intent == "switch_student":
        if tutor_mode and current_student_id == student["student_id"]:
            if subject:
                current_subject = choose_subject(subject)
                await send_text_command(session, f"Tiếp tục với {current_student}. Chuyển sang môn {SUBJECT_NAMES[current_subject]}. Đọc câu hỏi tiếp theo của lesson flow rồi chờ câu trả lời.", 2)
            return
        await start_tutor_session(session, student, subject)
        return
    if intent == "unknown_student":
        await send_text_command(session, 'Hỏi tự nhiên một câu ngắn: "Tiểu Vũ dạy Đậu Đậu hay Mini nè?"', 2)
        return
    if tutor_mode and lesson_session and lesson_waiting_for_answer:
        if await process_lesson_answer(session, text):
            return
    print(f"🎓 Đang dạy {current_student}" if tutor_mode else "💬 CHAT MODE", flush=True)

# ============================================================
# TOOLS
# ============================================================
def current_time():
    return get_time_text()


def calculator(expression):
    return calculate(expression)


def current_calendar():
    return get_calendar_text()


async def handle_tool_call(session, function_calls):
    responses = []
    for call in function_calls:
        name = call.name
        args = call.args or {}
        if name == "current_time":
            result = current_time()
        elif name == "calculator":
            result = calculator(args.get("expression", ""))
        elif name == "current_calendar":
            result = current_calendar()
        else:
            result = "Không có tool"
        responses.append(types.FunctionResponse(id=call.id, name=name, response={"result": result}))
    if responses:
        await session.send_tool_response(function_responses=responses)

# ============================================================
# AUDIO OUTPUT
# ============================================================
def open_speaker():
    global speaker_stream
    if speaker_stream is None:
        speaker_stream = sd.RawOutputStream(
            samplerate=OUTPUT_RATE,
            channels=1,
            dtype="int16",
            blocksize=0,
        )
        speaker_stream.start()
    return speaker_stream


def close_speaker():
    global speaker_stream
    stream = speaker_stream
    speaker_stream = None
    if stream is None:
        return
    try:
        stream.stop()
    except Exception:
        pass
    try:
        stream.close()
    except Exception:
        pass


def clear_speaker_queue():
    global speaker_generation
    speaker_generation += 1
    if speaker_queue is None:
        return
    while True:
        try:
            speaker_queue.get_nowait()
        except asyncio.QueueEmpty:
            break


async def speaker_writer():
    while True:
        item = await speaker_queue.get()
        if item is None:
            return
        generation, data = item
        if generation != speaker_generation:
            continue
        try:
            await asyncio.to_thread(open_speaker().write, data)
        except Exception as e:
            print("⚠️ Speaker lỗi:", repr(e), flush=True)
            close_speaker()


async def queue_speaker_audio(data):
    if not data or speaker_queue is None or shutdown_requested:
        return
    try:
        await speaker_queue.put((speaker_generation, data))
    except asyncio.CancelledError:
        return

# ============================================================
# MICROPHONE: MANUAL VAD
# ============================================================
# The previous version continuously fed the microphone to Gemini's automatic
# VAD. That path repeatedly showed "listening" but produced no input transcript.
# The rebuilt transport uses the documented manual activity_start/activity_end
# protocol. The client controls turn boundaries and keeps a small pre-roll so
# the first consonants of a sentence are not cut off.
VAD_SILENCE_MS = 800
VAD_PREROLL_MS = 200
VAD_MIN_SPEECH_MS = 160
VAD_MIN_RMS = 450.0
VAD_NOISE_MULTIPLIER = 2.2
VAD_LOG_INTERVAL = 0.75


def rms_level(data):
    if not data:
        return 0.0
    samples = array("h")
    samples.frombytes(data)
    if not samples:
        return 0.0
    total = 0.0
    for sample in samples:
        total += sample * sample
    return math.sqrt(total / len(samples))


async def microphone_sender(session):
    global listen_ready, model_speaking
    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue(maxsize=80)
    pre_roll = deque(maxlen=max(1, VAD_PREROLL_MS // 40))
    stopped = False

    def enqueue(data):
        if stopped or shutdown_requested:
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
        try:
            loop.call_soon_threadsafe(enqueue, bytes(indata))
        except Exception as e:
            print("⚠️ MIC callback lỗi:", repr(e), flush=True)

    try:
        device_info = sd.query_devices(MIC, "input")
        print(f"🎙️ MIC device {MIC}: {device_info['name']}", flush=True)
        print(f"🎙️ MIC channels={device_info['max_input_channels']} rate={INPUT_RATE} block={BLOCKSIZE}", flush=True)
    except Exception as e:
        print("⚠️ Không đọc được thông tin MIC:", repr(e), flush=True)

    with sd.RawInputStream(
        device=MIC,
        samplerate=INPUT_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=BLOCKSIZE,
        callback=callback,
    ):
        print("🎤 Microphone sẵn sàng.", flush=True)
        print("⏳ Chờ Tiểu Vũ nói xong rồi bắt đầu nghe.", flush=True)

        noise_samples = []
        noise_ready = False
        speech_active = False
        speech_ms = 0
        silence_ms = 0
        threshold = VAD_MIN_RMS
        last_log = 0.0
        sent_bytes = 0

        while not shutdown_requested:
            data = await audio_queue.get()
            level = rms_level(data)
            chunk_ms = max(1, int(BLOCKSIZE * 1000 / INPUT_RATE))

            # Never interpret the speaker's own voice as user speech.
            if not listen_ready or model_speaking:
                pre_roll.clear()
                noise_samples.clear()
                noise_ready = False
                speech_active = False
                speech_ms = 0
                silence_ms = 0
                continue

            now = loop.time()
            if not noise_ready:
                noise_samples.append(level)
                if len(noise_samples) >= max(10, int(1000 / chunk_ms)):
                    noise = sum(noise_samples) / len(noise_samples)
                    threshold = max(VAD_MIN_RMS, noise * VAD_NOISE_MULTIPLIER)
                    noise_ready = True
                    print(f"🎙️ VAD ready: noise={noise:.0f} threshold={threshold:.0f}", flush=True)
                continue

            pre_roll.append(data)
            if now - last_log >= VAD_LOG_INTERVAL:
                print(f"🎙️ MIC level={level:.0f} threshold={threshold:.0f}", flush=True)
                last_log = now

            is_speech = level >= threshold

            if not speech_active:
                if is_speech:
                    speech_active = True
                    speech_ms = chunk_ms
                    silence_ms = 0
                    listen_ready = False
                    print("🟢 VAD: speech START", flush=True)
                    try:
                        await session.send_realtime_input(activity_start=types.ActivityStart())
                        for buffered in pre_roll:
                            await session.send_realtime_input(
                                audio=types.Blob(data=buffered, mime_type="audio/pcm;rate=16000")
                            )
                            sent_bytes += len(buffered)
                    except Exception as e:
                        print("⚠️ activity_start/audio lỗi:", repr(e), flush=True)
                        speech_active = False
                        listen_ready = True
                        continue
                continue

            # Speech turn is active: send every chunk, including short pauses.
            try:
                await session.send_realtime_input(
                    audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                )
                sent_bytes += len(data)
            except Exception as e:
                print("⚠️ MIC gửi audio lỗi:", repr(e), flush=True)
                speech_active = False
                listen_ready = True
                continue

            speech_ms += chunk_ms
            if is_speech:
                silence_ms = 0
            else:
                silence_ms += chunk_ms

            if sent_bytes >= 32000:
                print(f"🎤 MIC → Gemini: {sent_bytes} bytes", flush=True)
                sent_bytes = 0

            if speech_ms >= VAD_MIN_SPEECH_MS and silence_ms >= VAD_SILENCE_MS:
                print(f"🔴 VAD: speech END ({speech_ms} ms)", flush=True)
                try:
                    await session.send_realtime_input(activity_end=types.ActivityEnd())
                except Exception as e:
                    print("⚠️ activity_end lỗi:", repr(e), flush=True)
                speech_active = False
                speech_ms = 0
                silence_ms = 0
                pre_roll.clear()
                # Remain locked until Gemini reports turn_complete.
                listen_ready = False

    stopped = True

# ============================================================
# RECEIVE LOOP
# ============================================================
async def receive_loop(session):
    global speaker_queue, speaker_task, model_speaking, listen_ready
    speaker_queue = asyncio.Queue(maxsize=256)
    speaker_task = asyncio.create_task(speaker_writer())
    last_input_transcript = ""
    try:
        async for response in session.receive():
            tool = getattr(response, "tool_call", None)
            if tool:
                calls = getattr(tool, "function_calls", None)
                if calls:
                    await handle_tool_call(session, calls)

            server = getattr(response, "server_content", None)
            if server is None:
                continue

            if getattr(server, "interrupted", False):
                print("🛑 Tiểu Vũ bị Lão sư ngắt lời.", flush=True)
                model_speaking = False
                clear_speaker_queue()

            input_transcription = getattr(server, "input_transcription", None)
            input_text = getattr(input_transcription, "text", None)
            if input_text:
                clean_text = input_text.strip()
                if clean_text and clean_text != last_input_transcript:
                    last_input_transcript = clean_text
                    print("📝 INPUT TRANSCRIPT:", repr(clean_text), flush=True)
                    await process_user_text(session, clean_text)

            output_transcription = getattr(server, "output_transcription", None)
            output_text = getattr(output_transcription, "text", None)
            if output_text:
                print("💗 Tiểu Vũ:", output_text, flush=True)

            model_turn = getattr(server, "model_turn", None)
            if model_turn:
                model_speaking = True
                for part in getattr(model_turn, "parts", []):
                    inline = getattr(part, "inline_data", None)
                    data = getattr(inline, "data", None)
                    if data:
                        await queue_speaker_audio(data)

            if getattr(server, "turn_complete", False):
                model_speaking = False
                last_input_transcript = ""
                if not shutdown_requested:
                    listen_ready = True
                    print("\n🎤 Tiểu Vũ đang nghe...", flush=True)
    finally:
        model_speaking = False
        listen_ready = False
        clear_speaker_queue()
        if speaker_task:
            try:
                speaker_queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
            try:
                await speaker_task
            except Exception:
                pass
        speaker_task = None
        speaker_queue = None

# ============================================================
# LIVE CONFIG
# ============================================================
def build_live_config():
    tools = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="current_time",
                description="Lấy giờ Việt Nam",
                parameters=types.Schema(type="OBJECT", properties={}),
            ),
            types.FunctionDeclaration(
                name="calculator",
                description="Tính toán",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={"expression": types.Schema(type="STRING")},
                    required=["expression"],
                ),
            ),
            types.FunctionDeclaration(
                name="current_calendar",
                description="Lấy lịch dương âm",
                parameters=types.Schema(type="OBJECT", properties={}),
            ),
        ]
    )

    instruction = SYSTEM_INSTRUCTION + """
TIỂU VŨ LIVE VOICE.
CHAT MODE: Nói chuyện với Lão sư Minh Tâm như một người bạn thân. Giữ personality.py: nữ, miền Nam, thân thiện, tự nhiên, vui tính, hơi tinh nghịch.
TUTOR MODE: Python quyết định học sinh. Python/lesson flow quyết định câu hỏi và độ khó. Không tự đổi tên, không tự đổi môn, không tự restart bài học. Nói với học sinh bằng giọng cô gia sư hoà nhã, khích lệ.
CHUYỂN MODE: Khi nhận diện Mini hoặc Đậu Đậu/Đậu Phộng muốn học, vào Tutor Mode. Khi đang nói với Lão sư, giữ CHAT MODE.
STARTUP: Khi Python yêu cầu lời chào khởi động, chủ động mở lời tự nhiên rồi chờ Lão sư.
TOOLS: Hỏi giờ dùng current_time. Tính dùng calculator. Ngày dùng current_calendar. Không đoán dữ liệu.
"""

    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(parts=[types.Part(text=instruction)]),
        tools=[tools],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        # Automatic VAD is deliberately disabled. microphone_sender owns the
        # activity_start/activity_end boundaries.
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(disabled=True)
        ),
    )

# ============================================================
# CONNECTION LIFECYCLE
# ============================================================
async def run_one_connection():
    global listen_ready, startup_greeting_sent
    listen_ready = False
    startup_greeting_sent = False
    open_speaker()
    config = build_live_config()
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Gemini Live connected", flush=True)
            receive_task = asyncio.create_task(receive_loop(session))
            microphone_task = asyncio.create_task(microphone_sender(session))
            await asyncio.sleep(0.25)
            await send_startup_greeting(session)
            await asyncio.gather(receive_task, microphone_task)
    finally:
        listen_ready = False
        clear_speaker_queue()
        close_speaker()


async def start_live_voice():
    global shutdown_requested
    shutdown_requested = False
    delay = 1
    while not shutdown_requested:
        try:
            await run_one_connection()
            delay = 1
        except Exception as e:
            print("Reconnect:", repr(e), flush=True)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 10)


def cleanup():
    global shutdown_requested, listen_ready
    shutdown_requested = True
    listen_ready = False
    clear_speaker_queue()
    close_speaker()
    print("🧹 Tiểu Vũ đóng.", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(start_live_voice())
    except KeyboardInterrupt:
        print("👋 Tiểu Vũ đã tắt.", flush=True)
        cleanup()
