# ============================================================
# TIỂU VŨ - LIVE VOICE
# STABLE STUDENT RECOGNITION VERSION
#
# CHAT MODE + TUTOR MODE
# HSK 3.0 + 3 TOOLS
#
# ĐẶC BIỆT:
# - Nhận diện học sinh bằng Python
# - Chống ASR sai: Đậu Đậu / đầu đầu / đầu phòng...
# - Hỗ trợ Mini / Đậu Phộng / Đậu Đậu
# - Giữ học sinh qua reconnect
# - Không tự khởi động lại bài học
# - Không tự đổi môn
# - Không nhận giọng Tiểu Vũ thành lời người dùng
# - 3 tools: Giờ / Máy tính / Lịch
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

startup_greeting_sent = False

command_suppressed_until = 0.0

# ------------------------------------------------------------
# Quan trọng:
#
# Khi Python vừa gửi prompt cho Gemini,
# mọi transcription trong khoảng này không được coi
# là lời người dùng.
# ------------------------------------------------------------

last_command_time = 0.0


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
            "DauDau",

            "Đậu Phộng",
            "Dau Phong",

            "Đậu Phụng",
            "Dau Phung",

            "Đầu Đầu",
            "Dau Dau",

            "Đầu Phòng",
            "Dau Phong",

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
            "mini",

            "Meanie",
            "meanie",

            "Mi Ni",
            "mi ni",

            "米妮",
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

            "official_name":
                student["official_name"],

            "called_name":
                alias.strip(),

            "gender":
                student["gender"],

            "grade":
                student["grade"],
        }


# ============================================================
# CANONICAL STUDENT NAMES
#
# Đây mới là tên Tiểu Vũ được phép gọi.
# Không dùng alias ASR để gọi lại học sinh.
# ============================================================

