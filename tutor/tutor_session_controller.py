# ============================================================
# TIỂU VŨ - TUTOR SESSION CONTROLLER V3
#
# NHIỆM VỤ:
#   1. Nhận lệnh từ Tutor Trigger
#   2. Xác định học sinh: Mini / Đậu Phộng / Đậu Đậu
#   3. Xác định môn học
#   4. KHÓA tên học sinh trong phiên
#   5. KHÔNG tự ý đổi tên trong suốt phiên
#   6. Khi bắt đầu học -> chủ động tạo câu hỏi
#   7. Sau mỗi câu trả lời -> tự tạo câu hỏi tiếp theo
#
# NGUYÊN TẮC:
#   "Đậu Phộng muốn học"
#       ↓
#   nickname = "Đậu Phộng"
#       ↓
#   lock session
#       ↓
#   Tiểu Vũ gọi "Đậu Phộng" suốt phiên
#
#   "Mini muốn học"
#       ↓
#   nickname = "Mini"
#
#   "Đậu Đậu muốn học"
#       ↓
#   nickname = "Đậu Đậu"
#
# KHÔNG ĐƯỢC FALLBACK VỀ MINI NẾU TRIGGER ĐÃ NHẬN DIỆN TÊN.
# ============================================================


import os
import sys


# ============================================================
# PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(
        0,
        BASE_DIR
    )


# ============================================================
# IMPORT LESSON ENGINE
# ============================================================

from tutor.lesson_manager import (
    create_lesson_session,
    finish_session,
    get_session_summary,
)

from tutor.question_engine import (
    generate_question,
    check_answer,
)


# ============================================================
# IMPORT TRIGGER
#
# File trigger của bạn cần nằm cùng package tutor.
#
# Ví dụ:
#
# tutor/
#   tutor_trigger.py
#   tutor_session_controller.py
# ============================================================

try:

    from tutor.tutor_trigger import (
        detect_tutor_command,
    )

except ImportError:

    detect_tutor_command = None


# ============================================================
# HỖ TRỢ DICT AN TOÀN
# ============================================================

def safe_get(
    data,
    key,
    default=None
):

    if not isinstance(
        data,
        dict
    ):

        return default

    return data.get(
        key,
        default
    )


# ============================================================
# DANH SÁCH HỌC SINH HỢP LỆ
#
# Chỉ những tên này mới được khóa vào lesson session.
# ============================================================

VALID_STUDENTS = {

    "mini": "Mini",

    "đậu phộng": "Đậu Phộng",
    "dau phong": "Đậu Phộng",

    "đậu phụng": "Đậu Phộng",
    "dau phung": "Đậu Phộng",

    "đậu đậu": "Đậu Đậu",
    "dau dau": "Đậu Đậu",

}


# ============================================================
# CHUẨN HÓA TÊN
# ============================================================

def normalize_student_name(
    nickname
):

    if not isinstance(
        nickname,
        str
    ):

        return None

    nickname = nickname.strip()

    if not nickname:

        return None

    key = nickname.lower()

    return VALID_STUDENTS.get(
        key,
        nickname
    )


# ============================================================
# XÁC ĐỊNH HỌC SINH
# ============================================================

def resolve_student(
    command,
    current_student=None
):

    # --------------------------------------------------------
    # ƯU TIÊN TUYỆT ĐỐI:
    # nickname do trigger nhận diện
    # --------------------------------------------------------

    command_nickname = safe_get(
        command,
        "nickname",
        None
    )

    if command_nickname:

        return normalize_student_name(
            command_nickname
        )


    # --------------------------------------------------------
    # Nếu trigger không nói tên,
    # giữ tên học sinh hiện tại.
    # --------------------------------------------------------

    if current_student:

        return normalize_student_name(
            current_student
        )


    # --------------------------------------------------------
    # Chỉ fallback Mini khi HOÀN TOÀN không có thông tin.
    # --------------------------------------------------------

    return "Mini"


# ============================================================
# XÁC ĐỊNH MÔN HỌC
# ============================================================

def resolve_subject(
    command,
    current_subject=None
):

    subject = safe_get(
        command,
        "subject",
        None
    )

    if subject:

        return subject


    if current_subject:

        return current_subject


    # Mặc định vẫn giữ Toán
    # vì phần này đang hoạt động ổn định.
    return "math"


# ============================================================
# KHÓA HỌC SINH CHO SESSION
# ============================================================

