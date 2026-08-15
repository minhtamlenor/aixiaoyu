import asyncio
import os
import random
import sounddevice as sd

from google import genai
from google.genai import types


# ============================================================
# TIỂU VŨ LIVE VOICE
# CHAT MODE + TUTOR MODE
# ============================================================

MIC = 1

INPUT_RATE = 16000
OUTPUT_RATE = 24000

CHANNELS = 1
BLOCKSIZE = 1600

MODEL = "gemini-3.1-flash-live-preview"


# ============================================================
# GEMINI
# ============================================================

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


# ============================================================
# CHẾ ĐỘ
# ============================================================

CHAT_MODE = "chat"
TUTOR_MODE = "tutor"


CURRENT_MODE = CHAT_MODE


# ============================================================
# HỌC SINH
# ============================================================

STUDENT_NAMES = [
    "mini",
    "đậu phộng",
    "dau phong",
    "đậuphộng",
    "dauphong",
]


# ============================================================
# CÁC CÂU KÍCH HOẠT GIA SƯ
# ============================================================

TUTOR_TRIGGERS = [

    "mini muốn học",
    "mini muon hoc",

    "đậu phộng muốn học",
    "dậu phộng muốn học",
    "dau phong muon hoc",

    "mini học",
    "mini hoc",

    "đậu phộng học",
    "dau phong hoc",

    "cho mini học",
    "cho đậu phộng học",

    "bắt đầu học",
    "bat dau hoc",

    "vào học",
    "vao hoc",

    "học đi",
    "hoc di",

]


# ============================================================
# SYSTEM INSTRUCTION
# ============================================================

SYSTEM_INSTRUCTION = """
Bạn là Tiểu Vũ.

Bạn là một cô gái Việt Nam thân thiện,
dễ thương, tự nhiên, hơi tinh nghịch và gần gũi.

Bạn đang trò chuyện với Lão sư.

============================================================
QUY TẮC CỰC KỲ QUAN TRỌNG
============================================================

Tiểu Vũ KHÔNG được tự nói thay cho người dùng.

Tiểu Vũ KHÔNG được tự đóng vai học sinh.

Tiểu Vũ KHÔNG được tự hỏi rồi tự trả lời.

Tiểu Vũ KHÔNG được tự tạo ra câu trả lời của Mini.

Tiểu Vũ chỉ trả lời khi thật sự có lời nói từ người dùng
hoặc khi chương trình gia sư gửi một câu hỏi cần đọc cho học sinh.

============================================================
CHAT MODE
============================================================

Ở CHAT MODE:

- Nói chuyện tự nhiên với Lão sư.
- Có thể trả lời câu hỏi.
- Có thể đùa vui.
- Không tự tạo cuộc hội thoại.
- Không tự hỏi rồi tự trả lời.
- Không tự đóng vai nhiều người.

Lão sư là người điều khiển cuộc trò chuyện.

============================================================
TUTOR MODE
============================================================

Khi chương trình chuyển sang TUTOR MODE:

Tiểu Vũ đang dạy Mini.

Tiểu Vũ phải:

1. Chủ động đọc câu hỏi do lesson_flow cung cấp.
2. Sau khi đọc câu hỏi thì DỪNG LẠI.
3. Chờ Mini trả lời.
4. Không tự trả lời thay Mini.
5. Không tự tạo đáp án.
6. Không tự tạo câu hỏi mới.
7. Không tự kết thúc câu hỏi.
8. Không tự đóng vai Mini.

Lesson Flow là nơi quyết định:

- đáp án đúng
- đáp án sai
- gợi ý
- điểm số
- câu hỏi tiếp theo
- kết thúc buổi học

Tiểu Vũ chỉ có nhiệm vụ:

NGHE → CHUYỂN LỜI NÓI THÀNH TEXT → NÓI PHẢN HỒI ĐƯỢC CHƯƠNG TRÌNH YÊU CẦU.

============================================================
KHI MINI TRẢ LỜI
============================================================

Ví dụ:

Tiểu Vũ:
"Mini ơi, 15 cộng 29 bằng bao nhiêu?"

Sau đó phải CHỜ.

Nếu Mini nói:

"44"

thì Tiểu Vũ KHÔNG tự quyết định đúng hay sai.

Chương trình sẽ kiểm tra.

Nếu chương trình gửi:

"Đúng rồi!"

thì Tiểu Vũ nói:

"Đúng rồi! Giỏi quá!"

Nếu chương trình gửi:

"Không sao, thử lại nha."

thì Tiểu Vũ nói:

"Không sao, Mini thử lại nha."

============================================================
KÍCH HOẠT GIA SƯ
============================================================

Nếu đang CHAT MODE và nghe thấy câu như:

"Mini muốn học"

"Đậu Phộng muốn học"

"Mini học"

"bắt đầu học"

"vào học"

thì hiểu rằng người dùng muốn chuyển sang
chế độ gia sư.

Không tự nói dài.

Chỉ xác nhận ngắn gọn.

Ví dụ:

"Ừ, Mini muốn học rồi ha. Mình bắt đầu nha."

Sau đó chương trình lesson_flow sẽ điều khiển buổi học.

============================================================
XƯNG HÔ
============================================================

Người dùng chính là Minh Tâm.

Minh Tâm là NAM.

Gọi Minh Tâm là:

"Lão sư"

Tiểu Vũ là NỮ.

Giọng nói:

- nữ
- miền Nam Việt Nam
- tự nhiên
- thân mật

Không gọi Minh Tâm là bà, chị, cô, nàng, mẹ.

============================================================
PHONG CÁCH
============================================================

Nói tự nhiên.

Không nói kiểu robot.

Không giải thích dài.

Không tự độc thoại.

Không tự tạo hội thoại giả.

Không tự trả lời câu hỏi của chính mình.

============================================================
"""


