# ============================================================
# TIỂU VŨ - LESSON MANAGER
# QUẢN LÝ MỘT BUỔI HỌC
# ============================================================

import sys
import os
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

from tutor.students import (
    get_student,
    get_nickname,
)

from tutor.curriculum import get_subject

from tutor.adaptive import (
    create_learning_plan,
    get_next_strategy,
)

from tutor.progress import (
    record_correct,
    record_wrong,
    record_hint,
    record_activity,
)

from tutor.question_engine import (
    generate_question,
    check_answer,
)


# ============================================================
# THÔNG TIN
# ============================================================

TUTOR_NAME = "Tiểu Vũ"


STRATEGY_NAMES = {
    "introduce": "Giới thiệu",
    "review": "Ôn lại nền tảng",
    "practice": "Luyện tập",
    "advance": "Nâng cao",
}


# ============================================================
# HÀM AN TOÀN
# ============================================================

def safe_get(data, key, default=None):

    if not isinstance(data, dict):
        return default

    return data.get(key, default)


# ============================================================
# TẠO SESSION ID
# ============================================================

def create_session_id(student_id, subject_id):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    return (
        f"{student_id}_"
        f"{subject_id}_"
        f"{timestamp}"
    )


# ============================================================
# TẠO BUỔI HỌC
# ============================================================

def create_lesson_session(student_id, subject_id):

    student = get_student(student_id)

    if not student:
        raise ValueError(
            f"Không tìm thấy học sinh: {student_id}"
        )

    subject = get_subject(subject_id)

    if not subject:
        raise ValueError(
            f"Không tìm thấy môn học: {subject_id}"
        )

    plan = create_learning_plan(
        student_id,
        subject_id,
    )

    strategy = safe_get(
        plan,
        "strategy",
        "introduce",
    )

    nickname = get_nickname(student_id)

    return {
        "session_id": create_session_id(
            student_id,
            subject_id,
        ),

        "student_id": student_id,

        "student_name": safe_get(
            student,
            "name",
            "Học sinh",
        ),

        "nickname": nickname,

        "subject_id": subject_id,

        "subject_name": safe_get(
            subject,
            "name",
            subject_id,
        ),

        "topic": safe_get(
            plan,
            "topic",
            "introduction",
        ),

        "strategy": strategy,

        "strategy_name": safe_get(
            plan,
            "strategy_name",
            STRATEGY_NAMES.get(
                strategy,
                strategy,
            ),
        ),

        "level": safe_get(
            plan,
            "level",
            "elementary",
        ),

        "accuracy": safe_get(
            plan,
            "accuracy",
            0,
        ),

        "questions": 0,
        "correct": 0,
        "wrong": 0,
        "hints": 0,
        "activities": 0,

        "emotion": "unknown",
        "engagement": "unknown",

        "status": "active",

        "step": 0,

        "current_question": None,
        "question_topic": None,

        "started_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "ended_at": None,
    }


# ============================================================
# LỜI CHÀO
# ============================================================

def get_greeting(session):

    nickname = safe_get(
        session,
        "nickname",
        "con",
    )

    subject = safe_get(
        session,
        "subject_name",
        "bài học",
    )

    return (
        f"Chào {nickname} nha! "
        f"Tiểu Vũ tới rồi nè. "
        f"Hôm nay mình học {subject} "
        f"một chút thật vui nha."
    )


# ============================================================
# KIỂM TRA CẢM XÚC
# ============================================================

def get_emotion_question(session):

    nickname = safe_get(
        session,
        "nickname",
        "con",
    )

    return (
        f"{nickname} ơi, trước khi học, "
        "con thấy hôm nay mình đang vui, "
        "bình thường, hơi mệt hay hơi buồn nè?"
    )


# ============================================================
# KHỞI ĐỘNG
# ============================================================

