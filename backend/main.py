import os
import json
import uuid
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .config import (
    UPLOADS_DIR, REPORTS_DIR, SAMPLES_DIR, FRONTEND_DIR,
    BASE_DIR, CURRENT_SYSTEM_DATE, RISK_THRESHOLD_LOW, RISK_THRESHOLD_MEDIUM
)
from .database import (
    init_db, get_db_connection, log_audit_event, get_all_audit_logs, verify_audit_integrity
)
from .auth import (
    verify_password, create_access_token, get_current_officer, get_password_hash
)
from .seed_data import seed_database
from .engines.ocr_engine import extract_document_ocr
from .engines.validation_engine import validate_extracted_document
from .engines.tampering_engine import analyze_document_tampering
from .engines.face_engine import crop_document_face, verify_face_biometrics
from .engines.risk_engine import calculate_screening_risk
from .engines.report_engine import generate_pdf_report

# Initialize FastAPI App
app = FastAPI(
    title="DocShield AI — Security Command API",
    description="AI-Powered Identity & Document Screening Platform API (SIH 26188)",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Initialization
@app.on_event("startup")
def on_startup():
    try:
        init_db()
        seed_database()
    except Exception as e:
        print(f"Startup initialization notice: {e}")

# Pydantic Request Models
class LoginRequest(BaseModel):
    username: str
    password: str

class ScreeningCreateRequest(BaseModel):
    domain: str = "01 — AIRLINES & GATE AGENTS"
    doc_type: str = "Passport"
    scenario_hint: Optional[str] = None  # "genuine_passport", "tampered_visa", "expired_id", or None for Live Upload

class OcrConfirmRequest(BaseModel):
    case_id: str
    extracted_data: Dict[str, Any]

class OfficerReviewRequest(BaseModel):
    case_id: str
    decision: str
    notes: Optional[str] = ""

class WatchlistEntryRequest(BaseModel):
    doc_number: str
    full_name: str
    nationality: str
    dob: str
    status: str
    reason: Optional[str] = ""
    alert_level: str = "MEDIUM"

# ----------------- AUTHENTICATION ENDPOINTS -----------------
class ForgotPasswordRequest(BaseModel):
    work_id: str

@app.post("/api/auth/login")
def login(req: LoginRequest):
    work_id = req.username.strip().lower()
    clean_user = work_id.split('@')[0]

    # Support synthetic demo credentials
    if work_id in ["demo.officer@docshield.ai", "demo.officer", "demo"] and req.password in ["Demo@123", "demo", "password123"]:
        access_token = create_access_token(data={"sub": "officer.sharma"})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "officer": {
                "id": 1,
                "username": "demo.officer",
                "full_name": "Senior Officer V. Sharma",
                "badge_number": "BSF-IMM-8924",
                "department": "Border Security & Immigration Control",
                "role": "Senior Screening Officer",
                "email": "demo.officer@docshield.ai"
            }
        }

    # Support default officer login
    if work_id in ["officer@docshield.ai", "officer.sharma"] and req.password in ["password123", "Demo@123"]:
        access_token = create_access_token(data={"sub": "officer.sharma"})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "officer": {
                "id": 1,
                "username": "officer.sharma",
                "full_name": "Officer Vikram Sharma",
                "badge_number": "BSF-IMM-8924",
                "department": "Border Security & Immigration Control",
                "role": "Senior Screening Officer",
                "email": "officer@docshield.ai"
            }
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM officers WHERE username = ? OR username = ?", (work_id, clean_user))
    officer = cursor.fetchone()
    conn.close()

    if not officer or not verify_password(req.password, officer["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please try again."
        )

    access_token = create_access_token(data={"sub": officer["username"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "officer": {
            "id": officer["id"],
            "username": officer["username"],
            "full_name": officer["full_name"],
            "badge_number": officer["badge_number"],
            "department": officer["department"],
            "role": officer["role"],
            "email": f"{officer['username']}@docshield.ai"
        }
    }

@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    return {
        "status": "success",
        "message": "Recovery request submitted. An authorized administrator will review your credentials."
    }

@app.get("/api/auth/me")
def get_me(officer: Dict[str, Any] = Depends(get_current_officer)):
    officer["email"] = "officer@docshield.ai"
    return {"officer": officer}


# ----------------- DASHBOARD & METRICS -----------------
@app.get("/api/stats/dashboard")
def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM screenings")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM screenings WHERE status LIKE '%GENUINE%' OR status = 'VERIFIED'")
    verified = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM screenings WHERE status LIKE '%REVIEW%'")
    suspicious = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM screenings WHERE status LIKE '%FAKE%' OR status LIKE '%SUSPICIOUS%' OR status = 'HIGH RISK'")
    high_risk = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT case_id, person_name, doc_type, doc_number, created_at, overall_risk_score, status, risk_level, officer_name
        FROM screenings ORDER BY created_at DESC LIMIT 10
    """)
    recent = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return {
        "metrics": {
            "total_screenings": total,
            "verified_documents": verified,
            "suspicious_documents": suspicious,
            "high_risk_cases": high_risk
        },
        "risk_distribution": [
            {"name": "Likely Genuine", "value": verified, "color": "#10b981"},
            {"name": "Requires Manual Review", "value": suspicious, "color": "#f59e0b"},
            {"name": "Likely Fake / Suspicious", "value": high_risk, "color": "#ef4444"}
        ],
        "recent_screenings": recent,
        "system_status": {
            "ocr_engine": "ONLINE (DocShield High-Resolution OCR)",
            "tampering_forensics": "ONLINE (Error Level Analysis ELA)",
            "face_biometrics": "ONLINE (1:1 Embedding Distance)",
            "demo_database": "ACTIVE (Border Watchlist Registry)"
        }
    }

# ----------------- HEALTH & SYSTEM DIAGNOSTICS -----------------
@app.get("/api/health")
def get_health_status():
    return {
        "status": "ok",
        "ocr": "ready",
        "service": "DocShield AI — Security Command",
        "version": "3.1.0"
    }

@app.get("/api/ocr/health")
def get_ocr_health_status():
    return {
        "status": "ready",
        "engine": "DocShield Hybrid OCR Engine (ICAO 9303 + VIZ)",
        "features": ["ICAO_9303_MRZ", "7_3_1_CHECKSUMS", "VIZ_EXTRACTION", "VERHOEFF_VALIDATION", "PDF_DECODING"],
        "max_resolution": "1600px",
        "timeout_limit_sec": 30
    }

# ----------------- SCREENING WORKFLOW ENDPOINTS -----------------
@app.post("/api/screening/create")
def create_screening(req: ScreeningCreateRequest, officer: Dict[str, Any] = Depends(get_current_officer)):
    case_id = f"CASE-2026-{uuid.uuid4().hex[:4].upper()}"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Preset sample image for demo scenarios
    doc_image_path = None
    face_doc_path = None
    face_live_path = None
    
    if req.scenario_hint == "genuine_passport":
        doc_image_path = "samples/sample_genuine_passport.jpg"
        face_doc_path = "samples/doc_face_genuine.jpg"
        face_live_path = "samples/live_face_genuine.jpg"
    elif req.scenario_hint == "tampered_visa":
        doc_image_path = "samples/sample_tampered_visa.jpg"
        face_doc_path = "samples/doc_face_tampered.jpg"
        face_live_path = "samples/live_face_tampered.jpg"
    elif req.scenario_hint == "expired_id":
        doc_image_path = "samples/sample_expired_id.jpg"
        face_doc_path = "samples/doc_face_expired.jpg"
        face_live_path = "samples/live_face_expired.jpg"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO screenings (
        case_id, domain, created_at, updated_at, officer_id, officer_name, doc_type,
        status, overall_risk_score, risk_level, doc_image_path, face_doc_path, face_live_path
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        case_id, req.domain, timestamp, timestamp, officer.get("id", 1), officer.get("full_name", "Security Officer"),
        req.doc_type, "PROCESSING", 0, "PENDING", doc_image_path, face_doc_path, face_live_path
    ))
    conn.commit()
    conn.close()

    log_audit_event(case_id, "SCREENING_INITIALIZED", officer.get("full_name", "Officer"), {
        "domain": req.domain,
        "doc_type": req.doc_type,
        "mode": "DEMO_SCENARIO" if req.scenario_hint else "LIVE_UPLOAD",
        "scenario_hint": req.scenario_hint or "custom_upload"
    })

    return {
        "case_id": case_id,
        "domain": req.domain,
        "doc_type": req.doc_type,
        "scenario_hint": req.scenario_hint,
        "doc_image_path": doc_image_path,
        "mode": "DEMO_SCENARIO" if req.scenario_hint else "LIVE_UPLOAD"
    }

@app.post("/api/screening/upload")
async def upload_document_image(
    case_id: str = Form(...),
    doc_type: str = Form("Passport"),
    domain: str = Form("01 — AIRLINES & GATE AGENTS"),
    file: UploadFile = File(...),
    officer: Dict[str, Any] = Depends(get_current_officer)
):
    file_ext = Path(file.filename).suffix.lower()
    allowed_exts = [".jpg", ".jpeg", ".png", ".webp", ".pdf", ".bmp", ".tiff"]
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Supported formats: JPG, JPEG, PNG, WEBP, PDF."
        )

    filename = f"{case_id}_{uuid.uuid4().hex[:4]}{file_ext}"
    saved_path = UPLOADS_DIR / filename
    
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    file_size = os.path.getsize(saved_path)
    if file_size > 25 * 1024 * 1024:
        os.remove(saved_path)
        raise HTTPException(status_code=400, detail="File size exceeds 25MB limit.")

    rel_path = f"uploads/{filename}"
    
    # Auto-detect & crop portrait face from the uploaded document
    doc_face_filename = f"face_doc_{case_id}.jpg"
    doc_face_path = str(UPLOADS_DIR / doc_face_filename)
    cropped_path, face_detected = crop_document_face(str(saved_path), doc_face_path)
    
    face_rel_path = f"uploads/{doc_face_filename}" if face_detected else None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE screenings SET doc_image_path = ?, face_doc_path = ?, doc_type = ?, updated_at = ?
    WHERE case_id = ?
    """, (rel_path, face_rel_path, doc_type, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), case_id))
    conn.commit()
    conn.close()

    log_audit_event(case_id, "DOCUMENT_UPLOADED", officer.get("full_name", "Officer"), {
        "filename": file.filename,
        "size_bytes": file_size,
        "doc_type": doc_type,
        "domain": domain,
        "face_detected": face_detected
    })

    return {
        "case_id": case_id,
        "file_name": file.filename,
        "file_size": file_size,
        "doc_image_path": rel_path,
        "face_doc_path": face_rel_path,
        "face_detected": face_detected
    }

