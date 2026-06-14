from datetime import datetime


def get_current_time() -> str:
    now = datetime.now()
    return f"It's {now.strftime('%-I:%M %p')}."
