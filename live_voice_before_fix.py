# ============================================================
# TIỂU VŨ - LIVE VOICE
# CHAT MODE + TUTOR MODE
#
# BẢN ỔN ĐỊNH
#
# - CHAT MODE
# - TUTOR MODE
# - MINH TIÊN / ĐẬU ĐẬU / ĐẬU PHỘNG / ĐẬU PHỤNG = LỚP 4
# - NHÃ TIÊN / MINI / MEANIE / 미니 = LỚP 6
#
# ƯU TIÊN:
# 1. TIẾNG TRUNG HSK 3.0
# 2. TOÁN
# 3. TIẾNG VIỆT
# 4. TIẾNG ANH
# 5. LỊCH SỬ
# 6. ĐỊA LÝ
# 7. GIAO TIẾP
# 8. XỬ LÝ VẤN ĐỀ
# 9. EQ
#
# LIVE:
# - AUTO RECONNECT
# - SESSION RESUMPTION
# - GOAWAY HANDLING
# - KHÔNG transparent
# - CHỈ CHÀO 1 LẦN MỖI LẦN CHẠY
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

# Session resumption handle.
# Chỉ giữ handle trong cùng một lần chạy chương trình.
session_resumption_handle = None

# Server đã gửi GOAWAY.
goaway_received = False

# Người dùng Ctrl+C.
shutdown_requested = False

# Chỉ chào một lần khi chương trình bắt đầu.
startup_greeting_sent = False


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
# AUDIO
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


# ============================================================
# REMOVE ACCENTS
# ============================================================

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


# ============================================================
# NEXT SUBJECT
# ============================================================

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
# SMART MATH ROTATION
# ============================================================

def math_instruction(grade):

    if grade == 4:

        return """
TOÁN LỚP 4:

Thường xuyên xen kẽ:

- phép nhân;
- phép chia;
- chia có dư;
- nhân số có nhiều chữ số;
- bài toán có lời văn;
- phân số cơ bản;
- đơn vị đo;
- chu vi;
- diện tích;
- suy luận.

Ưu tiên luyện nhân/chia nhưng không hỏi máy móc.

Không chỉ hỏi:
2 x 2.

Hãy thay đổi dạng:

- tìm số còn thiếu;
- bài toán ngược;
- tính nhẩm;
- chia có dư;
- bài toán thực tế;
- suy luận.
"""

    return """
TOÁN LỚP 6:

Phù hợp lớp 6.

Ưu tiên:

- số nguyên;
- phân số;
- tỉ số;
- biểu thức;
- đại lượng;
- hình học;
- bài toán nhiều bước;
- logic.

Đồng thời thường xuyên xen kẽ:

- bảng nhân;
- bảng chia;
- phản xạ nhân/chia.

Không hạ toàn bộ bài học xuống lớp 4.
"""


# ============================================================
# LEVEL INSTRUCTION
# ============================================================

def get_level_instruction(grade):

    if grade == 4:

        return f"""
HỌC SINH LỚP 4.

Không ra bài quá dễ.

{math_instruction(4)}

TIẾNG TRUNG:

- Ưu tiên HSK 3.0.
- Từ vựng phù hợp độ tuổi.
- Nghe hiểu.
- Phản xạ.
- Hội thoại.
- Đặt câu.
- Đọc hiểu ngắn.
"""

    return f"""
HỌC SINH LỚP 6.

Không được hạ kiến thức xuống lớp 4.

{math_instruction(6)}

TIẾNG TRUNG:

- Ưu tiên HSK 3.0.
- Tăng vốn từ.
- Nghe hiểu.
- Phản xạ.
- Hội thoại.
- Đặt câu.
- Đọc hiểu.
- Tình huống thực tế.
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
# START TUTOR SESSION
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

    # --------------------------------------------------------
    # SUBJECT
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    tutor_mode = True

    current_student = called_name

    current_student_id = student_id

    current_subject = subject

    current_grade = grade

    question_count = 0

    # --------------------------------------------------------
    # CONSOLE
    # --------------------------------------------------------

    print()

    if switching:
        print("🔄 CHUYỂN HỌC SINH")
    else:
        print("🎓 BẮT ĐẦU BUỔI HỌC")

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

    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    level_instruction = get_level_instruction(
        grade
    )

    if switching:

        intro = f"""
Học sinh vừa chuyển sang là "{current_student}".
Hãy tiếp tục buổi học với học sinh này.
"""

    else:

        intro = f"""
Hãy bắt đầu buổi học với "{current_student}".
"""

    prompt = f"""
TUTOR MODE ĐANG HOẠT ĐỘNG.

Học sinh hiện tại:

