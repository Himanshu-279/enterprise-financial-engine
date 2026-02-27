
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import traceback
from crewai import Crew, Process
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from task import verification_task, analyze_financial_document, investment_analysis, risk_assessment
from database import db # Final SQLite Database Manager

app = FastAPI(title="Pro Financial Document Analyzer")

# Task Store: Polling 
task_updates = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "Active", "message": "Enterprise Financial Engine is running"}

# --- BACKGROUND WORKER LOGIC ---
def process_worker(task_id: str, query: str, file_path: str, original_filename: str):
    """Background mein agents ko run karega aur LOCAL database mein save karega."""
    try:
        # 1. Start CrewAI Pipeline
        financial_crew = Crew(
            agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
            tasks=[verification_task, analyze_financial_document, investment_analysis, risk_assessment],
            process=Process.sequential,
            verbose=True
        )
        result = financial_crew.kickoff(inputs={'query': query, 'path': file_path})
        
        # 2. Database Integration (Bonus Point )
        db.save_analysis(original_filename, query, str(result))
        
        # 3. Update Status for UI Polling
        task_updates[task_id] = {"status": "Completed", "result": str(result)}
        print(f"✅ Task {task_id} archived in Local Database.")
        
    except Exception as e:
        print(f"❌ Worker Error: {traceback.format_exc()}")
        task_updates[task_id] = {"status": "Failed", "error": str(e)}
    
    finally:
        # Resource Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/analyze")
async def analyze_financial_document_endpoint(
    background_tasks: BackgroundTasks, # Asynchronous Queue Model (Bonus Point )
    file: UploadFile = File(...),
    query: str = Form(default="Detailed analysis of this financial report")
):
    task_id = str(uuid.uuid4())
    file_path = f"data/doc_{task_id}.pdf"
    
    try:
        os.makedirs("data", exist_ok=True)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Status Initialize 
        task_updates[task_id] = {"status": "Processing", "result": None}
        
        # Background task in queue 
        background_tasks.add_task(process_worker, task_id, query, file_path, file.filename)
        
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Analysis started in background worker."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{task_id}")
async def check_task_status(task_id: str):
    """Streamlit is endpoint ko polling ke liye use karega."""
    return task_updates.get(task_id, {"status": "Not Found"})

# --- HISTORY ENDPOINT (Bonus Point ) ---
@app.get("/history")
async def get_all_history():
    """Local SQLite se purana saara data fetch karega."""
    history_obj = db.get_history()
    return {"history": history_obj.data}

if __name__ == "__main__":
    import uvicorn
    # reload=True is for development only. Remove in production for better performance and security.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)