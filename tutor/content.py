# ============================================================
# TIỂU VŨ - LESSON CONTENT ENGINE
# BỘ MÁY TẠO NỘI DUNG BÀI HỌC
# ============================================================

from tutor.curriculum import get_subject
from tutor.adaptive import (
    STRATEGY_NAMES,
    STRATEGY_DESCRIPTIONS,
)


# ============================================================
# CÁC DẠNG HOẠT ĐỘNG
# ============================================================

ACTIVITY_TYPES = [
    "warm_up",
    "example",
    "question",
    "practice",
    "game",
    "challenge",
    "reflection",
]


# ============================================================
# CẤU TRÚC BÀI HỌC
# ============================================================

LESSON_STRUCTURES = {

    "introduce": [
        "warm_up",
        "example",
        "question",
        "practice",
        "practice",
    ],

    "review": [
        "warm_up",
        "simple_example",
        "hint",
        "question",
        "retry",
    ],

    "practice": [
        "warm_up",
        "question",
        "practice",
        "game",
        "practice",
    ],

    "advance": [
        "warm_up",
        "challenge",
        "reasoning",
        "challenge",
        "reflection",
    ],
}


# ============================================================
# TÊN HOẠT ĐỘNG
# ============================================================

ACTIVITY_NAMES = {

    "warm_up": "Khởi động",

    "example": "Ví dụ",

    "simple_example": "Ví dụ đơn giản",

    "question": "Câu hỏi",

    "practice": "Luyện tập",

    "hint": "Gợi ý",

    "retry": "Thử lại",

    "game": "Trò chơi",

    "challenge": "Thử thách",

    "reasoning": "Suy luận",

    "reflection": "Suy ngẫm",
}


# ============================================================
# MÔ TẢ HOẠT ĐỘNG
# ============================================================

ACTIVITY_DESCRIPTIONS = {

    "warm_up": (
        "Khởi động nhẹ nhàng để trẻ tập trung "
        "và kết nối với kiến thức."
    ),

    "example": (
        "Đưa ra một ví dụ gần gũi "
        "để trẻ hiểu khái niệm."
    ),

    "simple_example": (
        "Quay về ví dụ rất đơn giản "
        "để củng cố nền tảng."
    ),

    "question": (
        "Đặt một câu hỏi vừa sức "
        "để trẻ tự suy nghĩ."
    ),

    "practice": (
        "Cho trẻ luyện tập và tự đưa ra câu trả lời."
    ),

    "hint": (
        "Đưa một gợi ý nhỏ thay vì nói đáp án."
    ),

    "retry": (
        "Cho trẻ cơ hội thử lại."
    ),

    "game": (
        "Biến kiến thức thành trò chơi hoặc thử thách vui."
    ),

    "challenge": (
        "Đưa ra một câu hỏi khó hơn "
        "đòi hỏi suy luận."
    ),

    "reasoning": (
        "Yêu cầu trẻ giải thích vì sao "
        "con nghĩ như vậy."
    ),

    "reflection": (
        "Giúp trẻ nhìn lại cách mình suy nghĩ "
        "và điều vừa học."
    ),
}


# ============================================================
# NỘI DUNG THEO MÔN
# ============================================================

