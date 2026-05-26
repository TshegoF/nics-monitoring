"""
app.py — NICS Employee Time Monitoring System v2
New: Reception, Bathroom, Meeting, Working Hours, PIN security,
     Dropdown reasons, Supervisor status, Edit books, Admin-only password
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import auth
import database as db
from utils import (
    calc_late_minutes, calc_new_knockoff, calc_worked_minutes,
    format_email, safe_int,
    TEA_LIMIT, LUNCH_LIMIT, BATHROOM_LIMIT, MEETING_LIMIT, REQUIRED_HOURS,
    LATE_REASONS, TEA_REASONS, LUNCH_REASONS, BATHROOM_REASONS, RECEPTION_REASONS
)

SAST = timezone(timedelta(hours=2))
def now_sast():  return datetime.now(SAST)
def now_str():   return now_sast().strftime("%H:%M")
def today_str(): return now_sast().strftime("%Y-%m-%d")

def append_reason(existing, prefix, new_text):
    part = f"{prefix}: {new_text.strip()}"
    if existing and existing.strip():
        return f"{existing.strip()} | {part}"
    return part

def parse_reasons(reason_str):
    out = {"Late Reason": "", "Tea Reason": "", "Lunch Reason": "",
           "Bathroom Reason": "", "Reception Reason": ""}
    if not reason_str:
        return out
    for chunk in str(reason_str).split("|"):
        chunk = chunk.strip()
        for prefix, key in [("Late: ","Late Reason"),("Tea: ","Tea Reason"),
                             ("Lunch: ","Lunch Reason"),("Bathroom: ","Bathroom Reason"),
                             ("Reception: ","Reception Reason")]:
            if chunk.startswith(prefix):
                out[key] = chunk[len(prefix):]
    return out

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(page_title="NICS Time Monitoring", page_icon="🕐",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
#MainMenu,header,footer,[data-testid="stToolbar"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none!important}
.main-header{background:linear-gradient(135deg,#1F3864,#2E75B6);
  padding:1.2rem 2rem;border-radius:10px;color:white;text-align:center;
  margin-bottom:1.2rem;box-shadow:0 4px 12px rgba(0,0,0,0.15)}
.main-header h1,.main-header p{color:white!important}
.main-header h1{margin:0;font-size:1.6rem;font-weight:700}
.main-header p{margin:.3rem 0 0;font-size:.9rem;opacity:.9}
.cbox{border-radius:12px;padding:2rem;text-align:center;margin:1rem 0}
.cbox-blue{background:linear-gradient(135deg,#1F3864,#2E75B6)}
.cbox-red{background:linear-gradient(135deg,#C00000,#E53935)}
.cbox-orange{background:linear-gradient(135deg,#E65100,#FF6D00)}
.cbox-purple{background:linear-gradient(135deg,#4A148C,#7B1FA2)}
.cbox .digits{font-size:4rem;font-weight:700;font-family:monospace;
  letter-spacing:4px;color:white}
.cbox .lbl{font-size:1rem;color:rgba(255,255,255,0.9);margin-top:.5rem}
.badge{display:inline-block;padding:3px 10px;border-radius:4px;
  font-weight:700;font-size:.85rem;letter-spacing:.3px}
.badge-dial    {background:#2e7d32;color:#fff}
.badge-tea     {background:#e65100;color:#fff}
.badge-lunch   {background:#1565C0;color:#fff}
.badge-out     {background:#424242;color:#fff}
.badge-bath    {background:#6A1B9A;color:#fff}
.badge-meet    {background:#1565C0;color:#fff}
.badge-recep   {background:#00695C;color:#fff}
.badge-onduty  {background:#1B5E20;color:#fff}
.badge-offduty {background:#B71C1C;color:#fff}
div[data-testid="stButton"] button{border-radius:6px;font-weight:600}
</style>""", unsafe_allow_html=True)

for k, v in [("user",None),("active_tab","dashboard"),("dark_mode",False)]:
    if k not in st.session_state: st.session_state[k] = v

if st.session_state.dark_mode:
    st.markdown("""<style>.stApp{background:#1a1a2e!important}
    section[data-testid="stSidebar"]{background:#0f0f23!important}
    section[data-testid="stSidebar"] *{color:#e0e0e0!important}</style>""",
    unsafe_allow_html=True)
else:
    st.markdown("""<style>
    section[data-testid="stSidebar"]{background:#1F3864!important}
    section[data-testid="stSidebar"] *{color:#fff!important}
    section[data-testid="stSidebar"] .stButton button{
      background:rgba(255,255,255,0.15)!important;color:white!important;
      border:1px solid rgba(255,255,255,0.3)!important;border-radius:6px;width:100%}
    section[data-testid="stSidebar"] .stButton button:hover{
      background:rgba(255,255,255,0.3)!important}
    </style>""", unsafe_allow_html=True)

