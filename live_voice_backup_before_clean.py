# ============================================================
# TIỂU VŨ - LIVE VOICE
# ============================================================
#
# BẢN CLEAN - KHÔNG SESSION RESUMPTION
# KHÔNG GOAWAY HANDLING
#
# CHAT MODE + TUTOR MODE
# HSK 3.0 + TOÁN + TIẾNG VIỆT + TIẾNG ANH
# + LỊCH SỬ + ĐỊA LÝ + GIAO TIẾP + EQ
#
# 3 TOOLS:
#   1. current_time
#   2. calculator
#   3. current_calendar
#
# NGUYÊN TẮC LIVE:
#   - Tiểu Vũ chào đúng 1 lần khi khởi động.
#   - Sau khi chào -> chờ Lão sư nói.
#   - Không tự chào lại.
#   - Không tự nói sau reconnect.
#   - Không dùng Session Resumption.
#   - Không xử lý GOAWAY.
#   - turn_complete KHÔNG phải lỗi.
#   - Chỉ reconnect khi connection thực sự kết thúc/lỗi.
#
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
    )
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

shutdown_requested = False

# Chỉ chào một lần trong một lần chạy python main.py.
startup_greeting_sent = False

# Audio output.
audio_stream = None


# ============================================================
# STUDENTS
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

        STUDENT_ALIASES[
            alias.strip().lower()
        ] = {
            "student_id": student_id,
            "official_name": student["official_name"],
            "called_name": alias.strip(),
            "gender": student["gender"],
            "grade": student["grade"],
        }


# ============================================================
# TEXT HELPERS
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
# STUDENT DETECTION
# ============================================================

def alias_matches(alias, normalized, no_accent):

    alias_normalized = normalize_text(alias)

    alias_no_accent = remove_accents(
        alias_normalized
    )

    return (
        alias_normalized in normalized
        or alias_no_accent in no_accent
    )


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
# SUBJECT DETECTION
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
# TEACHER DETECTION
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

Ưu tiên thường xuyên:

- phép nhân;
- phép chia;
- chia có dư;
- nhân số nhiều chữ số;
- bài toán có lời văn;
- phân số cơ bản;
- đơn vị đo;
- chu vi;
- diện tích;
- suy luận.

Không chỉ hỏi phép tính đơn giản.
Hãy thay đổi dạng bài.
"""

    return """
TOÁN LỚP 6:

Phù hợp trình độ lớp 6.

Ưu tiên:

- số nguyên;
- phân số;
- tỉ số;
- biểu thức;
- đại lượng;
- hình học;
- bài toán nhiều bước;
- logic.

Đồng thời vẫn thường xuyên ôn nhân và chia.
"""


# ============================================================
# LEVEL
# ============================================================

def get_level_instruction(grade):

    if grade == 4:

        return f"""
HỌC SINH LỚP 4.

{math_instruction(4)}

TIẾNG TRUNG:

- ưu tiên HSK 3.0;
- từ vựng phù hợp;
- nghe hiểu;
- phản xạ;
- hội thoại;
- đặt câu;
- đọc hiểu ngắn.
"""

    return f"""
HỌC SINH LỚP 6.

{math_instruction(6)}

TIẾNG TRUNG:

