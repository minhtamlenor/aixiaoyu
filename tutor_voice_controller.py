# ============================================================
# TIỂU VŨ - TUTOR VOICE CONTROLLER
# VOICE -> TRIGGER -> SESSION -> LESSON FLOW
#
# Nhiệm vụ:
#
# 1. Nhận text đã được Voice transcription
# 2. Phát hiện:
#       "Mini muốn học"
#       "Đậu Phộng muốn học"
#       "Đậu Đậu muốn học"
#
# 3. Khi gọi tên học sinh + muốn học:
#       -> bật chế độ gia sư
#
# 4. Khi gọi "Lão sư":
#       -> giữ chế độ trò chuyện
#
# 5. Khi đã vào gia sư:
#       -> khóa tên học sinh
#       -> không tự đổi sang Mini
#       -> tự tạo câu hỏi đầu tiên
#       -> chủ động đưa câu hỏi cho bé
#
# 6. Giữ nguyên lesson_flow / question_engine hiện tại.
# ============================================================


import os
import sys
import re
import unicodedata


# ============================================================
# PATH PROJECT
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

if BASE_DIR not in sys.path:

    sys.path.insert(
        0,
        BASE_DIR
    )


# ============================================================
# IMPORT TUTOR TRIGGER
# ============================================================

try:

    from tutor_trigger import (
        detect_tutor_command
    )

except ImportError:

    detect_tutor_command = None


# ============================================================
# IMPORT LESSON FLOW
# ============================================================

try:

    from lesson_flow import (
        create_next_question,
        process_answer,
        show_question,
        get_session_nickname,
        lock_session_nickname,
    )

except ImportError:

    create_next_question = None
    process_answer = None
    show_question = None
    get_session_nickname = None
    lock_session_nickname = None


# ============================================================
# IMPORT LESSON MANAGER
# ============================================================

try:

    from tutor.lesson_manager import (
        create_lesson_session,
        finish_session,
        get_session_summary,
    )

except ImportError:

    create_lesson_session = None
    finish_session = None
    get_session_summary = None


# ============================================================
# IMPORT QUESTION ENGINE
# ============================================================

try:

    from tutor.question_engine import (
        check_answer,
    )

except ImportError:

    check_answer = None


# ============================================================
# CONSTANT
# ============================================================

CHAT_MODE = "chat"

TUTOR_MODE = "tutor"


DEFAULT_SUBJECT = "math"


DEFAULT_TOPIC = "addition"


DEFAULT_STRATEGY = "practice"


# ============================================================
# STUDENT
# ============================================================

STUDENT_NAMES = {

    "Mini": {
        "key": "mini",
    },

    "Đậu Phộng": {
        "key": "dau_phong",
    },

    "Đậu Đậu": {
        "key": "dau_dau",
    },

}


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if not isinstance(
        text,
        str
    ):

        return ""

    text = text.strip().lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# REMOVE ACCENTS
# ============================================================

def remove_accents(text):

    if not isinstance(
        text,
        str
    ):

        return ""

    normalized = unicodedata.normalize(
        "NFD",
        text
    )

    result = ""

    for char in normalized:

        if unicodedata.category(
            char
        ) != "Mn":

            result += char

    result = result.replace(
        "đ",
        "d"
    )

    result = result.replace(
        "Đ",
        "D"
    )

    result = re.sub(
        r"\s+",
        " ",
        result
    )

    return result.strip().lower()


# ============================================================
# DETECT STUDENT NAME
# ============================================================

def detect_student_name(text):

    normalized = normalize_text(
        text
    )

    no_accent = remove_accents(
        normalized
    )


    # ========================================================
    # ĐẬU PHỘNG
    # ========================================================

    dau_phong = [

        "đậu phộng",
        "đậu phụng",

        "dau phong",
        "dau phung",

    ]

    for name in dau_phong:

        if (
            name in normalized
            or name in no_accent
        ):

            return "Đậu Phộng"


    # ========================================================
    # ĐẬU ĐẬU
    # ========================================================

    dau_dau = [

        "đậu đậu",
        "dau dau",

    ]

    for name in dau_dau:

        if (
            name in normalized
            or name in no_accent
        ):

            return "Đậu Đậu"


    # ========================================================
    # MINI
    # ========================================================

    if "mini" in normalized:

        return "Mini"


    return None


