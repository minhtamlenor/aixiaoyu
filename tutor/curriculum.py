# ============================================================
# TIỂU VŨ - CHƯƠNG TRÌNH GIA SƯ
# LỘ TRÌNH THEO KHỐI LỚP + MÔN HỌC
# ============================================================

SUBJECTS = {
    "math": {
        "name": "Toán",
        "description": "Toán học, tư duy logic, tính toán và giải quyết vấn đề thực tế.",
    },
    "vietnamese": {
        "name": "Tiếng Việt",
        "description": "Đọc hiểu, tiếng Việt, viết, nói và nghe; ưu tiên vận dụng.",
    },
    "english": {
        "name": "Tiếng Anh",
        "description": "Từ vựng, giao tiếp, nghe, nói, đọc và viết.",
    },
    "chinese": {
        "name": "Tiếng Trung",
        "description": "HSK 3.0 theo trình độ từng học sinh; nghe, nói, đọc, từ vựng và phản xạ.",
    },
    "history": {
        "name": "Lịch sử",
        "description": "Lịch sử theo tiến trình, nhân vật, sự kiện, nguyên nhân - diễn biến - kết quả - ý nghĩa.",
    },
    "geography": {
        "name": "Địa lý",
        "description": "Bản đồ, tự nhiên, dân cư, kinh tế, môi trường và vận dụng vào địa phương.",
    },
    "eq": {
        "name": "Kỹ năng EQ và giao tiếp",
        "description": "Nhận biết người khác, lắng nghe, giao tiếp tử tế, hợp tác và xây dựng quan hệ.",
    },
    "problem_solving": {
        "name": "Kỹ năng giải quyết vấn đề",
        "description": "Xác định vấn đề, tìm nguyên nhân, tạo phương án, lựa chọn và kiểm tra giải pháp.",
    },
    "emotional_management": {
        "name": "Quản lý cảm xúc",
        "description": "Nhận biết, gọi tên, điều chỉnh cảm xúc và lựa chọn phản ứng phù hợp.",
    },
}

# ============================================================
# LỘ TRÌNH CHÍNH
# Mỗi môn có một chuỗi chủ đề. Tiểu Vũ đi theo thứ tự, nhưng
# có thể quay lại chủ đề yếu dựa trên progress.
# ============================================================

CURRICULUM = {
    4: {
        "math": [
            "natural_numbers",
            "rounding_and_estimation",
            "addition_subtraction",
            "multiplication_division",
            "fractions",
            "measurement_and_geometry",
            "ratio_and_word_problems",
            "statistics_and_probability",
            "integrated_problem_solving",
        ],
        "vietnamese": [
            "reading_main_idea",
            "vocabulary_and_dictionary",
            "nouns_verbs_adjectives",
            "sentences_and_punctuation",
            "reading_inference",
            "descriptive_writing",
            "narrative_writing",
            "speaking_and_listening",
            "integrated_language_practice",
        ],
        "history": [
            "early_vietnamese_states",
            "dai_viet_ly_tran",
            "le_so_and_lam_son",
            "tay_son_and_quang_trung",
            "nguyen_dynasty",
            "heroes_and_historical_figures",
            "culture_and_historical_heritage",
            "timeline_and_historical_thinking",
        ],
        "geography": [
            "maps_and_geographic_orientation",
            "northern_vietnam",
            "north_central_and_central_coast",
            "central_highlands",
            "southeastern_vietnam",
            "mekong_delta",
            "population_and_economic_activities",
            "local_environment_and_sustainability",
        ],
        "chinese_hsk1": [
            "greetings_and_politeness",
            "self_introduction",
            "family_and_people",
            "numbers_age_and_time",
            "school_and_daily_routine",
            "food_and_drink",
            "shopping_and_prices",
            "weather_and_daily_life",
            "likes_and_simple_preferences",
            "hsk1_integrated_review",
        ],
        "chinese": [
            "greetings_and_politeness",
            "self_introduction",
            "family_and_people",
            "numbers_age_and_time",
            "school_and_daily_routine",
            "food_and_drink",
            "shopping_and_prices",
            "weather_and_daily_life",
            "likes_and_simple_preferences",
            "hsk1_integrated_review",
        ],
    },
    6: {
        "math": [
            "sets_and_natural_numbers",
            "divisibility_and_prime_numbers",
            "integers",
            "fractions_and_rational_numbers",
            "ratios_and_percentages",
            "algebraic_expressions",
            "basic_geometry",
            "statistics_and_probability",
            "integrated_problem_solving",
        ],
        "vietnamese": [
            "literary_reading",
            "myth_legend_and_folktale",
            "poetry_and_imagery",
            "narrative_and_character",
            "informational_text",
            "vietnamese_language_in_context",
            "experience_and_narrative_writing",
            "opinion_and_presentation",
            "integrated_language_practice",
        ],
        "history": [
            "prehistoric_humanity",
            "ancient_mesopotamia_and_egypt",
            "ancient_india_and_china",
            "ancient_greece_and_rome",
            "southeast_asia_ancient_states",
            "ancient_vietnam_van_lang_au_lac",
            "vietnam_under_foreign_rule_and_resistance",
            "historical_sources_and_timeline",
        ],
        "geography": [
            "maps_coordinates_and_scale",
            "earth_structure_and_movements",
            "lithosphere_and_landforms",
            "atmosphere_weather_and_climate",
            "hydrosphere_rivers_and_oceans",
            "biosphere_soils_and_ecosystems",
            "population_human_environment",
            "local_fieldwork_and_sustainability",
        ],
        "chinese_hsk3": [
            "personal_information_and_relationships",
            "school_learning_and_plans",
            "daily_life_and_time_management",
            "health_and_lifestyle",
            "travel_transport_and_directions",
            "hobbies_media_and_experiences",
            "shopping_services_and_social_life",
            "opinions_reasons_and_comparisons",
            "culture_and_everyday_china",
            "hsk3_integrated_review",
        ],
        "chinese": [
            "personal_information_and_relationships",
            "school_learning_and_plans",
            "daily_life_and_time_management",
            "health_and_lifestyle",
            "travel_transport_and_directions",
            "hobbies_media_and_experiences",
            "shopping_services_and_social_life",
            "opinions_reasons_and_comparisons",
            "culture_and_everyday_china",
            "hsk3_integrated_review",
        ],
    },
}

