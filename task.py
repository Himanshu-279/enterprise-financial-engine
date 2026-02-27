
from crewai import Task
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from tools import search_tool, FinancialDocumentTool

# --- TASK 1: VERIFICATION ---
verification_task = Task(
    description=(
        "1. Scrutinize the document at {path} to identify its 'Financial DNA'.\n"
        "2. Confirm if numeric financial data is present.\n"
        "3. Output MUST start with: ###VERIFIER"
    ),
    expected_output="###VERIFIER\nAn Official Memo confirming the document's structure and numeric data presence.",
    agent=verifier,
    tools=[FinancialDocumentTool()],
    async_execution=False
)

# --- TASK 2: DATA ORACLE ---
analyze_financial_document = Task(
    description=(
        "1. Use 'read_data_tool' to extract precise metrics for: {query} from {path}.\n"
        "2. Locate Total Revenue and Net Income. If not found, write 'Data Unavailable'.\n"
        "3. Output MUST start with: ###ORACLE"
    ),
    expected_output="###ORACLE\n" + """
## ✅ VERIFIED FINANCIAL DATA
| Financial Metric | Actual Value Found | Source Section |
| :--- | :--- | :--- |
| [Metric] | [Value] | [Section] |

## 🚀 SENIOR ANALYST'S DATA-BACKED VERDICT
[Professional, aggressive analysis based ONLY on metrics.]
""",
    agent=financial_analyst,
    tools=[FinancialDocumentTool()],
    context=[verification_task],
    async_execution=False,
)

# --- TASK 3: STRATEGY ---
investment_analysis = Task(
    description=(
        "1. Analyze EXACT numbers from the Oracle.\n"
        "2. Suggest 3 high-conviction investment moves.\n"
        "3. Output MUST start with: ###STRATEGY"
    ),
    expected_output="###STRATEGY\nA high-conviction investment strategy based on verified metrics.",
    agent=investment_advisor,
    context=[analyze_financial_document], 
    async_execution=False,
)

# --- TASK 4: RISK ASSESSMENT ---
# Hum tools ko variable mein rakhenge
risk_tools = [FinancialDocumentTool()] 

risk_assessment = Task(
    description=(
        "1. First, analyze the context provided by the previous task 'analyze_financial_document'.\n"
        "2. IF the financial metrics (Net Income/Total Revenue) and potential risks are already present in the context, USE that information directly.\n"
        "3. IF the context is insufficient or contains 'Data Unavailable', ONLY THEN use 'read_data_tool' on the document at {path} to find risks.\n"
        "4. Identify 3 specific material threats mentioned in the text (e.g., regulatory changes, macro-economic shifts, or operational issues).\n"
        "5. Take the Net Income figure found in the context and calculate a 'Worst-Case Scenario' where these identified risks impact that figure by a factor of 10.\n"
        "6. Output MUST start with ###RISK and provide the final quantitative analysis."
    ),
    expected_output="A structured report starting with ###RISK, identifying 3 threats and their 10x calculated impact on the specific company's Net Income.",
    agent=risk_assessor,
    context=[analyze_financial_document], # Dynamic Context Sharing
    tools=risk_tools, 
    async_execution=False
)