# ============================================================
# DETECT LÃO SƯ
# ============================================================

def is_lao_su_call(text):

    normalized = normalize_text(
        text
    )

    patterns = [

        "lão sư",
        "lao su",

        "lão sư ơi",
        "lao su oi",

        "ê lão sư",
        "e lao su",

    ]

    for pattern in patterns:

        if pattern in normalized:

            return True


    return False


# ============================================================
# DETECT LESSON INTENT
# ============================================================

def detect_lesson_intent_local(text):

    normalized = normalize_text(
        text
    )

    no_accent = remove_accents(
        normalized
    )


    patterns = [

        # ----------------------------------------------------
        # MUỐN HỌC
        # ----------------------------------------------------

        "muốn học",
        "muon hoc",

        "con muốn học",
        "con muon hoc",

        # ----------------------------------------------------
        # BẮT ĐẦU
        # ----------------------------------------------------

        "bắt đầu học",
        "bat dau hoc",

        "bắt đầu bài học",
        "bat dau bai hoc",

        # ----------------------------------------------------
        # HỌC ĐI
        # ----------------------------------------------------

        "học đi",
        "hoc di",

        "học nha",
        "hoc nha",

        "học nhé",
        "hoc nhe",

        "học thôi",
        "hoc thoi",

        # ----------------------------------------------------
        # VÀO HỌC
        # ----------------------------------------------------

        "vào học",
        "vao hoc",

        "vô học",
        "vo hoc",

        "vào học đi",
        "vao hoc di",

        # ----------------------------------------------------
        # CHO CON HỌC
        # ----------------------------------------------------

        "cho con học",
        "cho con hoc",

        "cho học",
        "cho hoc",

        # ----------------------------------------------------
        # HỌC BÀI
        # ----------------------------------------------------

        "học bài",
        "hoc bai",

        "học bài đi",
        "hoc bai di",

        # ----------------------------------------------------
        # GIỜ HỌC
        # ----------------------------------------------------

        "giờ học",
        "gio hoc",

        "tới giờ học",
        "toi gio hoc",

        "đến giờ học",
        "den gio hoc",

    ]


    for pattern in patterns:

        if pattern in normalized:

            return True


    for pattern in patterns:

        pattern_no_accent = remove_accents(
            pattern
        )

        if pattern_no_accent in no_accent:

            return True


    # ========================================================
    # TÊN + HỌC
    # ========================================================

    student = detect_student_name(
        text
    )

    if student is not None:

        if (
            " học" in normalized
            or normalized.endswith("học")
            or " hoc" in no_accent
            or no_accent.endswith("hoc")
        ):

            return True


    return False


# ============================================================
# DETECT SUBJECT
# ============================================================

def detect_subject_local(text):

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


    return None


# ============================================================
# CONTROLLER
# ============================================================

