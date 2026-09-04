import os
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from .config import SAMPLES_DIR

def draw_guilloche(draw: ImageDraw.Draw, width: int, height: int, color=(210, 230, 245, 120)):
    """Draws security guilloche wavy lines common in passports and visas."""
    for y_offset in range(40, height, 25):
        points = []
        for x in range(0, width, 4):
            y = y_offset + math.sin(x * 0.05) * 8 + math.cos(x * 0.02) * 5
            points.append((x, y))
        draw.line(points, fill=color, width=1)

def generate_portrait_image(filename: str, face_type: str = "male_1", text_label: str = "TRAVELER"):
    """Generates a clean synthetic biometric portrait image."""
    filepath = SAMPLES_DIR / filename
    img = Image.new("RGB", (240, 300), color="#e2e8f0")
    draw = ImageDraw.Draw(img)
    
    # Gradient background
    for y in range(300):
        c = int(220 - y * 0.15)
        draw.line([(0, y), (240, y)], fill=(c, c + 5, c + 15))
        
    # Draw avatar silhouette / features
    # Head & Neck
    if "female" in face_type:
        # Hair
        draw.ellipse([50, 40, 190, 220], fill="#3e2723")
        # Face oval
        draw.ellipse([65, 60, 175, 190], fill="#f5d0b5")
        # Shoulders
        draw.polygon([(20, 300), (60, 210), (180, 210), (220, 300)], fill="#7c3aed")
        # Eyes
        draw.ellipse([88, 110, 106, 122], fill="#ffffff")
        draw.ellipse([93, 113, 101, 121], fill="#2d3748")
        draw.ellipse([134, 110, 152, 122], fill="#ffffff")
        draw.ellipse([139, 113, 147, 121], fill="#2d3748")
        # Smile
        draw.arc([105, 140, 135, 165], start=20, end=160, fill="#be185d", width=3)
    elif "mismatch" in face_type:
        # Different person silhouette
        draw.ellipse([55, 30, 185, 190], fill="#1e293b")
        draw.ellipse([70, 50, 170, 180], fill="#e0ac69")
        # Glasses
        draw.rectangle([80, 95, 110, 115], outline="#0f172a", width=3)
        draw.rectangle([130, 95, 160, 115], outline="#0f172a", width=3)
        draw.line([(110, 105), (130, 105)], fill="#0f172a", width=3)
        # Beard
        draw.polygon([(85, 150), (120, 185), (155, 150)], fill="#1e293b")
        # Shirt
        draw.polygon([(10, 300), (50, 200), (190, 200), (230, 300)], fill="#b91c1c")
    else:
        # Standard male
        # Hair
        draw.ellipse([60, 45, 180, 140], fill="#1e1e24")
        # Face oval
        draw.ellipse([65, 60, 175, 190], fill="#fcd34d")
        # Shoulders
        draw.polygon([(15, 300), (55, 200), (185, 200), (225, 300)], fill="#1e3a8a")
        # Eyes
        draw.ellipse([88, 110, 106, 122], fill="#ffffff")
        draw.ellipse([93, 113, 101, 121], fill="#1e293b")
        draw.ellipse([134, 110, 152, 122], fill="#ffffff")
        draw.ellipse([139, 113, 147, 121], fill="#1e293b")
        # Mouth
        draw.line([(105, 155), (135, 155)], fill="#991b1b", width=2)
        
    # Security hologram watermark across bottom
    draw.text((30, 270), f"SECURE-BIO :: {text_label}", fill=(255, 255, 255, 180))
    img.save(filepath, "JPEG", quality=95)
    return str(filepath)

