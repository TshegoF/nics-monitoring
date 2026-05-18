"""
auth.py  —  Authentication and role management
"""
import streamlit as st
from database import get_setting, get_agent_usernames, get_books

# ── Fixed admin usernames ──────────────────────────────────────────────────
ADMINS = {"edgart", "mabokop"}
SUPERVISORS = {"nomsa", "tmodise", "jramahlo", "tshepom", "bmohau"}

DEFAULT_ADMIN_PASSWORD      = "Admin@2025"
DEFAULT_SUPERVISOR_PASSWORD = "nics1068"


def get_admin_password() -> str:
    return get_setting("admin_password", DEFAULT_ADMIN_PASSWORD)

def get_supervisor_password() -> str:
    return get_setting("supervisor_password", DEFAULT_SUPERVISOR_PASSWORD)


def try_login(username: str, password: str) -> dict | None:
    """
    Returns a dict with keys: username, role, display_name
    Returns None if login fails.
    """
    username = username.strip().lower().replace("@nics.co.za", "")

    # Admin
    if username in ADMINS:
        if password == get_admin_password():
            return {"username": username, "role": "admin", "display_name": f"{username}@nics.co.za"}
        return None

    # Supervisor
    if username in SUPERVISORS:
        if password == get_supervisor_password():
            return {"username": username, "role": "supervisor", "display_name": f"{username}@nics.co.za"}
        return None

    # Agent — no password needed
    agents = get_agent_usernames()
    if username in [a.lower() for a in agents]:
        # find exact case
        exact = next((a for a in agents if a.lower() == username), username)
        return {"username": exact, "role": "agent", "display_name": f"{exact}@nics.co.za"}

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