@app.post("/api/ocr/extract")
def run_ocr(
    case_id: str = Form(...),
    scenario_hint: Optional[str] = Form(None),
    doc_type: Optional[str] = Form(None),
    officer: Dict[str, Any] = Depends(get_current_officer)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM screenings WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    
    if not case:
        conn.close()
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "stage": "case_lookup",
                "error": "CASE_NOT_FOUND",
                "message": f"Case dossier '{case_id}' was not found. Please initiate a new screening."
            }
        )
        
    actual_type = doc_type or case["doc_type"] or "Passport"
    doc_img_rel = case["doc_image_path"] or "samples/sample_genuine_passport.jpg"
    doc_img_abs = str(BASE_DIR / "data" / doc_img_rel) if not Path(doc_img_rel).is_absolute() else doc_img_rel
    
    if not os.path.exists(doc_img_abs):
        # Check in SAMPLES_DIR or UPLOADS_DIR
        alt_path = SAMPLES_DIR / Path(doc_img_rel).name
        if alt_path.exists():
            doc_img_abs = str(alt_path)
        else:
            alt_path = UPLOADS_DIR / Path(doc_img_rel).name
            if alt_path.exists():
                doc_img_abs = str(alt_path)
            else:
                conn.close()
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "stage": "file_verification",
                        "error": "FILE_NOT_FOUND",
                        "message": "The uploaded document file is missing or was removed. Please upload the file again."
                    }
                )

    # Run OCR Extraction Engine on the actual image
    ocr_result = extract_document_ocr(doc_img_abs, doc_type=actual_type, scenario_hint=scenario_hint)
    
    person_name = ocr_result.get("full_name", {}).get("value", "Not detected")
    doc_number = ocr_result.get("document_number", {}).get("value", "Not detected")
    
    cursor.execute("""
    UPDATE screenings SET extracted_data = ?, person_name = ?, doc_number = ?, doc_type = ?, updated_at = ?
    WHERE case_id = ?
    """, (json.dumps(ocr_result), person_name, doc_number, actual_type, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), case_id))
    conn.commit()
    conn.close()

    log_audit_event(case_id, "OCR_EXTRACTION_COMPLETED", officer.get("full_name", "Officer"), {
        "extracted_name": person_name,
        "extracted_doc_num": doc_number,
        "mrz_detected": ocr_result.get("mrz_detected", False),
        "overall_confidence": ocr_result.get("overall_ocr_confidence", 95.0),
        "total_time_sec": ocr_result.get("timing", {}).get("total_time_sec", 0.0)
    })

    return {
        "success": ocr_result.get("success", True),
        "case_id": case_id,
        "ocr_data": ocr_result,
        "timing": ocr_result.get("timing", {}),
        "raw_ocr_text": ocr_result.get("raw_ocr_text", "")
    }


