"""
database.py  —  All Supabase interactions for NICS Time Monitoring
"""
import os
import json
from datetime import datetime
from supabase import create_client, Client

# ── Connection ────────────────────────────────────────────────────────────
def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in Streamlit secrets.")
    return create_client(url, key)

# ── Attendance ─────────────────────────────────────────────────────────────
def get_attendance_today():
    today = datetime.now().strftime("%Y-%m-%d")
    sb = get_client()
    res = sb.table("attendance").select("*").eq("date", today).execute()
    return res.data or []

def get_attendance_all():
    sb = get_client()
    res = sb.table("attendance").select("*").order("date", desc=True).execute()
    return res.data or []

def get_attendance_range(start_date: str, end_date: str):
    sb = get_client()
    res = (sb.table("attendance").select("*")
             .gte("date", start_date).lte("date", end_date)
             .order("date").execute())
    return res.data or []

def upsert_attendance(record: dict):
    """Insert or update an attendance record."""
    sb = get_client()
    today = datetime.now().strftime("%Y-%m-%d")
    existing = (sb.table("attendance").select("id")
                  .eq("date", today).eq("agent", record["agent"]).execute())
    if existing.data:
        row_id = existing.data[0]["id"]
        sb.table("attendance").update(record).eq("id", row_id).execute()
    else:
        sb.table("attendance").insert(record).execute()

def clock_in_agent(agent: str, book: str, clock_in: str, late_minutes: int, reason: str = ""):
    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "agent": agent,
        "book": book,
        "clock_in": clock_in,
        "status": "Dialing",
        "late_minutes": late_minutes,
        "tea_extra": 0,
        "lunch_extra": 0,
        "reason": reason,
    }
    upsert_attendance(record)

def update_field(agent: str, field: str, value):
    today = datetime.now().strftime("%Y-%m-%d")
    sb = get_client()
    sb.table("attendance").update({field: value}).eq("date", today).eq("agent", agent).execute()

def clock_out_agent(agent: str, clock_out: str, late_min: int, tea_extra: int,
                    lunch_extra: int, new_knockoff: str):
    today = datetime.now().strftime("%Y-%m-%d")
    sb = get_client()
    sb.table("attendance").update({
        "clock_out": clock_out,
        "late_minutes": late_min,
        "tea_extra": tea_extra,
        "lunch_extra": lunch_extra,
        "new_knockoff": new_knockoff,
        "status": "Clocked Out",
    }).eq("date", today).eq("agent", agent).execute()

# ── Agents ─────────────────────────────────────────────────────────────────
def get_agents():
    sb = get_client()
    res = sb.table("agents").select("*").order("username").execute()
    return res.data or []

def add_agent(username: str, display_name: str):
    sb = get_client()
    sb.table("agents").insert({"username": username, "display_name": display_name}).execute()

def remove_agent(username: str):
    sb = get_client()
    sb.table("agents").delete().eq("username", username).execute()

def get_agent_usernames():
    return [a["username"] for a in get_agents()]

def get_display_name(username: str, agents_cache=None):
    if agents_cache:
        for a in agents_cache:
            if a["username"] == username:
                return a.get("display_name", username)
    return username

# ── Books ──────────────────────────────────────────────────────────────────
def get_books():
    sb = get_client()
    res = sb.table("books").select("*").order("book_name").execute()
    books = {}
    for row in (res.data or []):
        books[row["book_name"]] = {
            "supervisors": json.loads(row.get("supervisors", "[]")),
            "agents": json.loads(row.get("agents", "[]")),
        }
    return books

def save_books(books: dict):
    sb = get_client()
    sb.table("books").delete().neq("book_name", "").execute()
    for bname, bdata in books.items():
        sb.table("books").insert({
            "book_name": bname,
            "supervisors": json.dumps(bdata.get("supervisors", [])),
            "agents": json.dumps(bdata.get("agents", [])),
        }).execute()

def upsert_book(book_name: str, supervisors: list, agents: list):
    sb = get_client()
    existing = sb.table("books").select("book_name").eq("book_name", book_name).execute()
    payload = {"book_name": book_name, "supervisors": json.dumps(supervisors), "agents": json.dumps(agents)}
    if existing.data:
        sb.table("books").update(payload).eq("book_name", book_name).execute()
    else:
        sb.table("books").insert(payload).execute()

def delete_book(book_name: str):
    sb = get_client()
    sb.table("books").delete().eq("book_name", book_name).execute()

def get_supervisor_books(username: str):
    books = get_books()
    return {k: v for k, v in books.items() if username in v.get("supervisors", [])}

def get_agent_books(username: str):
    books = get_books()
    return [k for k, v in books.items() if username in v.get("agents", [])]

# ── Settings (passwords) ───────────────────────────────────────────────────
def get_setting(key: str, default: str = "") -> str:
    sb = get_client()
    res = sb.table("settings").select("value").eq("key", key).execute()
    if res.data:
        return res.data[0]["value"]
    return default

def set_setting(key: str, value: str):
    sb = get_client()
    existing = sb.table("settings").select("key").eq("key", key).execute()
    if existing.data:
        sb.table("settings").update({"value": value}).eq("key", key).execute()
    else:
        sb.table("settings").insert({"key": key, "value": value}).execute()
