# Invoice Extraction Pipeline

A complete invoice data extraction system built for hackathon evaluation. Extracts line items from PDF invoices using OCR, table detection, fuzzy deduplication, and ILP-based reconciliation.

## 🎯 Features

- **PDF Processing**: Automatic conversion and preprocessing with deskewing & illumination correction
- **Table Detection**: Morphological analysis to detect and segment invoice tables
- **OCR Extraction**: Tesseract-based text extraction with confidence scoring
- **Smart Deduplication**: Fuzzy matching to remove duplicate entries
- **ILP Reconciliation**: Optimization-based selection matching reported totals
- **REST API**: FastAPI endpoint for easy integration
- **Debug Mode**: Visual debugging with intermediate image outputs

## 🛠️ Tech Stack

- **Image Processing**: OpenCV, PIL, pdf2image
- **OCR**: Tesseract OCR with pytesseract wrapper
- **Optimization**: PuLP ILP solver (CBC backend)
- **Fuzzy Matching**: RapidFuzz for text similarity
- **API Framework**: FastAPI with Pydantic validation
- **Server**: Uvicorn ASGI server

## 📋 Prerequisites

### System Dependencies (Required)

**Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
```

**macOS:**
```bash
brew install poppler tesseract
```

**Windows:**
- Download and install [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)
- Download and install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- Add both to your system PATH

### Python Requirements

Python 3.10 or higher recommended.

## 🚀 Installation

### 1. Clone/Navigate to Project Directory

```bash
cd datathon
```

### 2. Create Virtual Environment (Recommended)

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## 🏃 Running the Application

### Start the API Server

**Standard Mode:**
```bash
python app.py
```

Or using uvicorn directly:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Debug Mode (with image outputs):**
```bash
# Windows PowerShell
$env:DEBUG="true"; python app.py

# Linux/macOS
DEBUG=true python app.py
```

The server will start at `http://localhost:8000`

### Verify Server is Running

Open browser to: `http://localhost:8000`

Or test health endpoint:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

## 🧪 Testing the API

### Method 1: Using cURL (Command Line)

**Extract from PDF URL:**
```bash
curl -X POST "http://localhost:8000/extract-bill-data" \
  -H "Content-Type: application/json" \
  -d "{\"document\": \"https://example.com/sample-invoice.pdf\"}"
```

**Windows PowerShell:**
```powershell
$body = @{
    document = "https://example.com/sample-invoice.pdf"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/extract-bill-data" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

### Method 2: Using Python Requests

Create a test script `test_api.py`:

```python
import requests
import json

url = "http://localhost:8000/extract-bill-data"
payload = {
    "document": "https://example.com/sample-invoice.pdf"
}

response = requests.post(url, json=payload)
print(json.dumps(response.json(), indent=2))
```

Run it:
```bash
python test_api.py
```

### Method 3: Interactive API Docs

FastAPI provides automatic interactive documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

Navigate to these URLs in your browser to test the API interactively.

### Sample Test URLs

You can use these public invoice samples for testing:
- `https://templates.invoicehome.com/invoice-template-us-neat-750px.png`
- Any publicly accessible PDF invoice URL

## 📊 API Reference

### POST /extract-bill-data

**Request Body:**
```json
{
  "document": "https://example.com/invoice.pdf"
}
```

**Success Response (200 OK):**
```json
{
  "is_success": true,
  "data": {
    "pagewise_line_items": {
      "1": [
        {
          "id": 1,
          "description": "Product A - Professional Services",
          "amount": 1234.50,
          "confidence": 92.5
        },
        {
          "id": 2,
          "description": "Product B - Consulting",
          "amount": 500.00,
          "confidence": 88.3
        }
      ]
    },
    "total_item_count": 2,
    "reconciled_amount": 1734.50,
    "reported_total": 1730.00,
    "deviation": 4.50,
    "average_confidence": 90.4,
    "requires_manual_review": false,
    "warnings": [],
    "reconciliation_status": "ok"
  }
}
```

**Error Response (400/500):**
```json
{
  "is_success": false,
  "error": "Failed to download PDF: Connection timeout"
}
```

### Response Fields Explained

- **pagewise_line_items**: Line items grouped by page number
- **total_item_count**: Total number of extracted line items
- **reconciled_amount**: Sum of selected items after ILP optimization
- **reported_total**: Total amount found in invoice (e.g., "Grand Total")
- **deviation**: Absolute difference between reconciled and reported
- **average_confidence**: Mean OCR confidence score (0-100)
- **requires_manual_review**: Flag indicating if human review recommended
- **warnings**: List of issues detected during processing
- **reconciliation_status**: ILP solver status (`ok` or `infeasible`)

## 📁 Project Structure