def create_warmup(session):

    subject_id = safe_get(
        session,
        "subject_id",
        "",
    )

    topic = safe_get(
        session,
        "topic",
        "introduction",
    )

    if subject_id == "math":

        if topic == "addition":

            return {
                "type": "warm_up",
                "topic": "addition",
                "question": (
                    "Có 2 quả táo, "
                    "mẹ cho thêm 3 quả. "
                    "Con có tất cả bao nhiêu quả?"
                ),
            }

        return {
            "type": "warm_up",
            "topic": topic,
            "question": (
                "Tiểu Vũ hỏi con một câu "
                "nhẹ nhẹ để khởi động nha."
            ),
        }

    if subject_id == "vietnamese":

        return {
            "type": "warm_up",
            "topic": topic,
            "question": (
                "Con hãy kể cho Tiểu Vũ "
                "một câu ngắn về ngày hôm nay."
            ),
        }

    if subject_id == "english":

        return {
            "type": "warm_up",
            "topic": topic,
            "question": (
                "Can you tell Tiểu Vũ "
                "how you feel today?"
            ),
        }

    if subject_id == "chinese":

        return {
            "type": "warm_up",
            "topic": topic,
            "question": "你今天感觉怎么样？",
        }

    return {
        "type": "warm_up",
        "topic": topic,
        "question": (
            "Con đã sẵn sàng chưa? "
            "Mình bắt đầu nhẹ nhàng nha."
        ),
    }


# ============================================================
# TẠO CÂU HỎI
# ============================================================

def create_question(session):

    strategy = safe_get(
        session,
        "strategy",
        "practice",
    )

    topic = safe_get(
        session,
        "topic",
        "addition",
    )

    subject_id = safe_get(
        session,
        "subject_id",
        "math",
    )

    question_data = generate_question(
        subject_id=subject_id,
        topic=topic,
        strategy=strategy,
    )

    if not isinstance(question_data, dict):
        raise ValueError(
            "Question Engine không trả về câu hỏi hợp lệ."
        )

    session["current_question"] = question_data

    session["question_topic"] = safe_get(
        question_data,
        "topic",
        topic,
    )

    session["step"] += 1

    return question_data


# ============================================================
# LẤY CÂU HỎI HIỆN TẠI
# ============================================================

def get_current_question(session):

    return session.get(
        "current_question"
    )


# ============================================================
# GỢI Ý
# ============================================================

def give_hint(session):

    session["hints"] += 1

    record_hint(
        session["student_id"],
        session["subject_id"],
    )

    question = get_current_question(
        session
    )

    return safe_get(
        question,
        "hint",
        (
            "Con thử nghĩ xem "
            "mình đã biết điều gì "
            "trong câu hỏi này rồi nha."
        ),
    )


# ============================================================
# TRẢ LỜI
# ============================================================

def answer(session, user_answer):

    question = get_current_question(
        session
    )

    if not question:

        return {
            "correct": False,
            "message": (
                "Tiểu Vũ chưa có câu hỏi "
                "cho con nè."
            ),
        }

    expected_answer = question.get(
        "answer"
    )

    result = check_answer(
        user_answer,
        expected_answer,
    )

    topic = safe_get(
        question,
        "topic",
        session.get(
            "topic",
            "introduction",
        ),
    )

    session["questions"] += 1

    if result:

        session["correct"] += 1

        record_correct(
            session["student_id"],
            session["subject_id"],
            topic,
        )

        return {
            "correct": True,
            "message": (
                "Đúng rồi! "
                "Con tự tìm ra đáp án đó!"
            ),
            "explanation": safe_get(
                question,
                "explanation",
                "",
            ),
        }

    session["wrong"] += 1

    record_wrong(
        session["student_id"],
        session["subject_id"],
        topic,
    )

    return {
        "correct": False,
        "message": (
            "Không sao đâu. "
            "Mình thử suy nghĩ lại "
            "một chút nha."
        ),
        "hint": safe_get(
            question,
            "hint",
            "Con thử nghĩ lại từng bước nha.",
        ),
    }


# ============================================================
# ĐỘ CHÍNH XÁC
# ============================================================

def calculate_session_accuracy(session):

    questions = session.get(
        "questions",
        0,
    )

    if questions <= 0:
        return 0.0

    return round(
        (
            session["correct"]
            / questions
        ) * 100,
        1,
    )


# ============================================================
# THÊM HOẠT ĐỘNG
# ============================================================

def add_activity(
    session,
    activity_type,
    description="",
):

    session["activities"] += 1

    record_activity(
        session["student_id"],
        session["subject_id"],
        activity_type,
    )

    return {
        "type": activity_type,
        "description": description,
        "step": session["step"],
    }


# ============================================================
# ĐIỀU CHỈNH CHIẾN LƯỢC
# ============================================================

