# ============================================================
# TIỂU VŨ - LIVE VOICE FIXED RUNTIME
#
# Giữ nguyên toàn bộ student / tutor / subject / tool logic
# trong live_voice.py. File này chỉ thay lớp runtime audio
# và cách gửi command để sửa 2 lỗi:
#   1. Có transcription nhưng không phát âm thanh.
#   2. Âm thanh giật/đứt khi chuyển sang Tutor Mode.
# ============================================================

import asyncio

import sounddevice as sd
from google.genai import types

import live_voice as core


# ============================================================
# AUDIO OUTPUT
# ============================================================

_audio_stream = None
_audio_lock = asyncio.Lock()


def _start_audio():
    global _audio_stream

    if _audio_stream is not None:
        return

    _audio_stream = sd.RawOutputStream(
        samplerate=core.OUTPUT_RATE,
        channels=1,
        dtype="int16",
        blocksize=0,
    )
    _audio_stream.start()


def _close_audio():
    global _audio_stream

    stream = _audio_stream
    _audio_stream = None

    if stream is None:
        return

    try:
        stream.stop()
    except Exception:
        pass

    try:
        stream.close()
    except Exception:
        pass


async def _play_audio(data):
    if not data:
        return

    async with _audio_lock:
        try:
            _start_audio()
            await asyncio.to_thread(
                _audio_stream.write,
                data,
            )
        except Exception as error:
            print(
                f"\n⚠️ Audio output lỗi: {error!r}",
                flush=True,
            )
            _close_audio()


# ============================================================
# SEND TEXT COMMAND
# ============================================================
# Gemini 3.1 Flash Live không nên trộn send_client_content
# với send_realtime_input sau khi phiên đã bắt đầu.
# Command nội bộ trong lúc đang hội thoại phải đi bằng
# send_realtime_input(text=...).
# ============================================================

async def send_text_command(
    session,
    text,
    suppress_seconds=3,
):
    loop = asyncio.get_running_loop()

    core.command_suppressed_until = (
        loop.time() + suppress_seconds
    )

    try:
        await session.send_realtime_input(text=text)
        return True
    except Exception as error:
        print(
            "⚠️ Command lỗi:",
            repr(error),
            flush=True,
        )
        return False


# live_voice.process_user_text() gọi send_text_command thông qua
# global namespace của module live_voice, nên thay đúng function ở đây.
core.send_text_command = send_text_command


# ============================================================
# RECEIVE LOOP
# ============================================================

async def receive_loop(session):
    input_text_seen = ""

    try:
        async for response in session.receive():

            # --------------------------------------------------
            # TOOL CALL
            # --------------------------------------------------
            tool = getattr(
                response,
                "tool_call",
                None,
            )

            if tool:
                calls = getattr(
                    tool,
                    "function_calls",
                    None,
                )
                if calls:
                    await core.handle_tool_call(
                        session,
                        calls,
                    )

            server = getattr(
                response,
                "server_content",
                None,
            )

            if not server:
                continue

            # --------------------------------------------------
            # USER TRANSCRIPTION
            # --------------------------------------------------
            input_transcription = getattr(
                server,
                "input_transcription",
                None,
            )

            input_text = getattr(
                input_transcription,
                "text",
                None,
            )

            if input_text:
                clean_text = input_text.strip()

                # input_transcription có thể xuất hiện nhiều lần
                # trong cùng một lượt. Chỉ xử lý một transcript duy nhất.
                if clean_text and clean_text != input_text_seen:
                    input_text_seen = clean_text

                    command = core.detect_tutor_command(
                        clean_text
                    )

                    # Chỉ đưa transcript vào Python controller khi
                    # thực sự là command điều khiển Tutor/Student.
                    # Chat bình thường để Gemini tự xử lý.
                    if (
                        command["intent"] != "chat"
                        or core.mentions_teacher(clean_text)
                    ):
                        await core.process_user_text(
                            session,
                            clean_text,
                        )

            # --------------------------------------------------
            # MODEL TRANSCRIPTION
            # --------------------------------------------------
            output_transcription = getattr(
                server,
                "output_transcription",
                None,
            )

            output_text = getattr(
                output_transcription,
                "text",
                None,
            )

            if output_text:
                print(
                    "💗 Tiểu Vũ:",
                    output_text,
                    flush=True,
                )

            # --------------------------------------------------
            # MODEL AUDIO
            # --------------------------------------------------
            model_turn = getattr(
                server,
                "model_turn",
                None,
            )

            if model_turn:
                for part in getattr(
                    model_turn,
                    "parts",
                    [],
                ):
                    inline_data = getattr(
                        part,
                        "inline_data",
                        None,
                    )

                    data = getattr(
                        inline_data,
                        "data",
                        None,
                    )

                    if data:
                        await _play_audio(data)

            # --------------------------------------------------
            # TURN COMPLETE
            # --------------------------------------------------
            if getattr(
                server,
                "turn_complete",
                False,
            ):
                input_text_seen = ""

                print(
                    "\n🎤 Tiểu Vũ đang nghe...",
                    flush=True,
                )

    except asyncio.CancelledError:
        raise
    except Exception as error:
        print(
            f"\n⚠️ Gemini Live connection lỗi: {error!r}",
            flush=True,
        )
        raise


# ============================================================
# RUN CONNECTION
# ============================================================

async def run_one_connection():
    config = core.build_live_config()

    async with core.client.aio.live.connect(
        model=core.MODEL,
        config=config,
    ) as session:
        print(
            "✅ Gemini Live connected",
            flush=True,
        )

        await asyncio.gather(
            receive_loop(session),
            core.microphone_sender(session),
        )


async def start_live_voice():
    core.shutdown_requested = False
    delay = 1

    try:
        while not core.shutdown_requested:
            try:
                await run_one_connection()
                delay = 1
            except asyncio.CancelledError:
                raise
            except Exception as error:
                print(
                    "Reconnect:",
                    repr(error),
                    flush=True,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10)
    finally:
        _close_audio()


def cleanup():
    core.shutdown_requested = True
    _close_audio()
    print(
        "🧹 Tiểu Vũ đóng.",
        flush=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(start_live_voice())
    except KeyboardInterrupt:
        cleanup()
