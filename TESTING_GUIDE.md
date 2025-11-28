# Complete Testing Guide

## 📋 Table of Contents
1. [Pre-Installation Check](#pre-installation-check)
2. [Installation Steps](#installation-steps)
3. [Module Testing](#module-testing)
4. [API Testing](#api-testing)
5. [Integration Testing](#integration-testing)
6. [Debug Mode Testing](#debug-mode-testing)
7. [Performance Testing](#performance-testing)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Installation Check

### System Requirements
- Python 3.10 or higher
- 4GB RAM minimum (8GB recommended)
- 1GB free disk space
- Internet connection (for PDF downloads)

### Check Python Version
```powershell
# Windows PowerShell
python --version

# Linux/macOS
python3 --version
```

Expected: `Python 3.10.x` or higher

---

## Installation Steps

### 1. Install System Dependencies

**Windows:**
```powershell
# Install Tesseract OCR
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH: C:\Program Files\Tesseract-OCR

# Install Poppler
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
# Extract and add to PATH: C:\poppler\Library\bin

# Verify installation
tesseract --version
pdftoppm -v
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr

# Verify installation
tesseract --version
pdftoppm -v
```

**macOS:**
```bash
brew install poppler tesseract

# Verify installation
tesseract --version
pdftoppm -v
```

### 2. Set Up Virtual Environment

```powershell
# Navigate to project directory
cd c:\Users\mohdd\Downloads\datathon

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Linux/macOS)
source venv/bin/activate

# Your prompt should now show (venv)
```

### 3. Install Python Packages

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# This installs:
# - fastapi, uvicorn (API)
# - pdf2image, pillow (PDF/image handling)
# - numpy, opencv-python-headless (image processing)
# - pytesseract (OCR)
# - pulp (optimization)
# - rapidfuzz (fuzzy matching)
# - requests (HTTP client)
# - python-multipart, pytest (utilities)
```

### 4. Verify Installation

```bash
python test_installation.py
```

**Expected Output:**
```
======================================================================
INVOICE EXTRACTION PIPELINE - Installation Validation
======================================================================

Checking Python package installations...

✓ NumPy               [OK]
✓ OpenCV              [OK]
✓ Pillow              [OK]
✓ pdf2image           [OK]
✓ pytesseract         [OK]
✓ PuLP                [OK]
✓ RapidFuzz           [OK]
✓ FastAPI             [OK]
✓ Pydantic            [OK]
✓ Uvicorn             [OK]
✓ Requests            [OK]

----------------------------------------------------------------------
Results: 11/11 packages installed
----------------------------------------------------------------------

======================================================================
Checking system dependencies...

✓ Tesseract OCR       [OK] - Version 5.x.x
✓ Poppler (pdf2image)  [OK]

======================================================================
✓ All checks passed! System is ready.
```

---

## Module Testing

Test each module individually to ensure proper functionality.

### Test 1: Preprocessing Module

```bash
# Create a test with a sample PDF
python preprocess.py path/to/sample.pdf
```

**Expected Output:**
```
Processing: path/to/sample.pdf
Converting PDF to images...
Converted 3 page(s)

Processing page 1...
  Original size: (2550, 3300)
  Processed shape: (3300, 2550, 3)

Processing page 2...
  Original size: (2550, 3300)
  Processed shape: (3300, 2550, 3)

Processing complete!
```

**With DEBUG=true:**
```powershell
$env:DEBUG="true"; python preprocess.py path/to/sample.pdf
```
Check `/tmp/debug_page_N.png` files created.

### Test 2: Table Detection Module

```bash
python table_detect.py
```

**Expected Output:**
```
Testing table segmentation...
Test mask shape: (100, 100)
Non-zero pixels: 1680

Detected 5 rows:
  Row 1: lines 10-12 (height: 2)
  Row 2: lines 30-32 (height: 2)
  Row 3: lines 50-52 (height: 2)
  Row 4: lines 70-72 (height: 2)
  Row 5: lines 90-92 (height: 2)

Detected 4 columns:
  Column 1: lines 20-22 (width: 2)
  Column 2: lines 40-42 (width: 2)
  Column 3: lines 60-62 (width: 2)
  Column 4: lines 80-82 (width: 2)

Test complete!
```

### Test 3: OCR Module

```bash
python ocr_cells.py
```

**Expected Output:**
```
Testing extract_amount_from_cell_text()...

Sample inputs and extracted amounts:
------------------------------------------------------------
✓ 'Total Amount: ₹1,234.50    ' -> 1234.5
✓ '(1,200.00)                  ' -> -1200.0
✓ '$500.75                     ' -> 500.75
✓ 'INR 2,50,000.00            ' -> 250000.0
✓ 'Amount: 1234.56 Dr         ' -> -1234.56
...

Testing extract_best_numeric_in_row()...
Extracted best numeric: 1234.5
```

### Test 4: Candidates Module

```bash
python candidates.py
```

**Expected Output:**
```
Testing candidate assembly functions...
============================================================

1. Creating synthetic table image...
   Table shape: (200, 400, 3)
   Rows: 3
   Cols: 3

2. Assembling candidates from table...
   Generated 3 candidate(s)
```

### Test 5: Deduplication Module

```bash
python dedupe.py
```

**Expected Output:**
```
============================================================
DEDUPLICATION MODULE TESTS
============================================================

Testing canonicalize_description()...

Input -> Canonicalized:
------------------------------------------------------------
✓ 'Item - 5 Nos. (Pack)'
   -> 'item 5'
✓ 'Product Description: Test Item'
   -> 'product test item'
...

Testing deduplicate_candidates()...

Input: 4 candidates
Expected: IDs 1, 2, 4 should merge (similar descriptions and amounts)

Output: 2 unique candidates
```

### Test 6: Reconciliation Module

```bash
python reconcile.py
```

**Expected Output:**
```
======================================================================
ILP RECONCILIATION DEMONSTRATION
======================================================================

Test Case 1: Select best candidates (no target total)
----------------------------------------------------------------------
Candidates:
  ID 1: Item A     $100.00 (conf: 95.0)
  ID 2: Item B     $200.00 (conf: 85.0)
  ID 3: Item C     $150.00 (conf: 90.0)
  ID 4: Item D     $ 50.00 (conf: 70.0)

Result:
  Status: ok
  Selected IDs: [1, 2, 3, 4]
  Selected Total: $500.00
  Deviation: $0.00
```

---

## API Testing

### Method 1: Start Server and Check Health

```bash
# Terminal 1: Start server
python app.py
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

```bash
# Terminal 2: Test health endpoint
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status": "healthy"}
```

### Method 2: Interactive API Documentation

1. Start the server (if not running):
   ```bash
   python app.py
   ```

2. Open browser to: **http://localhost:8000/docs**

3. You should see the Swagger UI with available endpoints

4. Click on **"POST /extract-bill-data"**

5. Click **"Try it out"**

6. Enter a test URL in the document field:
   ```
   https://templates.invoicehome.com/invoice-template-us-neat-750px.png
   ```

7. Click **"Execute"**

8. Check the response below

**Expected Response Structure:**
```json
{
  "is_success": true,
  "data": {
    "pagewise_line_items": {
      "1": [
        {
          "id": 1,
          "description": "Product or Service Description",
          "amount": 1234.50,
          "confidence": 92.5
        }
      ]
    },
    "total_item_count": 5,
    "reconciled_amount": 1234.50,
    "reported_total": 1230.00,
    "deviation": 4.50,
    "average_confidence": 90.4,
    "requires_manual_review": false,
    "warnings": [],
    "reconciliation_status": "ok"
  }
}
```

### Method 3: Automated Test Script

```bash
python test_api.py
```

**Interactive Prompt:**
```
======================================================================
INVOICE EXTRACTION API - Test Script
======================================================================

Testing health check endpoint...
✓ Health check passed: {'status': 'healthy'}

======================================================================

Enter invoice PDF URL (or press Enter for demo):
```

Press Enter to use demo URL, or paste your own invoice URL.

**Expected Output:**
```
Using demo URL: https://...

Testing extraction with URL: https://...
----------------------------------------------------------------------
Sending request...
Status code: 200

✓ Extraction successful!

Response summary:
  - Total items: 5
  - Reconciled amount: $1234.50
  - Reported total: $1230.00
  - Deviation: $4.50
  - Avg confidence: 91.3%
  - Manual review: False

✓ Result saved to: test_extraction_result.json
```

### Method 4: cURL Command

**Windows PowerShell:**
```powershell
$body = @{
    document = "https://example.com/invoice.pdf"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/extract-bill-data" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 10
```

**Linux/macOS:**
```bash
curl -X POST "http://localhost:8000/extract-bill-data" \
  -H "Content-Type: application/json" \
  -d '{"document": "https://example.com/invoice.pdf"}' \
  | jq '.'
```

---

## Integration Testing

### Full Pipeline Test

Create a test script `full_pipeline_test.py`:

```python
import requests
import json

def test_full_pipeline():
    """Test complete extraction pipeline."""
    
    # Test URLs (replace with actual invoice URLs)
    test_cases = [
        {
            "name": "Simple Invoice",
            "url": "https://example.com/simple-invoice.pdf",
            "expected_items": 5
        },
        {
            "name": "Multi-page Invoice",
            "url": "https://example.com/multi-page.pdf",
            "expected_items": 15
        }
    ]
    
    for test in test_cases:
        print(f"\nTesting: {test['name']}")
        print("-" * 60)
        
        response = requests.post(
            "http://localhost:8000/extract-bill-data",
            json={"document": test["url"]},
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['is_success']:
                data = result['data']
                item_count = data['total_item_count']
                print(f"✓ Extracted {item_count} items")
                print(f"  Reconciled: ${data['reconciled_amount']:.2f}")
                print(f"  Deviation: ${data['deviation']:.2f}")
            else:
                print(f"✗ Failed: {result.get('error')}")
        else:
            print(f"✗ HTTP {response.status_code}")

if __name__ == "__main__":
    test_full_pipeline()
```

Run it:
```bash
python full_pipeline_test.py
```

---

## Debug Mode Testing

### Enable Debug Output

```powershell
# Windows PowerShell
$env:DEBUG="true"; python app.py
```

```bash
# Linux/macOS
DEBUG=true python app.py
```

### Check Debug Images

Debug images are saved to `/tmp/`:

```bash
# Windows (in WSL or Git Bash)
ls /tmp/*.png

# Linux/macOS
ls -lh /tmp/*.png
```

**Expected Files:**
- `page_1_preprocessed.png` - Preprocessed first page
- `page_2_preprocessed.png` - Preprocessed second page
- `table_debug_N_tables.png` - Table detection visualization

### View Debug Images

```bash
# Windows
start /tmp/page_1_preprocessed.png

# Linux
xdg-open /tmp/page_1_preprocessed.png

# macOS
open /tmp/page_1_preprocessed.png
```

---

## Performance Testing

### Single Request Timing

```python
import time
import requests

url = "http://localhost:8000/extract-bill-data"
payload = {"document": "https://example.com/invoice.pdf"}

start = time.time()
response = requests.post(url, json=payload, timeout=120)
end = time.time()

print(f"Processing time: {end - start:.2f} seconds")
```

### Expected Performance
- **1-page invoice**: 10-20 seconds
- **5-page invoice**: 30-60 seconds
- **10-page invoice**: 60-120 seconds

---

## Troubleshooting

### Issue 1: Server Won't Start

**Symptom:**
```
Error: [Errno 10048] Only one usage of each socket address...
```

**Solution:**
```bash
# Check if port 8000 is in use
netstat -an | findstr :8000  # Windows
lsof -i :8000                # Linux/macOS

# Use different port
uvicorn app:app --port 8001
```

### Issue 2: Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'cv2'
```

**Solution:**
```bash
# Ensure virtual environment is activated
# Look for (venv) in prompt

# Reinstall packages
pip install -r requirements.txt
```

### Issue 3: Tesseract Not Found

**Symptom:**
```
pytesseract.pytesseract.TesseractNotFoundError
```

**Solution (Windows):**
```powershell
# Add to PATH
$env:PATH += ";C:\Program Files\Tesseract-OCR"

# Or set in code (add to app.py)
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Issue 4: PDF Conversion Fails

**Symptom:**
```
pdf2image.exceptions.PDFInfoNotInstalledError
```

**Solution:**
```bash
# Windows: Add poppler to PATH
$env:PATH += ";C:\poppler\Library\bin"

# Linux
sudo apt-get install poppler-utils

# macOS
brew install poppler
```

### Issue 5: Low Accuracy

**Symptom:**
```
Many items missing or incorrect amounts
```

**Solutions:**
1. Check input PDF quality (should be 300+ DPI)
2. Enable debug mode to inspect preprocessing
3. Adjust table detection parameters in `table_detect.py`
4. Lower fuzzy matching threshold in `dedupe.py`

### Issue 6: Request Timeout

**Symptom:**
```
requests.exceptions.Timeout
```

**Solutions:**
1. Increase timeout in test script
2. Process fewer pages
3. Reduce image DPI (200 instead of 300)
4. Check network connection for PDF download

---

## Test Checklist

Before submitting/deploying, verify:

- [ ] All modules pass individual tests
- [ ] Health check endpoint responds
- [ ] Can extract from sample invoice URL
- [ ] Response includes all required fields
- [ ] Confidence scores are reasonable (>80%)
- [ ] Reconciliation matches reported total (±$5)
- [ ] Debug mode saves intermediate images
- [ ] Error handling returns proper status codes
- [ ] Documentation is clear and complete

---

**Testing Complete!** 🎉

Your invoice extraction system is ready for evaluation.
