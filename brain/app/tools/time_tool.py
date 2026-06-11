from datetime import datetime

_ONES = [
    "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty"]


def _num(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return _TENS[n // 10] + ("-" + _ONES[n % 10] if n % 10 else "")


def _kitchen_time(hour: int, minute: int) -> str:
    if hour < 12:
        period = "in the morning"
    elif hour < 17:
        period = "in the afternoon"
    elif hour < 21:
        period = "in the evening"
    else:
        period = "at night"

    h = hour % 12 or 12
    h_next = (hour + 1) % 12 or 12

    if minute == 0:
        return f"{_num(h)} o'clock {period}"
    if minute == 15:
        return f"quarter past {_num(h)} {period}"
    if minute == 30:
        return f"half past {_num(h)} {period}"
    if minute == 45:
        return f"quarter to {_num(h_next)} {period}"
    if minute < 30:
        return f"{_num(minute)} past {_num(h)} {period}"
    return f"{_num(60 - minute)} to {_num(h_next)} {period}"


def get_current_time() -> str:
    now = datetime.now()
    return f"It's {_kitchen_time(now.hour, now.minute)}."
