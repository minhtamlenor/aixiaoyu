# ============================================================
# TIỂU VŨ - LESSON SESSION
# QUẢN LÝ MỘT BUỔI HỌC HOÀN CHỈNH
# ============================================================

from datetime import datetime

from tutor.students import get_student
from tutor.curriculum import get_subject
from tutor.adaptive import create_learning_plan
from tutor.progress import (
    record_correct,
    record_wrong,
)


# ============================================================
# THÔNG TIN CHUNG
# ============================================================

TUTOR_NAME = "Tiểu Vũ"


# ============================================================
# TRẠNG THÁI BUỔI HỌC
# ============================================================

STATUS_STARTED = "started"
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"


# ============================================================
# TẠO SESSION ID
# ============================================================

def create_session_id(
    student_id,
    subject_id,
):

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

def create_lesson_session(
    student_id,
    subject_id,
):

    student = get_student(
        student_id
    )

    if not student:

        raise ValueError(
            f"Không tìm thấy học sinh: {student_id}"
        )

    subject = get_subject(
        subject_id
    )

    if not subject:

        raise ValueError(
            f"Không tìm thấy môn học: {subject_id}"
        )

    plan = create_learning_plan(
        student_id,
        subject_id,
    )

    return {

        "session_id":
            create_session_id(
                student_id,
                subject_id,
            ),

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

        "level":
            plan["level"],

        "topic":
            plan["topic"],

        "strategy":
            plan["strategy"],

        "accuracy":
            plan["accuracy"],

        "questions_before":
            plan["questions"],

        "correct":
            0,

        "wrong":
            0,

        "hints":
            0,

        "activities":
            0,

        "current_question":
            None,

        "question_count":
            0,

        "status":
            STATUS_STARTED,

        "started_at":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "ended_at":
            None,
    }


# ============================================================
# BẮT ĐẦU BUỔI HỌC
# ============================================================

def start_session(session):

    session["status"] = STATUS_ACTIVE

    session["started_at"] = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    return session


# ============================================================
# LẤY THÔNG TIN HƯỚNG DẪN NỘI BỘ
# ============================================================

def get_session_plan(session):

    return {

        "subject":
            session["subject_name"],

        "topic":
            session["topic"],

        "level":
            session["level"],

        "strategy":
            session["strategy"],

        "accuracy_before":
            session["accuracy"],

        "questions_before":
            session["questions_before"],
    }


# ============================================================
# TẠO LỜI CHÀO
# ============================================================

def get_session_greeting(session):

    name = session["nickname"]
    subject = session["subject_name"]
    strategy = session["strategy"]

    greetings = {

        "introduce": [
            (
                f"Chào {name} nha! "
                f"Hôm nay Tiểu Vũ với con "
                f"khám phá {subject} một chút nghen."
            ),

            (
                f"Hello {name}! "
                f"Tiểu Vũ tới rồi nè. "
                f"Mình cùng học {subject} nha!"
            ),

            (
                f"{name} ơi, hôm nay mình "
                f"chơi với {subject} một chút nha. "
                f"Tiểu Vũ có vài điều thú vị muốn kể con nghe."
            ),
        ],

        "review": [
            (
                f"Chào {name}! "
                f"Hôm nay mình cùng ôn lại một chút "
                f"rồi thử lại nha."
            ),

            (
                f"Hello {name}! "
                f"Mình cùng làm vài bài nhẹ nhàng "
                f"để nhớ lại kiến thức nha."
            ),
        ],

        "practice": [
            (
                f"Chào {name!s}! "
                f"Hôm nay mình luyện {subject} "
                f"một chút nha."
            ),

            (
                f"{name} ơi, sẵn sàng chưa? "
                f"Tiểu Vũ có vài thử thách nhỏ cho con nè."
            ),
        ],

        "advance": [
            (
                f"Hello {name}! "
                f"Hôm nay Tiểu Vũ có một thử thách "
                f"khó hơn một chút cho con nè."
            ),

            (
                f"{name} ơi! "
                f"Hôm nay mình thử một câu hóc búa hơn nha. "
                f"Xem con nghĩ ra cách nào hay nhất."
            ),
        ],
    }

    options = greetings.get(
        strategy,
        greetings["introduce"],
    )

    # Chọn lời chào đầu tiên để hệ thống
    # không cần thêm thư viện random.
    return options[0]


# ============================================================
# ĐẶT CÂU HỎI HIỆN TẠI
# ============================================================

def set_question(
    session,
    question,
    topic=None,
):

    session["question_count"] += 1

    session["current_question"] = {

        "question":
            question,

        "topic":
            topic or session["topic"],

        "asked_at":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
    }

    return session["current_question"]


# ============================================================
# GHI NHẬN TRẢ LỜI ĐÚNG
# ============================================================

def answer_correct(
    session,
    topic=None,
):

    topic = (
        topic
        or session["topic"]
    )

    record_correct(
        session["student_id"],
        session["subject_id"],
        topic,
    )

    session["correct"] += 1

    session["current_question"] = None

    return {

        "result":
            "correct",

        "message":
            "Trả lời đúng.",

        "topic":
            topic,

        "correct":
            session["correct"],

        "wrong":
            session["wrong"],
    }


# ============================================================
# GHI NHẬN TRẢ LỜI SAI
# ============================================================

