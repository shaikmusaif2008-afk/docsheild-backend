import re
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
result, elapse = ocr("data/uploads/CASE-2026-FE90_fcfc.jpeg")

raw_lines = [text.strip() for box, text, score in result]
full_text = "\n".join(raw_lines)
print("Extracted lines:")
for l in raw_lines:
    print(" ", repr(l))

# 1. Detect Document Kind
is_aadhaar = bool(re.search(r'(aadhaar|uidai|government\s*of\s*in|goveranent|mera\s*aadhaar|peo/|3fa/dob)', full_text, re.I))
print("\nIs Aadhaar:", is_aadhaar)

# 2. Extract Aadhaar Number (12 digits)
aadhaar_num = None
m_aadh = re.search(r'\b(\d{4}\s*\d{4}\s*\d{4})\b', full_text)
if m_aadh:
    raw_digits = re.sub(r'\D', '', m_aadh.group(1))
    aadhaar_num = f"{raw_digits[0:4]} {raw_digits[4:8]} {raw_digits[8:12]}"
elif re.search(r'\b(\d{12})\b', full_text):
    m = re.search(r'\b(\d{12})\b', full_text)
    raw_digits = m.group(1)
    aadhaar_num = f"{raw_digits[0:4]} {raw_digits[4:8]} {raw_digits[8:12]}"

print("Aadhaar Number:", aadhaar_num)

# 3. Extract Name
# On Aadhaar: usually comes after "Government of India" / "Name" / "नाम"
name = None
for i, l in enumerate(raw_lines):
    if re.search(r'(name|narme|naam|नाम)', l, re.I):
        if i + 1 < len(raw_lines):
            cand = raw_lines[i+1].strip()
            # If cand is not DOB or Gender or Government
            if not re.search(r'(dob|male|female|government|aadhaar|\d)', cand, re.I):
                name = cand
    elif l.isupper() and len(l) >= 4 and not re.search(r'(government|india|aadhaar|male|female|dob)', l, re.I):
        if not name:
            name = l

# Format name if it's concatenated e.g. RAHULSHARMA -> RAHUL SHARMA
if name:
    # If CamelCase or all caps without spaces
    if " " not in name and len(name) > 5:
        # Check common name split e.g. RAHULSHARMA -> RAHUL SHARMA
        m_split = re.match(r'^([A-Z]{3,10})([A-Z]{3,10})$', name)
        if m_split:
            name = f"{m_split.group(1)} {m_split.group(2)}"

print("Extracted Name:", name)

# 4. Extract Gender
gender = "Not detected"
if re.search(r'(male|पुरुष|purush|\bm\b)', full_text, re.I) and not re.search(r'(female|महिला)', full_text, re.I):
    gender = "Male"
elif re.search(r'(female|महिला|mahila|\bf\b)', full_text, re.I):
    gender = "Female"

print("Extracted Gender:", gender)

# 5. Extract DOB
dob = "Not detected"
m_dob = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', full_text)
if m_dob:
    dob = m_dob.group(1)
elif re.search(r'(\b(19|20)\d{2}\b)', full_text):
    # Year of birth
    m_yob = re.search(r'(\b(19|20)\d{2}\b)', full_text)
    dob = f"{m_yob.group(1)}-01-01"

print("Extracted DOB:", dob)

# 6. Expiry & Authority
expiry = "Permanent / Lifetime" if is_aadhaar else "Not detected"
authority = "Unique Identification Authority of India (UIDAI)" if is_aadhaar else "Competent State Authority"
nationality = "IND" if is_aadhaar else "Not detected"

print("Nationality:", nationality)
print("Expiry:", expiry)
print("Authority:", authority)