# ============================================================
# AUDIO OUTPUT
# ============================================================

audio_stream = None


def start_audio():

    global audio_stream

    if audio_stream is None:

        audio_stream = sd.RawOutputStream(
            samplerate=OUTPUT_RATE,
            channels=1,
            dtype="int16"
        )

        audio_stream.start()


def play_audio(data):

    start_audio()

    audio_stream.write(data)


def stop_audio():

    global audio_stream

    if audio_stream is not None:

        try:

            audio_stream.stop()
            audio_stream.close()

        except Exception:

            pass

        audio_stream = None


# ============================================================
# KIỂM TRA CÂU KÍCH HOẠT
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    return (
        text
        .strip()
        .lower()
        .replace(".", "")
        .replace(",", "")
        .replace("!", "")
        .replace("?", "")
    )


def is_tutor_trigger(text):

    clean = normalize_text(text)

    for trigger in TUTOR_TRIGGERS:

        if trigger in clean:

            return True

    return False


# ============================================================
# CHUYỂN CHẾ ĐỘ
# ============================================================

def enter_tutor_mode():

    global CURRENT_MODE

    CURRENT_MODE = TUTOR_MODE

    print()
    print("=" * 60)
    print("🎓 CHUYỂN SANG CHẾ ĐỘ GIA SƯ")
    print("=" * 60)
    print()


def enter_chat_mode():

    global CURRENT_MODE

    CURRENT_MODE = CHAT_MODE

    print()
    print("=" * 60)
    print("💬 CHUYỂN SANG CHẾ ĐỘ TRÒ CHUYỆN")
    print("=" * 60)
    print()


# ============================================================
# MICROPHONE
# ============================================================

async def microphone_sender(session):

    loop = asyncio.get_running_loop()

    print(
        "🎤 Microphone đang hoạt động...",
        flush=True
    )

    def callback(
        indata,
        frames,
        time_info,
        status
    ):

        if status:

            print(
                "MIC:",
                status,
                flush=True
            )

        audio_bytes = indata.tobytes()

        asyncio.run_coroutine_threadsafe(

            session.send_realtime_input(

                audio=types.Blob(
                    data=audio_bytes,
                    mime_type="audio/pcm;rate=16000"
                )

            ),

            loop
        )

    with sd.InputStream(

        device=MIC,

        samplerate=INPUT_RATE,

        channels=CHANNELS,

        dtype="int16",

        blocksize=BLOCKSIZE,

        callback=callback

    ):

        while True:

            await asyncio.sleep(0.1)


# ============================================================
# NHẬN PHẢN HỒI GEMINI
# ============================================================

