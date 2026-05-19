"""
app.py  —  NICS Employee Time Monitoring System (Streamlit Web App)
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

import auth
import database as db
from utils import (
    calc_late_minutes, calc_break_extra, calc_new_knockoff,
    now_str, today_str, format_email, safe_str, safe_int,
    TEA_LIMIT, LUNCH_LIMIT
)

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NICS Time Monitoring",
    page_icon="🕐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide Streamlit menu and footer for all users
st.markdown("""
<style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important;}
</style>
""", unsafe_allow_html=True)

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1F3864 0%, #2E75B6 100%);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .main-header p  { margin: 0.3rem 0 0 0; font-size: 0.95rem; opacity: 0.9; }

    .status-card {
        padding: 1rem 1.2rem;
        border-radius: 8px;
        border-left: 5px solid #2E75B6;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 0.8rem;
    }
    .status-card.late   { border-color: #C00000; background: #FFF5F5; }
    .status-card.tea    { border-color: #ED7D31; background: #FFF8F0; }
    .status-card.lunch  { border-color: #4472C4; background: #F0F4FF; }
    .status-card.out    { border-color: #1D6A2E; background: #F0FFF4; }
    .status-card.dial   { border-color: #2E75B6; background: #F0F6FF; }

    .alert-box {
        padding: 0.8rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    .alert-late  { background: #FFE0E0; border: 1px solid #C00000; color: #C00000; }
    .alert-break { background: #FFF0CC; border: 1px solid #ED7D31; color: #C55A11; }

    .metric-row {
        display: flex; gap: 1rem; margin-bottom: 1rem;
    }
    .metric-box {
        flex: 1; background: white; border-radius: 8px;
        padding: 1rem; text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.07);
    }
    .metric-box .num { font-size: 2rem; font-weight: 700; color: #2E75B6; }
    .metric-box .lbl { font-size: 0.8rem; color: #666; margin-top: 0.2rem; }

    div[data-testid="stButton"] button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    .self-view {
        background: linear-gradient(135deg, #1F3864, #2E75B6);
        color: white; border-radius: 10px;
        padding: 1.5rem; margin-bottom: 1rem;
    }
    .self-view h3 { margin: 0 0 1rem 0; }
    .self-view .row { display: flex; justify-content: space-between; padding: 0.4rem 0;
                      border-bottom: 1px solid rgba(255,255,255,0.2); }
    .self-view .row:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🕐 EMPLOYEE TIME MONITORING SYSTEM</h1>
    <p>NICS Call Centre &nbsp;|&nbsp; Work Hours: 08:00 – 16:30 &nbsp;|&nbsp; Tea: 15 min &nbsp;|&nbsp; Lunch: 60 min</p>
</div>
""", unsafe_allow_html=True)

# ── Initialise session state ──────────────────────────────────────────────
for key, default in [("user", None), ("active_tab", "dashboard"),
                     ("alert_messages", []), ("last_refresh", time.time())]:
    if key not in st.session_state:
        st.session_state[key] = default

# ═══════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════════════════════
if not auth.is_logged_in():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### 🔐 Login")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g. cyounis (no @nics.co.za)")
            password = st.text_input("Password", type="password",
                                     placeholder="Supervisors & Admin only")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username.strip():
                st.error("Please enter your username.")
            else:
                user = auth.try_login(username.strip(), password.strip())
                if user:
                    st.session_state.user = user
                    st.success(f"Welcome, {user['display_name']}! Role: {user['role'].title()}")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("Invalid username or password. Agents do not need a password.")

        st.markdown("---")
        st.caption("💡 Agents: enter username only, no password needed.")
        st.caption("💡 Supervisors / Admin: enter username + password.")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP  (logged in)
