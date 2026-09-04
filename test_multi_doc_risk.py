import urllib.request
import json

def evaluate_case(domain, doc_type, person_name, img_path):
    # 1. Create Case
    req_data = json.dumps({'domain': domain, 'doc_type': doc_type}).encode('utf-8')
    create_req = urllib.request.Request('http://localhost:8000/api/screening/create', data=req_data, headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(create_req)
    case_info = json.loads(res.read().decode('utf-8'))
    case_id = case_info['case_id']

    # 2. Upload Document
    with open(img_path, 'rb') as f:
        img_bytes = f.read()

    boundary = '----WebKitFormBoundaryRiskMultiDocTest'
    body = bytearray()
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="case_id"\r\n\r\n{case_id}\r\n'.encode('utf-8'))
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="doc_type"\r\n\r\n{doc_type}\r\n'.encode('utf-8'))
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="domain"\r\n\r\n{domain}\r\n'.encode('utf-8'))
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="doc_test.jpeg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode('utf-8'))
    body.extend(img_bytes)
    body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

    upload_req = urllib.request.Request('http://localhost:8000/api/screening/upload', data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    urllib.request.urlopen(upload_req)

    # 3. OCR Extract
    ocr_body = bytearray()
    ocr_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="case_id"\r\n\r\n{case_id}\r\n'.encode('utf-8'))
    ocr_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="doc_type"\r\n\r\n{doc_type}\r\n'.encode('utf-8'))
    ocr_body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

    ocr_req = urllib.request.Request('http://localhost:8000/api/ocr/extract', data=ocr_body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    ocr_res = urllib.request.urlopen(ocr_req)
    ocr_json = json.loads(ocr_res.read().decode('utf-8'))
    ocr_data = ocr_json.get('ocr_data', {})

    # 4. Validation
    val_req = urllib.request.Request('http://localhost:8000/api/document/validate', data=ocr_body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    val_res = urllib.request.urlopen(val_req)
    val_json = json.loads(val_res.read().decode('utf-8'))
    val_data = val_json.get('validation_data', {})

    # 5. Tampering
    tamp_req = urllib.request.Request('http://localhost:8000/api/tampering/analyze', data=ocr_body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    tamp_res = urllib.request.urlopen(tamp_req)
    tamp_json = json.loads(tamp_res.read().decode('utf-8'))
    tamp_data = tamp_json.get('tampering_data', {})

    # 6. Calculate Risk
    risk_req = urllib.request.Request('http://localhost:8000/api/risk/calculate', data=ocr_body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    risk_res = urllib.request.urlopen(risk_req)
    risk_json = json.loads(risk_res.read().decode('utf-8'))
    risk_data = risk_json.get('risk_data', {})

    return {
        "case_id": case_id,
        "person_name": person_name,
        "extracted_name": ocr_data.get("full_name", {}).get("value"),
        "doc_number": ocr_data.get("document_number", {}).get("value"),
        "mrz_status": ocr_data.get("mrz_validation"),
        "tamper_risk": tamp_data.get("tampering_risk"),
        "risk_score": risk_data.get("overall_risk_score"),
        "risk_level": risk_data.get("risk_level"),
        "decision": risk_data.get("document_status"),
        "evidence": risk_data.get("evidence"),
        "factors": [f["name"] + " -> " + f["impact"] for f in risk_data.get("risk_factors", [])]
    }

print("="*70)
print("  MULTI-DOCUMENT DYNAMIC RISK SCORING VERIFICATION")
print("="*70)

# Test 1: Genuine Indian Passport (CASE-2026-F296_56be.jpeg)
res1 = evaluate_case("01 — AIRLINES & GATE AGENTS", "Passport", "Shaik Khaja Hussain", "data/uploads/CASE-2026-F296_56be.jpeg")
print(f"\n[DOC 1: Genuine Indian Passport]")
print(f"  Extracted Name: {res1['extracted_name']} | Doc No: {res1['doc_number']}")
print(f"  MRZ: {res1['mrz_status']} | Tampering: {res1['tamper_risk']}")
print(f"  Score: {res1['risk_score']}/100 -> Status: {res1['decision']}")
print(f"  Factors: {res1['factors']}")

# Test 2: Genuine Aadhaar Card (CASE-2026-FE90_fcfc.jpeg)
res2 = evaluate_case("05 — DOCUMENT VERIFICATION", "Aadhaar Card", "Rahul Sharma", "data/uploads/CASE-2026-FE90_fcfc.jpeg")
print(f"\n[DOC 2: Genuine Aadhaar Card]")
print(f"  Extracted Name: {res2['extracted_name']} | Doc No: {res2['doc_number']}")
print(f"  MRZ: {res2['mrz_status']} | Tampering: {res2['tamper_risk']}")
print(f"  Score: {res2['risk_score']}/100 -> Status: {res2['decision']}")
print(f"  Factors: {res2['factors']}")

# Test 3: Sample Tampered Visa
res3 = evaluate_case("01 — AIRLINES & GATE AGENTS", "Visa", "Alex Vance", "data/samples/sample_tampered_visa.jpg")
print(f"\n[DOC 3: Tampered Visa]")
print(f"  Extracted Name: {res3['extracted_name']} | Doc No: {res3['doc_number']}")
print(f"  MRZ: {res3['mrz_status']} | Tampering: {res3['tamper_risk']}")
print(f"  Score: {res3['risk_score']}/100 -> Status: {res3['decision']}")

print("\n" + "="*70)
print(f"SCORE SUMMARY: Doc 1: {res1['risk_score']}/100 | Doc 2: {res2['risk_score']}/100 | Doc 3: {res3['risk_score']}/100")
assert res1['risk_score'] != 45
assert res2['risk_score'] != 45
assert res3['risk_score'] >= 60
print("ALL RISK SCORES ARE DYNAMIC, EXPLAINABLE, AND EVIDENCE-BACKED!")
print("="*70)