SUBJECT_CONTENT = {

    # ========================================================
    # TOÁN
    # ========================================================

    "math": {

        "addition": {
            "concept": "Phép cộng",
            "examples": [
                "Con có 2 quả táo, mẹ cho thêm 3 quả. Con có tất cả bao nhiêu quả?",
                "2 cộng 3 nghĩa là bắt đầu từ 2 rồi thêm 3 đơn vị.",
            ],
            "skills": [
                "đếm",
                "cộng",
                "tư duy số",
                "giải bài toán có lời văn",
            ],
        },

        "subtraction": {
            "concept": "Phép trừ",
            "examples": [
                "Có 7 chiếc bánh, ăn mất 2 chiếc. Còn lại bao nhiêu chiếc?",
            ],
            "skills": [
                "đếm ngược",
                "trừ",
                "so sánh số lượng",
            ],
        },

        "multiplication": {
            "concept": "Phép nhân",
            "examples": [
                "Có 3 túi, mỗi túi có 2 quả táo. Có tất cả bao nhiêu quả?",
            ],
            "skills": [
                "nhóm bằng nhau",
                "phép nhân",
                "tư duy nhanh",
            ],
        },

        "division": {
            "concept": "Phép chia",
            "examples": [
                "Có 12 cái bánh chia đều cho 3 bạn. Mỗi bạn được mấy cái?",
            ],
            "skills": [
                "chia đều",
                "nhóm",
                "phép chia",
            ],
        },

        "geometry": {
            "concept": "Hình học",
            "examples": [
                "Hình vuông có 4 cạnh bằng nhau.",
            ],
            "skills": [
                "nhận biết hình",
                "đo lường",
                "không gian",
            ],
        },

        "logic": {
            "concept": "Tư duy logic",
            "examples": [
                "Nếu hôm nay là thứ Hai thì ngày mai là thứ mấy?",
            ],
            "skills": [
                "suy luận",
                "nhận dạng quy luật",
                "giải quyết vấn đề",
            ],
        },
    },


    # ========================================================
    # TIẾNG VIỆT
    # ========================================================

    "vietnamese": {

        "reading": {
            "concept": "Đọc hiểu",
            "skills": [
                "đọc",
                "hiểu nội dung",
                "tìm ý chính",
            ],
        },

        "vocabulary": {
            "concept": "Từ vựng",
            "skills": [
                "hiểu nghĩa từ",
                "đặt câu",
                "mở rộng vốn từ",
            ],
        },

        "writing": {
            "concept": "Viết và diễn đạt",
            "skills": [
                "đặt câu",
                "miêu tả",
                "kể chuyện",
            ],
        },
    },


    # ========================================================
    # TIẾNG ANH
    # ========================================================

    "english": {

        "vocabulary": {
            "concept": "Từ vựng tiếng Anh",
            "skills": [
                "nhớ từ",
                "phát âm",
                "sử dụng từ",
            ],
        },

        "conversation": {
            "concept": "Giao tiếp tiếng Anh",
            "skills": [
                "nghe",
                "nói",
                "phản xạ",
            ],
        },
    },


    # ========================================================
    # TIẾNG TRUNG
    # ========================================================

    "chinese": {

        "vocabulary": {
            "concept": "Từ vựng tiếng Trung",
            "skills": [
                "Hán tự",
                "pinyin",
                "nghĩa",
                "phát âm",
            ],
        },

        "conversation": {
            "concept": "Giao tiếp tiếng Trung",
            "skills": [
                "nghe",
                "nói",
                "phản xạ",
            ],
        },
    },


    # ========================================================
    # LỊCH SỬ
    # ========================================================

    "history": {

        "story": {
            "concept": "Lịch sử qua câu chuyện",
            "skills": [
                "ghi nhớ sự kiện",
                "hiểu nguyên nhân",
                "hiểu kết quả",
            ],
        },
    },


    # ========================================================
    # ĐỊA LÝ
    # ========================================================

    "geography": {

        "map": {
            "concept": "Bản đồ và địa lý",
            "skills": [
                "đọc bản đồ",
                "định hướng",
                "địa danh",
            ],
        },
    },


    # ========================================================
    # EQ
    # ========================================================

    "eq": {

        "communication": {
            "concept": "Giao tiếp tử tế và thông minh",
            "skills": [
                "lắng nghe",
                "diễn đạt",
                "thấu hiểu",
                "tôn trọng",
            ],
        },

        "empathy": {
            "concept": "Thấu hiểu cảm xúc người khác",
            "skills": [
                "nhận biết cảm xúc",
                "đặt mình vào vị trí người khác",
                "phản hồi phù hợp",
            ],
        },

        "boundaries": {
            "concept": "Ranh giới cá nhân",
            "skills": [
                "biết nói không",
                "tự bảo vệ",
                "tôn trọng người khác",
            ],
        },
    },


    # ========================================================
    # GIẢI QUYẾT VẤN ĐỀ
    # ========================================================

    "problem_solving": {

        "basic": {
            "concept": "Giải quyết vấn đề cơ bản",
            "skills": [
                "xác định vấn đề",
                "tìm nguyên nhân",
                "tìm phương án",
            ],
        },

        "reasoning": {
            "concept": "Suy luận",
            "skills": [
                "phân tích",
                "so sánh",
                "dự đoán hậu quả",
            ],
        },
    },


    # ========================================================
    # QUẢN LÝ CẢM XÚC
    # ========================================================

    "emotional_management": {

        "recognition": {
            "concept": "Nhận biết cảm xúc",
            "skills": [
                "gọi tên cảm xúc",
                "nhận biết dấu hiệu cơ thể",
            ],
        },

        "regulation": {
            "concept": "Điều chỉnh cảm xúc",
            "skills": [
                "hít thở",
                "tạm dừng",
                "suy nghĩ trước khi phản ứng",
            ],
        },

        "anger": {
            "concept": "Xử lý cơn giận",
            "skills": [
                "nhận biết cơn giận",
                "tạm dừng",
                "diễn đạt cảm xúc",
            ],
        },
    },
}


