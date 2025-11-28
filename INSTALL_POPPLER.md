# Installing Poppler on Windows

Complete step-by-step guide to install Poppler (required for pdf2image) and add it to your system PATH.

## What is Poppler?

Poppler is a PDF rendering library that includes utilities like `pdftoppm` (PDF to image converter). The Python library `pdf2image` uses Poppler's `pdftoppm` utility to convert PDF pages to images.

## Method 1: Download Pre-built Binaries (Recommended)

### Step 1: Download Poppler

**Option A: Official Repository (Most Current)**

1. Go to: **https://github.com/oschwartz10612/poppler-windows/releases**

2. Download the latest release:
   - Look for `Release-XX.XX.X-0` (latest version at top)
   - Download: **`Release-XX.XX.X-0.zip`**
   - Example: `Release-24.02.0-0.zip`

**Option B: Alternative Download Site**

1. Go to: **https://blog.alivate.com.au/poppler-windows/**
2. Download the latest `poppler-XX.XX.X_x86.7z` or `.zip` file

### Step 2: Extract Poppler

1. **Choose installation location:**
   - Recommended: `C:\poppler`
   - Or any location without spaces (e.g., `C:\Tools\poppler`)

2. **Extract the downloaded archive:**
   - Right-click the `.zip` file
   - Select **"Extract All..."**
   - Choose destination: `C:\poppler`
   - Click **"Extract"**

3. **Verify the structure:**
   After extraction, you should have:
   ```
   C:\poppler\
   ├── Library\
   │   ├── bin\           ← This folder contains the executables
   │   │   ├── pdftoppm.exe
   │   │   ├── pdfinfo.exe
   │   │   └── ... (other utilities)
   │   ├── include\
   │   └── lib\
   └── share\
   ```

   **Important**: The executables are in `C:\poppler\Library\bin\`

### Step 3: Add Poppler to System PATH

The PATH should point to the `bin` folder containing the executables.

#### Option A: Using GUI (Recommended)

1. Open **System Properties**:
   - Press `Windows Key + R`
   - Type: `sysdm.cpl`
   - Press Enter

2. Click the **"Advanced"** tab

3. Click **"Environment Variables"** button (bottom)

4. In **"System variables"** section (bottom half):
   - Scroll and find **"Path"**
   - Select it and click **"Edit"**

5. In the Edit window:
   - Click **"New"**
   - Add: `C:\poppler\Library\bin`
   - Click **"OK"**

6. Click **"OK"** on all remaining windows

#### Option B: Using PowerShell (Advanced)

```powershell
# Run PowerShell as Administrator
# Right-click PowerShell → "Run as Administrator"

# Add to System PATH (requires admin)
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "Machine") + ";C:\poppler\Library\bin",
    "Machine"
)

# OR add to User PATH (no admin needed)
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\poppler\Library\bin",
    "User"
)
```

#### Option C: Using Command Prompt

```cmd
# Run Command Prompt as Administrator

# Add to System PATH
setx /M PATH "%PATH%;C:\poppler\Library\bin"
```

### Step 4: Verify Installation

1. **Close and reopen** PowerShell/Command Prompt (very important!)

2. Test if Poppler is accessible:

```powershell
pdftoppm -v
```

**Expected Output:**
```
pdftoppm version 24.02.0
Copyright 2005-2024 The Poppler Developers - http://poppler.freedesktop.org
Copyright 1996-2011, 2022 Glyph & Cog, LLC
```

3. Test other utilities:

```powershell
pdfinfo -v
```

4. Test with Python:

```python
from pdf2image import convert_from_path

# Try converting a sample PDF
try:
    images = convert_from_path('sample.pdf', dpi=200)
    print(f"✓ Poppler working! Converted {len(images)} page(s)")
except Exception as e:
    print(f"✗ Error: {e}")
