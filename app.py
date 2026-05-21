"""
app.py — NICS Employee Time Monitoring System
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import auth
import database as db
from utils import (calc_late_minutes, calc_new_knockoff,
                   format_email, safe_int, TEA_LIMIT, LUNCH_LIMIT)

SAST = timezone(timedelta(hours=2))
def now_sast():  return datetime.now(SAST)
def now_str():   return now_sast().strftime("%H:%M")
def today_str(): return now_sast().strftime("%Y-%m-%d")

# ── helpers ────────────────────────────────────────────────────────────────────
def append_reason(existing, prefix, new_text):
    """Append a prefixed reason to any existing reason string."""
    part = f"{prefix}: {new_text.strip()}"
    if existing and existing.strip():
        return f"{existing.strip()} | {part}"
    return part

def parse_reasons(reason_str):
    """Split a combined reason string into a dict {Late, Tea, Lunch}."""
    out = {"Late Reason": "", "Tea Reason": "", "Lunch Reason": ""}
    if not reason_str:
        return out
    for chunk in str(reason_str).split("|"):
        chunk = chunk.strip()
        if chunk.startswith("Late: "):
            out["Late Reason"] = chunk[6:]
        elif chunk.startswith("Tea: "):
            out["Tea Reason"] = chunk[5:]
        elif chunk.startswith("Lunch: "):
            out["Lunch Reason"] = chunk[7:]
    return out

# ══════════════════════════════════════════════════════════════════════════════
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
.cbox .digits{font-size:4rem;font-weight:700;font-family:monospace;
  letter-spacing:4px;color:white}
.cbox .lbl{font-size:1rem;color:rgba(255,255,255,0.9);margin-top:.5rem}

/* Status badges — always visible on any background */
.badge{display:inline-block;padding:3px 10px;border-radius:4px;
  font-weight:700;font-size:.85rem;letter-spacing:.3px}
.badge-dial {background:#2e7d32;color:#ffffff}
.badge-tea  {background:#e65100;color:#ffffff}
.badge-lunch{background:#1565C0;color:#ffffff}
.badge-out  {background:#424242;color:#ffffff}

div[data-testid="stButton"] button{border-radius:6px;font-weight:600}
</style>""", unsafe_allow_html=True)

