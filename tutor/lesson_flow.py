# ============================================================
# TIỂU VŨ - LESSON FLOW V2
# VOICE + KEYBOARD + SESSION NICKNAME
# TUTOR MODE READY
#
# LUỒNG:
#
# Voice
#   ↓
# Tutor Trigger
#   ↓
# start_lesson()
#   ↓
# tạo Session
#   ↓
# tạo câu hỏi đầu tiên
#   ↓
# trả câu hỏi cho Voice
#   ↓
# Tiểu Vũ chủ động nói câu hỏi
# ============================================================


import os
import sys
from datetime import datetime


# ============================================================
# PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ============================================================
# IMPORT
# ============================================================

from tutor.lesson_manager import (
    create_lesson_session,
    get_greeting,
    get_emotion_question,
    create_warmup,
    finish_session,
    get_session_summary,
)

from tutor.question_engine import (
    generate_question,
    check_answer,
)


# ============================================================
# TIỆN ÍCH
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
# XÁC ĐỊNH TÊN GỌI CỦA PHIÊN
# ============================================================

def resolve_session_nickname(
    session,
    nickname=None
):

    existing = safe_get(
        session,
        "nickname",
        None
    )

    if (
        isinstance(existing, str)
        and existing.strip()
    ):

        return existing.strip()


    if (
        isinstance(nickname, str)
        and nickname.strip()
    ):

        session["nickname"] = (
            nickname.strip()
        )

        return session["nickname"]


    profile_nickname = safe_get(
        session,
        "student_nickname",
        None
    )

    if (
        isinstance(profile_nickname, str)
        and profile_nickname.strip()
    ):

        session["nickname"] = (
            profile_nickname.strip()
        )

        return session["nickname"]


    student_name = safe_get(
        session,
        "student_name",
        None
    )

    if (
        isinstance(student_name, str)
        and student_name.strip()
    ):

        session["nickname"] = (
            student_name.strip()
        )

        return session["nickname"]


    # --------------------------------------------------------
    # KHÔNG ĐƯỢC TỰ Ý ĐỔI SANG MINI NẾU ĐÃ CÓ TÊN
    # --------------------------------------------------------

    session["nickname"] = "Mini"

    return "Mini"


# ============================================================
# KHÓA TÊN GỌI CHO PHIÊN
# ============================================================

def lock_session_nickname(
    session,
    nickname
):

    if (
        not isinstance(
            nickname,
            str
        )
        or not nickname.strip()
    ):

        nickname = "Mini"


    nickname = nickname.strip()

    session["nickname"] = nickname

    session["nickname_locked"] = True

    return nickname


# ============================================================
# LẤY TÊN GỌI HIỆN TẠI
# ============================================================

def get_session_nickname(
    session
):

    nickname = safe_get(
        session,
        "nickname",
        None
    )

    if (
        isinstance(nickname, str)
        and nickname.strip()
    ):

        return nickname.strip()

    return "Mini"


# ============================================================
# GHI NHẬN CÂU HỎI
# ============================================================