CANONICAL_STUDENT_NAMES = {

    "minh_tien": "Đậu Đậu",

    "nha_tien": "Mini",
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
            f"\n⚠️ Audio output lỗi: {repr(e)}",
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
        r"[.,!?;:，。！？；：]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def remove_accents(text):

    if not isinstance(text, str):
        return ""

    text = text.replace("đ", "d")
    text = text.replace("Đ", "D")

    normalized = unicodedata.normalize(
        "NFD",
        text,
    )

    result = "".join(
        char
        for char in normalized
        if unicodedata.category(char) != "Mn"
    )

    return result.lower().strip()


def compact_text(text):

    text = normalize_text(text)

    return re.sub(
        r"\s+",
        "",
        text,
    )


# ============================================================
# FUZZY NAME NORMALIZATION
# ============================================================

def name_key(text):

    text = remove_accents(
        normalize_text(text)
    )

    text = text.replace(
        " ",
        "",
    )

    return text


# ============================================================
# STUDENT NAME PATTERNS
#
# Gemini Live ASR rất dễ nghe sai:
#
# Đậu Đậu
# -> đầu đầu
# -> dau dau
# -> đầuđầu
#
# Đậu Phộng
# -> đầu phòng
# -> đầu phộng
# -> dau phong
#
# Vì vậy không chỉ kiểm tra exact string.
# ============================================================

MINH_TIEN_NAME_KEYS = {

    "daudau",
    "daudau",
    "daudau",

    "daudau",

    "daudau",

    "daudau",

    "dauphong",

    "dauphong",

    "dauphung",

    "dauphung",

    "dau dau",

    "dau phong",

    "dau phung",

    "dau dau",

    "dau phong",

    "dau phung",

    "dau dau",

    "dau phong",

    "dau phung",
}


NHA_TIEN_NAME_KEYS = {

    "mini",
    "meanie",
    "mini",

    "mi ni",

    "mini",
}


# ============================================================
# ĐẶC BIỆT:
# Các cụm ASR tiếng Việt có thể xuất hiện thay cho Đậu Đậu.
# ============================================================

MINH_TIEN_PHONETIC_PATTERNS = [

    "đậu đậu",
    "đầu đầu",
    "dậu dậu",
    "dau dau",

    "đậuđậu",
    "đầuđầu",
    "daudau",

    "đậu đậu",
    "đầu đầu",

    "đậu phòng",
    "đầu phòng",
    "dau phong",

    "đậu phộng",
    "đầu phộng",
    "dau phong",

    "đậu phụng",
    "đầu phụng",
    "dau phung",

]


NHA_TIEN_PHONETIC_PATTERNS = [

    "mini",
    "mi ni",
    "meanie",
    "me ni",

]


# ============================================================
# ALIAS MATCH
# ============================================================

def alias_matches(
    alias,
    normalized,
    no_accent,
):

    alias_normalized = normalize_text(
        alias
    )

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

    compact = compact_text(text)

    # --------------------------------------------------------
    # 1. Exact aliases
    # --------------------------------------------------------

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

            print(
                f"🔎 Nhận diện học sinh: "
                f"{CANONICAL_STUDENT_NAMES.get(student['student_id'], student['official_name'])} "
                f"({student['official_name']})",
                flush=True,
            )

            return student


    # --------------------------------------------------------
    # 2. Minh Tiên / Đậu Đậu - fuzzy phonetic
    # --------------------------------------------------------

    for pattern in MINH_TIEN_PHONETIC_PATTERNS:

        pattern_normalized = normalize_text(
            pattern
        )

        pattern_no_accent = remove_accents(
            pattern_normalized
        )

        pattern_compact = compact_text(
            pattern_normalized
        )

        if (
            pattern_normalized in normalized
            or pattern_no_accent in no_accent
            or pattern_compact in compact
        ):

            student = STUDENT_ALIASES.get(
                "đậu đậu"
            )

            if student:

                print(
                    "🔎 Nhận diện học sinh: "
                    "Đậu Đậu "
                    "(Minh Tiên) "
                    "[phonetic match]",
                    flush=True,
                )

                return student


    # --------------------------------------------------------
    # 3. Mini
    # --------------------------------------------------------

    for pattern in NHA_TIEN_PHONETIC_PATTERNS:

        pattern_normalized = normalize_text(
            pattern
        )

        pattern_no_accent = remove_accents(
            pattern_normalized
        )

        if (
            pattern_normalized in normalized
            or pattern_no_accent in no_accent
        ):

            student = STUDENT_ALIASES.get(
                "mini"
            )

            if student:

                print(
                    "🔎 Nhận diện học sinh: "
                    "Mini (Nhã Tiên) "
                    "[phonetic match]",
                    flush=True,
                )

                return student


    # --------------------------------------------------------
    # 4. Trường hợp ASR viết liền
    # --------------------------------------------------------

    if (
        "daudau" in compact
        or "dauphong" in compact
        or "dauphung" in compact
        or "daudau" in compact
    ):

        student = STUDENT_ALIASES.get(
            "đậu đậu"
        )

        if student:
            return student


    if "mini" in compact:

        student = STUDENT_ALIASES.get(
            "mini"
        )

        if student:
            return student


    return None


# ============================================================
# SUBJECT
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
                or remove_accents(word)
                in no_accent
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

        "muốn học bài",
        "muon hoc bai",

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

        if (
            remove_accents(pattern)
            in no_accent
        ):
            return True


    return False


# ============================================================
# TEACHER
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
            or remove_accents(pattern)
            in no_accent
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

    "communication":
        "Kỹ năng giao tiếp",

    "problem_solving":
        "Kỹ năng xử lý vấn đề",

    "emotional_intelligence":
        "EQ và quản lý cảm xúc",
}


def get_next_subject():

    global rotation_index
    global last_subject

    if last_subject is None:

        last_subject = "chinese"

        rotation_index = 0

        return "chinese"


    rotation_index += 1

    if rotation_index >= len(
        SUBJECT_ROTATION
    ):

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

Luôn thay đổi dạng bài.
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

Đồng thời thường xuyên xen kẽ phản xạ nhân/chia.

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

