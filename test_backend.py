import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from backend.database import init_db, verify_audit_integrity, get_db_connection
from backend.seed_data import seed_database
from backend.engines.ocr_engine import extract_document_ocr
from backend.engines.validation_engine import validate_extracted_document
from backend.engines.tampering_engine import analyze_document_tampering
from backend.engines.face_engine import verify_face_biometrics
from backend.engines.risk_engine import calculate_screening_risk
from backend.engines.report_engine import generate_pdf_report

def run_tests():
    print("[TEST 1/6] Initializing Database and Seeding...")
    init_db()
    seed_database()
    print("[PASS] Database initialized and seeded successfully.")

    print("\n[TEST 2/6] Verifying Cryptographic Audit Hash Chain...")
    audit_res = verify_audit_integrity()
    print(f"[PASS] Audit Integrity Check: {audit_res['message']} (Total Blocks: {audit_res['total_blocks']})")
    assert audit_res["valid"] is True, "Audit chain integrity failed!"

    print("\n[TEST 3/6] Testing Scenario 1 (Genuine Passport)...")
    doc1 = str(BASE_DIR / "data" / "samples" / "sample_genuine_passport.jpg")
    p1_doc = str(BASE_DIR / "data" / "samples" / "doc_face_genuine.jpg")
    p1_live = str(BASE_DIR / "data" / "samples" / "live_face_genuine.jpg")

    ocr1 = extract_document_ocr(doc1, doc_type="Passport", scenario_hint="genuine_passport")
    val1 = validate_extracted_document(ocr1, doc_type="Passport")
    tamp1 = analyze_document_tampering(doc1, doc_type="Passport", scenario_hint="genuine_passport")
    face1 = verify_face_biometrics(p1_doc, p1_live, scenario_hint="genuine_passport")
    risk1 = calculate_screening_risk(ocr1, val1, tamp1, face1)

    print(f"  - OCR Confidence: {ocr1['overall_ocr_confidence']}%")
    print(f"  - Validation Status: {val1['overall_status']}")
    print(f"  - Tampering Risk: {tamp1['tampering_risk']} (Confidence: {tamp1['model_confidence']}%)")
    print(f"  - Face Match: {face1['match_score']}% ({face1['status']})")
    print(f"  - Overall Risk Score: {risk1['overall_risk_score']}/100 -> Status: {risk1['document_status']}")
    assert risk1["overall_risk_score"] <= 30, f"Expected Low Risk for genuine document, got {risk1['overall_risk_score']}"

    print("\n[TEST 4/6] Testing Scenario 2 (Tampered Visa with Spliced Photo)...")
    doc2 = str(BASE_DIR / "data" / "samples" / "sample_tampered_visa.jpg")
    p2_doc = str(BASE_DIR / "data" / "samples" / "doc_face_tampered.jpg")
    p2_live = str(BASE_DIR / "data" / "samples" / "live_face_tampered.jpg")

    ocr2 = extract_document_ocr(doc2, doc_type="Visa", scenario_hint="tampered_visa")
    val2 = validate_extracted_document(ocr2, doc_type="Visa")
    tamp2 = analyze_document_tampering(doc2, doc_type="Visa", scenario_hint="tampered_visa")
    face2 = verify_face_biometrics(p2_doc, p2_live, scenario_hint="tampered_visa")
    risk2 = calculate_screening_risk(ocr2, val2, tamp2, face2)

    print(f"  - OCR Confidence: {ocr2['overall_ocr_confidence']}%")
    print(f"  - Validation Status: {val2['overall_status']}")
    print(f"  - Tampering Risk: {tamp2['tampering_risk']} (Confidence: {tamp2['model_confidence']}%)")
    print(f"  - Flagged Bounding Boxes: {len(tamp2['bounding_boxes'])}")
    print(f"  - Face Match: {face2['match_score']}% ({face2['status']})")
    print(f"  - Overall Risk Score: {risk2['overall_risk_score']}/100 -> Status: {risk2['document_status']}")
    assert risk2["overall_risk_score"] >= 60, f"Expected High Risk for tampered document, got {risk2['overall_risk_score']}"

    print("\n[TEST 5/6] Testing Scenario 3 (Expired National ID)...")
    doc3 = str(BASE_DIR / "data" / "samples" / "sample_expired_id.jpg")
    p3_doc = str(BASE_DIR / "data" / "samples" / "doc_face_expired.jpg")
    p3_live = str(BASE_DIR / "data" / "samples" / "live_face_expired.jpg")

    ocr3 = extract_document_ocr(doc3, doc_type="National ID", scenario_hint="expired_id")
    val3 = validate_extracted_document(ocr3, doc_type="National ID")
    tamp3 = analyze_document_tampering(doc3, doc_type="National ID", scenario_hint="expired_id")
    face3 = verify_face_biometrics(p3_doc, p3_live, scenario_hint="expired_id")
    risk3 = calculate_screening_risk(ocr3, val3, tamp3, face3)

    print(f"  - Validation Status: {val3['overall_status']}")
    print(f"  - Tampering Risk: {tamp3['tampering_risk']}")
    print(f"  - Overall Risk Score: {risk3['overall_risk_score']}/100 -> Status: {risk3['document_status']}")
    assert risk3["overall_risk_score"] > 30, f"Expected Review/Medium Risk for expired document, got {risk3['overall_risk_score']}"

    print("\n[TEST 6/6] Testing PDF Dossier Report Generation...")
    sample_case_data = {
        "case_id": "CASE-TEST-99",
        "created_at": "2026-09-02 15:45:00 UTC",
        "officer_name": "Officer Vikram Sharma",
        "doc_type": "Passport",
        "person_name": "JOHNATHAN EDWARD DOE",
        "doc_number": "K28491047",
        "status": "VERIFIED",
        "overall_risk_score": 14,
        "extracted_data": ocr1,
        "validation_data": val1,
        "tampering_data": tamp1,
        "face_data": face1,
        "officer_decision": "CLEARED_FOR_ENTRY",
        "officer_notes": "All biometric, optical, and ELA forensic checks passed."
    }
    pdf_path = generate_pdf_report(sample_case_data, "SecureScreen_Report_CASE-TEST-99.pdf")
    print(f"[PASS] PDF Report successfully generated at: {pdf_path}")
    assert os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0, "PDF generation failed or file is empty!"

    print("\n" + "=" * 60)
    print("  ALL 6 SECURESCREEN AI TEST SUITES PASSED FLAWLESSLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
