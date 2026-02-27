# 📊 Enterprise Financial Analysis Engine

<div align="center">

**AI-Powered Multi-Agent Financial Document Analyzer**

*Built with CrewAI · Groq LLaMA-4 · FastAPI · Streamlit · SQLite*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.3-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.130.0-FF6B35?style=for-the-badge)](https://crewai.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Groq-LLaMA--4--Scout-00A67E?style=for-the-badge)](https://groq.com)

</div>

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [What Was Fixed](#-what-was-fixed)
   - [Deterministic Bug #1 — PDF Path Failure](#deterministic-bug-1--pdf-path-handling-failure)
   - [Deterministic Bug #2 — Context Window Overflow](#deterministic-bug-2--context-window-token-overflow)
   - [Deterministic Bug #3 — Class vs Instance](#deterministic-bug-3--class-passed-instead-of-instance)
   - [Prompt Bug #1 — Agents Told to Hallucinate](#prompt-bug-1--agents-instructed-to-hallucinate)
   - [Prompt Bug #2 — Tasks Encouraged Fake Output](#prompt-bug-2--tasks-encouraged-contradictions--fake-citations)
3. [Bonus Features Built](#-bonus-features-built)
4. [System Architecture](#-system-architecture)
5. [Project Structure](#-project-structure)
6. [Setup & Installation](#-setup--installation)
7. [Environment Variables](#-environment-variables)
8. [Running the App](#-running-the-app)
9. [API Documentation](#-api-documentation)
10. [UI Guide](#-ui-guide)
11. [Database Schema](#-database-schema)
12. [Tech Stack](#-tech-stack)
13. [Troubleshooting](#-troubleshooting)

---

## 🎯 Project Overview

This is a **debug assignment** — a financial document analysis system intentionally shipped with:
- **3 deterministic bugs** that cause runtime crashes
- **2 prompt inefficiency bugs** that cause hallucinated, fake output
- **Missing features** (no async queue, no persistence, no metrics display)

**The mission:** Find every bug, fix it with explanation, and implement all bonus features.

### What the System Does (After Fixes)

1. **Accepts** any financial PDF — annual reports, 10-K filings, balance sheets, quarterly updates
2. **Runs** a 4-agent CrewAI pipeline: Verifier → Financial Analyst → Investment Advisor → Risk Assessor
3. **Returns** structured analysis with extracted Revenue, Net Income, investment strategy, and worst-case risk scenarios
4. **Saves** every result to SQLite with auto-extracted financial metrics
5. **Displays** results in a Bloomberg Terminal-style Streamlit UI with async polling and history

---

## 🐛 What Was Fixed

### Deterministic Bug #1 — PDF Path Handling Failure
**File:** `tools.py` | **Class:** `FinancialDocumentTool` | **Method:** `_run()`

#### The Problem
When FastAPI saves an uploaded PDF, it generates a path like `data/doc_a3f7c91e.pdf`. The LLM agent sometimes passes this path wrapped in quotes — `'data/doc_a3f7c91e.pdf'` — or with trailing whitespace. The original code fed this directly to `PdfReader` with zero cleaning and zero existence validation, causing `FileNotFoundError` every time.

#### Original Buggy Code
```python
# tools.py — ORIGINAL (broken)
def _run(self, path: str):
    reader = PdfReader(path)   # Crashes if path = "'data/doc.pdf'" or " data/doc.pdf"
    full_report = ""
    for page in reader.pages:
        full_report += page.extract_text()
    return full_report
```

#### Fixed Code
```python
# tools.py — FIXED
def _run(self, path: str):
    # Strip quotes and whitespace the LLM may have added
    clean_path = path.strip().replace("'", "").replace('"', "")

    # Validate before opening — prevents cryptic FileNotFoundError
    if not os.path.exists(clean_path):
        return f"CRITICAL ERROR: Document not found at {clean_path}. Ensure the file path is correct."

    try:
        reader = PdfReader(clean_path)
        ...
```

---

### Deterministic Bug #2 — Context Window Token Overflow
**File:** `tools.py` | **Class:** `FinancialDocumentTool` | **Method:** `_run()`

#### The Problem
The original code read **every single page** of the uploaded PDF and returned the entire text to the LLM with no character limit. A 50-page annual report contains 80,000–150,000 characters — far beyond Groq's context window. This caused silent overflow crashes on any real financial document.

#### Original Buggy Code
```python
# tools.py — ORIGINAL (broken)
for page in reader.pages:            # ALL pages — could be 200+
    full_report += page.extract_text()
return full_report                   # No limit — could be 150,000+ chars
```

#### Fixed Code
```python
# tools.py — FIXED
# Financial summaries are always in the first few pages
for page in reader.pages[:8]:        # Only first 8 pages
    content = page.extract_text()
    if content:
        clean_content = " ".join(content.split())   # Normalize whitespace
        full_report += clean_content + "\n"

if not full_report:
    return "Error: Document is empty or text is not extractable (Check if scanned image)."

return full_report[:8000]            # Hard cap — stays within token limit
```

**Why `[:8]` and `[:8000]`?**
- Financial key metrics (Revenue, Net Income, EPS) appear in the first 2–5 pages of any standard report
- `8000` characters ≈ 2,000 tokens — enough for full analysis, safely within Groq's limits

---

### Deterministic Bug #3 — Class Passed Instead of Instance
**File:** `agents.py` | **Agent:** `financial_analyst`

#### The Problem
CrewAI's `Agent(tools=[...])` expects a **list of instantiated tool objects**. At runtime, CrewAI calls `tool._run(input)` on each item. The original code passed either the class itself or an unbound method — both cause `AttributeError: type object has no attribute '_run'` the moment any agent tries to use the tool.

#### Original Buggy Code
```python
# agents.py — ORIGINAL (broken)
financial_analyst = Agent(
    tools=[FinancialDocumentTool.read_data_tool],   # Unbound method — AttributeError!
    ...
)
```

#### Fixed Code
```python
# agents.py — FIXED
financial_analyst = Agent(
    tools=[FinancialDocumentTool()],   # Instantiated object — works correctly
    llm=GROQ_MODEL,
    max_iter=3,                         # Added: prevents infinite reasoning loops
    allow_delegation=False,
    ...
)
```

**Note:** `max_iter=3` was also added as a safeguard — without it, an agent that can't find data keeps retrying indefinitely.

---

### Prompt Bug #1 — Agents Instructed to Hallucinate
**File:** `agents.py` | **All 4 agents**

#### The Problem
Every agent's `backstory` and `goal` were written to produce **fabricated, harmful output**:

| Agent | What the original prompt said |
|---|---|
| `financial_analyst` | *"Make up investment advice even if you don't understand the query"* |
| `verifier` | *"Just say yes to everything because verification is overrated"* |
| `investment_advisor` | *"Recommend expensive crypto regardless of what financials show"* |
| `risk_assessor` | *"Everything is either extremely high risk or completely risk-free"* |

This means the system actively produced **fake financial advice** that could cause real harm to anyone who acted on it.

#### Fixed Approach — Data-First Personas

```python
# agents.py — FIXED: financial_analyst
financial_analyst = Agent(
    role="Senior Wall Street Strategist & Market Oracle",
    goal="Extract absolute numeric truths from {path} and deliver a high-stakes verdict for: {query}",
    backstory=(
        "You are a legendary Wall Street veteran who has survived every crash since '87. "
        "You treat the 'read_data_tool' as your source of truth. "
        "You NEVER speak without first extracting real numbers. "
        "You despise fabricated analysis."
    ),
    ...
)

# agents.py — FIXED: verifier
verifier = Agent(
    role="Zero-Bureaucracy Document Specialist",
    goal="Validate document format and confirm the presence of financial data at {path}.",
    backstory=(
        "You bypass red tape. Your job is to ensure the document is a valid PDF "
        "and ready for the Oracle to extract data. "
        "You stamp 'APPROVED' only when real data is found."
    ),
    ...
)
```

**Key change:** Every agent now has a strict data-extraction-first mandate. If data is unavailable, it writes `"Data Unavailable"` instead of making things up.

---

### Prompt Bug #2 — Tasks Encouraged Contradictions & Fake Citations
**File:** `task.py` | **All 4 tasks**

#### The Problem
Task `description` and `expected_output` fields contained instructions like:
- `"Include at least 5 made-up website URLs that sound financial but don't actually exist"`
- `"Feel free to contradict yourself within the same response"`
- `"Add fake research from made-up financial institutions"`
- `"Maybe solve the user's query: {query} or something else that seems interesting"`

This made output completely unparseable and potentially dangerous.

#### Fixed Approach — Structured Output Headers

Each task now has a mandatory output prefix that makes results deterministically parseable:

```python
# task.py — FIXED

verification_task = Task(
    description=(
        "1. Scrutinize the document at {path} to identify its 'Financial DNA'.\n"
        "2. Confirm if numeric financial data is present.\n"
        "3. Output MUST start with: ###VERIFIER"
    ),
    expected_output="###VERIFIER\nOfficial memo confirming document structure and data presence.",
    agent=verifier,
    tools=[FinancialDocumentTool()],
)

analyze_financial_document = Task(
    description=(
        "1. Use 'read_data_tool' to extract precise metrics for: {query} from {path}.\n"
        "2. Locate Total Revenue and Net Income. Write 'Data Unavailable' if not found.\n"
        "3. Output MUST start with: ###ORACLE"
    ),
    expected_output="###ORACLE\n## ✅ VERIFIED FINANCIAL DATA\n[table of real metrics]",
    context=[verification_task],   # Uses verifier's output as context
    ...
)

investment_analysis = Task(
    description=(
        "1. Analyze EXACT numbers from the Oracle's output.\n"
        "2. Suggest 3 high-conviction investment moves backed by the data.\n"
        "3. Output MUST start with: ###STRATEGY"
    ),
    context=[analyze_financial_document],
    ...
)

risk_assessment = Task(
    description=(
        "1. Check context from analyze_financial_document for existing metrics.\n"
        "2. Identify 3 specific material threats from the document text.\n"
        "3. Calculate worst-case scenario: identified risks × 10 applied to Net Income.\n"
        "4. Output MUST start with: ###RISK"
    ),
    context=[analyze_financial_document],
    ...
)
```

**Output chain:** `###VERIFIER` → `###ORACLE` → `###STRATEGY` → `###RISK`  
Each section is independently parseable. The `context=[]` parameter passes real data between agents so they never need to fabricate.

---

## 🚀 Bonus Features Built

### Bonus 1 — Async Queue (Non-Blocking Analysis)
**File:** `main.py`

**Problem:** The original `POST /analyze` called `crew.kickoff()` synchronously. The API would freeze for 60–90 seconds. The Streamlit UI showed a spinner with no feedback and would time out.

**Solution:** FastAPI's built-in `BackgroundTasks`. The POST endpoint returns a `task_id` in under 1 second. The CrewAI pipeline runs in a background thread. Streamlit polls `/status/{task_id}` every 3 seconds.

```
User clicks Run → POST /analyze (< 1 second) → task_id returned
                                                     ↓
                            Background thread: Verifier → Analyst → Advisor → Risk
                                                     ↓
                            task_updates[task_id] = {"status": "Completed", "result": "..."}
                                                     ↓
                            Streamlit polls GET /status/{task_id} every 3s → renders result
```

```python
# main.py — key implementation
@app.post("/analyze")
async def analyze_endpoint(background_tasks: BackgroundTasks, file: UploadFile, query: str):
    task_id = str(uuid.uuid4())
    task_updates[task_id] = {"status": "Processing", "result": None}
    background_tasks.add_task(process_worker, task_id, query, file_path, file.filename)
    return {"task_id": task_id, "status": "queued"}   # Returns in < 1 second ✅
```

---

### Bonus 2 — SQLite Persistence
**File:** `database.py`

**Problem:** No persistence — every analysis result was lost on server restart.

**Solution:** `DatabaseManager` class using Python's built-in `sqlite3`. Every completed analysis is automatically saved. `revenue` and `net_income` are extracted via regex from the raw result and stored in dedicated columns.

```python
# database.py — auto-extraction on save
def save_analysis(self, filename, query, result):
    rev = extract(r"(?:Total Revenue|Total revenues).*?([\$\d,.-]+...)", str(result))
    inc = extract(r"(?:Net Income).*?([\$\d,.-]+...)", str(result))
    cursor.execute(
        "INSERT INTO financial_analysis (filename, query, result, revenue, net_income) VALUES (?,?,?,?,?)",
        (filename, query, str(result), rev, inc)
    )
    self.conn.commit()
```

**Zero setup required** — `financial_data.db` is created automatically on first analysis.

---

### Bonus 3 — Financial Metrics Parser
**File:** `streamlit_app.py`

**Problem:** Raw CrewAI markdown was dumped as plain text — no structured financial data extraction or visual display.

**Solution:** `parse_metrics()` function with a two-priority system:

1. **Priority 1:** Pre-extracted DB columns (`revenue`, `net_income`) — always accurate
2. **Priority 2:** Regex on result markdown for additional metrics (FCF, Operating Income, EPS)

Results displayed as visual metric cards above the full report.

```python
# streamlit_app.py
def parse_metrics(record: dict) -> list:
    # Priority 1: already extracted by database.py on save
    if record.get("revenue") not in (None, "N/A", ""):
        cards.append(("💰 Total Revenue", record["revenue"], "metric-green", "DB column"))
    if record.get("net_income") not in (None, "N/A", ""):
        cards.append(("📈 Net Income", record["net_income"], "metric-blue", "DB column"))

    # Priority 2: regex fallback for metrics not in DB columns
    patterns = [
        ("💧 Free Cash Flow",  r"free\s+cash\s+flow.*?([\d,\.]+\s*(?:B|M|billion|million)?)"),
        ("⚙️ Oper. Income",   r"operating\s+(?:income|profit).*?([\d,\.]+\s*(?:B|M)?)"),
        ("📌 EPS",             r"(?:\bEPS\b|earnings per share).*?\$([\d,\.]+)"),
    ]
    for label, pattern, css in patterns:
        m = re.search(pattern, result_text, re.IGNORECASE)
        if m:
            cards.append((label, m.group(1), css, "parsed"))

    return cards
```

---

### Bonus 4 — History Sidebar with Instant Reload
**Files:** `streamlit_app.py` + `main.py` (`GET /history`)

**Problem:** No way to revisit past analyses without re-running the full 60-90 second CrewAI pipeline.

**Solution:** Sidebar dropdown populated from `GET /history`. Selecting any past record and clicking **Load Report** renders the full result from SQLite directly — **zero agents run, zero API cost, instant load**.

```python
# streamlit_app.py
history = fetch_history(URL)   # GET /history → SQLite records

if st.button("📂 Load Report"):
    st.session_state.viewed_record = selected_record   # Dict from SQLite
    st.session_state.result_text = None                # Clear any fresh result
    st.rerun()                                          # Instantly renders
```

---

## 🏗 System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                 STREAMLIT FRONTEND  :8501                        │
│                                                                  │
│  [Upload PDF] [Query Input] [🚀 Run Analysis]                   │
│       │                                                          │
│       │  POST /analyze (multipart/form-data)                    │
│       │  ← {task_id, status: "queued"}  (< 1 second)           │
│       │                                                          │
│       │  GET /status/{task_id}  every 3s                        │
│       │  ← {status: "Processing"} → Stage Tracker animates      │
│       │  ← {status: "Completed", result: "###VERIFIER..."}      │
│       │                                                          │
│       │  GET /history                                            │
│       │  ← {history: [{id, filename, revenue, net_income, ...}]}│
└───────┼──────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────────┐
│                 FASTAPI BACKEND  :8000                           │
│                                                                  │
│  POST /analyze                                                   │
│    → os.makedirs("data/") → save PDF                            │
│    → task_updates[task_id] = {"status": "Processing"}           │
│    → BackgroundTasks.add_task(process_worker, ...)              │
│    → return {"task_id": ..., "status": "queued"}  INSTANT ✅    │
│                                                                  │
│  GET /status/{task_id}  → task_updates.get(task_id)             │
│  GET /history           → db.get_history().data                 │
│  GET /                  → health check                           │
└───────┼──────────────────────────────────────────────────────────┘
        │  process_worker() runs in background thread
┌───────▼──────────────────────────────────────────────────────────┐
│                 CREWAI PIPELINE  (Sequential)                    │
│                                                                  │
│  🔍 Verifier          ###VERIFIER                               │
│    Goal: Validate PDF has financial data                         │
│    Tool: FinancialDocumentTool (read_data_tool)                  │
│         ↓ context passed                                         │
│  📊 Financial Analyst  ###ORACLE                                │
│    Goal: Extract Revenue, Net Income, key metrics                │
│    Tool: FinancialDocumentTool                                   │
│         ↓ context passed                                         │
│  💹 Investment Advisor  ###STRATEGY                             │
│    Goal: 3 high-conviction moves from real data                  │
│    Tool: none (uses context)                                     │
│         ↓ context passed                                         │
│  ⚠️  Risk Assessor  ###RISK                                     │
│    Goal: 3 material threats + 10x worst-case Net Income calc     │
│    Tool: FinancialDocumentTool (only if context insufficient)    │
│                                                                  │
│  LLM: groq/meta-llama/llama-4-scout-17b-16e-instruct            │
└───────┼──────────────────────────────────────────────────────────┘
        │  db.save_analysis(filename, query, result)
┌───────▼──────────────────────────────────────────────────────────┐
│              SQLite  financial_data.db                           │
│                                                                  │
│  financial_analysis table                                        │
│  ├── id, filename, query, result                                 │
│  ├── revenue    ← auto-extracted by regex in database.py        │
│  ├── net_income ← auto-extracted by regex in database.py        │
│  └── created_at                                                  │
│                                                                  │
│  Auto-created on first run. No setup required.                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
enterprise-financial-engine/
│
├── 📄 main.py              FastAPI backend — async queue, CORS, 4 endpoints
├── 🤖 agents.py            4 CrewAI agents with fixed, data-first personas
├── 📋 task.py              4 structured tasks with ###OUTPUT format headers
├── 🔧 tools.py             FinancialDocumentTool — fixed PDF reader (Bug #1 + #2)
├── 🗄  database.py          SQLite manager — save_analysis, get_history, auto-extract
├── 🖥  streamlit_app.py     Full UI — async polling, stage tracker, metrics, history
│
├── 📦 requirements.txt     All pinned dependencies
├── 🔑 .env                 API keys — NOT committed to git
├── 🚫 .gitignore           Excludes .env, *.db, data/
└── 📖 README.md            This file
│
├── data/                   Auto-created — temp PDFs (deleted after analysis)
└── financial_data.db       Auto-created SQLite — persists across restarts
```

---

## ⚙️ Setup & Installation

### Prerequisites

| Tool | Minimum Version | Check Command |
|---|---|---|
| Python | 3.10+ | `python --version` |
| pip | Latest | `pip --version` |
| Groq API Key | — | [console.groq.com](https://console.groq.com) (free) |

### Step 1 — Clone the Repo

```bash
git clone https://github.com/Himanshu-279/enterprise-financial-engine.git
cd enterprise-financial-engine
```

### Step 2 — Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 3 — Install All Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ **Critical pydantic note:**  
> `crewai==0.130.0` requires **`pydantic==1.10.13`** (v1 — NOT v2).  
> Never run `pip install pydantic --upgrade` in this project. It will break all agents with `ValidationError`.

### Step 4 — Create `.env` File

In the project root, create a file named `.env`:

```env
GROQ_API_KEY=gsk_your_actual_key_here
```

Get your free key at [console.groq.com](https://console.groq.com) → API Keys → Create API Key.

### Step 5 — Verify Setup

```bash
python -c "import crewai, fastapi, streamlit, PyPDF2; print('✅ All dependencies OK')"
```

---

## 🔑 Environment Variables

| Variable | Required | Description | Where to Get |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | API key for Groq LLaMA-4-Scout inference | [console.groq.com](https://console.groq.com) |

> `financial_data.db` and the `data/` folder are both **auto-created on first run**. You don't need to create them manually.

---

## ▶️ Running the App

Open **two separate terminal windows** in the project directory.

### Terminal 1 — Start the Backend

```bash
uvicorn main:app --reload --port 8000
```

Wait for:
```
🏠 Local Database Active: financial_data.db
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

Verify it works: open `http://localhost:8000` — you should see:
```json
{"status": "Active", "message": "Enterprise Financial Engine is running"}
```

### Terminal 2 — Start the Frontend

```bash
streamlit run streamlit_app.py
```

Wait for:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

Open **http://localhost:8501** in your browser.

---

## 📡 API Documentation

**Base URL:** `http://localhost:8000`  
**Interactive Swagger UI:** `http://localhost:8000/docs`  
**ReDoc:** `http://localhost:8000/redoc`

---

### `GET /`
Health check endpoint.

**Response `200 OK`:**
```json
{
  "status": "Active",
  "message": "Enterprise Financial Engine is running"
}
```

---

### `POST /analyze`

Upload a PDF document and start analysis in the background. **Returns instantly** — does not wait for the pipeline to finish.

**Request format:** `multipart/form-data`

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `file` | PDF file | ✅ Yes | — | Financial document to analyze |
| `query` | string | ❌ No | `"Detailed analysis of this financial report"` | Your specific question |

**cURL:**
```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@tesla_report.pdf" \
  -F "query=What is the total revenue and net income?"
```

**Python:**
```python
import requests

with open("annual_report.pdf", "rb") as f:
    resp = requests.post(
        "http://localhost:8000/analyze",
        files={"file": ("annual_report.pdf", f, "application/pdf")},
        data={"query": "Identify liquidity risks and cash flow concerns"}
    )

data = resp.json()
print(data["task_id"])   # Use this to poll /status
```

**Response `200 OK`:**
```json
{
  "task_id": "a3f7c91e-42b1-4d8e-9f2a-1b3c5d7e9f01",
  "status": "queued",
  "message": "Analysis started in background worker."
}
```

---

### `GET /status/{task_id}`

Check the status of a running or completed analysis. Poll this every 2–3 seconds after calling `POST /analyze`.

**Path parameter:**

| Parameter | Type | Description |
|---|---|---|
| `task_id` | UUID string | Returned by `POST /analyze` |

**cURL:**
```bash
curl http://localhost:8000/status/a3f7c91e-42b1-4d8e-9f2a-1b3c5d7e9f01
```

**Response — Still running:**
```json
{
  "status": "Processing",
  "result": null
}
```

**Response — Done:**
```json
{
  "status": "Completed",
  "result": "###VERIFIER\nDocument APPROVED — financial data confirmed.\n\n###ORACLE\n## ✅ VERIFIED FINANCIAL DATA\n| Financial Metric | Actual Value | Source |\n|---|---|---|\n| Total Revenue | $25.18B | Income Statement |\n| Net Income | $1.78B | Income Statement |\n\n## 🚀 ANALYST'S VERDICT\n...\n\n###STRATEGY\n...\n\n###RISK\n..."
}
```

**Response — Failed:**
```json
{
  "status": "Failed",
  "error": "CRITICAL ERROR: Document not found at data/doc_abc.pdf."
}
```

**Response — ID not found:**
```json
{
  "status": "Not Found"
}
```

---

### `GET /history`

Retrieve all past analyses from SQLite, ordered newest first.

**cURL:**
```bash
curl http://localhost:8000/history
```

**Response `200 OK`:**
```json
{
  "history": [
    {
      "id": 3,
      "filename": "tesla_q2_2025.pdf",
      "query": "What is the net profit?",
      "result": "###VERIFIER\n...\n###ORACLE\n...\n###STRATEGY\n...\n###RISK\n...",
      "revenue": "$25.18B",
      "net_income": "$1.78B",
      "created_at": "2026-02-26 18:04:53"
    },
    {
      "id": 2,
      "filename": "annual_report_2024.pdf",
      "query": "Analyze revenue growth",
      "result": "###VERIFIER\n...",
      "revenue": "$500M",
      "net_income": "$50M",
      "created_at": "2026-02-25 14:22:11"
    }
  ]
}
```

---

### Full End-to-End Example (Python)

```python
import requests, time

BASE = "http://localhost:8000"

# 1. Submit PDF
with open("financial_report.pdf", "rb") as f:
    resp = requests.post(
        f"{BASE}/analyze",
        files={"file": ("financial_report.pdf", f, "application/pdf")},
        data={"query": "Analyze revenue growth and identify top 3 risks"}
    )
resp.raise_for_status()
task_id = resp.json()["task_id"]
print(f"✅ Queued: {task_id}")

# 2. Poll until done
while True:
    poll = requests.get(f"{BASE}/status/{task_id}").json()
    status = poll["status"]
    print(f"⏳ Status: {status}")

    if status == "Completed":
        print("\n📊 Analysis Result:")
        print(poll["result"])
        break
    elif status == "Failed":
        print(f"\n❌ Error: {poll.get('error')}")
        break
    else:
        time.sleep(3)

# 3. Verify it was saved to history
history = requests.get(f"{BASE}/history").json()
print(f"\n🗄 Total analyses in DB: {len(history['history'])}")
latest = history["history"][0]
print(f"Latest — Revenue: {latest['revenue']} | Net Income: {latest['net_income']}")
```

---

## 🖥 UI Guide

### Tab 1 — Document Analysis
| Element | Description |
|---|---|
| **PDF Upload** | Drag & drop or browse — any financial PDF |
| **Query Selector** | 5 presets + custom text area |
| **🚀 Run Analysis** | Disabled until PDF uploaded + backend online |
| **Stage Tracker** | Animated 4-chip progress (Verifier → Oracle → Strategy → Risk) — updates every 3 seconds |
| **Metric Cards** | Revenue, Net Income, FCF, EPS — extracted from DB columns or regex |
| **Full Report** | Complete `###VERIFIER → ###ORACLE → ###STRATEGY → ###RISK` markdown |
| **📥 Download** | Saves result as JSON |

### Tab 2 — Job History
| Element | Description |
|---|---|
| **Stats Row** | Total records, how many have revenue/net_income extracted |
| **Record List** | All SQLite rows — filename, revenue, net_income, timestamp |
| **Expandable Rows** | Click any record to see full report + metric cards + download |

### Tab 3 — Debug Report
Complete list of all 5 bugs fixed and 4 bonus features — with file name, problem, and fix for each. Downloadable as `debug_report.json`.

### Tab 4 — Architecture
Agent flow diagram, full async request lifecycle (7 steps), backend/frontend tech stack, setup commands.

### Sidebar
| Element | Description |
|---|---|
| **Backend URL** | Configurable — default `http://localhost:8000` |
| **ONLINE / OFFLINE** | Live badge — pings `GET /` every 30 seconds |
| **🗄️ financial_data.db** | SQLite status indicator |
| **Load Past Report** | Dropdown of all history records — loads from SQLite with zero CrewAI re-run |
| **Session Stats** | Analysis count + last run duration |
| **🗑️ Clear Session** | Resets all UI state |

---

## 🗄 Database Schema

**File:** `financial_data.db` — auto-created by `database.py` on first run  
**Table:** `financial_analysis`

| Column | Type | Notes |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Auto-incrementing |
| `filename` | `TEXT` | Original uploaded PDF name |
| `query` | `TEXT` | User's analysis question |
| `result` | `TEXT` | Full CrewAI output: `###VERIFIER...###RISK` |
| `revenue` | `TEXT` | Auto-extracted on save (e.g. `$25.18B`) |
| `net_income` | `TEXT` | Auto-extracted on save (e.g. `$1.78B`) |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` (UTC) |

**How extraction works:** `database.py:save_analysis()` runs regex over the raw `result` text immediately after `crew.kickoff()` completes and stores the match in the `revenue`/`net_income` columns — no extra API call needed.

---

## 🛠 Tech Stack

| Layer | Technology | Version | Why |
|---|---|---|---|
| LLM | Groq LLaMA-4-Scout | Latest | Fastest open model, 16K context |
| Agent Framework | CrewAI | `0.130.0` pinned | Sequential multi-agent orchestration |
| Backend | FastAPI | `0.110.3` | Async endpoints, BackgroundTasks, CORS |
| ASGI Server | Uvicorn | `0.29.0` | Production async server |
| Frontend | Streamlit | `≥ 1.32.0` | Rapid UI with session state |
| PDF Parser | PyPDF2 | `3.0.1` | Text extraction from financial PDFs |
| Database | SQLite | Built-in stdlib | Zero-config local persistence |
| LLM Router | LiteLLM | `≥ 1.40.0` | Routes `groq/` prefix calls correctly |
| HTTP | Requests | `≥ 2.31.0` | Streamlit → FastAPI polling |
| Env | python-dotenv | `1.0.1` | `.env` loading |

---

## ❓ Troubleshooting

**Backend shows OFFLINE in the sidebar**
```bash
# Make sure Terminal 1 is running uvicorn
uvicorn main:app --reload --port 8000
# Manually verify: open http://localhost:8000 — should show {"status":"Active"}
```

**`pydantic` validation errors on startup**
```bash
# crewai 0.130.0 needs pydantic v1 — force correct version
pip install "pydantic==1.10.13" "pydantic_core==2.8.0"
```

**`ModuleNotFoundError: No module named 'crewai'`**
```bash
# Check virtual environment is activated
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

**Analysis stuck on "Processing" and never completes**
- Check **Terminal 1** (uvicorn) for error output from the background worker
- Most common causes: invalid `GROQ_API_KEY`, scanned PDF (image-only, no text), network issue
- A scanned PDF returns: `"Error: Document is empty or text is not extractable"`

**`CRITICAL ERROR: Document not found`**
- The `data/` folder is auto-created — if it fails, create it: `mkdir data`
- Ensure uvicorn is run from the **project root** (same folder as `main.py`)
- Ensure the PDF is not password-protected

**Groq API 429 rate limit**
- Free tier has request-per-minute limits — wait 60 seconds and retry
- Check [console.groq.com](https://console.groq.com) for your current usage

**`financial_data.db` not found**
- Created automatically on the first successful `POST /analyze`
- If analysis is failing before completion, the DB won't be written yet
- Check Terminal 1 logs for the line: `✅ Auto-Saved to History: filename.pdf`

Developed by: Himanshu Verma 



<div align="center">

**Enterprise Financial Engine** — Fixed · Documented · Production-Ready

*AI Intern Debug Assignment · 2026*
Developed by: Himanshu Verma 

</div>


<!-- # 📊 Enterprise Financial Analysis Engine v3.0

An advanced, multi-agent financial document analyzer built with **CrewAI**, **FastAPI**, and **Streamlit**. This system processes complex financial PDFs using a sequential 4-agent pipeline to deliver deep insights and risk assessments.

---

## 🚀 Key Features & Bonus Points
* **Asynchronous Processing**: Uses `BackgroundTasks` to ensure a non-blocking UI. The frontend polls for status updates without freezing the user experience.
* **Local Persistence**: Every analysis is automatically archived in a local **SQLite** database (`financial_data.db`).
* **Intelligent Metrics Parser**: Automatically extracts key figures like Revenue and Net Income using regex and displays them as metric cards.
* **Historical Reload**: Sidebar history allows instant reloading of past reports from the database with **zero re-run cost**.

---

## 🐛 Bugs Found & Fixed

| Component | Bug Type | Issue | Fix Implemented |
| :--- | :--- | :--- | :--- |
| `tools.py` | **Deterministic** | PDF Path handling failed due to raw string quotes/spaces. | Implemented `.strip().replace("'", "")` and `os.path.exists()` validation. |
| `tools.py` | **Deterministic** | Context Window Overflow (PDFs too large for LLM). | Capped PDF reading to first 8 pages and sliced text to 8000 characters. |
| `agents.py` | **Deterministic** | Tools passed as Classes instead of Instances. | Corrected to `tools=[FinancialDocumentTool()]`. |
| `agents.py` | **Efficiency** | Agents instructed to hallucinate/fabricate data. | Rewrote backstories with "Strict Numeric Truth" and "No Hallucination" rules. |
| `task.py` | **Efficiency** | Task outputs were unstructured and contradictory. | Implemented strict `###VERIFIER`, `###ORACLE`, `###STRATEGY`, `###RISK` headers. |
| `main.py` | **Architecture** | Synchronous API calls freezing the frontend. | Implemented `BackgroundTasks` for async execution and a status polling endpoint. |

---

## 🛠️ Setup Instructions

### 1. Prerequisites
* Python 3.10+
* Groq API Key (for LLaMA-4-Scout)

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-link>
cd financial-document-analyzer-debug

# Install dependencies
pip install -r requirements.txt


3. Environment Setup
Create a .env file in the root directory:
GROQ_API_KEY=your_actual_api_key_here

Step 1: Start the Backend (FastAPI)
uvicorn main:app --reload --port 8000

Step 2: Start the Frontend (Streamlit)
streamlit run streamlit_app.py

Step 3: Run Analysis
Upload a financial PDF.

Monitor the Stage Tracker animation as agents coordinate in real-time.

View results and metrics once the status hits Completed.

Check Analysis History to view past records saved in SQLite.

📡 API Documentation
1. Root Health Check
Endpoint: GET /

Response: {"status": "Active"}

2. Analyze Document (Async)
Endpoint: POST /analyze

Body: file (PDF), query (Text)

Response: {"task_id": "uuid", "status": "queued"}

3. Check Task Status
Endpoint: GET /status/{task_id}

Response: {"status": "Processing|Completed|Failed", "result": "..."}

4. Fetch History
Endpoint: GET /history

Response: List of all past analyses from SQLite.

⚙️ Multi-Agent Architecture
Verifier: Validates document structure and numeric data presence.

Financial Analyst (Oracle): Extracts precise numeric data points.

Investment Advisor: Builds a growth strategy based on extracted metrics.

Risk Assessor: Calculates 10x impact worst-case scenarios.

Developed by: Himanshu Verma (Batch 2026) -->


