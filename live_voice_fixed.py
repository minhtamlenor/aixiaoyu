# ============================================================
# TIỂU VŨ - LIVE VOICE FIXED RUNTIME
#
# Giữ nguyên toàn bộ student / tutor / subject / tool logic
# trong live_voice.py. File này chỉ thay lớp runtime audio
# và cách xử lý transcript để sửa:
#   1. Có transcription nhưng không phát âm thanh.
#   2. Âm thanh giật/đứt khi chuyển sang Tutor Mode.
#   3. Audio cũ tiếp tục phát sau khi Gemini báo interrupted.
#   4. Một transcript bị xử lý lặp nhiều lần.
# ============================================================

import asyncio

import sounddevice as sd

import live_voice as core


# ============================================================
# AUDIO OUTPUT
# ============================================================

_audio_stream = None
_audio_queue = None
_audio_task = None
_audio_generation = 0


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


async def _audio_writer():
    """Play queued Gemini PCM chunks without blocking receive_loop."""
    while True:
        item = await _audio_queue.get()

        if item is None:
            return

        generation, data = item

        # Discard chunks belonging to a response that was interrupted.
        if generation != _audio_generation:
            continue

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


async def _start_audio_runtime():
    global _audio_queue
    global _audio_task
    global _audio_generation

    _audio_generation = 0
    _audio_queue = asyncio.Queue(maxsize=32)
    _audio_task = asyncio.create_task(_audio_writer())


def _clear_audio_queue():
    global _audio_generation

    # Increment generation first so a chunk already waiting in the queue
    # can never be played after an interruption.
    _audio_generation += 1

    if _audio_queue is None:
        return

    while True:
        try:
            _audio_queue.get_nowait()
        except asyncio.QueueEmpty:
            break


async def _stop_audio_runtime():
    global _audio_task
    global _audio_queue

    _clear_audio_queue()

    if _audio_task is not None:
        try:
            _audio_queue.put_nowait(None)
        except asyncio.QueueFull:
            pass

        try:
            await _audio_task
        except Exception:
            pass

    _audio_task = None
    _audio_queue = None
    _close_audio()


async def _queue_audio(data):
    if not data or _audio_queue is None:
        return

    item = (_audio_generation, data)

    try:
        _audio_queue.put_nowait(item)
    except asyncio.QueueFull:
        # Keep latency bounded. If output falls behind, discard the oldest
        # queued chunk instead of allowing an audible growing delay.
        try:
            _audio_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

        try:
            _audio_queue.put_nowait(item)
        except asyncio.QueueFull:
            pass


# ============================================================
# SEND TEXT COMMAND
# ============================================================
# Gemini 3.1 Flash Live dùng send_realtime_input(text=...) cho
# command nội bộ sau khi phiên đã bắt đầu.
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
            # INTERRUPTION
            # --------------------------------------------------
            if getattr(server, "interrupted", False):
                print(
                    "🛑 Tiểu Vũ bị người nói ngắt lời.",
                    flush=True,
                )
                # Google khuyến nghị dừng phát và xoá buffer ngay khi
                # server báo interrupted.
                _clear_audio_queue()

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

                # input_transcription có thể xuất hiện nhiều lần trong
                # cùng một lượt. Không xử lý lại cùng một transcript.
                if clean_text and clean_text != input_text_seen:
                    input_text_seen = clean_text

                    # Khi đang ở Tutor Mode và lesson đang chờ câu trả lời,
                    # transcript của học sinh phải được chuyển vào lesson flow.
                    # Các transcript chat bình thường để Gemini tự xử lý.
                    command = core.detect_tutor_command(clean_text)

                    should_process = (
                        command["intent"] != "chat"
                        or core.mentions_teacher(clean_text)
                        or (
                            core.tutor_mode
                            and core.lesson_session
                            and core.lesson_waiting_for_answer
                        )
                    )

                    if should_process:
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
                        await _queue_audio(data)

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

    await _start_audio_runtime()

    try:
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
    finally:
        await _stop_audio_runtime()


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
        await _stop_audio_runtime()


def cleanup():
    core.shutdown_requested = True
    _clear_audio_queue()
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
