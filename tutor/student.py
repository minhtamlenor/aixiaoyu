# ============================================================
# TIỂU VŨ - HỒ SƠ HỌC SINH
# ============================================================

from datetime import date


STUDENTS = {
    "nha_tien": {
        "name": "Nguyễn Ngô Nhã Tiên",
        "gender": "nữ",
        "birth_date": date(2015, 8, 23),
    },

    "minh_tien": {
        "name": "Nguyễn Ngô Minh Tiên",
        "gender": "nam",
        "birth_date": date(2015, 7, 9),
    },
}


def calculate_age(birth_date):
    today = date.today()

    age = today.year - birth_date.year

    if (today.month, today.day) < (
        birth_date.month,
        birth_date.day,
    ):
        age -= 1

    return age


def get_student(student_id):
    student = STUDENTS.get(student_id)

    if not student:
        return None

    return {
        **student,
        "age": calculate_age(student["birth_date"]),
    }


def list_students():
    return [
        get_student(student_id)
        for student_id in STUDENTS
    ]


def get_student_text(student_id):
    student = get_student(student_id)

    if not student:
        return "Không tìm thấy học sinh."

    return (
        f"Học sinh: {student['name']}\n"
        f"Giới tính: {student['gender']}\n"
        f"Ngày sinh: "
        f"{student['birth_date'].strftime('%d/%m/%Y')}\n"
        f"Tuổi hiện tại: {student['age']}"
    )