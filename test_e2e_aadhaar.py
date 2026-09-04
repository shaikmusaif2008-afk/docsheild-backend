import urllib.request
import json

# 1. Create Screening for Document Verification Domain with Aadhaar Card
req_data = json.dumps({'domain': '05 — DOCUMENT VERIFICATION', 'doc_type': 'Aadhaar Card'}).encode('utf-8')
create_req = urllib.request.Request('http://localhost:8000/api/screening/create', data=req_data, headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(create_req)
case_info = json.loads(res.read().decode('utf-8'))
case_id = case_info['case_id']
print('Case Created:', case_id)

# 2. Upload the Aadhaar card image (CASE-2026-FE90_fcfc.jpeg)
with open('data/uploads/CASE-2026-FE90_fcfc.jpeg', 'rb') as f:
    img_bytes = f.read()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = bytearray()
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="case_id"\r\n\r\n{case_id}\r\n'.encode('utf-8'))
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="doc_type"\r\n\r\nAadhaar Card\r\n'.encode('utf-8'))
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="domain"\r\n\r\n05 — DOCUMENT VERIFICATION\r\n'.encode('utf-8'))
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="aadhaar_rahul.jpeg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode('utf-8'))
body.extend(img_bytes)
body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

upload_req = urllib.request.Request('http://localhost:8000/api/screening/upload', data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
upload_res = urllib.request.urlopen(upload_req)
print('Upload Status:', upload_res.getcode())

# 3. Trigger OCR Extraction
ocr_body = bytearray()
ocr_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="case_id"\r\n\r\n{case_id}\r\n'.encode('utf-8'))
ocr_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="doc_type"\r\n\r\nAadhaar Card\r\n'.encode('utf-8'))
ocr_body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

ocr_req = urllib.request.Request('http://localhost:8000/api/ocr/extract', data=ocr_body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
ocr_res = urllib.request.urlopen(ocr_req)
data = json.loads(ocr_res.read().decode('utf-8'))
ocr_data = data['ocr_data']

print('\n' + '='*50)
print('  END-TO-END AADHAAR CARD OCR VERIFICATION')
print('='*50)
print('OCR Success:      ', data['success'])
print('Full Name:        ', ocr_data['full_name']['value'])
print('Aadhaar Number:   ', ocr_data['document_number']['value'])
print('Nationality:      ', ocr_data['nationality']['value'])
print('Date of Birth:    ', ocr_data['dob']['value'])
print('Gender:           ', ocr_data['gender']['value'])
print('Date of Issue:    ', ocr_data['issue_date']['value'])
print('Date of Expiry:   ', ocr_data['expiry_date']['value'])
print('Issuing Authority:', ocr_data['issuing_authority']['value'])
print('MRZ Validation:   ', ocr_data['mrz_validation'])
print('='*50)

assert ocr_data['full_name']['value'] == 'RAHUL SHARMA'
assert ocr_data['document_number']['value'] == '1234 5678 9013'
assert ocr_data['nationality']['value'] == 'IND'
assert ocr_data['gender']['value'] == 'Male'
assert ocr_data['expiry_date']['value'] == 'Permanent / Lifetime'
assert ocr_data['issuing_authority']['value'] == 'Unique Identification Authority of India (UIDAI)'
print('ALL AADHAAR FIELDS MATCH 100%!')