class TutorVoiceController:

    """
    Bộ điều khiển phiên Voice + Tutor.

    Trạng thái:

        chat
        tutor

    Khi tutor:

        student được khóa
        subject được khóa
        câu hỏi được quản lý bởi lesson_flow
    """


    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        student_id=None,
        default_subject=DEFAULT_SUBJECT,
    ):

        self.mode = CHAT_MODE

        self.student = None

        self.student_id = student_id

        self.subject = default_subject

        self.session = None

        self.current_question = None

        self.session_started = False

        self.lesson_finished = False


    # ========================================================
    # GET MODE
    # ========================================================

    def get_mode(self):

        return self.mode


    # ========================================================
    # IS TUTOR
    # ========================================================

    def is_tutor_mode(self):

        return (
            self.mode == TUTOR_MODE
        )


    # ========================================================
    # IS CHAT
    # ========================================================

    def is_chat_mode(self):

        return (
            self.mode == CHAT_MODE
        )


    # ========================================================
    # START SESSION
    # ========================================================

    def start_tutor_session(
        self,
        student_name,
        subject=None,
    ):

        # ----------------------------------------------------
        # BẢO VỆ
        # ----------------------------------------------------

        if not student_name:

            return {
                "success": False,
                "message": (
                    "Chưa xác định được học sinh."
                ),
            }


        # ----------------------------------------------------
        # SUBJECT
        # ----------------------------------------------------

        if subject is None:

            subject = self.subject

        if subject is None:

            subject = DEFAULT_SUBJECT


        # ----------------------------------------------------
        # KHÓA TRẠNG THÁI
        # ----------------------------------------------------

        self.mode = TUTOR_MODE

        self.student = student_name

        self.subject = subject

        self.session_started = True

        self.lesson_finished = False


        # ----------------------------------------------------
        # TẠO LESSON SESSION
        # ----------------------------------------------------

        if create_lesson_session is not None:

            try:

                self.session = create_lesson_session(
                    self.student_id or student_name,
                    subject
                )

            except Exception as error:

                print(
                    "⚠️ Không tạo được lesson session:",
                    error
                )

                self.session = {

                    "student_id":
                        self.student_id or student_name,

                    "student_name":
                        student_name,

                    "subject_id":
                        subject,

                }

        else:

            self.session = {

                "student_id":
                    self.student_id or student_name,

                "student_name":
                    student_name,

                "subject_id":
                    subject,

            }


        # ----------------------------------------------------
        # KHÓA NICKNAME
        # ----------------------------------------------------

        if isinstance(
            self.session,
            dict
        ):

            self.session["nickname"] = (
                student_name
            )

            self.session["student_nickname"] = (
                student_name
            )

            self.session["nickname_locked"] = True

            self.session["subject_id"] = (
                subject
            )


        # ----------------------------------------------------
        # TẠO CÂU HỎI ĐẦU TIÊN
        #
        # ĐÂY LÀ PHẦN QUAN TRỌNG:
        #
        # Khi bật gia sư,
        # Tiểu Vũ KHÔNG chờ người lớn hỏi.
        #
        # Tiểu Vũ tự tạo câu hỏi.
        # ----------------------------------------------------

        question = self.create_first_question()


        return {

            "success": True,

            "mode": TUTOR_MODE,

            "student": self.student,

            "subject": self.subject,

            "question": question,

            "say": self.build_question_message(
                question
            ),

        }


    # ========================================================
    # CREATE FIRST QUESTION
    # ========================================================

    def create_first_question(self):

        if self.session is None:

            return None


        # ----------------------------------------------------
        # LESSON FLOW
        # ----------------------------------------------------

        if create_next_question is not None:

            try:

                question = create_next_question(
                    self.session
                )

                self.current_question = (
                    question
                )

                return question

            except Exception as error:

                print(
                    "⚠️ Question Engine lỗi:",
                    error
                )


        return None


    # ========================================================
    # CREATE NEXT QUESTION
    # ========================================================

    def create_next_question(self):

        if not self.is_tutor_mode():

            return None

        if self.session is None:

            return None


        if create_next_question is not None:

            try:

                question = create_next_question(
                    self.session
                )

                self.current_question = (
                    question
                )

                return question

            except Exception as error:

                print(
                    "⚠️ Không tạo được câu hỏi:",
                    error
                )

                return None


        return None


    # ========================================================
    # BUILD QUESTION MESSAGE
    # ========================================================

    def build_question_message(
        self,
        question=None,
    ):

        if question is None:

            question = self.current_question


        if not isinstance(
            question,
            dict
        ):

            return (
                f"{self.student} ơi, "
                "mình bắt đầu học nha!"
            )


        text = question.get(
            "question",
            ""
        )


        if not text:

            text = (
                "Mình bắt đầu bài học nha!"
            )


        return (
            f"{self.student} ơi, "
            f"{text}"
        )


    # ========================================================
    # PROCESS ANSWER
    # ========================================================

    def process_answer(
        self,
        answer,
    ):

        if not self.is_tutor_mode():

            return {

                "handled": False,

                "reason":
                    "not_tutor_mode",

            }


        if self.current_question is None:

            return {

                "handled": False,

                "reason":
                    "no_current_question",

            }


        if process_answer is not None:

            try:

                result = process_answer(
                    self.session,
                    self.current_question,
                    answer
                )

            except Exception as error:

                print(
                    "⚠️ process_answer lỗi:",
                    error
                )

                result = {

                    "correct": False,

                    "message":
                        "Tiểu Vũ chưa xử lý được câu trả lời.",

                }

        else:

            result = {

                "correct": False,

                "message":
                    "Lesson Flow chưa được kết nối.",

            }


        # ----------------------------------------------------
        # ĐÚNG
        # ----------------------------------------------------

        if result.get(
            "correct"
        ) is True:

            next_question = (
                self.create_next_question()
            )

            return {

                "handled": True,

                "correct": True,

                "result": result,

                "next_question":
                    next_question,

                "say": self.build_next_question_message(
                    result,
                    next_question
                ),

            }


        # ----------------------------------------------------
        # SAI
        # ----------------------------------------------------

        return {

            "handled": True,

            "correct": False,

            "result": result,

            "say": self.build_wrong_answer_message(
                result
            ),

        }


    # ========================================================
    # CORRECT MESSAGE
    # ========================================================

    def build_next_question_message(
        self,
        result,
        next_question,
    ):

        if next_question is None:

            return (
                f"Đúng rồi {self.student}! "
                "Giỏi quá nha."
            )


        next_text = next_question.get(
            "question",
            ""
        )


        return (
            f"Đúng rồi {self.student}! "
            f"Giỏi quá. Mình làm tiếp nha. "
            f"{next_text}"
        )


    # ========================================================
    # WRONG MESSAGE
    # ========================================================

    def build_wrong_answer_message(
        self,
        result,
    ):

        if not isinstance(
            result,
            dict
        ):

            return (
                f"Không sao {self.student}, "
                "mình thử lại nha."
            )


        hint = result.get(
            "hint",
            ""
        )


        if hint:

            return (
                f"Không sao {self.student}. "
                f"Con thử lại nha. "
                f"{hint}"
            )


        return (
            f"Không sao {self.student}. "
            "Con thử lại một lần nữa nha."
        )


    # ========================================================
    # NEXT QUESTION AFTER WRONG
    # ========================================================

    def retry_current_question(self):

        if not self.is_tutor_mode():

            return None


        return self.current_question


    # ========================================================
    # FINISH
    # ========================================================

    def finish_tutor_session(self):

        if self.session is not None:

            if finish_session is not None:

                try:

                    finish_session(
                        self.session
                    )

                except Exception as error:

                    print(
                        "⚠️ finish_session lỗi:",
                        error
                    )


        self.lesson_finished = True

        self.mode = CHAT_MODE


        summary = None


        if (
            self.session is not None
            and get_session_summary is not None
        ):

            try:

                summary = get_session_summary(
                    self.session
                )

            except Exception:

                summary = None


        return {

            "mode": CHAT_MODE,

            "student":
                self.student,

            "summary":
                summary,

        }


    # ========================================================
    # CHAT COMMAND
    # ========================================================

    def handle_chat_text(
        self,
        text,
    ):

        # ----------------------------------------------------
        # Nếu đang gia sư:
        #
        # Không được tự ý chuyển về Mini.
        # ----------------------------------------------------

        if self.is_tutor_mode():

            return {

                "handled": False,

                "mode":
                    TUTOR_MODE,

                "student":
                    self.student,

                "message":
                    "Đang trong phiên gia sư.",

            }


        # ----------------------------------------------------
        # LÃO SƯ
        # ----------------------------------------------------

        if is_lao_su_call(
            text
        ):

            return {

                "handled": True,

                "mode":
                    CHAT_MODE,

                "student":
                    None,

                "message":
                    "Tiểu Vũ đang trò chuyện với Lão sư.",

            }


        return {

            "handled": False,

            "mode":
                CHAT_MODE,

            "student":
                None,

        }


    # ========================================================
    # MAIN TEXT HANDLER
    # ========================================================

    def handle_transcript(
        self,
        text,
    ):

        if not isinstance(
            text,
            str
        ):

            return {

                "intent":
                    "chat",

                "mode":
                    self.mode,

                "student":
                    self.student,

            }


        text = text.strip()


        # ====================================================
        # ĐANG TRONG GIA SƯ
        # ====================================================

        if self.is_tutor_mode():

            # ------------------------------------------------
            # KHÔNG cho phép tên khác làm đổi học sinh.
            #
            # Ví dụ:
            #
            # Đậu Phộng đang học.
            #
            # Voice nhận:
            #
            # "Mini..."
            #
            # cũng KHÔNG đổi sang Mini.
            # ------------------------------------------------

            return {

                "intent":
                    "tutor_answer",

                "mode":
                    TUTOR_MODE,

                "student":
                    self.student,

                "subject":
                    self.subject,

                "text":
                    text,

            }


        # ====================================================
        # LÃO SƯ
        # ====================================================

        if is_lao_su_call(
            text
        ):

            return {

                "intent":
                    "chat",

                "mode":
                    CHAT_MODE,

                "student":
                    None,

                "text":
                    text,

            }


        # ====================================================
        # PHÁT HIỆN TÊN
        # ====================================================

        student = detect_student_name(
            text
        )


        # ====================================================
        # PHÁT HIỆN LỆNH HỌC
        # ====================================================

        lesson_intent = detect_lesson_intent_local(
            text
        )


        # ====================================================
        # PHÁT HIỆN MÔN
        # ====================================================

        subject = detect_subject_local(
            text
        )


        # ====================================================
        # CÓ TÊN + CÓ Ý ĐỊNH HỌC
        #
        # ĐÂY LÀ TRIGGER CHÍNH.
        #
        # Ví dụ:
        #
        # "Mini muốn học"
        #
        # "Đậu Phộng muốn học Toán"
        #
        # "Đậu Đậu học đi"
        # ====================================================

        if (
            student is not None
            and lesson_intent
        ):

            result = self.start_tutor_session(

                student_name=student,

                subject=subject,

            )


            return {

                "intent":
                    "start_lesson",

                "mode":
                    TUTOR_MODE,

                "student":
                    student,

                "subject":
                    self.subject,

                "question":
                    result.get(
                        "question"
                    ),

                "say":
                    result.get(
                        "say"
                    ),

                "success":
                    result.get(
                        "success",
                        False
                    ),

            }


        # ====================================================
        # CÓ Ý ĐỊNH HỌC NHƯNG KHÔNG NÓI TÊN
        #
        # Không tự ý chọn Mini.
        #
        # Đây là điểm rất quan trọng.
        #
        # "Con muốn học"
        #
        # không được biến thành:
        #
        # "Mini muốn học"
        # ====================================================

        if lesson_intent:

            return {

                "intent":
                    "lesson_needs_student",

                "mode":
                    CHAT_MODE,

                "student":
                    None,

                "subject":
                    subject,

                "text":
                    text,

                "say":
                    (
                        "Ủa, hôm nay ai muốn học với "
                        "Tiểu Vũ nè? Mini, Đậu Phộng "
                        "hay Đậu Đậu?"
                    ),

            }


        # ====================================================
        # CHAT BÌNH THƯỜNG
        # ====================================================

        return {

            "intent":
                "chat",

            "mode":
                CHAT_MODE,

            "student":
                None,

            "subject":
                None,

            "text":
                text,

        }


    # ========================================================
    # RESET
    # ========================================================

    def reset(self):

        self.mode = CHAT_MODE

        self.student = None

        self.subject = DEFAULT_SUBJECT

        self.session = None

        self.current_question = None

        self.session_started = False

        self.lesson_finished = False


    # ========================================================
    # STATUS
    # ========================================================

    def status(self):

        return {

            "mode":
                self.mode,

            "student":
                self.student,

            "subject":
                self.subject,

            "session_started":
                self.session_started,

            "lesson_finished":
                self.lesson_finished,

            "has_question":
                self.current_question is not None,

        }


