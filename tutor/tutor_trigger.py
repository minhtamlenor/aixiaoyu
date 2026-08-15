# ============================================================
# TIỂU VŨ - TUTOR TRIGGER V2
# NHẬN DIỆN LỆNH BẮT ĐẦU HỌC + NHẬN DIỆN HỌC SINH
# ============================================================

import re
import unicodedata


# ============================================================
# TÊN / BIỆT DANH HỌC SINH
# ============================================================

KNOWN_NICKNAMES = [
    "Mini",
    "Đậu Phộng",
    "Đậu phụng",
    "Đậu Đậu",
    "Đậu đậu",
]


# ============================================================
# CHUẨN HÓA TEXT
# ============================================================

def normalize_text(text):

    if not isinstance(text, str):
        return ""

    text = text.strip().lower()

    # --------------------------------------------------------
    # Chuẩn hóa khoảng trắng
    # --------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# CHUẨN HÓA BỎ DẤU
# Dùng để nhận diện cả:
#
# "Đậu Phộng"
# "dau phong"
# "Đậu phụng"
# "dau phung"
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

    return normalized_text_cleanup(result)


def normalized_text_cleanup(text):

    text = text.replace(
        "đ",
        "d"
    )

    text = text.replace(
        "Đ",
        "D"
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip().lower()


# ============================================================
# XÁC ĐỊNH NICKNAME
# ============================================================

def detect_nickname(text):

    normalized = normalize_text(
        text
    )

    no_accent = remove_accents(
        normalized
    )

    # ========================================================
    # ĐẬU PHỘNG
    # ========================================================

    dau_phong_patterns = [
        "đậu phộng",
        "đậu phụng",
        "đậu  phộng",
        "đậu  phụng",

        "dau phong",
        "dau phung",
    ]

    for pattern in dau_phong_patterns:

        if (
            pattern in normalized
            or pattern in no_accent
        ):

            return "Đậu Phộng"


    # ========================================================
    # ĐẬU ĐẬU
    # ========================================================

    dau_dau_patterns = [
        "đậu đậu",
        "dau dau",
    ]

    for pattern in dau_dau_patterns:

        if (
            pattern in normalized
            or pattern in no_accent
        ):

            return "Đậu Đậu"


    # ========================================================
    # MINI
    # ========================================================

    mini_patterns = [
        "mini",
    ]

    for pattern in mini_patterns:

        if pattern in normalized:

            return "Mini"


    # ========================================================
    # KHÔNG XÁC ĐỊNH
    # ========================================================

    return None


# ============================================================
# XÁC ĐỊNH Ý ĐỊNH BẮT ĐẦU HỌC
# ============================================================

def detect_lesson_intent(text):

    normalized = normalize_text(
        text
    )

    no_accent = remove_accents(
        normalized
    )

    # ========================================================
    # CỤM TỪ HỌC
    # ========================================================

    patterns = [

        # ----------------------------------------------------
        # MUỐN HỌC
        # ----------------------------------------------------

        "muốn học",
        "muon hoc",

        "con muốn học",
        "con muon hoc",

        "mini muốn học",
        "mini muon hoc",

        "đậu phộng muốn học",
        "đậu phụng muốn học",
        "dau phong muon hoc",
        "dau phung muon hoc",

        "đậu đậu muốn học",
        "dau dau muon hoc",


        # ----------------------------------------------------
        # BẮT ĐẦU HỌC
        # ----------------------------------------------------

        "bắt đầu học",
        "bat dau hoc",

        "bắt đầu bài học",
        "bat dau bai hoc",

        "bắt đầu học đi",
        "bat dau hoc di",


        # ----------------------------------------------------
        # HỌC ĐI
        # ----------------------------------------------------

        "học đi",
        "hoc di",

        "học thôi",
        "hoc thoi",

        "học nha",
        "hoc nha",

        "học nhé",
        "hoc nhe",


        # ----------------------------------------------------
        # VÀO HỌC
        # ----------------------------------------------------

        "vào học",
        "vao hoc",

        "vào học đi",
        "vao hoc di",

        "vô học",
        "vo hoc",

        "vô học đi",
        "vo hoc di",


        # ----------------------------------------------------
        # CHO CON HỌC
        # ----------------------------------------------------

        "cho con học",
        "cho con hoc",

        "cho mini học",
        "cho mini hoc",

        "cho đậu phộng học",
        "cho đậu phụng học",

        "cho đậu đậu học",

        "cho dau phong hoc",
        "cho dau phung hoc",

        "cho dau dau hoc",


        # ----------------------------------------------------
        # HỌC BÀI
        # ----------------------------------------------------

        "học bài",
        "hoc bai",

        "học bài đi",
        "hoc bai di",

        "học bài nha",
        "hoc bai nha",


        # ----------------------------------------------------
        # GIỜ HỌC
        # ----------------------------------------------------

        "giờ học",
        "gio hoc",

        "tới giờ học",
        "toi gio hoc",

        "đến giờ học",
        "den gio hoc",


        # ----------------------------------------------------
        # CÁCH NÓI TỰ NHIÊN
        # ----------------------------------------------------

        "học cái này",
        "hoc cai nay",

        "mình học đi",
        "minh hoc di",

        "mình học nha",
        "minh hoc nha",

        "học một chút",
        "hoc mot chut",

        "học một bài",
        "hoc mot bai",

    ]


    # ========================================================
    # KIỂM TRA CỤM CÓ DẤU
    # ========================================================

    for pattern in patterns:

        if pattern in normalized:

            return True


    # ========================================================
    # KIỂM TRA KHÔNG DẤU
    # ========================================================

    for pattern in patterns:

        pattern_no_accent = remove_accents(
            pattern
        )

        if pattern_no_accent in no_accent:

            return True


    # ========================================================
    # LOGIC BỔ SUNG
    #
    # Nếu câu rất ngắn nhưng có:
    #
    # "Mini học"
    # "Đậu Phộng học"
    # "Đậu Đậu học"
    #
    # thì vẫn xem là lệnh bắt đầu học.
    # ========================================================

    nickname = detect_nickname(
        normalized
    )

    if nickname is not None:

        short_learning_patterns = [

            "học",
            "hoc",

            "học nha",
            "hoc nha",

            "học nhé",
            "hoc nhe",

            "học thôi",
            "hoc thoi",

            "học đi",
            "hoc di",

        ]

        for pattern in short_learning_patterns:

            if pattern in normalized:
                return True

            if pattern in no_accent:
                return True


    return False


# ============================================================
# XÁC ĐỊNH MÔN HỌC
# ============================================================

def detect_subject(text):

    normalized = normalize_text(
        text
    )

    no_accent = remove_accents(
        normalized
    )


    # ========================================================
    # TOÁN
    # ========================================================

    math_words = [
        "toán",
        "toan",
        "math",
        "phép cộng",
        "phep cong",
        "phép trừ",
        "phep tru",
        "phép nhân",
        "phep nhan",
        "phép chia",
        "phep chia",
    ]

    for word in math_words:

        if (
            word in normalized
            or word in no_accent
        ):

            return "math"


    # ========================================================
    # TIẾNG VIỆT
    # ========================================================

    vietnamese_words = [
        "tiếng việt",
        "tieng viet",
        "tiếng việt nam",
        "tieng viet nam",
    ]

    for word in vietnamese_words:

        if (
            word in normalized
            or word in no_accent
        ):

            return "vietnamese"


    # ========================================================
    # TIẾNG ANH
    # ========================================================

    english_words = [
        "tiếng anh",
        "tieng anh",
        "english",
    ]

    for word in english_words:

        if (
            word in normalized
            or word in no_accent
        ):

            return "english"


    # ========================================================
    # TIẾNG TRUNG
    # ========================================================

    chinese_words = [
        "tiếng trung",
        "tieng trung",
        "tiếng hoa",
        "tieng hoa",
        "tiếng trung quốc",
        "tieng trung quoc",
        "chinese",
    ]

    for word in chinese_words:

        if (
            word in normalized
            or word in no_accent
        ):

            return "chinese"


    # ========================================================
    # KHÔNG XÁC ĐỊNH
    # ========================================================

    return None


# ============================================================
# PHÂN TÍCH TOÀN BỘ CÂU NÓI
# ============================================================

def detect_tutor_command(text):

    if not isinstance(
        text,
        str
    ):

        return {
            "intent": "chat",
            "nickname": None,
            "subject": None,
            "text": "",
        }


    nickname = detect_nickname(
        text
    )

    lesson_intent = detect_lesson_intent(
        text
    )

    subject = detect_subject(
        text
    )


    # ========================================================
    # CÓ LỆNH BẮT ĐẦU HỌC
    # ========================================================

    if lesson_intent:

        return {
            "intent": "start_lesson",

            # Tên học sinh nếu người nói gọi tên
            "nickname": nickname,

            # Môn học nếu người nói nói rõ
            "subject": subject,

            # Câu gốc
            "text": text,
        }


    # ========================================================
    # KHÔNG PHẢI LỆNH HỌC
    # ========================================================

    return {
        "intent": "chat",

        # Không tự ý lấy nickname trong chế độ chat
        "nickname": None,

        "subject": None,

        "text": text,
    }


# ============================================================
# CHUYỂN COMMAND THÀNH SESSION CONFIG
# ============================================================

def build_lesson_config(
    command,
    current_student=None,
    current_subject=None,
):

    if not isinstance(
        command,
        dict
    ):

        return {
            "start_lesson": False,
            "student": current_student,
            "subject": current_subject,
        }


    if command.get(
        "intent"
    ) != "start_lesson":

        return {
            "start_lesson": False,
            "student": current_student,
            "subject": current_subject,
        }


    # ========================================================
    # XÁC ĐỊNH HỌC SINH
    # ========================================================

    nickname = command.get(
        "nickname"
    )

    if nickname is None:

        nickname = current_student


    # ========================================================
    # XÁC ĐỊNH MÔN
    # ========================================================

    subject = command.get(
        "subject"
    )

    if subject is None:

        subject = current_subject


    # ========================================================
    # TRẢ SESSION CONFIG
    # ========================================================

    return {
        "start_lesson": True,

        "student": nickname,

        "subject": subject,

        "locked_student": nickname is not None,

        "locked_subject": subject is not None,
    }


# ============================================================
# TEST
# ============================================================

def demo():

    tests = [

        # ----------------------------------------------------
        # MINI
        # ----------------------------------------------------

        "Mini muốn học",

        "Mini muốn học Toán",

        "Mini học nha",

        "Cho Mini vào học",

        "Mini học đi",


        # ----------------------------------------------------
        # ĐẬU PHỘNG
        # ----------------------------------------------------

        "Đậu Phộng muốn học",

        "Đậu phụng muốn học",

        "Đậu Phộng muốn học Toán",

        "Cho Đậu Phộng vào học",

        "Đậu Phộng học nha",

        "dau phong muon hoc",


        # ----------------------------------------------------
        # ĐẬU ĐẬU
        # ----------------------------------------------------

        "Đậu Đậu muốn học",

        "Đậu đậu muốn học Toán",

        "Cho Đậu Đậu vào học",

        "Đậu Đậu học nha",

        "dau dau muon hoc",


        # ----------------------------------------------------
        # KHÔNG NÓI TÊN
        # ----------------------------------------------------

        "Con muốn học Toán",

        "Bắt đầu học",

        "Học đi",

        "Vô học nha",


        # ----------------------------------------------------
        # CHAT BÌNH THƯỜNG
        # ----------------------------------------------------

        "Lão sư hôm nay khỏe không?",

        "Tiểu Vũ đang làm gì đó?",

        "Hôm nay trời nóng quá",

    ]


    print()
    print("=" * 70)
    print("TIỂU VŨ - TUTOR TRIGGER V2 TEST")
    print("=" * 70)


    for text in tests:

        result = detect_tutor_command(
            text
        )

        print()
        print(
            "CÂU:",
            text
        )

        print(
            "KẾT QUẢ:",
            result
        )


        # ----------------------------------------------------
        # SESSION CONFIG
        # ----------------------------------------------------

        config = build_lesson_config(
            result
        )

        print(
            "SESSION:",
            config
        )


    print()
    print("=" * 70)
    print("TEST HOÀN TẤT")
    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    demo()