import urllib.request
import json
import uuid

# 1. Create Screening
req_data = json.dumps({'domain': '01 — AIRLINES & GATE AGENTS', 'doc_type': 'Passport'}).encode('utf-8')
create_req = urllib.request.Request('http://localhost:8000/api/screening/create', data=req_data, headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(create_req)
case_info = json.loads(res.read().decode('utf-8'))
case_id = case_info['case_id']
print('Case Created:', case_id)

# 2. Upload the Indian Passport image (CASE-2026-F296_56be.jpeg)
with open('data/uploads/CASE-2026-F296_56be.jpeg', 'rb') as f:
    img_bytes = f.read()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = bytearray()
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="case_id"\r\n\r\n{case_id}\r\n'.encode('utf-8'))
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="doc_type"\r\n\r\nPassport\r\n'.encode('utf-8'))
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="domain"\r\n\r\n01 — AIRLINES & GATE AGENTS\r\n'.encode('utf-8'))
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="passport_shaik.jpeg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode('utf-8'))
body.extend(img_bytes)
body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

upload_req = urllib.request.Request('http://localhost:8000/api/screening/upload', data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
upload_res = urllib.request.urlopen(upload_req)
print('Upload Status:', upload_res.getcode())

# 3. Trigger OCR Extraction
ocr_body = bytearray()
ocr_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="case_id"\r\n\r\n{case_id}\r\n'.encode('utf-8'))
ocr_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="doc_type"\r\n\r\nPassport\r\n'.encode('utf-8'))
ocr_body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

ocr_req = urllib.request.Request('http://localhost:8000/api/ocr/extract', data=ocr_body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
ocr_res = urllib.request.urlopen(ocr_req)
data = json.loads(ocr_res.read().decode('utf-8'))
ocr_data = data['ocr_data']

print('\n' + '='*50)
print('  END-TO-END SCREENING PIPELINE VERIFICATION')
print('='*50)
print('OCR Extraction Success:', data['success'])
print('Full Name:        ', ocr_data['full_name']['value'])
print('Doc Number:       ', ocr_data['document_number']['value'])
print('Nationality:      ', ocr_data['nationality']['value'])
print('Date of Birth:    ', ocr_data['dob']['value'])
print('Gender:           ', ocr_data['gender']['value'])
print('Date of Issue:    ', ocr_data['issue_date']['value'])
print('Date of Expiry:   ', ocr_data['expiry_date']['value'])
print('Issuing Authority:', ocr_data['issuing_authority']['value'])
print('MRZ Validation:   ', ocr_data['mrz_validation'])
print('='*50)

assert ocr_data['full_name']['value'] == 'KHAJA HUSSAIN SHAIK'
assert ocr_data['document_number']['value'] == 'H2914919'
assert ocr_data['dob']['value'] == '1979-09-19'
assert ocr_data['issue_date']['value'] == '2009-02-18'
assert ocr_data['expiry_date']['value'] == '2019-02-17'
assert ocr_data['gender']['value'] == 'Male'
print('ALL PASSPORT FIELDS MATCH 100%!')
