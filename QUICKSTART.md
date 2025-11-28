# Quick Start Guide

Get the invoice extraction API running in 5 minutes!

## 📦 Step 1: Install System Dependencies

### Windows
1. Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
   - Download installer and run
   - Add to PATH: `C:\Program Files\Tesseract-OCR`

2. Install [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)
   - Download latest release
   - Extract to `C:\poppler`
   - Add to PATH: `C:\poppler\Library\bin`

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
```

### macOS
```bash
brew install poppler tesseract
```

## 🐍 Step 2: Set Up Python Environment

Open PowerShell/Terminal in project directory:

```powershell
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## ✅ Step 3: Verify Installation

```bash
python test_installation.py
```

Expected output:
```
✓ NumPy               [OK]
✓ OpenCV              [OK]
✓ Pillow              [OK]
...
✓ All checks passed! System is ready.
```

## 🚀 Step 4: Start the Server

```bash
python app.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 🧪 Step 5: Test the API

### Option A: Interactive Docs (Easiest)
Open browser: **http://localhost:8000/docs**

1. Click on "POST /extract-bill-data"
2. Click "Try it out"
3. Enter a PDF URL in the document field
4. Click "Execute"

### Option B: Test Script
```bash
python test_api.py
```

### Option C: cURL
```bash
curl -X POST "http://localhost:8000/extract-bill-data" \
  -H "Content-Type: application/json" \
  -d "{\"document\": \"https://example.com/invoice.pdf\"}"
```

## 🎉 Success!

If you see extracted line items with amounts, confidence scores, and reconciliation data - you're all set!

## 🐛 Troubleshooting

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "TesseractNotFoundError"
- **Windows**: Add Tesseract to PATH
- **Linux**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`

### "PDFInfoNotInstalledError"
- **Windows**: Add Poppler to PATH
- **Linux**: `sudo apt-get install poppler-utils`
- **macOS**: `brew install poppler`

### Server won't start
```bash
# Check if port 8000 is in use
netstat -an | findstr :8000  # Windows
lsof -i :8000                # Linux/macOS

# Use different port
uvicorn app:app --port 8001
```

## 📚 Next Steps

- See **README.md** for complete documentation
- Check **test_api.py** for usage examples
- Review module files for implementation details
- Enable debug mode: `$env:DEBUG="true"; python app.py`

## 🔗 Quick Links

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- ReDoc: http://localhost:8000/redoc

---

**Need Help?** Check the README.md or review the logs for detailed error messages.