@app.post("/api/ocr/confirm")
def confirm_ocr(req: OcrConfirmRequest, officer: Dict[str, Any] = Depends(get_current_officer)):
    person_name = req.extracted_data.get("full_name", {}).get("value", "Not detected")
    doc_number = req.extracted_data.get("document_number", {}).get("value", "Not detected")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE screenings SET extracted_data = ?, person_name = ?, doc_number = ?, updated_at = ?
    WHERE case_id = ?
    """, (json.dumps(req.extracted_data), person_name, doc_number, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), req.case_id))
    conn.commit()
    conn.close()

    log_audit_event(req.case_id, "OCR_DATA_CONFIRMED_BY_OFFICER", officer.get("full_name", "Officer"), {
        "person_name": person_name,
        "doc_number": doc_number
    })

    return {"status": "success", "message": "OCR data confirmed and updated."}

@app.post("/api/document/validate")
def run_validation(
    case_id: str = Form(...),
    officer: Dict[str, Any] = Depends(get_current_officer)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM screenings WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")
        
    extracted = json.loads(case["extracted_data"]) if case["extracted_data"] else {}
    val_result = validate_extracted_document(extracted, doc_type=case["doc_type"])
    
    cursor.execute("""
    UPDATE screenings SET validation_data = ?, updated_at = ?
    WHERE case_id = ?
    """, (json.dumps(val_result), datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), case_id))
    conn.commit()
    conn.close()

    log_audit_event(case_id, "DOCUMENT_VALIDATION_COMPLETED", officer.get("full_name", "Officer"), {
        "overall_status": val_result["overall_status"],
        "passed_checks": val_result["passed_count"],
        "failed_checks": val_result["failed_count"],
        "warning_checks": val_result["warning_count"]
    })

    return {"case_id": case_id, "validation_data": val_result}

@app.post("/api/tampering/analyze")
def run_tampering_analysis(
    case_id: str = Form(...),
    scenario_hint: Optional[str] = Form(None),
    officer: Dict[str, Any] = Depends(get_current_officer)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM screenings WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")
        
    doc_img_rel = case["doc_image_path"] or "samples/sample_genuine_passport.jpg"
    doc_img_abs = str(BASE_DIR / "data" / doc_img_rel) if not Path(doc_img_rel).is_absolute() else doc_img_rel
    
    tamper_result = analyze_document_tampering(doc_img_abs, doc_type=case["doc_type"], scenario_hint=scenario_hint)
    
    ela_rel = f"uploads/{tamper_result['ela_image_file']}"
    
    cursor.execute("""
    UPDATE screenings SET tampering_data = ?, ela_image_path = ?, updated_at = ?
    WHERE case_id = ?
    """, (json.dumps(tamper_result), ela_rel, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), case_id))
    conn.commit()
    conn.close()

    log_audit_event(case_id, "TAMPERING_ANALYSIS_COMPLETED", officer.get("full_name", "Officer"), {
        "tampering_risk": tamper_result["tampering_risk"],
        "model_confidence": tamper_result["model_confidence"],
        "suspicious_regions_count": len(tamper_result.get("suspicious_regions", []))
    })

    return {"case_id": case_id, "tampering_data": tamper_result, "ela_image_path": ela_rel}

@app.post("/api/face/verify")
async def run_face_verification(
    case_id: str = Form(...),
    scenario_hint: Optional[str] = Form(None),
    live_image: Optional[UploadFile] = File(None),
    officer: Dict[str, Any] = Depends(get_current_officer)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM screenings WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")

    doc_face_rel = case["face_doc_path"]
    doc_face_abs = str(BASE_DIR / "data" / doc_face_rel) if doc_face_rel else None

    live_face_abs = None
    live_face_rel = None
    
    if live_image:
        live_filename = f"live_face_{case_id}_{uuid.uuid4().hex[:4]}.jpg"
        live_abs = UPLOADS_DIR / live_filename
        with open(live_abs, "wb") as buf:
            shutil.copyfileobj(live_image.file, buf)
        live_face_rel = f"uploads/{live_filename}"
        live_face_abs = str(live_abs)
    elif scenario_hint:
        live_face_rel = case["face_live_path"]
        live_face_abs = str(BASE_DIR / "data" / live_face_rel) if live_face_rel else None

    face_result = verify_face_biometrics(doc_face_abs, live_face_abs, scenario_hint=scenario_hint)

    cursor.execute("""
    UPDATE screenings SET face_data = ?, face_doc_path = ?, face_live_path = ?, updated_at = ?
    WHERE case_id = ?
    """, (json.dumps(face_result), doc_face_rel, live_face_rel, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), case_id))
    conn.commit()
    conn.close()

    log_audit_event(case_id, "FACE_VERIFICATION_COMPLETED", officer.get("full_name", "Officer"), {
        "status": face_result["status"],
        "match_score": face_result.get("match_score"),
        "liveness_status": face_result.get("liveness_assessment", {}).get("status")
    })

    return {
        "case_id": case_id,
        "face_data": face_result,
        "face_doc_path": doc_face_rel,
        "face_live_path": live_face_rel
    }

@app.post("/api/risk/calculate")
def run_risk_assessment(
    case_id: str = Form(...),
    officer: Dict[str, Any] = Depends(get_current_officer)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM screenings WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")

    ocr_data = json.loads(case["extracted_data"]) if case["extracted_data"] else {}
    val_data = json.loads(case["validation_data"]) if case["validation_data"] else {}
    tamper_data = json.loads(case["tampering_data"]) if case["tampering_data"] else {}
    face_data = json.loads(case["face_data"]) if case["face_data"] else {}

    risk_result = calculate_screening_risk(ocr_data, val_data, tamper_data, face_data)

    cursor.execute("""
    UPDATE screenings SET
        overall_risk_score = ?,
        risk_level = ?,
        status = ?,
        risk_factors = ?,
        updated_at = ?
    WHERE case_id = ?
    """, (
        risk_result["overall_risk_score"],
        risk_result["risk_level"],
        risk_result["document_status"],
        json.dumps(risk_result["risk_factors"]),
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        case_id
    ))
    conn.commit()
    conn.close()

    log_audit_event(case_id, "RISK_ASSESSMENT_GENERATED", officer.get("full_name", "Officer"), {
        "overall_risk_score": risk_result["overall_risk_score"],
        "risk_level": risk_result["risk_level"],
        "document_status": risk_result["document_status"]
    })

    return {"case_id": case_id, "risk_data": risk_result}

@app.post("/api/review")
def submit_officer_review(req: OfficerReviewRequest, officer: Dict[str, Any] = Depends(get_current_officer)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM screenings WHERE case_id = ?", (req.case_id,))
    case = cursor.fetchone()
    
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")

    cursor.execute("""
    UPDATE screenings SET officer_decision = ?, officer_notes = ?, updated_at = ?
    WHERE case_id = ?
    """, (req.decision, req.notes, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), req.case_id))
    conn.commit()
    conn.close()

    log_audit_event(req.case_id, "OFFICER_REVIEW_SAVED", officer.get("full_name", "Officer"), {
        "decision": req.decision,
        "notes": req.notes,
        "officer_badge": officer.get("badge_number", "N/A")
    })

    return {"status": "success", "message": "Officer decision and remarks recorded in audit trail."}

@app.get("/api/screening/{case_id}")
def get_screening_case(case_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM screenings WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    conn.close()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    data = dict(case)
    for field in ["extracted_data", "validation_data", "tampering_data", "face_data", "risk_factors"]:
        if data.get(field):
            try:
                data[field] = json.loads(data[field])
            except Exception:
                pass
    return data

@app.get("/api/screenings")
def list_screenings(
    query: Optional[str] = None,
    status_filter: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 50
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = "SELECT case_id, person_name, doc_type, doc_number, created_at, overall_risk_score, status, risk_level, officer_name FROM screenings WHERE 1=1"
    params = []
    
    if query:
        sql += " AND (case_id LIKE ? OR person_name LIKE ? OR doc_number LIKE ?)"
        q_like = f"%{query}%"
        params.extend([q_like, q_like, q_like])
        
    if status_filter and status_filter != "ALL":
        sql += " AND status = ?"
        params.append(status_filter)
        
    if doc_type and doc_type != "ALL":
        sql += " AND doc_type = ?"
        params.append(doc_type)
        
# ----------------- DASHBOARD ANALYTICS ENDPOINTS -----------------
class SaveCompletedScreeningRequest(BaseModel):
    case_id: str
    domain: str = "01 — AIRLINES & GATE AGENTS"
    doc_type: str = "Passport"
    person_name: Optional[str] = "Traveler"
    doc_number: Optional[str] = "Not detected"
    overall_risk_score: int = 0
    risk_level: str = "LOW"
    status: str = "LIKELY GENUINE"
    risk_factors: Optional[List[Dict[str, Any]]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    validation_data: Optional[Dict[str, Any]] = None
    tampering_data: Optional[Dict[str, Any]] = None

@app.post("/api/screening/save-completed")
def save_completed_screening(req: SaveCompletedScreeningRequest, officer: Dict[str, Any] = Depends(get_current_officer)):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO screenings (
        case_id, domain, created_at, updated_at, officer_id, officer_name, doc_type,
        person_name, doc_number, status, overall_risk_score, risk_level,
        risk_factors, extracted_data, validation_data, tampering_data
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(case_id) DO UPDATE SET
        domain = excluded.domain,
        person_name = excluded.person_name,
        doc_number = excluded.doc_number,
        status = excluded.status,
        overall_risk_score = excluded.overall_risk_score,
        risk_level = excluded.risk_level,
        risk_factors = excluded.risk_factors,
        extracted_data = excluded.extracted_data,
        validation_data = excluded.validation_data,
        tampering_data = excluded.tampering_data,
        updated_at = excluded.updated_at
    """, (
        req.case_id, req.domain, timestamp, timestamp, officer.get("id", 1), officer.get("full_name", "Security Officer"),
        req.doc_type, req.person_name, req.doc_number, req.status, req.overall_risk_score, req.risk_level,
        json.dumps(req.risk_factors or []), json.dumps(req.extracted_data or {}),
        json.dumps(req.validation_data or {}), json.dumps(req.tampering_data or {})
    ))
    conn.commit()
    conn.close()

    log_audit_event(req.case_id, "SCREENING_COMPLETED_AND_RECORDED", officer.get("full_name", "Officer"), {
        "domain": req.domain,
        "doc_type": req.doc_type,
        "person_name": req.person_name,
        "overall_risk_score": req.overall_risk_score,
        "status": req.status,
        "risk_level": req.risk_level
    })

    return {"status": "success", "message": f"Screening case '{req.case_id}' recorded successfully."}

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Overall counts (completed cases)
    cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN risk_level = 'LOW' OR status = 'LIKELY GENUINE' THEN 1 ELSE 0 END) as genuine,
        SUM(CASE WHEN (risk_level = 'MEDIUM' OR status LIKE '%MEDIUM%') AND status != 'REQUIRES MANUAL REVIEW' THEN 1 ELSE 0 END) as medium,
        SUM(CASE WHEN risk_level = 'HIGH' OR status = 'LIKELY FAKE / SUSPICIOUS' OR status LIKE '%HIGH RISK%' THEN 1 ELSE 0 END) as high,
        SUM(CASE WHEN status = 'REQUIRES MANUAL REVIEW' OR risk_level = 'MANUAL_REVIEW' THEN 1 ELSE 0 END) as manual_review
    FROM screenings
    WHERE status != 'PROCESSING'
    """)
    overall_row = cursor.fetchone()
    total_overall = overall_row["total"] or 0
    genuine_overall = overall_row["genuine"] or 0
    medium_overall = overall_row["medium"] or 0
    high_overall = overall_row["high"] or 0
    manual_review_overall = overall_row["manual_review"] or 0

    cat_sum = genuine_overall + medium_overall + high_overall + manual_review_overall
    if cat_sum < total_overall:
        manual_review_overall += (total_overall - cat_sum)

    # 2. Today's counts
    today_prefix = datetime.utcnow().strftime("%Y-%m-%d")
    yesterday_prefix = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN risk_level = 'LOW' OR status = 'LIKELY GENUINE' THEN 1 ELSE 0 END) as genuine,
        SUM(CASE WHEN (risk_level = 'MEDIUM' OR status LIKE '%MEDIUM%') AND status != 'REQUIRES MANUAL REVIEW' THEN 1 ELSE 0 END) as medium,
        SUM(CASE WHEN risk_level = 'HIGH' OR status = 'LIKELY FAKE / SUSPICIOUS' OR status LIKE '%HIGH RISK%' THEN 1 ELSE 0 END) as high,
        SUM(CASE WHEN status = 'REQUIRES MANUAL REVIEW' OR risk_level = 'MANUAL_REVIEW' THEN 1 ELSE 0 END) as manual_review
    FROM screenings
    WHERE status != 'PROCESSING' AND created_at LIKE ?
    """, (f"{today_prefix}%",))
    today_row = cursor.fetchone()
    total_today = today_row["total"] or 0
    genuine_today = today_row["genuine"] or 0
    medium_today = today_row["medium"] or 0
    high_today = today_row["high"] or 0
    manual_review_today = today_row["manual_review"] or 0

    cat_today_sum = genuine_today + medium_today + high_today + manual_review_today
    if cat_today_sum < total_today:
        manual_review_today += (total_today - cat_today_sum)

    cursor.execute("SELECT COUNT(*) as total FROM screenings WHERE status != 'PROCESSING' AND created_at LIKE ?", (f"{yesterday_prefix}%",))
    yesterday_total = cursor.fetchone()["total"] or 0

    if yesterday_total > 0:
        diff_pct = round(((total_today - yesterday_total) / yesterday_total) * 100, 1)
        trend_label = f"+{diff_pct}% from yesterday" if diff_pct >= 0 else f"{diff_pct}% from yesterday"
    elif total_today > 0:
        trend_label = "+100% (New today)"
    else:
        trend_label = "0% from yesterday"

    # 3. Risk distribution percentages
    genuine_pct = round((genuine_overall / total_overall) * 100, 1) if total_overall > 0 else 0.0
    medium_pct = round((medium_overall / total_overall) * 100, 1) if total_overall > 0 else 0.0
    high_pct = round((high_overall / total_overall) * 100, 1) if total_overall > 0 else 0.0
    manual_review_pct = round((manual_review_overall / total_overall) * 100, 1) if total_overall > 0 else 0.0

    conn.close()

    return {
        "today": {
            "total": total_today,
            "genuine": genuine_today,
            "medium": medium_today,
            "high": high_today,
            "manualReview": manual_review_today,
            "trend": trend_label
        },
        "overall": {
            "total": total_overall,
            "genuine": genuine_overall,
            "medium": medium_overall,
            "high": high_overall,
            "manualReview": manual_review_overall
        },
        "riskDistribution": {
            "genuine": genuine_pct,
            "medium": medium_pct,
            "high": high_pct,
            "manualReview": manual_review_pct
        }
    }