def lock_student(
    session,
    nickname
):

    nickname = normalize_student_name(
        nickname
    )

    if not nickname:

        nickname = "Mini"


    # --------------------------------------------------------
    # KHÓA TÊN
    # --------------------------------------------------------

    session["nickname"] = nickname

    session["student_nickname"] = nickname

    session["student_display_name"] = nickname

    session["nickname_locked"] = True

    session["student_locked"] = True


    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print()
    print(
        f"🔒 HỌC SINH ĐÃ KHÓA: {nickname}"
    )


    return nickname


# ============================================================
# LẤY HỌC SINH ĐÃ KHÓA
# ============================================================

def get_student(
    session
):

    # --------------------------------------------------------
    # ƯU TIÊN nickname đã khóa
    # --------------------------------------------------------

    nickname = safe_get(
        session,
        "nickname",
        None
    )

    if (
        isinstance(
            nickname,
            str
        )
        and nickname.strip()
    ):

        return nickname.strip()


    # --------------------------------------------------------
    # Dự phòng student_display_name
    # --------------------------------------------------------

    nickname = safe_get(
        session,
        "student_display_name",
        None
    )

    if (
        isinstance(
            nickname,
            str
        )
        and nickname.strip()
    ):

        return nickname.strip()


    # --------------------------------------------------------
    # Dự phòng student_nickname
    # --------------------------------------------------------

    nickname = safe_get(
        session,
        "student_nickname",
        None
    )

    if (
        isinstance(
            nickname,
            str
        )
        and nickname.strip()
    ):

        return nickname.strip()


    # --------------------------------------------------------
    # Cuối cùng mới Mini
    # --------------------------------------------------------

    return "Mini"


# ============================================================
# KHÓA MÔN HỌC
# ============================================================

def lock_subject(
    session,
    subject
):

    if not subject:

        subject = "math"


    session["subject_id"] = subject

    session["subject_locked"] = True


    return subject


# ============================================================
# LẤY MÔN HỌC
# ============================================================

def get_subject(
    session
):

    return safe_get(
        session,
        "subject_id",
        "math"
    )


# ============================================================
# TẠO CÂU HỎI
# ============================================================

def create_next_question(
    session
):

    student_id = safe_get(
        session,
        "student_id",
        None
    )

    subject_id = get_subject(
        session
    )

    topic = safe_get(
        session,
        "topic",
        "addition"
    )

    strategy = safe_get(
        session,
        "strategy",
        "practice"
    )


    question = generate_question(

        student_id=student_id,

        subject_id=subject_id,

        topic=topic,

        strategy=strategy,

    )


    if not isinstance(
        question,
        dict
    ):

        raise ValueError(
            "Question Engine không trả về câu hỏi hợp lệ."
        )


    # --------------------------------------------------------
    # LƯU CÂU HỎI
    # --------------------------------------------------------

    session["current_question"] = question

    session["current_question_answered"] = False

    session["question_topic"] = safe_get(
        question,
        "topic",
        topic
    )


    session["questions"] = (
        session.get(
            "questions",
            0
        ) + 1
    )


    session["step"] = (
        session.get(
            "step",
            0
        ) + 1
    )


    return question


# ============================================================
# TIỂU VŨ CHỦ ĐỘNG ĐƯA CÂU HỎI
# ============================================================

def present_question(
    session,
    question
):

    nickname = get_student(
        session
    )


    question_text = safe_get(
        question,
        "question",
        "Tiểu Vũ chưa tạo được câu hỏi."
    )


    print()
    print("=" * 60)

    print(
        f"💗 Tiểu Vũ: {nickname} ơi!"
    )

    print(
        question_text
    )

    print()

    print(
        f"🎤 {nickname} cứ nói đáp án tự nhiên nha."
    )

    print(
        "⌨️ Hoặc gõ đáp án rồi nhấn Enter."
    )

    print("=" * 60)


# ============================================================
# PROCESS ANSWER
# ============================================================

def process_answer(
    session,
    answer
):

    nickname = get_student(
        session
    )

    question = safe_get(
        session,
        "current_question",
        None
    )


    if not question:

        return {
            "correct": False,
            "message": "Chưa có câu hỏi hiện tại.",
        }


    result = check_answer(
        question,
        answer
    )


    if not isinstance(
        result,
        dict
    ):

        result = {
            "correct": False,
            "message": "Không xử lý được đáp án.",
        }


    # ========================================================
    # ĐÚNG
    # ========================================================

    if result.get(
        "correct"
    ) is True:

        session["correct"] = (
            session.get(
                "correct",
                0
            ) + 1
        )

        session["current_question_answered"] = True


        print()

        print(
            f"🌸 Đúng rồi {nickname}!"
        )


        explanation = safe_get(
            result,
            "explanation",
            ""
        )

        if explanation:

            print(
                explanation
            )


        return result


    # ========================================================
    # SAI
    # ========================================================

    session["wrong"] = (
        session.get(
            "wrong",
            0
        ) + 1
    )


    session["hints"] = (
        session.get(
            "hints",
            0
        ) + 1
    )


    print()

    print(
        f"💗 Không sao đâu {nickname}, "
        f"mình thử lại nha."
    )


    hint = safe_get(
        result,
        "hint",
        safe_get(
            question,
            "hint",
            "Con thử suy nghĩ thêm một chút nhé."
        )
    )


    print(
        f"💡 Gợi ý: {hint}"
    )


    return result


