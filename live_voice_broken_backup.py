# ============================================================
# TIỂU VŨ - LIVE VOICE
# ============================================================
# CHAT MODE + TUTOR MODE
#
# FIX VERSION
#
# FIX:
# - Không xử lý input transcription từng mảnh
# - Gom transcript rồi mới xử lý
# - Greeting chỉ 1 lần khi khởi động
# - Reconnect không greeting lại
# - GOAWAY xử lý an toàn
# - Session Resumption chỉ lưu handle mới nhất
# - Không spam handle ra console
# - Không tự tạo conversation sau reconnect
# - Microphone tiếp tục nghe sau reconnect
# - Giữ Chat Mode / Tutor Mode
# - Giữ 3 tools:
#       current_time
#       calculator
#       current_calendar
# - HSK 3.0 ưu tiên
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


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        api_version="v1beta"
    ),
)


# ============================================================
# GLOBAL STATE
# ============================================================

tutor_mode = False

current_student = None
current_student_id = None
current_subject = None
current_grade = None

question_count = 0

rotation_index = 0
last_subject = None

# Session Resumption:
# Chỉ giữ handle mới nhất.
session_resumption_handle = None

# GOAWAY:
# True khi server yêu cầu connection chuẩn bị đóng.
goaway_received = False

# Shutdown:
shutdown_requested = False

# Greeting:
startup_greeting_sent = False

# Transcript:
#
# Gemini Live có thể gửi transcription thành nhiều mảnh.
# Không xử lý từng mảnh.
#
# Ví dụ:
# "Chào"
# " Lão"
# " sư"
#
# sẽ được gom thành:
# "Chào Lão sư"
#
input_transcript_buffer = ""

# Đánh dấu đang có generation của model.
model_is_speaking = False


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
            "Minh Tiên",
            "Minh Tien",
            "Đậu Đậu",
            "Dau Dau",
            "Đậu Phộng",
            "Dau Phong",
            "Đậu Phụng",
            "Dau Phung",
        ],
    },

    "nha_tien": {
        "student_id": "nha_tien",
        "official_name": "Nhã Tiên",
        "gender": "female",
        "grade": 6,
        "aliases": [
            "Nhã Tiên",
            "Nha Tien",
            "Mini",
            "Meanie",
            "미니",
        ],
    },
}


# ============================================================
# ALIAS DATABASE
# ============================================================

STUDENT_ALIASES = {}

for student_id, student in STUDENTS.items():

    for alias in student["aliases"]:

        key = alias.strip().lower()

        STUDENT_ALIASES[key] = {
            "student_id": student_id,
            "official_name": student["official_name"],
            "called_name": alias.strip(),
            "gender": student["gender"],
            "grade": student["grade"],
        }


# ============================================================
# AUDIO OUTPUT
# ============================================================

audio_stream = None


def start_audio():

    global audio_stream

    if audio_stream is None:

        audio_stream = sd.RawOutputStream(
            samplerate=OUTPUT_RATE,
            channels=1,
            dtype="int16",
        )

        audio_stream.start()


def play_audio(data):

    if not data:
        return

    try:

        start_audio()

        audio_stream.write(data)

    except Exception as e:

        print(
            f"\n⚠️ Audio output lỗi: {e}",
            flush=True,
        )


def stop_audio():

    global audio_stream

    if audio_stream is not None:

        try:
            audio_stream.stop()
        except Exception:
            pass

        try:
            audio_stream.close()
        except Exception:
            pass

        audio_stream = None


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if not isinstance(text, str):
        return ""

    text = text.strip().lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def remove_accents(text):

    if not isinstance(text, str):
        return ""

    normalized = unicodedata.normalize(
        "NFD",
        text,
    )

    result = "".join(
        char
        for char in normalized
        if unicodedata.category(char) != "Mn"
    )

    result = result.replace("đ", "d")
    result = result.replace("Đ", "D")

    return result.lower().strip()


# ============================================================
# ALIAS MATCH
# ============================================================

def alias_matches(alias, normalized, no_accent):

    alias_normalized = normalize_text(alias)

    alias_no_accent = remove_accents(
        alias_normalized
    )

    if alias_normalized in normalized:
        return True

    if alias_no_accent in no_accent:
        return True

    return False


# ============================================================
# DETECT STUDENT
# ============================================================

