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

        "nicknames": [
            "Mini",
            "Nhã Tiên",
        ],

        "preferred_names": [
            "Mini",
            "Nhã Tiên",
        ],

        "description": (
            "Bé gái. Tên gọi thân mật là Mini."
        ),
    },


    "minh_tien": {
        "id": "minh_tien",
        "name": "Nguyễn Ngô Minh Tiên",
        "gender": "Nam",
        "birth_date": "09/07/2015",

        "nickname": "Đậu Đậu",

        "nicknames": [
            "Đậu Phộng",
            "Đậu Đậu",
            "Dou Dou",
            "豆豆",
        ],

        "preferred_names": [
            "Đậu Đậu",
            "Đậu Phộng",
            "Dou Dou",
        ],

        "description": (
            "Bé trai. Tên gọi thân mật là Đậu Phộng "
            "hoặc Đậu Đậu. Có cách gọi vui bằng tiếng Trung "
            "là Dou Dou / 豆豆."
        ),
    },
}


# ============================================================
# LẤY HỒ SƠ HỌC SINH
# ============================================================

def get_student(student_id):

    return STUDENTS.get(student_id)


# ============================================================
# LẤY TÊN ĐẦY ĐỦ
# ============================================================

def get_student_name(student_id):

    student = get_student(student_id)

    if not student:
        return "học sinh"

    return student["name"]


# ============================================================
# LẤY TÊN THÂN MẬT
# ============================================================

def get_nickname(student_id):

    student = get_student(student_id)

    if not student:
        return "con"

    nickname = student.get("nickname")

    if nickname:
        return nickname

    preferred_names = student.get(
        "preferred_names",
        [],
    )

    if preferred_names:
        return preferred_names[0]

    return student["name"]


# ============================================================
# LẤY DANH SÁCH TÊN
# ============================================================

def get_nicknames(student_id):

    student = get_student(student_id)

    if not student:
        return []

    return student.get(
        "nicknames",
        [],
    )


# ============================================================
# KIỂM TRA HỌC SINH
# ============================================================

def student_exists(student_id):

    return student_id in STUDENTS