# ── session defaults ───────────────────────────────────────────────────────────
for k, v in [("user", None), ("active_tab", "dashboard"), ("dark_mode", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── theme ──────────────────────────────────────────────────────────────────────
if st.session_state.dark_mode:
    st.markdown("""<style>
    .stApp{background:#1a1a2e!important}
    section[data-testid="stSidebar"]{background:#0f0f23!important}
    section[data-testid="stSidebar"] *{color:#e0e0e0!important}
    </style>""", unsafe_allow_html=True)
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

# ── header ─────────────────────────────────────────────────────────────────────
_t = now_sast()
st.markdown(f"""<div class="main-header">
<h1>🕐 EMPLOYEE TIME MONITORING SYSTEM — NICS</h1>
<p>NICS Call Centre &nbsp;|&nbsp; Work: 08:00–16:30 &nbsp;|&nbsp;
Tea: 15 min &nbsp;|&nbsp; Lunch: 60 min &nbsp;|&nbsp;
🇿🇦 {_t.strftime('%A, %d %B %Y')} &nbsp;<strong>{_t.strftime('%H:%M:%S')}</strong> SAST</p>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
if not auth.is_logged_in():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("### 🔐 Login")
        with st.form("login_form", clear_on_submit=False):
            uname = st.text_input("Username", placeholder="e.g. cyounis")
            pwd   = st.text_input("Password", type="password",
                                  placeholder="Supervisors & Admin only")
            if st.form_submit_button("Login", use_container_width=True):
                if not uname.strip():
                    st.error("Please enter your username.")
                else:
                    u = auth.try_login(uname.strip(), pwd.strip())
                    if u:
                        st.session_state.user = u
                        st.session_state.active_tab = (
                            "clockin" if u["role"] == "agent" else "dashboard")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Agents need no password.")
        st.caption("💡 Agents: username only. Supervisors/Admin: username + password.")
    st.stop()

user     = auth.current_user()
role     = auth.current_role()
username = auth.current_username()
tab      = st.session_state.active_tab

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"**👤 {format_email(username)}**")
    st.caption(f"Role: {role.title()}")

    if role == "agent":
        st.markdown("---")
        st.markdown("#### 📋 My Status Today")
        _recs = db.get_attendance_today(today_str())
        _me   = next((r for r in _recs if r["agent"] == username), None)
        if _me:
            st.success(f"🕐 In: **{_me.get('clock_in','—')}**")
            _ts = _me.get("tea_start","") or ""
            _te = _me.get("tea_end","")   or ""
            _ls = _me.get("lunch_start","") or ""
            _le = _me.get("lunch_end","")   or ""
            if _ts: st.info(f"☕ Tea: {_ts} → {_te or 'ongoing'}")
            if _ls: st.info(f"🍽️ Lunch: {_ls} → {_le or 'ongoing'}")
            st.warning(f"🚪 Knockoff: **{_me.get('new_knockoff','') or '16:30'}**")
            _sv = _me.get("status","") or "Dialing"
            _cls = {"Dialing":"badge badge-dial","Tea Break":"badge badge-tea",
                    "Lunch Break":"badge badge-lunch","Clocked Out":"badge badge-out"
                    }.get(_sv, "badge badge-dial")
            st.markdown(f"**Status:** <span class='{_cls}'>{_sv}</span>",
                        unsafe_allow_html=True)
        else:
            st.info("Not clocked in yet.")

    st.markdown("---")
    st.markdown("#### ⏱️ Actions")
    for _lbl, _key in [("⏰ Clock In","clockin"),("☕ Tea Break","tea"),
                       ("🍽️ Lunch Break","lunch"),("🚪 Clock Out","clockout")]:
        if st.button(_lbl, use_container_width=True, key=f"sb_{_key}"):
            st.session_state.active_tab = _key; st.rerun()

    if role in ("supervisor","admin"):
        st.markdown("---"); st.markdown("#### 📊 Reports & Tools")
        for _lbl, _key in [
            ("📊 Dashboard","dashboard"),("📋 Daily Report","daily_report"),
            ("📅 Weekly/Monthly","range_report"),("🔍 Absent Today","absent"),
            ("📜 Agent History","history"),("💾 Export to Excel","export"),
            ("📚 Manage Books","books"),("🔑 Change Password","password")]:
            if st.button(_lbl, use_container_width=True, key=f"sb_{_key}"):
                st.session_state.active_tab = _key; st.rerun()

    if role == "admin":
        st.markdown("---")
        if st.button("⚙️ Admin Panel", use_container_width=True, key="sb_admin"):
            st.session_state.active_tab = "admin"; st.rerun()

    st.markdown("---")
    if st.button("☀️ Light Mode" if st.session_state.dark_mode else "🌙 Dark Mode",
                 use_container_width=True, key="sb_dm"):
        st.session_state.dark_mode = not st.session_state.dark_mode; st.rerun()
    if st.button("🚪 Logout", use_container_width=True, key="sb_logout"):
        auth.logout(); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FRAGMENT: live clock — ticks every second on all pages
# ══════════════════════════════════════════════════════════════════════════════
@st.fragment(run_every=1)
def live_clock():
    n = now_sast()
    st.caption(f"🇿🇦 **{n.strftime('%H:%M:%S')} SAST** — {n.strftime('%A, %d %B %Y')}")

live_clock()

# ══════════════════════════════════════════════════════════════════════════════
# FRAGMENT: dashboard — auto-refreshes every 10 s
# ══════════════════════════════════════════════════════════════════════════════
@st.fragment(run_every=10)
def dashboard_fragment(role, username):
    records = db.get_attendance_today(today_str())
    if role == "supervisor":
        allowed = set()
        for bd in db.get_supervisor_books(username).values():
            allowed.update(bd.get("agents", []))
        records = [r for r in records if r["agent"] in allowed]

    st.subheader("📊 Live Agent Dashboard")
    st.caption(f"🔄 Auto-refreshes every 10 s | 🇿🇦 {now_sast().strftime('%H:%M:%S')} SAST")

    if not records:
        st.info("No agents have clocked in today yet.")
        return

    total    = len(records)
    on_time  = sum(1 for r in records if safe_int(r.get("late_minutes",0)) == 0)
    late_cnt = sum(1 for r in records if safe_int(r.get("late_minutes",0)) > 0)
    on_brk   = sum(1 for r in records if r.get("status","") in ("Tea Break","Lunch Break"))
    co       = sum(1 for r in records if r.get("status","") == "Clocked Out")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total",total); c2.metric("On Time",on_time); c3.metric("Late",late_cnt)
    c4.metric("On Break",on_brk); c5.metric("Clocked Out",co)
    st.markdown("---")

    cur = now_str()
    for r in records:
        s = r.get("status","")
        if s == "Tea Break" and r.get("tea_start"):
            try:
                el = int((datetime.strptime(cur,"%H:%M") -
                          datetime.strptime(r["tea_start"],"%H:%M")).total_seconds()/60)
                if el > TEA_LIMIT:
                    st.warning(f"⚠️ {format_email(r['agent'])} — Tea {el-TEA_LIMIT} min OVER!")
            except: pass
        if s == "Lunch Break" and r.get("lunch_start"):
            try:
                el = int((datetime.strptime(cur,"%H:%M") -
                          datetime.strptime(r["lunch_start"],"%H:%M")).total_seconds()/60)
                if el > LUNCH_LIMIT:
                    st.warning(f"⚠️ {format_email(r['agent'])} — Lunch {el-LUNCH_LIMIT} min OVER!")
            except: pass

    SC = {
        "Tea Break":   "background-color:#FFF3E0;color:#E65100;font-weight:bold",
        "Lunch Break": "background-color:#E3F2FD;color:#1565C0;font-weight:bold",
        "Clocked Out": "background-color:#EEEEEE;color:#212121;font-weight:bold",
        "Dialing":     "background-color:#E8F5E9;color:#1B5E20;font-weight:bold",
    }

    books_list = sorted(set(r.get("book","") or "—" for r in records))
    bf = st.selectbox("Filter by Book", ["All Books"]+books_list, key="dash_bf")

    def dur(s, e):
        try: return str(int((datetime.strptime(e,"%H:%M")-
                              datetime.strptime(s,"%H:%M")).total_seconds()/60))+"m"
        except: return "—"

    rows = []
    for r in records:
        if bf != "All Books" and (r.get("book","") or "—") != bf: continue
        pr = parse_reasons(r.get("reason",""))
        rows.append({
            "Agent":        format_email(r["agent"]),
            "Book":         r.get("book","—") or "—",
            "Status":       r.get("status","") or "—",
            "Clock In":     r.get("clock_in","") or "—",
            "Tea":          dur(r.get("tea_start",""), r.get("tea_end","")),
            "Lunch":        dur(r.get("lunch_start",""), r.get("lunch_end","")),
            "Knockoff":     r.get("new_knockoff","") or "16:30",
            "Late(m)":      safe_int(r.get("late_minutes",0)),
            "Late Reason":  pr["Late Reason"],
            "Tea Reason":   pr["Tea Reason"],
            "Lunch Reason": pr["Lunch Reason"],
        })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.map(
                lambda v: SC.get(v, "background-color:#E8F5E9;color:#1B5E20;font-weight:bold"),
                subset=["Status"]),
            use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# FRAGMENT: Tea break — reads fresh DB every second, full flow inside
# ══════════════════════════════════════════════════════════════════════════════
@st.fragment(run_every=1)
def tea_break_fragment(username, today_s):
    recs = db.get_attendance_today(today_s)
    me   = next((r for r in recs if r["agent"] == username), None)
    if not me:
        st.error("Clock in first before starting a break.")
        return

    ts = me.get("tea_start","") or ""
    te = me.get("tea_end","")   or ""

    # ── Not started yet ────────────────────────────────────────────────────────
    if not ts:
        st.info(f"☕ Tea break limit: **{TEA_LIMIT} minutes**")
        if st.button("☕ Start Tea Break", use_container_width=True,
                     type="primary", key="start_tea_frag"):
            s = now_str()
            db.update_field(username, "tea_start", s,           today_s)
            db.update_field(username, "status",    "Tea Break", today_s)
            st.rerun(scope="app")

    # ── Started, not ended — show live countdown ───────────────────────────────
    elif not te:
        try:
            tea_dt     = datetime.strptime(f"{today_s} {ts}", "%Y-%m-%d %H:%M").replace(tzinfo=SAST)
            limit_secs = TEA_LIMIT * 60
            elapsed    = int((now_sast() - tea_dt).total_seconds())
            remaining  = limit_secs - elapsed
            rem_m, rem_s = divmod(abs(remaining), 60)
            is_over    = remaining < 0

            if is_over:
                st.markdown(f"""<div class="cbox cbox-red">
                <div class="digits">+{rem_m:02d}:{rem_s:02d}</div>
                <div class="lbl">⚠️ OVER the 15-minute tea limit!</div>
                </div>""", unsafe_allow_html=True)
                reason = st.text_area("Reason for overage *",
                    placeholder="Why did you exceed 15 minutes?", key="tea_over_reason")
            else:
                st.markdown(f"""<div class="cbox cbox-blue">
                <div class="digits">{rem_m:02d}:{rem_s:02d}</div>
                <div class="lbl">☕ Tea break — counting down from 15:00</div>
                </div>""", unsafe_allow_html=True)
                st.info(f"☕ Started: **{ts} SAST** — press End when you return.")
                reason = ""

            if st.button("✅ End Tea Break", use_container_width=True,
                         type="primary", key="end_tea_frag"):
                if is_over and not (reason or "").strip():
                    st.error("Please provide a reason for the overage.")
                else:
                    et = now_str()
                    db.update_field(username, "tea_end", et,        today_s)
                    db.update_field(username, "status",  "Dialing", today_s)
                    if is_over:
                        om = max(1, int(abs(remaining) / 60))
                        db.update_field(username, "tea_extra", om, today_s)
                        if reason:
                            existing = me.get("reason","") or ""
                            new_r    = append_reason(existing, "Tea", reason)
                            db.update_field(username, "reason", new_r, today_s)
                    st.rerun(scope="app")

        except Exception as e:
            st.error(f"Countdown error: {e}")

    # ── Completed ──────────────────────────────────────────────────────────────
    else:
        try:
            d = int((datetime.strptime(te,"%H:%M") -
                     datetime.strptime(ts,"%H:%M")).total_seconds()/60)
            st.success(f"✅ Tea completed: {ts} → {te} ({d} min)")
        except:
            st.success(f"✅ Tea completed: {ts} → {te}")

# ══════════════════════════════════════════════════════════════════════════════
# FRAGMENT: Lunch break — reads fresh DB every second, full flow inside
# ══════════════════════════════════════════════════════════════════════════════
@st.fragment(run_every=1)
def lunch_break_fragment(username, today_s):
    recs = db.get_attendance_today(today_s)
    me   = next((r for r in recs if r["agent"] == username), None)
    if not me:
        st.error("Clock in first before starting a break.")
        return

    ls = me.get("lunch_start","") or ""
    le = me.get("lunch_end","")   or ""

    # ── Not started yet ────────────────────────────────────────────────────────
    if not ls:
        st.info(f"🍽️ Lunch break limit: **{LUNCH_LIMIT} minutes**")
        if st.button("🍽️ Start Lunch Break", use_container_width=True,
                     type="primary", key="start_lunch_frag"):
            s = now_str()
            db.update_field(username, "lunch_start", s,              today_s)
            db.update_field(username, "status",      "Lunch Break",  today_s)
            st.rerun(scope="app")

    # ── Started, not ended — show live countdown ───────────────────────────────
    elif not le:
        try:
            lun_dt     = datetime.strptime(f"{today_s} {ls}", "%Y-%m-%d %H:%M").replace(tzinfo=SAST)
            limit_secs = LUNCH_LIMIT * 60
            elapsed    = int((now_sast() - lun_dt).total_seconds())
            remaining  = limit_secs - elapsed
            rem_m, rem_s = divmod(abs(remaining), 60)
            is_over    = remaining < 0

            if is_over:
                st.markdown(f"""<div class="cbox cbox-red">
                <div class="digits">+{rem_m:02d}:{rem_s:02d}</div>
                <div class="lbl">⚠️ OVER the 60-minute lunch limit!</div>
                </div>""", unsafe_allow_html=True)
                reason = st.text_area("Reason for overage *",
                    placeholder="Why did you exceed 60 minutes?", key="lunch_over_reason")
            else:
                st.markdown(f"""<div class="cbox cbox-blue">
                <div class="digits">{rem_m:02d}:{rem_s:02d}</div>
                <div class="lbl">🍽️ Lunch break — counting down from 60:00</div>
                </div>""", unsafe_allow_html=True)
                st.info(f"🍽️ Started: **{ls} SAST** — press End when you return.")
                reason = ""

            if st.button("✅ End Lunch Break", use_container_width=True,
                         type="primary", key="end_lunch_frag"):
                if is_over and not (reason or "").strip():
                    st.error("Please provide a reason for the overage.")
                else:
                    et = now_str()
                    db.update_field(username, "lunch_end",   et,        today_s)
                    db.update_field(username, "status",      "Dialing", today_s)
                    if is_over:
                        om = max(1, int(abs(remaining) / 60))
                        db.update_field(username, "lunch_extra", om,    today_s)
                        if reason:
                            existing = me.get("reason","") or ""
                            new_r    = append_reason(existing, "Lunch", reason)
                            db.update_field(username, "reason", new_r, today_s)
                    st.rerun(scope="app")

        except Exception as e:
            st.error(f"Countdown error: {e}")

    # ── Completed ──────────────────────────────────────────────────────────────
    else:
        try:
            d = int((datetime.strptime(le,"%H:%M") -
                     datetime.strptime(ls,"%H:%M")).total_seconds()/60)
            st.success(f"✅ Lunch completed: {ls} → {le} ({d} min)")
        except:
            st.success(f"✅ Lunch completed: {ls} → {le}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ══════════════════════════════════════════════════════════════════════════════

# ── Dashboard ─────────────────────────────────────────────────────────────────
if tab == "dashboard" and role in ("supervisor","admin"):
    dashboard_fragment(role, username)

# ── Clock In ──────────────────────────────────────────────────────────────────
elif tab == "clockin":
    st.subheader("⏰ Clock In")
    recs = db.get_attendance_today(today_str())
    if any(r["agent"] == username for r in recs):
        me = next(r for r in recs if r["agent"] == username)
        st.warning(f"✅ Already clocked in at **{me.get('clock_in','—')}** SAST")
    else:
        ct   = now_str()
        late = calc_late_minutes(ct)
        reason = ""
        if late > 0:
            st.error(f"⚠️ {late} minutes late (SAST {ct}). Reason required.")
            reason = st.text_area("Reason *", placeholder="e.g. Traffic, load shedding")
        else:
            st.success(f"✅ On time! SAST: **{ct}**")
        books = db.get_agent_books(username)
        book  = (st.selectbox("Your Book", books) if books
                 else st.text_input("Book", value="Unassigned"))
        if st.button("✅ Confirm Clock In", use_container_width=True, type="primary"):
            if late > 0 and not reason.strip():
                st.error("Reason required for late arrival.")
            else:
                r_str = append_reason("", "Late", reason) if (late > 0 and reason.strip()) else ""
                db.clock_in_agent(username, book, ct, late, r_str, today_str())
                st.success(f"✅ Clocked in at {ct} SAST")
                time.sleep(0.8); st.rerun()

# ── Tea Break — fragment handles everything ───────────────────────────────────
elif tab == "tea":
    st.subheader("☕ Tea Break")
    tea_break_fragment(username, today_str())

# ── Lunch Break — fragment handles everything ─────────────────────────────────
elif tab == "lunch":
    st.subheader("🍽️ Lunch Break")
    lunch_break_fragment(username, today_str())

# ── Clock Out ─────────────────────────────────────────────────────────────────
elif tab == "clockout":
    st.subheader("🚪 Clock Out")
    recs = db.get_attendance_today(today_str())
    me   = next((r for r in recs if r["agent"] == username), None)
    if not me:
        st.error("Not clocked in today.")
    elif me.get("clock_out"):
        st.success(f"✅ Clocked out at **{me['clock_out']}** SAST.")
    else:
        ct      = now_str()
        late    = safe_int(me.get("late_minutes",0))
        tea_x   = safe_int(me.get("tea_extra",0))
        lunch_x = safe_int(me.get("lunch_extra",0))
        total   = late + tea_x + lunch_x
        nk      = calc_new_knockoff(late, tea_x, lunch_x)
        st.markdown("### 📋 Summary")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Clock In",     me.get("clock_in","—"))
            st.metric("Tea Extra",    f"{tea_x} min")
            st.metric("Total Extra",  f"{total} min")
        with c2:
            st.metric("Clock Out",    f"{ct} SAST")
            st.metric("Lunch Extra",  f"{lunch_x} min")
            st.metric("New Knockoff", nk)
        if late   > 0: st.error(f"⚠️ Late penalty: {late} min")
        if total == 0: st.success("✅ No penalties — knockoff 16:30")
        if st.button("✅ Confirm Clock Out", use_container_width=True, type="primary"):
            db.clock_out_agent(username, ct, late, tea_x, lunch_x, nk, today_str())
            st.success("✅ Clocked out! Goodbye 👋")
            time.sleep(1.5); auth.logout(); st.rerun()

# ── Daily Report ──────────────────────────────────────────────────────────────
elif tab == "daily_report" and role in ("supervisor","admin"):
    st.subheader("📊 Daily Report")
    records = db.get_attendance_today(today_str())
    if role == "supervisor":
        allowed = set()
        for bd in db.get_supervisor_books(username).values():
            allowed.update(bd.get("agents",[]))
        records = [r for r in records if r["agent"] in allowed]
    if not records:
        st.info("No records for today yet.")
    else:
        def dur(s, e):
            try: return str(int((datetime.strptime(e,"%H:%M")-
                                  datetime.strptime(s,"%H:%M")).total_seconds()/60))+"m"
            except: return "—"
        rows = []
        for r in records:
            pr = parse_reasons(r.get("reason",""))
            rows.append({
                "Agent":        format_email(r["agent"]),
                "Book":         r.get("book","—") or "—",
                "Status":       r.get("status",""),
                "In":           r.get("clock_in","") or "—",
                "Out":          r.get("clock_out","") or "—",
                "Tea":          dur(r.get("tea_start",""), r.get("tea_end","")),
                "Lunch":        dur(r.get("lunch_start",""), r.get("lunch_end","")),
                "Late(m)":      safe_int(r.get("late_minutes",0)),
                "Tea+(m)":      safe_int(r.get("tea_extra",0)),
                "Lunch+(m)":    safe_int(r.get("lunch_extra",0)),
                "Knockoff":     r.get("new_knockoff","") or "16:30",
                "Late Reason":  pr["Late Reason"],
                "Tea Reason":   pr["Tea Reason"],
                "Lunch Reason": pr["Lunch Reason"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        lc = len(df[df["Late(m)"] > 0])
        st.caption(f"Total: {len(df)} | On Time: {len(df)-lc} | Late: {lc}")

# ── Weekly/Monthly Report ─────────────────────────────────────────────────────
elif tab == "range_report" and role in ("supervisor","admin"):
    st.subheader("📅 Weekly / Monthly Report")
    c1, c2 = st.columns(2)
    with c1: start = st.date_input("From", value=now_sast().date().replace(day=1))
    with c2: end   = st.date_input("To",   value=now_sast().date())
    if st.button("Generate", type="primary"):
        records = db.get_attendance_range(str(start), str(end))
        if role == "supervisor":
            allowed = set()
            for bd in db.get_supervisor_books(username).values():
                allowed.update(bd.get("agents",[]))
            records = [r for r in records if r["agent"] in allowed]
        if not records:
            st.info("No data.")
        else:
            df = pd.DataFrame(records)
            for col in ["late_minutes","tea_extra","lunch_extra"]:
                df[col] = pd.to_numeric(df.get(col,0), errors="coerce").fillna(0)
            s = df.groupby("agent").agg(
                Days=("date","nunique"),
                Late_Min=("late_minutes","sum"),
                Tea_Extra=("tea_extra","sum"),
                Lunch_Extra=("lunch_extra","sum")
            ).reset_index()
            s["agent"] = s["agent"].apply(format_email)
            s.columns = ["Agent","Days","Late (min)","Tea Extra (min)","Lunch Extra (min)"]
            st.dataframe(s, use_container_width=True, hide_index=True)
            import io; buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                s.to_excel(w, index=False, sheet_name="Summary")
                df.to_excel(w, index=False, sheet_name="Raw")
            st.download_button("📥 Download Excel", buf.getvalue(),
                file_name=f"NICS_{start}_{end}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── Absent Today ──────────────────────────────────────────────────────────────
elif tab == "absent" and role in ("supervisor","admin"):
    st.subheader("🔍 Absent Today")
    all_a = db.get_agent_usernames()
    ci    = {r["agent"] for r in db.get_attendance_today(today_str())}
    if role == "supervisor":
        allowed = set()
        for bd in db.get_supervisor_books(username).values():
            allowed.update(bd.get("agents",[]))
        all_a = [a for a in all_a if a in allowed]
    absent = [a for a in all_a if a not in ci]
    if not absent:
        st.success("✅ All agents clocked in!")
    else:
        st.warning(f"⚠️ {len(absent)} absent:")
        for a in sorted(absent):
            st.markdown(f"- 📧 {format_email(a)}")

# ── Agent History ─────────────────────────────────────────────────────────────
elif tab == "history" and role in ("supervisor","admin"):
    st.subheader("📜 Agent History")
    all_a = db.get_agent_usernames()
    if role == "supervisor":
        allowed = set()
        for bd in db.get_supervisor_books(username).values():
            allowed.update(bd.get("agents",[]))
        all_a = [a for a in all_a if a in allowed]
    sel  = st.selectbox("Agent", [format_email(a) for a in sorted(all_a)])
    recs = [r for r in db.get_attendance_all() if r["agent"] == sel.split("@")[0]]
    if not recs:
        st.info("No records.")
    else:
        rows = []
        for r in recs:
            pr = parse_reasons(r.get("reason",""))
            rows.append({
                "Date":         r.get("date",""),
                "Book":         r.get("book","—") or "—",
                "Clock In":     r.get("clock_in","") or "—",
                "Clock Out":    r.get("clock_out","") or "—",
                "Late(m)":      safe_int(r.get("late_minutes",0)),
                "Tea Extra":    safe_int(r.get("tea_extra",0)),
                "Lunch Extra":  safe_int(r.get("lunch_extra",0)),
                "Knockoff":     r.get("new_knockoff","") or "16:30",
                "Status":       r.get("status",""),
                "Late Reason":  pr["Late Reason"],
                "Tea Reason":   pr["Tea Reason"],
                "Lunch Reason": pr["Lunch Reason"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Export ────────────────────────────────────────────────────────────────────
elif tab == "export" and role in ("supervisor","admin"):
    st.subheader("💾 Export")
    c1, c2 = st.columns(2)
    with c1: start = st.date_input("From", value=now_sast().date())
    with c2: end   = st.date_input("To",   value=now_sast().date())
    if st.button("Export", type="primary"):
        records = db.get_attendance_range(str(start), str(end))
        if role == "supervisor":
            allowed = set()
            for bd in db.get_supervisor_books(username).values():
                allowed.update(bd.get("agents",[]))
            records = [r for r in records if r["agent"] in allowed]
        if not records:
            st.info("No data.")
        else:
            import io
            rows = []
            for r in records:
                pr = parse_reasons(r.get("reason",""))
                rows.append({**{k: r.get(k,"") for k in [
                    "date","agent","book","clock_in","clock_out",
                    "late_minutes","tea_extra","lunch_extra","new_knockoff","status"]},
                    "Late Reason":  pr["Late Reason"],
                    "Tea Reason":   pr["Tea Reason"],
                    "Lunch Reason": pr["Lunch Reason"],
                })
            df = pd.DataFrame(rows)
            buf = io.BytesIO()
            df.to_excel(buf, index=False, engine="openpyxl")
            st.download_button("📥 Download", buf.getvalue(),
                file_name=f"NICS_{start}_{end}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── Manage Books ──────────────────────────────────────────────────────────────
elif tab == "books" and role in ("supervisor","admin"):
    st.subheader("📚 Manage Books")
    books  = db.get_books() if role == "admin" else db.get_supervisor_books(username)
    all_a  = db.get_agent_usernames()
    cl, cr = st.columns([1,2])
    with cl:
        st.markdown("#### Books")
        sel_book = (st.radio("Select", list(books.keys()),
                             label_visibility="collapsed") if books else None)
        if not books: st.info("No books yet.")
        if role == "admin":
            st.markdown("---")
            nb = st.text_input("New book name")
            if st.button("➕ Create") and nb.strip():
                if nb.strip() not in books:
                    db.upsert_book(nb.strip(),[],[]); st.success("Created")
                    time.sleep(0.4); st.rerun()
                else: st.warning("Already exists.")
            if sel_book and st.button("🗑️ Delete Book"):
                db.delete_book(sel_book); st.success("Deleted")
                time.sleep(0.4); st.rerun()
    with cr:
        if sel_book and sel_book in books:
            bd = books[sel_book]; ba = bd.get("agents",[])
            st.markdown(f"#### {sel_book} ({len(ba)} agents)")
            if ba:
                rs = st.selectbox("Remove agent",
                                  [format_email(a) for a in sorted(ba)], key="rem_ag")
                if st.button("🗑️ Remove from Book"):
                    ru = rs.split("@")[0]
                    db.upsert_book(sel_book, bd.get("supervisors",[]),
                                   [a for a in ba if a != ru])
                    st.success(f"Removed {ru}"); time.sleep(0.4); st.rerun()
            else:
                st.info("No agents yet.")
            ni = [a for a in all_a if a not in ba]
            if ni:
                as_ = st.selectbox("Add agent",
                                   [format_email(a) for a in sorted(ni)], key="add_ag")
                if st.button("➕ Add to Book", type="primary"):
                    au = as_.split("@")[0]
                    db.upsert_book(sel_book, bd.get("supervisors",[]), ba+[au])
                    st.success(f"Added {au}"); time.sleep(0.4); st.rerun()
            if role == "admin":
                st.markdown("---"); st.markdown("**Supervisors:**")
                bs = bd.get("supervisors",[]); all_s = list(auth.SUPERVISORS)
                if bs:
                    rs2 = st.selectbox("Remove sup",
                                       [format_email(s) for s in bs], key="rem_sup")
                    if st.button("🗑️ Remove Supervisor"):
                        ru2 = rs2.split("@")[0]
                        db.upsert_book(sel_book,[s for s in bs if s!=ru2],ba); st.rerun()
                na = [s for s in all_s if s not in bs]
                if na:
                    as2 = st.selectbox("Assign sup",
                                       [format_email(s) for s in na], key="add_sup")
                    if st.button("➕ Assign Supervisor", type="primary"):
                        au2 = as2.split("@")[0]
                        db.upsert_book(sel_book, bs+[au2], ba); st.rerun()

# ── Change Password ───────────────────────────────────────────────────────────
elif tab == "password" and role in ("supervisor","admin"):
    st.subheader("🔑 Change Password")
    pt = (st.selectbox("Change for", ["Admin","Supervisor"])
          if role == "admin" else "Supervisor")
    with st.form("pw"):
        np = st.text_input("New Password", type="password")
        cp = st.text_input("Confirm",      type="password")
        if st.form_submit_button("Update", type="primary"):
            if not np:     st.error("Cannot be empty.")
            elif np != cp: st.error("Passwords don't match.")
            else:
                db.set_setting(
                    "admin_password" if pt=="Admin" else "supervisor_password", np)
                st.success(f"✅ {pt} password updated.")

# ── Admin Panel ───────────────────────────────────────────────────────────────
elif tab == "admin" and role == "admin":
    st.subheader("⚙️ Admin Panel")
    agents = db.get_agents()
    c1, c2 = st.columns([1.2, 2])
    with c1:
        st.markdown("#### Add Agent")
        with st.form("add_f"):
            fn = st.text_input("Full Name", placeholder="e.g. Nokwanda Ntuli")
            un = st.text_input("Username",  placeholder="e.g. nokwandan")
            if st.form_submit_button("➕ Add", type="primary"):
                u = un.strip().replace("@nics.co.za","")
                if not u or not fn.strip():
                    st.error("All fields required.")
                elif u in [a["username"] for a in agents]:
                    st.warning("Already exists.")
                else:
                    db.add_agent(u, fn.strip())
                    st.success(f"✅ {fn} added! Assign to a book via 📚 Manage Books.")
                    time.sleep(0.8); st.rerun()
    with c2:
        st.markdown("#### Registered Agents")
        if agents:
            st.dataframe(
                pd.DataFrame([{"#":i+1,"Email":format_email(a["username"]),
                               "Name":a.get("display_name","")}
                              for i,a in enumerate(agents)]),
                use_container_width=True, hide_index=True)
            st.markdown("---")
            rem = st.selectbox("Remove",
                               [format_email(a["username"]) for a in agents])
            if st.button("🗑️ Remove Agent"):
                ru = rem.split("@")[0]
                if ru in auth.ADMINS:
                    st.error("Cannot remove admin.")
                else:
                    db.remove_agent(ru)
                    st.success(f"Removed {rem}"); time.sleep(0.4); st.rerun()

# ── Fallback ──────────────────────────────────────────────────────────────────
else:
    if role == "agent":
        st.info("👈 Use the sidebar to Clock In, manage breaks, or Clock Out.")
    elif role in ("supervisor","admin"):
        st.session_state.active_tab = "dashboard"; st.rerun()
