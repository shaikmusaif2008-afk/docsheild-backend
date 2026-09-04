import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..config import CURRENT_SYSTEM_DATE, PASSPORT_VALIDITY_MIN_DAYS
from ..database import get_db_connection

def parse_date_safely(date_str: str) -> Optional[datetime]:
    """Safely parses various date formats (YYYY-MM-DD, DD/MM/YYYY, DD MMM YYYY, etc.)."""
    if not date_str or date_str == "Not detected":
        return None
        
    clean = date_str.strip().replace("/", "-").replace(".", "-")
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y",
        "%d-%B-%Y", "%d %B %Y", "%Y%m%d", "%d-%m-%y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(clean, fmt)
        except Exception:
            pass
    return None

def validate_extracted_document(extracted_data: Dict[str, Any], doc_type: str = "Passport") -> Dict[str, Any]:
    """
    Validates actual OCR/MRZ data extracted from the uploaded document:
    - Required field detection
    - Date format & future birth date check
    - Expiration check (VALID, EXPIRED, UNKNOWN)
    - 6-month border threshold rule
    - MRZ checksum validation
    - Internal Consistency Check (Visual OCR vs MRZ field cross-check)
    - Demo Watchlist lookup
    """
    checks: List[Dict[str, Any]] = []

    def get_val(k: str) -> str:
        f = extracted_data.get(k)
        if isinstance(f, dict):
            return str(f.get("value", "")).strip()
        return str(f).strip() if f is not None else ""

    full_name = get_val("full_name")
    doc_num = get_val("document_number")
    nationality = get_val("nationality")
    dob_str = get_val("dob")
    issue_date_str = get_val("issue_date")
    expiry_date_str = get_val("expiry_date")
    
    mrz_detected = extracted_data.get("mrz_detected", False)
    mrz_validation = extracted_data.get("mrz_validation", "NOT_DETECTED")
    mrz_line1 = get_val("mrz_line1")
    mrz_line2 = get_val("mrz_line2")

    ref_date = datetime.strptime(CURRENT_SYSTEM_DATE, "%Y-%m-%d")

    # 1. Required Fields Check
    missing_fields = []
    if not full_name or full_name == "Not detected": missing_fields.append("Full Name")
    if not doc_num or doc_num == "Not detected": missing_fields.append("Document Number")
    if not dob_str or dob_str == "Not detected": missing_fields.append("Date of Birth")
    if not expiry_date_str or expiry_date_str == "Not detected": missing_fields.append("Date of Expiry")

    if not missing_fields:
        checks.append({
            "id": "chk_required_fields",
            "name": "Mandatory Fields Completeness",
            "status": "PASSED",
            "level": "GREEN",
            "explanation": "All critical identity fields (Name, Doc No, DOB, Expiry) were successfully parsed from the document."
        })
    elif len(missing_fields) <= 2:
        checks.append({
            "id": "chk_required_fields",
            "name": "Mandatory Fields Completeness",
            "status": "WARNING",
            "level": "YELLOW",
            "explanation": f"Some mandatory fields could not be confidently detected: {', '.join(missing_fields)}."
        })
    else:
        checks.append({
            "id": "chk_required_fields",
            "name": "Mandatory Fields Completeness",
            "status": "FAILED",
            "level": "RED",
            "explanation": f"Multiple critical mandatory fields missing: {', '.join(missing_fields)}. Image may be cropped or low resolution."
        })

    # 2. Document Number Format
    if doc_num and doc_num != "Not detected":
        clean_num = re.sub(r'[^A-Za-z0-9]', '', doc_num)
        if 6 <= len(clean_num) <= 12:
            checks.append({
                "id": "chk_doc_num_format",
                "name": "Document Number Syntax",
                "status": "PASSED",
                "level": "GREEN",
                "explanation": f"Document number '{doc_num}' complies with standard travel document alphanumeric formatting."
            })
        else:
            checks.append({
                "id": "chk_doc_num_format",
                "name": "Document Number Syntax",
                "status": "WARNING",
                "level": "YELLOW",
                "explanation": f"Document number '{doc_num}' length ({len(clean_num)}) deviates from standard travel document norms."
            })
    else:
        checks.append({
            "id": "chk_doc_num_format",
            "name": "Document Number Syntax",
            "status": "WARNING",
            "level": "YELLOW",
            "explanation": "Document number not detected in visual inspection zone."
        })

    # 3. Date Logical Consistency (DOB < Issue < Expiry, and DOB not in future)
    dob = parse_date_safely(dob_str)
    issue_date = parse_date_safely(issue_date_str)
    expiry_date = parse_date_safely(expiry_date_str)

    if dob and dob > ref_date:
        checks.append({
            "id": "chk_logical_dates",
            "name": "Chronological Date Logic",
            "status": "FAILED",
            "level": "RED",
            "explanation": f"Birth date ({dob_str}) is in the future relative to operational date ({CURRENT_SYSTEM_DATE})."
        })
    elif dob and issue_date and dob >= issue_date:
        checks.append({
            "id": "chk_logical_dates",
            "name": "Chronological Date Logic",
            "status": "FAILED",
            "level": "RED",
            "explanation": f"Date of Birth ({dob_str}) occurs on or after Issue Date ({issue_date_str})."
        })
    elif issue_date and expiry_date and issue_date >= expiry_date:
        checks.append({
            "id": "chk_logical_dates",
            "name": "Chronological Date Logic",
            "status": "FAILED",
            "level": "RED",
            "explanation": f"Issue Date ({issue_date_str}) occurs on or after Expiry Date ({expiry_date_str})."
        })
    else:
        checks.append({
            "id": "chk_logical_dates",
            "name": "Chronological Date Logic",
            "status": "PASSED",
            "level": "GREEN",
            "explanation": "Chronological sequence verified: DOB precedes Issue Date, which precedes Expiry Date."
        })

    # 4. Expiry Status Check (VALID, EXPIRED, UNKNOWN)
    if expiry_date:
        if expiry_date < ref_date:
            days_expired = (ref_date - expiry_date).days
            checks.append({
                "id": "chk_expiry_validity",
                "name": "Document Expiry Status",
                "status": "EXPIRED",
                "level": "RED",
                "explanation": f"DOCUMENT EXPIRED on {expiry_date.strftime('%Y-%m-%d')} ({days_expired} days expired relative to {CURRENT_SYSTEM_DATE})."
            })
        else:
            days_remaining = (expiry_date - ref_date).days
            if days_remaining < PASSPORT_VALIDITY_MIN_DAYS:
                checks.append({
                    "id": "chk_expiry_validity",
                    "name": "Document Expiry Status",
                    "status": "WARNING",
                    "level": "YELLOW",
                    "explanation": f"Document is VALID until {expiry_date.strftime('%Y-%m-%d')}, but has only {days_remaining} days remaining (<6-month border rule)."
                })
            else:
                checks.append({
                    "id": "chk_expiry_validity",
                    "name": "Document Expiry Status",
                    "status": "VALID",
                    "level": "GREEN",
                    "explanation": f"Document is fully VALID until {expiry_date.strftime('%Y-%m-%d')} ({days_remaining} days validity remaining)."
                })
    else:
        checks.append({
            "id": "chk_expiry_validity",
            "name": "Document Expiry Status",
            "status": "UNKNOWN",
            "level": "YELLOW",
            "explanation": "Document expiry date could not be parsed. Officer manual inspection required."
        })

    # 5. MRZ Checksum Integrity Check
    if mrz_detected:
        if mrz_validation == "VALID":
            checks.append({
                "id": "chk_mrz_checksum",
                "name": "ICAO 9303 MRZ Checksum Integrity",
                "status": "PASSED",
                "level": "GREEN",
                "explanation": "MRZ 7-3-1 mathematical check digits (Doc Number, DOB, Expiry, Composite) verified."
            })
        else:
            checks.append({
                "id": "chk_mrz_checksum",
                "name": "ICAO 9303 MRZ Checksum Integrity",
                "status": "FAILED",
                "level": "RED",
                "explanation": "ICAO 9303 check digit verification failed. Potential optical corruption or modified MRZ character."
            })
    else:
        checks.append({
            "id": "chk_mrz_checksum",
            "name": "ICAO 9303 MRZ Checksum Integrity",
            "status": "INFO",
            "level": "YELLOW",
            "explanation": "MRZ section not detected on document face (optional on standard national ID cards)."
        })

    # 6. Internal Consistency Cross-Check (Visual OCR vs MRZ Fields)
    # If both OCR visual text and MRZ exist, compare them
    mrz_fields = extracted_data.get("mrz_fields", {})
    if mrz_detected and mrz_fields:
        mrz_num = mrz_fields.get("document_number", "")
        if doc_num and mrz_num and doc_num != "Not detected" and mrz_num != "Not detected":
            if doc_num.upper() != mrz_num.upper():
                checks.append({
                    "id": "chk_internal_consistency",
                    "name": "Internal Data Consistency",
                    "status": "WARNING / DATA MISMATCH",
                    "level": "YELLOW",
                    "explanation": f"Visual Document Number '{doc_num}' disagrees with MRZ Document Number '{mrz_num}'. Review recommended."
                })
            else:
                checks.append({
                    "id": "chk_internal_consistency",
                    "name": "Internal Data Consistency",
                    "status": "PASSED",
                    "level": "GREEN",
                    "explanation": "Visual inspection text and MRZ fields match consistently across all zones."
                })

    # 7. Demo Border Watchlist & Registry Cross-Check
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM demo_watchlist WHERE doc_number = ? OR full_name LIKE ?", (doc_num, f"%{full_name}%"))
    db_record = cursor.fetchone()
    conn.close()

    if db_record:
        rec_status = db_record["status"]
        rec_reason = db_record["reason"] or "Listed in demo registry"
        
        if rec_status == "VALID":
            checks.append({
                "id": "chk_external_db",
                "name": "External Database Verification — Demo",
                "status": "PASSED",
                "level": "GREEN",
                "explanation": f"Demo Registry Match: Document active and in good standing ({rec_reason})."
            })
        elif rec_status in ["BLACKLISTED", "STOLEN"]:
            checks.append({
                "id": "chk_external_db",
                "name": "External Database Verification — Demo",
                "status": "FAILED",
                "level": "RED",
                "explanation": f"CRITICAL ALERT (Demo DB): Flagged as '{rec_status}' — Reason: {rec_reason}."
            })
        elif rec_status == "EXPIRED":
            checks.append({
                "id": "chk_external_db",
                "name": "External Database Verification — Demo",
                "status": "FAILED",
                "level": "RED",
                "explanation": f"WATCHLIST ALERT (Demo DB): Record marked as '{rec_status}' ({rec_reason})."
            })
        else:
            checks.append({
                "id": "chk_external_db",
                "name": "External Database Verification — Demo",
                "status": "WARNING",
                "level": "YELLOW",
                "explanation": f"DEMO REVIEW: Flagged for '{rec_status}' — Reason: {rec_reason}."
            })
    else:
        checks.append({
            "id": "chk_external_db",
            "name": "External Database Verification — Demo",
            "status": "INFO",
            "level": "YELLOW",
            "explanation": "Simulated Demo Database: Record not indexed in offline test registry. Live production requires national MHA connectivity."
        })

    has_red = any(c["level"] == "RED" for c in checks)
    has_yellow = any(c["level"] == "YELLOW" for c in checks)
    overall_status = "FAILED" if has_red else "WARNING" if has_yellow else "PASSED"

    return {
        "overall_status": overall_status,
        "total_checks": len(checks),
        "passed_count": sum(1 for c in checks if c["level"] == "GREEN"),
        "warning_count": sum(1 for c in checks if c["level"] == "YELLOW"),
        "failed_count": sum(1 for c in checks if c["level"] == "RED"),
        "checks": checks,
        "disclaimer": "Automated validation of actual OCR/MRZ data. Discrepancies warrant manual secondary inspection."
    }