# ============================================================
# SAU KHI TRẢ LỜI ĐÚNG
#
# TIỂU VŨ KHÔNG CHỜ LÃO SƯ.
#
# TỰ ĐỘNG TẠO CÂU HỎI TIẾP THEO.
# ============================================================

def continue_lesson(
    session
):

    # --------------------------------------------------------
    # Chỉ tiếp tục khi câu hiện tại đã được trả lời.
    # --------------------------------------------------------

    if not session.get(
        "current_question_answered",
        False
    ):

        return None


    # --------------------------------------------------------
    # TẠO CÂU HỎI MỚI
    # --------------------------------------------------------

    question = create_next_question(
        session
    )


    # --------------------------------------------------------
    # CHỦ ĐỘNG ĐƯA RA
    # --------------------------------------------------------

    present_question(
        session,
        question
    )


    return question


# ============================================================
# BẮT ĐẦU PHIÊN GIA SƯ
# ============================================================

def start_tutor_session(
    command,
    student_id="nha_tien",
    current_session=None
):

    # ========================================================
    # KIỂM TRA COMMAND
    # ========================================================

    if not isinstance(
        command,
        dict
    ):

        return None


    if command.get(
        "intent"
    ) != "start_lesson":

        return None


    # ========================================================
    # LẤY SESSION CŨ NẾU CÓ
    # ========================================================

    if isinstance(
        current_session,
        dict
    ):

        session = current_session

    else:

        subject_id = resolve_subject(
            command
        )

        session = create_lesson_session(
            student_id,
            subject_id
        )


    # ========================================================
    # XÁC ĐỊNH HỌC SINH
    # ========================================================

    nickname = resolve_student(
        command,
        get_student(
            session
        )
    )


    # ========================================================
    # CỰC KỲ QUAN TRỌNG:
    #
    # KHÓA NGAY TÊN HỌC SINH.
    #
    # TỪ ĐÂY TRỞ ĐI KHÔNG ĐƯỢC ĐỔI.
    # ========================================================

    lock_student(
        session,
        nickname
    )


    # ========================================================
    # XÁC ĐỊNH MÔN
    # ========================================================

    subject = resolve_subject(
        command,
        get_subject(
            session
        )
    )


    lock_subject(
        session,
        subject
    )


    # ========================================================
    # ĐÁNH DẤU CHẾ ĐỘ GIA SƯ
    # ========================================================

    session["mode"] = "tutor"

    session["tutor_mode"] = True

    session["lesson_active"] = True

    session["waiting_for_student"] = False


    # ========================================================
    # CHÀO ĐÚNG HỌC SINH
    # ========================================================

    print()
    print("=" * 60)

    print(
        f"🎓 TIỂU VŨ - CHẾ ĐỘ GIA SƯ"
    )

    print("=" * 60)

    print()

    print(
        f"💗 Tiểu Vũ: Chào {nickname} nha!"
    )

    print(
        f"Hôm nay mình học cùng nhau nè."
    )

    print(
        f"📚 Môn học: {subject}"
    )


    # ========================================================
    # QUAN TRỌNG:
    #
    # KHÔNG ĐỢI LÃO SƯ.
    #
    # BẬT GIA SƯ XONG -> TẠO CÂU HỎI NGAY.
    # ========================================================

    question = create_next_question(
        session
    )


    # ========================================================
    # ĐƯA CÂU HỎI RA NGAY
    # ========================================================

    present_question(
        session,
        question
    )


    return session


# ============================================================
# XỬ LÝ MỘT CÂU TRẢ LỜI
# ============================================================