def register_question(
    session
):

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

    subject_id = safe_get(
        session,
        "subject_id",
        "math"
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
    # LƯU CÂU HỎI HIỆN TẠI
    # --------------------------------------------------------

    session["current_question"] = (
        question
    )

    session["question_topic"] = safe_get(
        question,
        "topic",
        topic
    )

    register_question(
        session
    )

    return question


# ============================================================
# HIỂN THỊ CÂU HỎI
# ============================================================

def show_question(
    session,
    question
):

    nickname = get_session_nickname(
        session
    )

    print()
    print("CÂU HỎI")
    print("-" * 60)

    print(
        f"{nickname} ơi, "
        f"{safe_get(question, 'question', 'Không có câu hỏi.')}"
    )


# ============================================================
# HƯỚNG DẪN TRẢ LỜI
# ============================================================

def show_answer_input(
    session
):

    nickname = get_session_nickname(
        session
    )

    print()
    print("TRẢ LỜI")
    print("-" * 60)

    print(
        f"🎤 {nickname} cứ nói đáp án tự nhiên."
    )

    print(
        "⌨️ Hoặc gõ đáp án rồi nhấn Enter."
    )

    print(
        "💡 Tiểu Vũ sẽ tiếp nhận cả Voice và Keyboard."
    )


# ============================================================
# NHẬP BÀN PHÍM
# ============================================================

def get_keyboard_answer(
    session
):

    nickname = get_session_nickname(
        session
    )

    print()

    try:

        answer = input(
            f"{nickname} trả lời: "
        )

    except EOFError:

        return ""

    return answer.strip()


# ============================================================
# HIỂN THỊ GỢI Ý
# ============================================================

def show_hint(
    session,
    question
):

    nickname = get_session_nickname(
        session
    )

    print()
    print("GỢI Ý")
    print("-" * 60)

    print(
        f"{nickname} thử suy nghĩ từng bước một nha."
    )

    print(
        safe_get(
            question,
            "hint",
            "Con thử suy nghĩ thêm một chút nhé."
        )
    )


# ============================================================
# XỬ LÝ CÂU TRẢ LỜI
# ============================================================

def process_answer(
    session,
    question,
    answer
):

    nickname = get_session_nickname(
        session
    )

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
            "message": (
                "Tiểu Vũ chưa xử lý được câu trả lời này."
            ),
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

        print()
        print("TEST ĐÚNG")
        print("-" * 60)

        print(
            f"Đúng rồi {nickname}! "
            f"Con tự tìm ra đáp án đó!"
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
    print("TEST SAI")
    print("-" * 60)

    print(
        f"Không sao đâu {nickname}. "
        f"Mình thử lại một chút nha."
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
        f"Gợi ý: {hint}"
    )

    return result


# ============================================================
# TÍNH ĐỘ CHÍNH XÁC
# ============================================================

def calculate_accuracy(
    session
):

    questions = session.get(
        "questions",
        0
    )

    correct = session.get(
        "correct",
        0
    )

    if questions <= 0:

        return 0.0

    return round(
        (
            correct / questions
        ) * 100,
        1
    )


# ============================================================
# CẬP NHẬT ĐỘ CHÍNH XÁC
# ============================================================

def update_session_accuracy(
    session
):

    session["session_accuracy"] = (
        calculate_accuracy(
            session
        )
    )


# ============================================================
# CHÀO BẮT ĐẦU PHIÊN
# ============================================================

def show_session_start(
    session
):

    nickname = get_session_nickname(
        session
    )

    print()
    print("KHỞI ĐỘNG PHIÊN HỌC")
    print("-" * 60)

    print(
        f"Chào {nickname} nha! "
        f"Tiểu Vũ tới giờ học rồi nè."
    )

    print(
        f"Hôm nay {nickname} sẽ học cùng Tiểu Vũ."
    )


# ============================================================
# ============================================================
# ⭐ API CHÍNH CHO VOICE
# BẮT ĐẦU BUỔI HỌC NGAY LẬP TỨC
# ============================================================
# ============================================================

def start_lesson(
    student_id="nha_tien",
    subject_id="math",
    nickname=None,
):
    """
    API để voice.py gọi khi phát hiện:

        "Mini muốn học Toán"

    hoặc:

        "Đậu Phộng muốn học Toán"

    Hàm này KHÔNG chờ người dùng nhập gì.

    Nó sẽ:

        1. Tạo session
        2. Khóa nickname
        3. Xác định môn học
        4. Tạo câu hỏi đầu tiên
        5. Lưu câu hỏi hiện tại
        6. Trả session + question về cho Voice

    Voice sau đó sẽ tự đọc câu hỏi cho học sinh.
    """


    # ========================================================
    # TẠO SESSION
    # ========================================================

    session = create_lesson_session(
        student_id,
        subject_id
    )


    # ========================================================
    # KHÓA HỌC SINH
    # ========================================================

    nickname = resolve_session_nickname(
        session,
        nickname
    )

    lock_session_nickname(
        session,
        nickname
    )


    # ========================================================
    # ĐÁNH DẤU TUTOR MODE
    # ========================================================

    session["tutor_mode"] = True

    session["status"] = (
        "active"
    )

    session["voice_enabled"] = True

    session["keyboard_enabled"] = True


    # ========================================================
    # GHI THÔNG TIN BẮT ĐẦU
    # ========================================================

    session["started_at"] = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    # ========================================================
    # TẠO CÂU HỎI ĐẦU TIÊN
    # ========================================================

    question = create_next_question(
        session
    )


    # ========================================================
    # LƯU TRẠNG THÁI CHỜ TRẢ LỜI
    # ========================================================

    session["waiting_for_answer"] = True


    # ========================================================
    # TRẢ VỀ CHO VOICE
    # ========================================================

    return {
        "session": session,

        "question": question,

        "nickname": get_session_nickname(
            session
        ),

        "subject": safe_get(
            session,
            "subject_id",
            subject_id
        ),

        "tutor_mode": True,

        "waiting_for_answer": True,
    }


# ============================================================
# ⭐ TẠO CÂU HỎI TIẾP THEO CHO VOICE
# ============================================================

def next_lesson_question(
    session
):
    """
    Được gọi sau khi học sinh đã trả lời
    câu hỏi hiện tại.

    Không cần tạo session mới.
    """

    if not isinstance(
        session,
        dict
    ):

        raise ValueError(
            "Session không hợp lệ."
        )


    # --------------------------------------------------------
    # Tạo câu hỏi mới
    # --------------------------------------------------------

    question = create_next_question(
        session
    )


    # --------------------------------------------------------
    # Tiếp tục chờ trả lời
    # --------------------------------------------------------

    session["waiting_for_answer"] = True


    return question


# ============================================================
# ⭐ XỬ LÝ TRẢ LỜI TỪ VOICE HOẶC KEYBOARD
# ============================================================

def answer_current_question(
    session,
    answer
):
    """
    Nhận câu trả lời từ:

        🎤 Voice

    hoặc:

        ⌨️ Keyboard

    Sau đó kiểm tra đúng / sai.
    """

    if not isinstance(
        session,
        dict
    ):

        raise ValueError(
            "Session không hợp lệ."
        )


    question = safe_get(
        session,
        "current_question",
        None
    )


    if not isinstance(
        question,
        dict
    ):

        raise ValueError(
            "Không có câu hỏi hiện tại."
        )


    # ========================================================
    # KIỂM TRA
    # ========================================================

    result = process_answer(
        session,
        question,
        answer
    )


    # ========================================================
    # ĐÃ TRẢ LỜI
    # ========================================================

    session["waiting_for_answer"] = False


    # ========================================================
    # TRẢ KẾT QUẢ
    # ========================================================

    return {
        "result": result,

        "correct": result.get(
            "correct",
            False
        ),

        "question": question,

        "nickname": get_session_nickname(
            session
        ),

        "session": session,
    }


# ============================================================
# ⭐ TẠO PAYLOAD ĐỂ TIỂU VŨ NÓI
# ============================================================

def build_question_speech(
    session,
    question
):
    """
    Chuyển câu hỏi thành câu Tiểu Vũ nói.

    Voice.py chỉ cần lấy kết quả này
    và gửi cho Gemini Live.
    """

    nickname = get_session_nickname(
        session
    )

    question_text = safe_get(
        question,
        "question",
        ""
    )


    return (
        f"{nickname} ơi, "
        f"{question_text}"
    )


# ============================================================
# ⭐ TẠO PHẢN HỒI SAU KHI TRẢ LỜI
# ============================================================

def build_answer_speech(
    session,
    result
):

    nickname = get_session_nickname(
        session
    )


    if result.get(
        "correct"
    ):

        explanation = safe_get(
            result,
            "explanation",
            ""
        )

        if explanation:

            return (
                f"Đúng rồi {nickname}! "
                f"{explanation}"
            )

        return (
            f"Đúng rồi {nickname}! "
            f"Giỏi lắm nha."
        )


    hint = safe_get(
        result,
        "hint",
        ""
    )

    if hint:

        return (
            f"Không sao đâu {nickname}. "
            f"Mình thử lại nha. "
            f"{hint}"
        )


    return (
        f"Không sao đâu {nickname}. "
        f"Mình thử lại một chút nha."
    )


# ============================================================
# DEMO BUỔI HỌC
# DÙNG ĐỂ TEST LESSON FLOW ĐỘC LẬP
# ============================================================

def run_demo(
    student_id="nha_tien",
    subject_id="math",
    nickname=None
):

    print()
    print("=" * 60)
    print("          TIỂU VŨ - LESSON FLOW V2")
    print("          TUTOR MODE")
    print("=" * 60)


    # ========================================================
    # START LESSON
    # ========================================================

    lesson = start_lesson(
        student_id=student_id,
        subject_id=subject_id,
        nickname=nickname,
    )


    session = lesson["session"]

    question = lesson["question"]

    nickname = lesson["nickname"]


    # ========================================================
    # SESSION
    # ========================================================

    print()
    print("SESSION")
    print("-" * 60)

    print(
        f"Học sinh: {nickname}"
    )

    print(
        f"Môn học: {lesson['subject']}"
    )

    print(
        "Tutor Mode: ON"
    )

    print(
        "Nickname: LOCKED"
    )


    # ========================================================
    # CHÀO
    # ========================================================

    show_session_start(
        session
    )


    # ========================================================
    # CÂU HỎI ĐẦU TIÊN
    # ========================================================

    print()
    print("TẠO CÂU HỎI")
    print("-" * 60)

    print(
        question
    )


    show_question(
        session,
        question
    )


    show_answer_input(
        session
    )


    # ========================================================
    # DEMO ĐÚNG
    # ========================================================

    correct_answer = safe_get(
        question,
        "answer"
    )


    answer_current_question(
        session,
        correct_answer
    )


    # ========================================================
    # CÂU HỎI TIẾP THEO
    # ========================================================

    print()
    print("TẠO CÂU HỎI TIẾP THEO")
    print("-" * 60)


    question2 = next_lesson_question(
        session
    )


    print(
        question2
    )


    show_question(
        session,
        question2
    )


    show_answer_input(
        session
    )


    # ========================================================
    # DEMO SAI
    # ========================================================

    correct_answer2 = safe_get(
        question2,
        "answer"
    )


    if isinstance(
        correct_answer2,
        (int, float)
    ):

        wrong_answer = (
            correct_answer2 + 1
        )

    else:

        wrong_answer = "__sai__"


    answer_current_question(
        session,
        wrong_answer
    )


    # ========================================================
    # CẬP NHẬT
    # ========================================================

    update_session_accuracy(
        session
    )


    # ========================================================
    # KẾT THÚC
    # ========================================================

    finish_session(
        session
    )


    # ========================================================
    # KẾT QUẢ
    # ========================================================

    print()
    print("KẾT THÚC BUỔI HỌC")
    print("-" * 60)

    print(
        get_session_summary(
            session
        )
    )


    print()
    print(
        f"🌸 Buổi học của {nickname} đã hoàn tất."
    )


    print()
    print("=" * 60)
    print("TEST HOÀN TẤT")
    print("=" * 60)


    return session


# ============================================================
# TEST MINI
# ============================================================

def test_mini():

    print()
    print("=" * 60)
    print("TEST SESSION: MINI")
    print("=" * 60)


    run_demo(
        student_id="nha_tien",
        subject_id="math",
        nickname="Mini"
    )


# ============================================================
# TEST ĐẬU PHỘNG
# ============================================================

def test_dau_phong():

    print()
    print("=" * 60)
    print("TEST SESSION: ĐẬU PHỘNG")
    print("=" * 60)


    run_demo(
        student_id="nha_tien",
        subject_id="math",
        nickname="Đậu Phộng"
    )


# ============================================================
# TEST ĐẬU ĐẬU
# ============================================================

def test_dau_dau():

    print()
    print("=" * 60)
    print("TEST SESSION: ĐẬU ĐẬU")
    print("=" * 60)


    run_demo(
        student_id="nha_tien",
        subject_id="math",
        nickname="Đậu Đậu"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    run_demo(
        student_id="nha_tien",
        subject_id="math",
        nickname="Mini"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "Tiểu Vũ tạm dừng."
        )

    except Exception as error:

        print()
        print("=" * 60)
        print("RUNTIME ERROR")
        print("=" * 60)

        print(
            type(error).__name__,
            ":",
            error
        )