# ═══════════════════════════════════════════════════════════════════════════
user     = auth.current_user()
role     = auth.current_role()
username = auth.current_username()

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👤 {format_email(username)}")
    st.caption(f"Role: **{role.title()}**")
    st.markdown("---")

    # ── Agent self-view ──
    if role == "agent":
        st.markdown("#### 📋 My Status Today")
        today_records = db.get_attendance_today()
        my_record = next((r for r in today_records if r["agent"] == username), None)
        if my_record:
            st.success(f"🕐 Clock In: **{my_record.get('clock_in','—')}**")
            st.info(f"☕ Tea: {my_record.get('tea_start','—')} → {my_record.get('tea_end','—')}")
            st.info(f"🍽️ Lunch: {my_record.get('lunch_start','—')} → {my_record.get('lunch_end','—')}")
            ko = my_record.get("new_knockoff","") or "16:30"
            st.warning(f"🚪 Knockoff: **{ko}**")
            status = my_record.get("status","")
            st.markdown(f"**Status:** `{status}`")
        else:
            st.info("Not clocked in yet today.")
        st.markdown("---")

    # ── Clock actions ──
    st.markdown("#### ⏱️ Actions")

    if st.button("⏰ CLOCK IN", use_container_width=True):
        st.session_state.active_tab = "clockin"
    if st.button("☕ TEA START / END", use_container_width=True):
        st.session_state.active_tab = "tea"
    if st.button("🍽️ LUNCH START / END", use_container_width=True):
        st.session_state.active_tab = "lunch"
    if st.button("🚪 CLOCK OUT", use_container_width=True):
        st.session_state.active_tab = "clockout"

    st.markdown("---")

    # ── Role-based menu ──
    if role in ("supervisor", "admin"):
        st.markdown("#### 📊 Reports & Tools")
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.active_tab = "dashboard"
        if st.button("📋 Daily Report", use_container_width=True):
            st.session_state.active_tab = "daily_report"
        if st.button("📅 Weekly / Monthly", use_container_width=True):
            st.session_state.active_tab = "range_report"
        if st.button("🔍 Absent Today", use_container_width=True):
            st.session_state.active_tab = "absent"
        if st.button("📜 Agent History", use_container_width=True):
            st.session_state.active_tab = "history"
        if st.button("💾 Export to Excel", use_container_width=True):
            st.session_state.active_tab = "export"
        if st.button("📚 Manage Books", use_container_width=True):
            st.session_state.active_tab = "books"
        if st.button("🔑 Change Password", use_container_width=True):
            st.session_state.active_tab = "password"

    if role == "admin":
        st.markdown("#### ⚙️ Admin")
        if st.button("⚙️ Admin Panel", use_container_width=True):
            st.session_state.active_tab = "admin"

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        auth.logout()
        st.rerun()

# ── Main content area ──────────────────────────────────────────────────────
tab = st.session_state.active_tab

# ─────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────
if tab == "dashboard" and role in ("supervisor", "admin"):
    st.subheader("📊 Live Agent Dashboard")

   # Auto-refresh every 10 seconds
now_ts = time.time()

