# ============================================================
# TIỂU VŨ - ADAPTIVE LEARNING ENGINE
# BỘ NÃO THÍCH NGHI
# ============================================================

from tutor.progress import get_progress_summary
from tutor.curriculum import get_subject


# ============================================================
# TÊN CHIẾN LƯỢC
# ============================================================

STRATEGY_NAMES = {
    "introduce": "Giới thiệu",
    "review": "Ôn lại nền tảng",
    "practice": "Luyện tập",
    "advance": "Nâng cao",
}


# ============================================================
# MÔ TẢ CHIẾN LƯỢC
# ============================================================

STRATEGY_DESCRIPTIONS = {
    "introduce": (
        "Giới thiệu kiến thức bằng ví dụ đơn giản, "
        "trực quan và dễ hiểu."
    ),

    "review": (
        "Quay lại kiến thức nền tảng, "
        "tìm chỗ trẻ chưa hiểu và giải thích theo cách khác."
    ),

    "practice": (
        "Cho trẻ luyện tập qua câu hỏi, "
        "trò chơi, ví dụ và tình huống thực tế."
    ),

    "advance": (
        "Tăng độ khó, thêm suy luận, "
        "thử thách và yêu cầu trẻ giải thích cách suy nghĩ."
    ),
}


# ============================================================
# NGƯỠNG ĐÁNH GIÁ
# ============================================================

MIN_QUESTIONS_FOR_DECISION = 3

HIGH_ACCURACY = 85.0
MEDIUM_ACCURACY = 70.0
LOW_ACCURACY = 50.0


# ============================================================
# XÁC ĐỊNH CHIẾN LƯỢC
# ============================================================

def determine_strategy(summary):
    """
    Xác định chiến lược học tiếp theo
    dựa trên tiến độ của học sinh.
    """

    questions = summary.get("questions", 0)
    accuracy = summary.get("accuracy", 0.0)
    wrong = summary.get("wrong", 0)

    # --------------------------------------------------------
    # Chưa đủ dữ liệu
    # --------------------------------------------------------

    if questions < MIN_QUESTIONS_FOR_DECISION:

        return "introduce"

    # --------------------------------------------------------
    # Kết quả thấp
    # --------------------------------------------------------

    if accuracy < LOW_ACCURACY:

        return "review"

    # --------------------------------------------------------
    # Kết quả trung bình
    # --------------------------------------------------------

    if accuracy < MEDIUM_ACCURACY:

        return "review"

    # --------------------------------------------------------
    # Có tiến bộ nhưng chưa chắc
    # --------------------------------------------------------

    if accuracy < HIGH_ACCURACY:

        return "practice"

    # --------------------------------------------------------
    # Kết quả cao
    # --------------------------------------------------------

    if accuracy >= HIGH_ACCURACY:

        if wrong == 0:

            return "advance"

        return "practice"

    return "practice"


# ============================================================
# XÁC ĐỊNH CHIẾN LƯỢC THEO KẾT QUẢ CÂU VỪA LÀM
# ============================================================

def determine_next_strategy(
    summary,
    answer_correct=None,
):
    """
    Xác định chiến lược tiếp theo.

    answer_correct:
        True  = trả lời đúng
        False = trả lời sai
        None  = chưa có câu trả lời mới
    """

    questions = summary.get("questions", 0)
    accuracy = summary.get("accuracy", 0.0)

    # --------------------------------------------------------
    # Nếu vừa trả lời sai
    # --------------------------------------------------------

    if answer_correct is False:

        return "review"

    # --------------------------------------------------------
    # Nếu vừa trả lời đúng
    # --------------------------------------------------------

    if answer_correct is True:

        if accuracy >= HIGH_ACCURACY and questions >= 3:

            return "advance"

        return "practice"

    # --------------------------------------------------------
    # Chưa có kết quả mới
    # --------------------------------------------------------

    return determine_strategy(summary)


# ============================================================
# CHỦ ĐỀ ĐỀ XUẤT
# ============================================================

def get_recommended_topic(summary):
    """
    Chọn chủ đề nên học tiếp.
    """

    recommended = summary.get(
        "recommended_topic"
    )

    if recommended:

        return recommended

    weaknesses = summary.get(
        "weaknesses",
        []
    )

    if weaknesses:

        return weaknesses[0]

    strengths = summary.get(
        "strengths",
        []
    )

    if strengths:

        return strengths[0]

    return "introduction"


# ============================================================
# TẠO KẾ HOẠCH HỌC
# ============================================================

def create_learning_plan(
    student_id,
    subject_id,
):

    subject = get_subject(subject_id)

    if not subject:

        raise ValueError(
            f"Không tìm thấy môn học: {subject_id}"
        )

    summary = get_progress_summary(
        student_id,
        subject_id,
    )

    strategy = determine_strategy(
        summary
    )

    topic = get_recommended_topic(
        summary
    )

    return {

        "student_id": student_id,

        "subject_id": subject_id,

        "subject_name": subject["name"],

        "level": summary.get(
            "level",
            "elementary"
        ),

        "topic": topic,

        "strategy": strategy,

        "strategy_name": STRATEGY_NAMES[
            strategy
        ],

        "strategy_description": (
            STRATEGY_DESCRIPTIONS[
                strategy
            ]
        ),

        "step": 1,

        "max_steps": 10,

        "accuracy": summary.get(
            "accuracy",
            0.0
        ),

        "questions": summary.get(
            "questions",
            0
        ),

        "strengths": summary.get(
            "strengths",
            []
        ),

        "weaknesses": summary.get(
            "weaknesses",
            []
        ),

        "status": "ready",
    }


# ============================================================
# LẤY CHIẾN LƯỢC TIẾP THEO
# ============================================================

def get_next_strategy(
    student_id,
    subject_id,
    answer_correct=None,
):

    summary = get_progress_summary(
        student_id,
        subject_id,
    )

    strategy = determine_next_strategy(
        summary,
        answer_correct,
    )

    return {

        "strategy": strategy,

        "strategy_name": STRATEGY_NAMES[
            strategy
        ],

        "strategy_description": (
            STRATEGY_DESCRIPTIONS[
                strategy
            ]
        ),

        "accuracy": summary.get(
            "accuracy",
            0.0
        ),

        "questions": summary.get(
            "questions",
            0
        ),

        "status": "ready",
    }


# ============================================================
# MÔ TẢ CHO AI
# ============================================================

def get_strategy_instruction(strategy):

    return STRATEGY_DESCRIPTIONS.get(
        strategy,
        STRATEGY_DESCRIPTIONS["practice"]
    )


# ============================================================
# KIỂM TRA NHANH
# ============================================================

if __name__ == "__main__":

    student_id = "nha_tien"
    subject_id = "math"

    print()
    print("=" * 60)
    print("TIỂU VŨ - ADAPTIVE LEARNING ENGINE")
    print("=" * 60)

    plan = create_learning_plan(
        student_id,
        subject_id,
    )

    print()
    print("KẾ HOẠCH")
    print(plan)

    print()
    print("SAU KHI TRẢ LỜI ĐÚNG")
    print(
        get_next_strategy(
            student_id,
            subject_id,
            True,
        )
    )

    print()
    print("SAU KHI TRẢ LỜI SAI")
    print(
        get_next_strategy(
            student_id,
            subject_id,
            False,
        )
    )

    print()
    print("=" * 60)