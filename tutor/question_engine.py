# ============================================================
# TIỂU VŨ - QUESTION ENGINE
# BỘ MÁY TẠO VÀ XỬ LÝ CÂU HỎI
# ============================================================

import random


# ============================================================
# CẤU HÌNH
# ============================================================

TUTOR_NAME = "Tiểu Vũ"


# ============================================================
# HÀM TẠO CÂU HỎI TOÁN
# ============================================================

def generate_math_question(topic="addition", strategy="practice"):
    """
    Tạo một câu hỏi Toán.

    topic:
        addition
        subtraction
        multiplication
        division

    strategy:
        introduce
        review
        practice
        advance
    """

    # --------------------------------------------------------
    # PHÉP CỘNG
    # --------------------------------------------------------

    if topic == "addition":

        if strategy == "introduce":
            a = random.randint(1, 9)
            b = random.randint(1, 9)

        elif strategy == "review":
            a = random.randint(1, 10)
            b = random.randint(1, 10)

        elif strategy == "advance":
            a = random.randint(10, 50)
            b = random.randint(10, 50)

        else:
            a = random.randint(5, 30)
            b = random.randint(5, 30)

        answer = a + b

        return {
            "question": f"{a} + {b} bằng bao nhiêu?",
            "topic": "addition",
            "answer": answer,
            "hint": (
                f"Con thử bắt đầu từ {a}, "
                f"rồi đếm thêm {b} bước nhé."
            ),
            "explanation": (
                f"{a} cộng {b} bằng {answer}."
            ),
            "strategy": strategy,
        }

    # --------------------------------------------------------
    # PHÉP TRỪ
    # --------------------------------------------------------

    if topic == "subtraction":

        if strategy == "advance":
            a = random.randint(20, 80)
            b = random.randint(5, a)
        else:
            a = random.randint(5, 30)
            b = random.randint(1, a)

        answer = a - b

        return {
            "question": f"{a} - {b} bằng bao nhiêu?",
            "topic": "subtraction",
            "answer": answer,
            "hint": (
                f"Con thử bắt đầu từ {a}, "
                f"rồi bớt đi {b} nhé."
            ),
            "explanation": (
                f"{a} trừ {b} bằng {answer}."
            ),
            "strategy": strategy,
        }

    # --------------------------------------------------------
    # PHÉP NHÂN
    # --------------------------------------------------------

    if topic == "multiplication":

        a = random.randint(2, 9)
        b = random.randint(2, 9)

        answer = a * b

        return {
            "question": f"{a} × {b} bằng bao nhiêu?",
            "topic": "multiplication",
            "answer": answer,
            "hint": (
                f"Con thử nghĩ {a} nhóm, "
                f"mỗi nhóm có {b} nhé."
            ),
            "explanation": (
                f"{a} nhân {b} bằng {answer}."
            ),
            "strategy": strategy,
        }

    # --------------------------------------------------------
    # PHÉP CHIA
    # --------------------------------------------------------

    if topic == "division":

        b = random.randint(2, 9)
        answer = random.randint(2, 9)
        a = b * answer

        return {
            "question": f"{a} ÷ {b} bằng bao nhiêu?",
            "topic": "division",
            "answer": answer,
            "hint": (
                f"Con thử nghĩ xem có thể chia {a} "
                f"thành {b} nhóm bằng nhau như thế nào nhé."
            ),
            "explanation": (
                f"{a} chia {b} bằng {answer}."
            ),
            "strategy": strategy,
        }

    # --------------------------------------------------------
    # MẶC ĐỊNH
    # --------------------------------------------------------

    return generate_math_question(
        topic="addition",
        strategy=strategy,
    )


# ============================================================
# HÀM TẠO CÂU HỎI CHUNG
# ============================================================

def generate_question(
    student_id=None,
    subject_id="math",
    topic="addition",
    strategy="practice",
):
    """
    Hàm chính để lesson_manager gọi.

    Có hỗ trợ:
        student_id
        subject_id
        topic
        strategy
    """

    # --------------------------------------------------------
    # TOÁN
    # --------------------------------------------------------

    if subject_id == "math":

        return generate_math_question(
            topic=topic,
            strategy=strategy,
        )

    # --------------------------------------------------------
    # TIẾNG VIỆT
    # --------------------------------------------------------

    if subject_id == "vietnamese":

        return {
            "question": (
                "Con hãy đặt một câu có từ 'mẹ'."
            ),
            "topic": topic,
            "answer": None,
            "hint": (
                "Con thử nghĩ đến một việc "
                "mẹ thường làm cho con nhé."
            ),
            "explanation": (
                "Một câu hoàn chỉnh cần có ý nghĩa "
                "và diễn đạt rõ ràng."
            ),
            "strategy": strategy,
        }

    # --------------------------------------------------------
    # TIẾNG ANH
    # --------------------------------------------------------

    if subject_id == "english":

        return {
            "question": (
                "What is the opposite of 'big'?"
            ),
            "topic": topic,
            "answer": "small",
            "hint": (
                "Nó có nghĩa là 'nhỏ' đó."
            ),
            "explanation": (
                "The opposite of 'big' is 'small'."
            ),
            "strategy": strategy,
        }

    # --------------------------------------------------------
    # TIẾNG TRUNG
    # --------------------------------------------------------

    if subject_id == "chinese":

        return {
            "question": (
                "“你好” nghĩa là gì?"
            ),
            "topic": topic,
            "answer": "xin chào",
            "hint": (
                "Đây là một lời chào rất quen thuộc."
            ),
            "explanation": (
                "你好 có nghĩa là xin chào."
            ),
            "strategy": strategy,
        }

    # --------------------------------------------------------
    # MẶC ĐỊNH
    # --------------------------------------------------------

    return {
        "question": (
            "Con thử suy nghĩ về câu hỏi này nhé."
        ),
        "topic": topic,
        "answer": None,
        "hint": (
            "Tiểu Vũ sẽ gợi ý thêm nếu con cần."
        ),
        "explanation": "",
        "strategy": strategy,
    }


