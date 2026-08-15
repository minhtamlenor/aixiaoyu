# ============================================================
# TIỂU VŨ - STUDENT NAME / ALIAS MAPPING
# 2 HỌC SINH DUY NHẤT
#
# 👦 MINH TIÊN
#    = ĐẬU ĐẬU
#    = ĐẬU PHỘNG
#    = ĐẬU PHỤNG
#
# 👧 NHÃ TIÊN
#    = MINI
#
# TÊN ĐƯỢC GỌI SẼ ĐƯỢC GIỮ NGUYÊN TRONG SUỐT PHIÊN
# ============================================================

import re
import unicodedata


# ============================================================
# STUDENT DATABASE
# ============================================================

STUDENTS = {

    # ========================================================
    # 👦 BÉ TRAI - MINH TIÊN
    # ========================================================

    "minh_tien": {

        "student_id": "minh_tien",

        "official_name": "Minh Tiên",

        "gender": "male",

        "aliases": [
            "Minh Tiên",
            "Minh Tien",

            "Đậu Đậu",
            "Dau Dau",

            "Đậu Phộng",
            "Đậu Phụng",
            "Dau Phong",
            "Dau Phung",
        ],

    },


    # ========================================================
    # 👧 BÉ GÁI - NHÃ TIÊN
    # ========================================================

    "nha_tien": {

        "student_id": "nha_tien",

        "official_name": "Nhã Tiên",

        "gender": "female",

        "aliases": [
            "Nhã Tiên",
            "Nha Tien",

            "Mini",
        ],

    },

}


# ============================================================
# TẠO BẢNG ALIAS
# ============================================================

STUDENT_ALIASES = {}


for student_id, student in STUDENTS.items():

    for alias in student["aliases"]:

        STUDENT_ALIASES[
            alias.strip().lower()
        ] = {

            "student_id": student_id,

            "official_name": student[
                "official_name"
            ],

            "nickname": alias.strip(),

            "gender": student[
                "gender"
            ],

        }


# ============================================================
# CHUẨN HÓA TEXT
# ============================================================

def normalize_text(text):

    if not isinstance(text, str):

        return ""

    text = text.strip().lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# BỎ DẤU
# ============================================================

def remove_accents(text):

    if not isinstance(text, str):

        return ""

    normalized = unicodedata.normalize(
        "NFD",
        text
    )

    result = "".join(

        char

        for char in normalized

        if unicodedata.category(char) != "Mn"

    )

    result = result.replace(
        "đ",
        "d"
    )

    result = result.replace(
        "Đ",
        "D"
    )

    return result.lower().strip()


# ============================================================
# TÌM HỌC SINH TỪ TÊN ĐƯỢC GỌI
#
# Ví dụ:
#
# resolve_student_from_name("Đậu Phộng")
# → minh_tien
#
# resolve_student_from_name("Mini")
# → nha_tien
# ============================================================

def resolve_student_from_name(name):

    if not isinstance(name, str):

        return None


    normalized = normalize_text(
        name
    )

    no_accent = remove_accents(
        normalized
    )


    # --------------------------------------------------------
    # TÌM TRỰC TIẾP
    # --------------------------------------------------------

    student = STUDENT_ALIASES.get(
        normalized
    )

    if student is not None:

        return student


    # --------------------------------------------------------
    # TÌM KHÔNG DẤU
    # --------------------------------------------------------

    for alias, student in STUDENT_ALIASES.items():

        if remove_accents(alias) == no_accent:

            return student


    return None


# ============================================================
# TÌM HỌC SINH TRONG CẢ CÂU NÓI
#
# Ví dụ:
#
# "Đậu Phộng muốn học"
# "Cho Mini vào học"
# "Minh Tiên hôm nay học Toán"
# ============================================================

def resolve_student_from_text(text):

    if not isinstance(text, str):

        return None


    normalized = normalize_text(
        text
    )

    no_accent = remove_accents(
        normalized
    )


    # --------------------------------------------------------
    # ƯU TIÊN ALIAS DÀI TRƯỚC
    #
    # Tránh trường hợp tên ngắn bị bắt trước.
    # --------------------------------------------------------

    aliases = sorted(

        STUDENT_ALIASES.items(),

        key=lambda item: len(item[0]),

        reverse=True

    )


    for alias, student in aliases:

        alias_normalized = normalize_text(
            alias
        )

        alias_no_accent = remove_accents(
            alias_normalized
        )


        # Có dấu

        if alias_normalized in normalized:

            return {

                **student,

                "called_name": alias_normalized,

            }


        # Không dấu

        if alias_no_accent in no_accent:

            return {

                **student,

                "called_name": alias_normalized,

            }


    return None


# ============================================================
# LẤY STUDENT ID
# ============================================================

def resolve_student_id(name):

    student = resolve_student_from_name(
        name
    )

    if student is None:

        return None

    return student["student_id"]


# ============================================================
# LẤY TÊN ĐƯỢC GỌI
#
# Đây là tên Tiểu Vũ sẽ dùng để xưng hô trong PHIÊN.
# ============================================================

def resolve_call_name(name):

    student = resolve_student_from_name(
        name
    )

    if student is None:

        return None

    return student["nickname"]


# ============================================================
# LẤY TÊN CHÍNH THỨC
# ============================================================

def resolve_official_name(name):

    student = resolve_student_from_name(
        name
    )

    if student is None:

        return None

    return student["official_name"]


# ============================================================
# KIỂM TRA HAI HỌC SINH
# ============================================================

def test_student_aliases():

    tests = [

        # ----------------------------------------------------
        # 👦 MINH TIÊN
        # ----------------------------------------------------

        "Minh Tiên",

        "Đậu Đậu",

        "Đậu Phộng",

        "Đậu Phụng",

        "Dau Dau",

        "Dau Phong",

        "Dau Phung",


        # ----------------------------------------------------
        # 👧 NHÃ TIÊN
        # ----------------------------------------------------

        "Nhã Tiên",

        "Mini",

        "Nha Tien",

    ]


    print()

    print("=" * 70)

    print(
        "TIỂU VŨ - STUDENT ALIAS TEST"
    )

    print("=" * 70)


    for name in tests:

        student = resolve_student_from_name(
            name
        )


        print()

        print(
            "Tên gọi:",
            name
        )

        print(
            "Student:",
            student
        )


        if student:

            print(
                "Student ID:",
                student["student_id"]
            )

            print(
                "Tên chính thức:",
                student["official_name"]
            )

            print(
                "Tên gọi phiên:",
                student["nickname"]
            )


    print()

    print("=" * 70)

    print(
        "TEST CÂU NÓI VOICE"
    )

    print("=" * 70)


    voice_tests = [

        "Đậu Phộng muốn học",

        "Đậu Đậu muốn học Toán",

        "Minh Tiên muốn học",

        "Cho Đậu Phụng vào học",

        "Mini muốn học",

        "Nhã Tiên muốn học Toán",

        "Cho Mini học bài",

    ]


    for text in voice_tests:

        result = resolve_student_from_text(
            text
        )


        print()

        print(
            "Câu:",
            text
        )

        print(
            "Kết quả:",
            result
        )


    print()

    print("=" * 70)

    print(
        "TEST HOÀN TẤT"
    )

    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    test_student_aliases()