```

## Method 2: Using Conda (If Using Anaconda/Miniconda)

If you're using Conda:

```bash
conda install -c conda-forge poppler
```

This automatically handles PATH configuration.

## Method 3: Using Chocolatey (Package Manager)

If you have Chocolatey installed:

```powershell
# Run as Administrator
choco install poppler
```

## Method 4: Using Scoop (Package Manager)

If you have Scoop installed:

```powershell
scoop install poppler
```

## Troubleshooting

### Issue 1: "pdftoppm is not recognized"

**Cause**: PATH not set correctly or terminal not restarted.

**Solutions**:

1. **Restart your terminal** (close and reopen)
2. Restart your computer
3. Verify PATH contains `C:\poppler\Library\bin`

**Check PATH:**
```powershell
$env:Path -split ';' | Select-String -Pattern 'poppler'
```

**Check if pdftoppm.exe exists:**
```powershell
Test-Path "C:\poppler\Library\bin\pdftoppm.exe"
```

Should return `True`

### Issue 2: pdf2image can't find poppler

**Error:**
```
pdf2image.exceptions.PDFInfoNotInstalledError: Unable to get page count. Is poppler installed and in PATH?
```

**Solution 1 - Specify poppler path in code:**

```python
from pdf2image import convert_from_path

images = convert_from_path(
    'invoice.pdf',
    dpi=300,
    poppler_path=r'C:\poppler\Library\bin'
)
```

**Solution 2 - Set in your app.py:**

Add this near the top of `app.py`:

```python
import os

# Set poppler path if not in PATH
POPPLER_PATH = r'C:\poppler\Library\bin'
if os.path.exists(POPPLER_PATH):
    os.environ['PATH'] = POPPLER_PATH + os.pathsep + os.environ.get('PATH', '')
```

**Solution 3 - Environment variable:**

```powershell
# Set permanently
[Environment]::SetEnvironmentVariable(
    "POPPLER_PATH",
    "C:\poppler\Library\bin",
    "User"
)
```

### Issue 3: Wrong folder structure

**Problem**: Extracted folder structure is different than expected.

**Solution**: 
Make sure you're adding the correct path to PATH. The path should contain `pdftoppm.exe`.

**Find pdftoppm.exe:**
```powershell
Get-ChildItem -Path "C:\poppler" -Recurse -Filter "pdftoppm.exe" -ErrorAction SilentlyContinue
```

Add that folder to PATH (usually `C:\poppler\Library\bin`)

### Issue 4: Permission issues during extraction

**Solution**: 
- Extract to a user folder instead: `C:\Users\YourName\poppler`
- Or run extraction as Administrator

### Issue 5: Path with spaces causes issues

**Solution**:
Avoid paths with spaces. Instead of:
- ❌ `C:\Program Files\poppler`
- ✅ `C:\poppler`
- ✅ `C:\Tools\poppler`

If you must use spaces, ensure you quote the path in code:
```python
poppler_path = r'C:\Program Files\poppler\Library\bin'
```

## Verify Complete Setup

Run this verification script:

```python
# test_poppler.py
import sys
import os

def test_poppler():
    print("Testing Poppler Installation")
    print("=" * 60)
    
    # Test 1: Command line access
    print("\nTest 1: Command line access")
    import subprocess
    try:
        result = subprocess.run(['pdftoppm', '-v'], 
                              capture_output=True, text=True)
        version_line = result.stdout.split('\n')[0]
        print(f"✓ Command line: OK")
        print(f"  {version_line}")
    except FileNotFoundError:
        print("✗ Command line: FAILED")
        print("  pdftoppm not found in PATH")
        return False
    
    # Test 2: Check PATH
    print("\nTest 2: Check PATH")
    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    poppler_in_path = any('poppler' in p.lower() for p in path_dirs)
    if poppler_in_path:
        poppler_dirs = [p for p in path_dirs if 'poppler' in p.lower()]
        print(f"✓ Poppler in PATH")
        for p in poppler_dirs:
            print(f"  {p}")
    else:
        print("✗ Poppler not in PATH")
        print("  This may cause issues with pdf2image")
    
    # Test 3: Python pdf2image import
    print("\nTest 3: Import pdf2image")
    try:
        from pdf2image import convert_from_bytes
        print("✓ pdf2image imported successfully")
    except ImportError:
        print("✗ pdf2image not installed")
        print("  Run: pip install pdf2image")
        return False
    
    # Test 4: Convert sample PDF
    print("\nTest 4: PDF conversion test")
    try:
        from pdf2image import convert_from_bytes
        
        # Minimal valid PDF
        sample_pdf = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Page) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000315 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
