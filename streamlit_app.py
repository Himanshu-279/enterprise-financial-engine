"""
streamlit_app.py  —  Enterprise Financial Engine  (Final)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Design  : Original v1 CSS (Bloomberg Terminal · Cyberpunk)
Features: v3 Async Polling + History Tab + Metrics Parser

Compatible with YOUR exact files:
  POST /analyze       → {task_id, status:"queued"}
  GET  /status/{id}   → {status:"Processing|Completed|Failed", result}
  GET  /history       → {history:[{id,filename,query,result,revenue,net_income,created_at}]}
"""

import streamlit as st
import requests
import time, json, re
from datetime import datetime

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Financial Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
# CSS  —  Original Design (100% preserved) + new component classes
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Syne:wght@400;600;700;800&display=swap');

/* ── Root Variables ── */
:root {
    --bg-primary: #0a0d12;
    --bg-secondary: #0f1318;
    --bg-card: #141920;
    --bg-elevated: #1a2030;
    --accent-green: #00ff88;
    --accent-orange: #ff6b35;
    --accent-blue: #4fc3f7;
    --accent-red: #ff4757;
    --accent-gold: #ffd700;
    --text-primary: #e8eaf0;
    --text-secondary: #8892a4;
    --text-dim: #4a5568;
    --border: #1e2a3a;
    --border-bright: #2a3a50;
    --glow-green: 0 0 20px rgba(0, 255, 136, 0.3);
    --glow-orange: 0 0 20px rgba(255, 107, 53, 0.3);
}

/* ── Global Reset ── */
html, body, .stApp {
    background-color: var(--bg-primary) !important;
    font-family: 'Syne', sans-serif;
    color: var(--text-primary);
}

/* ── Hide Streamlit Branding ── */
#MainMenu, footer, .stDeployButton { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-bright); border-radius: 2px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div { padding: 1.5rem 1rem; }

/* ── Sidebar Logo Area ── */
.sidebar-logo {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 1.5rem; padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}
.sidebar-logo-icon {
    width: 44px; height: 44px;
    background: linear-gradient(135deg, var(--accent-green), #00c9ff);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
}
.sidebar-logo-text  { font-size: 0.8rem; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; }
.sidebar-logo-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); }

/* ── Status Badge ── */
.status-badge {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 8px 14px; border-radius: 8px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.78rem;
    font-weight: 600; letter-spacing: 0.05em;
    width: 100%; margin-bottom: 0.5rem;
}
.status-online  { background: rgba(0,255,136,0.1);  border: 1px solid rgba(0,255,136,0.3); color: var(--accent-green); }
.status-offline { background: rgba(255,71,87,0.1);  border: 1px solid rgba(255,71,87,0.3); color: var(--accent-red); }
.status-dot { width: 8px; height: 8px; border-radius: 50%; animation: pulse 2s infinite; }
.dot-green  { background: var(--accent-green); box-shadow: var(--glow-green); }
.dot-red    { background: var(--accent-red); }

/* ── Profile Card ── */
.profile-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1rem; margin-top: 1rem;
}
.profile-label {
    font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase;
    letter-spacing: 0.1em; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.75rem;
}
.profile-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 0; border-bottom: 1px solid var(--border);
}
.profile-row:last-child { border-bottom: none; }
.profile-key { font-size: 0.75rem; color: var(--text-secondary); }
.profile-val { font-size: 0.75rem; color: var(--text-primary); font-weight: 600; font-family: 'JetBrains Mono', monospace; }

/* ── Main Header ── */
.main-header { padding: 2rem 0 1.5rem; border-bottom: 1px solid var(--border); margin-bottom: 1.5rem; }
.main-header-tag   { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--accent-green); letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 0.4rem; }
.main-header-title { font-size: 1.6rem; font-weight: 800; color: var(--text-primary); line-height: 1.2; margin-bottom: 0.3rem; }
.main-header-sub   { font-size: 0.85rem; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]  { background: transparent !important; border-bottom: 1px solid var(--border) !important; gap: 0 !important; padding: 0 !important; }
.stTabs [data-baseweb="tab"]       { background: transparent !important; color: var(--text-secondary) !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem !important; padding: 10px 20px !important; border: none !important; border-bottom: 2px solid transparent !important; transition: all 0.2s !important; }
.stTabs [data-baseweb="tab"]:hover { color: var(--text-primary) !important; }
.stTabs [aria-selected="true"]     { color: var(--accent-orange) !important; border-bottom: 2px solid var(--accent-orange) !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 1.5rem 0 !important; }

/* ── Upload Zone ── */
[data-testid="stFileUploader"] {
    background: var(--bg-card) !important;
    border: 1.5px dashed var(--border-bright) !important;
    border-radius: 12px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--accent-green) !important; }

/* ── Text Area ── */
.stTextArea textarea {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-bright) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
    transition: border-color 0.2s !important;
}
.stTextArea textarea:focus { border-color: var(--accent-green) !important; box-shadow: var(--glow-green) !important; }

