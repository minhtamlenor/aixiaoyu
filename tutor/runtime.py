# ============================================================
# TIEU VU - TUTOR RUNTIME
# BO CHAY GIA SU
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

from tutor.students import get_student
from tutor.curriculum import get_subject
from tutor.progress import get_progress_summary
from tutor.adaptive import create_learning_plan
from tutor.lesson_manager import (
    create_lesson_session,
    get_greeting,
    get_emotion_question,
    create_warmup,
    get_session_summary,
)


# ============================================================
# TEN GIA SU
# ============================================================

TUTOR_NAME = "Tiểu Vũ"


# ============================================================
# HAM AN TOAN
# ============================================================

def safe_get(data, key, default=None):

    if not isinstance(data, dict):
        return default

    return data.get(
        key,
        default
    )


# ============================================================
# IN TIEU DE
# ============================================================

def print_header(title):

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


# ============================================================
# HIEN THI HOC SINH
# ============================================================

def show_student(student_id):

    student = get_student(
        student_id
    )

    if not student:

        print()
        print(
            "Không tìm thấy học sinh:",
            student_id
        )

        return None

    print_header(
        "HỒ SƠ HỌC SINH"
    )

    print(
        "Tên đầy đủ :",
        safe_get(
            student,
            "name",
            "unknown"
        )
    )

    print(
        "Tên gọi     :",
        safe_get(
            student,
            "nickname",
            safe_get(
                student,
                "name",
                "unknown"
            )
        )
    )

    print(
        "Giới tính   :",
        safe_get(
            student,
            "gender",
            "unknown"
        )
    )

    print(
        "Ngày sinh   :",
        safe_get(
            student,
            "birth_date",
            "unknown"
        )
    )

    return student


# ============================================================
# HIEN THI MON HOC
# ============================================================

def show_subject(subject_id):

    subject = get_subject(
        subject_id
    )

    if not subject:

        print()
        print(
            "Không tìm thấy môn học:",
            subject_id
        )

        return None

    print_header(
        "MÔN HỌC"
    )

    print(
        "Mã môn      :",
        subject_id
    )

    print(
        "Tên môn     :",
        safe_get(
            subject,
            "name",
            subject_id
        )
    )

    print(
        "Mục tiêu    :",
        safe_get(
            subject,
            "description",
            ""
        )
    )

    return subject


# ============================================================
# HIEN THI TIEN DO
# ============================================================

def show_progress(
    student_id,
    subject_id
):

    progress = get_progress_summary(
        student_id,
        subject_id
    )

    if not isinstance(
        progress,
        dict
    ):

        print()
        print(
            "Chưa có dữ liệu tiến độ."
        )

        return {}

    print_header(
        "TIẾN ĐỘ HỌC TẬP"
    )

    print(
        "Học sinh      :",
        safe_get(
            progress,
            "student",
            "unknown"
        )
    )

    print(
        "Môn           :",
        safe_get(
            progress,
            "subject",
            "unknown"
        )
    )

    print(
        "Số câu        :",
        safe_get(
            progress,
            "questions",
            0
        )
    )

    print(
        "Đúng          :",
        safe_get(
            progress,
            "correct",
            0
        )
    )

    print(
        "Sai           :",
        safe_get(
            progress,
            "wrong",
            0
        )
    )

    print(
        "Gợi ý         :",
        safe_get(
            progress,
            "hints",
            0
        )
    )

    print(
        "Độ chính xác  :",
        safe_get(
            progress,
            "accuracy",
            0
        ),
        "%"
    )

    print(
        "Điểm mạnh     :",
        safe_get(
            progress,
            "strengths",
            []
        )
    )

    print(
        "Điểm yếu      :",
        safe_get(
            progress,
            "weaknesses",
            []
        )
    )

    print(
        "Chủ đề đề xuất:",
        safe_get(
            progress,
            "recommended_topic",
            "unknown"
        )
    )

    print(
        "Cảm xúc       :",
        safe_get(
            progress,
            "emotion",
            "unknown"
        )
    )

    print(
        "Tập trung     :",
        safe_get(
            progress,
            "engagement",
            "unknown"
        )
    )

    return progress