# ============================================================
# KỸ NĂNG LINH ĐỘNG - KHÔNG GẮN CỨNG THEO MỘT BỘ SGK
# ============================================================

LIFE_SKILLS = {
    "eq": [
        "listen_before_responding",
        "express_needs_politely",
        "empathy_and_perspective",
        "respectful_disagreement",
        "teamwork_and_turn_taking",
        "asking_for_help",
        "apologizing_and_repairing",
        "building_trust_and_friendship",
    ],
    "problem_solving": [
        "identify_the_real_problem",
        "separate_facts_and_assumptions",
        "find_root_causes",
        "generate_multiple_options",
        "compare_tradeoffs",
        "make_a_plan",
        "test_and_adjust",
        "learn_from_failure",
    ],
    "emotional_management": [
        "name_the_emotion",
        "notice_body_signals",
        "pause_before_reacting",
        "breathing_and_reset",
        "handle_frustration",
        "handle_disappointment",
        "handle_conflict",
        "self_compassion_and_recovery",
    ],
}


def get_subject(subject_id):
    return SUBJECTS.get(subject_id)


def get_subject_list():
    return list(SUBJECTS.keys())


def get_curriculum(student_grade, subject_id, chinese_level=None):
    grade_data = CURRICULUM.get(student_grade, {})

    if subject_id == "chinese":
        if chinese_level == "hsk3" or student_grade >= 6:
            return grade_data.get("chinese_hsk3", grade_data.get("chinese", []))
        return grade_data.get("chinese_hsk1", grade_data.get("chinese", []))

    if subject_id in LIFE_SKILLS:
        return LIFE_SKILLS[subject_id]

    return grade_data.get(subject_id, [])


def get_first_topic(student_grade, subject_id, chinese_level=None):
    path = get_curriculum(student_grade, subject_id, chinese_level)
    return path[0] if path else "introduction"


def get_next_topic(student_grade, subject_id, current_topic, chinese_level=None):
    path = get_curriculum(student_grade, subject_id, chinese_level)
    if not path:
        return "introduction"
    if current_topic not in path:
        return path[0]
    index = path.index(current_topic)
    return path[(index + 1) % len(path)]


def get_topic_index(student_grade, subject_id, topic, chinese_level=None):
    path = get_curriculum(student_grade, subject_id, chinese_level)
    try:
        return path.index(topic)
    except ValueError:
        return 0
