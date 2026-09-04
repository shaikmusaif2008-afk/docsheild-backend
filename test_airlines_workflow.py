import urllib.request
import json
import time

print("="*60)
print("  DOCSHIELD AI — AIRLINES & GATE AGENTS WORKFLOW TEST")
print("="*60)

# 1. Test Session Creation
req_data = json.dumps({'domain': '01 — AIRLINES & GATE AGENTS', 'doc_type': 'Passport'}).encode('utf-8')
create_req = urllib.request.Request('http://localhost:8000/api/screening/create', data=req_data, headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(create_req)
case_info = json.loads(res.read().decode('utf-8'))
case_id = case_info['case_id']
print(f"[STEP 01] Case Created: {case_id}")

# 2. Upload Document into Slot
with open('data/uploads/CASE-2026-F296_56be.jpeg', 'rb') as f:
    img_bytes = f.read()

boundary = '----WebKitFormBoundaryAirlinesTest789'
body = bytearray()
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="case_id"\r\n\r\n{case_id}\r\n'.encode('utf-8'))
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="doc_type"\r\n\r\nPassport\r\n'.encode('utf-8'))
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="domain"\r\n\r\n01 — AIRLINES & GATE AGENTS\r\n'.encode('utf-8'))
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="shaik_khaja_passport.jpeg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode('utf-8'))
body.extend(img_bytes)
body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

upload_req = urllib.request.Request('http://localhost:8000/api/screening/upload', data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
upload_res = urllib.request.urlopen(upload_req)
print(f"[STEP 03] Upload Document: HTTP {upload_res.getcode()}")

# 3. Dynamic OCR Extraction on Uploaded Document
ocr_body = bytearray()
ocr_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="case_id"\r\n\r\n{case_id}\r\n'.encode('utf-8'))
ocr_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="doc_type"\r\n\r\nPassport\r\n'.encode('utf-8'))
ocr_body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

ocr_req = urllib.request.Request('http://localhost:8000/api/ocr/extract', data=ocr_body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
ocr_res = urllib.request.urlopen(ocr_req)
ocr_json = json.loads(ocr_res.read().decode('utf-8'))
ocr_data = ocr_json['ocr_data']

print(f"[STEP 03 -> 04] Extracted Name:    {ocr_data['full_name']['value']}")
print(f"[STEP 03 -> 04] Document Number:   {ocr_data['document_number']['value']}")
print(f"[STEP 03 -> 04] MRZ Status:        {ocr_data['mrz_validation']}")
print(f"[STEP 03 -> 04] OCR Confidence:    {ocr_data['overall_ocr_confidence']}%")

assert ocr_data['full_name']['value'] == 'KHAJA HUSSAIN SHAIK'
assert ocr_data['document_number']['value'] == 'H2914919'
assert ocr_data['mrz_validation'] == 'VALID'

print("\n" + "="*60)
print("  AIRLINES & GATE AGENTS SEQUENTIAL WORKFLOW VERIFIED 100%!")
print("="*60)
