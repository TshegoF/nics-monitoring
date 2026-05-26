"""
utils.py — Shared helpers
"""
from datetime import datetime, timedelta, timezone

START_TIME    = datetime.strptime("08:00", "%H:%M").time()
KNOCKOFF_TIME = datetime.strptime("16:30", "%H:%M").time()
TEA_LIMIT     = 15   # minutes
LUNCH_LIMIT   = 60   # minutes
BATHROOM_LIMIT = 5   # minutes
MEETING_LIMIT  = 30  # minutes (minimum expected)
REQUIRED_HOURS = 8   # hours per day

SAST = timezone(timedelta(hours=2))

# ── Dropdown reasons ───────────────────────────────────────────────────────
LATE_REASONS = [
    "-- Select a reason --",
    "Load shedding / power outage",
    "Taxi strike / no transport available",
    "Accident on the road",
    "Heavy traffic congestion",
    "Family emergency",
    "Medical emergency",
    "Public transport delay",
    "Car breakdown",
    "Personal emergency",
    "Overslept",
    "Heavy rain / flooding",
    "Road closure / diversion",
    "Child care issue",
    "Other (speak to supervisor)",
]

TEA_REASONS = [
    "-- Select a reason --",
    "Feeling unwell / nausea",
    "Long queue at the kitchen",
    "Bathroom emergency",
    "Medical condition",
    "Delayed by colleague",
    "Personal care / hygiene",
    "Lost track of time",
    "Other (speak to supervisor)",
]

LUNCH_REASONS = [
    "-- Select a reason --",
    "Waiting for food / long queue",
    "Feeling unwell",
    "Personal emergency",
    "Bathroom emergency",
    "Delayed by colleague",
    "Medical condition",
    "Lost track of time",
    "Other (speak to supervisor)",
]

BATHROOM_REASONS = [
    "-- Select a reason --",
    "Nature call",
    "Feeling unwell / stomach cramps",
    "Menstrual / personal care",
    "Medical condition",
    "Other (speak to supervisor)",
]

RECEPTION_REASONS = [
    "-- Select a reason --",
    "Delivering documents",
    "Receiving a visitor",
    "Collecting a parcel / delivery",
    "IT / facilities request",
    "Management request",
    "Personal errand (approved)",
    "Other (speak to supervisor)",
]

# ── Time helpers ───────────────────────────────────────────────────────────
def calc_late_minutes(clock_in_str: str) -> int:
    try:
        ci    = datetime.strptime(clock_in_str, "%H:%M").time()
        delta = (datetime.combine(datetime.today(), ci) -
                 datetime.combine(datetime.today(), START_TIME)).total_seconds() / 60
        return max(0, int(delta))
    except Exception:
        return 0

def calc_break_extra(start_str: str, end_str: str, limit: int) -> int:
    try:
        s    = datetime.strptime(start_str, "%H:%M")
        e    = datetime.strptime(end_str,   "%H:%M")
        mins = int((e - s).total_seconds() / 60)
        return max(0, mins - limit)
    except Exception:
        return 0

def calc_new_knockoff(late: int, tea_extra: int, lunch_extra: int,
                      bathroom_extra: int = 0) -> str:
    total = late + tea_extra + lunch_extra + bathroom_extra
    ko    = datetime.combine(datetime.today(), KNOCKOFF_TIME) + timedelta(minutes=total)
    return ko.strftime("%H:%M")

def calc_worked_minutes(clock_in: str, clock_out: str,
                        tea_start: str, tea_end: str,
                        lunch_start: str, lunch_end: str) -> int:
    """Calculate actual working/dialling minutes excluding breaks."""
    try:
        ci = datetime.strptime(clock_in,  "%H:%M")
        co = datetime.strptime(clock_out, "%H:%M")
        total = int((co - ci).total_seconds() / 60)
        if tea_start and tea_end:
            try:
                ts = datetime.strptime(tea_start, "%H:%M")
                te = datetime.strptime(tea_end,   "%H:%M")
                total -= int((te - ts).total_seconds() / 60)
            except: pass
        if lunch_start and lunch_end:
            try:
                ls = datetime.strptime(lunch_start, "%H:%M")
                le = datetime.strptime(lunch_end,   "%H:%M")
                total -= int((le - ls).total_seconds() / 60)
            except: pass
        return max(0, total)
    except Exception:
        return 0

def now_str() -> str:
    return datetime.now(SAST).strftime("%H:%M")

def today_str() -> str:
    return datetime.now(SAST).strftime("%Y-%m-%d")

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
