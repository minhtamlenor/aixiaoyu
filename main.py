# ============================================================
# TIỂU VŨ - MAIN
# ============================================================

import datetime
import voice

from student_memory import (
    build_memory_instruction,
    remember_preferences,
)
from tutor.adaptive import create_learning_plan
from tutor.curriculum import get_curriculum
from tutor.students import get_chinese_level, get_grade


# ------------------------------------------------------------
# BỘ NHỚ + LỘ TRÌNH GIA SƯ
# ------------------------------------------------------------
# Không sửa voice.py để giữ nguyên voice runtime đang ổn.
# Wrapper này chỉ bổ sung:
#   1. trí nhớ sở thích,
#   2. lộ trình học theo lớp + môn,
#   3. mode giao tiếp tiếng Trung theo HSK của từng bé.
# Không tạo thêm voice_fixed hay file voice phụ.
# ------------------------------------------------------------


def _is_chinese_conversation_request(text):
    normalized = voice.normalize_text(text)
    compact = voice.remove_accents(normalized)
    patterns = [
        "giao tiếp tiếng trung",
        "giao tiep tieng trung",
        "giao tiep tieng trung",
        "giao tiếp bằng tiếng trung",
        "giao tiep bang tieng trung",
        "luyện nói tiếng trung",
        "luyen noi tieng trung",
        "luyện giao tiếp tiếng trung",
        "luyen giao tiep tieng trung",
        "nói chuyện bằng tiếng trung",
        "noi chuyen bang tieng trung",
        "nói tiếng trung với con",
        "noi tieng trung voi con",
    ]
    return any(
        pattern in normalized or voice.remove_accents(pattern) in compact
        for pattern in patterns
    )


def _build_curriculum_instruction(student_id, subject):
    """Tạo chỉ dẫn lộ trình ngắn cho Gemini, không thay đổi voice engine."""
    try:
        plan = create_learning_plan(student_id, subject)
    except Exception:
        return ""

    roadmap = plan.get("roadmap") or get_curriculum(
        get_grade(student_id),
        subject,
        get_chinese_level(student_id) if subject == "chinese" else None,
    )

    topic_index = plan.get("topic_index", 1)
    topic_total = plan.get("topic_total", len(roadmap))
    current_topic = plan.get("topic", "introduction")
    strategy = plan.get("strategy_name", "Giới thiệu")

    roadmap_text = " → ".join(roadmap)

    review_rule = (
        "Sau mỗi vài chủ đề phải xen kẽ một lượt ôn tập ngắn; thỉnh thoảng dùng bài test từ vựng/ngữ pháp để kiểm tra mức độ nhớ bài, không biến mọi lượt học thành bài kiểm tra."
    )

    chinese_rule = ""
    if subject == "chinese":
        level = get_chinese_level(student_id)
        chinese_rule = f"""
TIẾNG TRUNG:
- Trình độ bắt buộc: {level.upper()} theo HSK 3.0.
- Không dùng từ/cấu trúc vượt trình độ một cách tùy tiện.
- Trong giờ học tiếng Trung thông thường: dạy từ vựng, ngữ pháp, nghe hiểu, đặt câu và đọc hiểu theo lộ trình.
- Định kỳ kiểm tra lại từ vựng + ngữ pháp đúng trình độ {level.upper()}.
- Khi Lão sư yêu cầu giao tiếp tiếng Trung, chuyển sang CHINESE CONVERSATION MODE; lúc đó ưu tiên hội thoại và phản xạ, không giảng bài dài.
"""

    return f"""
LỘ TRÌNH GIA SƯ BẮT BUỘC:
- Môn: {subject}
- Chủ đề hiện tại: {current_topic} ({topic_index}/{topic_total})
- Chiến lược hiện tại: {strategy}
- Roadmap: {roadmap_text}
- {review_rule}
{chinese_rule}
Không random chủ đề vô hạn. Dạy theo roadmap, dựa vào kết quả của bé để ôn lại điểm yếu hoặc chuyển sang chủ đề kế tiếp.
"""


