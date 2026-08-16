# ============================================================
# TIỂU VŨ - MAIN
# ============================================================

import asyncio

from voice_io import start_voice_io, cleanup_voice_io


# ============================================================
# MAIN
# ============================================================
def main():
    try:
        asyncio.run(start_voice_io())
    except KeyboardInterrupt:
        print()
        print("👋 Tiểu Vũ đã tắt.")
    except Exception as e:
        print()
        print("❌ Tiểu Vũ gặp lỗi:")
        print(e)
    finally:
        cleanup_voice_io()


if __name__ == "__main__":
    main()
