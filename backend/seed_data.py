import json
from datetime import datetime, timedelta
from .database import get_db_connection, init_db, log_audit_event
from .auth import get_password_hash
from .sample_assets import generate_sample_documents

def seed_database():
    init_db()
    generate_sample_documents()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Seed Officers
    cursor.execute("SELECT COUNT(*) FROM officers")
    if cursor.fetchone()[0] == 0:
        officers_data = [
            ("officer.sharma", "Officer Vikram Sharma", "BSF-IMM-8924", "Border Security & Immigration Control", "Senior Screening Officer", get_password_hash("password123")),
            ("officer.patel", "Officer Priya Patel", "BSF-IMM-9102", "International Airport Division", "Biometrics & Fraud Specialist", get_password_hash("password123")),
            ("inspector.kumar", "Inspector Rajesh Kumar", "BSF-IMM-7741", "Border Command Center", "Superintending Officer", get_password_hash("password123"))
        ]
        
        for u, f, b, d, r, p in officers_data:
            cursor.execute("""
            INSERT INTO officers (username, full_name, badge_number, department, role, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (u, f, b, d, r, p, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")))
            
        print("Officers successfully seeded.")

    # 2. Seed Demo Watchlist Database
    cursor.execute("SELECT COUNT(*) FROM demo_watchlist")
    if cursor.fetchone()[0] == 0:
        watchlist_records = [
            ("K28491047", "JOHNATHAN EDWARD DOE", "IND", "1988-06-14", "VALID", "Active biometric travel document in good standing", "LOW"),
            ("V84729104", "ALEX K. VANCE", "GBR", "1982-11-23", "STOLEN", "Reported stolen blank visa folio (Embassy Transit Incident 2021)", "HIGH"),
            ("ID-90418247", "MARIA ELENA GOMEZ", "ESP", "1991-03-29", "EXPIRED", "Expired Schengen identification credential", "MEDIUM"),
            ("P99824100", "VIKTOR ZHDANOV", "RUS", "1979-10-05", "BLACKLISTED", "Interpol Red Notice Ref #2024-IN-9812: Document Counterfeiting", "HIGH"),
            ("D48291023", "SAMUEL OKONKWO", "NGA", "1985-04-12", "REVIEW_REQUIRED", "Flagged for Secondary Physical Inspection (Border Alert #88)", "MEDIUM"),
            ("P11928472", "CHEN WEI", "CHN", "1993-12-01", "VALID", "Standard valid international tourist document", "LOW")
        ]
        
        for num, name, nat, dob, stat, reason, alert in watchlist_records:
            cursor.execute("""
            INSERT OR REPLACE INTO demo_watchlist (doc_number, full_name, nationality, dob, status, reason, alert_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (num, name, nat, dob, stat, reason, alert))
            
        print("Demo Watchlist Database successfully seeded.")

    # 3. Seed Sample Historical Cases
    cursor.execute("SELECT COUNT(*) FROM screenings")
    need_sample_cases = cursor.fetchone()[0] == 0
    
    sample_cases = []
    if need_sample_cases:
        sample_cases = [
            {
                "case_id": "CASE-1041",
                "created_at": (datetime.utcnow() - timedelta(hours=3, minutes=20)).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "officer_name": "Officer Vikram Sharma",
                "doc_type": "Passport",
                "person_name": "JOHNATHAN EDWARD DOE",
                "doc_number": "K28491047",
                "status": "VERIFIED",
                "overall_risk_score": 14,
                "risk_level": "LOW",
                "officer_decision": "CLEARED_FOR_ENTRY",
                "officer_notes": "All biometric and optical checks passed. No tampering indicators. Direct clearance granted.",
                "doc_image_path": "samples/sample_genuine_passport.jpg"
            },
            {
                "case_id": "CASE-1042",
                "created_at": (datetime.utcnow() - timedelta(hours=1, minutes=45)).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "officer_name": "Officer Vikram Sharma",
                "doc_type": "Visa",
                "person_name": "ALEX K. VANCE",
                "doc_number": "V84729104",
                "status": "HIGH RISK",
                "overall_risk_score": 82,
                "risk_level": "HIGH",
                "officer_decision": "ESCALATED_SECONDARY_INSPECTION",
                "officer_notes": "High tampering anomaly: spliced photo boundary + altered expiry year (2029) + stolen folio alert in Demo DB.",
                "doc_image_path": "samples/sample_tampered_visa.jpg"
            },
            {
                "case_id": "CASE-1043",
                "created_at": (datetime.utcnow() - timedelta(minutes=35)).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "officer_name": "Officer Priya Patel",
                "doc_type": "National ID",
                "person_name": "MARIA ELENA GOMEZ",
                "doc_number": "ID-90418247",
                "status": "REVIEW REQUIRED",
                "overall_risk_score": 58,
                "risk_level": "MEDIUM",
                "officer_decision": "REFER_EMBASSY_CONSULAR",
                "officer_notes": "Document expired in 2023. Traveler referred to consular liaison desk for emergency travel document renewal.",
                "doc_image_path": "samples/sample_expired_id.jpg"
            }
        ]
        
        for c in sample_cases:
            cursor.execute("""
            INSERT INTO screenings (
                case_id, created_at, updated_at, officer_id, officer_name, doc_type, person_name, doc_number,
                status, overall_risk_score, risk_level, extracted_data, validation_data, tampering_data,
                face_data, risk_factors, officer_decision, officer_notes, doc_image_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["case_id"], c["created_at"], c["created_at"], 1, c["officer_name"], c["doc_type"],
                c["person_name"], c["doc_number"], c["status"], c["overall_risk_score"], c["risk_level"],
                json.dumps({"full_name": c["person_name"], "document_number": c["doc_number"]}),
                json.dumps({"overall_status": "PASSED" if c["status"] == "VERIFIED" else "FAILED"}),
                json.dumps({"tampering_risk": "HIGH" if "HIGH" in c["status"] else "LOW", "model_confidence": 92.4}),
                json.dumps({"status": "MATCH" if c["status"] == "VERIFIED" else "MISMATCH", "match_score": 94 if c["status"] == "VERIFIED" else 32}),
                json.dumps([{"name": "Tampering & Forensic Integrity", "status": "PASSED" if c["status"] == "VERIFIED" else "CRITICAL"}]),
                c["officer_decision"], c["officer_notes"], c["doc_image_path"]
            ))

    conn.commit()
    conn.close()

    # Now log audit events with separate committed transactions
    if need_sample_cases:
        for c in sample_cases:
            log_audit_event(c["case_id"], "SCREENING_CREATED", c["officer_name"], {"action": "Initial document screening record generated", "doc_type": c["doc_type"]})
            log_audit_event(c["case_id"], "OCR_EXTRACTED", c["officer_name"], {"person_name": c["person_name"], "doc_number": c["doc_number"]})
            log_audit_event(c["case_id"], "FORENSIC_TAMPER_SCANNED", c["officer_name"], {"risk_level": c["risk_level"], "tampering_score": c["overall_risk_score"]})
            log_audit_event(c["case_id"], "OFFICER_DECISION_RECORDED", c["officer_name"], {"decision": c["officer_decision"], "notes": c["officer_notes"]})
            
        print("Sample historical screening cases and audit blocks seeded.")

if __name__ == "__main__":
    seed_database()
