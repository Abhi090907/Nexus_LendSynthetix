import io
import json
import logging
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline import ingest_pdf_pipeline
from risk_scoring import calculate_risk_score
from query_engine import query_loan_documents
from qdrant_store import get_qdrant_client
from config import get_collection_name

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from openai import OpenAI
from war_room_graph import run_war_room

logger = logging.getLogger(__name__)

# Load whisper model globally (if available)
try:
    if WhisperModel:
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    else:
        whisper_model = None
except Exception as e:
    logger.error(f"Failed to load whisper model: {e}")
    whisper_model = None

app = FastAPI(title="LendSynthetix Loan War Room API")

# Setup CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)


@app.post("/upload-pdf")
async def upload_pdf(files: List[UploadFile] = File(...)):
    """
    Accepts PDF records, processes them via the pipeline
    and registers embeddings into the local vector DB.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    saved_paths = []
    
    try:
        # Save temp files
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                continue
                
            temp_path = TEMP_DIR / file.filename
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(temp_path)
            
        if not saved_paths:
            raise HTTPException(status_code=400, detail="No valid PDF files found.")

        # Wipe previous documents so new uploads do not mix context
        logger.info("Emptying old database collections...")
        try:
            client = get_qdrant_client()
            client.delete_collection(get_collection_name(None))
        except Exception as e:
            logger.warning(f"Could not delete collection before ingestion (it might not exist): {e}")

        # Ingest
        # Note: ingest_pdf_pipeline processes documents to the existing loan_documents collection
        # We wrap this to catch upstream errors
        ingest_pdf_pipeline(pdf_paths=saved_paths)
        
        return {
            "status": "success", 
            "message": f"Successfully processed {len(saved_paths)} PDFs into the vector store.",
            "processed_files": [p.name for p in saved_paths]
        }

    except Exception as e:
        logger.error(f"Error during PDF processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup
        for path in saved_paths:
            if path.exists():
                path.unlink()


class ApplicantData(BaseModel):
    person_age: int = 30
    person_income: int = 50000
    person_emp_length: float = 5.0
    loan_amnt: int = 10000
    loan_int_rate: float = 10.0
    loan_percent_income: float = 0.2
    cb_person_default_on_file: str = "N"
    cb_person_cred_hist_length: int = 5

class ExplainRequest(BaseModel):
    applicant: ApplicantData

@app.post("/explain-loan")
def explain_loan(req: ExplainRequest):
    """
    Processes applicant data and outputs an explainability graph object.
    """
    # map ApplicantData to what calculate_risk_score expects
    financial_analysis = {
        "metrics": req.applicant.dict()
    }
    
    try:
        result = calculate_risk_score(
            financial_analysis=financial_analysis,
            risk_memo={},
            compliance_memo={}
        )
        return {
            "status": "success",
            "prediction": result.get("risk_score"),
            "risk_level": result.get("risk_level"),
            "predicted_grade": result.get("predicted_grade"),
            "shap_explanation": result.get("shap_explanation", []),
            "key_drivers": result.get("key_drivers", [])
        }
    except Exception as e:
        logger.error(f"Error running risk explainability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-agent")
async def ask_agent(request: Request):
    content_type = request.headers.get("content-type", "")
    
    text_query = ""
    transcribed_text = ""
    
    if "application/json" in content_type:
        data = await request.json()
        text_query = data.get("text", "")
    elif "multipart/form-data" in content_type:
        form = await request.form()
        audio_file = form.get("audio")
        if audio_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                tmp.write(await audio_file.read())
                tmp_path = tmp.name
            
            try:
                if whisper_model:
                    segments, info = whisper_model.transcribe(tmp_path, beam_size=5)
                    transcribed_text = " ".join([segment.text for segment in segments])
                else:
                    transcribed_text = "Whisper model not loaded."
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            
            text_query = transcribed_text

    if not text_query:
        raise HTTPException(status_code=400, detail="No text or audio provided.")

    # 1. Gather context
    applicant = ApplicantData()
    financial_analysis = {"metrics": applicant.dict()}
    try:
        risk_result = calculate_risk_score(
            financial_analysis=financial_analysis,
            risk_memo={},
            compliance_memo={}
        )
        risk_score = risk_result.get("risk_score")
        risk_level = risk_result.get("risk_level")
        predicted_grade = risk_result.get("predicted_grade")
        shap_explanation = risk_result.get("shap_explanation", [])
    except Exception as e:
        risk_score, risk_level, predicted_grade, shap_explanation = ("Unknown", "Unknown", "Unknown", [])
        
    # 2. Similar cases from Qdrant
    try:
        similar_cases = query_loan_documents(text_query)
    except Exception as e:
        similar_cases = f"Could not retrieve similar cases: {e}"

    # 3. LLM Agent
    from config import get_settings
    settings = get_settings()
    
    client = OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "dummy-key"
    )
    
    system_prompt = "You are a financial risk analyst assistant. Explain loan decisions clearly, justify outcomes using data, and suggest practical improvements in simple language."

    user_prompt = f"""