# ============================================================
# LẤY NỘI DUNG CHỦ ĐỀ
# ============================================================

def get_topic_content(
    subject_id,
    topic,
):

    subject_data = SUBJECT_CONTENT.get(
        subject_id,
        {}
    )

    content = subject_data.get(
        topic
    )

    if content:

        return content

    return {
        "concept": topic,
        "examples": [],
        "skills": [],
    }


# ============================================================
# TẠO HOẠT ĐỘNG
# ============================================================

def create_activity(
    subject_id,
    topic,
    strategy,
    activity_type,
    step,
):

    content = get_topic_content(
        subject_id,
        topic,
    )

    return {

        "step": step,

        "type": activity_type,

        "name": ACTIVITY_NAMES.get(
            activity_type,
            activity_type,
        ),

        "description": ACTIVITY_DESCRIPTIONS.get(
            activity_type,
            "",
        ),

        "subject_id": subject_id,

        "topic": topic,

        "concept": content.get(
            "concept",
            topic,
        ),

        "skills": content.get(
            "skills",
            [],
        ),

        "examples": content.get(
            "examples",
            [],
        ),

        "strategy": strategy,

        "strategy_name": STRATEGY_NAMES.get(
            strategy,
            strategy,
        ),
    }


# ============================================================
# TẠO TOÀN BỘ BÀI HỌC
# ============================================================

def create_lesson_content(
    subject_id,
    topic,
    strategy="introduce",
):

    subject = get_subject(
        subject_id
    )

    if not subject:

        raise ValueError(
            f"Không tìm thấy môn học: {subject_id}"
        )

    structure = LESSON_STRUCTURES.get(
        strategy,
        LESSON_STRUCTURES["introduce"],
    )

    activities = []

    for index, activity_type in enumerate(
        structure,
        start=1,
    ):

        activity = create_activity(
            subject_id=subject_id,
            topic=topic,
            strategy=strategy,
            activity_type=activity_type,
            step=index,
        )

        activities.append(
            activity
        )

    return {

        "subject_id": subject_id,

        "subject_name": subject["name"],

        "topic": topic,

        "strategy": strategy,

        "strategy_name": STRATEGY_NAMES.get(
            strategy,
            strategy,
        ),

        "strategy_description": (
            STRATEGY_DESCRIPTIONS.get(
                strategy,
                "",
            )
        ),

        "activities": activities,

        "total_steps": len(
            activities
        ),

        "status": "ready",
    }


# ============================================================
# LẤY HOẠT ĐỘNG TIẾP THEO
# ============================================================

def get_activity(
    lesson,
    step,
):

    activities = lesson.get(
        "activities",
        []
    )

    if step < 1:

        step = 1

    if step > len(activities):

        return None

    return activities[
        step - 1
    ]


# ============================================================
# KIỂM TRA
# ============================================================

if __name__ == "__main__":

    lesson = create_lesson_content(
        "math",
        "addition",
        "introduce",
    )

    print()
    print("=" * 60)
    print("TIỂU VŨ - CONTENT ENGINE")
    print("=" * 60)

    print()

    print(
        "MÔN:",
        lesson["subject_name"]
    )

    print(
        "CHỦ ĐỀ:",
        lesson["topic"]
    )

    print(
        "CHIẾN LƯỢC:",
        lesson["strategy_name"]
    )

    print()

    for activity in lesson["activities"]:

        print(
            f"Step {activity['step']}: "
            f"{activity['type']} "
            f"→ {activity['name']}"
        )

    print()
    print("=" * 60)