# ============================================================
# TAO KE HOACH HOC
# ============================================================

def build_learning_plan(
    student_id,
    subject_id
):

    print_header(
        "ĐANG TẠO BỘ NÃO GIA SƯ..."
    )

    try:

        plan = create_learning_plan(
            student_id,
            subject_id
        )

    except Exception as error:

        print()
        print(
            "LỖI KHI TẠO KẾ HOẠCH:"
        )

        print(
            type(error).__name__,
            ":",
            error
        )

        return {
            "topic": "introduction",
            "strategy": "introduce",
            "strategy_name": "Giới thiệu",
            "accuracy": 0,
            "questions": 0,
            "strengths": [],
            "weaknesses": [],
            "reason": (
                "Bắt đầu bằng kiến thức nền tảng "
                "và quan sát cách trẻ học."
            ),
            "status": "ready",
        }

    if not isinstance(
        plan,
        dict
    ):

        return {
            "topic": "introduction",
            "strategy": "introduce",
            "strategy_name": "Giới thiệu",
            "accuracy": 0,
            "questions": 0,
            "strengths": [],
            "weaknesses": [],
            "reason": (
                "Bắt đầu bằng hoạt động khởi động."
            ),
            "status": "ready",
        }

    return plan


# ============================================================
# HIEN THI BO NAO
# ============================================================

def show_learning_plan(plan):

    print_header(
        "BỘ NÃO GIA SƯ"
    )

    topic = safe_get(
        plan,
        "topic",
        "unknown"
    )

    strategy = safe_get(
        plan,
        "strategy",
        "unknown"
    )

    strategy_names = {

        "introduce": "Giới thiệu",

        "review": "Ôn lại nền tảng",

        "practice": "Luyện tập",

        "advance": "Nâng cao",

    }

    strategy_name = safe_get(
        plan,
        "strategy_name",
        strategy_names.get(
            strategy,
            strategy
        )
    )

    accuracy = safe_get(
        plan,
        "accuracy",
        0
    )

    questions = safe_get(
        plan,
        "questions",
        0
    )

    strengths = safe_get(
        plan,
        "strengths",
        []
    )

    weaknesses = safe_get(
        plan,
        "weaknesses",
        []
    )

    reason = safe_get(
        plan,
        "reason",
        "Tiểu Vũ sẽ quan sát cách học của bé."
    )

    status = safe_get(
        plan,
        "status",
        "ready"
    )

    print(
        "Chủ đề        :",
        topic
    )

    print(
        "Chiến lược    :",
        strategy
    )

    print(
        "Tên chiến lược:",
        strategy_name
    )

    print(
        "Độ chính xác  :",
        accuracy,
        "%"
    )

    print(
        "Số câu        :",
        questions
    )

    print(
        "Điểm mạnh     :",
        strengths
    )

    print(
        "Điểm yếu      :",
        weaknesses
    )

    print(
        "Lý do         :",
        reason
    )

    print(
        "Trạng thái    :",
        status
    )

    return plan


# ============================================================
# TAO BUOI HOC
# ============================================================

def build_lesson(
    student_id,
    subject_id
):

    print_header(
        "KHỞI TẠO BUỔI HỌC"
    )

    try:

        session = create_lesson_session(
            student_id,
            subject_id
        )

    except Exception as error:

        print()
        print(
            "LỖI KHI TẠO BUỔI HỌC:"
        )

        print(
            type(error).__name__,
            ":",
            error
        )

        return None

    return session


# ============================================================
# HIEN THI BUOI HOC
# ============================================================

def show_lesson_start(
    session
):

    print_header(
        "TIỂU VŨ ĐÃ SẴN SÀNG"
    )

    print()

    print(
        get_greeting(
            session
        )
    )

    print()

    print(
        get_emotion_question(
            session
        )
    )

    print()

    warmup = create_warmup(
        session
    )

    print_header(
        "HOẠT ĐỘNG KHỞI ĐỘNG"
    )

    print(
        safe_get(
            warmup,
            "question",
            "Mình bắt đầu nha!"
        )
    )

    return warmup


