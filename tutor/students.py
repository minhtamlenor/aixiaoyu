# ============================================================
# TIỂU VŨ - HỒ SƠ HỌC SINH
# ============================================================

STUDENTS = {
    "nha_tien": {
        "id": "nha_tien",
        "name": "Nguyễn Ngô Nhã Tiên",
        "gender": "Nữ",
        "birth_date": "23/08/2015",
        "nickname": "Mini",
        "grade": 6,
        "chinese_level": "hsk3",
        "nicknames": ["Mini", "Nhã Tiên"],
        "preferred_names": ["Mini", "Nhã Tiên"],
        "description": "Bé gái. Tên gọi thân mật là Mini. Học lớp 6. Tiếng Trung theo HSK 3.0, mức HSK 3.",
    },
    "minh_tien": {
        "id": "minh_tien",
        "name": "Nguyễn Ngô Minh Tiên",
        "gender": "Nam",
        "birth_date": "09/07/2015",
        "nickname": "Đậu Đậu",
        "grade": 4,
        "chinese_level": "hsk1",
        "nicknames": ["Đậu Phộng", "Đậu Đậu", "Dou Dou", "豆豆"],
        "preferred_names": ["Đậu Đậu", "Đậu Phộng", "Dou Dou"],
        "description": "Bé trai. Tên gọi thân mật là Đậu Phộng hoặc Đậu Đậu. Học lớp 4. Tiếng Trung theo HSK 3.0, mức HSK 1.",
    },
}


def get_student(student_id):
    return STUDENTS.get(student_id)


def get_student_name(student_id):
    student = get_student(student_id)
    return student["name"] if student else "học sinh"


def get_nickname(student_id):
    student = get_student(student_id)
    if not student:
        return "con"
    return student.get("nickname") or student.get("preferred_names", [student["name"]])[0]


def get_nicknames(student_id):
    student = get_student(student_id)
    return student.get("nicknames", []) if student else []


def get_grade(student_id):
    student = get_student(student_id)
    return student.get("grade", 4) if student else 4


def get_chinese_level(student_id):
    student = get_student(student_id)
    return student.get("chinese_level", "hsk1") if student else "hsk1"


def student_exists(student_id):
    return student_id in STUDENTS
