# ============================================================
# TIỂU VŨ - MAIN
# ============================================================

import asyncio

from live_voice import (
    start_live_voice,
    cleanup
)


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        asyncio.run(
            start_live_voice()
        )

    except KeyboardInterrupt:

        print()
        print("👋 Tiểu Vũ đã tắt.")

    except Exception as e:

        print()
        print("❌ Tiểu Vũ gặp lỗi:")
        print(e)

    finally:

        cleanup()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()