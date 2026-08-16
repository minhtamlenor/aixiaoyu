# ============================================================
# TIỂU VŨ - STUDENT MEMORY
# Lưu sở thích đơn giản trên máy local để Tiểu Vũ nhớ qua các lần chạy.
# Không chứa API key và không đưa dữ liệu này lên GitHub.
# ============================================================

import json
import os
import re
import tempfile


MEMORY_FILE = os.path.join(os.path.dirname(__file__), ".xiaoyu_student_memory.json")
MAX_FACTS_PER_STUDENT = 30

PREFERENCE_WORDS = (
    "thích", "không thích", "ghét", "mê", "yêu thích", "yêu",
    "sở thích", "hay chơi", "hay xem", "hay đọc", "muốn",
    "sợ", "món khoái khẩu", "món yêu thích", "màu yêu thích",
)


def _empty_memory():
    return {
        "minh_tien": {"facts": []},
        "nha_tien": {"facts": []},
    }


def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty_memory()
        base = _empty_memory()
        for student_id in base:
            facts = data.get(student_id, {}).get("facts", [])
            if isinstance(facts, list):
                base[student_id]["facts"] = [str(x).strip() for x in facts if str(x).strip()][-MAX_FACTS_PER_STUDENT:]
        return base
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return _empty_memory()


def save_memory(memory):
    directory = os.path.dirname(MEMORY_FILE)
    fd, temp_path = tempfile.mkstemp(prefix="xiaoyu_memory_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, MEMORY_FILE)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _sentences(text):
    return [part.strip(" \t\r\n,，;；") for part in re.split(r"[.!?！？。\n]+", text or "") if part.strip()]


def _looks_like_preference(sentence):
    lowered = sentence.lower()
    return any(word in lowered for word in PREFERENCE_WORDS)


def remember_preferences(text, student_id):
    """Lưu các câu có tín hiệu sở thích; không cố suy đoán ngoài lời nói."""
    if not student_id or not text:
        return []

    memory = load_memory()
    if student_id not in memory:
        memory[student_id] = {"facts": []}

    added = []
    for sentence in _sentences(text):
        if len(sentence) < 4 or len(sentence) > 220:
            continue
        if not _looks_like_preference(sentence):
            continue
        fact = re.sub(r"\s+", " ", sentence).strip()
        if fact not in memory[student_id]["facts"]:
            memory[student_id]["facts"].append(fact)
            added.append(fact)

    if added:
        memory[student_id]["facts"] = memory[student_id]["facts"][-MAX_FACTS_PER_STUDENT:]
        save_memory(memory)
    return added


def get_student_memory(student_id):
    memory = load_memory()
    return list(memory.get(student_id, {}).get("facts", []))


def build_memory_instruction(student_id, student_name):
    facts = get_student_memory(student_id)
    if not facts:
        return ""
    lines = "\n".join(f"- {fact}" for fact in facts)
    return f"""
THÔNG TIN ĐÃ NHỚ VỀ {student_name.upper()}:
{lines}

Hãy dùng các sở thích này một cách tự nhiên khi trò chuyện hoặc dạy học.
Không đọc danh sách sở thích như một báo cáo. Không nói rằng em đang đọc bộ nhớ.
Nếu phù hợp, có thể hỏi thêm để hiểu {student_name} hơn và cập nhật sở thích mới khi bé chia sẻ.
"""


def build_all_memory_instruction(student_names):
    memory = load_memory()
    blocks = []
    for student_id, student_name in student_names.items():
        facts = memory.get(student_id, {}).get("facts", [])
        if not facts:
            continue
        lines = "\n".join(f"- {fact}" for fact in facts)
        blocks.append(f"{student_name}:\n{lines}")
    if not blocks:
        return ""
    return """
BỘ NHỚ SỞ THÍCH HỌC SINH:
""" + "\n\n".join(blocks) + """

Quy tắc sử dụng:
- Chỉ lồng ghép tự nhiên, đúng học sinh.
- Không đọc danh sách bộ nhớ ra thành tiếng.
- Không nói rằng Tiểu Vũ đang lưu dữ liệu.
- Khi bé chia sẻ một sở thích mới, ghi nhớ để những lần trò chuyện sau có thể dùng lại.
"""
