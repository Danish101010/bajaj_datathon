"""
Debug script to analyze OCR quality on the datathon invoice.
Downloads the image, preprocesses it, and shows OCR results.
"""

import requests
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
import pytesseract
from pytesseract import Output

# Invoice URL
url = "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&st=2025-11-24T14%3A13%3A22Z&se=2026-11-25T14%3A13%3A00Z&sr=b&sp=r&sig=WFJYfNw0PJdZOpOYlsoAW0XujYGG1x2HSbcDREiFXSU%3D"

print("Downloading invoice...")
response = requests.get(url, timeout=30)
print(f"Downloaded {len(response.content)} bytes")

# Load image
img = Image.open(BytesIO(response.content))
print(f"Image size: {img.size}")
print(f"Image mode: {img.mode}")

# Convert to numpy array
img_array = np.array(img)
print(f"Array shape: {img_array.shape}")

# Convert to BGR for OpenCV
if len(img_array.shape) == 2:
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
elif img_array.shape[2] == 4:
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
else:
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

print(f"BGR shape: {img_bgr.shape}")

# Apply preprocessing
gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

# Try different preprocessing approaches
print("\n" + "="*60)
print("Testing different preprocessing methods...")
print("="*60)

# Method 1: Original image
print("\n1. Original Image OCR:")
text1 = pytesseract.image_to_string(img)
print(f"Extracted text (first 500 chars):")
print(text1[:500])
print(f"\nTotal length: {len(text1)}")

# Method 2: Grayscale with threshold
print("\n2. Grayscale + Binary Threshold:")
_, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
text2 = pytesseract.image_to_string(Image.fromarray(thresh))
print(f"Extracted text (first 500 chars):")
print(text2[:500])
print(f"\nTotal length: {len(text2)}")

# Method 3: Adaptive threshold
print("\n3. Adaptive Threshold:")
adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY, 11, 2)
text3 = pytesseract.image_to_string(Image.fromarray(adaptive))
print(f"Extracted text (first 500 chars):")
print(text3[:500])
print(f"\nTotal length: {len(text3)}")

# Method 4: Increase contrast
print("\n4. Increased Contrast:")
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
contrast = clahe.apply(gray)
text4 = pytesseract.image_to_string(Image.fromarray(contrast))
print(f"Extracted text (first 500 chars):")
print(text4[:500])
print(f"\nTotal length: {len(text4)}")

# Method 5: Denoise + threshold
print("\n5. Denoised + Threshold:")
denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
_, thresh_denoised = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
text5 = pytesseract.image_to_string(Image.fromarray(thresh_denoised))
print(f"Extracted text (first 500 chars):")
print(text5[:500])
print(f"\nTotal length: {len(text5)}")

# Save debug images
cv2.imwrite("C:/tmp/original.png", img_bgr)
cv2.imwrite("C:/tmp/grayscale.png", gray)
cv2.imwrite("C:/tmp/threshold.png", thresh)
cv2.imwrite("C:/tmp/adaptive.png", adaptive)
cv2.imwrite("C:/tmp/contrast.png", contrast)
cv2.imwrite("C:/tmp/denoised.png", thresh_denoised)

print("\n" + "="*60)
print("Debug images saved to C:/tmp/")
print("="*60)

# Detailed token analysis with best method
print("\n" + "="*60)
print("Detailed Token Analysis (Method 5 - Denoised):")
print("="*60)

ocr_data = pytesseract.image_to_data(Image.fromarray(thresh_denoised), 
                                      output_type=Output.DICT)

print(f"\nTotal tokens: {len(ocr_data['text'])}")
print("\nTokens with confidence > 60:")
print("-" * 60)

valid_tokens = []
for i in range(len(ocr_data['text'])):
    text = ocr_data['text'][i].strip()
    conf = int(ocr_data['conf'][i])
    
    if text and conf > 60:
        valid_tokens.append({
            'text': text,
            'conf': conf,
            'left': ocr_data['left'][i],
            'top': ocr_data['top'][i]
        })
        print(f"{text:30s} | Conf: {conf:3d} | Pos: ({ocr_data['left'][i]:4d}, {ocr_data['top'][i]:4d})")

print(f"\nFound {len(valid_tokens)} high-confidence tokens")

# Look for numeric values
print("\n" + "="*60)
print("Numeric values found:")
print("="*60)
import re
for token in valid_tokens:
    if re.search(r'\d', token['text']):
        print(f"{token['text']:20s} | Conf: {token['conf']:3d}")
