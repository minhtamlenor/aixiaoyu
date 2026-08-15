# ============================================================
# TIỂU VŨ - LESSON BRAIN
# BỘ NÃO QUYẾT ĐỊNH CÁCH DẠY
# ============================================================

from tutor.adaptive import create_learning_plan


# ============================================================
# CHIẾN LƯỢC
# ============================================================

STRATEGIES = {
    "introduce": {
        "name": "Giới thiệu",
        "description": (
            "Giới thiệu kiến thức bằng ví dụ đơn giản, "
            "trực quan và gần gũi."
        ),
    },

    "review": {
        "name": "Ôn nền tảng",
        "description": (
            "Quay lại kiến thức nền tảng bằng cách nhẹ nhàng, "
            "không làm trẻ cảm thấy mình đang bị học lại."
        ),
    },

    "practice": {
        "name": "Luyện tập",
        "description": (
            "Cho trẻ luyện tập qua câu hỏi, ví dụ, "
            "trò chơi và tình huống thực tế."
        ),
    },

    "advance": {
        "name": "Nâng cao",
        "description": (
            "Tăng độ khó và khuyến khích trẻ giải thích "
            "cách suy nghĩ của mình."
        ),
    },
}


# ============================================================
# CHỦ ĐỀ TOÁN
# ============================================================

MATH_TOPICS = [
    "mental_math",
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "word_problem",
    "geometry",
    "measurement",
    "logic",
    "reasoning",
]


# ============================================================
# TẠO BỘ NÃO CHO MỘT BUỔI HỌC
# ============================================================

def create_lesson_brain(student_id, subject_id):

    plan = create_learning_plan(
        student_id,
        subject_id,
    )

    strategy = plan.get(
        "strategy",
        "introduce",
    )

    topic = plan.get(
        "topic",
        "general",
    )

    return {
        "student_id": student_id,
        "subject_id": subject_id,
        "subject_name": plan.get(
            "subject_name",
            subject_id,
        ),
        "level": plan.get(
            "level",
            "elementary",
        ),
        "topic": topic,
        "strategy": strategy,
        "strategy_name": STRATEGIES.get(
            strategy,
            STRATEGIES["introduce"],
        )["name"],
        "accuracy": plan.get(
            "accuracy",
            0,
        ),
        "questions": plan.get(
            "questions",
            0,
        ),
        "strengths": plan.get(
            "strengths",
            [],
        ),
        "weaknesses": plan.get(
            "weaknesses",
            [],
        ),
        "reason": plan.get(
            "reason",
            "",
        ),
        "step": 1,
        "max_steps": 10,
        "status": "ready",
    }


# ============================================================
# XÁC ĐỊNH HOẠT ĐỘNG TIẾP THEO
# ============================================================

def get_next_activity(brain):

    strategy = brain["strategy"]
    step = brain["step"]

    # --------------------------------------------------------
    # GIỚI THIỆU
    # --------------------------------------------------------

    if strategy == "introduce":

        if step == 1:
            return "warm_up"

        if step == 2:
            return "example"

        if step == 3:
            return "question"

        return "practice"


    # --------------------------------------------------------
    # ÔN TẬP
    # --------------------------------------------------------

    if strategy == "review":

        if step == 1:
            return "review_example"

        if step == 2:
            return "question"

        if step == 3:
            return "hint"

        return "practice"


    # --------------------------------------------------------
    # LUYỆN TẬP
    # --------------------------------------------------------

    if strategy == "practice":

        if step % 4 == 1:
            return "question"

        if step % 4 == 2:
            return "example"

        if step % 4 == 3:
            return "question"

        return "game"


    # --------------------------------------------------------
    # NÂNG CAO
    # --------------------------------------------------------

    if strategy == "advance":

        if step == 1:
            return "challenge"

        if step == 2:
            return "reasoning"

        if step == 3:
            return "question"

        return "challenge"


    return "question"


# ============================================================
# TĂNG BƯỚC
# ============================================================

def advance_brain(brain):

    brain["step"] += 1

    if brain["step"] > brain["max_steps"]:
        brain["status"] = "completed"

    return brain


# ============================================================
# PHẢN ỨNG KHI TRẺ TRẢ LỜI ĐÚNG
# ============================================================

def handle_correct_answer(brain):

    brain["last_result"] = "correct"

    if brain["strategy"] == "introduce":

        if brain["step"] >= 3:
            brain["strategy"] = "practice"

    elif brain["strategy"] == "practice":

        if brain["step"] >= 6:
            brain["strategy"] = "advance"

    elif brain["strategy"] == "review":

        brain["strategy"] = "practice"

    return advance_brain(brain)


# ============================================================
# PHẢN ỨNG KHI TRẺ TRẢ LỜI SAI
# ============================================================

def handle_wrong_answer(brain):

    brain["last_result"] = "wrong"

    # Không tăng độ khó khi trẻ đang gặp khó khăn.

    if brain["strategy"] == "advance":

        brain["strategy"] = "practice"

    elif brain["strategy"] == "practice":

        brain["strategy"] = "review"

    elif brain["strategy"] == "introduce":

        brain["strategy"] = "review"

    return advance_brain(brain)


# ============================================================
# PHẢN ỨNG KHI TRẺ CẦN GỢI Ý
# ============================================================

def handle_hint(brain):

    brain["last_result"] = "hint"

    brain["hint_used"] = (
        brain.get("hint_used", 0) + 1
    )

    return advance_brain(brain)


# ============================================================
# KIỂM TRA BUỔI HỌC
# ============================================================

def is_completed(brain):

    return brain.get(
        "status"
    ) == "completed"


# ============================================================
# TÓM TẮT BỘ NÃO
# ============================================================

def get_brain_summary(brain):

    return {
        "student_id": brain["student_id"],
        "subject_id": brain["subject_id"],
        "subject_name": brain["subject_name"],
        "topic": brain["topic"],
        "strategy": brain["strategy"],
        "strategy_name": brain["strategy_name"],
        "step": brain["step"],
        "max_steps": brain["max_steps"],
        "accuracy": brain["accuracy"],
        "questions": brain["questions"],
        "strengths": brain["strengths"],
        "weaknesses": brain["weaknesses"],
        "status": brain["status"],
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("TIỂU VŨ - LESSON BRAIN TEST")
    print("=" * 60)

    brain = create_lesson_brain(
        "nha_tien",
        "math",
    )

    print()
    print("BỘ NÃO BAN ĐẦU")
    print("-" * 60)
    print(get_brain_summary(brain))

    print()
    print("HOẠT ĐỘNG")

    for _ in range(5):

        activity = get_next_activity(brain)

        print(
            f"Step {brain['step']}: {activity}"
        )

        advance_brain(brain)

    print()
    print("TEST TRẢ LỜI ĐÚNG")

    brain = create_lesson_brain(
        "nha_tien",
        "math",
    )

    handle_correct_answer(brain)

    print(
        get_brain_summary(brain)
    )

    print()
    print("TEST TRẢ LỜI SAI")

    brain = create_lesson_brain(
        "nha_tien",
        "math",
    )

    handle_wrong_answer(brain)

    print(
        get_brain_summary(brain)
    )

    print()
    print("TEST HOÀN TẤT")