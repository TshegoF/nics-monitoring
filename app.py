"""
app.py  —  NICS Employee Time Monitoring System (Streamlit Web App)
Fixes: SA time, auto-refresh without logout, tea/lunch countdown, dashboard, dark mode
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import time

import auth
import database as db
from utils import (
    calc_late_minutes, calc_break_extra, calc_new_knockoff,
    today_str, format_email, safe_str, safe_int,
    TEA_LIMIT, LUNCH_LIMIT
)

# ── South Africa Time (UTC+2) ─────────────────────────────────────────────
SAST = timezone(timedelta(hours=2))

def now_sast():
    return datetime.now(SAST)

def now_str():
    return now_sast().strftime("%H:%M")

def today_str():
    return now_sast().strftime("%Y-%m-%d")

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NICS Time Monitoring",
    page_icon="🕐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Hide Streamlit menu/toolbar ───────────────────────────────────────────
st.markdown("""
<style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    [data-testid="stToolbar"]      {visibility: hidden !important;}
    [data-testid="stDecoration"]   {display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important;}
</style>
""", unsafe_allow_html=True)

# ── Theme CSS (light/dark) ────────────────────────────────────────────────
LIGHT_CSS = """
<style>
:root {
    --bg: #F0F2F6; --card: #FFFFFF; --text: #1F3864;
    --accent: #2E75B6; --border: #D0D8E4;
    --sidebar-bg: #1F3864; --sidebar-text: #FFFFFF;
}
.stApp { background-color: var(--bg); }
section[data-testid="stSidebar"] { background-color: var(--sidebar-bg) !important; }
section[data-testid="stSidebar"] * { color: var(--sidebar-text) !important; }
section[data-testid="stSidebar"] .stButton button {
    background: rgba(255,255,255,0.15) !important;
    color: white !important; border: 1px solid rgba(255,255,255,0.3) !important;
    border-radius: 6px; width: 100%;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(255,255,255,0.3) !important;
}
</style>
"""

DARK_CSS = """
<style>
:root {
    --bg: #1a1a2e; --card: #16213e; --text: #e0e0e0;
    --accent: #4a9edd; --border: #333;
    --sidebar-bg: #0f0f23; --sidebar-text: #e0e0e0;
}
.stApp { background-color: var(--bg) !important; color: var(--text) !important; }
.stApp * { color: var(--text) !important; }
section[data-testid="stSidebar"] { background-color: var(--sidebar-bg) !important; }
[data-testid="stMetric"] { background: var(--card) !important; border-radius: 8px; padding: 8px; }
.stDataFrame { background: var(--card) !important; }
div[data-testid="stMarkdownContainer"] { color: var(--text) !important; }
</style>
"""

# ── Shared CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1F3864 0%, #2E75B6 100%);
        padding: 1.2rem 2rem; border-radius: 10px; color: white;
        text-align: center; margin-bottom: 1.2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .main-header h1 { margin: 0; font-size: 1.6rem; font-weight: 700; color: white !important; }
    .main-header p  { margin: 0.3rem 0 0 0; font-size: 0.9rem; opacity: 0.9; color: white !important; }

    .countdown-box {
        background: linear-gradient(135deg, #1F3864, #2E75B6);
        color: white; border-radius: 12px; padding: 1.5rem;
        text-align: center; margin: 1rem 0;
    }
    .countdown-box .timer { font-size: 3rem; font-weight: 700; font-family: monospace; }
    .countdown-box .label { font-size: 1rem; opacity: 0.9; margin-top: 0.3rem; }
    .countdown-box.over  { background: linear-gradient(135deg, #C00000, #E53935); }

    div[data-testid="stButton"] button { border-radius: 6px; font-weight: 600; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────
defaults = {
    "user": None,
    "active_tab": "dashboard",
    "dark_mode": False,
    "last_refresh": 0.0,
    "tea_countdown_start": None,
    "lunch_countdown_start": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Apply theme
st.markdown(DARK_CSS if st.session_state.dark_mode else LIGHT_CSS, unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────
current_time = now_sast().strftime("%H:%M")
current_date = now_sast().strftime("%A, %d %B %Y")
st.markdown(f"""
<div class="main-header">
    <h1>🕐 EMPLOYEE TIME MONITORING SYSTEM — NICS</h1>
    <p>NICS Call Centre &nbsp;|&nbsp; Work: 08:00–16:30 &nbsp;|&nbsp;
       Tea: 15 min &nbsp;|&nbsp; Lunch: 60 min &nbsp;|&nbsp;
       🇿🇦 {current_date} &nbsp; {current_time} SAST</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════════════════════
