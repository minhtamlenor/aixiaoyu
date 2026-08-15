# ============================================================
# TIỂU VŨ - LIVE VOICE
# STABLE STUDENT RECOGNITION VERSION
#
# CHAT MODE + TUTOR MODE
# HSK 3.0 + 3 TOOLS
#
# CORE:
# - Python nhận diện học sinh
# - Canonical name
# - Fuzzy ASR correction
# - Reconnect giữ trạng thái
# - Không tự đổi môn
# - Không tự restart bài học
# ============================================================

import asyncio
import random
import re
import unicodedata
from datetime import datetime

import sounddevice as sd
from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY,
    MODEL,
    MIC,
    INPUT_RATE,
    OUTPUT_RATE,
    CHANNELS,
    BLOCKSIZE,
)
from personality import SYSTEM_INSTRUCTION
from tools.time_tool import get_time_text
from tools.calculator import calculate
from tools.calendar_tool import get_calendar_text

# Existing lesson framework. Do not duplicate it here.
from tutor.lesson_flow import (
    start_lesson,
    next_lesson_question,
    answer_current_question,
    build_question_speech,
    build_answer_speech,
)


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        api_version="v1beta"
    )
)


# ============================================================
# GLOBAL STATE
# ============================================================

speaker_stream = None
tutor_mode = False

current_student = None
current_student_id = None
current_subject = None
current_grade = None

lesson_session = None
lesson_waiting_for_answer = False

question_count = 0
rotation_index = 0
last_subject = None

shutdown_requested = False
startup_greeting_sent = False
command_suppressed_until = 0.0


# ============================================================
# STUDENT DATABASE
# ============================================================

STUDENTS = {
    "minh_tien": {
        "student_id": "minh_tien",
        "official_name": "Minh Tiên",
        "gender": "male",
        "grade": 4,
        "aliases": [
            "Minh Tiên", "Minh Tien",
            "Đậu Đậu", "Dau Dau",
            "Đậu Phộng", "Dau Phong",
            "Đậu Phụng", "Dau Phung",
            "Đầu Đầu", "Đầu Phòng",
        ],
    },
    "nha_tien": {
        "student_id": "nha_tien",
        "official_name": "Nhã Tiên",
        "gender": "female",
        "grade": 6,
        "aliases": [
            "Nhã Tiên", "Nha Tien",
            "Mini", "mini",
            "Meanie", "Mi Ni",
            "米妮", "미니",
        ],
    },
}

CANONICAL_STUDENT_NAMES = {
    "minh_tien": "Đậu Đậu",
    "nha_tien": "Mini",
}

STUDENT_ALIASES = {}
for student_id, student in STUDENTS.items():
    for alias in student["aliases"]:
        key = alias.lower().strip()
        STUDENT_ALIASES[key] = {
            "student_id": student_id,
            "official_name": student["official_name"],
            "called_name": alias.strip(),
            "gender": student["gender"],
            "grade": student["grade"],
        }


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"[.,!?;:，。！？；：]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_accents(text):
    if not isinstance(text, str):
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
    )
    return text.lower().strip()


def compact_text(text):
    return re.sub(r"\s+", "", normalize_text(text))


# ============================================================
# NAME MATCHING
# ============================================================

def alias_matches(alias, text):
    normalized = normalize_text(text)
    no_accent = remove_accents(normalized)
    alias_normalized = normalize_text(alias)
    alias_no_accent = remove_accents(alias_normalized)
    return (
        alias_normalized in normalized
        or alias_no_accent in no_accent
    )


MINH_TIEN_PATTERNS = [
    "đậu đậu", "đầu đầu", "dau dau", "daudau", "đậuđậu",
    "đậu phộng", "đầu phòng", "dau phong",
    "đậu phụng", "đầu phụng", "dau phung",
]

NHA_TIEN_PATTERNS = [
    "mini", "mi ni", "meanie", "me ni",
]


# ============================================================
# DETECT STUDENT
# ============================================================