/* ── Text Input (URL bar) ── */
.stTextInput input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-bright) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* ── Run Button ── */
.stButton > button {
    background: linear-gradient(135deg, var(--accent-orange), #ff3f7a) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.85rem !important;
    font-weight: 700 !important; letter-spacing: 0.05em !important;
    padding: 0.65rem 1.5rem !important; width: 100% !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 15px rgba(255,107,53,0.3) !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(255,107,53,0.5) !important; }
.stButton > button:active { transform: translateY(0) !important; }
.stButton > button:disabled { opacity: 0.38 !important; transform: none !important; }

/* ── Download Button ── */
.stDownloadButton > button {
    background: var(--bg-elevated) !important; color: var(--text-primary) !important;
    border: 1px solid var(--border-bright) !important; border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.78rem !important;
    padding: 0.4rem 1rem !important; width: auto !important;
}
.stDownloadButton > button:hover { border-color: var(--accent-green) !important; color: var(--accent-green) !important; }

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: var(--bg-card) !important; border-color: var(--border-bright) !important;
    color: var(--text-primary) !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ── Section Labels ── */
.section-label {
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.5rem;
}
.section-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 1rem; }

/* ── Result Container ── */
.result-container {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 14px; padding: 1.5rem; min-height: 300px;
    position: relative; overflow: visible;
    word-wrap: break-word; overflow-wrap: break-word;
}
.result-container::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--accent-green), var(--accent-blue), var(--accent-orange));
}

/* ── Success Alert ── */
.success-alert {
    background: rgba(0,255,136,0.08); border: 1px solid rgba(0,255,136,0.25);
    border-radius: 10px; padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
    color: var(--accent-green); margin-bottom: 1rem;
    display: flex; align-items: center; gap: 10px;
}

/* ── Empty State ── */
.empty-state {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; height: 250px; color: var(--text-dim); gap: 12px;
}
.empty-state-icon { font-size: 2.5rem; opacity: 0.4; }
.empty-state-text { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }

/* ── Debug Cards ── */
.debug-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-left: 3px solid var(--accent-orange);
    border-radius: 10px; padding: 1.2rem 1.5rem; margin-bottom: 1rem;
    transition: border-color 0.2s;
}
.debug-card:hover { border-left-color: var(--accent-green); }
.debug-card-type  { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--accent-orange); text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.4rem; }
.debug-card-title { font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem; }
.debug-card-desc  { font-size: 0.82rem; color: var(--text-secondary); line-height: 1.6; }
.debug-code {
    display: inline-block; background: rgba(79,195,247,0.1); color: var(--accent-blue);
    font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;
    padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(79,195,247,0.2); margin: 2px;
}
/* Bonus card variant */
.debug-card-bonus { border-left-color: var(--accent-green); }
.debug-card-bonus .debug-card-type { color: var(--accent-green); }

/* ── Agent Flow ── */
.agent-flow { display: flex; align-items: stretch; gap: 0; margin: 2rem 0; overflow-x: auto; padding-bottom: 0.5rem; }
.agent-card {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
    padding: 1rem; min-width: 160px; flex: 1; text-align: center; position: relative;
}
.agent-card::after { content: '→'; position: absolute; right: -22px; top: 50%; transform: translateY(-50%); color: var(--text-dim); font-size: 1.2rem; z-index: 1; }
.agent-card:last-child::after { display: none; }
.agent-card + .agent-card { margin-left: 24px; }
.agent-icon { font-size: 1.8rem; margin-bottom: 0.4rem; }
.agent-name { font-size: 0.75rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.2rem; }
.agent-role { font-size: 0.65rem; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; }
.agent-tag  { display: inline-block; margin-top: 0.5rem; padding: 2px 8px; border-radius: 4px; font-size: 0.6rem; font-family: 'JetBrains Mono', monospace; }
.tag-verify  { background: rgba(0,255,136,0.1); color: var(--accent-green); }
.tag-extract { background: rgba(79,195,247,0.1); color: var(--accent-blue); }
.tag-invest  { background: rgba(255,215,0,0.1);  color: var(--accent-gold); }
.tag-risk    { background: rgba(255,71,87,0.1);   color: var(--accent-red); }

/* ── Metrics Row ── */
.metrics-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.metric-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 10px; padding: 0.9rem 1.2rem; flex: 1; min-width: 120px;
}
.metric-label { font-size: 0.65rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.1em; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.3rem; }
.metric-value { font-size: 1.3rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.metric-sub   { font-size: 0.65rem; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; margin-top: 0.1rem; }
.metric-green  { color: var(--accent-green); }
.metric-blue   { color: var(--accent-blue); }
.metric-gold   { color: var(--accent-gold); }
.metric-orange { color: var(--accent-orange); }
.metric-red    { color: var(--accent-red); }

/* ── Stage Tracker (new — fits original style) ── */
.stage-tracker {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 14px; padding: 1.8rem; text-align: center;
    position: relative;
}
.stage-tracker::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--accent-green), var(--accent-blue));
}
.stage-icon  { font-size: 2.2rem; margin-bottom: 0.6rem; }
.stage-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.25rem; }
.stage-sub   { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1.2rem; }
.progress-bar-bg   { background: var(--border); border-radius: 4px; height: 4px; overflow: hidden; margin-bottom: 1rem; }
.progress-bar-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, var(--accent-green), var(--accent-blue)); animation: shimmer 1.5s infinite; }