async def _start_tutor_session_with_memory(session, student, subject=None, switching=False):
    # Khi chỉ nhắc tên bé mà chưa nói môn, vẫn chuyển sang Tutor Mode
    # nhưng TUYỆT ĐỐI không mặc định sang Tiếng Trung. Hỏi bé muốn học môn nào.
    if subject is None:
        voice.current_mode = voice.TUTOR_MODE
        voice.current_student = student["called_name"]
        voice.current_student_id = student["student_id"]
        voice.current_subject = None
        voice.current_grade = student["grade"]

        memory_instruction = build_memory_instruction(
            student["student_id"],
            student["official_name"],
        )
        subject_prompt = f"""
TUTOR MODE ĐÃ BẬT CHO {student['called_name']}.

Học sinh: {student['called_name']}
Tên chính thức: {student['official_name']}
Lớp: {student['grade']}

QUAN TRỌNG:
- Chưa có môn học được chọn.
- KHÔNG được tự mặc định Tiếng Trung, dù Tiếng Trung là môn ưu tiên.
- Hãy hỏi {student['called_name']} muốn học môn nào.
- Có thể chọn: Toán, Tiếng Việt, Tiếng Anh, Lịch sử, Địa lý, Tiếng Trung, Kỹ năng giao tiếp, Kỹ năng xử lý vấn đề hoặc EQ/quản lý cảm xúc.
- Chỉ hỏi đúng MỘT câu ngắn rồi DỪNG để bé chọn.
- Không bắt đầu bài học trước khi bé chọn môn.
"""
        print(
            f"🎓 BẮT ĐẦU GIA SƯ: {student['called_name']} — CHỜ CHỌN MÔN",
            flush=True,
        )
        combined = "\n".join(
            part for part in [memory_instruction, subject_prompt] if part
        )
        await session.send_realtime_input(text=combined)
        return

    await _original_start_tutor_session(
        session,
        student,
        subject,
        switching=switching,
    )

    student_id = student["student_id"]
    active_subject = subject

    memory_instruction = build_memory_instruction(
        student_id,
        student["official_name"],
    )
    curriculum_instruction = _build_curriculum_instruction(
        student_id,
        active_subject,
    )

    combined = "\n".join(
        part for part in [memory_instruction, curriculum_instruction] if part
    )
    if combined:
        await session.send_realtime_input(text=combined)


def _current_student_record():
    """Lấy lại record học sinh hiện tại với called_name để dùng khi bé chọn môn."""
    if not voice.current_student_id:
        return None
    current = voice.STUDENTS.get(voice.current_student_id)
    if not current:
        return None
    return {
        **current,
        "called_name": voice.current_student,
        "official_name": current.get("official_name", voice.current_student),
    }


async def _start_chinese_conversation(session, student):
    """Bật riêng mode giao tiếp tiếng Trung, không tạo lesson engine mới."""
    voice.current_mode = voice.TUTOR_MODE
    voice.current_student = student["called_name"]
    voice.current_student_id = student["student_id"]
    voice.current_subject = "chinese"
    voice.current_grade = student["grade"]
    voice.last_subject = "chinese"
    if "chinese" in voice.SUBJECT_ROTATION:
        voice.rotation_index = voice.SUBJECT_ROTATION.index("chinese")

    level = get_chinese_level(student["student_id"])
    grade = get_grade(student["student_id"])

    prompt = f"""
CHINESE CONVERSATION MODE — ĐÃ BẬT.

Học sinh: {student['called_name']}
Lớp: {grade}
Trình độ tiếng Trung: {level.upper()} theo HSK 3.0.

MỤC TIÊU:
- Luyện giao tiếp tiếng Trung thực tế, nghe hiểu và phản xạ nói.
- Chỉ dùng từ vựng, mẫu câu và độ khó phù hợp {level.upper()}.
- Hỏi đáp tự nhiên theo trình độ của bé; chủ đề gần gũi với trẻ.
- Mỗi lượt chỉ nói một câu hỏi hoặc một lượt hội thoại ngắn rồi DỪNG để bé trả lời.
- Không biến mode này thành bài giảng dài.
- Nếu bé trả lời sai: sửa rất ngắn, cho mẫu đúng rồi hỏi tiếp.
- Nếu bé không hiểu: giải thích ngắn bằng tiếng Việt, sau đó quay lại tiếng Trung.
- Ưu tiên tiếng Trung chuẩn Mandarin/普通话.
- Không dùng tiếng Trung vượt trình độ chỉ để làm câu hỏi khó hơn.
- Có thể linh động kiểm tra từ vựng và ngữ pháp HSK {level.upper()}, nhưng ưu tiên giao tiếp.

Hãy bắt đầu bằng một câu chào tiếng Trung tự nhiên dành cho {student['called_name']} và đúng MỘT câu hỏi đơn giản phù hợp {level.upper()}, rồi dừng.
"""
    print(
        f"🗣️ CHINESE CONVERSATION: {student['called_name']} — {level.upper()}",
        flush=True,
    )
    await session.send_realtime_input(text=prompt)


_original_start_tutor_session = voice.start_tutor_session
_original_process_user_text = voice.process_user_text


voice.start_tutor_session = _start_tutor_session_with_memory


