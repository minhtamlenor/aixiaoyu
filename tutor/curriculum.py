# ============================================================
# TIỂU VŨ - CHƯƠNG TRÌNH GIA SƯ
# ============================================================

SUBJECTS = {

    "math": {
        "name": "Toán",
        "description": (
            "Toán học, tư duy logic, tính toán và giải bài toán."
        ),
    },

    "vietnamese": {
        "name": "Tiếng Việt",
        "description": (
            "Đọc hiểu, từ vựng, ngữ pháp, viết và diễn đạt."
        ),
    },

    "english": {
        "name": "Tiếng Anh",
        "description": (
            "Từ vựng, giao tiếp, nghe, nói, đọc và viết."
        ),
    },

    "chinese": {
        "name": "Tiếng Trung",
        "description": (
            "Hán tự, pinyin, từ vựng, giao tiếp và nghe nói."
        ),
    },

    "history": {
        "name": "Lịch sử",
        "description": (
            "Kiến thức lịch sử thông qua câu chuyện và nhân vật."
        ),
    },

    "geography": {
        "name": "Địa lý",
        "description": (
            "Địa lý Việt Nam và thế giới, bản đồ, "
            "khí hậu, con người và môi trường."
        ),
    },

    "eq": {
        "name": "Kỹ năng EQ và giao tiếp",
        "description": (
            "Giao tiếp tử tế, lắng nghe, thấu hiểu người khác, "
            "xử lý tình huống xã hội và xây dựng quan hệ tốt."
        ),
    },

    "problem_solving": {
        "name": "Kỹ năng giải quyết vấn đề",
        "description": (
            "Phân tích vấn đề, tìm nguyên nhân, "
            "đưa ra phương án và lựa chọn giải pháp."
        ),
    },

    "emotional_management": {
        "name": "Quản lý cảm xúc",
        "description": (
            "Nhận biết cảm xúc, gọi tên cảm xúc, "
            "điều chỉnh cảm xúc và phản ứng phù hợp."
        ),
    },
}


def get_subject(subject_id):
    return SUBJECTS.get(subject_id)


def get_subject_list():
    return list(SUBJECTS.keys())