- Tên gọi: {current_student}
- Tên chính thức: {official_name}
- Lớp: {grade}
- Student ID: {student_id}
- Môn hiện tại: {SUBJECT_NAMES.get(current_subject, current_subject)}

{level_instruction}

{intro}

QUY TẮC:

1. Luôn gọi học sinh bằng đúng tên:
"{current_student}"

2. Không gọi học sinh bằng alias khác.

3. Không gọi học sinh là Lão sư.

4. Không đọc Student ID.

5. Không nói về hệ thống.

6. Không nói về prompt.

7. Không nói "Tutor Mode".

8. Không hỏi người lớn.

9. Tiểu Vũ phải chủ động.

10. Chỉ đưa MỘT câu hỏi mỗi lượt.

11. Sau câu hỏi phải DỪNG.

12. Chờ học sinh trả lời.

13. Khi học sinh trả lời:
- đánh giá đúng/sai;
- nếu sai giải thích ngắn;
- động viên;
- đưa câu tiếp theo;
- chỉ một câu;
- rồi DỪNG.

14. Không tự trả lời thay học sinh.

15. Không ra bài quá dễ.

16. Luôn điều chỉnh theo lớp.

17. Tiếng Trung HSK 3.0 là môn ưu tiên.

18. Khi học Toán:
thường xuyên quay lại nhân và chia,
nhưng thay đổi dạng bài.

BẮT ĐẦU:

- chào "{current_student}";
- nói một câu thân thiện;
- đưa đúng MỘT câu hỏi;
- DỪNG.

Không đưa câu hỏi thứ hai.
"""

    print(
        f"🎓 Tiểu Vũ đang dạy {current_student}...",
        flush=True,
    )

    await session.send_realtime_input(
        text=prompt
    )


# ============================================================
# EXIT TUTOR MODE
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
- Chờ Lão sư nói chuyện rồi mới phản hồi.
"""
        )

    except Exception as e:

        print(
            f"\n⚠️ Không thể chuyển Chat Mode: {e}",
            flush=True,
        )


# ============================================================
# TOOL 1 - TIME
# ============================================================

def current_time():

    return get_time_text()


# ============================================================
# TOOL 2 - CALCULATOR
# ============================================================

def calculator(expression):

    return calculate(
        expression
    )


# ============================================================
# TOOL 3 - CALENDAR
# ============================================================

def current_calendar():

    return get_calendar_text()