def generate_sample_documents():
    """Generates the 3 main demo documents (Genuine Passport, Tampered Visa, Expired ID)."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate portraits first
    p_genuine = generate_portrait_image("doc_face_genuine.jpg", "male_1", "JOHNATHAN DOE")
    p_live_genuine = generate_portrait_image("live_face_genuine.jpg", "male_1", "LIVE MATCH")
    
    p_tampered_doc = generate_portrait_image("doc_face_tampered.jpg", "male_1", "ALEX VANCE")
    p_live_tampered = generate_portrait_image("live_face_tampered.jpg", "mismatch", "IMPOSTOR")
    
    p_expired_doc = generate_portrait_image("doc_face_expired.jpg", "female_1", "MARIA GOMEZ")
    p_live_expired = generate_portrait_image("live_face_expired.jpg", "female_1", "LIVE MATCH")

    # 2. Document 1: Genuine Passport
    doc1_path = SAMPLES_DIR / "sample_genuine_passport.jpg"
    img1 = Image.new("RGB", (900, 580), color="#f8fafc")
    d1 = ImageDraw.Draw(img1)
    
    # Outer Border & Header
    d1.rectangle([10, 10, 890, 570], outline="#0284c7", width=3)
    d1.rectangle([15, 15, 885, 75], fill="#0f172a")
    d1.text((35, 30), "REPUBLIC OF INDIA / RÉPUBLIQUE DE L'INDE", fill="#f8fafc")
    d1.text((700, 30), "PASSPORT / PASSEPORT", fill="#38bdf8")
    
    # Guilloche patterns
    draw_guilloche(d1, 900, 580, (203, 213, 225))
    
    # Paste Photo
    photo1 = Image.open(p_genuine).resize((180, 220))
    img1.paste(photo1, (40, 110))
    d1.rectangle([38, 108, 222, 332], outline="#0284c7", width=2)
    
    # Text Details
    fields_1 = [
        ("Type / Type", "P", 260, 100),
        ("Country Code", "IND", 380, 100),
        ("Passport No.", "K28491047", 560, 100),
        ("Given Name(s)", "JOHNATHAN EDWARD", 260, 150),
        ("Surname", "DOE", 560, 150),
        ("Nationality", "INDIAN", 260, 200),
        ("Date of Birth", "14 JUN 1988", 560, 200),
        ("Sex", "M", 260, 250),
        ("Place of Birth", "NEW DELHI", 380, 250),
        ("Date of Issue", "10 APR 2021", 260, 300),
        ("Date of Expiry", "09 APR 2031", 560, 300),
        ("Authority", "PASSPORT SEVA KENDRA DELHI", 260, 350)
    ]
    
    for label, val, x, y in fields_1:
        d1.text((x, y), label.upper(), fill="#64748b")
        d1.text((x, y + 16), val, fill="#0f172a")
        
    # Official Emblem / Watermark
    d1.ellipse([700, 230, 830, 360], outline="#cbd5e1", width=3)
    d1.text((725, 290), "EMBLEM", fill="#94a3b8")
    
    # MRZ Box
    d1.rectangle([20, 460, 880, 560], fill="#f1f5f9", outline="#94a3b8", width=1)
    d1.text((40, 480), "P<INDDOE<<JOHNATHAN<EDWARD<<<<<<<<<<<<<<<<<<<", fill="#0f172a")
    d1.text((40, 515), "K284910478IND8806144M3104092<<<<<<<<<<<<<<<4", fill="#0f172a")
    
    img1.save(doc1_path, "JPEG", quality=95)

    # 3. Document 2: Tampered Visa (Altered Expiry & Spliced Photo)
    doc2_path = SAMPLES_DIR / "sample_tampered_visa.jpg"
    img2 = Image.new("RGB", (900, 580), color="#fffbeb")
    d2 = ImageDraw.Draw(img2)
    
    # Border & Header
    d2.rectangle([10, 10, 890, 570], outline="#b45309", width=3)
    d2.rectangle([15, 15, 885, 75], fill="#78350f")
    d2.text((35, 30), "ENTRY VISA / VISA D'ENTRÉE", fill="#fef3c7")
    d2.text((700, 30), "MULTI-ENTRY B1", fill="#fbbf24")
    
    # Guilloche
    draw_guilloche(d2, 900, 580, (254, 215, 170))
    
    # Photo with a visible artificial border overlay (tamper signature)
    photo2 = Image.open(p_tampered_doc).resize((180, 220))
    img2.paste(photo2, (40, 110))
    d2.rectangle([36, 106, 224, 334], outline="#ef4444", width=3) # Spliced edge
    
    # Text Fields
    fields_2 = [
        ("Visa No.", "V84729104", 260, 100),
        ("Type", "BUSINESS / MULTI", 560, 100),
        ("Full Name", "ALEX K. VANCE", 260, 150),
        ("Nationality", "BRITISH (GBR)", 560, 150),
        ("Date of Birth", "23 NOV 1982", 260, 200),
        ("Sex", "M", 560, 200),
        ("Date of Issue", "15 JAN 2022", 260, 250),
        ("Date of Expiry", "31 DEC 2029 [ALTERED]", 560, 250), # Altered font color/artifact
        ("Stay Duration", "90 DAYS PER ENTRY", 260, 300),
        ("Issuing Post", "CONSULATE GENERAL MUMBAI", 560, 300)
    ]
    
    for label, val, x, y in fields_2:
        d2.text((x, y), label.upper(), fill="#78350f")
        if "ALTERED" in val:
            # Draw altered text with distinct artifact box
            d2.rectangle([x - 4, y + 12, x + 230, y + 36], fill="#fee2e2", outline="#ef4444")
            d2.text((x, y + 16), val, fill="#b91c1c")
        else:
            d2.text((x, y + 16), val, fill="#1c1917")
            
    # Red Stamp
    d2.ellipse([680, 320, 830, 450], outline="#dc2626", width=3)
    d2.text((710, 375), "IMMIGRATION\nVERIFIED", fill="#dc2626")
    
    # MRZ
    d2.rectangle([20, 460, 880, 560], fill="#fef3c7", outline="#d97706", width=1)
    d2.text((40, 480), "V<GBRVANCE<<ALEX<K<<<<<<<<<<<<<<<<<<<<<<<<<<", fill="#1c1917")
    d2.text((40, 515), "V847291042GBR8211237M2912314<<<<<<<<<<<<<<<2", fill="#1c1917")
    
    img2.save(doc2_path, "JPEG", quality=95)

    # 4. Document 3: Expired National ID
    doc3_path = SAMPLES_DIR / "sample_expired_id.jpg"
    img3 = Image.new("RGB", (900, 580), color="#f1f5f9")
    d3 = ImageDraw.Draw(img3)
    
    # Header
    d3.rectangle([10, 10, 890, 570], outline="#475569", width=3)
    d3.rectangle([15, 15, 885, 75], fill="#334155")
    d3.text((35, 30), "NATIONAL IDENTITY CARD / DOCUMENTO NACIONAL", fill="#f8fafc")
    d3.text((680, 30), "KINGDOM OF SPAIN", fill="#94a3b8")
    
    draw_guilloche(d3, 900, 580, (226, 232, 240))
    
    photo3 = Image.open(p_expired_doc).resize((180, 220))
    img3.paste(photo3, (40, 110))
    d3.rectangle([38, 108, 222, 332], outline="#475569", width=2)
    
    fields_3 = [
        ("Document ID", "ID-90418247", 260, 100),
        ("Nationality", "ESP", 560, 100),
        ("Surname", "GOMEZ", 260, 150),
        ("First Name", "MARIA ELENA", 560, 150),
        ("Date of Birth", "29 MAR 1991", 260, 200),
        ("Sex", "F", 560, 200),
        ("Date of Issue", "18 MAY 2013", 260, 250),
        ("Date of Expiry", "17 MAY 2023 (EXPIRED)", 560, 250),
        ("Authority", "MINISTERIO DEL INTERIOR", 260, 300)
    ]
    
    for label, val, x, y in fields_3:
        d3.text((x, y), label.upper(), fill="#64748b")
        if "EXPIRED" in val:
            d3.text((x, y + 16), val, fill="#ef4444")
        else:
            d3.text((x, y + 16), val, fill="#0f172a")
            
    # MRZ
    d3.rectangle([20, 460, 880, 560], fill="#e2e8f0", outline="#64748b", width=1)
    d3.text((40, 480), "I<ESPGOMEZ<<MARIA<ELENA<<<<<<<<<<<<<<<<<<<<<", fill="#0f172a")
    d3.text((40, 515), "ID904182478ESP9103294F2305174<<<<<<<<<<<<<<<8", fill="#0f172a")
    
    img3.save(doc3_path, "JPEG", quality=95)

if __name__ == "__main__":
    generate_sample_documents()
    print("Sample document assets successfully generated.")