408
%%EOF"""
        
        images = convert_from_bytes(sample_pdf, dpi=72)
        print(f"✓ PDF conversion: OK")
        print(f"  Converted {len(images)} page(s)")
        print(f"  Image size: {images[0].size}")
    except Exception as e:
        print(f"✗ PDF conversion: FAILED")
        print(f"  Error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All Poppler tests passed!")
    print("\nPoppler is correctly installed and configured.")
    return True

if __name__ == "__main__":
    success = test_poppler()
    sys.exit(0 if success else 1)
```

Run it:
```powershell
python test_poppler.py
```

## Integration with Your Invoice Extractor

Once Poppler is installed, your invoice extraction pipeline will work. The `preprocess.py` module uses it:

```python
from pdf2image import convert_from_bytes

def convert_pdf_bytes_to_images(pdf_bytes: bytes, dpi: int = 300):
    """Convert PDF bytes to PIL images using Poppler."""
    images = convert_from_bytes(pdf_bytes, dpi=dpi)
    return images
```

If you need to specify poppler path explicitly:

```python
# In preprocess.py, modify the function:
def convert_pdf_bytes_to_images(pdf_bytes: bytes, dpi: int = 300):
    """Convert PDF bytes to PIL images using Poppler."""
    images = convert_from_bytes(
        pdf_bytes, 
        dpi=dpi,
        poppler_path=r'C:\poppler\Library\bin'  # Specify if not in PATH
    )
    return images
```

## Alternative: Portable Installation (No Admin)

If you can't modify system PATH:

1. Extract Poppler to your user folder:
   ```
   C:\Users\YourName\poppler\Library\bin
   ```

2. Set PATH for current PowerShell session:
   ```powershell
   $env:Path += ";C:\Users\YourName\poppler\Library\bin"
   ```

3. Or set in Python at runtime:
   ```python
   import os
   os.environ['PATH'] += r';C:\Users\YourName\poppler\Library\bin'
   ```

## Quick Reference Card

```
┌──────────────────────────────────────────────────────────────┐
│ POPPLER QUICK REFERENCE                                      │
├──────────────────────────────────────────────────────────────┤
│ Download: https://github.com/oschwartz10612/poppler-windows │
│ Extract to: C:\poppler                                       │
│ Add to PATH: C:\poppler\Library\bin                          │
│ Test Command: pdftoppm -v                                    │
│                                                              │
│ Key Files:                                                   │
│  - pdftoppm.exe  (PDF to image converter)                   │
│  - pdfinfo.exe   (PDF information)                          │
│  - pdfimages.exe (Extract images from PDF)                  │
│                                                              │
│ Add to PATH:                                                 │
│  1. Windows Key + R → sysdm.cpl                              │
│  2. Advanced → Environment Variables                         │
│  3. Edit PATH → Add: C:\poppler\Library\bin                  │
│  4. Restart terminal                                         │
│                                                              │
│ Python usage:                                                │
│  from pdf2image import convert_from_bytes                   │
│  images = convert_from_bytes(pdf_bytes, dpi=300)           │
└──────────────────────────────────────────────────────────────┘
```

## Common Installation Locations

After installation, verify one of these paths exists:

```powershell
# Check common locations
Test-Path "C:\poppler\Library\bin\pdftoppm.exe"
Test-Path "C:\Program Files\poppler\bin\pdftoppm.exe"
Test-Path "C:\Tools\poppler\Library\bin\pdftoppm.exe"
```

---

**Need more help?**
- Poppler project: https://poppler.freedesktop.org/
- pdf2image docs: https://github.com/Belval/pdf2image
- Windows builds: https://github.com/oschwartz10612/poppler-windows

**Next Step**: After installing both Tesseract and Poppler, run:
```powershell
python test_installation.py
```

This will verify all dependencies are correctly installed!