def detect_student(text):
    normalized = normalize_text(text)
    compact = compact_text(text)
    no_accent = remove_accents(text)

    for alias, student in sorted(
        STUDENT_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        if alias_matches(alias, text):
            print(
                f"🔎 Nhận diện: {CANONICAL_STUDENT_NAMES.get(student['student_id'], student['official_name'])}",
                flush=True,
            )
            return student

    for pattern in MINH_TIEN_PATTERNS:
        p = normalize_text(pattern)
        if (
            p in normalized
            or remove_accents(p) in no_accent
            or compact_text(p) in compact
        ):
            return STUDENT_ALIASES["đậu đậu"]

    for pattern in NHA_TIEN_PATTERNS:
        p = normalize_text(pattern)
        if p in normalized or remove_accents(p) in no_accent:
            return STUDENT_ALIASES["mini"]

    return None


# ============================================================
# SUBJECT DETECTION
# ============================================================

SUBJECT_PATTERNS = {
    "chinese": ["tiếng trung", "tieng trung", "tiếng hoa", "hsk", "chinese"],
    "math": ["toán", "toan", "math", "phép cộng", "phép trừ", "phép nhân", "phép chia", "nhân", "chia", "cửu chương"],
    "vietnamese": ["tiếng việt", "ngữ văn"],
    "english": ["tiếng anh", "english"],
    "history": ["lịch sử", "history"],
    "geography": ["địa lý", "geography"],
    "communication": ["giao tiếp", "communication"],
    "problem_solving": ["xử lý vấn đề", "giải quyết vấn đề", "problem solving"],
    "emotional_intelligence": ["cảm xúc", "quản lý cảm xúc", "eq"],
}


def detect_subject(text):
    normalized = normalize_text(text)
    no_accent = remove_accents(text)
    for subject, words in SUBJECT_PATTERNS.items():
        for word in words:
            if word in normalized or remove_accents(word) in no_accent:
                return subject
    return None


# ============================================================
# LEARNING INTENT
# ============================================================

LEARNING_PATTERNS = [
    "muốn học", "bắt đầu học", "học đi", "học nha", "học nhé",
    "học thôi", "vào học", "cho con học", "học bài", "giờ học",
]


def detect_learning_intent(text):
    normalized = normalize_text(text)
    no_accent = remove_accents(text)
    for pattern in LEARNING_PATTERNS:
        if pattern in normalized or remove_accents(pattern) in no_accent:
            return True
    return False


# ============================================================
# FAREWELL
# ============================================================

FAREWELL_PATTERNS = [
    "tạm biệt",
    "tam biet",
    "dừng phiên",
    "dung phien",
    "dừng chat",
    "dung chat",
    "nghỉ nhé",
    "nghi nhe",
    "ngủ thôi",
    "ngu thoi",
]


def detect_farewell(text):
    normalized = normalize_text(text)
    no_accent = remove_accents(text)
    return any(
        pattern in normalized
        or remove_accents(pattern) in no_accent
        for pattern in FAREWELL_PATTERNS
    )


# ============================================================
# MENTIONS TEACHER
# ============================================================

def mentions_teacher(text):
    normalized = normalize_text(text)
    return "lão sư" in normalized or "lao su" in remove_accents(text)


# ============================================================
# SUBJECT ROTATION
# ============================================================

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


def choose_subject(subject=None):
    global rotation_index
    global last_subject

    if subject in SUBJECT_NAMES:
        last_subject = subject
        return subject

    # Không có môn cụ thể: dùng luân phiên các môn đã có.
    # Không tạo môn mới và không thay đổi curriculum hiện tại.
    if last_subject in SUBJECT_ROTATION:
        start = SUBJECT_ROTATION.index(last_subject) + 1
        rotation_index = start % len(SUBJECT_ROTATION)
    else:
        rotation_index %= len(SUBJECT_ROTATION)

    selected = SUBJECT_ROTATION[rotation_index]
    rotation_index = (rotation_index + 1) % len(SUBJECT_ROTATION)
    last_subject = selected
    return selected


# ============================================================
# LEVEL INSTRUCTION
# ============================================================

def get_level_instruction(grade):
    if grade == 4:
        return """
HỌC SINH LỚP 4.

TOÁN:
- nhân
- chia
- chia có dư
- bài toán lời văn
- phân số
- chu vi
- diện tích
- logic

TIẾNG TRUNG:
- HSK 3.0
- từ vựng
- nghe hiểu
- phản xạ
- hội thoại
"""

    return """
HỌC SINH LỚP 6.

TOÁN:
- số nguyên
- phân số
- biểu thức
- hình học
- logic

TIẾNG TRUNG:
- HSK 3.0
- tăng vốn từ
- nghe hiểu
- hội thoại
- đọc hiểu
"""


# ============================================================
# TUTOR COMMAND
# ============================================================

def detect_tutor_command(text):
    student = detect_student(text)
    subject = detect_subject(text)
    learning = detect_learning_intent(text)

    if mentions_teacher(text):
        return {"intent": "chat", "student": None, "subject": None}

    if student and learning:
        return {"intent": "start_lesson", "student": student, "subject": subject}

    if student:
        return {"intent": "switch_student", "student": student, "subject": subject}

    if learning:
        return {"intent": "unknown_student", "student": None, "subject": subject}

    return {"intent": "chat", "student": None, "subject": None}


# ============================================================
# SEND COMMAND TO GEMINI
# ============================================================

async def send_text_command(session, text, suppress_seconds=3):
    global command_suppressed_until

    loop = asyncio.get_running_loop()
    command_suppressed_until = loop.time() + suppress_seconds

    try:
        await session.send_realtime_input(text=text)
        return True
    except Exception as e:
        print("⚠️ Command lỗi:", repr(e), flush=True)
        return False


# ============================================================
# STARTUP GREETING
# ============================================================

async def send_startup_greeting(session):
    global startup_greeting_sent

    if startup_greeting_sent:
        return

    hour = datetime.now().hour

    if hour < 7:
        greeting = "Chào buổi sáng Lão sư!"
    else:
        greeting = "Chào Lão sư!"

    startup_greeting_sent = True

    await send_text_command(
        session,
        f"""
Hãy chủ động chào Lão sư bằng đúng câu này:
{greeting}
Chỉ nói câu chào. Không hỏi thêm câu nào.
""",
        3,
    )


# ============================================================
# LESSON FLOW BRIDGE
# ============================================================

async def start_voice_lesson(student, subject=None):
    global lesson_session
    global lesson_waiting_for_answer

    subject_id = choose_subject(subject)

    lesson = start_lesson(
        student_id=student["student_id"],
        subject_id=subject_id,
        nickname=CANONICAL_STUDENT_NAMES.get(
            student["student_id"],
            student["official_name"],
        ),
    )

    lesson_session = lesson["session"]
    lesson_waiting_for_answer = bool(
        lesson.get("waiting_for_answer")
    )

    question = lesson.get("question")
    speech = build_question_speech(
        lesson_session,
        question,
    )

    return speech


async def process_lesson_answer(session, text):
    global lesson_waiting_for_answer

    if not lesson_session or not lesson_waiting_for_answer:
        return False

    try:
        result = answer_current_question(
            lesson_session,
            text,
        )

        feedback = build_answer_speech(
            lesson_session,
            result["result"],
        )

        next_question = next_lesson_question(
            lesson_session,
        )

        lesson_waiting_for_answer = True

        next_speech = build_question_speech(
            lesson_session,
            next_question,
        )

        await send_text_command(
            session,
            f"""
Đây là kết quả từ lesson flow:
{feedback}

Sau đó hỏi ngay câu tiếp theo:
{next_speech}

Chỉ nói feedback ngắn và câu hỏi tiếp theo. Dừng.
""",
            3,
        )

        return True

    except Exception as e:
        print(
            "⚠️ Lesson flow lỗi:",
            repr(e),
            flush=True,
        )
        return False


# ============================================================
# START TUTOR
# ============================================================

async def start_tutor_session(session, student, subject=None, switching=False):
    global tutor_mode
    global current_student
    global current_student_id
    global current_subject
    global current_grade
    global lesson_session
    global lesson_waiting_for_answer

    if not student:
        return

    student_id = student["student_id"]
    called_name = CANONICAL_STUDENT_NAMES.get(
        student_id,
        student["official_name"]
    )
    grade = student["grade"]
    selected_subject = choose_subject(subject)

    tutor_mode = True
    current_student = called_name
    current_student_id = student_id
    current_subject = selected_subject
    current_grade = grade
    lesson_session = None
    lesson_waiting_for_answer = False

    print()
    print("🎓 BẮT ĐẦU HỌC", flush=True)
    print("👤", current_student, flush=True)
    print("📚", SUBJECT_NAMES.get(selected_subject, selected_subject), flush=True)

    # Dùng lesson flow hiện có để tạo câu hỏi đầu tiên.
    try:
        question_speech = await start_voice_lesson(
            student,
            selected_subject,
        )

        await send_text_command(
            session,
            f"""
TUTOR MODE.

Python đã xác định học sinh: {current_student}
Lớp: {grade}
Môn hiện tại: {SUBJECT_NAMES.get(selected_subject, selected_subject)}

Lesson flow đã tạo câu hỏi đầu tiên:
{question_speech}

Hãy nói lời chào rất ngắn với {current_student}, sau đó đọc đúng câu hỏi trên.
Không tự đổi học sinh.
Không tự đổi môn.
Không thêm câu hỏi khác.
Dừng sau câu hỏi.
""",
            4,
        )
        return

    except Exception as e:
        print(
            "⚠️ Không khởi động được lesson flow:",
            repr(e),
            flush=True,
        )

    # Fallback tối thiểu: giữ hành vi Tutor cũ nếu lesson flow gặp lỗi.
    prompt = f"""
TUTOR MODE.

Python đã xác định:
Học sinh: {current_student}
Lớp: {grade}
Môn: {SUBJECT_NAMES.get(selected_subject, selected_subject)}

{get_level_instruction(grade)}

QUY TẮC:
- Chỉ gọi học sinh là "{current_student}".
- Không dùng alias.
- Không gọi Lão sư.
- Không nói về hệ thống.
- Không tự đổi môn.
- Không tự đổi học sinh.
- Mỗi lần chỉ hỏi một câu.
- Hỏi xong dừng.

Chào {current_student} thật ngắn.
Đưa một câu hỏi.
Dừng.
"""
    await send_text_command(session, prompt, 4)


# ============================================================
# EXIT TUTOR
# ============================================================

async def exit_tutor_mode(session):
    global tutor_mode
    global current_student
    global current_student_id
    global current_subject
    global current_grade
    global lesson_session
    global lesson_waiting_for_answer

    tutor_mode = False
    current_student = None
    current_student_id = None
    current_subject = None
    current_grade = None
    lesson_session = None
    lesson_waiting_for_answer = False

    hour = datetime.now().hour

    if hour >= 21:
        command = """
CHAT MODE.
Người nói là Lão sư.
Phiên chat đang kết thúc.
Chỉ nói: Chúc Lão sư ngủ ngon!
Không nói thêm.
"""
    else:
        command = """
CHAT MODE.
Người nói là Lão sư.
Không tự học.
Không tạo bài.
Chờ Lão sư nói.
"""

    await send_text_command(
        session,
        command,
        3,
    )


# ============================================================
# TOOLS
# ============================================================

def current_time():
    return get_time_text()


def calculator(expression):
    return calculate(expression)


def current_calendar():
    return get_calendar_text()


# ============================================================
# PROCESS USER TEXT
# ============================================================

async def process_user_text(session, text):
    global tutor_mode
    global current_student
    global current_student_id
    global current_subject
    global current_grade

    if not text:
        return

    text = text.strip()
    if not text:
        return

    loop = asyncio.get_running_loop()

    if loop.time() < command_suppressed_until:
        print("🔇 Bỏ qua tiếng của Tiểu Vũ:", text, flush=True)
        return

    print("\n👤 Người nói:", text, flush=True)

    # Tạm biệt/dừng phiên phải được xử lý trước answer của lesson flow.
    if detect_farewell(text):
        await exit_tutor_mode(session)
        return

    command = detect_tutor_command(text)
    intent = command["intent"]
    student = command["student"]
    subject = command["subject"]

    if mentions_teacher(text):
        await exit_tutor_mode(session)
        return

    if intent == "start_lesson":
        if tutor_mode and current_student_id == student["student_id"]:
            print("ℹ️ Đã đang học với học sinh này.", flush=True)
            return

        await start_tutor_session(
            session,
            student,
            subject,
            switching=tutor_mode,
        )
        return

    if intent == "switch_student":
        new_id = student["student_id"]

        if tutor_mode and current_student_id == new_id:
            if subject:
                current_subject = choose_subject(subject)
                await send_text_command(
                    session,
                    f"""
Tiếp tục với {current_student}.
Chuyển sang môn:
{SUBJECT_NAMES.get(current_subject, current_subject)}

Chỉ hỏi câu hỏi tiếp theo của lesson flow.
Sau đó dừng.
""",
                    3,
                )
            return

        await start_tutor_session(
            session,
            student,
            subject,
            switching=tutor_mode,
        )
        return

    if intent == "unknown_student":
        await send_text_command(
            session,
            """
Người nói muốn học.
Hỏi đúng một câu:
"Tiểu Vũ dạy Đậu Đậu hay Mini nè?"
""",
            3,
        )
        return

    # Nếu đang có câu hỏi lesson flow, câu nói này là câu trả lời của bé.
    if tutor_mode and lesson_session and lesson_waiting_for_answer:
        handled = await process_lesson_answer(
            session,
            text,
        )
        if handled:
            return

    if intent == "chat":
        if tutor_mode:
            print(f"🎓 Đang dạy {current_student}", flush=True)
        else:
            print("💬 CHAT MODE", flush=True)


# ============================================================
# TOOL CALL HANDLER
# ============================================================

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

        responses.append(
            types.FunctionResponse(
                id=call.id,
                name=name,
                response={"result": result},
            )
        )

    if responses:
        await session.send_tool_response(
            function_responses=responses
        )


# ============================================================
# MICROPHONE
# ============================================================

async def microphone_sender(session):
    loop = asyncio.get_running_loop()

    def callback(indata, frames, time_info, status):
        if status:
            print("MIC:", status, flush=True)

        future = asyncio.run_coroutine_threadsafe(
            session.send_realtime_input(
                audio=types.Blob(
                    data=indata.tobytes(),
                    mime_type="audio/pcm;rate=16000",
                )
            ),
            loop,
        )

        future.add_done_callback(lambda f: None)

    with sd.InputStream(
        device=MIC,
        samplerate=INPUT_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=BLOCKSIZE,
        callback=callback,
    ):
        while not shutdown_requested:
            await asyncio.sleep(0.1)


# ============================================================
# RECEIVE LOOP / SPEAKER
# ============================================================

def open_speaker():
    global speaker_stream

    if speaker_stream is not None:
        return speaker_stream

    speaker_stream = sd.RawOutputStream(
        samplerate=OUTPUT_RATE,
        channels=1,
        dtype="int16",
    )
    speaker_stream.start()
    return speaker_stream


def close_speaker():
    global speaker_stream

    if speaker_stream is None:
        return

    try:
        speaker_stream.stop()
    except Exception:
        pass

    try:
        speaker_stream.close()
    except Exception:
        pass

    speaker_stream = None


async def receive_loop(session, speaker):
    async for response in session.receive():
        tool = getattr(response, "tool_call", None)

        if tool:
            calls = getattr(tool, "function_calls", None)
            if calls:
                await handle_tool_call(session, calls)

        server = getattr(response, "server_content", None)
        if not server:
            continue

        input_text = getattr(
            getattr(server, "input_transcription", None),
            "text",
            None,
        )

        if input_text:
            await process_user_text(session, input_text)

        output = getattr(
            getattr(server, "output_transcription", None),
            "text",
            None,
        )

        if output:
            print("💗 Tiểu Vũ:", output, flush=True)

        model_turn = getattr(server, "model_turn", None)

        if model_turn:
            for part in model_turn.parts:
                data = getattr(
                    getattr(part, "inline_data", None),
                    "data",
                    None,
                )

                if data:
                    try:
                        speaker.write(data)
                    except Exception as e:
                        print("⚠️ Speaker lỗi:", repr(e), flush=True)


# ============================================================
# LIVE CONFIG
# ============================================================

def build_live_config():
    tools = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="current_time",
                description="Lấy giờ Việt Nam",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={}
                )
            ),
            types.FunctionDeclaration(
                name="calculator",
                description="Tính toán",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "expression": types.Schema(type="STRING")
                    },
                    required=["expression"]
                )
            ),
            types.FunctionDeclaration(
                name="current_calendar",
                description="Lấy lịch dương âm",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={}
                )
            ),
        ]
    )

    instruction = SYSTEM_INSTRUCTION + """
TIỂU VŨ LIVE VOICE.

CHAT MODE:
- Nói chuyện với Lão sư.
- Không tự học nếu Python chưa kích hoạt Tutor Mode.

TUTOR MODE:
- Python quyết định học sinh.
- Python/lesson flow quyết định câu hỏi.
- Không tự đổi tên.
- Không tự đổi môn.
- Không tự restart.
- Khi nhận câu hỏi từ Python, đọc đúng câu hỏi và dừng.
- Khi nhận feedback + câu hỏi tiếp theo từ Python, nói đúng nội dung đó và dừng.

Nếu Python gửi:
Đậu Đậu

chỉ gọi:
Đậu Đậu

HSK 3.0 ưu tiên.

TOOLS:
Hỏi giờ: dùng current_time.
Tính: dùng calculator.
Ngày: dùng current_calendar.

Không đoán dữ liệu.
"""

    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            parts=[types.Part(text=instruction)]
        ),
        tools=[tools],
        input_audio_transcription={},
        output_audio_transcription={},
    )


# ============================================================
# RUN
# ============================================================

async def run_one_connection():
    config = build_live_config()
    speaker = open_speaker()

    try:
        async with client.aio.live.connect(
            model=MODEL,
            config=config,
        ) as session:
            print("✅ Gemini Live connected", flush=True)

            await send_startup_greeting(session)

            await asyncio.gather(
                receive_loop(session, speaker),
                microphone_sender(session),
            )
    finally:
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
    global shutdown_requested
    shutdown_requested = True
    close_speaker()
    print("🧹 Tiểu Vũ đóng.", flush=True)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        asyncio.run(start_live_voice())
    except KeyboardInterrupt:
        cleanup()