# ============================================================
# TOOL CALL HANDLER
# ============================================================

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

            expression = args.get(
                "expression",
                "",
            )

            result = calculator(
                expression
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
                "MIC:",
                status,
                flush=True,
            )

        audio_bytes = indata.tobytes()

        try:

            asyncio.run_coroutine_threadsafe(

                session.send_realtime_input(

                    audio=types.Blob(
                        data=audio_bytes,
                        mime_type="audio/pcm;rate=16000",
                    )

                ),

                loop,

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
# PROCESS USER TEXT
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

        try:

            await exit_tutor_mode(
                session
            )

        except Exception:

            pass

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

        if subject:

            print(
                f"📚 Môn học: "
                f"{SUBJECT_NAMES.get(subject, subject)}",
                flush=True,
            )

        else:

            print(
                "📚 Môn học: Tiếng Trung HSK 3.0",
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

        new_student_id = student["student_id"]

        # CÙNG HỌC SINH

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

                if subject in SUBJECT_ROTATION:

                    global last_subject
                    global rotation_index

                    last_subject = subject

                    rotation_index = SUBJECT_ROTATION.index(
                        subject
                    )

                await session.send_realtime_input(

                    text=f"""
Tiếp tục với {current_student}.

Bây giờ chuyển sang môn:

{SUBJECT_NAMES.get(subject, subject)}

Nội dung phù hợp lớp {current_grade}.

Chỉ hỏi MỘT câu rồi DỪNG.
"""
                )

            else:

                next_subject = get_next_subject()

                current_subject = next_subject

                await session.send_realtime_input(

                    text=f"""
Tiếp tục với {current_student}.

Hãy chuyển sang môn tiếp theo:

{SUBJECT_NAMES.get(next_subject, next_subject)}

Nội dung phù hợp lớp {current_grade}.

Nếu là Toán, nhớ xen kẽ nhân/chia.

Chỉ đưa MỘT câu hỏi rồi DỪNG.
"""
                )

            return

        # KHÁC HỌC SINH

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

    if intent == "chat":

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
# RECEIVE LOOP
# ============================================================

async def receive_loop(session):

    global session_resumption_handle
    global goaway_received

    try:

        async for response in session.receive():

            # ------------------------------------------------
            # GOAWAY
            # ------------------------------------------------

            if response.go_away is not None:

                goaway_received = True

                time_left = getattr(
                    response.go_away,
                    "time_left",
                    None,
                )

                print(
                    "\n⚠️ Gemini Live gửi GOAWAY.",
                    flush=True,
                )

                if time_left is not None:

                    print(
                        f"⏳ Connection sắp đóng: {time_left}",
                        flush=True,
                    )

                print(
                    "🔄 Đóng connection và reconnect...",
                    flush=True,
                )

                return True

            # ------------------------------------------------
            # SESSION RESUMPTION
            # ------------------------------------------------

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

                # CHỈ IN KHI HANDLE THỰC SỰ THAY ĐỔI

                if (
                    resumable
                    and new_handle
                    and new_handle != session_resumption_handle
                ):

                    session_resumption_handle = new_handle

                    print(
                        "\n🔑 Session Resumption handle đã cập nhật.",
                        flush=True,
                    )

            # ------------------------------------------------
            # TOOL
            # ------------------------------------------------

            tool_call = getattr(
                response,
                "tool_call",
                None,
            )

            if tool_call:

                await handle_tool_call(
                    session,
                    tool_call.function_calls,
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
            # USER TRANSCRIPTION
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

                            play_audio(data)

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

    # Không bao giờ chào lại.
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
    # TIME TOOL
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

    # --------------------------------------------------------
    # TOOLS
    # --------------------------------------------------------

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
TIỂU VŨ - LIVE VOICE EDUCATION SYSTEM
============================================================

Có 2 chế độ:

1. CHAT MODE
2. TUTOR MODE


============================================================
CHAT MODE
============================================================

Người lớn là:

"Lão sư"

Trong Chat Mode:

- gọi người lớn là Lão sư;
- trò chuyện tự nhiên;
- không tự mở bài học;
- không tự tạo bài kiểm tra;
- trả lời qua lại tự nhiên.


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


============================================================
QUAN TRỌNG
============================================================

Python quyết định học sinh.

Không tự ý đổi học sinh.

Nếu Python nói học sinh hiện tại là Mini:
hãy gọi Mini.

Nếu Python nói học sinh hiện tại là Đậu Phộng:
hãy gọi Đậu Phộng.


============================================================
HSK 3.0
============================================================

Tiếng Trung là môn ưu tiên hàng đầu.

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
3. Hỏi MỘT câu.
4. DỪNG.
5. Chờ học sinh.
6. Chấm.
7. Giải thích ngắn nếu sai.
8. Động viên.
9. Đưa câu tiếp theo.
10. DỪNG.

Không hỏi nhiều câu cùng một lượt.


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

Khi hỏi giờ:
BẮT BUỘC dùng current_time.

Khi cần tính:
BẮT BUỘC dùng calculator.

Khi hỏi ngày:
BẮT BUỘC dùng current_calendar.

Không đoán giờ.

Không đoán ngày.

Không đoán ngày âm.


============================================================
LIVE VOICE
============================================================

Tiểu Vũ chỉ tự chào một lần khi chương trình khởi động.

Sau khi chào:

- chờ Lão sư nói;
- không tự chào lại;
- không tự bắt đầu hội thoại mới;
- không tự gửi lời chào sau reconnect.

Khi reconnect:
tiếp tục chờ người nói.

Không tự nói lại lời chào.


============================================================
"""


    # --------------------------------------------------------
    # CONFIG
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SESSION RESUMPTION
    #
    # KHÔNG transparent=True
    # --------------------------------------------------------

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
# RUN ONE CONNECTION
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
        # RECEIVE
        # ----------------------------------------------------

        receive_task = asyncio.create_task(

            receive_loop(
                session
            )

        )

        # ----------------------------------------------------
        # GREETING
        #
        # startup_greeting_sent quyết định.
        # Không phụ thuộc vào session handle.
        # ----------------------------------------------------

        if not startup_greeting_sent:

            await startup_greeting(
                session
            )

        # ----------------------------------------------------
        # MICROPHONE
        # ----------------------------------------------------

        microphone_task = asyncio.create_task(

            microphone_sender(
                session
            )

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
                        f"\n⚠️ Receive task lỗi: {repr(e)}",
                        flush=True,
                    )

                    reconnect_required = True

            # ------------------------------------------------
            # CANCEL PENDING
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
    global session_resumption_handle
    global startup_greeting_sent

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    reset_state()

    shutdown_requested = False

    # Mỗi lần chạy python main.py là một phiên mới.
    session_resumption_handle = None

    # Chào đúng một lần trong lần chạy này.
    startup_greeting_sent = False

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # RECONNECT LOOP
    # --------------------------------------------------------

    while not shutdown_requested:

        try:

            reconnect_required = await run_one_connection()

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
            # NORMAL CLOSE
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
                f"🔄 Tiểu Vũ sẽ reconnect sau "
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