async def receive_loop(session):

    global CURRENT_MODE

    while True:

        async for response in session.receive():

            # =================================================
            # USER TRANSCRIPTION
            # =================================================

            if (
                response.server_content
                and response.server_content.input_transcription
            ):

                text = (
                    response.server_content
                    .input_transcription
                    .text
                )

                if text:

                    print(
                        "\n👤 Lão sư:",
                        text,
                        flush=True
                    )

                    # =========================================
                    # PHÁT HIỆN YÊU CẦU HỌC
                    # =========================================

                    if (
                        CURRENT_MODE == CHAT_MODE
                        and is_tutor_trigger(text)
                    ):

                        enter_tutor_mode()

                        # Chỉ xác nhận.
                        # KHÔNG tự tạo câu hỏi.
                        await session.send_realtime_input(

                            text=(
                                "Hãy xác nhận thật ngắn rằng "
                                "Mini đã muốn học và Tiểu Vũ "
                                "đã sẵn sàng. "
                                "Không đặt câu hỏi mới. "
                                "Không tự trả lời. "
                                "Không tự đóng vai Mini."
                            )

                        )


            # =================================================
            # TIỂU VŨ TRANSCRIPTION
            # =================================================

            if (
                response.server_content
                and response.server_content.output_transcription
            ):

                text = (
                    response.server_content
                    .output_transcription
                    .text
                )

                if text:

                    print(
                        "💗 Tiểu Vũ:",
                        text,
                        flush=True
                    )


            # =================================================
            # AUDIO CHUNK
            # =================================================

            if (
                response.server_content
                and response.server_content.model_turn
            ):

                for part in (
                    response.server_content
                    .model_turn.parts
                ):

                    if part.inline_data:

                        audio = (
                            part.inline_data.data
                        )

                        play_audio(audio)


            # =================================================
            # TURN COMPLETE
            # =================================================

            if (
                response.server_content
                and response.server_content.turn_complete
            ):

                stop_audio()

                print(
                    "\n🎤 Tiểu Vũ đang nghe...",
                    flush=True
                )


# ============================================================
# MAIN
# ============================================================

async def main():

    print()

    print("=" * 60)
    print("       TIỂU VŨ LIVE VOICE")
    print("       CHAT + TUTOR MODE")
    print("=" * 60)

    print()

    print(
        "🔌 Đang kết nối Gemini Live...",
        flush=True
    )


    # ========================================================
    # CONFIG
    # ========================================================

    config = types.LiveConnectConfig(

        response_modalities=[
            "AUDIO"
        ],

        speech_config=types.SpeechConfig(

            voice_config=types.VoiceConfig(

                prebuilt_voice_config=
                types.PrebuiltVoiceConfig(

                    voice_name="Aoede"

                )

            )

        ),

        system_instruction=types.Content(

            parts=[

                types.Part(
                    text=SYSTEM_INSTRUCTION
                )

            ]

        ),

        input_audio_transcription={},

        output_audio_transcription={}

    )


    # ========================================================
    # CONNECT
    # ========================================================

    async with client.aio.live.connect(

        model=MODEL,

        config=config

    ) as session:

        print(
            "✅ Đã kết nối Gemini Live!",
            flush=True
        )

        print()

        print(
            "💬 CHAT MODE",
            flush=True
        )

        print(
            "💡 Nói chuyện tự nhiên với Tiểu Vũ.",
            flush=True
        )

        print(
            "💡 Nói 'Mini muốn học' để vào gia sư.",
            flush=True
        )

        print(
            "💡 Nhấn Ctrl+C để thoát.",
            flush=True
        )

        print()


        # ====================================================
        # RECEIVE LOOP
        # ====================================================

        receive_task = asyncio.create_task(

            receive_loop(session)

        )


        # ====================================================
        # CHÀO BAN ĐẦU
        # ====================================================

        await session.send_realtime_input(

            text=(
                "Hãy chào Lão sư thật ngắn gọn, "
                "thân mật và tự nhiên. "
                "Sau đó dừng lại và chờ Lão sư nói. "
                "Không tự hỏi rồi tự trả lời."
            )

        )


        # ====================================================
        # MICROPHONE
        # ====================================================

        microphone_task = asyncio.create_task(

            microphone_sender(session)

        )


        # ====================================================
        # CHẠY SONG SONG
        # ====================================================

        await asyncio.gather(

            microphone_task,

            receive_task

        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        stop_audio()

        print()

        print(
            "👋 Tiểu Vũ đã tắt."
        )

    except Exception as e:

        stop_audio()

        print()

        print(
            "❌ Lỗi:",
            type(e).__name__,
            e
        )