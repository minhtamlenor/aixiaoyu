# ============================================================
# TIỂU VŨ - CONFIG
# ============================================================

import os


# ============================================================
# GEMINI
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "Chưa tìm thấy GEMINI_API_KEY."
    )


MODEL = "gemini-3.1-flash-live-preview"


# ============================================================
# MICROPHONE
# ============================================================

MIC = 1

INPUT_RATE = 16000
OUTPUT_RATE = 24000

CHANNELS = 1
BLOCKSIZE = 1600