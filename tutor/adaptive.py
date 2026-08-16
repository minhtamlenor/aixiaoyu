# ============================================================
# TIỂU VŨ - ADAPTIVE LEARNING ENGINE
# LỘ TRÌNH THÍCH ỨNG THEO LỚP + TIẾN ĐỘ
# ============================================================

from tutor.progress import get_progress_summary
from tutor.curriculum import get_subject, get_curriculum
from tutor.students import get_grade, get_chinese_level

STRATEGY_NAMES = {
    "introduce": "Giới thiệu",
    "review": "Ôn lại nền tảng",
    "practice": "Luyện tập",
    "advance": "Nâng cao",
}

STRATEGY_DESCRIPTIONS = {
    "introduce": "Giới thiệu kiến thức mới bằng ví dụ đơn giản, trực quan.",
    "review": "Quay lại nền tảng và sửa đúng điểm chưa vững.",
    "practice": "Luyện tập có hướng dẫn và vận dụng vào tình huống.",
    "advance": "Tăng độ khó, yêu cầu suy luận và giải thích cách nghĩ.",
}

MIN_QUESTIONS_FOR_DECISION = 3
HIGH_ACCURACY = 85.0
MEDIUM_ACCURACY = 70.0
LOW_ACCURACY = 50.0
QUESTIONS_PER_TOPIC = 5


def determine_strategy(summary):
    questions = summary.get("questions", 0)
    accuracy = summary.get("accuracy", 0.0)
    wrong = summary.get("wrong", 0)
    if questions < MIN_QUESTIONS_FOR_DECISION:
        return "introduce"
    if accuracy < LOW_ACCURACY:
        return "review"
    if accuracy < MEDIUM_ACCURACY:
        return "review"
    if accuracy < HIGH_ACCURACY:
        return "practice"
    if wrong == 0:
        return "advance"
    return "practice"


def determine_next_strategy(summary, answer_correct=None):
    questions = summary.get("questions", 0)
    accuracy = summary.get("accuracy", 0.0)
    if answer_correct is False:
        return "review"
    if answer_correct is True:
        if accuracy >= HIGH_ACCURACY and questions >= 3:
            return "advance"
        return "practice"
    return determine_strategy(summary)


def get_recommended_topic(summary, student_id=None, subject_id=None):
    weaknesses = summary.get("weaknesses", [])
    if weaknesses:
        return weaknesses[0]

    if not student_id or not subject_id:
        return summary.get("recommended_topic") or "introduction"

    grade = get_grade(student_id)
    chinese_level = get_chinese_level(student_id) if subject_id == "chinese" else None
    roadmap = get_curriculum(grade, subject_id, chinese_level)
    if not roadmap:
        return "introduction"

    # Mỗi chủ đề có một cụm câu hỏi. Khi học sinh đã đi qua cụm đó,
    # Tiểu Vũ chuyển sang chủ đề kế tiếp thay vì random vô hạn.
    questions = summary.get("questions", 0)
    index = min(questions // QUESTIONS_PER_TOPIC, len(roadmap) - 1)
    return roadmap[index]


def create_learning_plan(student_id, subject_id):
    subject = get_subject(subject_id)
    if not subject:
        raise ValueError(f"Không tìm thấy môn học: {subject_id}")

    summary = get_progress_summary(student_id, subject_id)
    strategy = determine_strategy(summary)
    topic = get_recommended_topic(summary, student_id, subject_id)
    grade = get_grade(student_id)
    chinese_level = get_chinese_level(student_id) if subject_id == "chinese" else None
    roadmap = get_curriculum(grade, subject_id, chinese_level)
    topic_index = roadmap.index(topic) + 1 if topic in roadmap else 1

    return {
        "student_id": student_id,
        "subject_id": subject_id,
        "subject_name": subject["name"],
        "grade": grade,
        "chinese_level": chinese_level,
        "level": summary.get("level", "elementary"),
        "topic": topic,
        "topic_index": topic_index,
        "topic_total": len(roadmap),
        "roadmap": roadmap,
        "strategy": strategy,
        "strategy_name": STRATEGY_NAMES[strategy],
        "strategy_description": STRATEGY_DESCRIPTIONS[strategy],
        "step": 1,
        "max_steps": 10,
        "accuracy": summary.get("accuracy", 0.0),
        "questions": summary.get("questions", 0),
        "strengths": summary.get("strengths", []),
        "weaknesses": summary.get("weaknesses", []),
        "status": "ready",
    }


def get_next_strategy(student_id, subject_id, answer_correct=None):
    summary = get_progress_summary(student_id, subject_id)
    strategy = determine_next_strategy(summary, answer_correct)
    return {
        "strategy": strategy,
        "strategy_name": STRATEGY_NAMES[strategy],
        "strategy_description": STRATEGY_DESCRIPTIONS[strategy],
        "accuracy": summary.get("accuracy", 0.0),
        "questions": summary.get("questions", 0),
        "status": "ready",
    }


def get_strategy_instruction(strategy):
    return STRATEGY_DESCRIPTIONS.get(strategy, STRATEGY_DESCRIPTIONS["practice"])


if __name__ == "__main__":
    plan = create_learning_plan("nha_tien", "math")
    print("TIỂU VŨ - ADAPTIVE LEARNING ENGINE")
    print(plan)