/* ── Stage Chips ── */
.stage-chips { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; }
.chip-base   { padding: 3px 10px; border-radius: 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; }
.chip-done   { background: rgba(0,255,136,0.12);  color: var(--accent-green); border: 1px solid rgba(0,255,136,0.25); }
.chip-active { background: rgba(79,195,247,0.12); color: var(--accent-blue);  border: 1px solid rgba(79,195,247,0.25); animation: pulse 1.2s infinite; }
.chip-wait   { background: rgba(74,85,104,0.15);  color: var(--text-dim);     border: 1px solid rgba(74,85,104,0.2); }

/* ── History Row ── */
.hist-row {
    display: flex; align-items: center; gap: 12px;
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 0.5rem;
    transition: border-color 0.2s;
}
.hist-row:hover { border-color: var(--border-bright); }
.hist-id   { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--text-dim); min-width: 32px; }
.hist-file { font-size: 0.8rem; color: var(--text-primary); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hist-val  { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; white-space: nowrap; }
.hist-date { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--text-secondary); min-width: 120px; text-align: right; }

/* ── DB Tag ── */
.db-tag {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(79,195,247,0.1); border: 1px solid rgba(79,195,247,0.22);
    border-radius: 5px; padding: 2px 8px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--accent-blue);
}

/* ── Animations ── */
@keyframes pulse   { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.6;transform:scale(0.85)} }
@keyframes shimmer { 0%,100%{opacity:0.6} 50%{opacity:1} }
@keyframes fadeIn  { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }

hr { border-color: var(--border) !important; }
.stSpinner > div { border-top-color: var(--accent-green) !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════
def _init(key, val):
    if key not in st.session_state:
        st.session_state[key] = val

_init("backend_url",    "https://enterprise-financial-engine.onrender.com")
_init("task_id",        None)
_init("poll_status",    None)   # "Processing" | "Completed" | "Failed"
_init("poll_count",     0)
_init("result_text",    None)   # raw CrewAI result string
_init("current_fname",  None)
_init("viewed_record",  None)   # loaded from history
_init("analysis_time",  None)
_init("query_used",     None)


# ═══════════════════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=30, show_spinner=False)
def check_backend_health(url: str) -> bool:
    try:
        return requests.get(f"{url}/", timeout=3).status_code == 200
    except Exception:
        return False

def poll_task(url: str, task_id: str) -> dict:
    """GET /status/{task_id} — no cache, always live."""
    try:
        r = requests.get(f"{url}/status/{task_id}", timeout=5)
        return r.json() if r.status_code == 200 else {"status": "Not Found"}
    except Exception:
        return {"status": "Error"}

@st.cache_data(ttl=8, show_spinner=False)
def fetch_history(url: str) -> list:
    """GET /history → {history: [...]}"""
    try:
        r = requests.get(f"{url}/history", timeout=5)
        if r.status_code == 200:
            return r.json().get("history", [])
    except Exception:
        pass
    try:
        from database import db as _db
        return _db.get_history().data
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# METRICS PARSER
# Priority 1: DB columns (revenue, net_income already extracted)
# Priority 2: Regex on result markdown
# ═══════════════════════════════════════════════════════════════
def parse_metrics(record: dict) -> list:
    """Returns [(label, value, css_class, source), ...]"""
    cards = []

    rev = (record.get("revenue")    or "").strip()
    inc = (record.get("net_income") or "").strip()
    if rev and rev != "N/A":
        cards.append(("💰 Total Revenue",  rev, "metric-green",  "DB column"))
    if inc and inc != "N/A":
        cards.append(("📈 Net Income",     inc, "metric-blue",   "DB column"))

    text = record.get("result") or ""
    already = {c[0] for c in cards}
    extra = [
        ("💧 Free Cash Flow",   r"(?:free\s+cash\s+flow|FCF)[^\$\d]{0,30}\$?\s*([\d,\.]+\s*(?:billion|million|B|M)?)", "metric-gold"),
        ("⚙️ Oper. Income",    r"operating\s+(?:income|profit)[^\$\d]{0,30}\$?\s*([\d,\.]+\s*(?:billion|million|B|M)?)", "metric-orange"),
        ("📌 EPS",              r"(?:\bEPS\b|earnings per share)[^\$\d]{0,15}\$?\s*([\d,\.]+)", "metric-green"),
    ]
    for lbl, pat, cls in extra:
        if lbl not in already:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                cards.append((lbl, m.group(1).strip(), cls, "parsed"))

    return cards


# ═══════════════════════════════════════════════════════════════
# RESULT RENDERER  (shared by Tab 1 + Tab 2)
# ═══════════════════════════════════════════════════════════════
def render_result(record: dict, elapsed: float = None, from_db: bool = False):
    fname  = record.get("filename") or "—"
    result = record.get("result")   or ""
    db_tag = '<span class="db-tag" style="margin-left:8px;">🗄️ SQLite</span>' if from_db else ""
    time_str = f" · ⏱ {elapsed:.0f}s" if elapsed else ""

    st.markdown(f"""
    <div class="success-alert">
        ✅ &nbsp;<strong>{fname}</strong>{time_str} {db_tag}
    </div>
    """, unsafe_allow_html=True)

    # ── Metrics Cards ─────────────────────────────────────────
    cards = parse_metrics(record)
    if cards:
        st.markdown('<div class="section-label">📊 Extracted Financial Metrics</div>',
                    unsafe_allow_html=True)
        html = '<div class="metrics-row">'
        for lbl, val, cls, src in cards:
            html += f"""
            <div class="metric-card">
                <div class="metric-label">{lbl}</div>
                <div class="metric-value {cls}">{val}</div>
                <div class="metric-sub">{src}</div>
            </div>"""
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    # ── Full Report ───────────────────────────────────────────
    st.markdown('<div class="section-label">📝 Full Analysis Report</div>',
                unsafe_allow_html=True)
    st.markdown(result)
    st.markdown("<br>", unsafe_allow_html=True)

    report_data = {
        "filename":  fname,
        "query":     record.get("query", ""),
        "analysis":  result,
        "revenue":   record.get("revenue", "N/A"),
        "net_income":record.get("net_income", "N/A"),
        "timestamp": datetime.now().isoformat(),
    }
    st.download_button(
        label="📥  Download Report (JSON)",
        data=json.dumps(report_data, indent=2, default=str),
        file_name=f"report_{str(record.get('id','x'))}_{fname[:10]}.json",
        mime="application/json",
    )


# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="sidebar-logo-icon">📊</div>
        <div>
            <div class="sidebar-logo-title">FinEngine</div>
            <div class="sidebar-logo-text">v3.0 · Async + SQLite</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">System Status</div>', unsafe_allow_html=True)
    new_url = st.text_input("API Endpoint", value=st.session_state.backend_url,
                             label_visibility="collapsed", key="url_inp")
    if new_url != st.session_state.backend_url:
        st.session_state.backend_url = new_url
        check_backend_health.clear()
        fetch_history.clear()

    URL = st.session_state.backend_url
    is_online = check_backend_health(URL)

    if is_online:
        st.markdown('<div class="status-badge status-online"><div class="status-dot dot-green"></div>Backend: ONLINE</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge status-offline"><div class="status-dot dot-red"></div>Backend: OFFLINE</div>', unsafe_allow_html=True)
        st.warning("⚠️ Backend offline — Render instance might be sleeping, wait 50 seconds.", icon=None)

    st.markdown('<div style="margin-top:0.4rem;"><span class="db-tag">🗄️ financial_data.db</span></div>',
                unsafe_allow_html=True)

    # ── History Dropdown ──────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">📂 Load Past Report</div>', unsafe_allow_html=True)

    history = fetch_history(URL)
    if history:
        opts = {}
        for rec in history:
            fname   = (rec.get("filename") or "?")[:20]
            created = (rec.get("created_at") or "")[:10]
            rev     = rec.get("revenue") or "—"
            opts[f"#{rec['id']} · {fname} · {rev}"] = rec

        sel = st.selectbox("Report", ["— select —"] + list(opts.keys()),
                           label_visibility="collapsed", key="hist_dd")
        if sel != "— select —":
            if st.button("📂  Load Report", use_container_width=True, key="load_btn"):
                st.session_state.viewed_record = opts[sel]
                st.session_state.result_text   = None
                st.session_state.task_id       = None
                st.session_state.poll_status   = None
                fetch_history.clear()
                st.rerun()
    else:
        st.caption("No records yet.")

    # ── Session Stats ─────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">Session Stats</div>', unsafe_allow_html=True)
    sc1, sc2 = st.columns(2)
    with sc1:
        st.metric("Analyses", 1 if st.session_state.result_text else 0)
    with sc2:
        t = st.session_state.analysis_time
        st.metric("Last Run", f"{t:.0f}s" if t else "—")

    # ── Profile Card ──────────────────────────────────────────
    st.markdown("""
    <div class="profile-card">
        <div class="profile-label">👤 Developer Profile</div>
        <div class="profile-row"><span class="profile-key">Role</span> <span class="profile-val">AI Intern Candidate</span></div>
        <div class="profile-row"><span class="profile-key">Batch</span><span class="profile-val">2026</span></div>
        <div class="profile-row"><span class="profile-key">Queue</span><span class="profile-val">BackgroundTasks</span></div>
        <div class="profile-row"><span class="profile-key">DB</span>   <span class="profile-val">SQLite</span></div>
        <div class="profile-row"><span class="profile-key">UI</span>   <span class="profile-val">Streamlit</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Session", use_container_width=True, key="clear_btn"):
        for k in ["task_id","poll_status","poll_count","result_text",
                  "current_fname","viewed_record","analysis_time","query_used"]:
            st.session_state[k] = None
        st.session_state.poll_count = 0
        check_backend_health.clear()
        fetch_history.clear()
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# MAIN HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<div class="main-header">
    <div class="main-header-tag">⚡ Async Queue · SQLite · Multi-Agent CrewAI</div>
    <div class="main-header-title">Enterprise Financial Analysis Engine</div>
    <div class="main-header-sub">Powered by Groq · LLaMA 4 · 4-Agent Sequential Pipeline · Real-time Stage Tracking</div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "📄  Document Analysis",
    "🕐  Job History",
    "🐛  Debug Report",
    "⚙️  Architecture",
])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1 — DOCUMENT ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab1:
    col_left, col_right = st.columns([1, 1.1], gap="large")

    # ── LEFT: Upload + Query ──────────────────────────────────
    with col_left:
        st.markdown('<div class="section-label">Upload Financial Report</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Choose a PDF file", type=["pdf"],
            help="Upload annual reports, 10-K, quarterly filings, balance sheets etc.",
            key="pdf_uploader"
        )

        st.markdown('<div class="section-label" style="margin-top:1rem;">Custom Analysis Query</div>',
                    unsafe_allow_html=True)
        query_options = [
            "Detailed analysis of revenue growth and profitability trends",
            "Identify liquidity risks and cash flow concerns",
            "Investment opportunity assessment with valuation metrics",
            "Comprehensive risk factor analysis and mitigation strategies",
            "What is the net profit?",
            "Custom query...",
        ]
        selected_query = st.selectbox("Select a preset query", query_options, label_visibility="collapsed")
        user_query = st.text_area(
            "Query (editable)",
            value="" if selected_query == "Custom query..." else selected_query,
            height=110, label_visibility="collapsed",
            placeholder="e.g. Analyze Q2-2025 Net Income trends vs industry peers..."
        )

        is_polling  = (st.session_state.poll_status == "Processing")
        run_disabled = not uploaded_file or not user_query.strip() or not is_online or is_polling

        if   not is_online:  st.markdown('<p style="font-family:JetBrains Mono;font-size:0.7rem;color:#ff4757;margin-top:0.5rem;">⚠️ Backend offline — start FastAPI first</p>', unsafe_allow_html=True)
        elif not uploaded_file: st.markdown('<p style="font-family:JetBrains Mono;font-size:0.7rem;color:#8892a4;margin-top:0.5rem;">← Upload a PDF to enable analysis</p>', unsafe_allow_html=True)
        elif is_polling:     st.markdown('<p style="font-family:JetBrains Mono;font-size:0.7rem;color:#4fc3f7;margin-top:0.5rem;">⏳ Analysis running in background…</p>', unsafe_allow_html=True)

        run_clicked = st.button("🚀  Run Analysis", disabled=run_disabled, use_container_width=True)

        # ── STEP A: POST /analyze → task_id instantly ─────────
        if run_clicked and uploaded_file:
            try:
                start_t = time.time()
                resp = requests.post(
                    f"{URL}/analyze",
                    files={"file": (uploaded_file.name, uploaded_file.read(), "application/pdf")},
                    data={"query": user_query.strip()},
                    timeout=15,
                )
                resp.raise_for_status()
                body = resp.json()

                st.session_state.task_id       = body.get("task_id")
                st.session_state.poll_status   = "Processing"
                st.session_state.poll_count    = 0
                st.session_state.result_text   = None
                st.session_state.current_fname = uploaded_file.name
                st.session_state.viewed_record = None
                st.session_state.query_used    = user_query.strip()
                st.session_state._start_t      = start_t
                fetch_history.clear()
                st.rerun()

            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to backend. Is FastAPI running?")
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out.")
            except requests.exceptions.HTTPError as e:
                st.error(f"❌ API Error {e.response.status_code}: {e.response.text[:200]}")
            except Exception as e:
                st.error(f"❌ {str(e)}")

    # ── RIGHT: Polling + Result ───────────────────────────────
    with col_right:
        st.markdown('<div class="section-label">AI Generation Results</div>', unsafe_allow_html=True)

        # ── STEP B: Poll every 3s until Completed/Failed ──────
        if st.session_state.task_id and st.session_state.poll_status == "Processing":
            data   = poll_task(URL, st.session_state.task_id)
            status = data.get("status", "Processing")
            st.session_state.poll_count += 1

            if status == "Completed":
                elapsed = time.time() - getattr(st.session_state, "_start_t", time.time())
                st.session_state.poll_status   = "Completed"
                st.session_state.result_text   = data.get("result", "")
                st.session_state.analysis_time = elapsed
                fetch_history.clear()

            elif status == "Failed":
                st.session_state.poll_status = "Failed"
                st.error(f"❌ Analysis failed: {data.get('error', 'Unknown error')}")

            else:
                # ── Stage Tracker ─────────────────────────────
                stages = [
                    ("🔍 Verifier",    "###VERIFIER — Validating document"),
                    ("📊 Oracle",      "###ORACLE — Extracting metrics"),
                    ("💹 Strategy",    "###STRATEGY — Building thesis"),
                    ("⚠️ Risk Engine", "###RISK — Worst-case analysis"),
                ]
                idx  = min(st.session_state.poll_count // 3, 3)
                pct  = min(8 + idx * 23, 88)

                chips_html = ""
                for i, (n, _) in enumerate(stages):
                    if   i < idx: chips_html += f'<span class="chip-base chip-done">✓ {n}</span>'
                    elif i == idx: chips_html += f'<span class="chip-base chip-active">⟳ {n}</span>'
                    else:          chips_html += f'<span class="chip-base chip-wait">{n}</span>'

                st.markdown(f"""
                <div class="stage-tracker">
                    <div class="stage-icon">🤖</div>
                    <div class="stage-title">{stages[idx][1]}</div>
                    <div class="stage-sub">
                        task_id: {st.session_state.task_id[:26]}…<br>
                        <span style="color:var(--text-dim)">Poll #{st.session_state.poll_count} · auto-refresh every 3s</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width:{pct}%"></div>
                    </div>
                    <div class="stage-chips">{chips_html}</div>
                </div>
                """, unsafe_allow_html=True)

                time.sleep(3)
                st.rerun()

        # ── Show completed result (fresh run) ─────────────────
        if st.session_state.result_text and st.session_state.poll_status == "Completed":
            render_result({
                "id":         st.session_state.task_id or "—",
                "filename":   st.session_state.current_fname or "—",
                "query":      st.session_state.query_used or "",
                "result":     st.session_state.result_text,
                "revenue":    "N/A",
                "net_income": "N/A",
            }, elapsed=st.session_state.analysis_time, from_db=False)

        # ── Show history-loaded result ─────────────────────────
        elif st.session_state.viewed_record:
            st.markdown("""
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
            color:var(--accent-blue);margin-bottom:0.75rem;">
                📂 Loaded from SQLite — no CrewAI re-run
            </div>""", unsafe_allow_html=True)
            render_result(st.session_state.viewed_record, from_db=True)

        # ── Empty state ───────────────────────────────────────
        elif st.session_state.poll_status != "Processing":
            st.markdown("""
            <div class="result-container">
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <div class="empty-state-text">Upload a PDF and run analysis</div>
                    <div class="empty-state-text" style="color:#2a3a50;font-size:0.7rem;">
                        Results will appear here · Or load a past report from the sidebar
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2 — JOB HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab2:
    st.markdown("""
    <h2 style="font-size:1.5rem;font-weight:800;color:#e8eaf0;margin-bottom:0.3rem;">🕐 Analysis History</h2>
    <p style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#8892a4;margin-bottom:1.2rem;">
        All records from <span class="db-tag">🗄️ financial_data.db</span>
    </p>
    """, unsafe_allow_html=True)

    history = fetch_history(URL)

    if history:
        total   = len(history)
        has_rev = sum(1 for r in history if (r.get("revenue")    or "N/A") != "N/A")
        has_inc = sum(1 for r in history if (r.get("net_income") or "N/A") != "N/A")

        st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-card">
                <div class="metric-label">Total Records</div>
                <div class="metric-value metric-green">{total}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">With Revenue</div>
                <div class="metric-value metric-blue">{has_rev}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">With Net Income</div>
                <div class="metric-value metric-gold">{has_inc}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">DB</div>
                <div class="metric-value metric-orange" style="font-size:0.9rem;">SQLite</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-label">All Records (newest first)</div>', unsafe_allow_html=True)

        for rec in history:
            rid     = str(rec.get("id", ""))
            fname   = rec.get("filename", "?")
            rev     = rec.get("revenue",    "N/A") or "N/A"
            inc     = rec.get("net_income", "N/A") or "N/A"
            created = (rec.get("created_at") or "")[:16].replace("T", " ")

            st.markdown(f"""
            <div class="hist-row">
                <div class="hist-id">#{rid}</div>
                <div class="hist-file">📄 {fname}</div>
                <div class="hist-val" style="color:var(--accent-green);">💰 {rev}</div>
                <div class="hist-val" style="color:var(--accent-blue);">📈 {inc}</div>
                <div class="hist-date">{created}</div>
            </div>
            """, unsafe_allow_html=True)

            if rec.get("result"):
                with st.expander(f"📊 View Full Report · #{rid} · {fname}"):
                    cards = parse_metrics(rec)
                    if cards:
                        cols = st.columns(min(len(cards), 5))
                        for col, (lbl, val, _, _src) in zip(cols, cards):
                            col.metric(lbl, val)
                        st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(rec.get("result", ""))
                    st.download_button(
                        "📥 Download JSON",
                        data=json.dumps(rec, indent=2, default=str),
                        file_name=f"report_{rid}_{fname[:10]}.json",
                        mime="application/json",
                        key=f"dl_{rid}",
                    )
    else:
        st.markdown("""
        <div class="result-container">
            <div class="empty-state">
                <div class="empty-state-icon">🕐</div>
                <div class="empty-state-text">No records in financial_data.db yet</div>
                <div class="empty-state-text" style="color:#2a3a50;font-size:0.7rem;">Run your first analysis to populate history</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if st.button("🔄 Refresh History", key="ref_h"):
        fetch_history.clear()
        st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3 — DEBUG REPORT  (original design preserved)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab3:
    st.markdown("""
    <h2 style="font-size:1.5rem;font-weight:800;color:#e8eaf0;margin-bottom:0.3rem;">🐛 Bugs Fixed in the Challenge</h2>
    <p style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#8892a4;margin-bottom:1.5rem;">
        Detailed breakdown of all deterministic bugs, prompt inefficiencies, and bonus features.
    </p>
    """, unsafe_allow_html=True)

    bugs = [
        {
            "type": "Deterministic Bug #1", "file": "tools.py", "bonus": False,
            "title": "PDF File Path Not Handled Correctly",
            "desc": "The FinancialDocumentTool's _run() method received raw path strings with quotes and spaces. Added .strip().replace() cleaning and os.path.exists() validation before reading.",
            "fix": "path.strip().replace(\"'\", \"\")",
        },
        {
            "type": "Deterministic Bug #2", "file": "tools.py", "bonus": False,
            "title": "Token Limit Exceeded — Context Window Crash",
            "desc": "PdfReader was reading ALL pages and sending unlimited text to the LLM, causing context window overflow. Fixed by slicing to first 8 pages and capping output at 8000 characters.",
            "fix": "reader.pages[:8]  →  full_report[:8000]",
        },
        {
            "type": "Deterministic Bug #3", "file": "agents.py", "bonus": False,
            "title": "Class Passed Instead of Instance to tools=[]",
            "desc": "In agents.py, tools were passed as class references (FinancialDocumentTool) instead of instantiated objects. This caused AttributeError at runtime.",
            "fix": "tools=[FinancialDocumentTool()]  — instance, not class",
        },
        {
            "type": "Inefficient Prompt #1", "file": "agents.py", "bonus": False,
            "title": "Agents Instructed to Hallucinate Financial Data",
            "desc": "Original backstories told agents to 'make up investment advice' and 'fabricate URLs'. All backstories rewritten to strictly extract real numbers and refuse analysis when data unavailable.",
            "fix": "Rewritten backstories: 'NEVER speak without extracted real data'",
        },
        {
            "type": "Inefficient Prompt #2", "file": "task.py", "bonus": False,
            "title": "Tasks Encouraged Contradictions and Fabrication",
            "desc": "Tasks told agents to 'include contradictory strategies' and 'add fake research'. Rewritten with strict ###VERIFIER / ###ORACLE / ###STRATEGY / ###RISK headers for deterministic parsing.",
            "fix": "Structured output headers + strict data-only task descriptions",
        },
        {
            "type": "Bonus: Async Queue", "file": "main.py", "bonus": True,
            "title": "Synchronous Blocking — User Frozen for 60s+",
            "desc": "Original POST /analyze blocked until CrewAI finished. Now uses BackgroundTasks — POST returns task_id instantly, Streamlit polls /status/{task_id} every 3 seconds.",
            "fix": "BackgroundTasks.add_task(process_worker) → {task_id} returned instantly",
        },
        {
            "type": "Bonus: SQLite DB", "file": "database.py", "bonus": True,
            "title": "No Persistence — Results Lost on Restart",
            "desc": "DatabaseManager saves every analysis to financial_data.db with auto-extracted revenue and net_income columns via regex. Full history survives restarts.",
            "fix": "db.save_analysis() → financial_analysis table · revenue + net_income columns",
        },
        {
            "type": "Bonus: Metrics Parser", "file": "streamlit_app.py", "bonus": True,
            "title": "Raw Markdown Only — No Structured Financial Data",
            "desc": "parse_metrics() first checks DB columns (revenue, net_income already extracted by database.py), then falls back to regex on the result markdown to find FCF, EPS, etc.",
            "fix": "DB columns priority → regex fallback → st.metric cards",
        },
        {
            "type": "Bonus: History Sidebar", "file": "streamlit_app.py", "bonus": True,
            "title": "No Way to Reload Past Reports Without Re-Running CrewAI",
            "desc": "GET /history → sidebar dropdown with all records. Clicking 'Load Report' fetches from SQLite directly and displays result with metrics — zero CrewAI re-run.",
            "fix": "fetch_history() → dropdown → direct record render → no agents re-run",
        },
    ]

    for bug in bugs:
        bonus_class = "debug-card-bonus" if bug["bonus"] else ""
        type_color  = "var(--accent-green)" if bug["bonus"] else "var(--accent-orange)"
        st.markdown(f"""
        <div class="debug-card {bonus_class}">
            <div class="debug-card-type" style="color:{type_color};">
                {bug['type']} · <span style="color:var(--text-secondary)">{bug['file']}</span>
            </div>
            <div class="debug-card-title">{bug['title']}</div>
            <div class="debug-card-desc">{bug['desc']}</div>
            <div style="margin-top:0.6rem;">
                <span class="debug-code">Fix: {bug['fix']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="📥  Download Debug Report (JSON)",
        data=json.dumps({"bugs_fixed": bugs, "generated_at": datetime.now().isoformat()}, indent=2),
        file_name="debug_report.json",
        mime="application/json",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 4 — ARCHITECTURE  (original design + updated content)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab4:
    st.markdown("""
    <h2 style="font-size:1.5rem;font-weight:800;color:#e8eaf0;margin-bottom:0.3rem;">⚙️ System Architecture</h2>
    <p style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#8892a4;margin-bottom:1.5rem;">
        CrewAI 4-Agent Pipeline · Groq LLaMA-4 · FastAPI BackgroundTasks · SQLite
    </p>
    """, unsafe_allow_html=True)

    # Metrics
    st.markdown("""
    <div class="metrics-row">
        <div class="metric-card">
            <div class="metric-label">Total Agents</div>
            <div class="metric-value metric-green">4</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Pipeline Tasks</div>
            <div class="metric-value metric-blue">4</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Queue</div>
            <div class="metric-value metric-gold" style="font-size:0.85rem;">BG Tasks</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Database</div>
            <div class="metric-value metric-orange" style="font-size:0.85rem;">SQLite</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">LLM</div>
            <div class="metric-value metric-green" style="font-size:0.75rem;">Groq LLaMA-4</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Agent Flow (original design)
    st.markdown("""
    <div class="agent-flow">
        <div class="agent-card">
            <div class="agent-icon">🔍</div>
            <div class="agent-name">Verifier</div>
            <div class="agent-role">Doc Specialist</div>
            <span class="agent-tag tag-verify">###VERIFIER</span>
        </div>
        <div class="agent-card">
            <div class="agent-icon">📊</div>
            <div class="agent-name">Financial Analyst</div>
            <div class="agent-role">Wall St. Oracle</div>
            <span class="agent-tag tag-extract">###ORACLE</span>
        </div>
        <div class="agent-card">
            <div class="agent-icon">💹</div>
            <div class="agent-name">Inv. Advisor</div>
            <div class="agent-role">Growth Guru</div>
            <span class="agent-tag tag-invest">###STRATEGY</span>
        </div>
        <div class="agent-card">
            <div class="agent-icon">⚠️</div>
            <div class="agent-name">Risk Assessor</div>
            <div class="agent-role">Chaos Expert</div>
            <span class="agent-tag tag-risk">###RISK</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Stack cards
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("""
        <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:1.2rem;">
            <div class="section-label" style="margin-bottom:0.8rem;">Backend Stack</div>
            <div class="profile-row"><span class="profile-key">Framework</span> <span class="profile-val">FastAPI + Uvicorn</span></div>
            <div class="profile-row"><span class="profile-key">Queue</span>     <span class="profile-val">BackgroundTasks (built-in)</span></div>
            <div class="profile-row"><span class="profile-key">Agent System</span><span class="profile-val">CrewAI · Sequential</span></div>
            <div class="profile-row"><span class="profile-key">LLM</span>       <span class="profile-val">Groq / LLaMA-4-Scout</span></div>
            <div class="profile-row"><span class="profile-key">PDF Parser</span><span class="profile-val">PyPDF2</span></div>
            <div class="profile-row"><span class="profile-key">Database</span>  <span class="profile-val">SQLite · financial_data.db</span></div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:1.2rem;">
            <div class="section-label" style="margin-bottom:0.8rem;">Frontend Stack</div>
            <div class="profile-row"><span class="profile-key">UI Framework</span> <span class="profile-val">Streamlit 1.x</span></div>
            <div class="profile-row"><span class="profile-key">Polling</span>      <span class="profile-val">GET /status · 3s interval</span></div>
            <div class="profile-row"><span class="profile-key">Metrics</span>      <span class="profile-val">DB columns + regex parser</span></div>
            <div class="profile-row"><span class="profile-key">Caching</span>      <span class="profile-val">@st.cache_data</span></div>
            <div class="profile-row"><span class="profile-key">Theming</span>      <span class="profile-val">Custom CSS · Bloomberg Dark</span></div>
            <div class="profile-row"><span class="profile-key">Fonts</span>        <span class="profile-val">Syne + JetBrains Mono</span></div>
        </div>
        """, unsafe_allow_html=True)

    # Data flow
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:1.5rem;">
        <div class="section-label" style="margin-bottom:1rem;">Async Data Flow</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#8892a4;line-height:2.3;">
            <span style="color:var(--accent-green)">① User</span> uploads PDF + query → Streamlit POST /analyze<br>
            <span style="color:var(--accent-blue)">② FastAPI</span> saves PDF → task_updates[task_id]="Processing" →
            <strong style="color:var(--text-primary)">returns {task_id} instantly</strong><br>
            <span style="color:var(--accent-gold)">③ BackgroundTasks</span> .add_task(process_worker) → non-blocking thread<br>
            <span style="color:var(--accent-orange)">④ process_worker</span> → Verifier [###VERIFIER] → Oracle [###ORACLE] → Advisor [###STRATEGY] → Risk [###RISK]<br>
            <span style="color:var(--accent-green)">⑤ db.save_analysis()</span> → financial_data.db · auto-extracts revenue + net_income<br>
            <span style="color:var(--accent-blue)">⑥ Streamlit polls</span> GET /status/{task_id} every 3s → Stage Tracker chips animate<br>
            <span style="color:var(--accent-gold)">⑦ GET /history</span> → sidebar dropdown → direct record load → 0 re-runs
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🚀 Run — 2 Terminals Only"):
        st.code("""
# Install
pip install fastapi uvicorn crewai streamlit requests PyPDF2 python-dotenv

# .env
GROQ_API_KEY=your_groq_key_here

# Terminal 1 — Backend
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
streamlit run streamlit_app.py
# Open: http://localhost:8501
        """, language="bash")
