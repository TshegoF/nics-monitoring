"""
auth.py — Authentication with PIN security + receptionist role
"""
import streamlit as st
from database import get_setting, get_agent_usernames, get_agents, get_receptionists

ADMINS      = {"edgart", "mabokop", "caleb"}
SUPERVISORS = {"nomsa", "tmodise", "jramahlo", "tshepom", "bmohau"}

DEFAULT_ADMIN_PASSWORD      = "Admin@2025"
DEFAULT_SUPERVISOR_PASSWORD = "nics1068"


def get_admin_password() -> str:
    return get_setting("admin_password", DEFAULT_ADMIN_PASSWORD)

def get_supervisor_password() -> str:
    return get_setting("supervisor_password", DEFAULT_SUPERVISOR_PASSWORD)


def try_login(username: str, password: str, pin: str = "") -> dict | None:
    username = username.strip().lower().replace("@nics.co.za", "")

    # ── Admin ──
    if username in ADMINS:
        if password == get_admin_password():
            return {"username": username, "role": "admin",
                    "display_name": f"{username}@nics.co.za"}
        return None

    # ── Supervisor ──
    if username in SUPERVISORS:
        if password == get_supervisor_password():
            return {"username": username, "role": "supervisor",
                    "display_name": f"{username}@nics.co.za"}
        return None

    # ── Receptionist ──
    receptionists = get_receptionists()
    rec_usernames = [r["username"].lower() for r in receptionists]
    if username in rec_usernames:
        rec = next(r for r in receptionists if r["username"].lower() == username)
        stored_pin = rec.get("pin", "") or ""
        if stored_pin and pin != stored_pin:
            return None
        exact = rec["username"]
        return {"username": exact, "role": "receptionist",
                "display_name": f"{exact}@nics.co.za"}

    # ── Agent — verified by PIN ──
    agents = get_agents()
    agent_usernames = [a["username"].lower() for a in agents]
    if username in agent_usernames:
        exact = next(a["username"] for a in agents if a["username"].lower() == username)
        agent = next(a for a in agents if a["username"].lower() == username)
        stored_pin = agent.get("pin", "") or ""
        # If PIN is set, require it
        if stored_pin:
            if pin != stored_pin:
                return None
        return {"username": exact, "role": "agent",
                "display_name": f"{exact}@nics.co.za"}

    return None


def is_logged_in() -> bool:
    return st.session_state.get("user") is not None

def current_user() -> dict:
    return st.session_state.get("user", {})

def current_role() -> str:
    return current_user().get("role", "")

def current_username() -> str:
    return current_user().get("username", "")

def logout():
    for key in ["user", "active_tab"]:
        st.session_state.pop(key, None)