def update_strategy(
    session,
    answer_correct,
):

    next_plan = get_next_strategy(
        session["student_id"],
        session["subject_id"],
        answer_correct,
    )

    strategy = safe_get(
        next_plan,
        "strategy",
        session["strategy"],
    )

    session["strategy"] = strategy

    session["strategy_name"] = safe_get(
        next_plan,
        "strategy_name",
        STRATEGY_NAMES.get(
            strategy,
            strategy,
        ),
    )

    return next_plan


# ============================================================
# KẾT THÚC BUỔI HỌC
# ============================================================

def finish_session(session):

    session["status"] = "completed"

    session["ended_at"] = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    session["accuracy"] = (
        calculate_session_accuracy(
            session
        )
    )

    session["current_question"] = None

    return session


# ============================================================
# TÓM TẮT
# ============================================================

def get_session_summary(session):

    return {
        "session_id": session.get(
            "session_id"
        ),

        "student": session.get(
            "student_name"
        ),

        "nickname": session.get(
            "nickname"
        ),

        "subject": session.get(
            "subject_name"
        ),

        "topic": session.get(
            "topic"
        ),

        "strategy": session.get(
            "strategy"
        ),

        "level": session.get(
            "level"
        ),

        "questions": session.get(
            "questions",
            0,
        ),

        "correct": session.get(
            "correct",
            0,
        ),

        "wrong": session.get(
            "wrong",
            0,
        ),

        "hints": session.get(
            "hints",
            0,
        ),

        "activities": session.get(
            "activities",
            0,
        ),

        "accuracy": calculate_session_accuracy(
            session
        ),

        "emotion": session.get(
            "emotion",
            "unknown",
        ),

        "engagement": session.get(
            "engagement",
            "unknown",
        ),

        "status": session.get(
            "status"
        ),

        "started_at": session.get(
            "started_at"
        ),

        "ended_at": session.get(
            "ended_at"
        ),
    }


# ============================================================
# DEMO
# ============================================================

def demo():

    print()
    print("=" * 60)
    print("          TIỂU VŨ - LESSON MANAGER")
    print("=" * 60)

    session = create_lesson_session(
        "nha_tien",
        "math",
    )

    print()
    print("SESSION")
    print("-" * 60)
    print(session)

    print()
    print("LỜI CHÀO")
    print("-" * 60)
    print(
        get_greeting(session)
    )

    print()
    print("KIỂM TRA CẢM XÚC")
    print("-" * 60)
    print(
        get_emotion_question(
            session
        )
    )

    print()
    print("KHỞI ĐỘNG")
    print("-" * 60)
    print(
        create_warmup(session)
    )

    print()
    print("TẠO CÂU HỎI")
    print("-" * 60)

    question = create_question(
        session
    )

    print(question)

    print()
    print("GỢI Ý")
    print("-" * 60)

    print(
        give_hint(session)
    )

    print()
    print("TEST ĐÚNG")
    print("-" * 60)

    correct_answer = question.get(
        "answer"
    )

    result = answer(
        session,
        correct_answer,
    )

    print(result)

    update_strategy(
        session,
        True,
    )

    print()
    print("CHIẾN LƯỢC TIẾP THEO")
    print("-" * 60)

    print(
        session["strategy"],
        "-",
        session["strategy_name"],
    )

    print()
    print("TEST SAI")
    print("-" * 60)

    question = create_question(
        session
    )

    result = answer(
        session,
        "__wrong_answer__",
    )

    print(result)

    update_strategy(
        session,
        False,
    )

    print()
    print("CHIẾN LƯỢC SAU KHI SAI")
    print("-" * 60)

    print(
        session["strategy"],
        "-",
        session["strategy_name"],
    )

    print()
    print("KẾT THÚC BUỔI HỌC")
    print("-" * 60)

    finish_session(
        session
    )

    print(
        get_session_summary(
            session
        )
    )

    print()
    print("=" * 60)
    print("TEST HOÀN TẤT")
    print("=" * 60)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        demo()

    except KeyboardInterrupt:

        print()
        print("Tiểu Vũ tạm dừng.")

    except Exception as error:

        print()
        print("=" * 60)
        print("RUNTIME ERROR")
        print("=" * 60)

        print(
            type(error).__name__,
            ":",
            error,
        )