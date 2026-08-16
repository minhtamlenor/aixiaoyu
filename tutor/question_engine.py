# ============================================================
# TIỂU VŨ - QUESTION ENGINE
# CÂU HỎI THEO LỘ TRÌNH + KHỐI LỚP + HSK
# ============================================================

import random


def _q(question, answer, topic, hint="Con thử suy nghĩ từng bước nhé.", explanation=""):
    return {
        "question": question,
        "topic": topic,
        "answer": answer,
        "hint": hint,
        "explanation": explanation,
    }


def generate_math_question(topic="addition", strategy="practice"):
    if topic == "natural_numbers" or topic == "sets_and_natural_numbers":
        a = random.randint(20, 99)
        b = random.randint(10, 49)
        return _q(f"Số nào lớn hơn: {a} hay {b}?", str(max(a, b)), topic)
    if topic == "rounding_and_estimation":
        n = random.randint(100, 999)
        answer = round(n, -1)
        return _q(f"Làm tròn {n} đến hàng chục được bao nhiêu?", str(answer), topic)
    if topic in ("addition", "addition_subtraction"):
        a, b = random.randint(10, 500), random.randint(10, 500)
        return _q(f"{a} + {b} bằng bao nhiêu?", str(a + b), topic)
    if topic == "subtraction":
        a = random.randint(20, 800)
        b = random.randint(1, a)
        return _q(f"{a} - {b} bằng bao nhiêu?", str(a - b), topic)
    if topic in ("multiplication", "multiplication_division"):
        a, b = random.randint(2, 9), random.randint(2, 9)
        return _q(f"{a} × {b} bằng bao nhiêu?", str(a * b), topic)
    if topic == "division":
        b, answer = random.randint(2, 9), random.randint(2, 12)
        a = b * answer
        return _q(f"{a} ÷ {b} bằng bao nhiêu?", str(answer), topic)
    if topic == "fractions":
        a, b = random.randint(1, 4), random.randint(2, 9)
        return _q(f"Phân số nào biểu thị {a} phần trong {b} phần bằng nhau?", f"{a}/{b}", topic)
    if topic == "measurement_and_geometry":
        length = random.randint(3, 20)
        width = random.randint(2, 15)
        return _q(f"Hình chữ nhật dài {length} cm, rộng {width} cm. Diện tích là bao nhiêu cm²?", str(length * width), topic)
    if topic == "ratio_and_word_problems":
        each = random.randint(2, 9)
        groups = random.randint(3, 8)
        return _q(f"Có {groups} túi, mỗi túi {each} quả. Có tất cả bao nhiêu quả?", str(groups * each), topic)
    if topic == "divisibility_and_prime_numbers":
        return _q("Số nào sau đây là số nguyên tố: 9, 11 hay 15?", "11", topic)
    if topic == "integers":
        a, b = random.randint(-9, 9), random.randint(-9, 9)
        return _q(f"{a} + ({b}) bằng bao nhiêu?", str(a + b), topic)
    if topic == "fractions_and_rational_numbers":
        a, b = random.randint(1, 8), random.randint(2, 9)
        return _q(f"Phân số {a}/{b} có tử số là bao nhiêu?", str(a), topic)
    if topic == "ratios_and_percentages":
        p = random.choice([10, 20, 25, 50])
        n = random.choice([20, 40, 60, 80, 100])
        return _q(f"{p}% của {n} bằng bao nhiêu?", str(p * n // 100), topic)
    if topic == "algebraic_expressions":
        x = random.randint(1, 9)
        return _q(f"Nếu x = {x}, giá trị của 2x + 3 là bao nhiêu?", str(2 * x + 3), topic)
    if topic == "basic_geometry":
        return _q("Tổng số đo ba góc của một tam giác bằng bao nhiêu độ?", "180", topic)
    if topic in ("statistics_and_probability",):
        return _q("Khi gieo một đồng xu cân bằng, xác suất xuất hiện mặt ngửa là bao nhiêu?", "1/2", topic)
    if topic == "integrated_problem_solving":
        return _q("Một cửa hàng có 5 hộp, mỗi hộp 8 quyển vở. Bán 7 quyển. Còn lại bao nhiêu quyển?", "33", topic)
    return _q("12 + 8 bằng bao nhiêu?", "20", topic)


VIETNAMESE_BANK = {
    "reading_main_idea": [
        ("Khi đọc một đoạn văn, ý chính là gì?", "Nội dung quan trọng nhất mà đoạn văn muốn nói"),
        ("Muốn tìm ý chính, con nên chú ý điều gì?", "Các ý và câu quan trọng được lặp lại hoặc nhấn mạnh"),
    ],
    "vocabulary_and_dictionary": [
        ("Từ 'chăm chỉ' gần nghĩa với từ nào?", "siêng năng"),
    ],
    "nouns_verbs_adjectives": [
        ("Trong câu 'Em bé chạy nhanh', từ 'chạy' là từ loại gì?", "động từ"),
        ("Trong câu 'Bông hoa đẹp', từ 'đẹp' là từ loại gì?", "tính từ"),
    ],
    "sentences_and_punctuation": [
        ("Cuối câu hỏi thường dùng dấu gì?", "dấu chấm hỏi"),
    ],
    "literary_reading": [
        ("Khi phân tích nhân vật, con nên dựa vào những gì?", "hành động, lời nói, suy nghĩ và hoàn cảnh của nhân vật"),
    ],
    "myth_legend_and_folktale": [
        ("Truyền thuyết thường gắn với điều gì?", "nhân vật và sự kiện lịch sử được nhân dân lưu truyền"),
    ],
    "poetry_and_imagery": [
        ("Hình ảnh trong thơ giúp người đọc điều gì?", "hình dung và cảm nhận rõ hơn sự vật, cảm xúc"),
    ],
    "narrative_and_character": [
        ("Một bài văn tự sự thường có những yếu tố nào?", "nhân vật, sự việc và diễn biến câu chuyện"),
    ],
    "informational_text": [
        ("Văn bản thông tin chủ yếu nhằm làm gì?", "cung cấp thông tin và kiến thức"),
    ],
}

HISTORY_BANK = {
    "early_vietnamese_states": [("Nhà nước Văn Lang gắn với thời đại nào?", "các vua Hùng")],
    "dai_viet_ly_tran": [("Nhà Trần ba lần đánh bại quân xâm lược nào?", "quân Mông - Nguyên")],
    "le_so_and_lam_son": [("Ai lãnh đạo cuộc khởi nghĩa Lam Sơn?", "Lê Lợi")],
    "tay_son_and_quang_trung": [("Quang Trung là tên hiệu của ai?", "Nguyễn Huệ")],
    "nguyen_dynasty": [("Triều Nguyễn được thành lập vào năm nào?", "1802")],
    "prehistoric_humanity": [("Người tối cổ đã biết sử dụng công cụ chủ yếu làm từ gì?", "đá")],
    "ancient_mesopotamia_and_egypt": [("Nền văn minh Ai Cập cổ đại phát triển bên dòng sông nào?", "sông Nile")],
    "ancient_india_and_china": [("Một trong những con sông lớn gắn với văn minh Ấn Độ cổ đại là sông nào?", "sông Ấn")],
    "ancient_greece_and_rome": [("Thế vận hội Olympic cổ đại bắt nguồn từ nền văn minh nào?", "Hy Lạp")],
    "ancient_vietnam_van_lang_au_lac": [("Âu Lạc do ai lãnh đạo?", "An Dương Vương")],
    "vietnam_under_foreign_rule_and_resistance": [("Hai Bà Trưng khởi nghĩa chống lại ách đô hộ của triều đại nào?", "nhà Hán")],
}

GEOGRAPHY_BANK = {
    "maps_and_geographic_orientation": [("Bản đồ dùng để làm gì?", "thể hiện thu nhỏ bề mặt Trái Đất hoặc một khu vực")],
    "maps_coordinates_and_scale": [("Kinh tuyến gốc có số độ bao nhiêu?", "0°")],
    "earth_structure_and_movements": [("Trái Đất tự quay quanh trục theo hướng nào?", "từ tây sang đông")],
    "lithosphere_and_landforms": [("Núi là dạng địa hình có độ cao như thế nào so với vùng xung quanh?", "cao")],
    "atmosphere_weather_and_climate": [("Thời tiết và khí hậu khác nhau chủ yếu ở thời gian quan sát như thế nào?", "thời tiết ngắn hạn, khí hậu dài hạn")],
    "hydrosphere_rivers_and_oceans": [("Nguồn nước nào chiếm phần lớn diện tích nước trên Trái Đất?", "nước mặn")],
    "biosphere_soils_and_ecosystems": [("Hệ sinh thái gồm những thành phần cơ bản nào?", "sinh vật và môi trường sống của chúng")],
}

LIFE_BANK = {
    "eq": [
        ("Khi bạn đang nói mà bạn mình ngắt lời, con nên làm gì trước?", "bình tĩnh, lắng nghe và nói lại nhu cầu của mình một cách lịch sự"),
        ("Nếu thấy bạn buồn, một cách thể hiện sự đồng cảm là gì?", "hỏi thăm và lắng nghe bạn"),
    ],
    "problem_solving": [
        ("Bước đầu tiên khi gặp một vấn đề là gì?", "xác định rõ vấn đề"),
        ("Tại sao nên nghĩ ra nhiều phương án trước khi chọn một giải pháp?", "để so sánh và chọn phương án phù hợp hơn"),
    ],
    "emotional_management": [
        ("Khi đang rất tức giận, việc đầu tiên nên làm là gì?", "dừng lại và bình tĩnh trước khi phản ứng"),
        ("Gọi đúng tên cảm xúc giúp ích gì?", "giúp mình hiểu và điều chỉnh cảm xúc tốt hơn"),
    ],
}

CHINESE_BANK = {
    "greetings_and_politeness": [
        ("“你好”是什么意思？", "xin chào"),
        ("“谢谢”是什么意思？", "cảm ơn"),
    ],
    "self_introduction": [
        ("“你叫什么名字？”怎么回答？", "我叫……"),
    ],
    "family_and_people": [
        ("“妈妈”是什么意思？", "mẹ"),
        ("“弟弟”是什么意思？", "em trai"),
    ],
    "numbers_age_and_time": [
        ("“你几岁？”怎么回答？", "我……岁。"),
    ],
    "school_and_daily_routine": [
        ("“学校”是什么意思？", "trường học"),
        ("“老师”是什么意思？", "giáo viên"),
    ],
    "food_and_drink": [
        ("“你喜欢喝什么？”怎么回答？", "我喜欢喝……"),
    ],
    "shopping_and_prices": [
        ("“多少钱？”是什么意思？", "bao nhiêu tiền"),
    ],
    "personal_information_and_relationships": [
        ("“你住在哪里？”怎么回答？", "我住在……"),
        ("“你跟谁一起学习？”怎么回答？", "我跟……一起学习。"),
    ],
    "school_learning_and_plans": [
        ("“你明天有什么计划？”怎么回答？", "我明天要……"),
    ],
    "daily_life_and_time_management": [
        ("“你每天几点起床？”怎么回答？", "我每天……点起床。"),
    ],
    "health_and_lifestyle": [
        ("“你怎么了？”常用来问什么？", "hỏi xem một người có chuyện gì hoặc không khỏe thế nào"),
    ],
    "travel_transport_and_directions": [
        ("“怎么去学校？”是什么意思？", "đi đến trường bằng cách nào"),
    ],
    "hobbies_media_and_experiences": [
        ("“你喜欢做什么？”怎么回答？", "我喜欢……"),
    ],
    "shopping_services_and_social_life": [
        ("“可以便宜一点吗？”常用于什么场景？", "mua sắm và thương lượng giá"),
    ],
    "opinions_reasons_and_comparisons": [
        ("“为什么？”是什么意思？", "tại sao"),
        ("“我觉得……”常用来表达什么？", "ý kiến hoặc cảm nhận của mình"),
    ],
    "culture_and_everyday_china": [
        ("春节是中国的什么节日？", "một trong những lễ hội truyền thống quan trọng nhất của Trung Quốc"),
    ],
}


def _bank_question(bank, topic):
    items = bank.get(topic) or []
    if not items:
        return None
    question, answer = random.choice(items)
    return _q(question, answer, topic)


def generate_question(student_id=None, subject_id="math", topic="addition", strategy="practice"):
    if subject_id == "math":
        return generate_math_question(topic, strategy)
    if subject_id == "vietnamese":
        return _bank_question(VIETNAMESE_BANK, topic) or _q("Con hãy nói một câu rõ nghĩa.", "", topic)
    if subject_id == "history":
        return _bank_question(HISTORY_BANK, topic) or _q("Con hãy kể một sự kiện lịch sử con đã học.", "", topic)
    if subject_id == "geography":
        return _bank_question(GEOGRAPHY_BANK, topic) or _q("Con hãy nói một điều con biết về địa lý.", "", topic)
    if subject_id in LIFE_BANK:
        return _bank_question(LIFE_BANK, topic) or _bank_question(LIFE_BANK, subject_id) or _q("Con sẽ xử lý tình huống này thế nào?", "", topic)
    if subject_id == "chinese":
        return _bank_question(CHINESE_BANK, topic) or _q("你今天感觉怎么样？", "很好", topic)
    if subject_id == "english":
        return _q("What is the opposite of 'big'?", "small", topic)
    return _q("Con thử suy nghĩ về câu hỏi này nhé.", "", topic)


def check_answer(question_data, user_answer):
    if not isinstance(question_data, dict):
        return {"correct": False, "message": "Tiểu Vũ chưa có dữ liệu câu hỏi."}
    correct_answer = question_data.get("answer")
    if correct_answer in (None, ""):
        return {"correct": True, "message": "Câu trả lời mở đã được ghi nhận.", "explanation": question_data.get("explanation", "")}
    user = str(user_answer).strip().lower()
    correct = str(correct_answer).strip().lower()
    if user == correct or correct in user:
        return {"correct": True, "message": "Đúng rồi!", "explanation": question_data.get("explanation", "")}
    return {"correct": False, "message": "Không sao, mình thử lại nhé.", "hint": question_data.get("hint", "Con thử suy nghĩ từng bước nhé.")}


def get_hint(question_data):
    return question_data.get("hint", "Con thử suy nghĩ thêm một chút nhé.") if isinstance(question_data, dict) else "Con thử suy nghĩ thêm một chút nhé."


def get_explanation(question_data):
    return question_data.get("explanation", "") if isinstance(question_data, dict) else ""


if __name__ == "__main__":
    print(generate_question("minh_tien", "math", "fractions", "practice"))
