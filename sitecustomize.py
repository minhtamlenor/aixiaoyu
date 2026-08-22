"""Tiểu Vũ Chat Story bootstrap.

Python imports sitecustomize automatically during normal startup. This layer adds
Buddhist Story Engine behavior around the existing voice runtime without editing
voice.py, Tutor Engine, audio transport, or Gemini connection code.
"""

import asyncio
import time

import voice
from story_engine import (
    get_story_prompt,
    is_story_request,
    is_story_continue_request,
    proactive_story_allowed,
)


if not getattr(voice, "_xiaoyu_story_bootstrap_v1", False):
    voice._xiaoyu_story_bootstrap_v1 = True
    _base_process_user_text = voice.process_user_text
    _base_send_text = voice.send_text
    _story_last_user_activity = time.monotonic()
    _story_task = None

    async def _proactive_story_loop(session):
        global _story_last_user_activity
        while not voice.shutdown_requested:
            try:
                await asyncio.sleep(5)
                if voice.current_mode != voice.CHAT_MODE:
                    continue
                if voice.model_speaking or not voice.listen_enabled:
                    continue
                if not proactive_story_allowed(_story_last_user_activity):
                    continue

                prompt = get_story_prompt(proactive=True)
                if not prompt:
                    continue

                print("📖 Tiểu Vũ chủ động mở chuyện Phật giáo.", flush=True)
                await _base_send_text(session, prompt)
                _story_last_user_activity = time.monotonic()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                print("⚠️ Proactive Buddhist story lỗi:", repr(exc), flush=True)

    def _ensure_story_task(session):
        global _story_task
        if _story_task is None or _story_task.done():
            _story_task = asyncio.create_task(_proactive_story_loop(session))

    async def _story_process_user_text(session, text):
        global _story_last_user_activity
        _story_last_user_activity = time.monotonic()

        if voice.current_mode == voice.CHAT_MODE and is_story_request(text):
            prompt = get_story_prompt(
                continuation=is_story_continue_request(text)
            )
            if prompt:
                print("📖 Tiểu Vũ lấy chuyện từ Buddhist Story Library.", flush=True)
                await _base_send_text(session, prompt)
                return

        await _base_process_user_text(session, text)

    async def _story_send_text(session, text):
        _ensure_story_task(session)
        await _base_send_text(session, text)

    voice.process_user_text = _story_process_user_text
    voice.send_text = _story_send_text