```
datathon/
├── app.py                  # FastAPI application & main endpoints
├── preprocess.py           # PDF conversion & image preprocessing
├── table_detect.py         # Table detection & segmentation
├── ocr_cells.py           # OCR wrapper & text extraction
├── candidates.py          # Candidate assembly & row merging
├── dedupe.py              # Deduplication & filtering logic
├── reconcile.py           # ILP-based reconciliation
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── README.md             # This file
```

### Module Descriptions

- **app.py**: REST API with extraction pipeline orchestration
- **preprocess.py**: Deskewing, illumination correction, CLAHE enhancement
- **table_detect.py**: Morphological line detection and table segmentation
- **ocr_cells.py**: Tesseract wrapper with token extraction and amount parsing
- **candidates.py**: Cell-by-cell OCR and candidate line item assembly
- **dedupe.py**: Fuzzy matching, canonicalization, header/footer filtering
- **reconcile.py**: PuLP ILP formulation for optimal item selection

## 🐳 Docker Deployment

### Build Image

```bash
docker build -t invoice-extractor .
```

### Run Container

```bash
docker run -p 8000:8000 invoice-extractor
```

### With Debug Mode

```bash
docker run -p 8000:8000 -e DEBUG=true invoice-extractor
```

### Access API

```bash
curl http://localhost:8000/health
```

## 🔍 Testing Individual Modules

Each module includes test functions in `__main__` blocks:

### Test Preprocessing
```bash
python preprocess.py path/to/invoice.pdf
```

### Test Table Detection
```bash
python table_detect.py
```

### Test OCR Extraction
```bash
python ocr_cells.py
```

### Test Candidate Assembly
```bash
python candidates.py
```

### Test Deduplication
```bash
python dedupe.py
```

### Test ILP Reconciliation
```bash
python reconcile.py
```

## 🐛 Debugging

### Enable Debug Mode

Set environment variable to save intermediate images to `/tmp`:

```bash
# Windows
$env:DEBUG="true"

# Linux/macOS
export DEBUG=true
```

Debug outputs:
- `/tmp/page_N_preprocessed.png` - Preprocessed pages
- `/tmp/debug_page_N.png` - Processing artifacts
- `/tmp/table_debug_N_tables.png` - Table detection visualization

### Check Logs

The application streams detailed logs to stdout:

```
2025-11-28 10:30:15 - app - INFO - Starting extraction for document: https://...
2025-11-28 10:30:16 - app - INFO - Step 1: Downloading PDF...
2025-11-28 10:30:17 - app - INFO - Downloaded 245632 bytes
2025-11-28 10:30:17 - app - INFO - Step 2: Converting PDF to images...
2025-11-28 10:30:18 - app - INFO - Converted to 3 page(s)
...
```

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'cv2'`
- **Solution**: `pip install opencv-python-headless`

**Issue**: `TesseractNotFoundError`
- **Solution**: Install Tesseract OCR and add to PATH

**Issue**: `pdf2image.exceptions.PDFInfoNotInstalledError`
- **Solution**: Install poppler-utils

**Issue**: `PulpSolverError: Pulp: Error while trying to execute cbc`
- **Solution**: PuLP should install CBC automatically, try reinstalling: `pip install --force-reinstall pulp`

## 🎓 Algorithm Overview

### Extraction Pipeline

1. **Download & Convert**: Fetch PDF and convert to 300 DPI images
2. **Preprocess**: Deskew using minAreaRect, correct illumination, apply CLAHE
3. **Detect Tables**: Extract horizontal/vertical lines, combine masks, find contours
4. **Segment Cells**: Compute row/column projections to identify boundaries
5. **OCR Cells**: Extract text with confidence from each cell
6. **Assemble Candidates**: Build line items with description and amount
7. **Merge Wrapped**: Combine continuation rows based on proximity
8. **Filter Headers**: Remove repeated top/bottom regions across pages
9. **Deduplicate**: Fuzzy match similar items (token_set_ratio ≥ 88)
10. **Reconcile**: ILP optimization to match reported total
11. **Return Results**: Structured JSON with warnings and review flags

### ILP Formulation

```
Maximize: Σ(confidence_i × x_i) - 10 × z

Subject to:
- x_i ∈ {0, 1}  (binary: select item or not)
- |Σ(amount_i × x_i) - reported_total| ≤ tolerance
- Σ(x_j) ≤ 1  for each duplicate group
- z = absolute deviation from target
```

## 📝 License

This project is developed for hackathon evaluation purposes.

## 🤝 Contributing

For issues or improvements, please document changes clearly with appropriate testing.

## 📧 Support

For technical questions during hackathon evaluation, refer to this documentation or check module-level docstrings for implementation details.