# ============================================================
# DEMO TEST
# ============================================================

def demo():

    print()

    print(
        "=" * 70
    )

    print(
        "TIỂU VŨ - TUTOR VOICE CONTROLLER TEST"
    )

    print(
        "=" * 70
    )


    controller = TutorVoiceController()


    tests = [

        # ----------------------------------------------------
        # MINI
        # ----------------------------------------------------

        "Mini muốn học",

        # ----------------------------------------------------
        # RESET
        # ----------------------------------------------------

    ]


    for text in tests:

        print()

        print(
            "VOICE:",
            text
        )

        result = controller.handle_transcript(
            text
        )

        print(
            "RESULT:"
        )

        print(
            result
        )

        print()

        print(
            "STATUS:"
        )

        print(
            controller.status()
        )


    # ========================================================
    # RESET
    # ========================================================

    controller.reset()


    # ========================================================
    # TEST ĐẬU PHỘNG
    # ========================================================

    print()

    print(
        "-" * 70
    )

    print(
        "TEST ĐẬU PHỘNG"
    )

    print(
        "-" * 70
    )


    result = controller.handle_transcript(
        "Đậu Phộng muốn học Toán"
    )


    print(
        result
    )


    print()

    print(
        "STATUS:"
    )

    print(
        controller.status()
    )


    # ========================================================
    # ĐANG HỌC -> KHÔNG ĐỔI TÊN
    # ========================================================

    print()

    print(
        "-" * 70
    )

    print(
        "TEST KHÓA TÊN"
    )

    print(
        "-" * 70
    )


    result = controller.handle_transcript(
        "Mini muốn học"
    )


    print(
        result
    )


    print()

    print(
        "STATUS SAU KHI NHẬN MINI:"
    )

    print(
        controller.status()
    )


    # ========================================================
    # RESET
    # ========================================================

    controller.reset()


    # ========================================================
    # TEST ĐẬU ĐẬU
    # ========================================================

    print()

    print(
        "-" * 70
    )

    print(
        "TEST ĐẬU ĐẬU"
    )

    print(
        "-" * 70
    )


    result = controller.handle_transcript(
        "Đậu Đậu muốn học"
    )


    print(
        result
    )


    print()

    print(
        "STATUS:"
    )

    print(
        controller.status()
    )


    # ========================================================
    # RESET
    # ========================================================

    controller.reset()


    # ========================================================
    # TEST LÃO SƯ
    # ========================================================

    print()

    print(
        "-" * 70
    )

    print(
        "TEST LÃO SƯ"
    )

    print(
        "-" * 70
    )


    result = controller.handle_transcript(
        "Lão sư ơi"
    )


    print(
        result
    )


    print()

    print(
        "=" * 70
    )

    print(
        "TEST HOÀN TẤT"
    )

    print(
        "=" * 70
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        demo()

    except KeyboardInterrupt:

        print()

        print(
            "Tiểu Vũ tạm dừng."
        )

    except Exception as error:

        print()

        print(
            "=" * 70
        )

        print(
            "RUNTIME ERROR"
        )

        print(
            "=" * 70
        )

        print(
            type(error).__name__,
            ":",
            error
        )