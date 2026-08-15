from datetime import datetime
from zoneinfo import ZoneInfo


VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_current_time():
    now = datetime.now(VIETNAM_TZ)

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
        "datetime": (
            f"{weekdays[now.weekday()]}, "
            f"ngày {now.strftime('%d/%m/%Y')}, "
            f"lúc {now.strftime('%H:%M')}"
        )
    }


def get_time_text():
    data = get_current_time()

    return (
        f"Hiện tại là {data['datetime']}. "
        f"Múi giờ Việt Nam (UTC+7)."
    )