async def _process_user_text_with_memory(session, text):
    # Nếu câu vừa nghe có tên một bé, lưu sở thích ngay cho đúng bé.
    # Nếu đang Tutor Mode và bé tự chia sẻ, lưu vào bé hiện tại.
    student = voice.detect_student(text)
    student_id = student["student_id"] if student else voice.current_student_id

    if student_id:
        added = remember_preferences(text, student_id)
        if added:
            print(
                f"🧠 Nhớ sở thích {student_id}: {', '.join(added)}",
                flush=True,
            )

    # Chuyển riêng sang giao tiếp tiếng Trung khi Lão sư yêu cầu.
    if _is_chinese_conversation_request(text):
        target = student or _current_student_record()

        if target is None:
            await session.send_realtime_input(
                text="Hãy hỏi ngắn: Tiểu Vũ luyện tiếng Trung với Mini hay Đậu Đậu nè? Chỉ hỏi một câu."
            )
            return

        await _start_chinese_conversation(session, target)
        return

    # Nếu đang Tutor Mode và bé đã chọn môn bằng một câu không nhắc lại tên,
    # ví dụ "Toán", "học Toán", thì dùng đúng học sinh hiện tại.
    selected_subject = voice.detect_subject(text)
    if voice.current_mode == voice.TUTOR_MODE and selected_subject:
        target = student or _current_student_record()
        if target is not None:
            await voice.start_tutor_session(
                session,
                target,
                selected_subject,
                switching=True,
            )
            return

    # Giữ nguyên luồng voice hiện tại; bộ nhớ + lộ trình chỉ bổ sung context.
    await _original_process_user_text(session, text)


# ------------------------------------------------------------
# STARTUP GREETING GUARD
# ------------------------------------------------------------
# voice.py vẫn là voice baseline. Chỉ chặn đúng câu lệnh startup cũ
# và thay bằng lời chào thân thiện theo thời gian trong ngày:
#   1. "Chào Lão sư!"
#   2. chào theo đúng mốc giờ hiện tại
#   3. hỏi thăm Lão sư tự nhiên
#   4. giữ CHAT MODE và chờ Lão sư
# Không ảnh hưởng các lượt nói khác.
_original_send_text = voice.send_text


def _time_aware_startup_greeting():
    """Tạo ngữ cảnh lời chào theo giờ máy lúc Tiểu Vũ được kích hoạt."""
    hour = datetime.datetime.now().hour

    if hour == 23:
        return "Chào Lão sư! Khuya rồi, Lão sư vẫn còn thức làm việc à?"
    if 0 <= hour <= 4:
        return "Chào Lão sư! Giờ này khuya lắm rồi, Lão sư vẫn còn thức à?"
    if 5 <= hour <= 11:
        return "Chào Lão sư! Chào buổi sáng! Hôm nay Lão sư thấy thế nào ạ?"
    if hour == 12:
        return "Chào Lão sư! Chào buổi trưa! Lão sư dùng bữa và nghỉ ngơi chưa ạ?"
    if 13 <= hour <= 17:
        return "Chào Lão sư! Chào buổi chiều! Hôm nay công việc của Lão sư ổn chứ ạ?"
    if 18 <= hour <= 22:
        return "Chào Lão sư! Chào buổi tối! Hôm nay Lão sư có mệt không ạ?"

    return "Chào Lão sư! Hôm nay Lão sư thấy thế nào ạ?"


async def _send_text_with_startup_guard(session, text):
    if text.strip() == "Chào Lão sư thật ngắn gọn và tự nhiên. Không hỏi câu hỏi mới.":
        greeting = _time_aware_startup_greeting()
        text = f"""
Tiểu Vũ vừa được kích hoạt và đang ở CHAT MODE với Lão sư Minh Tâm.

TÍNH CÁCH:
- Thân thiện, vui vẻ, gần gũi, tự nhiên; không máy móc, không quá trang trọng.
- Luôn nhớ Lão sư là người đang nói chuyện với Tiểu Vũ.

LỜI CHÀO KÍCH HOẠT:
- Câu đầu tiên BẮT BUỘC phải bắt đầu chính xác bằng: "Chào Lão sư!"
- Sau đó dùng lời chào theo thời gian hiện tại: "{greeting}"
- Có thể diễn đạt tự nhiên, vui vẻ, nhưng không được bỏ câu "Chào Lão sư!".
- Sau lời chào, hỏi thăm Lão sư một câu ngắn phù hợp thời điểm trong ngày.
- Không hỏi bài học, không gọi học sinh, không chuyển sang Tutor Mode.
- Chỉ chào hỏi và hỏi thăm, sau đó DỪNG để chờ Lão sư nói tiếp.
"""
    await _original_send_text(session, text)


voice.process_user_text = _process_user_text_with_memory
voice.send_text = _send_text_with_startup_guard


if __name__ == "__main__":
    voice.start()
