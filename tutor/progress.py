# ============================================================
# TIỂU VŨ - PROGRESS ENGINE
# BỘ NHỚ TIẾN BỘ HỌC TẬP
# ============================================================

import json
import os
from datetime import datetime

from tutor.students import get_student
from tutor.curriculum import get_subject


# ============================================================
# FILE LƯU DỮ LIỆU
# ============================================================

DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data",
)

PROGRESS_FILE = os.path.join(
    DATA_DIR,
    "progress.json",
)


# ============================================================
# BỘ NHỚ TIẾN ĐỘ
# ============================================================

PROGRESS = {}


# ============================================================
# THỜI GIAN
# ============================================================

def now():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# ĐẢM BẢO THƯ MỤC DATA
# ============================================================

def ensure_data_directory():

    os.makedirs(
        DATA_DIR,
        exist_ok=True,
    )


# ============================================================
# LƯU FILE
# ============================================================

def save_progress():

    ensure_data_directory()

    with open(
        PROGRESS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            PROGRESS,
            file,
            ensure_ascii=False,
            indent=4,
        )


# ============================================================
# ĐỌC FILE
# ============================================================

def load_progress():

    global PROGRESS

    ensure_data_directory()

    if not os.path.exists(PROGRESS_FILE):

        PROGRESS = {}

        return PROGRESS

    try:

        with open(
            PROGRESS_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

            if isinstance(data, dict):

                PROGRESS = data

            else:

                PROGRESS = {}

    except (
        json.JSONDecodeError,
        OSError,
    ):

        PROGRESS = {}

    return PROGRESS


# ============================================================
# LOAD NGAY KHI MODULE ĐƯỢC IMPORT
# ============================================================

load_progress()


# ============================================================
# TẠO HỒ SƠ TIẾN ĐỘ
# ============================================================

def create_progress(
    student_id,
    subject_id,
):

    student = get_student(
        student_id
    )

    subject = get_subject(
        subject_id
    )

    if not student:

        raise ValueError(
            f"Không tìm thấy học sinh: {student_id}"
        )

    if not subject:

        raise ValueError(
            f"Không tìm thấy môn học: {subject_id}"
        )

    key = (
        f"{student_id}:{subject_id}"
    )

    if key not in PROGRESS:

        PROGRESS[key] = {

            "student_id":
                student_id,

            "student_name":
                student["name"],

            "nickname":
                student.get(
                    "nickname",
                    student["name"],
                ),

            "subject_id":
                subject_id,

            "subject_name":
                subject["name"],

            "questions":
                0,

            "correct":
                0,

            "wrong":
                0,

            "hints":
                0,

            "activities":
                0,

            "accuracy":
                0.0,

            "strengths":
                [],

            "weaknesses":
                [],

            "topics":
                {},

            "recent_lessons":
                [],

            "emotion":
                "unknown",

            "engagement":
                "unknown",

            "last_activity":
                None,

            "level":
                "elementary",
        }

        save_progress()

    return PROGRESS[key]


# ============================================================
# CẬP NHẬT ĐỘ CHÍNH XÁC
# ============================================================

def update_accuracy(progress):

    questions = progress["questions"]

    if questions <= 0:

        progress["accuracy"] = 0.0

        return

    progress["accuracy"] = round(
        (
            progress["correct"]
            / questions
        ) * 100,
        1,
    )


# ============================================================
# GHI NHẬN ĐÚNG
# ============================================================

def record_correct(
    student_id,
    subject_id,
    topic=None,
):

    progress = create_progress(
        student_id,
        subject_id,
    )

    progress["questions"] += 1

    progress["correct"] += 1

    if topic:

        if topic not in progress["topics"]:

            progress["topics"][topic] = {
                "questions": 0,
                "correct": 0,
                "wrong": 0,
            }

        progress["topics"][topic][
            "questions"
        ] += 1

        progress["topics"][topic][
            "correct"
        ] += 1

    update_accuracy(progress)

    progress["last_activity"] = now()

    save_progress()

    return progress


# ============================================================
# GHI NHẬN SAI
# ============================================================

def record_wrong(
    student_id,
    subject_id,
    topic=None,
):

    progress = create_progress(
        student_id,
        subject_id,
    )

    progress["questions"] += 1

    progress["wrong"] += 1

    if topic:

        if topic not in progress["topics"]:

            progress["topics"][topic] = {
                "questions": 0,
                "correct": 0,
                "wrong": 0,
            }

        progress["topics"][topic][
            "questions"
        ] += 1

        progress["topics"][topic][
            "wrong"
        ] += 1

    update_accuracy(progress)

    progress["last_activity"] = now()

    save_progress()

    return progress


# ============================================================
# GHI NHẬN GỢI Ý
# ============================================================

def record_hint(
    student_id,
    subject_id,
):

    progress = create_progress(
        student_id,
        subject_id,
    )

    progress["hints"] += 1

    progress["last_activity"] = now()

    save_progress()

    return progress


# ============================================================
# GHI NHẬN HOẠT ĐỘNG
# ============================================================

def record_activity(
    student_id,
    subject_id,
    activity_name,
):

    progress = create_progress(
        student_id,
        subject_id,
    )

    progress["activities"] += 1

    progress["recent_lessons"].append(
        {
            "activity":
                activity_name,

            "time":
                now(),
        }
    )

    progress["recent_lessons"] = (
        progress["recent_lessons"][-20:]
    )

    progress["last_activity"] = now()

    save_progress()

    return progress


# ============================================================
# ĐÁNH GIÁ CHỦ ĐỀ
# ============================================================

def evaluate_topics(progress):

    strengths = []
    weaknesses = []

    for topic, data in progress[
        "topics"
    ].items():

        questions = data["questions"]

        if questions <= 0:

            continue

        accuracy = (
            data["correct"]
            / questions
        ) * 100

        if accuracy >= 80:

            strengths.append(topic)

        elif accuracy < 60:

            weaknesses.append(topic)

    progress["strengths"] = strengths

    progress["weaknesses"] = weaknesses

    save_progress()

    return progress


# ============================================================
# GỢI Ý ĐỘ KHÓ
# ============================================================

def recommend_level(
    student_id,
    subject_id,
):

    progress = create_progress(
        student_id,
        subject_id,
    )

    questions = progress["questions"]

    accuracy = progress["accuracy"]

    if questions < 5:

        return "elementary"

    if accuracy < 60:

        return "beginner"

    if accuracy >= 85:

        return "advanced"

    return "elementary"


# ============================================================
# GỢI Ý CHỦ ĐỀ CẦN ÔN
# ============================================================

def recommend_topic(
    student_id,
    subject_id,
):

    progress = create_progress(
        student_id,
        subject_id,
    )

    evaluate_topics(progress)

    if progress["weaknesses"]:

        return progress[
            "weaknesses"
        ][0]

    worst_topic = None

    worst_accuracy = 101

    for topic, data in progress[
        "topics"
    ].items():

        questions = data["questions"]

        if questions <= 0:

            continue

        accuracy = (
            data["correct"]
            / questions
        ) * 100

        if accuracy < worst_accuracy:

            worst_accuracy = accuracy

            worst_topic = topic

    return worst_topic


# ============================================================
# CẢM XÚC
# ============================================================

def set_emotion(
    student_id,
    subject_id,
    emotion,
):

    progress = create_progress(
        student_id,
        subject_id,
    )

    progress["emotion"] = emotion

    progress["last_activity"] = now()

    save_progress()

    return progress


# ============================================================
# MỨC ĐỘ HỨNG THÚ
# ============================================================

def set_engagement(
    student_id,
    subject_id,
    engagement,
):

    progress = create_progress(
        student_id,
        subject_id,
    )

    progress["engagement"] = engagement

    progress["last_activity"] = now()

    save_progress()

    return progress


# ============================================================
# LẤY TIẾN ĐỘ
# ============================================================

def get_progress(
    student_id,
    subject_id,
):

    return create_progress(
        student_id,
        subject_id,
    )


# ============================================================
# TÓM TẮT TIẾN ĐỘ
# ============================================================

def get_progress_summary(
    student_id,
    subject_id,
):

    progress = create_progress(
        student_id,
        subject_id,
    )

    evaluate_topics(progress)

    return {

        "student":
            progress["nickname"],

        "subject":
            progress["subject_name"],

        "questions":
            progress["questions"],

        "correct":
            progress["correct"],

        "wrong":
            progress["wrong"],

        "hints":
            progress["hints"],

        "accuracy":
            progress["accuracy"],

        "level":
            recommend_level(
                student_id,
                subject_id,
            ),

        "strengths":
            progress["strengths"],

        "weaknesses":
            progress["weaknesses"],

        "recommended_topic":
            recommend_topic(
                student_id,
                subject_id,
            ),

        "emotion":
            progress["emotion"],

        "engagement":
            progress["engagement"],

        "last_activity":
            progress["last_activity"],
    }


# ============================================================
# XÓA TIẾN ĐỘ MỘT MÔN
# ============================================================

def reset_progress(
    student_id,
    subject_id,
):

    key = (
        f"{student_id}:{subject_id}"
    )

    if key in PROGRESS:

        del PROGRESS[key]

        save_progress()

        return True

    return False


# ============================================================
# XÓA TOÀN BỘ TIẾN ĐỘ
# ============================================================

def reset_all_progress():

    global PROGRESS

    PROGRESS = {}

    save_progress()

    return True