# ============================================================
# TOM TAT
# ============================================================

def show_final_summary(
    session
):

    print_header(
        "TÓM TẮT BUỔI HỌC"
    )

    summary = get_session_summary(
        session
    )

    print(
        "Học sinh      :",
        safe_get(
            summary,
            "nickname",
            safe_get(
                summary,
                "student",
                "unknown"
            )
        )
    )

    print(
        "Môn           :",
        safe_get(
            summary,
            "subject",
            "unknown"
        )
    )

    print(
        "Chủ đề        :",
        safe_get(
            summary,
            "topic",
            "unknown"
        )
    )

    print(
        "Chiến lược    :",
        safe_get(
            summary,
            "strategy",
            "unknown"
        )
    )

    print(
        "Số câu        :",
        safe_get(
            summary,
            "questions",
            0
        )
    )

    print(
        "Đúng          :",
        safe_get(
            summary,
            "correct",
            0
        )
    )

    print(
        "Sai           :",
        safe_get(
            summary,
            "wrong",
            0
        )
    )

    print(
        "Gợi ý         :",
        safe_get(
            summary,
            "hints",
            0
        )
    )

    print(
        "Độ chính xác  :",
        safe_get(
            summary,
            "accuracy",
            0
        ),
        "%"
    )

    print(
        "Hoạt động     :",
        safe_get(
            summary,
            "activities",
            0
        )
    )

    print(
        "Trạng thái    :",
        safe_get(
            summary,
            "status",
            "unknown"
        )
    )

    return summary


# ============================================================
# CHAY MOT BUOI HOC
# ============================================================

def start_tutor(
    student_id,
    subject_id
):

    print()
    print("=" * 60)
    print("              TIỂU VŨ - GIA SƯ")
    print("=" * 60)

    print()

    print(
        "Thời gian:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    # --------------------------------------------------------
    # HOC SINH
    # --------------------------------------------------------

    student = show_student(
        student_id
    )

    if not student:
        return None

    # --------------------------------------------------------
    # MON HOC
    # --------------------------------------------------------

    subject = show_subject(
        subject_id
    )

    if not subject:
        return None

    # --------------------------------------------------------
    # TIEN DO
    # --------------------------------------------------------

    progress = show_progress(
        student_id,
        subject_id
    )

    # --------------------------------------------------------
    # BO NAO
    # --------------------------------------------------------

    plan = build_learning_plan(
        student_id,
        subject_id
    )

    show_learning_plan(
        plan
    )

    # --------------------------------------------------------
    # BUOI HOC
    # --------------------------------------------------------

    session = build_lesson(
        student_id,
        subject_id
    )

    if not session:
        return None

    # --------------------------------------------------------
    # KHOI DONG
    # --------------------------------------------------------

    warmup = show_lesson_start(
        session
    )

    # --------------------------------------------------------
    # THONG TIN NOI BO
    # --------------------------------------------------------

    print()

    print(
        "Tiểu Vũ đang chuẩn bị bài học..."
    )

    print(
        "Chủ đề:",
        safe_get(
            session,
            "topic",
            "unknown"
        )
    )

    print(
        "Chiến lược:",
        safe_get(
            session,
            "strategy",
            "unknown"
        )
    )

    print()

    print(
        "Tiểu Vũ sẽ không chỉ hỏi đáp."
    )

    print(
        "Tiểu Vũ sẽ xen kẽ:"
    )

    print(
        "- câu hỏi"
    )

    print(
        "- giải thích"
    )

    print(
        "- ví dụ"
    )

    print(
        "- trò chơi"
    )

    print(
        "- tình huống thực tế"
    )

    print(
        "- thử thách"
    )

    print()

    return {
        "student": student,
        "subject": subject,
        "progress": progress,
        "plan": plan,
        "session": session,
        "warmup": warmup,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    start_tutor(
        "nha_tien",
        "math"
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