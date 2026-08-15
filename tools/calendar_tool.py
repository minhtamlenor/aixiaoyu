# ============================================================
# TIỂU VŨ - CALENDAR TOOL
# DƯƠNG LỊCH + THỨ + ÂM LỊCH
# ============================================================

from datetime import datetime
from zoneinfo import ZoneInfo

from lunardate import LunarDate


VIETNAM_TZ = ZoneInfo(
    "Asia/Ho_Chi_Minh"
)


WEEKDAYS = [
    "Thứ Hai",
    "Thứ Ba",
    "Thứ Tư",
    "Thứ Năm",
    "Thứ Sáu",
    "Thứ Bảy",
    "Chủ Nhật",
]


def get_calendar():

    now = datetime.now(
        VIETNAM_TZ
    )

    lunar = LunarDate.fromSolarDate(
        now.year,
        now.month,
        now.day
    )

    weekday = WEEKDAYS[
        now.weekday()
    ]

    return {
        "weekday": weekday,

        "solar_date": (
            f"{now.day:02d}/"
            f"{now.month:02d}/"
            f"{now.year}"
        ),

        "solar_year": now.year,
        "solar_month": now.month,
        "solar_day": now.day,

        "lunar_date": (
            f"{lunar.day:02d}/"
            f"{lunar.month:02d}/"
            f"{lunar.year}"
        ),

        "lunar_year": lunar.year,
        "lunar_month": lunar.month,
        "lunar_day": lunar.day,

        "time": now.strftime(
            "%H:%M:%S"
        ),
    }


def get_calendar_text():

    data = get_calendar()

    return (
        f"Hôm nay là {data['weekday']}, "
        f"ngày {data['solar_date']} "
        f"dương lịch, "
        f"tương ứng ngày "
        f"{data['lunar_date']} âm lịch. "
        f"Hiện tại là {data['time']} "
        f"giờ Việt Nam."
    )