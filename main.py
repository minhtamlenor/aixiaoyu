# ============================================================
# TIỂU VŨ - MAIN
# ============================================================

import voice

from student_memory import (
    build_memory_instruction,
    remember_preferences,
)


# ------------------------------------------------------------
# BỘ NHỚ SỞ THÍCH
# ------------------------------------------------------------
# Không sửa voice.py để giữ nguyên bản voice đang ổn.
# Wrapper này chỉ bổ sung trí nhớ sở thích cho Tutor Mode.
# Dữ liệu được lưu local trong .xiaoyu_student_memory.json
# và đã được .gitignore loại khỏi GitHub.
# ------------------------------------------------------------

_original_start_tutor_session = voice.start_tutor_session
_original_process_user_text = voice.process_user_text


async def _start_tutor_session_with_memory(session, student, subject=None, switching=False):
    await _original_start_tutor_session(
        session,
        student,
        subject,
        switching=switching,
    )

    # Nạp sở thích đã nhớ ngay khi bé bước vào Tutor Mode.
    memory_instruction = build_memory_instruction(
        student["student_id"],
        student["official_name"],
    )
    if memory_instruction:
        await session.send_realtime_input(text=memory_instruction)


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

    await _original_process_user_text(session, text)

    # Nếu bé vừa nói một sở thích mới, cập nhật ngay ngữ cảnh Gemini.
    if student_id:
        memory_instruction = build_memory_instruction(
            student_id,
            student["official_name"] if student else (voice.current_student or student_id),
        )
        if memory_instruction:
            await session.send_realtime_input(text=memory_instruction)


voice.start_tutor_session = _start_tutor_session_with_memory
voice.process_user_text = _process_user_text_with_memory


if __name__ == "__main__":
    voice.start()