# ============================================================
# KIỂM TRA CÂU TRẢ LỜI
# ============================================================

def check_answer(
    question_data,
    user_answer,
):
    """
    Kiểm tra câu trả lời của học sinh.
    """

    if not isinstance(question_data, dict):

        return {
            "correct": False,
            "message": (
                "Tiểu Vũ chưa có dữ liệu câu hỏi."
            ),
        }

    correct_answer = question_data.get(
        "answer"
    )

    # --------------------------------------------------------
    # Chuẩn hóa câu trả lời
    # --------------------------------------------------------

    if isinstance(user_answer, str):

        user_answer_clean = (
            user_answer.strip().lower()
        )

    else:

        user_answer_clean = user_answer

    # --------------------------------------------------------
    # Chuẩn hóa đáp án
    # --------------------------------------------------------

    if isinstance(correct_answer, str):

        correct_answer_clean = (
            correct_answer.strip().lower()
        )

    else:

        correct_answer_clean = correct_answer

    # --------------------------------------------------------
    # Kiểm tra
    # --------------------------------------------------------

    if (
        user_answer_clean
        == correct_answer_clean
    ):

        return {
            "correct": True,
            "message": (
                "Đúng rồi! "
                "Con tự tìm ra đáp án đó!"
            ),
            "explanation": question_data.get(
                "explanation",
                "",
            ),
        }

    # --------------------------------------------------------
    # Trả lời sai
    # --------------------------------------------------------

    return {
        "correct": False,
        "message": (
            "Không sao đâu. "
            "Mình thử suy nghĩ lại một chút nha."
        ),
        "hint": question_data.get(
            "hint",
            "Con thử suy nghĩ thêm một chút nhé.",
        ),
    }


# ============================================================
# LẤY GỢI Ý
# ============================================================

def get_hint(question_data):

    if not isinstance(question_data, dict):

        return (
            "Con thử suy nghĩ thêm một chút nhé."
        )

    return question_data.get(
        "hint",
        "Con thử suy nghĩ thêm một chút nhé.",
    )


# ============================================================
# LẤY GIẢI THÍCH
# ============================================================

def get_explanation(question_data):

    if not isinstance(question_data, dict):

        return ""

    return question_data.get(
        "explanation",
        "",
    )


# ============================================================
# TEST QUESTION ENGINE
# ============================================================

def demo():

    print()
    print("=" * 60)
    print("TIỂU VŨ - QUESTION ENGINE")
    print("=" * 60)

    # --------------------------------------------------------
    # TẠO CÂU HỎI
    # --------------------------------------------------------

    question = generate_question(
        student_id="nha_tien",
        subject_id="math",
        topic="addition",
        strategy="practice",
    )

    print()
    print("TẠO CÂU HỎI")
    print("-" * 60)
    print(question)

    # --------------------------------------------------------
    # HIỂN THỊ CÂU HỎI
    # --------------------------------------------------------

    print()
    print("CÂU HỎI")
    print("-" * 60)
    print(
        question["question"]
    )

    # --------------------------------------------------------
    # HIỂN THỊ GỢI Ý
    # --------------------------------------------------------

    print()
    print("GỢI Ý")
    print("-" * 60)
    print(
        get_hint(question)
    )

    # --------------------------------------------------------
    # TEST ĐÚNG
    # --------------------------------------------------------

    print()
    print("TEST ĐÚNG")
    print("-" * 60)

    result_correct = check_answer(
        question,
        question["answer"],
    )

    print(
        result_correct
    )

    # --------------------------------------------------------
    # TEST SAI
    # --------------------------------------------------------

    print()
    print("TEST SAI")
    print("-" * 60)

    wrong_answer = (
        question["answer"] + 1
        if isinstance(
            question["answer"],
            int
        )
        else "sai"
    )

    result_wrong = check_answer(
        question,
        wrong_answer,
    )

    print(
        result_wrong
    )

    # --------------------------------------------------------
    # HOÀN TẤT
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("TEST HOÀN TẤT")
    print("=" * 60)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    demo()