from datetime import datetime
from zoneinfo import ZoneInfo


VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_vietnam_now():
    """Return the current Vietnam time as a timezone-aware datetime."""
    return datetime.now(VIETNAM_TZ)


def format_vietnamese_hour(hour: int) -> str:
    """Natural Vietnamese spoken form for a 24-hour clock hour."""
    hour = hour % 24

    if hour == 23:
        return "11 giờ khuya"
    if hour == 0:
        return "12 giờ khuya"
    if hour == 1:
        return "1 giờ khuya"
    if 2 <= hour <= 10:
        return f"{hour} giờ sáng"
    if hour == 11:
        return "11 giờ trưa"
    if hour == 12:
        return "12 giờ trưa"
    if 13 <= hour <= 18:
        return f"{hour - 12} giờ chiều"
    return f"{hour - 12} giờ tối"


def get_time_period(hour: int) -> str:
    """Natural Vietnamese period used by greetings and time-aware prompts."""
    hour = hour % 24

    if 0 <= hour <= 1:
        return "khuya"
    if 2 <= hour <= 6:
        return "sáng sớm"
    if 7 <= hour <= 10:
        return "buổi sáng"
    if 11 <= hour <= 12:
        return "buổi trưa"
    if 13 <= hour <= 18:
        return "buổi chiều"
    if 19 <= hour <= 22:
        return "buổi tối"
    return "khuya"


def get_current_time():
    now = get_vietnam_now()

    weekdays = [
        "Thứ Hai",
        "Thứ Ba",
        "Thứ Tư",
        "Thứ Năm",
        "Thứ Sáu",
        "Thứ Bảy",
        "Chủ Nhật"
    ]

    return {
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": weekdays[now.weekday()],
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second,
        "spoken_time": format_vietnamese_hour(now.hour),
        "period": get_time_period(now.hour),
        "datetime": (
            f"{weekdays[now.weekday()]}, "
            f"ngày {now.strftime('%d/%m/%Y')}, "
            f"lúc {now.strftime('%H:%M')}"
        )
    }


def get_time_text():
    data = get_current_time()

    return (
        f"Hiện tại là {data['spoken_time']} "
        f"{data['minute']:02d} phút. "
        f"Hôm nay là {data['weekday']}, ngày {data['date']}. "
        f"Múi giờ Việt Nam (UTC+7)."
    )