The user is asking: "{text_query}"

Context about the current loan:
- Risk Score: {risk_score}
- Risk Level: {risk_level}
- Predicted Grade: {predicted_grade}
- SHAP Explanation (Key Drivers): {shap_explanation}

Similar Past Cases Context (from Vector DB):
{similar_cases}

Please provide a helpful, clear, and context-aware answer.
"""

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500
        )
        answer = response.choices[0].message.content
        confidence = 0.95
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        answer = f"I received your question: '{text_query}'. However, my OpenAI connection failed: {e}. Here is context I found: Risk Score {risk_score}, Grade {predicted_grade}. Similar cases info size: {len(similar_cases)} chars."
        confidence = 0.0

    suggested_questions = [
        "Why was this loan rejected?",
        "How can this loan be approved?",
        "What are the biggest risk factors?"
    ]

    return {
        "question": text_query,
        "transcribed_text": transcribed_text,
        "answer": answer,
        "confidence": confidence,
        "suggested_questions": suggested_questions
    }

@app.post("/run-war-room")
async def execute_war_room():
    """
    Triggers the AI multi-agent debate (War Room) manually.
    Saves results to public/dashboard/war_room_output.json.
    """
    question = (
        "Should we approve this commercial loan? "
        "Summarize the key risks and opportunities and recommend "
        "APPROVE, REJECT, or CONDITIONAL APPROVAL."
    )
    
    try:
        logger.info("Starting War Room debate...")
        result = run_war_room(question)
        
        # Prepare JSON output for dashboard
        output = {
            "question":           question,
            "collection_name":    get_collection_name(None),
            "financial_analysis": result.get("financial_analysis") or {},
            "sales_memo":         result.get("sales_memo")         or {},
            "risk_memo":          result.get("risk_memo")          or {},
            "sales_rebuttal":     result.get("sales_rebuttal")     or {},
            "compliance_memo":    result.get("compliance_memo")    or {},
            "market_intelligence": result.get("market_intelligence") or {},
            "risk_score":         result.get("risk_score")         or {},
            "stress_test_results":result.get("stress_test_results")or {},
            "final_decision":     result.get("final_decision")     or {},
            "altman_z":           result.get("altman_z")           or {},
            "sentiment_memo":     result.get("sentiment_memo")     or {},
            "report_meta":        result.get("report_meta")        or {},
        }
        
        # Define the output path in the public/dashboard folder
        out_path = Path("..") / "public" / "dashboard" / "war_room_output.json"
        
        # Ensure directory exists (though it should)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
            
        return {"status": "success", "message": "War Room debate completed and results saved."}
        
    except Exception as e:
        logger.error(f"War Room execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download-report")
async def download_report(collection: str = Query(default="unknown")):
    """
    Generates and returns a signed PDF report from most recent war_room_output.json.
    """
    from report_generator import generate_signed_pdf

    candidate_paths = [
        Path("..") / "public" / "dashboard" / "war_room_output.json",
        Path("war_room_output.json"),
    ]
    out_path = next((p for p in candidate_paths if p.exists()), None)
    if out_path is None:
        raise HTTPException(status_code=404, detail="No report available yet")

    try:
        with open(out_path, "r", encoding="utf-8") as file_obj:
            report_data = json.load(file_obj)

        pdf_bytes = generate_signed_pdf(report_data, collection)
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"LendSynthetix_CAN_{collection}_{date_str}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