_t = now_sast()
st.markdown(f"""<div class="main-header">
<h1>🕐 EMPLOYEE TIME MONITORING SYSTEM — NICS</h1>
<p>NICS Call Centre &nbsp;|&nbsp; Work: 08:00–16:30 &nbsp;|&nbsp;
Tea: 15 min &nbsp;|&nbsp; Lunch: 60 min &nbsp;|&nbsp;
🇿🇦 {_t.strftime('%A, %d %B %Y')} &nbsp;<strong>{_t.strftime('%H:%M:%S')}</strong> SAST</p>
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════
if not auth.is_logged_in():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("### 🔐 Login")
        with st.form("login_form", clear_on_submit=False):
            uname = st.text_input("Username", placeholder="e.g. cyounis")
            pwd   = st.text_input("Password", type="password",
                                  placeholder="Supervisors & Admin only")
            pin   = st.text_input("PIN", type="password",
                                  placeholder="4-digit PIN (agents & receptionists)")
            if st.form_submit_button("Login", use_container_width=True):
                if not uname.strip():
                    st.error("Please enter your username.")
                else:
                    u = auth.try_login(uname.strip(), pwd.strip(), pin.strip())
                    if u:
                        st.session_state.user = u
                        r = u["role"]
                        st.session_state.active_tab = (
                            "clockin" if r in ("agent","receptionist") else "dashboard")
                        st.rerun()
                    else:
                        st.error("Invalid credentials or incorrect PIN.")
        st.caption("💡 Agents & Receptionists: enter username + your 4-digit PIN.")
        st.caption("💡 Supervisors & Admin: enter username + password.")
    st.stop()

user     = auth.current_user()
role     = auth.current_role()
username = auth.current_username()
tab      = st.session_state.active_tab

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"**👤 {format_email(username)}**")
    st.caption(f"Role: {role.title()}")

    # ── Self-view for agents & receptionists ──
    if role in ("agent", "receptionist"):
        st.markdown("---")
        st.markdown("#### 📋 My Status Today")
        _recs = db.get_attendance_today(today_str())
        _me   = next((r for r in _recs if r["agent"] == username), None)
        if _me:
            st.success(f"🕐 In: **{_me.get('clock_in','—')}**")
            for icon, s, e, lbl in [
                ("☕", "tea_start",       "tea_end",       "Tea"),
                ("🍽️","lunch_start",     "lunch_end",     "Lunch"),
                ("🚻","bathroom_start",  "bathroom_end",  "Bathroom"),
                ("📋","reception_start", "reception_end", "Reception"),
                ("🤝","meeting_start",   "meeting_end",   "Meeting"),
            ]:
                sv = _me.get(s,"") or ""
                ev = _me.get(e,"") or ""
                if sv:
                    st.info(f"{icon} {lbl}: {sv} → {ev or 'ongoing'}")
            st.warning(f"🚪 Knockoff: **{_me.get('new_knockoff','') or '16:30'}**")
            _sv  = _me.get("status","") or "Dialing"
            _cls = {
                "Dialing":    "badge badge-dial",
                "Tea Break":  "badge badge-tea",
                "Lunch Break":"badge badge-lunch",
                "Bathroom":   "badge badge-bath",
                "Meeting":    "badge badge-meet",
                "Reception":  "badge badge-recep",
                "Clocked Out":"badge badge-out",
            }.get(_sv, "badge badge-dial")
            st.markdown(f"**Status:** <span class='{_cls}'>{_sv}</span>",
                        unsafe_allow_html=True)
        else:
            st.info("Not clocked in yet.")

    st.markdown("---")
    st.markdown("#### ⏱️ Actions")
    for _lbl, _key in [
        ("⏰ Clock In",       "clockin"),
        ("☕ Tea Break",      "tea"),
        ("🍽️ Lunch Break",   "lunch"),
        ("🚻 Bathroom",       "bathroom"),
        ("📋 Reception",      "reception"),
        ("🤝 Meeting",        "meeting"),
        ("🚪 Clock Out",      "clockout"),
    ]:
        if st.button(_lbl, use_container_width=True, key=f"sb_{_key}"):
            st.session_state.active_tab = _key; st.rerun()

    if role in ("supervisor","admin","receptionist"):
        st.markdown("---"); st.markdown("#### 📊 Reports & Tools")
        report_items = [
            ("📊 Dashboard",       "dashboard"),
            ("📋 Daily Report",    "daily_report"),
            ("📅 Weekly/Monthly",  "range_report"),
            ("🔍 Absent Today",    "absent"),
            ("📜 Agent History",   "history"),
            ("💾 Export to Excel", "export"),
        ]
        # Receptionist only sees dashboard
        if role == "receptionist":
            report_items = [("📊 Dashboard","dashboard")]
        for _lbl, _key in report_items:
            if st.button(_lbl, use_container_width=True, key=f"sb_{_key}"):
                st.session_state.active_tab = _key; st.rerun()

    if role in ("supervisor","admin"):
        if role == "admin":
            for _lbl, _key in [
                ("📚 Manage Books",    "books"),
                ("🔑 Change Password", "password"),
                ("⚙️ Admin Panel",     "admin"),
            ]:
                if st.button(_lbl, use_container_width=True, key=f"sb_{_key}"):
                    st.session_state.active_tab = _key; st.rerun()
        else:
            # Supervisor: books only (no password, no admin)
            if st.button("📚 Manage Books", use_container_width=True, key="sb_books"):
                st.session_state.active_tab = "books"; st.rerun()

    st.markdown("---")
    if st.button("☀️ Light Mode" if st.session_state.dark_mode else "🌙 Dark Mode",
                 use_container_width=True, key="sb_dm"):
        st.session_state.dark_mode = not st.session_state.dark_mode; st.rerun()
    if st.button("🚪 Logout", use_container_width=True, key="sb_logout"):
        auth.logout(); st.rerun()

# ── Live clock ────────────────────────────────────────────────
@st.fragment(run_every=1)
def live_clock():
    n = now_sast()
    st.caption(f"🇿🇦 **{n.strftime('%H:%M:%S')} SAST** — {n.strftime('%A, %d %B %Y')}")
live_clock()

# ── Status colour map for dashboard ──────────────────────────
SC = {
    "Tea Break":   "background-color:#FFF3E0;color:#E65100;font-weight:bold",
    "Lunch Break": "background-color:#E3F2FD;color:#1565C0;font-weight:bold",
    "Clocked Out": "background-color:#EEEEEE;color:#212121;font-weight:bold",
    "Dialing":     "background-color:#E8F5E9;color:#1B5E20;font-weight:bold",
    "Bathroom":    "background-color:#F3E5F5;color:#6A1B9A;font-weight:bold",
    "Meeting":     "background-color:#E3F2FD;color:#0D47A1;font-weight:bold",
    "Reception":   "background-color:#E0F2F1;color:#00695C;font-weight:bold",
    "On Duty":     "background-color:#E8F5E9;color:#1B5E20;font-weight:bold",
    "Off Duty":    "background-color:#FFEBEE;color:#B71C1C;font-weight:bold",
}

def dur(s, e):
    try:
        return str(int((datetime.strptime(e,"%H:%M") -
                        datetime.strptime(s,"%H:%M")).total_seconds()/60))+"m"
    except: return "—"

# ═══════════════════════════════════════════════════════════════
# COUNTDOWN FRAGMENT FACTORY
# ═══════════════════════════════════════════════════════════════
def make_countdown_fragment(frag_key, start_field, end_field, extra_field,
                            status_name, limit_minutes, color_class,
                            start_label, end_label, reasons_list,
                            reason_prefix, icon):
    @st.fragment(run_every=1)
    def countdown_frag(username, today_s):
        recs = db.get_attendance_today(today_s)
        me   = next((r for r in recs if r["agent"] == username), None)
        if not me:
            st.error("Clock in first."); return

        sv = me.get(start_field,"") or ""
        ev = me.get(end_field,"")   or ""

        if not sv:
            st.info(f"{icon} Time limit: **{limit_minutes} minutes**")
            if st.button(f"{icon} {start_label}", use_container_width=True,
                         type="primary", key=f"start_{frag_key}"):
                s = now_str()
                db.update_field(username, start_field, s,           today_s)
                db.update_field(username, "status",    status_name, today_s)
                st.rerun(scope="app")

        elif not ev:
            try:
                start_dt  = datetime.strptime(f"{today_s} {sv}","%Y-%m-%d %H:%M").replace(tzinfo=SAST)
                elapsed   = int((now_sast()-start_dt).total_seconds())
                remaining = limit_minutes*60 - elapsed
                rem_m, rem_s = divmod(abs(remaining),60)
                is_over   = remaining < 0

                css = f"cbox-red" if is_over else color_class
                prefix = "+" if is_over else ""
                lbl = f"⚠️ OVER the {limit_minutes}-minute limit!" if is_over else f"{icon} Counting down from {limit_minutes:02d}:00"
                st.markdown(f"""<div class="cbox {css}">
                <div class="digits">{prefix}{rem_m:02d}:{rem_s:02d}</div>
                <div class="lbl">{lbl}</div></div>""", unsafe_allow_html=True)
                st.caption(f"{icon} Started: **{sv} SAST** | Limit: {limit_minutes} min")

                reason = ""
                if is_over:
                    reason = st.selectbox("Reason for overage *", reasons_list,
                                          key=f"{frag_key}_reason_sel")
                else:
                    st.info(f"Press {end_label} when you return.")

                if st.button(f"✅ {end_label}", use_container_width=True,
                             type="primary", key=f"end_{frag_key}"):
                    if is_over and (not reason or reason.startswith("--")):
                        st.error("Please select a reason for the overage.")
                    else:
                        et = now_str()
                        db.update_field(username, end_field,    et,        today_s)
                        db.update_field(username, "status",     "Dialing", today_s)
                        if is_over:
                            om = max(1, int(abs(remaining)/60))
                            db.update_field(username, extra_field, om, today_s)
                            existing = me.get("reason","") or ""
                            db.update_field(username,"reason",
                                append_reason(existing,reason_prefix,reason),today_s)
                        st.success(f"✅ Ended at {et} SAST")
                        st.rerun(scope="app")
            except Exception as e:
                st.error(f"Timer error: {e}")
        else:
            d = dur(sv, ev)
            st.success(f"✅ Completed: {sv} → {ev} ({d})")

    return countdown_frag

# Create fragment instances
tea_fragment      = make_countdown_fragment("tea","tea_start","tea_end","tea_extra",
    "Tea Break",   TEA_LIMIT,     "cbox-blue",  "Start Tea Break",  "End Tea Break",
    TEA_REASONS,   "Tea",         "☕")
lunch_fragment    = make_countdown_fragment("lunch","lunch_start","lunch_end","lunch_extra",
    "Lunch Break", LUNCH_LIMIT,   "cbox-blue",  "Start Lunch Break","End Lunch Break",
    LUNCH_REASONS, "Lunch",       "🍽️")
bathroom_fragment = make_countdown_fragment("bathroom","bathroom_start","bathroom_end","bathroom_extra",
    "Bathroom",    BATHROOM_LIMIT,"cbox-purple","Go to Bathroom",   "Return from Bathroom",
    BATHROOM_REASONS,"Bathroom",  "🚻")
meeting_fragment  = make_countdown_fragment("meeting","meeting_start","meeting_end","meeting_extra",
    "Meeting",     MEETING_LIMIT, "cbox-orange","Start Meeting",    "End Meeting",
    ["-- Select a reason --","Team meeting","Client call","Training session",
     "Management briefing","Performance review","Other"],
    "Meeting","🤝")

# ═══════════════════════════════════════════════════════════════
# DASHBOARD FRAGMENT
# ═══════════════════════════════════════════════════════════════
@st.fragment(run_every=10)
def dashboard_fragment(role, username):
    records = db.get_attendance_today(today_str())
    if role == "supervisor":
        allowed = set()
        for bd in db.get_supervisor_books(username).values():
            allowed.update(bd.get("agents",[]))
        records = [r for r in records if r["agent"] in allowed]

    # Receptionist sees all agents but NO reasons
    show_reasons = role in ("admin","supervisor")

    st.subheader("📊 Live Agent Dashboard")
    st.caption(f"🔄 Auto-refreshes every 10 s | 🇿🇦 {now_sast().strftime('%H:%M:%S')} SAST")

    if not records:
        st.info("No agents have clocked in today yet."); return

    total    = len(records)
    on_time  = sum(1 for r in records if safe_int(r.get("late_minutes",0))==0)
    late_cnt = sum(1 for r in records if safe_int(r.get("late_minutes",0))>0)
    on_brk   = sum(1 for r in records if r.get("status","") in
                   ("Tea Break","Lunch Break","Bathroom","Meeting","Reception"))
    co       = sum(1 for r in records if r.get("status","")=="Clocked Out")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total",total); c2.metric("On Time",on_time); c3.metric("Late",late_cnt)
    c4.metric("On Break",on_brk); c5.metric("Clocked Out",co)
    st.markdown("---")

    cur = now_str()
    for r in records:
        s = r.get("status","")
        for sname, sfield, limit in [
            ("Tea Break","tea_start",TEA_LIMIT),
            ("Lunch Break","lunch_start",LUNCH_LIMIT),
            ("Bathroom","bathroom_start",BATHROOM_LIMIT),
        ]:
            if s == sname and r.get(sfield):
                try:
                    el = int((datetime.strptime(cur,"%H:%M") -
                              datetime.strptime(r[sfield],"%H:%M")).total_seconds()/60)
                    if el > limit:
                        st.warning(f"⚠️ {format_email(r['agent'])} — {sname} {el-limit} min OVER!")
                except: pass

    books_list = sorted(set(r.get("book","") or "—" for r in records))
    bf = st.selectbox("Filter by Book",["All Books"]+books_list,key="dash_bf")

    rows = []
    for r in records:
        if bf != "All Books" and (r.get("book","") or "—") != bf: continue
        pr = parse_reasons(r.get("reason",""))
        row = {
            "Agent":      format_email(r["agent"]),
            "Book":       r.get("book","—") or "—",
            "Status":     r.get("status","") or "—",
            "Clock In":   r.get("clock_in","") or "—",
            "Tea":        dur(r.get("tea_start",""),r.get("tea_end","")),
            "Lunch":      dur(r.get("lunch_start",""),r.get("lunch_end","")),
            "Bathroom":   dur(r.get("bathroom_start",""),r.get("bathroom_end","")),
            "Meeting":    dur(r.get("meeting_start",""),r.get("meeting_end","")),
            "Knockoff":   r.get("new_knockoff","") or "16:30",
            "Late(m)":    safe_int(r.get("late_minutes",0)),
        }
        if show_reasons:
            row["Late Reason"]     = pr["Late Reason"]
            row["Tea Reason"]      = pr["Tea Reason"]
            row["Lunch Reason"]    = pr["Lunch Reason"]
            row["Bathroom Reason"] = pr["Bathroom Reason"]
        rows.append(row)

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.map(lambda v: SC.get(v,""), subset=["Status"]),
            use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════
# WORKING HOURS FRAGMENT
# ═══════════════════════════════════════════════════════════════
@st.fragment(run_every=60)
def working_hours_fragment(role, username):
    records = db.get_attendance_today(today_str())
    if role == "supervisor":
        allowed = set()
        for bd in db.get_supervisor_books(username).values():
            allowed.update(bd.get("agents",[]))
        records = [r for r in records if r["agent"] in allowed]
    elif role == "agent":
        records = [r for r in records if r["agent"] == username]

    st.subheader("⏱️ Working Hours Today")
    st.caption(f"Required: {REQUIRED_HOURS}h (480 min) | Excludes tea & lunch breaks")

    if not records:
        st.info("No records yet."); return

    rows = []
    req = REQUIRED_HOURS * 60
    for r in records:
        ci = r.get("clock_in","") or ""
        co = r.get("clock_out","") or now_str()
        if not ci: continue
        wm = calc_worked_minutes(ci, co,
            r.get("tea_start","") or "", r.get("tea_end","") or "",
            r.get("lunch_start","") or "", r.get("lunch_end","") or "")
        pct = min(100, int(wm/req*100))
        status_icon = "✅" if wm >= req else ("🟡" if wm >= req*0.75 else "🔴")
        rows.append({
            "Agent":        format_email(r["agent"]),
            "Clock In":     ci,
            "Clock Out":    r.get("clock_out","") or "Still working",
            "Worked (min)": wm,
            "Required":     req,
            "% Complete":   f"{pct}%",
            "Status":       status_icon,
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════
if tab == "dashboard" and role in ("supervisor","admin","receptionist"):
    dashboard_fragment(role, username)

elif tab == "working_hours" and role in ("supervisor","admin","agent"):
    working_hours_fragment(role, username)

elif tab == "clockin":
    st.subheader("⏰ Clock In")
    recs = db.get_attendance_today(today_str())
    if any(r["agent"] == username for r in recs):
        me = next(r for r in recs if r["agent"] == username)
        st.warning(f"✅ Already clocked in at **{me.get('clock_in','—')}** SAST")
    else:
        ct   = now_str(); late = calc_late_minutes(ct)
        if late > 0:
            st.error(f"⚠️ {late} minutes late (SAST {ct}). Please select a reason.")
            reason_sel = st.selectbox("Reason for late arrival *", LATE_REASONS)
        else:
            st.success(f"✅ On time! SAST: **{ct}**")
            reason_sel = ""
        books = db.get_agent_books(username)
        book  = (st.selectbox("Your Book", books) if books
                 else st.text_input("Book", value="Unassigned"))
        if st.button("✅ Confirm Clock In", use_container_width=True, type="primary"):
            if late > 0 and (not reason_sel or reason_sel.startswith("--")):
                st.error("Please select a reason for your late arrival.")
            else:
                r_str = append_reason("","Late",reason_sel) if late>0 and reason_sel else ""
                db.clock_in_agent(username, book, ct, late, r_str, today_str())
                st.success(f"✅ Clocked in at {ct} SAST")
                time.sleep(0.8); st.rerun()

elif tab == "tea":
    st.subheader("☕ Tea Break")
    tea_fragment(username, today_str())

elif tab == "lunch":
    st.subheader("🍽️ Lunch Break")
    lunch_fragment(username, today_str())

elif tab == "bathroom" and role in ("agent","receptionist"):
    st.subheader("🚻 Bathroom Break")
    bathroom_fragment(username, today_str())

elif tab == "reception":
    st.subheader("📋 Reception")
    recs    = db.get_attendance_today(today_str())
    me      = next((r for r in recs if r["agent"] == username), None)
    if not me:
        st.error("Clock in first.")
    else:
        rs = me.get("reception_start","") or ""
        re = me.get("reception_end","")   or ""
        if not rs:
            st.info("Log when you go to reception and when you return.")
            reason_sel = st.selectbox("Reason for going to reception *", RECEPTION_REASONS)
            if st.button("📋 Go to Reception", use_container_width=True, type="primary"):
                if not reason_sel or reason_sel.startswith("--"):
                    st.error("Please select a reason.")
                else:
                    s = now_str()
                    db.update_field(username,"reception_start",s,today_str())
                    db.update_field(username,"status","Reception",today_str())
                    existing = me.get("reason","") or ""
                    db.update_field(username,"reason",
                        append_reason(existing,"Reception",reason_sel),today_str())
                    st.success(f"Logged at {s} SAST"); time.sleep(0.5); st.rerun()
        elif not re:
            st.info(f"📋 At reception since **{rs} SAST**")
            try:
                start_dt = datetime.strptime(f"{today_str()} {rs}","%Y-%m-%d %H:%M").replace(tzinfo=SAST)
                elapsed  = int((now_sast()-start_dt).total_seconds()/60)
                st.metric("Time at reception", f"{elapsed} min")
            except: pass
            if st.button("✅ Return from Reception", use_container_width=True, type="primary"):
                et = now_str()
                db.update_field(username,"reception_end",et,today_str())
                db.update_field(username,"status","Dialing",today_str())
                st.success(f"✅ Returned at {et} SAST"); time.sleep(0.5); st.rerun()
        else:
            st.success(f"✅ Reception: {rs} → {re} ({dur(rs,re)})")

elif tab == "meeting":
    st.subheader("🤝 Meeting")
    meeting_fragment(username, today_str())

elif tab == "clockout":
    st.subheader("🚪 Clock Out")
    recs = db.get_attendance_today(today_str())
    me   = next((r for r in recs if r["agent"] == username), None)
    if not me: st.error("Not clocked in today.")
    elif me.get("clock_out"): st.success(f"✅ Clocked out at **{me['clock_out']}** SAST.")
    else:
        ct      = now_str()
        late    = safe_int(me.get("late_minutes",0))
        tea_x   = safe_int(me.get("tea_extra",0))
        lunch_x = safe_int(me.get("lunch_extra",0))
        bath_x  = safe_int(me.get("bathroom_extra",0))
        total   = late + tea_x + lunch_x + bath_x
        nk      = calc_new_knockoff(late, tea_x, lunch_x, bath_x)
        wm      = calc_worked_minutes(
            me.get("clock_in","") or "", ct,
            me.get("tea_start","") or "", me.get("tea_end","") or "",
            me.get("lunch_start","") or "", me.get("lunch_end","") or "")
        st.markdown("### 📋 Summary")
        c1,c2 = st.columns(2)
        with c1:
            st.metric("Clock In",     me.get("clock_in","—"))
            st.metric("Tea Extra",    f"{tea_x} min")
            st.metric("Total Extra",  f"{total} min")
            st.metric("Worked Today", f"{wm} min ({round(wm/60,1)}h)")
        with c2:
            st.metric("Clock Out",    f"{ct} SAST")
            st.metric("Lunch Extra",  f"{lunch_x} min")
            st.metric("New Knockoff", nk)
            req = REQUIRED_HOURS * 60
            pct = min(100, int(wm/req*100))
            st.metric("Target",       f"{pct}% of {REQUIRED_HOURS}h")
        if late > 0:   st.error(f"⚠️ Late penalty: {late} min")
        if bath_x > 0: st.warning(f"⚠️ Bathroom overage: {bath_x} min")
        if total == 0: st.success("✅ No penalties — knockoff 16:30")
        if st.button("✅ Confirm Clock Out", use_container_width=True, type="primary"):
            db.clock_out_agent(username, ct, late, tea_x, lunch_x, nk,
                               today_str(), wm)
            st.success("✅ Clocked out! Goodbye 👋")
            time.sleep(1.5); auth.logout(); st.rerun()

elif tab == "daily_report" and role in ("supervisor","admin","receptionist"):
    st.subheader("📊 Daily Report")
    records = db.get_attendance_today(today_str())
    if role == "supervisor":
        allowed = set()
        for bd in db.get_supervisor_books(username).values():
            allowed.update(bd.get("agents",[]))
        records = [r for r in records if r["agent"] in allowed]
    if not records: st.info("No records for today yet.")
    else:
        rows = []
        for r in records:
            pr = parse_reasons(r.get("reason",""))
            rows.append({
                "Agent":     format_email(r["agent"]),
                "Book":      r.get("book","—") or "—",
                "Status":    r.get("status",""),
                "In":        r.get("clock_in","") or "—",
                "Out":       r.get("clock_out","") or "—",
                "Tea":       dur(r.get("tea_start",""),r.get("tea_end","")),
                "Lunch":     dur(r.get("lunch_start",""),r.get("lunch_end","")),
                "Bathroom":  dur(r.get("bathroom_start",""),r.get("bathroom_end","")),
                "Meeting":   dur(r.get("meeting_start",""),r.get("meeting_end","")),
                "Late(m)":   safe_int(r.get("late_minutes",0)),
                "Tea+(m)":   safe_int(r.get("tea_extra",0)),
                "Lunch+(m)": safe_int(r.get("lunch_extra",0)),
                "Bath+(m)":  safe_int(r.get("bathroom_extra",0)),
                "Knockoff":  r.get("new_knockoff","") or "16:30",
                "Worked(m)": safe_int(r.get("worked_minutes",0)),
                "Late Reason":  pr["Late Reason"] if role!="receptionist" else "",
                "Tea Reason":   pr["Tea Reason"]  if role!="receptionist" else "",
                "Lunch Reason": pr["Lunch Reason"] if role!="receptionist" else "",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        lc = len(df[df["Late(m)"]>0])
        st.caption(f"Total: {len(df)} | On Time: {len(df)-lc} | Late: {lc}")

elif tab == "range_report" and role in ("supervisor","admin"):
    st.subheader("📅 Weekly / Monthly Report")
    c1,c2 = st.columns(2)
    with c1: start = st.date_input("From",value=now_sast().date().replace(day=1))
    with c2: end   = st.date_input("To",  value=now_sast().date())
    if st.button("Generate",type="primary"):
        records = db.get_attendance_range(str(start),str(end))
        if role == "supervisor":
            allowed = set()
            for bd in db.get_supervisor_books(username).values():
                allowed.update(bd.get("agents",[]))
            records = [r for r in records if r["agent"] in allowed]
        if not records: st.info("No data.")
        else:
            df = pd.DataFrame(records)
            for col in ["late_minutes","tea_extra","lunch_extra","bathroom_extra","worked_minutes"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col],errors="coerce").fillna(0)
            s = df.groupby("agent").agg(
                Days=("date","nunique"),
                Late_Min=("late_minutes","sum"),
                Tea_X=("tea_extra","sum"),
                Lunch_X=("lunch_extra","sum"),
                Bath_X=("bathroom_extra","sum"),
                Worked_Min=("worked_minutes","sum"),
            ).reset_index()
            s["agent"] = s["agent"].apply(format_email)
            s["Worked (h)"] = (s["Worked_Min"]/60).round(1)
            s.columns = ["Agent","Days","Late (min)","Tea Extra","Lunch Extra",
                         "Bathroom Extra","Worked (min)","Worked (h)"]
            st.dataframe(s, use_container_width=True, hide_index=True)
            import io; buf = io.BytesIO()
            with pd.ExcelWriter(buf,engine="openpyxl") as w:
                s.to_excel(w,index=False,sheet_name="Summary")
                df.to_excel(w,index=False,sheet_name="Raw")
            st.download_button("📥 Download Excel",buf.getvalue(),
                file_name=f"NICS_{start}_{end}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

elif tab == "absent" and role in ("supervisor","admin","receptionist"):
    st.subheader("🔍 Absent Today")
    all_a = db.get_agent_usernames()
    ci    = {r["agent"] for r in db.get_attendance_today(today_str())}
    if role == "supervisor":
        allowed = set()
        for bd in db.get_supervisor_books(username).values():
            allowed.update(bd.get("agents",[]))
        all_a = [a for a in all_a if a in allowed]
    absent = [a for a in all_a if a not in ci]
    if not absent: st.success("✅ All agents clocked in!")
    else:
        st.warning(f"⚠️ {len(absent)} absent:")
        for a in sorted(absent): st.markdown(f"- 📧 {format_email(a)}")

elif tab == "history" and role in ("supervisor","admin"):
    st.subheader("📜 Agent History")
    all_a = db.get_agent_usernames()
    if role == "supervisor":
        allowed = set()
        for bd in db.get_supervisor_books(username).values():
            allowed.update(bd.get("agents",[]))
        all_a = [a for a in all_a if a in allowed]
    sel  = st.selectbox("Agent",[format_email(a) for a in sorted(all_a)])
    recs = [r for r in db.get_attendance_all() if r["agent"]==sel.split("@")[0]]
    if not recs: st.info("No records.")
    else:
        rows = []
        for r in recs:
            pr = parse_reasons(r.get("reason",""))
            rows.append({
                "Date":r.get("date",""),"Book":r.get("book","—") or "—",
                "Clock In":r.get("clock_in","") or "—",
                "Clock Out":r.get("clock_out","") or "—",
                "Late(m)":safe_int(r.get("late_minutes",0)),
                "Tea Extra":safe_int(r.get("tea_extra",0)),
                "Lunch Extra":safe_int(r.get("lunch_extra",0)),
                "Bath Extra":safe_int(r.get("bathroom_extra",0)),
                "Worked(m)":safe_int(r.get("worked_minutes",0)),
                "Knockoff":r.get("new_knockoff","") or "16:30",
                "Status":r.get("status",""),
                "Late Reason":pr["Late Reason"],
                "Tea Reason":pr["Tea Reason"],
                "Lunch Reason":pr["Lunch Reason"],
            })
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

elif tab == "export" and role in ("supervisor","admin"):
    st.subheader("💾 Export")
    c1,c2 = st.columns(2)
    with c1: start = st.date_input("From",value=now_sast().date())
    with c2: end   = st.date_input("To",  value=now_sast().date())
    if st.button("Export",type="primary"):
        records = db.get_attendance_range(str(start),str(end))
        if role == "supervisor":
            allowed = set()
            for bd in db.get_supervisor_books(username).values():
                allowed.update(bd.get("agents",[]))
            records = [r for r in records if r["agent"] in allowed]
        if not records: st.info("No data.")
        else:
            import io; rows = []
            for r in records:
                pr = parse_reasons(r.get("reason",""))
                rows.append({**{k:r.get(k,"") for k in [
                    "date","agent","book","clock_in","clock_out",
                    "late_minutes","tea_extra","lunch_extra","bathroom_extra",
                    "meeting_extra","new_knockoff","worked_minutes","status"]},
                    "Late Reason":pr["Late Reason"],
                    "Tea Reason":pr["Tea Reason"],
                    "Lunch Reason":pr["Lunch Reason"],
                    "Bathroom Reason":pr["Bathroom Reason"],
                })
            df = pd.DataFrame(rows); buf = io.BytesIO()
            df.to_excel(buf,index=False,engine="openpyxl")
            st.download_button("📥 Download",buf.getvalue(),
                file_name=f"NICS_{start}_{end}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

elif tab == "books" and role in ("supervisor","admin"):
    st.subheader("📚 Manage Books")
    books  = db.get_books() if role=="admin" else db.get_supervisor_books(username)
    all_a  = db.get_agent_usernames()
    cl,cr  = st.columns([1,2])
    with cl:
        st.markdown("#### Books")
        sel_book = (st.radio("Select",list(books.keys()),
                             label_visibility="collapsed") if books else None)
        if not books: st.info("No books yet.")
        if role == "admin":
            st.markdown("---")
            nb = st.text_input("New book name")
            if st.button("➕ Create") and nb.strip():
                if nb.strip() not in books:
                    db.upsert_book(nb.strip(),[],[])
                    st.success("Created"); time.sleep(0.4); st.rerun()
                else: st.warning("Already exists.")
            if sel_book:
                st.markdown("---")
                st.markdown("**Rename book:**")
                new_name = st.text_input("New name", value=sel_book, key="rename_input")
                if st.button("✏️ Rename Book"):
                    if new_name.strip() and new_name.strip() != sel_book:
                        if db.rename_book(sel_book, new_name.strip()):
                            st.success(f"Renamed to '{new_name}'")
                            time.sleep(0.4); st.rerun()
                        else: st.error("Rename failed.")
                    else: st.warning("Enter a different name.")
                st.markdown("---")
                if st.button("🗑️ Delete Book"):
                    db.delete_book(sel_book)
                    st.success("Deleted"); time.sleep(0.4); st.rerun()
    with cr:
        if sel_book and sel_book in books:
            bd = books[sel_book]; ba = bd.get("agents",[])
            st.markdown(f"#### {sel_book} ({len(ba)} agents)")
            if ba:
                rs = st.selectbox("Remove agent",
                    [format_email(a) for a in sorted(ba)],key="rem_ag")
                if st.button("🗑️ Remove from Book"):
                    ru = rs.split("@")[0]
                    db.upsert_book(sel_book,bd.get("supervisors",[]),
                                   [a for a in ba if a!=ru])
                    st.success(f"Removed {ru}"); time.sleep(0.4); st.rerun()
            else: st.info("No agents yet.")
            ni = [a for a in all_a if a not in ba]
            if ni:
                as_ = st.selectbox("Add agent",
                    [format_email(a) for a in sorted(ni)],key="add_ag")
                if st.button("➕ Add to Book",type="primary"):
                    au = as_.split("@")[0]
                    db.upsert_book(sel_book,bd.get("supervisors",[]),ba+[au])
                    st.success(f"Added {au}"); time.sleep(0.4); st.rerun()
            if role == "admin":
                st.markdown("---"); st.markdown("**Supervisors:**")
                bs = bd.get("supervisors",[]); all_s = list(auth.SUPERVISORS)
                if bs:
                    rs2 = st.selectbox("Remove sup",
                        [format_email(s) for s in bs],key="rem_sup")
                    if st.button("🗑️ Remove Supervisor"):
                        ru2 = rs2.split("@")[0]
                        db.upsert_book(sel_book,[s for s in bs if s!=ru2],ba); st.rerun()
                na = [s for s in all_s if s not in bs]
                if na:
                    as2 = st.selectbox("Assign sup",
                        [format_email(s) for s in na],key="add_sup")
                    if st.button("➕ Assign Supervisor",type="primary"):
                        au2 = as2.split("@")[0]
                        db.upsert_book(sel_book,bs+[au2],ba); st.rerun()

elif tab == "password" and role == "admin":
    st.subheader("🔑 Change Password")
    pt = st.selectbox("Change for",["Admin","Supervisor"])
    with st.form("pw"):
        np = st.text_input("New Password",type="password")
        cp = st.text_input("Confirm",type="password")
        if st.form_submit_button("Update",type="primary"):
            if not np: st.error("Cannot be empty.")
            elif np!=cp: st.error("Don't match.")
            else:
                db.set_setting(
                    "admin_password" if pt=="Admin" else "supervisor_password",np)
                st.success(f"✅ {pt} password updated.")

elif tab == "admin" and role == "admin":
    st.subheader("⚙️ Admin Panel")
    admin_tab = st.tabs(["👤 Agents","🛎️ Receptionists","🔐 PINs"])

    with admin_tab[0]:
        agents = db.get_agents()
        c1,c2  = st.columns([1.2,2])
        with c1:
            st.markdown("#### Add Agent")
            with st.form("add_f"):
                fn  = st.text_input("Full Name",placeholder="e.g. Nokwanda Ntuli")
                un  = st.text_input("Username", placeholder="e.g. nokwandan")
                pin = st.text_input("4-digit PIN",placeholder="e.g. 1234",max_chars=4)
                if st.form_submit_button("➕ Add Agent",type="primary"):
                    u = un.strip().replace("@nics.co.za","")
                    if not u or not fn.strip():
                        st.error("Name and username required.")
                    elif not pin.strip().isdigit() or len(pin.strip())!=4:
                        st.error("PIN must be exactly 4 digits.")
                    elif u in [a["username"] for a in agents]:
                        st.warning("Already exists.")
                    else:
                        db.add_agent(u,fn.strip(),pin.strip())
                        st.success(f"✅ {fn} added!")
                        time.sleep(0.8); st.rerun()
        with c2:
            st.markdown("#### Registered Agents")
            if agents:
                st.dataframe(pd.DataFrame([
                    {"#":i+1,"Email":format_email(a["username"]),
                     "Name":a.get("display_name",""),
                     "PIN Set":"✅" if a.get("pin") else "❌"}
                    for i,a in enumerate(agents)]),
                    use_container_width=True,hide_index=True)
                st.markdown("---")
                rem = st.selectbox("Remove",[format_email(a["username"]) for a in agents])
                if st.button("🗑️ Remove Agent"):
                    ru = rem.split("@")[0]
                    if ru in auth.ADMINS: st.error("Cannot remove admin.")
                    else:
                        db.remove_agent(ru)
                        st.success(f"Removed {rem}"); time.sleep(0.4); st.rerun()

    with admin_tab[1]:
        st.markdown("#### Receptionists")
        recs_list = db.get_receptionists()
        c1,c2 = st.columns([1.2,2])
        with c1:
            st.markdown("**Add Receptionist**")
            with st.form("add_rec"):
                rfn = st.text_input("Full Name",placeholder="e.g. Maggy Ramahlo")
                run = st.text_input("Username", placeholder="e.g. mramahlo")
                rpin= st.text_input("4-digit PIN",max_chars=4)
                if st.form_submit_button("➕ Add",type="primary"):
                    u = run.strip().replace("@nics.co.za","")
                    if not u or not rfn.strip():
                        st.error("Name and username required.")
                    elif not rpin.strip().isdigit() or len(rpin.strip())!=4:
                        st.error("PIN must be 4 digits.")
                    elif u in [r["username"] for r in recs_list]:
                        st.warning("Already exists.")
                    else:
                        db.add_receptionist(u,rfn.strip(),rpin.strip())
                        st.success(f"✅ {rfn} added!")
                        time.sleep(0.8); st.rerun()
        with c2:
            if recs_list:
                st.dataframe(pd.DataFrame([
                    {"Username":format_email(r["username"]),
                     "Name":r.get("display_name",""),
                     "PIN Set":"✅" if r.get("pin") else "❌"}
                    for r in recs_list]),
                    use_container_width=True,hide_index=True)
                rem_r = st.selectbox("Remove",[format_email(r["username"]) for r in recs_list])
                if st.button("🗑️ Remove Receptionist"):
                    db.remove_receptionist(rem_r.split("@")[0])
                    st.success(f"Removed {rem_r}"); time.sleep(0.4); st.rerun()

    with admin_tab[2]:
        st.markdown("#### Update Agent PINs")
        st.info("Use this to reset or update a PIN for any agent.")
        agents = db.get_agents()
        sel_a  = st.selectbox("Select Agent",[format_email(a["username"]) for a in agents])
        new_pin= st.text_input("New 4-digit PIN",max_chars=4,type="password")
        if st.button("🔐 Update PIN",type="primary"):
            if not new_pin.strip().isdigit() or len(new_pin.strip())!=4:
                st.error("PIN must be exactly 4 digits.")
            else:
                db.update_agent_pin(sel_a.split("@")[0],new_pin.strip())
                st.success(f"✅ PIN updated for {sel_a}")

else:
    if role in ("agent","receptionist"):
        st.info("👈 Use the sidebar to Clock In, manage breaks, or Clock Out.")
    elif role in ("supervisor","admin"):
        st.session_state.active_tab = "dashboard"; st.rerun()