- Ưu tiên HSK 3.0.
- Từ vựng phù hợp.
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
        }


    # --------------------------------------------------------
    # Có học sinh + có ý định học
    # --------------------------------------------------------

    if student is not None and learning:

        return {

            "intent": "start_lesson",

            "student": student,

            "subject": subject,
        }


    # --------------------------------------------------------
    # Có học sinh nhưng chưa nói muốn học
    # --------------------------------------------------------

    if student is not None:

        return {

            "intent": "switch_student",

            "student": student,

            "subject": subject,
        }


    # --------------------------------------------------------
    # Muốn học nhưng không nói học sinh
    # --------------------------------------------------------

    if learning:

        return {

            "intent": "unknown_student",

            "student": None,

            "subject": subject,
        }


    return {

        "intent": "chat",

        "student": None,

        "subject": None,
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
# SEND TEXT COMMAND
# ============================================================

async def send_text_command(
    session,
    text,
    suppress_seconds=3.0,
):

    global command_suppressed_until

    loop = asyncio.get_running_loop()

    command_suppressed_until = (
        loop.time() + suppress_seconds
    )


    try:

        await session.send_client_content(

            turns=types.Content(

                role="user",

                parts=[

                    types.Part(
                        text=text
                    )

                ],
            ),

            turn_complete=True,

        )

        return True


    except Exception as e:

        print(
            f"\n⚠️ Không gửi được command: "
            f"{repr(e)}",
            flush=True,
        )

        return False


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


    student_id = student[
        "student_id"
    ]

    # --------------------------------------------------------
    # LUÔN dùng canonical name
    #
    # Không dùng alias Gemini vừa nghe được.
    # --------------------------------------------------------

    called_name = (
        CANONICAL_STUDENT_NAMES.get(
            student_id,
            student["official_name"],
        )
    )

    official_name = student[
        "official_name"
    ]

    grade = student[
        "grade"
    ]


    # --------------------------------------------------------
    # CHỌN MÔN
    # --------------------------------------------------------

    if subject is None:

        if not tutor_mode:

            subject = "chinese"

        elif current_subject is not None:

            subject = current_subject

        else:

            subject = "chinese"

    else:

        last_subject = subject

        if subject in SUBJECT_ROTATION:

            rotation_index = (
                SUBJECT_ROTATION.index(
                    subject
                )
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

        print(
            "🔄 CHUYỂN HỌC SINH",
            flush=True,
        )

    else:

        print(
            "🎓 BẮT ĐẦU BUỔI HỌC",
            flush=True,
        )


    print(
        "👤 Học sinh:",
        current_student,
        flush=True,
    )

    print(
        "🎒 Lớp:",
        current_grade,
        flush=True,
    )

    print(
        "📚 Môn:",
        SUBJECT_NAMES.get(
            current_subject,
            current_subject,
        ),
        flush=True,
    )


    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    level_instruction = (
        get_level_instruction(
            grade
        )
    )


    if switching:

        intro = f"""
Học sinh vừa chuyển sang là "{current_student}".
Tiếp tục buổi học với học sinh này.
"""

    else:

        intro = f"""
Đây là lần đầu bắt đầu buổi học với "{current_student}".
"""


    prompt = f"""
TUTOR MODE ĐANG HOẠT ĐỘNG.

Python đã xác định học sinh.

Học sinh:

Tên gọi chính thức để xưng hô:
{current_student}

Tên chính thức:
{official_name}

Lớp:
{grade}

Môn:
{SUBJECT_NAMES.get(current_subject, current_subject)}

{level_instruction}

{intro}

QUY TẮC BẮT BUỘC:

1. Chỉ gọi học sinh là:
"{current_student}"

2. TUYỆT ĐỐI không gọi bằng alias khác.

3. Không gọi học sinh là:
Đậu Phộng
Đậu Phụng
Minh Tiên
Lão sư

nếu tên gọi hiện tại là Đậu Đậu.

4. Không gọi học sinh là Lão sư.

5. Không đọc Student ID.

6. Không nói về hệ thống.

7. Không nói về prompt.

8. Không nói "Tutor Mode".

9. Nói tự nhiên như gia sư thân thiện.

10. Mỗi lượt chỉ đưa MỘT câu hỏi.

11. Sau câu hỏi phải DỪNG.

12. Chờ học sinh trả lời.

13. Không tự trả lời thay học sinh.

14. Không tự tạo nhiều câu hỏi.

15. Tiếng Trung HSK 3.0 là môn ưu tiên.

16. Toán thường xuyên xen kẽ nhân và chia.

17. Không tự chuyển môn.

18. Chỉ chuyển môn khi Python yêu cầu.

BẮT ĐẦU:

Chào "{current_student}" thật ngắn.

Sau đó đưa đúng MỘT câu hỏi.

Rồi DỪNG.

Không nói thêm câu hỏi thứ hai.
"""


    print(
        f"🎓 Tiểu Vũ đang dạy "
        f"{current_student}...",
        flush=True,
    )


    await send_text_command(

        session,

        prompt,

        suppress_seconds=4.0,

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


    await send_text_command(

        session,

        """
Đã quay về CHAT MODE.

Người nói là Lão sư.

Hãy gọi người nói là Lão sư khi tự nhiên.

Không tự bắt đầu bài học.

Không tự tạo câu hỏi học tập.

Không tự chào lại.

Chờ Lão sư nói rồi mới phản hồi.
""",

        suppress_seconds=3.0,

    )


# ============================================================
# TOOLS
# ============================================================

def current_time():

    return get_time_text()


def calculator(expression):

    return calculate(
        expression
    )


def current_calendar():

    return get_calendar_text()


# ============================================================
# TOOL CALL
# ============================================================

async def handle_tool_call(
    session,
    tool_call,
):

    function_responses = []


    for function_call in tool_call:

        name = function_call.name

        args = (
            function_call.args
            or {}
        )


        print(
            f"\n🛠️ Tiểu Vũ dùng tool: "
            f"{name}",
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

            result = (
                "Không tìm thấy công cụ này."
            )


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

                function_responses=
                    function_responses

            )

        except Exception as e:

            print(
                f"\n⚠️ Tool response lỗi: "
                f"{repr(e)}",
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


        audio_bytes = (
            indata.tobytes()
        )


        try:

            future = (
                asyncio
                .run_coroutine_threadsafe(

                    session.send_realtime_input(

                        audio=types.Blob(

                            data=audio_bytes,

                            mime_type=
                                "audio/pcm;rate=16000",

                        )

                    ),

                    loop,

                )
            )


            def done_callback(f):

                try:

                    f.exception()

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
            f"\n⚠️ Microphone lỗi: "
            f"{repr(e)}",
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
    global last_subject
    global rotation_index


    if not text:
        return


    text = text.strip()


    if not text:
        return


    # --------------------------------------------------------
    # CHỐNG TRANSCRIPTION CỦA COMMAND
    # --------------------------------------------------------

    loop = asyncio.get_running_loop()


    if loop.time() < command_suppressed_until:

        print(
            f"\n🔇 Bỏ qua transcription "
            f"của Tiểu Vũ: {text}",
            flush=True,
        )

        return


    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    print(
        f"\n👤 Người nói: {text}",
        flush=True,
    )


    # --------------------------------------------------------
    # DETECT COMMAND
    # --------------------------------------------------------

    command = detect_tutor_command(
        text
    )


    intent = command[
        "intent"
    ]

    student = command[
        "student"
    ]

    subject = command[
        "subject"
    ]


    # --------------------------------------------------------
    # LÃO SƯ
    # --------------------------------------------------------

    if mentions_teacher(text):

        await exit_tutor_mode(
            session
        )

        return


    # ========================================================
    # START LESSON
    # ========================================================

    if intent == "start_lesson":

        if (
            tutor_mode
            and current_student_id
            == student["student_id"]
        ):

            print(
                "🔇 Đã ở Tutor Mode với "
                "học sinh này. "
                "Không khởi động lại.",
                flush=True,
            )

            return


        print(
            f"🎓 Phát hiện học sinh: "
            f"{CANONICAL_STUDENT_NAMES.get(
                student['student_id'],
                student['official_name']
            )}",
            flush=True,
        )


        if subject:

            print(
                f"📚 Môn học: "
                f"{SUBJECT_NAMES.get(
                    subject,
                    subject
                )}",
                flush=True,
            )

        else:

            print(
                "📚 Môn học: "
                "Tiếng Trung HSK 3.0",
                flush=True,
            )


        await start_tutor_session(

            session,

            student,

            subject,

            switching=tutor_mode,

        )

        return


    # ========================================================
    # SWITCH STUDENT
    # ========================================================

    if intent == "switch_student":

        new_student_id = (
            student["student_id"]
        )


        # ----------------------------------------------------
        # CÙNG HỌC SINH
        # ----------------------------------------------------

        if (
            tutor_mode
            and new_student_id
            == current_student_id
        ):

            print(
                f"🎓 Vẫn là học sinh hiện tại: "
                f"{current_student}",
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


                await send_text_command(

                    session,

                    f"""
Tiếp tục với {current_student}.

Bây giờ chuyển sang môn:

{SUBJECT_NAMES.get(
    subject,
    subject
)}

Nội dung phù hợp lớp {current_grade}.

Chỉ đưa MỘT câu hỏi.

Sau đó DỪNG.
""",

                    suppress_seconds=3.0,

                )

            else:

                print(
                    "ℹ️ Không có môn mới. "
                    "Giữ nguyên môn hiện tại.",
                    flush=True,
                )


            return


        # ----------------------------------------------------
        # KHÁC HỌC SINH
        # ----------------------------------------------------

        print(
            f"🔄 Đổi học sinh: "
            f"{current_student or 'chưa có'}"
            f" → "
            f"{CANONICAL_STUDENT_NAMES.get(
                student['student_id'],
                student['official_name']
            )}",
            flush=True,
        )


        await start_tutor_session(

            session,

            student,

            subject,

            switching=tutor_mode,

        )

        return


    # ========================================================
    # MUỐN HỌC NHƯNG KHÔNG NÓI TÊN
    # ========================================================

    if intent == "unknown_student":

        print(
            "⚠️ Chưa xác định được "
            "học sinh.",
            flush=True,
        )


        await send_text_command(

            session,

            """
Người nói muốn bắt đầu học
nhưng chưa nói tên học sinh.

Hỏi thật ngắn:

"Tiểu Vũ dạy Đậu Đậu hay Mini nè?"

Chỉ hỏi một câu.

Không tự bắt đầu bài học.
""",

            suppress_seconds=3.0,

        )

        return


    # ========================================================
    # CHAT
    # ========================================================

    if intent == "chat":

        if tutor_mode:

            print(
                f"🎓 Tutor Mode: "
                f"{current_student}",
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

    try:

        async for response in session.receive():

            # ------------------------------------------------
            # TOOL
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


    except asyncio.CancelledError:

        raise


    except Exception as e:

        print(

            "\n⚠️ GEMINI LIVE RECEIVE ERROR",

            flush=True,

        )


        print(

            f"   Type: {type(e).__name__}",

            flush=True,

        )


        print(

            f"   Detail: {repr(e)}",

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


    greeting = (
        get_startup_greeting()
    )


    print(

        f"\n💗 Tiểu Vũ chủ động: "
        f"{greeting}",

        flush=True,

    )


    ok = await send_text_command(

        session,

        f"""
Hãy nói đúng câu sau với Lão sư:

"{greeting}"

Không thêm câu nào khác.

Sau khi nói xong thì DỪNG.

Chờ Lão sư nói.
""",

        suppress_seconds=5.0,

    )


    if ok:

        startup_greeting_sent = True


# ============================================================
# LIVE CONFIG
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

    calculator_tool = (
        types.FunctionDeclaration(

            name="calculator",

            description=(
                "Tính toán biểu thức "
                "toán học chính xác."
            ),

            parameters=types.Schema(

                type="OBJECT",

                properties={

                    "expression": types.Schema(

                        type="STRING",

                        description=(
                            "Biểu thức toán học."
                        ),

                    ),

                },

                required=[
                    "expression"
                ],

            ),

        )
    )


    # --------------------------------------------------------
    # CALENDAR
    # --------------------------------------------------------

    calendar_tool = (
        types.FunctionDeclaration(

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
    )


    tools = types.Tool(

        function_declarations=[

            time_tool,

            calculator_tool,

            calendar_tool,

        ]

    )


    # --------------------------------------------------------
    # FULL SYSTEM INSTRUCTION
    # --------------------------------------------------------

    full_instruction = (
        SYSTEM_INSTRUCTION
        + """

============================================================
TIỂU VŨ LIVE VOICE
============================================================

Có hai chế độ:

1. CHAT MODE
2. TUTOR MODE

============================================================
CHAT MODE
============================================================

Người lớn là Lão sư.

Không tự bắt đầu bài học.

Không tự tạo bài kiểm tra.

Không tự chào lại.

Chờ Lão sư nói.

============================================================
TUTOR MODE
============================================================

Python là hệ thống quyết định học sinh.

Không tự suy đoán học sinh.

Không tự đổi học sinh.

Không tự đổi môn.

Khi Python gửi tên học sinh,
phải dùng đúng tên đó.

Nếu Python nói:

"Đậu Đậu"

thì chỉ được gọi:

"Đậu Đậu"

Không gọi:

"Đậu Phộng"

"Đậu Phụng"

"Minh Tiên"

"Đầu Phòng"

hoặc alias khác.

============================================================
HSK 3.0
============================================================

Tiếng Trung HSK 3.0 là môn ưu tiên.

============================================================
TOÁN
============================================================

Lớp 4 thường xuyên luyện:

- nhân
- chia
- chia có dư
- bài toán có lời văn
- phân số
- hình học
- logic

Lớp 6:

- số nguyên
- phân số
- tỉ số
- biểu thức
- hình học
- logic

============================================================
RECONNECT
============================================================

Nếu connection bị đóng:

Không chào lại.

Không tự bắt đầu bài học.

Không lặp lại command cũ.

Nếu Python đã xác định học sinh,
tiếp tục chờ người dùng nói.

============================================================
TOOLS
============================================================

Nếu Lão sư hỏi giờ:
BẮT BUỘC dùng current_time.

Nếu cần tính:
BẮT BUỘC dùng calculator.

Nếu hỏi ngày:
BẮT BUỘC dùng current_calendar.

Không đoán giờ.

Không đoán ngày.

Không đoán ngày âm.

============================================================
CỰC KỲ QUAN TRỌNG
============================================================

Không được coi lời Tiểu Vũ là lời của Lão sư.

Không tự đóng vai học sinh.

Không tự trả lời thay học sinh.

Không tự tạo nhiều câu hỏi.

Không tự chuyển môn.

Không tự khởi động lại bài học.
"""
    )


    return types.LiveConnectConfig(

        response_modalities=[
            "AUDIO"
        ],

        speech_config=types.SpeechConfig(

            voice_config=types.VoiceConfig(

                prebuilt_voice_config=
                    types.PrebuiltVoiceConfig(

                        voice_name="Aoede"

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

                sliding_window=
                    types.SlidingWindow()

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

            "💡 Gọi tên bé + "
            "'muốn học' để bắt đầu.",

            flush=True,

        )


        print(

            "💡 Gọi tên bé khác "
            "để chuyển học sinh.",

            flush=True,

        )


        print(

            "💡 Gọi 'Lão sư' "
            "để về Chat Mode.",

            flush=True,

        )


        print(

            "💡 HSK 3.0 được ưu tiên.",

            flush=True,

        )


        print(

            "💡 Toán thường xuyên "
            "ôn nhân và chia.",

            flush=True,

        )


        print(

            "💡 Các môn sẽ luân phiên.",

            flush=True,

        )


        print(

            "💡 3 tools: "
            "Giờ / Máy tính / Lịch.",

            flush=True,

        )


        print(

            "💡 Ctrl+C để thoát.",

            flush=True,

        )


        print()


        receive_task = asyncio.create_task(

            receive_loop(
                session
            )

        )


        if not startup_greeting_sent:

            await startup_greeting(
                session
            )


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

                return_when=
                    asyncio.FIRST_COMPLETED,

            )


            reconnect_required = False


            if receive_task in done:

                try:

                    result = (
                        receive_task.result()
                    )

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
    global command_suppressed_until


    reset_state()


    shutdown_requested = False

    startup_greeting_sent = False

    command_suppressed_until = 0.0


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


            print(

                "\n⚠️ Gemini Live "
                "connection đã đóng.",

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


            # ------------------------------------------------
            # KHÔNG reset tutor state.
            #
            # current_student vẫn giữ nguyên.
            # ------------------------------------------------

            continue


        except asyncio.CancelledError:

            shutdown_requested = True

            break


        except KeyboardInterrupt:

            shutdown_requested = True

            break


        except Exception as e:

            print(

                "\n❌ TIỂU VŨ LIVE ERROR",

                flush=True,

            )


            print(

                f"   Type: "
                f"{type(e).__name__}",

                flush=True,

            )


            print(

                f"   Detail: {repr(e)}",

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

        "\n🧹 Tiểu Vũ đã đóng audio "
        "và dọn dẹp.",

        flush=True,

    )
