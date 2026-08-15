# ============================================================
# TIỂU VŨ - ACTIVITY ENGINE
# BỘ ĐIỀU KHIỂN HOẠT ĐỘNG HỌC
# ============================================================

from tutor.content import (
    create_lesson_content,
    get_activity,
)

from tutor.adaptive import (
    get_next_strategy,
)

from tutor.progress import (
    record_correct,
    record_wrong,
)


# ============================================================
# TRẠNG THÁI
# ============================================================

STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"


# ============================================================
# TẠO HOẠT ĐỘNG
# ============================================================

def create_activity_session(
    student_id,
    subject_id,
    topic,
    strategy="introduce",
):

    lesson = create_lesson_content(
        subject_id,
        topic,
        strategy,
    )

    return {
        "student_id": student_id,
        "subject_id": subject_id,
        "topic": topic,
        "strategy": strategy,
        "strategy_name": lesson["strategy_name"],
        "current_step": 1,
        "total_steps": lesson["total_steps"],
        "lesson": lesson,
        "status": STATUS_ACTIVE,
        "correct": 0,
        "wrong": 0,
        "hints": 0,
    }


# ============================================================
# LẤY HOẠT ĐỘNG HIỆN TẠI
# ============================================================

def get_current_activity(session):

    if not session:
        return None

    step = session.get(
        "current_step",
        1,
    )

    lesson = session.get(
        "lesson"
    )

    if not lesson:
        return None

    return get_activity(
        lesson,
        step,
    )


# ============================================================
# TIẾN TỚI BƯỚC TIẾP THEO
# ============================================================

def next_activity(session):

    if not session:
        return None

    current_step = session.get(
        "current_step",
        1,
    )

    total_steps = session.get(
        "total_steps",
        0,
    )

    if current_step >= total_steps:

        session["status"] = STATUS_COMPLETED

        return None

    session["current_step"] = (
        current_step + 1
    )

    return get_current_activity(
        session
    )


# ============================================================
# GHI NHẬN TRẢ LỜI ĐÚNG
# ============================================================

def answer_correct(
    session,
):

    if not session:
        return None

    session["correct"] += 1

    record_correct(
        session["student_id"],
        session["subject_id"],
        session["topic"],
    )

    return next_activity(
        session
    )


# ============================================================
# GHI NHẬN TRẢ LỜI SAI
# ============================================================

def answer_wrong(
    session,
):

    if not session:
        return None

    session["wrong"] += 1

    record_wrong(
        session["student_id"],
        session["subject_id"],
        session["topic"],
    )

    return next_activity(
        session
    )


# ============================================================
# GỢI Ý
# ============================================================

def use_hint(session):

    if not session:
        return None

    session["hints"] += 1

    return {
        "type": "hint",
        "message": (
            "Đưa cho học sinh một gợi ý nhỏ "
            "mà chưa tiết lộ đáp án."
        ),
        "step": session.get(
            "current_step",
            1,
        ),
    }


# ============================================================
# THỬ LẠI
# ============================================================

def retry_activity(session):

    if not session:
        return None

    return get_current_activity(
        session
    )


# ============================================================
# CHUYỂN CHIẾN LƯỢC
# ============================================================

def change_strategy(
    session,
    strategy,
):

    if not session:
        return None

    session["strategy"] = strategy

    session["lesson"] = create_lesson_content(
        session["subject_id"],
        session["topic"],
        strategy,
    )

    session["strategy_name"] = (
        session["lesson"]["strategy_name"]
    )

    session["current_step"] = 1

    session["total_steps"] = (
        session["lesson"]["total_steps"]
    )

    session["status"] = STATUS_ACTIVE

    return get_current_activity(
        session
    )


# ============================================================
# TỰ ĐIỀU CHỈNH SAU CÂU TRẢ LỜI
# ============================================================

def adapt_after_answer(
    session,
    answer_correct_value,
):

    if not session:
        return None

    strategy_data = get_next_strategy(
        session["student_id"],
        session["subject_id"],
        answer_correct_value,
    )

    next_strategy = strategy_data[
        "strategy"
    ]

    current_strategy = session.get(
        "strategy",
        "introduce",
    )

    # --------------------------------------------------------
    # Nếu cần đổi chiến lược
    # --------------------------------------------------------

    if next_strategy != current_strategy:

        return change_strategy(
            session,
            next_strategy,
        )

    # --------------------------------------------------------
    # Nếu vẫn giữ chiến lược
    # --------------------------------------------------------

    if answer_correct_value is True:

        return answer_correct(
            session
        )

    if answer_correct_value is False:

        return answer_wrong(
            session
        )

    return get_current_activity(
        session
    )


# ============================================================
# HOÀN THÀNH BUỔI HỌC
# ============================================================

def complete_session(session):

    if not session:
        return None

    session["status"] = STATUS_COMPLETED

    return {
        "student_id": session[
            "student_id"
        ],
        "subject_id": session[
            "subject_id"
        ],
        "topic": session[
            "topic"
        ],
        "strategy": session[
            "strategy"
        ],
        "correct": session[
            "correct"
        ],
        "wrong": session[
            "wrong"
        ],
        "hints": session[
            "hints"
        ],
        "status": session[
            "status"
        ],
    }


# ============================================================
# TÓM TẮT BUỔI HỌC
# ============================================================

def get_activity_summary(session):

    if not session:

        return {}

    total = (
        session["correct"]
        + session["wrong"]
    )

    if total > 0:

        accuracy = round(
            session["correct"]
            / total
            * 100,
            1,
        )

    else:

        accuracy = 0.0

    return {

        "student_id": session[
            "student_id"
        ],

        "subject_id": session[
            "subject_id"
        ],

        "topic": session[
            "topic"
        ],

        "strategy": session[
            "strategy"
        ],

        "strategy_name": session[
            "strategy_name"
        ],

        "current_step": session[
            "current_step"
        ],

        "total_steps": session[
            "total_steps"
        ],

        "correct": session[
            "correct"
        ],

        "wrong": session[
            "wrong"
        ],

        "hints": session[
            "hints"
        ],

        "accuracy": accuracy,

        "status": session[
            "status"
        ],
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("TIỂU VŨ - ACTIVITY ENGINE")
    print("=" * 60)

    session = create_activity_session(
        "nha_tien",
        "math",
        "addition",
        "introduce",
    )

    print()
    print("HOẠT ĐỘNG BAN ĐẦU")
    print(
        get_current_activity(
            session
        )
    )

    print()
    print("DÙNG GỢI Ý")
    print(
        use_hint(session)
    )

    print()
    print("TRẢ LỜI ĐÚNG")

    activity = adapt_after_answer(
        session,
        True,
    )

    print(activity)

    print()
    print("TÓM TẮT")

    print(
        get_activity_summary(
            session
        )
    )

    print()
    print("=" * 60)