def detect_student(text):

    normalized = normalize_text(text)

    no_accent = remove_accents(
        normalized
    )

    aliases = sorted(
        STUDENT_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for alias, student in aliases:

        if alias_matches(
            alias,
            normalized,
            no_accent,
        ):
            return student

    return None


# ============================================================
# DETECT SUBJECT
# ============================================================

def detect_subject(text):

    normalized = normalize_text(text)

    no_accent = remove_accents(
        normalized
    )

    subject_patterns = {

        "chinese": [
            "tiếng trung",
            "tieng trung",
            "tiếng hoa",
            "tieng hoa",
            "trung văn",
            "trung van",
            "chinese",
            "hsk",
            "hsk 3",
            "hsk 3.0",
        ],

        "math": [
            "toán",
            "toan",
            "math",
            "phép cộng",
            "phep cong",
            "phép trừ",
            "phep tru",
            "phép nhân",
            "phep nhan",
            "phép chia",
            "phep chia",
            "nhân",
            "nhan",
            "chia",
            "cửu chương",
            "cuu chuong",
            "bảng nhân",
            "bang nhan",
            "bảng chia",
            "bang chia",
        ],

        "vietnamese": [
            "tiếng việt",
            "tieng viet",
            "ngữ văn",
            "ngu van",
        ],

        "english": [
            "tiếng anh",
            "tieng anh",
            "english",
        ],

        "history": [
            "lịch sử",
            "lich su",
            "history",
        ],

        "geography": [
            "địa lý",
            "dia ly",
            "geography",
        ],

        "communication": [
            "giao tiếp",
            "giao tiep",
            "kỹ năng giao tiếp",
            "ky nang giao tiep",
            "communication",
        ],

        "problem_solving": [
            "xử lý vấn đề",
            "xu ly van de",
            "giải quyết vấn đề",
            "giai quyet van de",
            "problem solving",
        ],

        "emotional_intelligence": [
            "cảm xúc",
            "cam xuc",
            "quản lý cảm xúc",
            "quan ly cam xuc",
            "eq",
            "trí tuệ cảm xúc",
            "tri tue cam xuc",
        ],
    }

    for subject, words in subject_patterns.items():

        for word in words:

            if (
                word in normalized
                or remove_accents(word) in no_accent
            ):
                return subject

    return None


# ============================================================
# LEARNING INTENT
# ============================================================

def detect_learning_intent(text):

    normalized = normalize_text(text)

    no_accent = remove_accents(
        normalized
    )

    patterns = [

        "muốn học",
        "muon hoc",

        "bắt đầu học",
        "bat dau hoc",

        "bắt đầu bài học",
        "bat dau bai hoc",

        "học đi",
        "hoc di",

        "học nha",
        "hoc nha",

        "học nhé",
        "hoc nhe",

        "học thôi",
        "hoc thoi",

        "vào học",
        "vao hoc",

        "vô học",
        "vo hoc",

        "cho con học",
        "cho con hoc",

        "học bài",
        "hoc bai",

        "giờ học",
        "gio hoc",

        "đến giờ học",
        "den gio hoc",

        "tới giờ học",
        "toi gio hoc",
    ]

    for pattern in patterns:

        if pattern in normalized:
            return True

        if remove_accents(pattern) in no_accent:
            return True

    return False


# ============================================================
# DETECT TEACHER
# ============================================================

def mentions_teacher(text):

    normalized = normalize_text(text)

    no_accent = remove_accents(
        normalized
    )

    patterns = [
        "lão sư",
        "lao su",
    ]

    for pattern in patterns:

        if (
            pattern in normalized
            or remove_accents(pattern) in no_accent
        ):
            return True

    return False


# ============================================================
# SUBJECT ROTATION
# ============================================================

SUBJECT_ROTATION = [

    "chinese",
    "math",
    "vietnamese",
    "english",
    "history",
    "geography",
    "communication",
    "problem_solving",
    "emotional_intelligence",

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


def get_next_subject():

    global rotation_index
    global last_subject

    if last_subject is None:

        last_subject = "chinese"
        rotation_index = 0

        return "chinese"

    rotation_index += 1

    if rotation_index >= len(SUBJECT_ROTATION):
        rotation_index = 0

    subject = SUBJECT_ROTATION[
        rotation_index
    ]

    last_subject = subject

    return subject


# ============================================================
# MATH
# ============================================================

def math_instruction(grade):

    if grade == 4:

        return """
TOÁN LỚP 4:

Thường xuyên xen kẽ:

- phép nhân
- phép chia
- chia có dư
- nhân số có nhiều chữ số
- bài toán có lời văn
- phân số cơ bản
- đơn vị đo
- chu vi
- diện tích
- suy luận

Ưu tiên luyện nhân/chia nhưng không hỏi máy móc.

Thay đổi dạng bài:
- tìm số còn thiếu
- bài toán ngược
- tính nhẩm
- chia có dư
- bài toán thực tế
- suy luận
"""

    return """
TOÁN LỚP 6:

Phù hợp lớp 6.

Ưu tiên:
- số nguyên
- phân số
- tỉ số
- biểu thức
- đại lượng
- hình học
- bài toán nhiều bước
- logic

Đồng thời thường xuyên xen kẽ:
- bảng nhân
- bảng chia
- phản xạ nhân/chia

Không hạ toàn bộ bài học xuống lớp 4.
"""


# ============================================================
# LEVEL
# ============================================================

def get_level_instruction(grade):

    if grade == 4:

        return f"""
HỌC SINH LỚP 4.

Không ra bài quá dễ.

{math_instruction(4)}

TIẾNG TRUNG:

- Ưu tiên HSK 3.0
- Từ vựng phù hợp
- Nghe hiểu
- Phản xạ
- Hội thoại
- Đặt câu
- Đọc hiểu ngắn
"""

    return f"""
HỌC SINH LỚP 6.

Không được hạ kiến thức xuống lớp 4.

{math_instruction(6)}

TIẾNG TRUNG:

- Ưu tiên HSK 3.0
- Tăng vốn từ
- Nghe hiểu
- Phản xạ
- Hội thoại
- Đặt câu
- Đọc hiểu
- Tình huống thực tế
"""


# ============================================================
# COMMAND DETECTION
# ============================================================

def detect_tutor_command(text):

    student = detect_student(text)
    subject = detect_subject(text)
    learning = detect_learning_intent(text)

    if mentions_teacher(text):

        return {
            "intent": "chat",
            "student": None,
            "subject": None,
            "text": text,
        }

    if student is not None and learning:

        return {
            "intent": "start_lesson",
            "student": student,
            "subject": subject,
            "text": text,
        }

    if student is not None:

        return {
            "intent": "switch_student",
            "student": student,
            "subject": subject,
            "text": text,
        }

    if learning:

        return {
            "intent": "unknown_student",
            "student": None,
            "subject": subject,
            "text": text,
        }

    return {
        "intent": "chat",
        "student": None,
        "subject": None,
        "text": text,
    }


# ============================================================
# GREETING
# ============================================================

def get_startup_greeting():

    hour = datetime.now().hour

    if 4 <= hour < 11:

        return random.choice([
            "Chào buổi sáng Lão sư! Tiểu Vũ tới rồi ạ!",
            "Chào buổi sáng Lão sư! Hôm nay mình bắt đầu nhẹ nhàng nhé!",
            "Buổi sáng vui vẻ nha Lão sư! Tiểu Vũ sẵn sàng rồi ạ!",
        ])

    if 11 <= hour < 18:

        return random.choice([
            "Chào Lão sư! Tiểu Vũ đây ạ!",
            "Lão sư tới rồi nè! Tiểu Vũ sẵn sàng ạ!",
            "Chào Lão sư! Hôm nay mình cùng làm vài điều thú vị nhé!",
        ])

    return random.choice([
        "Chào buổi tối Lão sư! Tiểu Vũ ở đây nè!",
        "Buổi tối vui vẻ Lão sư! Tiểu Vũ tới rồi ạ!",
        "Chào buổi tối Lão sư! Hôm nay mình nói chuyện một chút nhé!",
    ])


# ============================================================
# START TUTOR
# ============================================================

async def start_tutor_session(
    session,
    student,
    subject=None,
    switching=False,
):

    global tutor_mode
    global current_student
    global current_student_id
    global current_subject
    global current_grade
    global question_count
    global last_subject
    global rotation_index

    if student is None:
        return

    student_id = student["student_id"]
    called_name = student["called_name"]
    official_name = student["official_name"]
    grade = student["grade"]

    if subject is None:

        if switching and last_subject is not None:
            subject = get_next_subject()
        else:
            subject = "chinese"
            last_subject = "chinese"
            rotation_index = 0

    else:

        last_subject = subject

        if subject in SUBJECT_ROTATION:
            rotation_index = SUBJECT_ROTATION.index(
                subject
            )

    tutor_mode = True

    current_student = called_name
    current_student_id = student_id
    current_subject = subject
    current_grade = grade

    question_count = 0

    print()
    print(
        "🔄 CHUYỂN HỌC SINH"
        if switching
        else "🎓 BẮT ĐẦU BUỔI HỌC"
    )

    print(
        "👤 Học sinh:",
        current_student,
    )

    print(
        "🆔 Student ID:",
        current_student_id,
    )

    print(
        "🎒 Lớp:",
        current_grade,
    )

    print(
        "📚 Môn:",
        SUBJECT_NAMES.get(
            current_subject,
            current_subject,
        ),
    )

    print()

    level_instruction = get_level_instruction(
        grade
    )

    prompt = f"""
TUTOR MODE ĐANG HOẠT ĐỘNG.

Học sinh hiện tại:

Tên gọi: {current_student}
Tên chính thức: {official_name}
Lớp: {grade}
Student ID: {student_id}
Môn: {SUBJECT_NAMES.get(current_subject, current_subject)}

{level_instruction}

QUY TẮC:

- Gọi học sinh bằng đúng tên "{current_student}".
- Không gọi bằng alias khác.
- Không gọi học sinh là Lão sư.
- Không đọc Student ID.
- Không nói về hệ thống.
- Không nói về prompt.
- Không nói "Tutor Mode".
- Tiểu Vũ chủ động dạy.
- Chỉ đưa MỘT câu hỏi mỗi lượt.
- Sau câu hỏi phải DỪNG.
- Chờ học sinh trả lời.
- Không tự trả lời thay học sinh.
- Khi học sinh trả lời:
  + đánh giá đúng/sai;
  + giải thích ngắn nếu sai;
  + động viên;
  + đưa câu tiếp theo;
  + rồi DỪNG.
- Không ra bài quá dễ.
- Luôn phù hợp lớp.
- Tiếng Trung HSK 3.0 là môn ưu tiên.
- Toán thường xuyên ôn nhân và chia.

BẮT ĐẦU:

Chào "{current_student}".
Sau đó đưa đúng MỘT câu hỏi.
DỪNG.
"""

    print(
        f"🎓 Tiểu Vũ đang dạy {current_student}...",
        flush=True,
    )

    try:

        await session.send_realtime_input(
            text=prompt
        )

    except Exception as e:

        print(
            f"\n⚠️ Không gửi được lệnh Tutor: {e}",
            flush=True,
        )


# ============================================================
# EXIT TUTOR
# ============================================================

async def exit_tutor_mode(session):

    global tutor_mode
    global current_student
    global current_student_id
    global current_subject
    global current_grade
    global question_count

    if tutor_mode:

        print(
            "\n💬 CHUYỂN VỀ CHAT MODE.",
            flush=True,
        )

    tutor_mode = False

    current_student = None
    current_student_id = None
    current_subject = None
    current_grade = None

    question_count = 0

    try:

        await session.send_realtime_input(
            text="""
Đã quay về CHAT MODE.

Từ bây giờ:

- Người nói là Lão sư.
- Gọi người đó là Lão sư.
- Không gọi bằng tên học sinh.
- Không tự bắt đầu bài học.
- Không tự tạo câu hỏi học tập.
- Chờ Lão sư nói rồi mới phản hồi.
"""
        )

    except Exception as e:

        print(
            f"\n⚠️ Không thể chuyển Chat Mode: {e}",
            flush=True,
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


async def handle_tool_call(
    session,
    tool_call,
):

    function_responses = []

    for function_call in tool_call:

        name = function_call.name
        args = function_call.args or {}

        print(
            f"\n🛠️ Tiểu Vũ dùng tool: {name}",
            flush=True,
        )

        if name == "current_time":

            result = current_time()

        elif name == "calculator":

            result = calculator(
                args.get(
                    "expression",
                    "",
                )
            )

        elif name == "current_calendar":

            result = current_calendar()

        else:

            result = "Không tìm thấy công cụ này."

        function_responses.append(
            types.FunctionResponse(
                id=function_call.id,
                name=name,
                response={
                    "result": result
                },
            )
        )

    if function_responses:

        try:

            await session.send_tool_response(
                function_responses=function_responses
            )

        except Exception as e:

            print(
                f"\n⚠️ Không gửi được tool response: {e}",
                flush=True,
            )


# ============================================================
# PROCESS COMPLETE USER TEXT
# ============================================================

async def process_user_text(
    session,
    text,
):

    global tutor_mode
    global current_student
    global current_student_id
    global current_subject
    global current_grade
    global last_subject
    global rotation_index

    text = text.strip()

    if not text:
        return

    print(
        f"\n👤 Người nói: {text}",
        flush=True,
    )

    command = detect_tutor_command(text)

    intent = command["intent"]
    student = command["student"]
    subject = command["subject"]

    # --------------------------------------------------------
    # LÃO SƯ
    # --------------------------------------------------------

    if mentions_teacher(text):

        await exit_tutor_mode(
            session
        )

        return

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if intent == "start_lesson":

        print(
            f"🎓 Phát hiện học sinh: "
            f"{student['called_name']}",
            flush=True,
        )

        await start_tutor_session(
            session,
            student,
            subject,
            switching=tutor_mode,
        )

        return

    # --------------------------------------------------------
    # SWITCH
    # --------------------------------------------------------

    if intent == "switch_student":

        new_student_id = student["student_id"]

        if (
            tutor_mode
            and new_student_id == current_student_id
        ):

            print(
                f"🎓 Vẫn là học sinh hiện tại: "
                f"{student['called_name']}",
                flush=True,
            )

            if subject:

                current_subject = subject
                last_subject = subject

                if subject in SUBJECT_ROTATION:

                    rotation_index = (
                        SUBJECT_ROTATION.index(
                            subject
                        )
                    )

                await session.send_realtime_input(
                    text=f"""
Tiếp tục với {current_student}.

Chuyển sang môn:
{SUBJECT_NAMES.get(subject, subject)}

Phù hợp lớp {current_grade}.

Chỉ đưa MỘT câu hỏi rồi DỪNG.
"""
                )

            else:

                next_subject = get_next_subject()

                current_subject = next_subject

                await session.send_realtime_input(
                    text=f"""
Tiếp tục với {current_student}.

Chuyển sang môn:
{SUBJECT_NAMES.get(next_subject, next_subject)}

Phù hợp lớp {current_grade}.

Nếu là Toán, thường xuyên xen kẽ nhân/chia.

Chỉ đưa MỘT câu hỏi rồi DỪNG.
"""
                )

            return

        print(
            f"🔄 Đổi học sinh: "
            f"{current_student or 'chưa có'}"
            f" → "
            f"{student['called_name']}",
            flush=True,
        )

        await start_tutor_session(
            session,
            student,
            subject,
            switching=True,
        )

        return

    # --------------------------------------------------------
    # UNKNOWN STUDENT
    # --------------------------------------------------------

    if intent == "unknown_student":

        print(
            "⚠️ Chưa xác định được học sinh.",
            flush=True,
        )

        await session.send_realtime_input(
            text="""
Người nói muốn bắt đầu học nhưng chưa nói tên học sinh.

Hãy hỏi thật ngắn:

"Tiểu Vũ dạy Mini hay Minh Tiên nè?"

Chỉ hỏi một câu.
Không tự chọn học sinh.
"""
        )

        return

    # --------------------------------------------------------
    # NORMAL CHAT
    # --------------------------------------------------------

    if tutor_mode:

        print(
            f"🎓 Tutor Mode: {current_student}",
            flush=True,
        )

    else:

        print(
            "💬 Chat Mode",
            flush=True,
        )


# ============================================================
# MICROPHONE
# ============================================================

async def microphone_sender(session):

    loop = asyncio.get_running_loop()

    print(
        "🎤 Microphone đang hoạt động...",
        flush=True,
    )

    def callback(
        indata,
        frames,
        time_info,
        status,
    ):

        if status:

            print(
                f"\n🎤 MIC: {status}",
                flush=True,
            )

        if shutdown_requested:
            return

        audio_bytes = indata.tobytes()

        try:

            future = asyncio.run_coroutine_threadsafe(

                session.send_realtime_input(

                    audio=types.Blob(
                        data=audio_bytes,
                        mime_type="audio/pcm;rate=16000",
                    )

                ),

                loop,
            )

            # Không block callback để chờ Gemini.
            # Chỉ gửi audio rồi tiếp tục nghe.

            future.add_done_callback(
                lambda f: None
            )

        except Exception:

            pass

    try:

        with sd.InputStream(

            device=MIC,

            samplerate=INPUT_RATE,

            channels=CHANNELS,

            dtype="int16",

            blocksize=BLOCKSIZE,

            callback=callback,

        ):

            while not shutdown_requested:

                await asyncio.sleep(
                    0.1
                )

    except asyncio.CancelledError:

        raise

    except Exception as e:

        print(
            f"\n⚠️ Microphone lỗi: {e}",
            flush=True,
        )


# ============================================================
# RECEIVE LOOP
# ============================================================

async def receive_loop(session):

    global session_resumption_handle
    global goaway_received
    global input_transcript_buffer
    global model_is_speaking

    input_transcript_buffer = ""
    model_is_speaking = False

    try:

        async for response in session.receive():

            # =================================================
            # GOAWAY
            # =================================================

            goaway = getattr(
                response,
                "go_away",
                None,
            )

            if goaway is not None:

                if not goaway_received:

                    goaway_received = True

                    time_left = getattr(
                        goaway,
                        "time_left",
                        None,
                    )

                    print(
                        "\n⚠️ Gemini Live gửi GOAWAY.",
                        flush=True,
                    )

                    if time_left is not None:

                        print(
                            f"⏳ Server báo connection sắp đóng: "
                            f"{time_left}",
                            flush=True,
                        )

                    print(
                        "🔄 Sẽ reconnect an toàn...",
                        flush=True,
                    )

                return True

            # =================================================
            # SESSION RESUMPTION
            # =================================================

            update = getattr(
                response,
                "session_resumption_update",
                None,
            )

            if update is not None:

                new_handle = getattr(
                    update,
                    "new_handle",
                    None,
                )

                resumable = getattr(
                    update,
                    "resumable",
                    False,
                )

                if (
                    resumable
                    and new_handle
                    and new_handle != session_resumption_handle
                ):

                    session_resumption_handle = new_handle

                    # KHÔNG spam console.
                    #
                    # Chỉ báo lần đầu trong connection
                    # hoặc khi cần debug.
                    #
                    # Handle vẫn được lưu đầy đủ.

            # =================================================
            # TOOL CALL
            # =================================================

            tool_call = getattr(
                response,
                "tool_call",
                None,
            )

            if tool_call:

                function_calls = getattr(
                    tool_call,
                    "function_calls",
                    [],
                )

                if function_calls:

                    await handle_tool_call(
                        session,
                        function_calls,
                    )

            # =================================================
            # SERVER CONTENT
            # =================================================

            server_content = getattr(
                response,
                "server_content",
                None,
            )

            if server_content is None:

                continue

            # =================================================
            # INPUT TRANSCRIPTION
            #
            # CHỈ GOM.
            # KHÔNG XỬ LÝ NGAY.
            # =================================================

            input_transcription = getattr(
                server_content,
                "input_transcription",
                None,
            )

            if input_transcription:

                text = getattr(
                    input_transcription,
                    "text",
                    None,
                )

                if text:

                    input_transcript_buffer += text

            # =================================================
            # OUTPUT TRANSCRIPTION
            # =================================================

            output_transcription = getattr(
                server_content,
                "output_transcription",
                None,
            )

            if output_transcription:

                text = getattr(
                    output_transcription,
                    "text",
                    None,
                )

                if text:

                    model_is_speaking = True

                    print(
                        "💗 Tiểu Vũ:",
                        text,
                        flush=True,
                    )

            # =================================================
            # MODEL AUDIO
            # =================================================

            model_turn = getattr(
                server_content,
                "model_turn",
                None,
            )

            if model_turn:

                model_is_speaking = True

                parts = getattr(
                    model_turn,
                    "parts",
                    [],
                )

                for part in parts:

                    inline_data = getattr(
                        part,
                        "inline_data",
                        None,
                    )

                    if inline_data:

                        data = getattr(
                            inline_data,
                            "data",
                            None,
                        )

                        if data:

                            play_audio(data)

            # =================================================
            # TURN COMPLETE
            # =================================================

            turn_complete = getattr(
                server_content,
                "turn_complete",
                False,
            )

            if turn_complete:

                model_is_speaking = False

                stop_audio()

                # ---------------------------------------------
                # INPUT TRANSCRIPT HOÀN TẤT
                # ---------------------------------------------

                final_text = (
                    input_transcript_buffer
                    .strip()
                )

                input_transcript_buffer = ""

                if final_text:

                    await process_user_text(
                        session,
                        final_text,
                    )

                print(
                    "\n🎤 Tiểu Vũ đang nghe...",
                    flush=True,
                )

    except asyncio.CancelledError:

        raise

    except Exception as e:

        print(
            f"\n⚠️ Receive loop kết thúc: {repr(e)}",
            flush=True,
        )

        return True

    return False


# ============================================================
# STARTUP GREETING
# ============================================================

async def startup_greeting(session):

    global startup_greeting_sent

    if startup_greeting_sent:

        return

    greeting = get_startup_greeting()

    print(
        f"💗 Tiểu Vũ chủ động: {greeting}",
        flush=True,
    )

    try:

        await session.send_realtime_input(

            text=(
                "Hãy nói chính xác câu sau "
                "với Lão sư bằng giọng tự nhiên, "
                "thân mật và vui vẻ. "
                "Không thêm lời giải thích: "
                + greeting
            )

        )

        startup_greeting_sent = True

    except Exception as e:

        print(
            f"\n⚠️ Không gửi được lời chào: {e}",
            flush=True,
        )


# ============================================================
# BUILD LIVE CONFIG
# ============================================================

def build_live_config():

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    time_tool = types.FunctionDeclaration(

        name="current_time",

        description=(
            "Lấy giờ hiện tại chính xác "
            "theo múi giờ Việt Nam UTC+7."
        ),

        parameters=types.Schema(
            type="OBJECT",
            properties={},
        ),
    )

    # --------------------------------------------------------
    # CALCULATOR
    # --------------------------------------------------------

    calculator_tool = types.FunctionDeclaration(

        name="calculator",

        description=(
            "Tính toán biểu thức toán học chính xác."
        ),

        parameters=types.Schema(

            type="OBJECT",

            properties={

                "expression": types.Schema(

                    type="STRING",

                    description=(
                        "Biểu thức toán học cần tính."
                    ),
                ),
            },

            required=[
                "expression"
            ],
        ),
    )

    # --------------------------------------------------------
    # CALENDAR
    # --------------------------------------------------------

    calendar_tool = types.FunctionDeclaration(

        name="current_calendar",

        description=(
            "Lấy thứ, ngày dương lịch, "
            "ngày âm lịch và giờ Việt Nam."
        ),

        parameters=types.Schema(
            type="OBJECT",
            properties={},
        ),
    )

    tools = types.Tool(

        function_declarations=[
            time_tool,
            calculator_tool,
            calendar_tool,
        ]

    )

    # ========================================================
    # SYSTEM INSTRUCTION
    # ========================================================

    full_instruction = SYSTEM_INSTRUCTION + """

============================================================
TIỂU VŨ - LIVE VOICE
============================================================

Có hai chế độ:

1. CHAT MODE
2. TUTOR MODE


============================================================
CHAT MODE
============================================================

Người lớn là:

"Lão sư"

Trong Chat Mode:

- gọi người lớn là Lão sư;
- nói chuyện tự nhiên;
- trả lời trực tiếp;
- không tự mở bài học;
- không tự tạo bài kiểm tra;
- không tự chào lại;
- sau khi đã chào lúc khởi động thì chờ Lão sư nói.


============================================================
HỌC SINH
============================================================

MINH TIÊN:

- Lớp 4
- Student ID: minh_tien

Alias:

- Minh Tiên
- Đậu Đậu
- Đậu Phộng
- Đậu Phụng


NHÃ TIÊN:

- Lớp 6
- Student ID: nha_tien

Alias:

- Nhã Tiên
- Mini
- Meanie
- 미니


============================================================
QUYỀN QUẢN LÝ HỌC SINH
============================================================

Python quyết định học sinh.

Không tự ý đổi học sinh.

Nếu Python xác định học sinh là Mini:
hãy gọi Mini.

Nếu Python xác định học sinh là Minh Tiên:
hãy gọi Minh Tiên.


============================================================
HSK 3.0
============================================================

Tiếng Trung là môn ưu tiên.

Ưu tiên:

- từ vựng;
- nghe;
- phản xạ;
- hội thoại;
- đặt câu;
- đọc hiểu;
- giao tiếp.


============================================================
TOÁN
============================================================

Lớp 4:

- nhân;
- chia;
- chia có dư;
- nhân nhiều chữ số;
- bài toán có lời văn;
- phân số cơ bản;
- hình học;
- đơn vị đo;
- chu vi;
- diện tích;
- logic.

Lớp 6:

- số nguyên;
- phân số;
- tỉ số;
- biểu thức;
- đại lượng;
- hình học;
- bài toán nhiều bước;
- logic.

Nhân và chia phải được ôn thường xuyên.


============================================================
TUTOR MODE
============================================================

Khi Tutor Mode:

1. Gọi đúng tên học sinh.
2. Nói ngắn.
3. Hỏi một câu.
4. Dừng.
5. Chờ học sinh.
6. Đánh giá câu trả lời.
7. Giải thích ngắn nếu sai.
8. Động viên.
9. Đưa câu tiếp theo.
10. Dừng.

Không tự trả lời thay học sinh.

Không hỏi nhiều câu cùng lúc.


============================================================
LÃO SƯ
============================================================

Nếu nghe "Lão sư":

- hiểu đó là người lớn;
- dừng bài học;
- quay Chat Mode;
- gọi người nói là Lão sư.


============================================================
TOOLS
============================================================

Nếu người dùng hỏi giờ:
BẮT BUỘC dùng current_time.

Nếu cần tính toán:
BẮT BUỘC dùng calculator.

Nếu hỏi ngày:
BẮT BUỘC dùng current_calendar.

Không đoán giờ.

Không đoán ngày.

Không đoán ngày âm.


============================================================
STARTUP
============================================================

Tiểu Vũ chỉ tự chào một lần khi chương trình bắt đầu.

Sau khi chào:

- chờ Lão sư;
- không tự chào lại;
- không tự bắt đầu hội thoại;
- không tự nói sau reconnect.

Reconnect không phải là một lần khởi động mới.


============================================================
LIVE CONVERSATION
============================================================

Nghe người nói.

Hiểu toàn bộ câu nói.

Trả lời tự nhiên.

Sau khi trả lời xong:

DỪNG.

Chờ người nói tiếp.

Không tự tạo vòng hội thoại.


============================================================
"""

    config_kwargs = {

        "response_modalities": [
            "AUDIO"
        ],

        "speech_config": types.SpeechConfig(

            voice_config=types.VoiceConfig(

                prebuilt_voice_config=(
                    types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )

            )

        ),

        "system_instruction": types.Content(

            parts=[
                types.Part(
                    text=full_instruction
                )
            ]

        ),

        "tools": [
            tools
        ],

        "input_audio_transcription": {},

        "output_audio_transcription": {},

        "context_window_compression": (
            types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow()
            )
        ),

    }

    # ========================================================
    # SESSION RESUMPTION
    # ========================================================

    if session_resumption_handle:

        config_kwargs["session_resumption"] = (

            types.SessionResumptionConfig(

                handle=session_resumption_handle

            )

        )

    else:

        config_kwargs["session_resumption"] = (

            types.SessionResumptionConfig()

        )

    return types.LiveConnectConfig(
        **config_kwargs
    )


# ============================================================
# ONE CONNECTION
# ============================================================

async def run_one_connection():

    global goaway_received

    goaway_received = False

    print(
        "\n🔌 Đang mở Gemini Live connection...",
        flush=True,
    )

    if session_resumption_handle:

        print(
            "♻️ Resume session bằng handle hiện tại...",
            flush=True,
        )

    else:

        print(
            "🆕 Tạo session mới...",
            flush=True,
        )

    config = build_live_config()

    async with client.aio.live.connect(

        model=MODEL,

        config=config,

    ) as session:

        print(
            "✅ Đã kết nối Gemini Live!",
            flush=True,
        )

        print()

        print(
            "🎤 Tiểu Vũ đang nghe...",
            flush=True,
        )

        print(
            "💡 Gọi tên bé + 'muốn học' để bắt đầu.",
            flush=True,
        )

        print(
            "💡 Gọi tên bé khác để chuyển học sinh.",
            flush=True,
        )

        print(
            "💡 Gọi 'Lão sư' để về Chat Mode.",
            flush=True,
        )

        print(
            "💡 HSK 3.0 được ưu tiên.",
            flush=True,
        )

        print(
            "💡 Toán thường xuyên ôn nhân và chia.",
            flush=True,
        )

        print(
            "💡 Các môn sẽ luân phiên.",
            flush=True,
        )

        print(
            "💡 3 tools: Giờ / Máy tính / Lịch.",
            flush=True,
        )

        print(
            "💡 Ctrl+C để thoát.",
            flush=True,
        )

        print()

        # ----------------------------------------------------
        # RECEIVE FIRST
        # ----------------------------------------------------

        receive_task = asyncio.create_task(
            receive_loop(session)
        )

        # ----------------------------------------------------
        # GREETING
        #
        # Chỉ chạy ở connection đầu tiên.
        # ----------------------------------------------------

        if not startup_greeting_sent:

            await startup_greeting(
                session
            )

        # ----------------------------------------------------
        # MICROPHONE
        # ----------------------------------------------------

        microphone_task = asyncio.create_task(
            microphone_sender(session)
        )

        try:

            done, pending = await asyncio.wait(

                [
                    receive_task,
                    microphone_task,
                ],

                return_when=asyncio.FIRST_COMPLETED,

            )

            reconnect_required = False

            if receive_task in done:

                try:

                    result = receive_task.result()

                    if result:

                        reconnect_required = True

                except Exception as e:

                    print(
                        f"\n⚠️ Receive task lỗi: "
                        f"{repr(e)}",
                        flush=True,
                    )

                    reconnect_required = True

            if microphone_task in done:

                try:

                    microphone_task.result()

                except Exception as e:

                    print(
                        f"\n⚠️ Microphone task lỗi: "
                        f"{repr(e)}",
                        flush=True,
                    )

                    reconnect_required = True

            for task in pending:

                task.cancel()

            if pending:

                await asyncio.gather(
                    *pending,
                    return_exceptions=True,
                )

            return reconnect_required

        finally:

            stop_audio()

            if not receive_task.done():
                receive_task.cancel()

            if not microphone_task.done():
                microphone_task.cancel()

            await asyncio.gather(
                receive_task,
                microphone_task,
                return_exceptions=True,
            )


# ============================================================
# RESET
# ============================================================

def reset_state():

    global tutor_mode
    global current_student
    global current_student_id
    global current_subject
    global current_grade
    global question_count
    global rotation_index
    global last_subject
    global input_transcript_buffer
    global model_is_speaking

    tutor_mode = False

    current_student = None
    current_student_id = None
    current_subject = None
    current_grade = None

    question_count = 0

    rotation_index = 0
    last_subject = None

    input_transcript_buffer = ""
    model_is_speaking = False


# ============================================================
# START LIVE VOICE
# ============================================================

async def start_live_voice():

    global shutdown_requested
    global session_resumption_handle
    global startup_greeting_sent

    reset_state()

    shutdown_requested = False

    # Mỗi lần python main.py là một phiên mới.
    session_resumption_handle = None

    # Greeting chỉ một lần trong lần chạy này.
    startup_greeting_sent = False

    print()

    print(
        "======================================"
    )

    print(
        "       TIỂU VŨ LIVE VOICE"
    )

    print(
        "       CHAT + TUTOR MODE"
    )

    print(
        "       HSK 3.0 + 3 TOOLS"
    )

    print(
        "       AUTO RECONNECT"
    )

    print(
        "       SESSION RESUMPTION"
    )

    print(
        "======================================"
    )

    print()

    print(
        "🔌 Đang chuẩn bị Gemini Live...",
        flush=True,
    )

    reconnect_delay = 1

    while not shutdown_requested:

        try:

            reconnect_required = (
                await run_one_connection()
            )

            if shutdown_requested:
                break

            if reconnect_required:

                print(
                    "\n⚠️ Gemini Live connection đã kết thúc.",
                    flush=True,
                )

                print(
                    f"🔄 Reconnect sau "
                    f"{reconnect_delay} giây...",
                    flush=True,
                )

                await asyncio.sleep(
                    reconnect_delay
                )

                reconnect_delay = min(
                    reconnect_delay * 2,
                    10,
                )

                continue

            # ------------------------------------------------
            # CONNECTION KẾT THÚC KHÔNG RÕ LÝ DO
            # ------------------------------------------------

            print(
                "\n⚠️ Gemini Live connection đã kết thúc.",
                flush=True,
            )

            print(
                f"🔄 Reconnect sau "
                f"{reconnect_delay} giây...",
                flush=True,
            )

            await asyncio.sleep(
                reconnect_delay
            )

            reconnect_delay = min(
                reconnect_delay * 2,
                10,
            )

        except asyncio.CancelledError:

            shutdown_requested = True
            break

        except KeyboardInterrupt:

            shutdown_requested = True
            break

        except Exception as e:

            print(
                f"\n❌ Tiểu Vũ gặp lỗi: {repr(e)}",
                flush=True,
            )

            if shutdown_requested:
                break

            print(
                f"🔄 Reconnect sau "
                f"{reconnect_delay} giây...",
                flush=True,
            )

            try:

                await asyncio.sleep(
                    reconnect_delay
                )

            except asyncio.CancelledError:

                shutdown_requested = True
                break

            reconnect_delay = min(
                reconnect_delay * 2,
                10,
            )

    stop_audio()


# ============================================================
# CLEANUP
# ============================================================

def cleanup():

    global shutdown_requested

    shutdown_requested = True

    stop_audio()

    print(
        "\n🧹 Tiểu Vũ đã đóng audio và dọn dẹp.",
        flush=True,
    )