if now_ts - st.session_state.last_refresh >= 10:
    st.session_state.last_refresh = now_ts
    st.rerun()
    
    records = db.get_attendance_today()
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
        # Summary metrics
        total   = len(records)
        on_time = sum(1 for r in records if safe_int(r.get("late_minutes",0)) == 0)
        late    = sum(1 for r in records if safe_int(r.get("late_minutes",0)) > 0)
        on_break= sum(1 for r in records if r.get("status","") in ("Tea Break","Lunch Break"))
        clocked_out = sum(1 for r in records if r.get("status","") == "Clocked Out")

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Total Agents", total)
        c2.metric("On Time", on_time)
        c3.metric("Late", late, delta=f"-{late}" if late else None, delta_color="inverse")
        c4.metric("On Break", on_break)
        c5.metric("Clocked Out", clocked_out)

        st.markdown("---")

        # Overage alerts
        alerts = []
        for r in records:
            status = r.get("status","")
            if status == "Tea Break" and r.get("tea_start"):
                try:
                    elapsed = int((datetime.strptime(now_str(),"%H:%M") -
                                   datetime.strptime(r["tea_start"],"%H:%M")).total_seconds()/60)
                    if elapsed > TEA_LIMIT:
                        alerts.append(f"⚠️ {format_email(r['agent'])} — Tea break {elapsed-TEA_LIMIT} min over limit!")
                except: pass
            if status == "Lunch Break" and r.get("lunch_start"):
                try:
                    elapsed = int((datetime.strptime(now_str(),"%H:%M") -
                                   datetime.strptime(r["lunch_start"],"%H:%M")).total_seconds()/60)
                    if elapsed > LUNCH_LIMIT:
                        alerts.append(f"⚠️ {format_email(r['agent'])} — Lunch {elapsed-LUNCH_LIMIT} min over limit!")
                except: pass

        if alerts:
            for a in alerts:
                st.warning(a)

        # Book filter
        books_in_data = sorted(set(r.get("book","") or "—" for r in records))
        book_filter = st.selectbox("Filter by Book", ["All Books"] + books_in_data)

        # Build dataframe
        rows = []
        for r in records:
            if book_filter != "All Books" and (r.get("book","") or "—") != book_filter:
                continue
            tea_dur = ""
            if r.get("tea_start") and r.get("tea_end"):
                try:
                    tea_dur = int((datetime.strptime(r["tea_end"],"%H:%M") -
                                   datetime.strptime(r["tea_start"],"%H:%M")).total_seconds()/60)
                except: pass
            lunch_dur = ""
            if r.get("lunch_start") and r.get("lunch_end"):
                try:
                    lunch_dur = int((datetime.strptime(r["lunch_end"],"%H:%M") -
                                     datetime.strptime(r["lunch_start"],"%H:%M")).total_seconds()/60)
                except: pass
            rows.append({
                "Agent":       format_email(r["agent"]),
                "Book":        r.get("book","—") or "—",
                "Status":      r.get("status",""),
                "Clock In":    r.get("clock_in","") or "—",
                "Tea (min)":   tea_dur if tea_dur != "" else "—",
                "Lunch (min)": lunch_dur if lunch_dur != "" else "—",
                "Knockoff":    r.get("new_knockoff","") or "16:30",
                "Late (min)":  safe_int(r.get("late_minutes",0)),
                "Reason":      r.get("reason","") or "",
            })

        if rows:
            df = pd.DataFrame(rows)
            def color_status(val):
                colors = {
                    "Tea Break":   "background-color: #FFF3E0; color: #E65100",
                    "Lunch Break": "background-color: #E3F2FD; color: #1565C0",
                    "Clocked Out": "background-color: #E8F5E9; color: #1B5E20",
                    "Dialing":     "background-color: #F3F8FF; color: #1F3864",
                }
                return colors.get(val, "")
            styled = df.style.map(color_status, subset=["Status"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

        st.caption(f"🔄 Auto-refreshes every 60 seconds. Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ─────────────────────────────────────────────────────────────────────────
# CLOCK IN
# ─────────────────────────────────────────────────────────────────────────
elif tab == "clockin":
    st.subheader("⏰ Clock In")
    today_records = db.get_attendance_today()
    already_in = any(r["agent"] == username for r in today_records)

    if already_in:
        st.warning("You have already clocked in today.")
    else:
        clock_in_time = now_str()
        late_mins = calc_late_minutes(clock_in_time)

        if late_mins > 0:
            st.error(f"⚠️ You are {late_mins} minutes late. A reason is required.")
            reason = st.text_area("Reason for late arrival *", placeholder="e.g. Traffic, load shedding...")
        else:
            st.success(f"✅ On time! Clock in at **{clock_in_time}**")
            reason = ""

        # Book selection
        agent_books = db.get_agent_books(username)
        if agent_books:
            book = st.selectbox("Your Book", agent_books)
        else:
            book = st.text_input("Book (ask admin to assign you to a book)", value="Unassigned")

        if st.button("✅ Confirm Clock In", use_container_width=True, type="primary"):
            if late_mins > 0 and not reason.strip():
                st.error("Please provide a reason for your late arrival.")
            else:
                db.clock_in_agent(username, book, clock_in_time, late_mins, reason)
                st.success(f"Clocked in at {clock_in_time} ✅")
                time.sleep(1)
                st.session_state.active_tab = "dashboard" if role != "agent" else "clockin"
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# TEA BREAK
# ─────────────────────────────────────────────────────────────────────────
elif tab == "tea":
    st.subheader("☕ Tea Break")
    today_records = db.get_attendance_today()
    my_record = next((r for r in today_records if r["agent"] == username), None)

    if not my_record:
        st.error("You have not clocked in today. Please clock in first.")
    else:
        tea_start = my_record.get("tea_start","") or ""
        tea_end   = my_record.get("tea_end","")   or ""

        if not tea_start:
            st.info(f"Tea break limit: **{TEA_LIMIT} minutes**")
            if st.button("☕ Start Tea Break", use_container_width=True, type="primary"):
                db.update_field(username, "tea_start", now_str())
                db.update_field(username, "status", "Tea Break")
                st.success(f"Tea break started at {now_str()}")
                time.sleep(1); st.rerun()
        elif not tea_end:
            try:
                elapsed = int((datetime.strptime(now_str(),"%H:%M") -
                               datetime.strptime(tea_start,"%H:%M")).total_seconds()/60)
            except: elapsed = 0
            over = max(0, elapsed - TEA_LIMIT)
            st.info(f"Tea started: **{tea_start}** | Elapsed: **{elapsed} min**")
            if over > 0:
                st.warning(f"⚠️ You are {over} minute(s) over the {TEA_LIMIT}-minute limit!")
                reason = st.text_area("Reason for overage *")
            else:
                reason = ""
                st.success(f"✅ Within limit ({TEA_LIMIT - elapsed} min remaining)")

            if st.button("✅ End Tea Break", use_container_width=True, type="primary"):
                if over > 0 and not reason.strip():
                    st.error("Please provide a reason for the overage.")
                else:
                    db.update_field(username, "tea_end", now_str())
                    db.update_field(username, "status", "Dialing")
                    if over > 0:
                        db.update_field(username, "tea_extra", over)
                        db.update_field(username, "reason", reason)
                    st.success("Tea break ended ✅")
                    time.sleep(1); st.rerun()
        else:
            dur = int((datetime.strptime(tea_end,"%H:%M") -
                       datetime.strptime(tea_start,"%H:%M")).total_seconds()/60)
            st.success(f"Tea break completed: {tea_start} → {tea_end} ({dur} min)")

# ─────────────────────────────────────────────────────────────────────────
# LUNCH BREAK
# ─────────────────────────────────────────────────────────────────────────
elif tab == "lunch":
    st.subheader("🍽️ Lunch Break")
    today_records = db.get_attendance_today()
    my_record = next((r for r in today_records if r["agent"] == username), None)

    if not my_record:
        st.error("You have not clocked in today. Please clock in first.")
    else:
        lunch_start = my_record.get("lunch_start","") or ""
        lunch_end   = my_record.get("lunch_end","")   or ""

        if not lunch_start:
            st.info(f"Lunch break limit: **{LUNCH_LIMIT} minutes**")
            if st.button("🍽️ Start Lunch Break", use_container_width=True, type="primary"):
                db.update_field(username, "lunch_start", now_str())
                db.update_field(username, "status", "Lunch Break")
                st.success(f"Lunch started at {now_str()}")
                time.sleep(1); st.rerun()
        elif not lunch_end:
            try:
                elapsed = int((datetime.strptime(now_str(),"%H:%M") -
                               datetime.strptime(lunch_start,"%H:%M")).total_seconds()/60)
            except: elapsed = 0
            over = max(0, elapsed - LUNCH_LIMIT)
            st.info(f"Lunch started: **{lunch_start}** | Elapsed: **{elapsed} min**")
            if over > 0:
                st.warning(f"⚠️ You are {over} minute(s) over the {LUNCH_LIMIT}-minute limit!")
                reason = st.text_area("Reason for overage *")
            else:
                reason = ""
                st.success(f"✅ Within limit ({LUNCH_LIMIT - elapsed} min remaining)")

            if st.button("✅ End Lunch Break", use_container_width=True, type="primary"):
                if over > 0 and not reason.strip():
                    st.error("Please provide a reason for the overage.")
                else:
                    db.update_field(username, "lunch_end", now_str())
                    db.update_field(username, "status", "Dialing")
                    if over > 0:
                        db.update_field(username, "lunch_extra", over)
                        if reason: db.update_field(username, "reason", reason)
                    st.success("Lunch break ended ✅")
                    time.sleep(1); st.rerun()
        else:
            dur = int((datetime.strptime(lunch_end,"%H:%M") -
                       datetime.strptime(lunch_start,"%H:%M")).total_seconds()/60)
            st.success(f"Lunch completed: {lunch_start} → {lunch_end} ({dur} min)")

# ─────────────────────────────────────────────────────────────────────────
# CLOCK OUT
# ─────────────────────────────────────────────────────────────────────────
elif tab == "clockout":
    st.subheader("🚪 Clock Out")
    today_records = db.get_attendance_today()
    my_record = next((r for r in today_records if r["agent"] == username), None)

    if not my_record:
        st.error("You have not clocked in today.")
    elif my_record.get("clock_out"):
        st.success(f"You already clocked out at **{my_record['clock_out']}**.")
    else:
        clock_out_time = now_str()
        late_mins  = safe_int(my_record.get("late_minutes",0))
        tea_extra  = safe_int(my_record.get("tea_extra",0))

        lunch_extra = safe_int(my_record.get("lunch_extra",0))
        if my_record.get("lunch_start") and not my_record.get("lunch_end"):
            try:
                lunch_mins = int((datetime.strptime(clock_out_time,"%H:%M") -
                                  datetime.strptime(my_record["lunch_start"],"%H:%M")).total_seconds()/60)
                lunch_extra = max(0, lunch_mins - LUNCH_LIMIT)
            except: pass

        total_extra  = late_mins + tea_extra + lunch_extra
        new_knockoff = calc_new_knockoff(late_mins, tea_extra, lunch_extra)

        st.markdown("### 📋 Clock Out Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Clock In",     my_record.get("clock_in","—"))
            st.metric("Tea Extra",    f"{tea_extra} min")
            st.metric("Total Extra",  f"{total_extra} min")
        with col2:
            st.metric("Clock Out",    clock_out_time)
            st.metric("Lunch Extra",  f"{lunch_extra} min")
            st.metric("New Knockoff", new_knockoff)

        if late_mins > 0:
            st.error(f"⚠️ Late arrival: {late_mins} minutes")
        if total_extra == 0:
            st.success("✅ No penalties — standard knockoff at 16:30")

        if st.button("✅ Confirm Clock Out", use_container_width=True, type="primary"):
            db.clock_out_agent(username, clock_out_time, late_mins,
                               tea_extra, lunch_extra, new_knockoff)
            st.success("Clocked out successfully! Goodbye 👋")
            time.sleep(1.5)
            auth.logout()
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# DAILY REPORT
# ─────────────────────────────────────────────────────────────────────────
elif tab == "daily_report" and role in ("supervisor","admin"):
    st.subheader("📊 Daily Attendance Report")
    records = db.get_attendance_today()

    if role == "supervisor":
        sup_books = db.get_supervisor_books(username)
        allowed = set()
        for bd in sup_books.values(): allowed.update(bd.get("agents",[]))
        records = [r for r in records if r["agent"] in allowed]

    if not records:
        st.info("No records for today yet.")
    else:
        rows = []
        for r in records:
            tea_dur = ""
            if r.get("tea_start") and r.get("tea_end"):
                try: tea_dur = int((datetime.strptime(r["tea_end"],"%H:%M")-datetime.strptime(r["tea_start"],"%H:%M")).total_seconds()/60)
                except: pass
            lunch_dur = ""
            if r.get("lunch_start") and r.get("lunch_end"):
                try: lunch_dur = int((datetime.strptime(r["lunch_end"],"%H:%M")-datetime.strptime(r["lunch_start"],"%H:%M")).total_seconds()/60)
                except: pass
            rows.append({
                "Agent":       format_email(r["agent"]),
                "Book":        r.get("book","—") or "—",
                "Status":      r.get("status",""),
                "Clock In":    r.get("clock_in","") or "—",
                "Clock Out":   r.get("clock_out","") or "—",
                "Tea (min)":   tea_dur if tea_dur != "" else "—",
                "Lunch (min)": lunch_dur if lunch_dur != "" else "—",
                "Late (min)":  safe_int(r.get("late_minutes",0)),
                "Tea Extra":   safe_int(r.get("tea_extra",0)),
                "Lunch Extra": safe_int(r.get("lunch_extra",0)),
                "Knockoff":    r.get("new_knockoff","") or "16:30",
                "Reason":      r.get("reason","") or "",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        total = len(df)
        late_count = len(df[df["Late (min)"] > 0])
        st.markdown(f"**Total:** {total} &nbsp;|&nbsp; **On Time:** {total-late_count} &nbsp;|&nbsp; **Late:** {late_count}")

# ─────────────────────────────────────────────────────────────────────────
# RANGE REPORT (Weekly / Monthly)
# ─────────────────────────────────────────────────────────────────────────
elif tab == "range_report" and role in ("supervisor","admin"):
    st.subheader("📅 Weekly / Monthly Report")
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("From", value=datetime.today().replace(day=1))
    with col2:
        end = st.date_input("To", value=datetime.today())

    if st.button("Generate Report", type="primary"):
        records = db.get_attendance_range(str(start), str(end))
        if role == "supervisor":
            sup_books = db.get_supervisor_books(username)
            allowed = set()
            for bd in sup_books.values(): allowed.update(bd.get("agents",[]))
            records = [r for r in records if r["agent"] in allowed]

        if not records:
            st.info("No records found for selected range.")
        else:
            df = pd.DataFrame(records)
            summary = df.groupby("agent").agg(
                Days_Present   = ("date","nunique"),
                Total_Late_Min = ("late_minutes","sum"),
                Total_Tea_Extra= ("tea_extra","sum"),
                Total_Lunch_Extra=("lunch_extra","sum"),
            ).reset_index()
            summary["agent"] = summary["agent"].apply(format_email)
            summary.columns = ["Agent","Days Present","Total Late (min)","Tea Extra (min)","Lunch Extra (min)"]
            st.dataframe(summary, use_container_width=True, hide_index=True)

            # Excel download
            import io
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                summary.to_excel(writer, index=False, sheet_name="Summary")
                df.to_excel(writer, index=False, sheet_name="Raw Data")
            st.download_button("📥 Download Excel", buf.getvalue(),
                file_name=f"NICS_Report_{start}_{end}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ─────────────────────────────────────────────────────────────────────────
# ABSENT TODAY
# ─────────────────────────────────────────────────────────────────────────
elif tab == "absent" and role in ("supervisor","admin"):
    st.subheader("🔍 Absent Today")
    all_agents = db.get_agent_usernames()
    today_records = db.get_attendance_today()
    clocked_in = {r["agent"] for r in today_records}

    if role == "supervisor":
        sup_books = db.get_supervisor_books(username)
        allowed = set()
        for bd in sup_books.values(): allowed.update(bd.get("agents",[]))
        all_agents = [a for a in all_agents if a in allowed]

    absent = [a for a in all_agents if a not in clocked_in]

    if not absent:
        st.success("✅ All agents have clocked in today!")
    else:
        st.warning(f"⚠️ {len(absent)} agent(s) have not clocked in today:")
        for a in sorted(absent):
            st.markdown(f"- 📧 {format_email(a)}")

# ─────────────────────────────────────────────────────────────────────────
# AGENT HISTORY
# ─────────────────────────────────────────────────────────────────────────
elif tab == "history" and role in ("supervisor","admin"):
    st.subheader("📜 Agent History")
    all_agents = db.get_agent_usernames()

    if role == "supervisor":
        sup_books = db.get_supervisor_books(username)
        allowed = set()
        for bd in sup_books.values(): allowed.update(bd.get("agents",[]))
        all_agents = [a for a in all_agents if a in allowed]

    selected = st.selectbox("Select Agent", [format_email(a) for a in sorted(all_agents)])
    sel_username = selected.split("@")[0]

    records = db.get_attendance_all()
    agent_records = [r for r in records if r["agent"] == sel_username]

    if not agent_records:
        st.info("No records found for this agent.")
    else:
        df = pd.DataFrame(agent_records)
        cols = ["date","book","clock_in","clock_out","late_minutes","tea_extra","lunch_extra","new_knockoff","status","reason"]
        cols = [c for c in cols if c in df.columns]
        df = df[cols]
        df.columns = [c.replace("_"," ").title() for c in df.columns]
        st.dataframe(df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────
# EXPORT TO EXCEL
# ─────────────────────────────────────────────────────────────────────────
elif tab == "export" and role in ("supervisor","admin"):
    st.subheader("💾 Export Attendance")
    col1, col2 = st.columns(2)
    with col1: start = st.date_input("From", value=datetime.today())
    with col2: end   = st.date_input("To",   value=datetime.today())

    if st.button("Generate Export", type="primary"):
        records = db.get_attendance_range(str(start), str(end))
        if role == "supervisor":
            sup_books = db.get_supervisor_books(username)
            allowed = set()
            for bd in sup_books.values(): allowed.update(bd.get("agents",[]))
            records = [r for r in records if r["agent"] in allowed]

        if not records:
            st.info("No data found for selected range.")
        else:
            import io
            df = pd.DataFrame(records)
            buf = io.BytesIO()
            df.to_excel(buf, index=False, engine="openpyxl")
            st.download_button("📥 Download Excel", buf.getvalue(),
                file_name=f"NICS_Attendance_{start}_{end}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.success(f"✅ {len(records)} records ready for download.")

# ─────────────────────────────────────────────────────────────────────────
# MANAGE BOOKS
# ─────────────────────────────────────────────────────────────────────────
elif tab == "books" and role in ("supervisor","admin"):
    st.subheader("📚 Manage Books")
    books = db.get_books()
    all_agents = db.get_agent_usernames()

    if role == "supervisor":
        books = db.get_supervisor_books(username)

    book_names = list(books.keys())

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("#### Books")
        if book_names:
            selected_book = st.radio("Select a book", book_names, label_visibility="collapsed")
        else:
            selected_book = None
            st.info("No books yet.")

        if role == "admin":
            st.markdown("---")
            new_book = st.text_input("New book name")
            if st.button("➕ Create Book") and new_book.strip():
                if new_book.strip() not in books:
                    db.upsert_book(new_book.strip(), [], [])
                    st.success(f"Book '{new_book}' created.")
                    time.sleep(0.5); st.rerun()
                else:
                    st.warning("Book already exists.")
            if selected_book and st.button("🗑️ Delete Book", type="secondary"):
                db.delete_book(selected_book)
                st.success(f"Book '{selected_book}' deleted.")
                time.sleep(0.5); st.rerun()

    with col_right:
        if selected_book and selected_book in books:
            bdata = books[selected_book]
            st.markdown(f"#### {selected_book}")

            # Agents in this book
            book_agents = bdata.get("agents", [])
            st.markdown(f"**Agents ({len(book_agents)}):**")
            if book_agents:
                remove_agent_sel = st.selectbox("Select agent to remove",
                    [format_email(a) for a in sorted(book_agents)], key="rem_ag")
                if st.button("🗑️ Remove Agent from Book"):
                    rem_u = remove_agent_sel.split("@")[0]
                    updated = [a for a in book_agents if a != rem_u]
                    db.upsert_book(selected_book,
                        bdata.get("supervisors",[]), updated)
                    st.success(f"Removed {rem_u} from {selected_book}")
                    time.sleep(0.5); st.rerun()
            else:
                st.info("No agents in this book yet.")

            st.markdown("---")
            not_in_book = [a for a in all_agents if a not in book_agents]
            if not_in_book:
                add_agent_sel = st.selectbox("Add agent to book",
                    [format_email(a) for a in sorted(not_in_book)], key="add_ag")
                if st.button("➕ Add Agent to Book", type="primary"):
                    add_u = add_agent_sel.split("@")[0]
                    updated = book_agents + [add_u]
                    db.upsert_book(selected_book, bdata.get("supervisors",[]), updated)
                    st.success(f"Added {add_u} to {selected_book}")
                    time.sleep(0.5); st.rerun()

            # Supervisors (admin only)
            if role == "admin":
                st.markdown("---")
                st.markdown("**Assigned Supervisors:**")
                book_sups = bdata.get("supervisors", [])
                all_sups = list(auth.SUPERVISORS)
                if book_sups:
                    rem_sup = st.selectbox("Remove supervisor",
                        [format_email(s) for s in book_sups], key="rem_sup")
                    if st.button("🗑️ Remove Supervisor"):
                        rem_u = rem_sup.split("@")[0]
                        db.upsert_book(selected_book,
                            [s for s in book_sups if s != rem_u], book_agents)
                        st.rerun()
                not_assigned = [s for s in all_sups if s not in book_sups]
                if not_assigned:
                    add_sup = st.selectbox("Assign supervisor",
                        [format_email(s) for s in not_assigned], key="add_sup")
                    if st.button("➕ Assign Supervisor", type="primary"):
                        add_u = add_sup.split("@")[0]
                        db.upsert_book(selected_book, book_sups + [add_u], book_agents)
                        st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────────────────────────────────
elif tab == "password" and role in ("supervisor","admin"):
    st.subheader("🔑 Change Password")
    if role == "admin":
        pw_type = st.selectbox("Change password for", ["Admin", "Supervisor"])
    else:
        pw_type = "Supervisor"

    with st.form("pw_form"):
        new_pw  = st.text_input("New Password", type="password")
        conf_pw = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Update Password", type="primary")

    if submitted:
        if not new_pw:
            st.error("Password cannot be empty.")
        elif new_pw != conf_pw:
            st.error("Passwords do not match.")
        else:
            key = "admin_password" if pw_type == "Admin" else "supervisor_password"
            db.set_setting(key, new_pw)
            st.success(f"✅ {pw_type} password updated successfully.")

# ─────────────────────────────────────────────────────────────────────────
# ADMIN PANEL
# ─────────────────────────────────────────────────────────────────────────
elif tab == "admin" and role == "admin":
    st.subheader("⚙️ Admin Panel — Manage Agents")
    agents = db.get_agents()

    col1, col2 = st.columns([1.5, 2])

    with col1:
        st.markdown("#### Add New Agent")
        with st.form("add_agent_form"):
            full_name = st.text_input("Full Name", placeholder="e.g. Nokwanda Ntuli")
            new_uname = st.text_input("Username", placeholder="e.g. nokwandan")
            add_submitted = st.form_submit_button("➕ Add Agent", type="primary")

        if add_submitted:
            uname = new_uname.strip().replace("@nics.co.za","")
            if not uname or not full_name.strip():
                st.error("Full name and username are required.")
            elif uname in [a["username"] for a in agents]:
                st.warning(f"'{uname}' already exists.")
            else:
                db.add_agent(uname, full_name.strip())
                st.success(f"✅ {full_name} ({format_email(uname)}) added!\nAssign to a book via 📚 Manage Books.")
                time.sleep(1); st.rerun()

    with col2:
        st.markdown("#### Registered Agents")
        if agents:
            df_agents = pd.DataFrame([{
                "#": i+1,
                "Username": format_email(a["username"]),
                "Full Name": a.get("display_name",""),
            } for i, a in enumerate(agents)])
            st.dataframe(df_agents, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### Remove Agent")
            remove_sel = st.selectbox("Select agent to remove",
                [format_email(a["username"]) for a in agents])
            if st.button("🗑️ Remove Agent", type="secondary"):
                rem_u = remove_sel.split("@")[0]
                if rem_u in auth.ADMINS:
                    st.error("Cannot remove admin accounts.")
                else:
                    db.remove_agent(rem_u)
                    st.success(f"{remove_sel} removed.")
                    time.sleep(0.5); st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# DEFAULT — show dashboard for supervisor/admin, actions for agent
# ─────────────────────────────────────────────────────────────────────────
elif tab not in ("clockin","tea","lunch","clockout","dashboard","daily_report",
                 "range_report","absent","history","export","books","password","admin"):
    if role == "agent":
        st.info("👈 Use the sidebar to Clock In, manage breaks, or Clock Out.")
    else:
        st.session_state.active_tab = "dashboard"
        st.rerun()