if not auth.is_logged_in():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### 🔐 Login")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="e.g. cyounis")
            password = st.text_input("Password", type="password",
                                     placeholder="Supervisors & Admin only — agents leave blank")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username.strip():
                st.error("Please enter your username.")
            else:
                user = auth.try_login(username.strip(), password.strip())
                if user:
                    st.session_state.user = user
                    st.session_state.active_tab = "dashboard" if user["role"] != "agent" else "clockin"
                    st.session_state.last_refresh = time.time()
                    st.rerun()
                else:
                    st.error("Invalid username or password. Agents do not need a password.")

        st.markdown("---")
        st.caption("💡 Agents: enter username only — no password needed.")
        st.caption("💡 Supervisors / Admin: enter username + password.")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# LOGGED IN
# ═══════════════════════════════════════════════════════════════════════════
user     = auth.current_user()
role     = auth.current_role()
username = auth.current_username()

# ── Auto-refresh for dashboard (does NOT log out — only reruns if on dashboard) ──
if role in ("supervisor", "admin") and st.session_state.active_tab == "dashboard":
    now_ts = time.time()
    if now_ts - st.session_state.last_refresh > 10:
        st.session_state.last_refresh = now_ts
        st.rerun()

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**👤 {format_email(username)}**")
    st.caption(f"Role: {role.title()} | 🇿🇦 {current_time} SAST")
    st.markdown("---")

    # Agent self-view
    if role == "agent":
        st.markdown("#### 📋 My Status Today")
        today_records = db.get_attendance_today(today_str())
        my_record = next((r for r in today_records if r["agent"] == username), None)
        if my_record:
            st.success(f"🕐 In: **{my_record.get('clock_in','—')}**")
            tea_s = my_record.get('tea_start','') or ''
            tea_e = my_record.get('tea_end','') or ''
            lunch_s = my_record.get('lunch_start','') or ''
            lunch_e = my_record.get('lunch_end','') or ''
            if tea_s:
                st.info(f"☕ Tea: {tea_s} → {tea_e or 'ongoing'}")
            if lunch_s:
                st.info(f"🍽️ Lunch: {lunch_s} → {lunch_e or 'ongoing'}")
            ko = my_record.get("new_knockoff","") or "16:30"
            st.warning(f"🚪 Knockoff: **{ko}**")
            st.markdown(f"Status: `{my_record.get('status','')}`")
        else:
            st.info("Not clocked in yet.")
        st.markdown("---")

    # Actions
    st.markdown("#### ⏱️ Actions")
    if st.button("⏰ Clock In",         use_container_width=True): st.session_state.active_tab = "clockin";  st.rerun()
    if st.button("☕ Tea Break",         use_container_width=True): st.session_state.active_tab = "tea";      st.rerun()
    if st.button("🍽️ Lunch Break",      use_container_width=True): st.session_state.active_tab = "lunch";    st.rerun()
    if st.button("🚪 Clock Out",         use_container_width=True): st.session_state.active_tab = "clockout"; st.rerun()

    if role in ("supervisor", "admin"):
        st.markdown("---")
        st.markdown("#### 📊 Reports & Tools")
        if st.button("📊 Dashboard",        use_container_width=True): st.session_state.active_tab = "dashboard";    st.rerun()
        if st.button("📋 Daily Report",      use_container_width=True): st.session_state.active_tab = "daily_report"; st.rerun()
        if st.button("📅 Weekly/Monthly",    use_container_width=True): st.session_state.active_tab = "range_report"; st.rerun()
        if st.button("🔍 Absent Today",      use_container_width=True): st.session_state.active_tab = "absent";       st.rerun()
        if st.button("📜 Agent History",     use_container_width=True): st.session_state.active_tab = "history";      st.rerun()
        if st.button("💾 Export to Excel",   use_container_width=True): st.session_state.active_tab = "export";       st.rerun()
        if st.button("📚 Manage Books",      use_container_width=True): st.session_state.active_tab = "books";        st.rerun()
        if st.button("🔑 Change Password",   use_container_width=True): st.session_state.active_tab = "password";     st.rerun()

    if role == "admin":
        st.markdown("---")
        st.markdown("#### ⚙️ Admin")
        if st.button("⚙️ Admin Panel",       use_container_width=True): st.session_state.active_tab = "admin"; st.rerun()

    st.markdown("---")
    # Dark mode toggle
    dm_label = "☀️ Light Mode" if st.session_state.dark_mode else "🌙 Dark Mode"
    if st.button(dm_label, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    if st.button("🚪 Logout", use_container_width=True):
        auth.logout()
        st.rerun()

# ── Main content ───────────────────────────────────────────────────────────
tab = st.session_state.active_tab

# ─────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────
if tab == "dashboard" and role in ("supervisor", "admin"):
    st.subheader("📊 Live Agent Dashboard")
    st.caption(f"🔄 Auto-refreshes every 10 seconds | 🇿🇦 {now_sast().strftime('%H:%M:%S')} SAST")

    records = db.get_attendance_today(today_str())
    agents_cache = db.get_agents()

    if role == "supervisor":
        sup_books = db.get_supervisor_books(username)
        allowed_agents = set()
        for bdata in sup_books.values():
            allowed_agents.update(bdata.get("agents", []))
        records = [r for r in records if r["agent"] in allowed_agents]

    if not records:
        st.info("No agents have clocked in today yet.")
    else:
        total       = len(records)
        on_time     = sum(1 for r in records if safe_int(r.get("late_minutes", 0)) == 0)
        late        = sum(1 for r in records if safe_int(r.get("late_minutes", 0)) > 0)
        on_break    = sum(1 for r in records if r.get("status", "") in ("Tea Break", "Lunch Break"))
        clocked_out = sum(1 for r in records if r.get("status", "") == "Clocked Out")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total", total)
        c2.metric("On Time", on_time)
        c3.metric("Late", late)
        c4.metric("On Break", on_break)
        c5.metric("Clocked Out", clocked_out)
        st.markdown("---")

        # Overage alerts
        current_hm = now_str()
        for r in records:
            status = r.get("status", "")
            if status == "Tea Break" and r.get("tea_start"):
                try:
                    elapsed = int((datetime.strptime(current_hm, "%H:%M") -
                                   datetime.strptime(r["tea_start"], "%H:%M")).total_seconds() / 60)
                    if elapsed > TEA_LIMIT:
                        st.warning(f"⚠️ {format_email(r['agent'])} — Tea {elapsed - TEA_LIMIT} min OVER limit!")
                except: pass
            if status == "Lunch Break" and r.get("lunch_start"):
                try:
                    elapsed = int((datetime.strptime(current_hm, "%H:%M") -
                                   datetime.strptime(r["lunch_start"], "%H:%M")).total_seconds() / 60)
                    if elapsed > LUNCH_LIMIT:
                        st.warning(f"⚠️ {format_email(r['agent'])} — Lunch {elapsed - LUNCH_LIMIT} min OVER limit!")
                except: pass

        # Book filter
        books_in_data = sorted(set(r.get("book", "") or "—" for r in records))
        book_filter = st.selectbox("Filter by Book", ["All Books"] + books_in_data)

        rows = []
        for r in records:
            if book_filter != "All Books" and (r.get("book", "") or "—") != book_filter:
                continue
            tea_dur = "—"
            if r.get("tea_start") and r.get("tea_end"):
                try:
                    tea_dur = str(int((datetime.strptime(r["tea_end"], "%H:%M") -
                                       datetime.strptime(r["tea_start"], "%H:%M")).total_seconds() / 60)) + " min"
                except: pass
            lunch_dur = "—"
            if r.get("lunch_start") and r.get("lunch_end"):
                try:
                    lunch_dur = str(int((datetime.strptime(r["lunch_end"], "%H:%M") -
                                         datetime.strptime(r["lunch_start"], "%H:%M")).total_seconds() / 60)) + " min"
                except: pass
            rows.append({
                "Agent":        format_email(r["agent"]),
                "Book":         r.get("book", "—") or "—",
                "Status":       r.get("status", ""),
                "Clock In":     r.get("clock_in", "") or "—",
                "Tea":          tea_dur,
                "Lunch":        lunch_dur,
                "Knockoff":     r.get("new_knockoff", "") or "16:30",
                "Late (min)":   safe_int(r.get("late_minutes", 0)),
                "Reason":       r.get("reason", "") or "",
            })

        if rows:
            df = pd.DataFrame(rows)
            def color_status(val):
                return {
                    "Tea Break":   "background-color:#FFF3E0;color:#E65100",
                    "Lunch Break": "background-color:#E3F2FD;color:#1565C0",
                    "Clocked Out": "background-color:#E8F5E9;color:#1B5E20",
                    "Dialing":     "background-color:#F3F8FF;color:#1F3864",
                }.get(val, "")
            st.dataframe(df.style.map(color_status, subset=["Status"]),
                         use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────
# CLOCK IN
# ─────────────────────────────────────────────────────────────────────────
elif tab == "clockin":
    st.subheader("⏰ Clock In")
    today_records = db.get_attendance_today(today_str())
    already_in = any(r["agent"] == username for r in today_records)

    if already_in:
        st.warning("✅ You have already clocked in today.")
        my_r = next(r for r in today_records if r["agent"] == username)
        st.info(f"Clock in time: **{my_r.get('clock_in','—')}**")
    else:
        clock_in_time = now_str()
        late_mins = calc_late_minutes(clock_in_time)
        reason = ""

        if late_mins > 0:
            st.error(f"⚠️ You are {late_mins} minutes late (SAST {clock_in_time}). A reason is required.")
            reason = st.text_area("Reason for late arrival *", placeholder="e.g. Traffic, load shedding...")
        else:
            st.success(f"✅ On time! Current SAST time: **{clock_in_time}**")

        agent_books = db.get_agent_books(username)
        book = st.selectbox("Your Book", agent_books) if agent_books else st.text_input("Book", value="Unassigned")

        if st.button("✅ Confirm Clock In", use_container_width=True, type="primary"):
            if late_mins > 0 and not reason.strip():
                st.error("Please provide a reason for your late arrival.")
            else:
                db.clock_in_agent(username, book, clock_in_time, late_mins, reason)
                st.success(f"✅ Clocked in at {clock_in_time} SAST")
                time.sleep(1)
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# TEA BREAK  (with countdown)
# ─────────────────────────────────────────────────────────────────────────
elif tab == "tea":
    st.subheader("☕ Tea Break")
    today_records = db.get_attendance_today(today_str())
    my_record = next((r for r in today_records if r["agent"] == username), None)

    if not my_record:
        st.error("You have not clocked in today. Please clock in first.")
    else:
        tea_start = my_record.get("tea_start", "") or ""
        tea_end   = my_record.get("tea_end", "")   or ""

        if not tea_start:
            st.info(f"Tea break limit: **{TEA_LIMIT} minutes**")
            if st.button("☕ Start Tea Break", use_container_width=True, type="primary"):
                ts = now_str()
                db.update_field(username, "tea_start", ts, today_str())
                db.update_field(username, "status", "Tea Break", today_str())
                st.session_state.tea_countdown_start = now_sast().timestamp()
                st.success(f"Tea break started at {ts} SAST")
                time.sleep(0.5)
                st.rerun()

        elif not tea_end:
            # Show live countdown
            try:
                tea_start_dt = datetime.strptime(f"{today_str()} {tea_start}", "%Y-%m-%d %H:%M").replace(tzinfo=SAST)
                elapsed_secs = int((now_sast() - tea_start_dt).total_seconds())
                elapsed_mins = elapsed_secs // 60
                limit_secs   = TEA_LIMIT * 60
                remaining    = limit_secs - elapsed_secs
                over         = max(0, -remaining)
                rem_m, rem_s = divmod(abs(remaining), 60)
                is_over      = remaining < 0

                if is_over:
                    st.markdown(f"""
                    <div class="countdown-box over">
                        <div class="timer">+{rem_m:02d}:{rem_s:02d}</div>
                        <div class="label">⚠️ OVER the 15-minute limit!</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="countdown-box">
                        <div class="timer">{rem_m:02d}:{rem_s:02d}</div>
                        <div class="label">☕ Tea break — time remaining</div>
                    </div>""", unsafe_allow_html=True)

                st.caption(f"Started: {tea_start} SAST | Elapsed: {elapsed_mins} min")

                if is_over:
                    reason = st.text_area("Reason for overage *", placeholder="Please explain why you exceeded 15 minutes")
                else:
                    reason = ""

                if st.button("✅ End Tea Break", use_container_width=True, type="primary"):
                    if is_over and not reason.strip():
                        st.error("Please provide a reason for the overage.")
                    else:
                        end_t = now_str()
                        db.update_field(username, "tea_end", end_t, today_str())
                        db.update_field(username, "status", "Dialing", today_str())
                        if is_over:
                            over_mins = int(over / 60)
                            db.update_field(username, "tea_extra", over_mins, today_str())
                            if reason: db.update_field(username, "reason", reason, today_str())
                        st.success(f"✅ Tea break ended at {end_t} SAST")
                        st.session_state.tea_countdown_start = None
                        time.sleep(0.5)
                        st.rerun()

                # Auto-rerun every second for live countdown
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Countdown error: {e}")

        else:
            try:
                dur = int((datetime.strptime(tea_end, "%H:%M") -
                           datetime.strptime(tea_start, "%H:%M")).total_seconds() / 60)
                st.success(f"✅ Tea break completed: {tea_start} → {tea_end} ({dur} min)")
            except:
                st.success(f"✅ Tea break completed: {tea_start} → {tea_end}")

# ─────────────────────────────────────────────────────────────────────────
# LUNCH BREAK  (with countdown)
# ─────────────────────────────────────────────────────────────────────────
elif tab == "lunch":
    st.subheader("🍽️ Lunch Break")
    today_records = db.get_attendance_today(today_str())
    my_record = next((r for r in today_records if r["agent"] == username), None)

    if not my_record:
        st.error("You have not clocked in today. Please clock in first.")
    else:
        lunch_start = my_record.get("lunch_start", "") or ""
        lunch_end   = my_record.get("lunch_end", "")   or ""

        if not lunch_start:
            st.info(f"Lunch break limit: **{LUNCH_LIMIT} minutes**")
            if st.button("🍽️ Start Lunch Break", use_container_width=True, type="primary"):
                ts = now_str()
                db.update_field(username, "lunch_start", ts, today_str())
                db.update_field(username, "status", "Lunch Break", today_str())
                st.session_state.lunch_countdown_start = now_sast().timestamp()
                st.success(f"Lunch started at {ts} SAST")
                time.sleep(0.5)
                st.rerun()

        elif not lunch_end:
            try:
                lunch_start_dt = datetime.strptime(f"{today_str()} {lunch_start}", "%Y-%m-%d %H:%M").replace(tzinfo=SAST)
                elapsed_secs   = int((now_sast() - lunch_start_dt).total_seconds())
                elapsed_mins   = elapsed_secs // 60
                limit_secs     = LUNCH_LIMIT * 60
                remaining      = limit_secs - elapsed_secs
                over           = max(0, -remaining)
                rem_m, rem_s   = divmod(abs(remaining), 60)
                is_over        = remaining < 0

                if is_over:
                    st.markdown(f"""
                    <div class="countdown-box over">
                        <div class="timer">+{rem_m:02d}:{rem_s:02d}</div>
                        <div class="label">⚠️ OVER the 60-minute limit!</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="countdown-box">
                        <div class="timer">{rem_m:02d}:{rem_s:02d}</div>
                        <div class="label">🍽️ Lunch break — time remaining</div>
                    </div>""", unsafe_allow_html=True)

                st.caption(f"Started: {lunch_start} SAST | Elapsed: {elapsed_mins} min")

                if is_over:
                    reason = st.text_area("Reason for overage *", placeholder="Please explain why you exceeded 60 minutes")
                else:
                    reason = ""

                if st.button("✅ End Lunch Break", use_container_width=True, type="primary"):
                    if is_over and not reason.strip():
                        st.error("Please provide a reason for the overage.")
                    else:
                        end_t = now_str()
                        db.update_field(username, "lunch_end", end_t, today_str())
                        db.update_field(username, "status", "Dialing", today_str())
                        if is_over:
                            over_mins = int(over / 60)
                            db.update_field(username, "lunch_extra", over_mins, today_str())
                            if reason: db.update_field(username, "reason", reason, today_str())
                        st.success(f"✅ Lunch ended at {end_t} SAST")
                        st.session_state.lunch_countdown_start = None
                        time.sleep(0.5)
                        st.rerun()

                # Auto-rerun every second for live countdown
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Countdown error: {e}")

        else:
            try:
                dur = int((datetime.strptime(lunch_end, "%H:%M") -
                           datetime.strptime(lunch_start, "%H:%M")).total_seconds() / 60)
                st.success(f"✅ Lunch completed: {lunch_start} → {lunch_end} ({dur} min)")
            except:
                st.success(f"✅ Lunch completed: {lunch_start} → {lunch_end}")

# ─────────────────────────────────────────────────────────────────────────
# CLOCK OUT
# ─────────────────────────────────────────────────────────────────────────
elif tab == "clockout":
    st.subheader("🚪 Clock Out")
    today_records = db.get_attendance_today(today_str())
    my_record = next((r for r in today_records if r["agent"] == username), None)

    if not my_record:
        st.error("You have not clocked in today.")
    elif my_record.get("clock_out"):
        st.success(f"✅ You already clocked out at **{my_record['clock_out']}** SAST.")
    else:
        clock_out_time = now_str()
        late_mins   = safe_int(my_record.get("late_minutes", 0))
        tea_extra   = safe_int(my_record.get("tea_extra", 0))
        lunch_extra = safe_int(my_record.get("lunch_extra", 0))

        total_extra  = late_mins + tea_extra + lunch_extra
        new_knockoff = calc_new_knockoff(late_mins, tea_extra, lunch_extra)

        st.markdown("### 📋 Clock Out Summary")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Clock In",    my_record.get("clock_in", "—"))
            st.metric("Tea Extra",   f"{tea_extra} min")
            st.metric("Total Extra", f"{total_extra} min")
        with c2:
            st.metric("Clock Out",   clock_out_time + " SAST")
            st.metric("Lunch Extra", f"{lunch_extra} min")
            st.metric("New Knockoff", new_knockoff)

        if late_mins > 0:
            st.error(f"⚠️ Late arrival penalty: {late_mins} minutes")
        if total_extra == 0:
            st.success("✅ No penalties — standard knockoff at 16:30")

        if st.button("✅ Confirm Clock Out", use_container_width=True, type="primary"):
            db.clock_out_agent(username, clock_out_time, late_mins,
                               tea_extra, lunch_extra, new_knockoff, today_str())
            st.success("✅ Clocked out successfully! Goodbye 👋")
            time.sleep(1.5)
            auth.logout()
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# DAILY REPORT
# ─────────────────────────────────────────────────────────────────────────
elif tab == "daily_report" and role in ("supervisor", "admin"):
    st.subheader("📊 Daily Attendance Report")
    st.caption(f"Date: {today_str()} SAST")
    records = db.get_attendance_today(today_str())

    if role == "supervisor":
        sup_books = db.get_supervisor_books(username)
        allowed = set()
        for bd in sup_books.values(): allowed.update(bd.get("agents", []))
        records = [r for r in records if r["agent"] in allowed]

    if not records:
        st.info("No records for today yet.")
    else:
        rows = []
        for r in records:
            def dur(s, e):
                try: return str(int((datetime.strptime(e,"%H:%M")-datetime.strptime(s,"%H:%M")).total_seconds()/60))+"m"
                except: return "—"
            rows.append({
                "Agent":       format_email(r["agent"]),
                "Book":        r.get("book","—") or "—",
                "Status":      r.get("status",""),
                "In":          r.get("clock_in","") or "—",
                "Out":         r.get("clock_out","") or "—",
                "Tea":         dur(r.get("tea_start",""), r.get("tea_end","")),
                "Lunch":       dur(r.get("lunch_start",""), r.get("lunch_end","")),
                "Late(m)":     safe_int(r.get("late_minutes",0)),
                "Tea+":        safe_int(r.get("tea_extra",0)),
                "Lunch+":      safe_int(r.get("lunch_extra",0)),
                "Knockoff":    r.get("new_knockoff","") or "16:30",
                "Reason":      r.get("reason","") or "",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        late_c = len(df[df["Late(m)"] > 0])
        st.caption(f"Total: {len(df)} | On Time: {len(df)-late_c} | Late: {late_c}")

# ─────────────────────────────────────────────────────────────────────────
# WEEKLY / MONTHLY REPORT
# ─────────────────────────────────────────────────────────────────────────
elif tab == "range_report" and role in ("supervisor", "admin"):
    st.subheader("📅 Weekly / Monthly Report")
    c1, c2 = st.columns(2)
    with c1: start = st.date_input("From", value=now_sast().date().replace(day=1))
    with c2: end   = st.date_input("To",   value=now_sast().date())

    if st.button("Generate Report", type="primary"):
        records = db.get_attendance_range(str(start), str(end))
        if role == "supervisor":
            sup_books = db.get_supervisor_books(username)
            allowed = set()
            for bd in sup_books.values(): allowed.update(bd.get("agents",[]))
            records = [r for r in records if r["agent"] in allowed]

        if not records:
            st.info("No records found.")
        else:
            df = pd.DataFrame(records)
            df["late_minutes"]  = pd.to_numeric(df.get("late_minutes",  0), errors="coerce").fillna(0)
            df["tea_extra"]     = pd.to_numeric(df.get("tea_extra",     0), errors="coerce").fillna(0)
            df["lunch_extra"]   = pd.to_numeric(df.get("lunch_extra",   0), errors="coerce").fillna(0)
            summary = df.groupby("agent").agg(
                Days=("date","nunique"),
                Late_Min=("late_minutes","sum"),
                Tea_Extra=("tea_extra","sum"),
                Lunch_Extra=("lunch_extra","sum"),
            ).reset_index()
            summary["agent"] = summary["agent"].apply(format_email)
            summary.columns = ["Agent","Days Present","Late (min)","Tea Extra (min)","Lunch Extra (min)"]
            st.dataframe(summary, use_container_width=True, hide_index=True)
            import io
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                summary.to_excel(w, index=False, sheet_name="Summary")
                df.to_excel(w, index=False, sheet_name="Raw Data")
            st.download_button("📥 Download Excel", buf.getvalue(),
                file_name=f"NICS_Report_{start}_{end}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ─────────────────────────────────────────────────────────────────────────
# ABSENT TODAY
# ─────────────────────────────────────────────────────────────────────────
elif tab == "absent" and role in ("supervisor", "admin"):
    st.subheader("🔍 Absent Today")
    all_agents    = db.get_agent_usernames()
    today_records = db.get_attendance_today(today_str())
    clocked_in    = {r["agent"] for r in today_records}

    if role == "supervisor":
        sup_books = db.get_supervisor_books(username)
        allowed = set()
        for bd in sup_books.values(): allowed.update(bd.get("agents",[]))
        all_agents = [a for a in all_agents if a in allowed]

    absent = [a for a in all_agents if a not in clocked_in]
    if not absent:
        st.success("✅ All agents have clocked in today!")
    else:
        st.warning(f"⚠️ {len(absent)} agent(s) not yet clocked in:")
        for a in sorted(absent):
            st.markdown(f"- 📧 {format_email(a)}")

# ─────────────────────────────────────────────────────────────────────────
# AGENT HISTORY
# ─────────────────────────────────────────────────────────────────────────
elif tab == "history" and role in ("supervisor", "admin"):
    st.subheader("📜 Agent History")
    all_agents = db.get_agent_usernames()
    if role == "supervisor":
        sup_books = db.get_supervisor_books(username)
        allowed = set()
        for bd in sup_books.values(): allowed.update(bd.get("agents",[]))
        all_agents = [a for a in all_agents if a in allowed]

    selected  = st.selectbox("Select Agent", [format_email(a) for a in sorted(all_agents)])
    sel_uname = selected.split("@")[0]
    records   = db.get_attendance_all()
    agent_recs = [r for r in records if r["agent"] == sel_uname]

    if not agent_recs:
        st.info("No records found for this agent.")
    else:
        df = pd.DataFrame(agent_recs)
        keep = [c for c in ["date","book","clock_in","clock_out","late_minutes",
                             "tea_extra","lunch_extra","new_knockoff","status","reason"] if c in df.columns]
        df = df[keep]
        df.columns = [c.replace("_"," ").title() for c in df.columns]
        st.dataframe(df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────
elif tab == "export" and role in ("supervisor", "admin"):
    st.subheader("💾 Export Attendance")
    c1, c2 = st.columns(2)
    with c1: start = st.date_input("From", value=now_sast().date())
    with c2: end   = st.date_input("To",   value=now_sast().date())
    if st.button("Generate Export", type="primary"):
        records = db.get_attendance_range(str(start), str(end))
        if role == "supervisor":
            sup_books = db.get_supervisor_books(username)
            allowed = set()
            for bd in sup_books.values(): allowed.update(bd.get("agents",[]))
            records = [r for r in records if r["agent"] in allowed]
        if not records:
            st.info("No data found.")
        else:
            import io
            df  = pd.DataFrame(records)
            buf = io.BytesIO()
            df.to_excel(buf, index=False, engine="openpyxl")
            st.download_button("📥 Download Excel", buf.getvalue(),
                file_name=f"NICS_Attendance_{start}_{end}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.success(f"✅ {len(records)} records ready.")

# ─────────────────────────────────────────────────────────────────────────
# MANAGE BOOKS
# ─────────────────────────────────────────────────────────────────────────
elif tab == "books" and role in ("supervisor", "admin"):
    st.subheader("📚 Manage Books")
    books      = db.get_books() if role == "admin" else db.get_supervisor_books(username)
    all_agents = db.get_agent_usernames()
    book_names = list(books.keys())

    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.markdown("#### Books")
        selected_book = st.radio("Select", book_names, label_visibility="collapsed") if book_names else None
        if not book_names: st.info("No books yet.")
        if role == "admin":
            st.markdown("---")
            new_book = st.text_input("New book name")
            if st.button("➕ Create Book") and new_book.strip():
                if new_book.strip() not in books:
                    db.upsert_book(new_book.strip(), [], [])
                    st.success(f"Book '{new_book}' created.")
                    time.sleep(0.4); st.rerun()
                else: st.warning("Already exists.")
            if selected_book and st.button("🗑️ Delete Book", type="secondary"):
                db.delete_book(selected_book)
                st.success("Deleted."); time.sleep(0.4); st.rerun()

    with col_r:
        if selected_book and selected_book in books:
            bdata       = books[selected_book]
            book_agents = bdata.get("agents", [])
            st.markdown(f"#### {selected_book} ({len(book_agents)} agents)")

            if book_agents:
                rem_sel = st.selectbox("Select agent to remove",
                    [format_email(a) for a in sorted(book_agents)], key="rem_ag")
                if st.button("🗑️ Remove from Book"):
                    ru = rem_sel.split("@")[0]
                    db.upsert_book(selected_book, bdata.get("supervisors",[]),
                                   [a for a in book_agents if a != ru])
                    st.success(f"Removed {ru}"); time.sleep(0.4); st.rerun()
            else:
                st.info("No agents in this book yet.")

            not_in = [a for a in all_agents if a not in book_agents]
            if not_in:
                add_sel = st.selectbox("Add agent", [format_email(a) for a in sorted(not_in)], key="add_ag")
                if st.button("➕ Add Agent to Book", type="primary"):
                    au = add_sel.split("@")[0]
                    db.upsert_book(selected_book, bdata.get("supervisors",[]), book_agents + [au])
                    st.success(f"Added {au}"); time.sleep(0.4); st.rerun()

            if role == "admin":
                st.markdown("---")
                st.markdown("**Supervisors:**")
                book_sups = bdata.get("supervisors", [])
                all_sups  = list(auth.SUPERVISORS)
                if book_sups:
                    rs = st.selectbox("Remove supervisor",
                        [format_email(s) for s in book_sups], key="rem_sup")
                    if st.button("🗑️ Remove Supervisor"):
                        ru = rs.split("@")[0]
                        db.upsert_book(selected_book,
                            [s for s in book_sups if s != ru], book_agents)
                        st.rerun()
                not_ass = [s for s in all_sups if s not in book_sups]
                if not_ass:
                    as_ = st.selectbox("Assign supervisor",
                        [format_email(s) for s in not_ass], key="add_sup")
                    if st.button("➕ Assign Supervisor", type="primary"):
                        au2 = as_.split("@")[0]
                        db.upsert_book(selected_book, book_sups + [au2], book_agents)
                        st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────────────────────────────────
elif tab == "password" and role in ("supervisor", "admin"):
    st.subheader("🔑 Change Password")
    pw_type = st.selectbox("Change for", ["Admin", "Supervisor"]) if role == "admin" else "Supervisor"
    with st.form("pw_form"):
        new_pw  = st.text_input("New Password", type="password")
        conf_pw = st.text_input("Confirm",      type="password")
        if st.form_submit_button("Update Password", type="primary"):
            if not new_pw:           st.error("Password cannot be empty.")
            elif new_pw != conf_pw:  st.error("Passwords do not match.")
            else:
                key = "admin_password" if pw_type == "Admin" else "supervisor_password"
                db.set_setting(key, new_pw)
                st.success(f"✅ {pw_type} password updated.")

# ─────────────────────────────────────────────────────────────────────────
# ADMIN PANEL
# ─────────────────────────────────────────────────────────────────────────
elif tab == "admin" and role == "admin":
    st.subheader("⚙️ Admin Panel — Manage Agents")
    agents = db.get_agents()
    c1, c2 = st.columns([1.2, 2])

    with c1:
        st.markdown("#### Add New Agent")
        with st.form("add_form"):
            full_name = st.text_input("Full Name",  placeholder="e.g. Nokwanda Ntuli")
            new_uname = st.text_input("Username",   placeholder="e.g. nokwandan")
            if st.form_submit_button("➕ Add Agent", type="primary"):
                uname = new_uname.strip().replace("@nics.co.za","")
                if not uname or not full_name.strip():
                    st.error("Full name and username required.")
                elif uname in [a["username"] for a in agents]:
                    st.warning(f"'{uname}' already exists.")
                else:
                    db.add_agent(uname, full_name.strip())
                    st.success(f"✅ {full_name} ({format_email(uname)}) added!")
                    time.sleep(0.8); st.rerun()

    with c2:
        st.markdown("#### Registered Agents")
        if agents:
            df_a = pd.DataFrame([{"#":i+1,"Email":format_email(a["username"]),"Name":a.get("display_name","")}
                                  for i,a in enumerate(agents)])
            st.dataframe(df_a, use_container_width=True, hide_index=True)
            st.markdown("---")
            rem = st.selectbox("Remove agent", [format_email(a["username"]) for a in agents])
            if st.button("🗑️ Remove Agent", type="secondary"):
                ru = rem.split("@")[0]
                if ru in auth.ADMINS:
                    st.error("Cannot remove admin accounts.")
                else:
                    db.remove_agent(ru)
                    st.success(f"Removed {rem}"); time.sleep(0.4); st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# FALLBACK
# ─────────────────────────────────────────────────────────────────────────
else:
    if role == "agent":
        st.info("👈 Use the sidebar to Clock In, manage your breaks, or Clock Out.")
    elif role in ("supervisor", "admin"):
        st.session_state.active_tab = "dashboard"
        st.rerun()
