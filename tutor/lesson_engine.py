# ============================================================
# TIỂU VŨ - LESSON ENGINE
# HỆ THỐNG BÀI HỌC
# ============================================================

from tutor.students import get_student
from tutor.curriculum import get_subject


# ============================================================
# TRẠNG THÁI HỌC TẬP
# ============================================================

LEVEL_BEGINNER = "beginner"
LEVEL_ELEMENTARY = "elementary"
LEVEL_ADVANCED = "advanced"


# ============================================================
# TẠO PHIÊN HỌC
# ============================================================

def create_lesson(
    student_id,
    subject_id,
    level=LEVEL_ELEMENTARY,
):

    student = get_student(student_id)
    subject = get_subject(subject_id)

    if not student:
        raise ValueError(
            f"Không tìm thấy học sinh: {student_id}"
        )

    if not subject:
        raise ValueError(
            f"Không tìm thấy môn học: {subject_id}"
        )

    return {
        "student_id": student_id,
        "student_name": student["name"],

        "subject_id": subject_id,
        "subject_name": subject["name"],

        "level": level,

        "questions_asked": 0,
        "correct_answers": 0,
        "wrong_answers": 0,

        "hints_used": 0,

        "status": "started",
    }


# ============================================================
# GHI NHẬN CÂU TRẢ LỜI
# ============================================================

def record_answer(
    lesson,
    correct,
    used_hint=False,
):

    lesson["questions_asked"] += 1

    if correct:
        lesson["correct_answers"] += 1
    else:
        lesson["wrong_answers"] += 1

    if used_hint:
        lesson["hints_used"] += 1

    return lesson


# ============================================================
# TÍNH ĐIỂM PHIÊN HỌC
# ============================================================

def calculate_score(lesson):

    total = lesson["questions_asked"]

    if total == 0:
        return 0

    correct = lesson["correct_answers"]

    return round(
        correct / total * 100
    )


# ============================================================
# ĐÁNH GIÁ PHIÊN HỌC
# ============================================================

def evaluate_lesson(lesson):

    score = calculate_score(lesson)

    if score >= 90:

        evaluation = "excellent"

    elif score >= 75:

        evaluation = "good"

    elif score >= 50:

        evaluation = "needs_practice"

    else:

        evaluation = "needs_support"


    return {
        "score": score,
        "evaluation": evaluation,
    }


# ============================================================
# ĐỀ XUẤT ĐỘ KHÓ TIẾP THEO
# ============================================================

def suggest_next_level(lesson):

    score = calculate_score(lesson)

    current = lesson["level"]

    if score >= 90:

        if current == LEVEL_BEGINNER:
            return LEVEL_ELEMENTARY

        if current == LEVEL_ELEMENTARY:
            return LEVEL_ADVANCED

        return LEVEL_ADVANCED


    if score < 50:

        if current == LEVEL_ADVANCED:
            return LEVEL_ELEMENTARY

        if current == LEVEL_ELEMENTARY:
            return LEVEL_BEGINNER

        return LEVEL_BEGINNER


    return current


# ============================================================
# TẠO TÓM TẮT PHIÊN HỌC
# ============================================================

def get_lesson_summary(lesson):

    evaluation = evaluate_lesson(
        lesson
    )

    next_level = suggest_next_level(
        lesson
    )

    return {

        "student": lesson["student_name"],

        "subject": lesson["subject_name"],

        "questions": lesson["questions_asked"],

        "correct": lesson["correct_answers"],

        "wrong": lesson["wrong_answers"],

        "hints": lesson["hints_used"],

        "score": evaluation["score"],

        "evaluation": evaluation["evaluation"],

        "next_level": next_level,
    }