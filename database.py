"""
database.py — Supabase interactions v2
"""
import os, json
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

SAST = timezone(timedelta(hours=2))

def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set.")
    return create_client(url, key)

def today_sast():
    return datetime.now(SAST).strftime("%Y-%m-%d")

# ── Attendance ─────────────────────────────────────────────────────────────
def get_attendance_today(date: str = None):
    d  = date or today_sast()
    sb = get_client()
    return (sb.table("attendance").select("*").eq("date", d).execute()).data or []

def get_attendance_all():
    sb = get_client()
    return (sb.table("attendance").select("*").order("date", desc=True).execute()).data or []

def get_attendance_range(start: str, end: str):
    sb = get_client()
    return (sb.table("attendance").select("*")
              .gte("date", start).lte("date", end)
              .order("date").execute()).data or []

def upsert_attendance(record: dict, date: str = None):
    d  = date or today_sast()
    sb = get_client()
    ex = (sb.table("attendance").select("id")
            .eq("date", d).eq("agent", record["agent"]).execute())
    if ex.data:
        sb.table("attendance").update(record).eq("id", ex.data[0]["id"]).execute()
    else:
        record["date"] = d
        sb.table("attendance").insert(record).execute()

def clock_in_agent(agent: str, book: str, clock_in: str,
                   late_minutes: int, reason: str = "", date: str = None):
    d = date or today_sast()
    upsert_attendance({
        "date": d, "agent": agent, "book": book,
        "clock_in": clock_in, "status": "Dialing",
        "late_minutes": late_minutes, "tea_extra": 0,
        "lunch_extra": 0, "bathroom_extra": 0,
        "meeting_extra": 0, "reason": reason,
    }, d)

def update_field(agent: str, field: str, value, date: str = None):
    d  = date or today_sast()
    sb = get_client()
    sb.table("attendance").update({field: value}).eq("date", d).eq("agent", agent).execute()

def clock_out_agent(agent: str, clock_out: str, late_min: int, tea_extra: int,
                    lunch_extra: int, new_knockoff: str, date: str = None,
                    worked_minutes: int = 0):
    d  = date or today_sast()
    sb = get_client()
    sb.table("attendance").update({
        "clock_out": clock_out, "late_minutes": late_min,
        "tea_extra": tea_extra, "lunch_extra": lunch_extra,
        "new_knockoff": new_knockoff, "status": "Clocked Out",
        "worked_minutes": worked_minutes,
    }).eq("date", d).eq("agent", agent).execute()

# ── Agents ─────────────────────────────────────────────────────────────────
def get_agents():
    sb = get_client()
    return (sb.table("agents").select("*").order("username").execute()).data or []

def add_agent(username: str, display_name: str, pin: str = ""):
    get_client().table("agents").insert({
        "username": username, "display_name": display_name, "pin": pin
    }).execute()

def update_agent_pin(username: str, pin: str):
    get_client().table("agents").update({"pin": pin}).eq("username", username).execute()

def remove_agent(username: str):
    get_client().table("agents").delete().eq("username", username).execute()

def get_agent_usernames():
    return [a["username"] for a in get_agents()]

# ── Receptionists ──────────────────────────────────────────────────────────
def get_receptionists():
    sb = get_client()
    return (sb.table("receptionists").select("*").order("username").execute()).data or []

def add_receptionist(username: str, display_name: str, pin: str = ""):
    get_client().table("receptionists").insert({
        "username": username, "display_name": display_name, "pin": pin
    }).execute()

def update_receptionist_pin(username: str, pin: str):
    get_client().table("receptionists").update({"pin": pin}).eq("username", username).execute()

def remove_receptionist(username: str):
    get_client().table("receptionists").delete().eq("username", username).execute()

# ── Books ──────────────────────────────────────────────────────────────────
def get_books():
    sb   = get_client()
    rows = (sb.table("books").select("*").order("book_name").execute()).data or []
    return {r["book_name"]: {
        "supervisors": json.loads(r.get("supervisors", "[]")),
        "agents":      json.loads(r.get("agents", "[]")),
    } for r in rows}

def upsert_book(book_name: str, supervisors: list, agents: list):
    sb  = get_client()
    pay = {"book_name": book_name,
           "supervisors": json.dumps(supervisors),
           "agents": json.dumps(agents)}
    ex  = sb.table("books").select("book_name").eq("book_name", book_name).execute()
    if ex.data:
        sb.table("books").update(pay).eq("book_name", book_name).execute()
    else:
        sb.table("books").insert(pay).execute()

def rename_book(old_name: str, new_name: str):
    """Rename a book without losing its agents/supervisors."""
    sb = get_client()
    ex = sb.table("books").select("*").eq("book_name", old_name).execute()
    if not ex.data:
        return False
    row = ex.data[0]
    # Insert with new name
    sb.table("books").insert({
        "book_name": new_name,
        "supervisors": row.get("supervisors", "[]"),
        "agents": row.get("agents", "[]"),
    }).execute()
    # Also update all attendance records
    sb.table("attendance").update({"book": new_name}).eq("book", old_name).execute()
    # Delete old
    sb.table("books").delete().eq("book_name", old_name).execute()
    return True

def delete_book(book_name: str):
    get_client().table("books").delete().eq("book_name", book_name).execute()

def get_supervisor_books(username: str):
    return {k: v for k, v in get_books().items()
            if username in v.get("supervisors", [])}

def get_agent_books(username: str):
    return [k for k, v in get_books().items()
            if username in v.get("agents", [])]

# ── Settings ───────────────────────────────────────────────────────────────
def get_setting(key: str, default: str = "") -> str:
    sb  = get_client()
    res = sb.table("settings").select("value").eq("key", key).execute()
    return res.data[0]["value"] if res.data else default

def set_setting(key: str, value: str):
    sb = get_client()
    ex = sb.table("settings").select("key").eq("key", key).execute()
    if ex.data:
        sb.table("settings").update({"value": value}).eq("key", key).execute()
    else:
        sb.table("settings").insert({"key": key, "value": value}).execute()