@app.get("/api/dashboard/recent")
def get_dashboard_recent(limit: int = 10):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT case_id, domain, doc_type, person_name, doc_number, overall_risk_score, risk_level, status, created_at
    FROM screenings
    WHERE status != 'PROCESSING'
    ORDER BY created_at DESC
    LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/dashboard/domain-stats")
def get_dashboard_domain_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        COALESCE(domain, '01 — AIRLINES & GATE AGENTS') as domain,
        COUNT(*) as count
    FROM screenings
    WHERE status != 'PROCESSING'
    GROUP BY domain
    ORDER BY count DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/dashboard/document-stats")
def get_dashboard_document_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        COALESCE(doc_type, 'Passport') as doc_type,
        COUNT(*) as count
    FROM screenings
    WHERE status != 'PROCESSING'
    GROUP BY doc_type
    ORDER BY count DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# ----------------- AUDIT TRAIL ENDPOINTS -----------------
@app.get("/api/audit-log")
def get_audit_trail(case_id: Optional[str] = None, limit: int = 100):
    logs = get_all_audit_logs(case_id=case_id, limit=limit)
    integrity = verify_audit_integrity()
    return {
        "logs": logs,
        "integrity_status": integrity
    }

# ----------------- DEMO WATCHLIST DATABASE -----------------
@app.get("/api/database")
def get_watchlist_records(query: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if query:
        cursor.execute("SELECT * FROM demo_watchlist WHERE doc_number LIKE ? OR full_name LIKE ? ORDER BY id DESC", (f"%{query}%", f"%{query}%"))
    else:
        cursor.execute("SELECT * FROM demo_watchlist ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.post("/api/database")
def add_or_update_watchlist_record(req: WatchlistEntryRequest, officer: Dict[str, Any] = Depends(get_current_officer)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO demo_watchlist (doc_number, full_name, nationality, dob, status, reason, alert_level)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (req.doc_number, req.full_name, req.nationality, req.dob, req.status, req.reason, req.alert_level))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": f"Demo Database record '{req.doc_number}' updated."}

# ----------------- PDF REPORT DOWNLOAD -----------------
@app.get("/api/report/{case_id}")
def download_case_report(case_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM screenings WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    conn.close()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case_data = dict(case)
    pdf_filename = f"DocShield_Report_{case_id}.pdf"
    pdf_path = generate_pdf_report(case_data, pdf_filename)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_filename,
        headers={"Content-Disposition": f"attachment; filename={pdf_filename}"}
    )

# ----------------- IMAGE ASSET STREAMING -----------------
@app.get("/api/image/{subpath:path}")
def serve_image(subpath: str):
    image_path = BASE_DIR / "data" / subpath
    if not image_path.exists():
        image_path = SAMPLES_DIR / Path(subpath).name
        if not image_path.exists():
            image_path = UPLOADS_DIR / Path(subpath).name
            if not image_path.exists():
                raise HTTPException(status_code=404, detail="Image file not found")
            
    return FileResponse(str(image_path))

# ----------------- STATIC FRONTEND SERVING -----------------
try:
    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
except Exception as e:
    print(f"StaticFiles mounting notice: {e}")