def answer_wrong(
    session,
    topic=None,
):

    topic = (
        topic
        or session["topic"]
    )

    record_wrong(
        session["student_id"],
        session["subject_id"],
        topic,
    )

    session["wrong"] += 1

    return {

        "result":
            "wrong",

        "message":
            "Cần thử lại.",

        "topic":
            topic,

        "correct":
            session["correct"],

        "wrong":
            session["wrong"],
    }


# ============================================================
# GHI NHẬN DÙNG GỢI Ý
# ============================================================

def use_hint(session):

    session["hints"] += 1

    return {

        "hint_used":
            True,

        "hints":
            session["hints"],
    }


# ============================================================
# GHI NHẬN HOẠT ĐỘNG
# ============================================================

def add_activity(
    session,
    activity_type,
):

    session["activities"] += 1

    return {

        "activity":
            activity_type,

        "activities":
            session["activities"],
    }


# ============================================================
# KẾT THÚC BUỔI HỌC
# ============================================================

def complete_session(session):

    session["status"] = STATUS_COMPLETED

    session["ended_at"] = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    session["current_question"] = None

    return session


# ============================================================
# TÍNH ĐỘ CHÍNH XÁC TRONG BUỔI HỌC
# ============================================================

def get_session_accuracy(session):

    total = (
        session["correct"]
        +
        session["wrong"]
    )

    if total == 0:

        return 0.0

    return round(
        (
            session["correct"]
            /
            total
        )
        * 100,
        1,
    )


# ============================================================
# TÓM TẮT BUỔI HỌC
# ============================================================

def get_session_summary(session):

    return {

        "session_id":
            session["session_id"],

        "student":
            session["nickname"],

        "subject":
            session["subject_name"],

        "topic":
            session["topic"],

        "strategy":
            session["strategy"],

        "level":
            session["level"],

        "questions":
            session["question_count"],

        "correct":
            session["correct"],

        "wrong":
            session["wrong"],

        "hints":
            session["hints"],

        "activities":
            session["activities"],

        "accuracy":
            get_session_accuracy(
                session
            ),

        "status":
            session["status"],

        "started_at":
            session["started_at"],

        "ended_at":
            session["ended_at"],
    }


# ============================================================
# TẠO PROMPT NỘI BỘ CHO TIỂU VŨ
# ============================================================

def build_session_instruction(session):

    summary = get_session_summary(
        session
    )

    return f"""
============================================================
TIỂU VŨ - BUỔI HỌC HIỆN TẠI
============================================================

Học sinh:
{session["student_name"]}

Tên gọi:
{session["nickname"]}

Môn:
{session["subject_name"]}

Chủ đề:
{session["topic"]}

Mức độ:
{session["level"]}

Chiến lược:
{session["strategy"]}

Tiến độ trước buổi học:
{session["questions_before"]} câu

Độ chính xác trước buổi học:
{session["accuracy"]}%


============================================================
TIẾN ĐỘ TRONG BUỔI HỌC
============================================================

Số câu:
{summary["questions"]}

Đúng:
{summary["correct"]}

Sai:
{summary["wrong"]}

Gợi ý:
{summary["hints"]}

Hoạt động:
{summary["activities"]}


============================================================
QUY TẮC
============================================================

Đây là thông tin nội bộ.

Không đọc các thông tin kỹ thuật
cho học sinh.

Không biến buổi học thành kỳ thi.

Không liên tục đưa câu hỏi
mà không giải thích.

Hãy xen kẽ:

- câu hỏi;
- giải thích;
- ví dụ;
- trò chơi;
- câu đố;
- tình huống thực tế;
- khuyến khích trẻ giải thích suy nghĩ.

Nếu trẻ trả lời đúng:

→ khen cụ thể;
→ giải thích ngắn;
→ có thể nâng độ khó.

Nếu trẻ trả lời sai:

→ không chê;
→ không làm trẻ xấu hổ;
→ đưa gợi ý;
→ cho trẻ thử lại.

Nếu trẻ dùng nhiều gợi ý:

→ giảm độ khó;
→ chia nhỏ vấn đề.

Nếu trẻ trả lời tốt:

→ tăng thử thách từ từ.

Mục tiêu:

GIÚP TRẺ HIỂU VÀ TỰ SUY NGHĨ.

Không chạy theo điểm số.
"""


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("============================================================")
    print("TIỂU VŨ - LESSON SESSION TEST")
    print("============================================================")
    print()

    session = create_lesson_session(
        "nha_tien",
        "math",
    )

    print("SESSION:")
    print(session)

    print()
    print("------------------------------------------------------------")
    print("BẮT ĐẦU")
    print("------------------------------------------------------------")

    start_session(session)

    print(
        get_session_greeting(
            session
        )
    )

    print()
    print("------------------------------------------------------------")
    print("KẾ HOẠCH")
    print("------------------------------------------------------------")

    print(
        get_session_plan(
            session
        )
    )

    print()
    print("------------------------------------------------------------")
    print("CÂU HỎI")
    print("------------------------------------------------------------")

    set_question(
        session,
        "2 + 3 bằng bao nhiêu?",
        "addition",
    )

    print(
        session["current_question"]
    )

    print()
    print("------------------------------------------------------------")
    print("TRẢ LỜI ĐÚNG")
    print("------------------------------------------------------------")

    answer_correct(
        session,
        "addition",
    )

    print(
        get_session_summary(
            session
        )
    )

    print()
    print("------------------------------------------------------------")
    print("KẾT THÚC")
    print("------------------------------------------------------------")

    complete_session(
        session
    )

    print(
        get_session_summary(
            session
        )
    )