- ưu tiên HSK 3.0;
- tăng vốn từ;
- nghe hiểu;
- phản xạ;
- hội thoại;
- đặt câu;
- đọc hiểu;
- tình huống thực tế.
"""


# ============================================================
# TUTOR COMMAND
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
# STARTUP GREETING
# ============================================================

def get_startup_greeting():

    hour = datetime.now().hour

    if 4 <= hour < 11:

        return random.choice([
            "Chào buổi sáng Lão sư! Tiểu Vũ tới rồi ạ!",
            "Chào buổi sáng Lão sư! Tiểu Vũ sẵn sàng rồi ạ!",
        ])

    if 11 <= hour < 18:

        return random.choice([
            "Chào Lão sư! Tiểu Vũ đây ạ!",
            "Lão sư tới rồi nè! Tiểu Vũ sẵn sàng ạ!",
        ])

    return random.choice([
        "Chào buổi tối Lão sư! Tiểu Vũ ở đây nè!",
        "Buổi tối vui vẻ Lão sư! Tiểu Vũ tới rồi ạ!",
    ])


# ============================================================
# AUDIO OUTPUT
# ============================================================

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
# TOOL 1
# ============================================================

def current_time():

    return get_time_text()


# ============================================================
# TOOL 2
# ============================================================

def calculator(expression):

    return calculate(expression)


# ============================================================
# TOOL 3
# ============================================================

def current_calendar():

    return get_calendar_text()


# ============================================================
# TOOL HANDLER
# ============================================================

async def handle_tool_call(
    session,
    function_calls,
):

    if not function_calls:
        return

    function_responses = []

    for function_call in function_calls:

        name = function_call.name

        args = function_call.args or {}

        print(
            f"\n🛠️ Tiểu Vũ dùng tool: {name}",
            flush=True,
        )

        try:

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

                result = (
                    "Không tìm thấy công cụ này."
                )

        except Exception as e:

            result = f"Lỗi tool: {e}"

        function_responses.append(
            types.FunctionResponse(
                id=function_call.id,
                name=name,
                response={
                    "result": result
                },
            )
        )

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
# TUTOR SESSION
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

    called_name = student["called_name"]

    official_name = student["official_name"]

    student_id = student["student_id"]

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

            rotation_index = (
                SUBJECT_ROTATION.index(subject)
            )

    tutor_mode = True

    current_student = called_name
    current_student_id = student_id
    current_subject = subject
    current_grade = grade

    question_count = 0

    print()

    if switching:
        print("🔄 CHUYỂN HỌC SINH")
    else:
        print("🎓 BẮT ĐẦU BUỔI HỌC")

    print(
        f"👤 Học sinh: {current_student}"
    )

    print(
        f"🎒 Lớp: {current_grade}"
    )

    print(
        f"📚 Môn: "
        f"{SUBJECT_NAMES.get(current_subject, current_subject)}"
    )

    level_instruction = get_level_instruction(
        grade
    )

    if switching:

        intro = f"""
Học sinh vừa chuyển sang là "{current_student}".
Tiếp tục buổi học với học sinh này.
"""

    else:

        intro = f"""
Hãy bắt đầu buổi học với "{current_student}".
"""

    prompt = f"""
TUTOR MODE.

Học sinh:

Tên gọi: {current_student}
Tên chính thức: {official_name}
Lớp: {grade}
Môn: {SUBJECT_NAMES.get(current_subject, current_subject)}

{level_instruction}

{intro}

QUY TẮC:

- Gọi đúng tên học sinh.
- Không gọi học sinh là Lão sư.
- Không nói Student ID.
- Không nói về hệ thống.
- Không nói về prompt.
- Không hỏi người lớn.
- Chủ động nhưng tự nhiên.
- Chỉ đưa MỘT câu hỏi mỗi lượt.
- Sau câu hỏi phải DỪNG.
- Chờ học sinh trả lời.
- Không tự trả lời thay học sinh.
- Nếu sai: giải thích thật ngắn.
- Động viên.
- Sau đó đưa đúng một câu tiếp theo.
- Phù hợp đúng lớp.
- HSK 3.0 là ưu tiên.
- Toán thường xuyên xen kẽ nhân và chia.

Bây giờ:
Chào {current_student}.
Nói một câu ngắn.
Đưa đúng một câu hỏi.
Sau đó DỪNG.
"""

    await session.send_realtime_input(
        text=prompt
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

Người nói là Lão sư.

Từ bây giờ:
- gọi người nói là Lão sư;
- trò chuyện tự nhiên;
- không tự bắt đầu bài học;
- không tự tạo câu hỏi;
- chờ Lão sư nói rồi mới trả lời.
"""
        )

    except Exception as e:

        print(
            f"\n⚠️ Không thể chuyển Chat Mode: {e}",
            flush=True,
        )


# ============================================================
# PROCESS USER TEXT
# ============================================================

