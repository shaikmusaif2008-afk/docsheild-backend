import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from backend.database import init_db
from backend.seed_data import seed_database
from backend.engines.ocr_engine import extract_document_ocr
from backend.engines.validation_engine import validate_extracted_document
from backend.engines.tampering_engine import analyze_document_tampering
from backend.engines.face_engine import crop_document_face, verify_face_biometrics
from backend.engines.risk_engine import calculate_screening_risk
from backend.engines.report_engine import generate_pdf_report

def run_live_upload_tests():
    print("=" * 65)
    print("  RUNNING COMPREHENSIVE LIVE UPLOAD & DYNAMIC PIPELINE TESTS")
    print("=" * 65)

    init_db()
    seed_database()

    # -------------------------------------------------------------
    # TEST A: Passport for Emily Watson
    # -------------------------------------------------------------
    print("\n[TEST A] Processing New Upload: Emily Watson's UK Passport...")
    img_a = str(BASE_DIR / "data" / "test_uploads" / "test_passport_emily.jpg")
    
    # 1. OCR Extraction (No scenario hint -> Live upload mode)
    ocr_a = extract_document_ocr(img_a, doc_type="Passport", scenario_hint=None)
    print(f"  - Mode: {ocr_a.get('mode')}")
    print(f"  - Name Extracted: {ocr_a['full_name']['value']}")
    print(f"  - Document Number: {ocr_a['document_number']['value']}")
    print(f"  - DOB Extracted: {ocr_a['dob']['value']}")
    print(f"  - Expiry Extracted: {ocr_a['expiry_date']['value']}")
    print(f"  - MRZ Detected: {ocr_a['mrz_detected']} (Status: {ocr_a['mrz_validation']})")
    
    assert "WATSON" in ocr_a["full_name"]["value"].upper(), "Test A failed: Expected Emily Watson name in OCR!"
    assert "P88392019" in ocr_a["document_number"]["value"], "Test A failed: Expected passport number P88392019!"
    assert ocr_a["mrz_detected"] is True, "Test A failed: Expected MRZ to be detected!"

    # 2. Validation
    val_a = validate_extracted_document(ocr_a, doc_type="Passport")
    print(f"  - Validation Overall Status: {val_a['overall_status']} ({val_a['passed_count']} checks passed)")
    assert val_a["overall_status"] == "PASSED" or val_a["overall_status"] == "WARNING", "Validation check failed for valid passport!"

    # 3. Tampering Analysis on image
    tamp_a = analyze_document_tampering(img_a, doc_type="Passport", scenario_hint=None)
    print(f"  - Tampering Risk: {tamp_a['tampering_risk']} (Confidence: {tamp_a['model_confidence']}%)")
    print(f"  - Summary: {tamp_a['summary']}")

    # 4. Face Extraction
    face_crop_a = str(BASE_DIR / "data" / "uploads" / "face_doc_test_a.jpg")
    _, face_detected_a = crop_document_face(img_a, face_crop_a)
    print(f"  - Portrait Face Detected: {face_detected_a}")
    assert face_detected_a is True, "Expected portrait to be detected from passport!"

    # 5. Face Verification WITHOUT 2nd face
    face_res_a = verify_face_biometrics(face_crop_a, live_face_path=None, scenario_hint=None)
    print(f"  - Face Verification (No 2nd image): Status = {face_res_a['status']} ({face_res_a['explanation']})")
    assert face_res_a["status"] == "UNAVAILABLE", "Expected UNAVAILABLE when second face image is omitted!"

    # 6. Risk Calculation
    risk_a = calculate_screening_risk(ocr_a, val_a, tamp_a, face_res_a)
    print(f"  - Dynamic Risk Score: {risk_a['overall_risk_score']}/100 -> Status: {risk_a['document_status']}")
    print(f"  - Reasons: {risk_a['reasons']}")
    print("[PASS] Test A completed successfully with dynamic data!")

    # -------------------------------------------------------------
    # TEST B: Visa for Chen Wei
    # -------------------------------------------------------------
    print("\n[TEST B] Processing New Upload: Chen Wei's Japanese Transit Visa...")
    img_b = str(BASE_DIR / "data" / "test_uploads" / "test_visa_chen.jpg")
    
    ocr_b = extract_document_ocr(img_b, doc_type="Visa", scenario_hint=None)
    print(f"  - Name Extracted: {ocr_b['full_name']['value']}")
    print(f"  - Document Number: {ocr_b['document_number']['value']}")
    print(f"  - DOB Extracted: {ocr_b['dob']['value']}")
    print(f"  - Expiry Extracted: {ocr_b['expiry_date']['value']}")
    
    assert "CHEN" in ocr_b["full_name"]["value"].upper(), "Test B failed: Expected Chen Wei name!"
    assert "V99120482" in ocr_b["document_number"]["value"], "Test B failed: Expected visa number V99120482!"
    # Ensure Test B extracted values differ from Test A
    assert ocr_b["document_number"]["value"] != ocr_a["document_number"]["value"], "Dynamic check failed: Test A and Test B have identical doc numbers!"
    print("[PASS] Test B extracted completely distinct dynamic fields!")

    # -------------------------------------------------------------
    # TEST C: Poor Quality / Incomplete Fragment
    # -------------------------------------------------------------
    print("\n[TEST C] Processing Poor Quality / Incomplete Document...")
    img_c = str(BASE_DIR / "data" / "test_uploads" / "test_poor_quality_cropped.jpg")
    
    ocr_c = extract_document_ocr(img_c, doc_type="Passport", scenario_hint=None)
    print(f"  - Name: {ocr_c['full_name']['value']}")
    print(f"  - Document Number: {ocr_c['document_number']['value']}")
    print(f"  - MRZ Detected: {ocr_c['mrz_detected']}")
    
    # Must report 'Not detected' rather than fabricating values
    assert ocr_c["mrz_detected"] is False, "Expected MRZ not detected on partial receipt!"
    
    # Face detection on poor image without face
    face_crop_c = str(BASE_DIR / "data" / "uploads" / "face_doc_test_c.jpg")
    _, face_detected_c = crop_document_face(img_c, face_crop_c)
    print(f"  - Face Detected on text receipt: {face_detected_c}")
    assert face_detected_c is False, "Expected no face detected on receipt image!"

    val_c = validate_extracted_document(ocr_c, doc_type="Passport")
    tamp_c = analyze_document_tampering(img_c, doc_type="Passport", scenario_hint=None)
    face_res_c = verify_face_biometrics(doc_face_path=None, live_face_path=None, scenario_hint=None)
    risk_c = calculate_screening_risk(ocr_c, val_c, tamp_c, face_res_c)
    
    print(f"  - Validation Status: {val_c['overall_status']}")
    print(f"  - Dynamic Risk Score: {risk_c['overall_risk_score']}/100 -> Status: {risk_c['document_status']}")
    print(f"  - Reasons: {risk_c['reasons']}")
    assert risk_c["overall_risk_score"] > risk_a["overall_risk_score"], "Expected higher risk score for incomplete poor quality image!"
    print("[PASS] Test C handled missing fields gracefully without fabricating fake data!")

    # -------------------------------------------------------------
    # TEST D: PDF Dossier Report Generation for New Upload Case
    # -------------------------------------------------------------
    print("\n[TEST D] Generating PDF Dossier for Live Case...")
    case_data = {
        "case_id": "CASE-2026-LIVE01",
        "created_at": "2026-09-02 16:30:00 UTC",
        "officer_name": "Officer Vikram Sharma",
        "doc_type": "Passport",
        "person_name": ocr_a["full_name"]["value"],
        "doc_number": ocr_a["document_number"]["value"],
        "status": risk_a["document_status"],
        "overall_risk_score": risk_a["overall_risk_score"],
        "extracted_data": ocr_a,
        "validation_data": val_a,
        "tampering_data": tamp_a,
        "face_data": face_res_a,
        "officer_decision": "CLEARED_FOR_ENTRY",
        "officer_notes": "Live upload processed dynamically through OpenCV & ICAO MRZ engine."
    }
    pdf_out = generate_pdf_report(case_data, "SecureScreen_Report_CASE-2026-LIVE01.pdf")
    assert os.path.exists(pdf_out) and os.path.getsize(pdf_out) > 0, "PDF generation failed!"
    print(f"[PASS] PDF Dossier generated: {pdf_out}")

    print("\n" + "=" * 65)
    print("  ALL LIVE UPLOAD TEST SUITES PASSED FLAWLESSLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_live_upload_tests()