def handle_student_answer(
    session,
    answer
):

    if not isinstance(
        session,
        dict
    ):

        return None


    if not session.get(
        "tutor_mode",
        False
    ):

        return None


    # --------------------------------------------------------
    # LẤY TÊN ĐÃ KHÓA
    # --------------------------------------------------------

    nickname = get_student(
        session
    )


    print()

    print(
        f"🎤 {nickname}: {answer}"
    )


    # --------------------------------------------------------
    # CHẤM ĐÁP ÁN
    # --------------------------------------------------------

    result = process_answer(
        session,
        answer
    )


    # ========================================================
    # ĐÚNG
    #
    # TỰ ĐỘNG SANG CÂU MỚI.
    # ========================================================

    if result.get(
        "correct"
    ) is True:

        continue_lesson(
            session
        )


    # ========================================================
    # SAI
    #
    # CHƯA sang câu mới.
    #
    # Học sinh có thể trả lời lại.
    # ========================================================

    else:

        session["waiting_for_student"] = True


    return result


# ============================================================
# PHÂN TÍCH VOICE COMMAND
#
# Hàm này là cầu nối:
#
# VOICE
#   ↓
# transcript
#   ↓
# tutor_trigger
#   ↓
# tutor_session_controller
# ============================================================

def handle_voice_text(
    text,
    current_session=None,
    student_id="nha_tien"
):

    # --------------------------------------------------------
    # Không có trigger
    # --------------------------------------------------------

    if detect_tutor_command is None:

        print(
            "⚠️ Không import được tutor_trigger."
        )

        return current_session


    # --------------------------------------------------------
    # PHÂN TÍCH CÂU NÓI
    # --------------------------------------------------------

    command = detect_tutor_command(
        text
    )


    print()

    print(
        "VOICE COMMAND:"
    )

    print(
        command
    )


    # ========================================================
    # NẾU LÀ LỆNH HỌC
    # ========================================================

    if command.get(
        "intent"
    ) == "start_lesson":

        return start_tutor_session(

            command,

            student_id=student_id,

            current_session=current_session,

        )


    # ========================================================
    # CHAT BÌNH THƯỜNG
    # ========================================================

    return current_session


# ============================================================
# KẾT THÚC SESSION
# ============================================================

def end_tutor_session(
    session
):

    if not isinstance(
        session,
        dict
    ):

        return


    nickname = get_student(
        session
    )


    session["lesson_active"] = False

    session["tutor_mode"] = False

    session["mode"] = "chat"


    finish_session(
        session
    )


    print()

    print("=" * 60)

    print(
        f"🌸 Buổi học của {nickname} đã hoàn tất."
    )


    print(
        get_session_summary(
            session
        )
    )

    print("=" * 60)


# ============================================================
# TEST TRỰC TIẾP
# ============================================================

def demo():

    print()
    print("=" * 70)
    print("TIỂU VŨ - TUTOR SESSION CONTROLLER V3")
    print("=" * 70)


    # ========================================================
    # TEST 1 - MINI
    # ========================================================

    print()
    print("TEST 1: MINI")
    print("-" * 70)


    command = {
        "intent": "start_lesson",
        "nickname": "Mini",
        "subject": "math",
        "text": "Mini muốn học Toán",
    }


    session = start_tutor_session(
        command,
        student_id="nha_tien"
    )


    print()

    print(
        "Tên đang khóa:",
        get_student(
            session
        )
    )


    # ========================================================
    # TEST 2 - ĐẬU PHỘNG
    # ========================================================

    print()
    print()
    print("TEST 2: ĐẬU PHỘNG")
    print("-" * 70)


    command = {
        "intent": "start_lesson",
        "nickname": "Đậu Phộng",
        "subject": "math",
        "text": "Đậu Phộng muốn học Toán",
    }


    session = start_tutor_session(
        command,
        student_id="nha_tien"
    )


    print()

    print(
        "Tên đang khóa:",
        get_student(
            session
        )
    )


    # ========================================================
    # TEST 3 - ĐẬU ĐẬU
    # ========================================================

    print()
    print()
    print("TEST 3: ĐẬU ĐẬU")
    print("-" * 70)


    command = {
        "intent": "start_lesson",
        "nickname": "Đậu Đậu",
        "subject": "math",
        "text": "Đậu Đậu muốn học Toán",
    }


    session = start_tutor_session(
        command,
        student_id="nha_tien"
    )


    print()

    print(
        "Tên đang khóa:",
        get_student(
            session
        )
    )


    # ========================================================
    # TEST HOÀN TẤT
    # ========================================================

    print()
    print("=" * 70)
    print("TEST HOÀN TẤT")
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        demo()

    except KeyboardInterrupt:

        print()
        print(
            "Tiểu Vũ tạm dừng."
        )

    except Exception as error:

        print()
        print("=" * 70)
        print("RUNTIME ERROR")
        print("=" * 70)

        print(
            type(error).__name__,
            ":",
            error
        )