async def process_user_text(
    session,
    text,
):

    global current_subject
    global last_subject
    global rotation_index

    if not text:
        return

    text = text.strip()

    if not text:
        return

    print(
        f"\n👤 Người nói: {text}",
        flush=True,
    )

    command = detect_tutor_command(
        text
    )

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
    # START LESSON
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
    # SWITCH STUDENT
    # --------------------------------------------------------

    if intent == "switch_student":

        new_student_id = (
            student["student_id"]
        )

        if (
            tutor_mode
            and new_student_id
            == current_student_id
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

                next_subject = (
                    get_next_subject()
                )

                current_subject = next_subject

                await session.send_realtime_input(
                    text=f"""
Tiếp tục với {current_student}.

Chuyển sang môn:
{SUBJECT_NAMES.get(next_subject, next_subject)}

Phù hợp lớp {current_grade}.

Nếu là Toán, thường xuyên ôn nhân và chia.

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
    # CHAT
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

        data = indata.tobytes()

        if shutdown_requested:
            return

        try:

            future = (
                asyncio.run_coroutine_threadsafe(
                    session.send_realtime_input(
                        audio=types.Blob(
                            data=data,
                            mime_type=(
                                "audio/pcm;rate=16000"
                            ),
                        )
                    ),
                    loop,
                )
            )

            # Không block callback.
            # Chỉ để exception không bị nuốt hoàn toàn.
            def done_callback(f):

                try:
                    f.result()
                except Exception:
                    pass

            future.add_done_callback(
                done_callback
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

        raise


# ============================================================
# RECEIVE LOOP
# ============================================================

async def receive_loop(session):

    """
    Chỉ đọc dữ liệu từ Gemini.

    QUAN TRỌNG:

    turn_complete = kết thúc lượt nói bình thường.

    Nó KHÔNG được coi là connection error.

    Không dùng:
    - Session Resumption
    - GOAWAY
    """

    try:

        async for response in session.receive():

            # ------------------------------------------------
            # TOOL CALL
            # ------------------------------------------------

            tool_call = getattr(
                response,
                "tool_call",
                None,
            )

            if tool_call:

                function_calls = getattr(
                    tool_call,
                    "function_calls",
                    None,
                )

                if function_calls:

                    await handle_tool_call(
                        session,
                        function_calls,
                    )

            # ------------------------------------------------
            # SERVER CONTENT
            # ------------------------------------------------

            server_content = getattr(
                response,
                "server_content",
                None,
            )

            if server_content is None:

                continue

            # ------------------------------------------------
            # INPUT TRANSCRIPTION
            # ------------------------------------------------

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

                    await process_user_text(
                        session,
                        text,
                    )

            # ------------------------------------------------
            # OUTPUT TRANSCRIPTION
            # ------------------------------------------------

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

                    print(
                        "💗 Tiểu Vũ:",
                        text,
                        flush=True,
                    )

            # ------------------------------------------------
            # AUDIO
            # ------------------------------------------------

            model_turn = getattr(
                server_content,
                "model_turn",
                None,
            )

            if model_turn:

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

                            play_audio(
                                data
                            )

            # ------------------------------------------------
            # TURN COMPLETE
            # ------------------------------------------------

            if getattr(
                server_content,
                "turn_complete",
                False,
            ):

                stop_audio()

                print(
                    "\n🎤 Tiểu Vũ đang nghe...",
                    flush=True,
                )

                # QUAN TRỌNG:
                # KHÔNG return.
                # KHÔNG reconnect.
                #
                # Đây chỉ là:
                # Gemini đã nói xong.
                #
                # Tiếp tục chờ microphone.

    except asyncio.CancelledError:

        raise

    except Exception as e:

        print(
            f"\n⚠️ Gemini Live connection lỗi: "
            f"{repr(e)}",
            flush=True,
        )

        # Chỉ ở đây mới yêu cầu reconnect.
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
        f"\n💗 Tiểu Vũ chủ động: {greeting}",
        flush=True,
    )

    try:

        await session.send_realtime_input(
            text=(
                "Hãy nói chính xác câu sau "
                "với Lão sư bằng giọng tự nhiên, "
                "thân mật và vui vẻ. "
                "Không thêm câu hỏi. "
                "Không thêm lời nào khác: "
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
            "theo múi giờ Việt Nam UTC+7. "
            "Không tự đoán giờ."
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

    # --------------------------------------------------------
    # SYSTEM INSTRUCTION
    # --------------------------------------------------------

    full_instruction = SYSTEM_INSTRUCTION + """

============================================================
TIỂU VŨ - LIVE VOICE
============================================================

Đây là một trợ lý giọng nói.

Có hai chế độ:

1. CHAT MODE
2. TUTOR MODE


============================================================
CHAT MODE
============================================================

Người lớn là Lão sư.

Trong Chat Mode:

- gọi người nói là Lão sư;
- trò chuyện tự nhiên;
- trả lời đúng câu hỏi;
- không tự bắt đầu bài học;
- không tự tạo bài kiểm tra;
- không tự hỏi liên tục;
- sau khi trả lời thì chờ Lão sư nói tiếp.


============================================================
STARTUP
============================================================

Tiểu Vũ chỉ chào một lần khi chương trình bắt đầu.

Sau lời chào:

DỪNG.

Chờ Lão sư nói.

Không tự chào lại.

Không tự nói:
"Lão sư ơi..."
nếu Lão sư chưa nói gì.

Không tự mở cuộc hội thoại mới.


============================================================
LIVE VOICE
============================================================

Người dùng nói -> Tiểu Vũ trả lời.

Tiểu Vũ nói xong -> DỪNG.

Chờ người dùng.

Không tự tạo lượt nói mới.

Không lặp lại lời chào.

Không tự nói sau khi một lượt đã hoàn thành.


============================================================
HAI HỌC SINH
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


Python quyết định học sinh.

Nếu Python nói học sinh là Mini:
gọi Mini.

Nếu Python nói học sinh là Minh Tiên:
gọi Minh Tiên.

Không tự ý đổi học sinh.


============================================================
HSK 3.0
============================================================

Tiếng Trung HSK 3.0 là môn ưu tiên.

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
- phân số;
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

- gọi đúng tên học sinh;
- phù hợp đúng lớp;
- nói ngắn;
- chỉ một câu hỏi mỗi lượt;
- sau câu hỏi phải dừng;
- chờ học sinh;
- đánh giá câu trả lời;
- giải thích ngắn nếu sai;
- động viên;
- đưa câu tiếp theo;
- lại dừng.


============================================================
LÃO SƯ
============================================================

Nếu nghe "Lão sư":

- hiểu người nói là người lớn;
- nếu đang Tutor Mode thì dừng bài học;
- quay về Chat Mode;
- gọi người nói là Lão sư.


============================================================
TOOLS
============================================================

Nếu Lão sư hỏi giờ:

BẮT BUỘC dùng current_time.

Nếu cần tính toán:

BẮT BUỘC dùng calculator.

Nếu hỏi ngày/thứ/ngày âm:

BẮT BUỘC dùng current_calendar.

Không tự đoán giờ.

Không tự đoán ngày.

Không tự đoán ngày âm.


============================================================
QUAN TRỌNG NHẤT
============================================================

Sau khi trả lời xong:

DỪNG.

Không tự nói thêm.

Chờ người dùng.

Không tự chào lại.

Không tự hỏi:
"Lão sư có chuyện gì cần nói với Tiểu Vũ không?"

trừ khi nội dung cuộc trò chuyện thực sự yêu cầu.

============================================================
"""


    return types.LiveConnectConfig(

        response_modalities=[
            "AUDIO"
        ],

        speech_config=types.SpeechConfig(

            voice_config=types.VoiceConfig(

                prebuilt_voice_config=(
                    types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )

            )

        ),

        system_instruction=types.Content(

            parts=[
                types.Part(
                    text=full_instruction
                )
            ]

        ),

        tools=[
            tools
        ],

        input_audio_transcription={},

        output_audio_transcription={},

        context_window_compression=(
            types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow()
            )
        ),
    )


# ============================================================
# RUN ONE CONNECTION
# ============================================================

async def run_one_connection():

    print(
        "\n🔌 Đang mở Gemini Live connection...",
        flush=True,
    )

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
        # RECEIVE TASK
        # ----------------------------------------------------

        receive_task = asyncio.create_task(
            receive_loop(session)
        )

        # ----------------------------------------------------
        # STARTUP GREETING
        #
        # CHỈ CHÀO 1 LẦN.
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

            # ------------------------------------------------
            # RECEIVE KẾT THÚC
            # ------------------------------------------------

            if receive_task in done:

                try:

                    reconnect_required = (
                        receive_task.result()
                    )

                except Exception as e:

                    print(
                        f"\n⚠️ Receive task lỗi: "
                        f"{repr(e)}",
                        flush=True,
                    )

                    reconnect_required = True

            # ------------------------------------------------
            # MICROPHONE KẾT THÚC
            # ------------------------------------------------

            if microphone_task in done:

                try:

                    microphone_task.result()

                except asyncio.CancelledError:

                    pass

                except Exception as e:

                    print(
                        f"\n⚠️ Microphone task lỗi: "
                        f"{repr(e)}",
                        flush=True,
                    )

                    reconnect_required = True

            # ------------------------------------------------
            # CANCEL TASK CÒN LẠI
            # ------------------------------------------------

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
# RESET STATE
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

    tutor_mode = False

    current_student = None
    current_student_id = None
    current_subject = None
    current_grade = None

    question_count = 0

    rotation_index = 0
    last_subject = None


# ============================================================
# START LIVE VOICE
# ============================================================

async def start_live_voice():

    global shutdown_requested
    global startup_greeting_sent

    reset_state()

    shutdown_requested = False

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
        "       NO SESSION RESUMPTION"
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
                    "\n⚠️ Gemini Live connection "
                    "đã kết thúc.",
                    flush=True,
                )

                print(
                    f"🔄 Tạo session mới sau "
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
            # Không có lỗi rõ ràng nhưng connection đã đóng.
            # ------------------------------------------------

            print(
                "\n⚠️ Gemini Live connection "
                "đã đóng.",
                flush=True,
            )

            print(
                f"🔄 Tạo session mới sau "
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
                f"\n❌ Gemini Live lỗi: "
                f"{repr(e)}",
                flush=True,
            )

            if shutdown_requested:
                break

            print(
                f"🔄 Tạo session mới sau "
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