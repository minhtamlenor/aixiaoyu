# ============================================================
# TIỂU VŨ - SESSION ENGINE
# Quản lý một buổi học của từng học sinh
# ============================================================

from datetime import datetime

from tutor.students import (
    get_student,
    get_student_name,
    get_nickname,
)

from tutor.curriculum import (
    get_subject,
)


# ============================================================
# TẠO SESSION ID
# ============================================================

def create_session_id(student_id, subject_id):
    """
    Tạo mã phiên học.
    """

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

def create_session(student_id, subject_id):
    """
    Tạo một buổi học mới.
    """

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

    nickname = get_nickname(student_id)

    session = {
        "session_id": create_session_id(
            student_id,
            subject_id,
        ),

        "student_id": student_id,

        "student_name": student["name"],

        "nickname": nickname,

        "gender": student["gender"],

        "birth_date": student["birth_date"],

        "subject_id": subject_id,

        "subject_name": subject["name"],

        "started_at": datetime.now().isoformat(),

        "status": "started",

        # ----------------------------------------------------
        # THỐNG KÊ BUỔI HỌC
        # ----------------------------------------------------

        "questions_asked": 0,

        "correct_answers": 0,

        "wrong_answers": 0,

        "hints_used": 0,

        "activities_completed": 0,

        # ----------------------------------------------------
        # TRẠNG THÁI HỌC TẬP
        # ----------------------------------------------------

        "current_topic": None,

        "current_level": "elementary",

        "last_question": None,

        "last_answer": None,

        "last_result": None,

        # ----------------------------------------------------
        # CẢM XÚC / TƯƠNG TÁC
        # ----------------------------------------------------

        "engagement": "unknown",

        "emotion": "unknown",

        "needs_encouragement": False,

        # ----------------------------------------------------
        # GHI CHÚ
        # ----------------------------------------------------

        "notes": [],
    }

    return session


# ============================================================
# CẬP NHẬT THỐNG KÊ
# ============================================================

def record_question(session):
    """
    Ghi nhận một câu hỏi đã được đưa ra.
    """

    session["questions_asked"] += 1

    return session


def record_correct(session):
    """
    Ghi nhận câu trả lời đúng.
    """

    session["correct_answers"] += 1

    session["last_result"] = "correct"

    session["needs_encouragement"] = False

    return session


def record_wrong(session):
    """
    Ghi nhận câu trả lời sai.
    """

    session["wrong_answers"] += 1

    session["last_result"] = "wrong"

    session["needs_encouragement"] = True

    return session


def record_hint(session):
    """
    Ghi nhận học sinh đã sử dụng gợi ý.
    """

    session["hints_used"] += 1

    return session


def record_activity(session):
    """
    Ghi nhận một hoạt động hoàn thành.
    """

    session["activities_completed"] += 1

    return session


# ============================================================
# CẬP NHẬT CÂU HỎI
# ============================================================

def set_question(
    session,
    question,
):
    """
    Lưu câu hỏi hiện tại.
    """

    session["last_question"] = question

    return session


# ============================================================
# CẬP NHẬT CÂU TRẢ LỜI
# ============================================================

def set_answer(
    session,
    answer,
):
    """
    Lưu câu trả lời của học sinh.
    """

    session["last_answer"] = answer

    return session


# ============================================================
# CẬP NHẬT CHỦ ĐỀ
# ============================================================

def set_topic(
    session,
    topic,
):
    """
    Đặt chủ đề đang học.
    """

    session["current_topic"] = topic

    return session


# ============================================================
# CẬP NHẬT CẤP ĐỘ
# ============================================================

def set_level(
    session,
    level,
):
    """
    Đặt cấp độ bài học.
    """

    session["current_level"] = level

    return session


# ============================================================
# CẢM XÚC
# ============================================================

def set_emotion(
    session,
    emotion,
):
    """
    Lưu trạng thái cảm xúc quan sát được.
    """

    session["emotion"] = emotion

    return session


def set_engagement(
    session,
    engagement,
):
    """
    Lưu mức độ hứng thú/tham gia.
    """

    session["engagement"] = engagement

    return session


# ============================================================
# GHI CHÚ
# ============================================================

def add_note(
    session,
    note,
):
    """
    Thêm ghi chú cho buổi học.
    """

    if note:
        session["notes"].append(note)

    return session


# ============================================================
# KẾT THÚC SESSION
# ============================================================

def finish_session(session):
    """
    Kết thúc buổi học.
    """

    session["status"] = "completed"

    session["finished_at"] = (
        datetime.now().isoformat()
    )

    return session


# ============================================================
# TỶ LỆ ĐÚNG
# ============================================================

def get_accuracy(session):
    """
    Tính tỷ lệ trả lời đúng.
    """

    total = session["questions_asked"]

    if total <= 0:
        return 0.0

    correct = session["correct_answers"]

    return round(
        (correct / total) * 100,
        2,
    )


# ============================================================
# THỐNG KÊ SESSION
# ============================================================

def get_session_summary(session):
    """
    Trả về thống kê ngắn gọn.
    """

    return {
        "session_id": session["session_id"],

        "student": session["nickname"],

        "subject": session["subject_name"],

        "questions": session["questions_asked"],

        "correct": session["correct_answers"],

        "wrong": session["wrong_answers"],

        "hints": session["hints_used"],

        "accuracy": get_accuracy(session),

        "activities": (
            session["activities_completed"]
        ),

        "emotion": session["emotion"],

        "engagement": session["engagement"],

        "status": session["status"],
    }


# ============================================================
# LỜI CHÀO BUỔI HỌC
# ============================================================

def get_greeting(session):
    """
    Tạo lời chào ban đầu cho Tiểu Vũ.
    """

    name = session["nickname"]

    subject = session["subject_name"]

    greetings = [

        f"Chào {name} nha! Hôm nay mình cùng học {subject} nhé.",

        f"Hello {name}! Tiểu Vũ tới rồi nè. Mình học {subject} một chút nha.",

        f"Aaa, {name} tới rồi! Hôm nay mình khám phá {subject} nha.",

        f"Chào {name}! Sẵn sàng chưa? Tiểu Vũ có một buổi học {subject} thú vị dành cho con nè.",

        f"{name} ơi, hôm nay mình thử một điều mới trong {subject} nha!",

    ]

    # Chọn lời chào dựa trên thời điểm
    index = datetime.now().second % len(greetings)

    return greetings[index]


# ============================================================
# THÔNG TIN HỌC SINH
# ============================================================

def get_session_student(session):
    """
    Lấy thông tin học sinh từ session.
    """

    return get_student(
        session["student_id"]
    )


# ============================================================
# KIỂM TRA SESSION
# ============================================================

def validate_session(session):
    """
    Kiểm tra session có hợp lệ không.
    """

    required_fields = [

        "session_id",

        "student_id",

        "student_name",

        "nickname",

        "subject_id",

        "subject_name",

        "status",

    ]

    for field in required_fields:

        if field not in session:

            return False

    return True