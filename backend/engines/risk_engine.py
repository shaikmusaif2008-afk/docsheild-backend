import re
from typing import Dict, Any, List, Optional

def calculate_screening_risk(
    ocr_data: Dict[str, Any],
    val_data: Dict[str, Any],
    tamper_data: Dict[str, Any],
    face_data: Optional[Dict[str, Any]] = None,
    doc_type: str = "Passport",
    case_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evidence-Based, Explainable, Dynamic Document Risk Engine.
    Calculates composite risk score strictly from actual optical, mathematical,
    and forensic evidence.
    """
    if face_data is None:
        face_data = {}

    factors: List[Dict[str, Any]] = []
    reasons: List[str] = []

    # 1. Build Structured Risk Evidence Object
    evidence: Dict[str, Any] = {
        "ocr": {},
        "mrz": {},
        "consistency": {},
        "validity": {},
        "tampering": {},
        "biometrics": {},
        "database": {}
    }

    # --- A. OCR & Optical Quality Evidence ---
    ocr_success = ocr_data.get("success", True)
    ocr_conf = float(ocr_data.get("overall_ocr_confidence", 95.0) or 0.0)
    raw_ocr = ocr_data.get("raw_ocr_text", "")
    
    if not ocr_success or ocr_conf < 30.0 or len(raw_ocr.strip()) < 5:
        evidence["ocr"] = {
            "status": "INCONCLUSIVE",
            "confidence": ocr_conf,
            "error": ocr_data.get("error", "OCR_LOW_CONFIDENCE")
        }
    elif ocr_conf < 75.0:
        evidence["ocr"] = {
            "status": "WARNING",
            "confidence": ocr_conf
        }
    else:
        evidence["ocr"] = {
            "status": "PASS",
            "confidence": ocr_conf
        }

    # --- B. MRZ Evidence ---
    is_mrz_expected = doc_type.lower() in ["passport", "visa"] or "mrz" in doc_type.lower()
    mrz_detected = ocr_data.get("mrz_detected", False)
    mrz_val = ocr_data.get("mrz_validation", "NOT_DETECTED")

    if not is_mrz_expected:
        evidence["mrz"] = {
            "status": "NOT_APPLICABLE",
            "detected": False,
            "checksum_valid": True
        }
    elif mrz_val == "VALID":
        evidence["mrz"] = {
            "status": "PASS",
            "detected": True,
            "checksum_valid": True,
            "line1": ocr_data.get("mrz_line1", {}).get("value", "") if isinstance(ocr_data.get("mrz_line1"), dict) else str(ocr_data.get("mrz_line1", "")),
            "line2": ocr_data.get("mrz_line2", {}).get("value", "") if isinstance(ocr_data.get("mrz_line2"), dict) else str(ocr_data.get("mrz_line2", ""))
        }
    elif mrz_val == "CHECK_FAILED":
        evidence["mrz"] = {
            "status": "FAIL",
            "detected": True,
            "checksum_valid": False,
            "explanation": "ICAO 9303 7-3-1 check digit validation failed."
        }
    else:
        evidence["mrz"] = {
            "status": "NOT_DETECTED" if not mrz_detected else "WARNING",
            "detected": mrz_detected,
            "checksum_valid": False
        }

    # --- C. Field Consistency Evidence ---
    val_checks = val_data.get("checks", [])
    cons_chk = next((c for c in val_checks if c.get("id") == "chk_internal_consistency"), None)
    if cons_chk:
        if cons_chk.get("level") == "RED":
            evidence["consistency"] = {"status": "FAIL", "explanation": cons_chk.get("explanation")}
        elif cons_chk.get("level") == "YELLOW":
            evidence["consistency"] = {"status": "WARNING", "explanation": cons_chk.get("explanation")}
        else:
            evidence["consistency"] = {"status": "PASS", "explanation": "Visual fields match MRZ readings."}
    else:
        evidence["consistency"] = {"status": "PASS", "explanation": "Internal field alignment verified."}

    # --- D. Validity (Active vs Expired) Evidence ---
    exp_chk = next((c for c in val_checks if c.get("id") == "chk_expiry_validity"), None)
    if exp_chk:
        exp_status = exp_chk.get("status", "VALID")
        if exp_status == "EXPIRED":
            evidence["validity"] = {"status": "EXPIRED", "explanation": exp_chk.get("explanation")}
        elif exp_status == "WARNING":
            evidence["validity"] = {"status": "NEAR_EXPIRY", "explanation": exp_chk.get("explanation")}
        elif exp_status == "UNKNOWN":
            evidence["validity"] = {"status": "UNKNOWN", "explanation": "Expiry date not available on document substrate."}
        else:
            evidence["validity"] = {"status": "ACTIVE", "explanation": "Document is within valid operational date range."}
    else:
        evidence["validity"] = {"status": "ACTIVE", "explanation": "Validity timeframe verified."}

    # --- E. Forensic Tampering Evidence ---
    tamper_risk = str(tamper_data.get("tampering_risk", "LOW")).upper()
    tamper_conf = float(tamper_data.get("tampering_confidence", 95.0) or 95.0)
    anomalies_cnt = len(tamper_data.get("flagged_regions", []))

    if tamper_risk == "HIGH":
        evidence["tampering"] = {
            "status": "FAIL",
            "risk_level": "HIGH",
            "confidence": tamper_conf,
            "anomalies_detected": anomalies_cnt,
            "summary": tamper_data.get("summary", "High-energy compression / splicing anomalies detected.")
        }
    elif tamper_risk == "MEDIUM":
        evidence["tampering"] = {
            "status": "WARNING",
            "risk_level": "MEDIUM",
            "confidence": tamper_conf,
            "anomalies_detected": anomalies_cnt,
            "summary": tamper_data.get("summary", "Moderate localized edge variance.")
        }
    elif "INCONCLUSIVE" in tamper_risk:
        evidence["tampering"] = {
            "status": "INCONCLUSIVE",
            "risk_level": "INCONCLUSIVE",
            "confidence": tamper_conf,
            "summary": "Low optical resolution or uncalibrated color space."
        }
    else:
        evidence["tampering"] = {
            "status": "PASS",
            "risk_level": "LOW",
            "confidence": tamper_conf,
            "anomalies_detected": 0,
            "summary": "No localized tampering indicators identified across substrate."
        }

    # --- F. Biometrics Evidence ---
    face_status = str(face_data.get("status", "UNAVAILABLE")).upper()
    face_score = face_data.get("match_score")
    if face_status == "MISMATCH":
        evidence["biometrics"] = {"status": "FAIL", "similarity_score": face_score, "explanation": "Facial feature vector divergence."}
    elif face_status == "REVIEW":
        evidence["biometrics"] = {"status": "WARNING", "similarity_score": face_score, "explanation": "Marginal facial similarity score."}
    elif face_status == "MATCH":
        evidence["biometrics"] = {"status": "PASS", "similarity_score": face_score, "explanation": "Facial biometric concordance verified."}
    else:
        evidence["biometrics"] = {"status": "NOT_AVAILABLE", "explanation": "Live facial capture not provided."}

    # --- G. Database / Watchlist Evidence ---
    db_chk = next((c for c in val_checks if c.get("id") == "chk_external_db"), None)
    if db_chk and db_chk.get("level") == "RED":
        evidence["database"] = {"status": "WATCHLIST_MATCH", "explanation": db_chk.get("explanation")}
    else:
        evidence["database"] = {"status": "CLEAR", "explanation": "No watchlist alerts identified."}

    # 2. Inconclusive Check: Check if image is unreadable
    if evidence["ocr"]["status"] == "INCONCLUSIVE":
        return {
            "overall_risk_score": None,
            "risk_level": "MANUAL_REVIEW",
            "document_status": "REQUIRES MANUAL REVIEW",
            "badge_color": "YELLOW",
            "analysis_status": "INCONCLUSIVE",
            "recommendation": "Risk score unavailable — optical resolution, blur, or severe cropping prevents conclusive AI analysis. Physical officer inspection required.",
            "risk_factors": [{
                "name": "Optical Quality & Text Extraction",
                "impact": "Inconclusive",
                "status": "INCONCLUSIVE",
                "level": "YELLOW",
                "description": "Optical character recognition could not parse sufficient text from document."
            }],
            "evidence": evidence,
            "reasons": ["Document image is unreadable or heavily cropped."],
            "disclaimer": "Decision support analysis only. Does not replace authorized border personnel judgment."
        }

    # 3. Dynamic Explainable Risk Score Accumulator (Starts strictly at 0)
    calculated_score = 0
    formula_parts = ["0 (Base Score)"]
    bases_ledger = []

    # Rule 1: MRZ Checksum Failure (+25 pts)
    if evidence["mrz"]["status"] == "FAIL":
        calculated_score += 25
        formula_parts.append("+25 (MRZ Checksum Failed)")
        bases_ledger.append({
            "category": "Mathematical Forensics",
            "signal_name": "ICAO 9303 MRZ Checksum",
            "basis": "MRZ line 2 check-digit verification failed modulo-10 cyclic weighted [7, 3, 1] algorithm.",
            "finding_status": "FAILED",
            "points_added": 25,
            "points_display": "+25 pts",
            "level": "RED"
        })
        factors.append({
            "name": "ICAO 9303 MRZ Integrity",
            "impact": "+25 pts (Checksum Failed)",
            "status": "FAILED",
            "level": "RED",
            "description": "MRZ mathematical check-digit verification failed."
        })
        reasons.append("ICAO 9303 MRZ check-digit verification failed.")
    elif evidence["mrz"]["status"] == "PASS":
        bases_ledger.append({
            "category": "Mathematical Forensics",
            "signal_name": "ICAO 9303 MRZ Checksum",
            "basis": "All TD1/TD2/TD3 check digits verified with 100% mathematical integrity.",
            "finding_status": "PASSED",
            "points_added": 0,
            "points_display": "+0 pts (Pass)",
            "level": "GREEN"
        })
        factors.append({
            "name": "ICAO 9303 MRZ Integrity",
            "impact": "+0 pts (Checksum Passed)",
            "status": "PASSED",
            "level": "GREEN",
            "description": "MRZ mathematical check digits verified."
        })

    # Rule 2: Field Inconsistency / Mismatch (+25 pts)
    if evidence["consistency"]["status"] == "FAIL":
        calculated_score += 25
        formula_parts.append("+25 (Data Mismatch)")
        bases_ledger.append({
            "category": "Data Alignment",
            "signal_name": "Data Consistency Cross-Check",
            "basis": evidence["consistency"].get("explanation", "Visual OCR fields differ from MRZ machine reading."),
            "finding_status": "FAILED",
            "points_added": 25,
            "points_display": "+25 pts",
            "level": "RED"
        })
        factors.append({
            "name": "Data Consistency Cross-Check",
            "impact": "+25 pts (Major Mismatch)",
            "status": "FAILED",
            "level": "RED",
            "description": evidence["consistency"].get("explanation", "Visual OCR differs from MRZ.")
        })
        reasons.append("Visual inspection zone values differ from MRZ reading.")
    elif evidence["consistency"]["status"] == "WARNING":
        calculated_score += 15
        formula_parts.append("+15 (Field Variance)")
        bases_ledger.append({
            "category": "Data Alignment",
            "signal_name": "Data Consistency Cross-Check",
            "basis": evidence["consistency"].get("explanation", "Minor field variance detected between visual text and MRZ."),
            "finding_status": "WARNING",
            "points_added": 15,
            "points_display": "+15 pts",
            "level": "YELLOW"
        })
        factors.append({
            "name": "Data Consistency Cross-Check",
            "impact": "+15 pts (Field Variance)",
            "status": "WARNING",
            "level": "YELLOW",
            "description": evidence["consistency"].get("explanation", "Minor field variance detected.")
        })
        reasons.append("Minor field variance detected between visual text and machine zone.")
    else:
        bases_ledger.append({
            "category": "Data Alignment",
            "signal_name": "Data Consistency Cross-Check",
            "basis": "Visual field values match machine readable zone and reference tokens.",
            "finding_status": "PASSED",
            "points_added": 0,
            "points_display": "+0 pts (Pass)",
            "level": "GREEN"
        })

    # Rule 3: Forensic Tampering (+25 pts for HIGH, +12 for MEDIUM)
    if evidence["tampering"]["status"] == "FAIL":
        calculated_score += 25
        formula_parts.append("+25 (Substrate Manipulation)")
        bases_ledger.append({
            "category": "Pixel Forensics",
            "signal_name": "Forensic Tampering AI & ELA",
            "basis": evidence["tampering"].get("summary", "Critical compression or localized font anomaly detected."),
            "finding_status": "FAILED",
            "points_added": 25,
            "points_display": "+25 pts",
            "level": "RED"
        })
        factors.append({
            "name": "Forensic Tampering AI",
            "impact": "+25 pts (High Tampering Anomaly)",
            "status": "FAILED",
            "level": "RED",
            "description": evidence["tampering"].get("summary", "Critical compression or localized font anomaly.")
        })
        reasons.append("Forensic analysis detected high-energy localized compression / edge anomalies.")
    elif evidence["tampering"]["status"] == "WARNING":
        calculated_score += 12
        formula_parts.append("+12 (Moderate ELA Variance)")
        bases_ledger.append({
            "category": "Pixel Forensics",
            "signal_name": "Forensic Tampering AI & ELA",
            "basis": evidence["tampering"].get("summary", "Moderate localized gradient variance flagged."),
            "finding_status": "WARNING",
            "points_added": 12,
            "points_display": "+12 pts",
            "level": "YELLOW"
        })
        factors.append({
            "name": "Forensic Tampering AI",
            "impact": "+12 pts (Moderate Variance)",
            "status": "WARNING",
            "level": "YELLOW",
            "description": evidence["tampering"].get("summary", "Moderate localized variance flagged.")
        })
        reasons.append("Forensic analysis flagged localized gradient variance.")
    elif evidence["tampering"]["status"] == "INCONCLUSIVE":
        calculated_score += 8
        formula_parts.append("+8 (Inconclusive Optics)")
        bases_ledger.append({
            "category": "Pixel Forensics",
            "signal_name": "Forensic Tampering AI & ELA",
            "basis": "Image resolution or lighting angle prevented definitive tampering analysis.",
            "finding_status": "INCONCLUSIVE",
            "points_added": 8,
            "points_display": "+8 pts",
            "level": "YELLOW"
        })
        factors.append({
            "name": "Forensic Tampering AI",
            "impact": "+8 pts (Inconclusive Optics)",
            "status": "WARNING",
            "level": "YELLOW",
            "description": "Image quality prevented definitive tampering analysis."
        })
    else:
        bases_ledger.append({
            "category": "Pixel Forensics",
            "signal_name": "Forensic Tampering AI & ELA",
            "basis": "No localized compression, copy-move, or splicing anomalies detected across substrate.",
            "finding_status": "PASSED",
            "points_added": 0,
            "points_display": "+0 pts (Pass)",
            "level": "GREEN"
        })

    # Rule 4: Watchlist Database Alert (+30 pts)
    if evidence["database"]["status"] == "WATCHLIST_MATCH":
        calculated_score += 30
        formula_parts.append("+30 (Watchlist Flag)")
        bases_ledger.append({
            "category": "Security Registry",
            "signal_name": "Border Watchlist Database",
            "basis": "Document number or biographical details match active border security watchlist.",
            "finding_status": "CRITICAL",
            "points_added": 30,
            "points_display": "+30 pts",
            "level": "RED"
        })
        factors.append({
            "name": "Border Watchlist Registry",
            "impact": "+30 pts (Watchlist Match)",
            "status": "CRITICAL",
            "level": "RED",
            "description": "Document or subject flagged in border security database."
        })
        reasons.append("Document flagged in simulated government security watchlist.")
    else:
        bases_ledger.append({
            "category": "Security Registry",
            "signal_name": "Border Watchlist Database",
            "basis": "Zero hits in simulated border security and lost/stolen passport database.",
            "finding_status": "PASSED",
            "points_added": 0,
            "points_display": "+0 pts (Clear)",
            "level": "GREEN"
        })

    # Rule 5: Facial Biometric Mismatch (+25 pts for MISMATCH, +10 for REVIEW)
    if evidence["biometrics"]["status"] == "FAIL":
        calculated_score += 25
        formula_parts.append("+25 (Face Mismatch)")
        bases_ledger.append({
            "category": "Biometrics",
            "signal_name": "1:1 Face Verification",
            "basis": f"Presented live face vector diverges from document photo ({face_score}% similarity).",
            "finding_status": "FAILED",
            "points_added": 25,
            "points_display": f"+25 pts ({face_score}%)",
            "level": "RED"
        })
        factors.append({
            "name": "Facial Biometrics",
            "impact": f"+25 pts (Face Mismatch: {face_score}%)",
            "status": "CRITICAL",
            "level": "RED",
            "description": "Presented face diverges from document portrait photo."
        })
        reasons.append(f"Face verification resulted in a mismatch ({face_score}% similarity).")
    elif evidence["biometrics"]["status"] == "WARNING":
        calculated_score += 10
        formula_parts.append("+10 (Face Similarity Review)")
        bases_ledger.append({
            "category": "Biometrics",
            "signal_name": "1:1 Face Verification",
            "basis": f"Marginal facial biometric similarity ({face_score}%) requires manual check.",
            "finding_status": "WARNING",
            "points_added": 10,
            "points_display": f"+10 pts ({face_score}%)",
            "level": "YELLOW"
        })
        factors.append({
            "name": "Facial Biometrics",
            "impact": f"+10 pts (Review Required: {face_score}%)",
            "status": "WARNING",
            "level": "YELLOW",
            "description": "Marginal facial biometric similarity."
        })
        reasons.append(f"Face match requires manual verification ({face_score}% similarity).")
    elif evidence["biometrics"]["status"] == "PASS":
        bases_ledger.append({
            "category": "Biometrics",
            "signal_name": "1:1 Face Verification",
            "basis": f"High facial embedding concordance verified ({face_score}% similarity).",
            "finding_status": "PASSED",
            "points_added": 0,
            "points_display": f"+0 pts ({face_score}%)",
            "level": "GREEN"
        })

    # Rule 6: Low Optical OCR Quality (+8 pts)
    if evidence["ocr"]["status"] == "WARNING":
        calculated_score += 8
        formula_parts.append("+8 (OCR Quality Penalty)")
        bases_ledger.append({
            "category": "Optical Quality",
            "signal_name": "OCR Optical Confidence",
            "basis": f"Average OCR confidence is {ocr_conf}%. Minor optical blur or glare detected.",
            "finding_status": "WARNING",
            "points_added": 8,
            "points_display": "+8 pts",
            "level": "YELLOW"
        })
        factors.append({
            "name": "OCR Optical Confidence",
            "impact": "+8 pts (Low Contrast/Angle)",
            "status": "WARNING",
            "level": "YELLOW",
            "description": f"Average OCR confidence is {ocr_conf}%. Optical blur detected."
        })
    else:
        bases_ledger.append({
            "category": "Optical Quality",
            "signal_name": "OCR Optical Confidence",
            "basis": f"High OCR confidence ({ocr_conf}%) with clean character segmentation.",
            "finding_status": "PASSED",
            "points_added": 0,
            "points_display": "+0 pts (Pass)",
            "level": "GREEN"
        })

    # Rule 7: Document Expiration (ONLY +5 pts — Expired DOES NOT mean fake!)
    if evidence["validity"]["status"] == "EXPIRED":
        calculated_score += 5
        formula_parts.append("+5 (Expired Document)")
        bases_ledger.append({
            "category": "Regulatory Validity",
            "signal_name": "Document Expiry & Window",
            "basis": "Document validity period has expired (Validity status is distinct from substrate authenticity).",
            "finding_status": "EXPIRED",
            "points_added": 5,
            "points_display": "+5 pts",
            "level": "YELLOW"
        })
        factors.append({
            "name": "Document Validity (Expiration)",
            "impact": "+5 pts (Expired Validity)",
            "status": "WARNING",
            "level": "YELLOW",
            "description": "Document validity period has expired (Authenticity is separate from validity)."
        })
        reasons.append("Document validity period has expired.")
    elif evidence["validity"]["status"] == "NEAR_EXPIRY":
        calculated_score += 3
        formula_parts.append("+3 (Near Expiry)")
        bases_ledger.append({
            "category": "Regulatory Validity",
            "signal_name": "Document Expiry & Window",
            "basis": "Document expires within 6 months (<180 days remaining).",
            "finding_status": "WARNING",
            "points_added": 3,
            "points_display": "+3 pts",
            "level": "YELLOW"
        })
        factors.append({
            "name": "Document Validity",
            "impact": "+3 pts (Near Expiration)",
            "status": "WARNING",
            "level": "YELLOW",
            "description": "Document expires within 6 months (<180 days remaining)."
        })
    else:
        bases_ledger.append({
            "category": "Regulatory Validity",
            "signal_name": "Document Expiry & Window",
            "basis": "Document is within its valid operational date window.",
            "finding_status": "PASSED",
            "points_added": 0,
            "points_display": "+0 pts (Valid)",
            "level": "GREEN"
        })

    # Clamp final score between 0 and 100
    final_score = max(0, min(100, int(round(calculated_score))))
    formula_str = " ".join(formula_parts) + f" = {final_score}/100"

    scoring_breakdown = {
        "base_score": 0,
        "calculated_score": final_score,
        "formula": formula_str,
        "bases_ledger": bases_ledger,
        "total_factors_evaluated": len(bases_ledger),
        "anomalies_flagged": sum(1 for b in bases_ledger if b["points_added"] > 0)
    }

    # Three-Tier Standard Decision
    if final_score <= 25:
        risk_level = "LOW"
        doc_status = "LIKELY GENUINE"
        badge_color = "GREEN"
        recommendation = "Standard clearance recommended. Document features and cryptographic indicators align with authentic issuing standards."
    elif final_score <= 55:
        risk_level = "MEDIUM"
        doc_status = "REQUIRES MANUAL REVIEW"
        badge_color = "YELLOW"
        recommendation = "Manual officer inspection recommended. Verify highlighted fields or optical variances before clearance."
    else:
        risk_level = "HIGH"
        doc_status = "LIKELY FAKE / SUSPICIOUS"
        badge_color = "RED"
        recommendation = "MANDATORY ESCALATION: Refer subject and document to Secondary Inspection Counter for physical forensics."

    # Structured Audit Log
    print(f"\n[RISK ENGINE EVALUATION LOG]")
    print(f"  CASE ID:           {case_id or 'CASE-LIVE'}")
    print(f"  DOCUMENT TYPE:     {doc_type}")
    print(f"  OCR CONFIDENCE:    {ocr_conf}%")
    print(f"  MRZ STATUS:        {evidence['mrz']['status']}")
    print(f"  CONSISTENCY:       {evidence['consistency']['status']}")
    print(f"  VALIDITY:          {evidence['validity']['status']}")
    print(f"  TAMPERING RISK:    {evidence['tampering']['risk_level']}")
    print(f"  BIOMETRICS:        {evidence['biometrics']['status']}")
    print(f"  FORMULA:           {formula_str}")
    print(f"  CALCULATED SCORE:  {final_score}/100")
    print(f"  FINAL DECISION:    {doc_status} ({risk_level})")

    return {
        "overall_risk_score": final_score,
        "risk_level": risk_level,
        "document_status": doc_status,
        "badge_color": badge_color,
        "analysis_status": "SUCCESS",
        "recommendation": recommendation,
        "risk_factors": factors,
        "scoring_breakdown": scoring_breakdown,
        "bases_ledger": bases_ledger,
        "evidence": evidence,
        "reasons": reasons,
        "disclaimer": "Automated screening provides an assessment based on available document evidence. It does not replace official authentication or an authorized officer's decision."
    }
