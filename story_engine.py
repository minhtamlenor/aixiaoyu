# ============================================================
# TIỂU VŨ - STORY ENGINE
# Buddhist story library for CHAT MODE
#
# Content lives in stories/buddhism/*.md.
# To add a new story: add one Markdown file to that folder and
# commit it. No Python code or prompt change is required.
# ============================================================

import random
import re
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STORY_DIR = BASE_DIR / "stories" / "buddhism"

STORY_REQUEST_PATTERNS = [
    "kể chuyện phật giáo", "ke chuyen phat giao", "kể chuyện phật", "ke chuyen phat",
    "chuyện phật giáo", "chuyen phat giao", "kể chuyện đức phật", "ke chuyen duc phat",
    "phật giáo kể chuyện", "phat giao ke chuyen", "chuyện đạo phật", "chuyen dao phat",
    "kể chuyện đạo phật", "ke chuyen dao phat", "kể tiếp chuyện", "ke tiep chuyen",
    "kể tiếp đi", "ke tiep di",
]

PROACTIVE_ENABLED = True
PROACTIVE_COOLDOWN_SECONDS = 600
PROACTIVE_IDLE_SECONDS = 60

_last_story_key = None
_last_story = None
_last_story_at = 0.0


def _normalize(text):
    text = (text or "").lower().strip()
    return re.sub(r"\s+", " ", text)


def is_story_request(text):
    normalized = _normalize(text)
    return any(pattern in normalized for pattern in STORY_REQUEST_PATTERNS)


def is_story_continue_request(text):
    normalized = _normalize(text)
    return any(pattern in normalized for pattern in [
        "kể tiếp", "ke tiep", "kể tiếp đi", "ke tiep di", "tiếp đi", "tiep di",
    ])


def _parse_story(path):
    text = path.read_text(encoding="utf-8")
    title = path.stem
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if match:
        title = match.group(1).strip()

    def section(name):
        match = re.search(
            rf"^##\s+{re.escape(name)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
            text,
            re.MULTILINE | re.IGNORECASE,
        )
        return match.group(1).strip() if match else ""

    return {
        "key": path.stem,
        "title": title,
        "topic": section("topic"),
        "source_note": section("source_note"),
        "story": section("story"),
        "message": section("message"),
        "comedy_angle": section("comedy_angle"),
        "tags": section("tags"),
        "path": str(path),
    }


def load_stories():
    if not STORY_DIR.exists():
        return []
    stories = []
    for path in sorted(STORY_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        try:
            story = _parse_story(path)
            if story["story"]:
                stories.append(story)
        except Exception as exc:
            print(f"⚠️ Không đọc được story {path.name}: {exc}", flush=True)
    return stories


def choose_story(preferred_topic=None):
    global _last_story_key, _last_story
    stories = load_stories()
    if not stories:
        return None
    candidates = stories
    if preferred_topic:
        topic = _normalize(preferred_topic)
        matching = [story for story in stories if topic in _normalize(story["topic"] + " " + story["tags"])]
        if matching:
            candidates = matching
    not_last = [story for story in candidates if story["key"] != _last_story_key]
    if not_last:
        candidates = not_last
    story = random.choice(candidates)
    _last_story_key = story["key"]
    _last_story = story
    return story


def build_story_prompt(story, proactive=False, continuation=False):
    if not story:
        return ""
    if continuation:
        mode_text = "Lão sư vừa nói muốn nghe tiếp câu chuyện đang kể. Hãy tiếp tục đúng câu chuyện này."
    elif proactive:
        mode_text = "Tiểu Vũ chủ động đề nghị kể chuyện vì cuộc trò chuyện đang có khoảng lặng."
    else:
        mode_text = "Lão sư vừa yêu cầu kể chuyện."
    return f"""
CHAT MODE — BUDDHIST STORY MODE

{mode_text}

CÂU CHUYỆN:
Tiêu đề: {story['title']}
Chủ đề: {story['topic']}
Nguồn/ghi chú biên tập: {story['source_note']}

NỘI DUNG NỀN:
{story['story']}

THÔNG ĐIỆP:
{story['message']}

GỢI Ý HÀI ĐỘC THOẠI:
{story['comedy_angle']}

QUY TẮC KỂ:
- Kể bằng tiếng Việt tự nhiên, giọng một cô gái miền Nam thân thiện.
- Phong cách hài độc thoại: quan sát đời thường, punchline nhẹ, duyên và thông minh.
- Có thể cười vào những thói quen rất con người, nhưng KHÔNG chế giễu Đức Phật, giáo pháp, người tu hoặc nỗi đau của người khác.
- Không bịa thêm sự kiện lịch sử/kinh điển như thể đó là sự thật.
- Nội dung nền là khung sự kiện; được phép diễn đạt lại cho tự nhiên và hài hước.
- Không biến câu chuyện thành bài giảng đạo đức khô khan.
- Sau một đoạn mở đầu hài, kể mạch chuyện rõ ràng rồi rút ra thông điệp ngắn.
- Kể như đang nói chuyện trực tiếp với Lão sư, không đọc tiêu đề hay các nhãn kỹ thuật.
- Không nói "theo prompt", "Story Engine", "file", "Markdown" hoặc "nguồn dữ liệu".
- Không tự chuyển sang Tutor Mode.
- Mỗi lượt nói một đoạn vừa phải, khoảng 30–90 giây. Sau đó dừng để Lão sư có thể phản ứng.
- Nếu đây là lượt tiếp tục, KHÔNG chọn câu chuyện mới và không kể lại phần đã kể; tiếp tục từ mạch chuyện hiện tại.
"""


def get_story_prompt(preferred_topic=None, proactive=False, continuation=False):
    global _last_story_at
    story = _last_story if continuation else choose_story(preferred_topic)
    if not story:
        return None
    _last_story_at = time.monotonic()
    return build_story_prompt(story, proactive=proactive, continuation=continuation)


def proactive_story_allowed(last_user_activity):
    if not PROACTIVE_ENABLED:
        return False
    now = time.monotonic()
    if now - _last_story_at < PROACTIVE_COOLDOWN_SECONDS:
        return False
    if now - last_user_activity < PROACTIVE_IDLE_SECONDS:
        return False
    return bool(load_stories())
