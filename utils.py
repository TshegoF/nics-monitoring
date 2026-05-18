"""
utils.py  —  Shared helpers for time calculations
"""
from datetime import datetime, timedelta

START_TIME    = datetime.strptime("08:00", "%H:%M").time()
KNOCKOFF_TIME = datetime.strptime("16:30", "%H:%M").time()
TEA_LIMIT     = 15   # minutes
LUNCH_LIMIT   = 60   # minutes


def calc_late_minutes(clock_in_str: str) -> int:
    try:
        ci = datetime.strptime(clock_in_str, "%H:%M").time()
        delta = (datetime.combine(datetime.today(), ci) -
                 datetime.combine(datetime.today(), START_TIME)).total_seconds() / 60
        return max(0, int(delta))
    except Exception:
        return 0


def calc_break_extra(start_str: str, end_str: str, limit: int) -> int:
    try:
        s = datetime.strptime(start_str, "%H:%M")
        e = datetime.strptime(end_str, "%H:%M")
        mins = int((e - s).total_seconds() / 60)
        return max(0, mins - limit)
    except Exception:
        return 0


def calc_new_knockoff(late: int, tea_extra: int, lunch_extra: int) -> str:
    total = late + tea_extra + lunch_extra
    ko = datetime.combine(datetime.today(), KNOCKOFF_TIME) + timedelta(minutes=total)
    return ko.strftime("%H:%M")


def now_str() -> str:
    return datetime.now().strftime("%H:%M")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def format_email(username: str) -> str:
    return f"{username}@nics.co.za"


def safe_str(val) -> str:
    s = str(val) if val is not None else ""
    return s if s.strip() not in ("", "nan", "NaN", "None") else ""


def safe_int(val, default=0) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default
