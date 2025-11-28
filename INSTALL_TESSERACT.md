# Installing Tesseract OCR on Windows

Complete step-by-step guide to install Tesseract OCR and add it to your system PATH.

## Method 1: Using the Official Installer (Recommended)

### Step 1: Download Tesseract

1. Go to the official Tesseract Windows installer repository:
   **https://github.com/UB-Mannheim/tesseract/wiki**

2. Click on the latest installer link (usually at the top):
   - For 64-bit Windows: `tesseract-ocr-w64-setup-5.x.x.xxxxxxxx.exe`
   - For 32-bit Windows: `tesseract-ocr-w32-setup-5.x.x.xxxxxxxx.exe`

3. Or download directly from:
   **https://digi.bib.uni-mannheim.de/tesseract/**

### Step 2: Run the Installer

1. Double-click the downloaded `.exe` file

2. Click **"Yes"** when Windows asks for permission

3. In the installer wizard:
   - Click **"Next"** on the welcome screen
   - Accept the license agreement
   - **Important**: Note the installation path (default is `C:\Program Files\Tesseract-OCR`)
   - Keep the default installation path or choose a custom one
   - Select components (keep all defaults)
   - Click **"Install"**

4. Wait for installation to complete

5. Click **"Finish"**

### Step 3: Add Tesseract to System PATH

#### Option A: During Installation
The installer may ask if you want to add Tesseract to PATH. If so, **check the box** and you're done!

#### Option B: Manual PATH Configuration (if not added during install)

**Using GUI (Easiest):**

1. Open **System Properties**:
   - Press `Windows Key + R`
   - Type: `sysdm.cpl`
   - Press Enter

2. Click the **"Advanced"** tab

3. Click **"Environment Variables"** button at the bottom

4. In the **"System variables"** section (bottom half), scroll and find **"Path"**

5. Select **"Path"** and click **"Edit"**

6. Click **"New"**

7. Add the Tesseract path:
   ```
   C:\Program Files\Tesseract-OCR
   ```

8. Click **"OK"** on all windows

**Using PowerShell (Advanced):**

```powershell
# Run PowerShell as Administrator
# Right-click PowerShell icon -> "Run as Administrator"

# Add to User PATH
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Program Files\Tesseract-OCR",
    "User"
)

# OR add to System PATH (requires admin)
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "Machine") + ";C:\Program Files\Tesseract-OCR",
    "Machine"
)
```

**Using Command Prompt (Alternative):**

```cmd
# Run Command Prompt as Administrator

# Add to System PATH
setx /M PATH "%PATH%;C:\Program Files\Tesseract-OCR"
```

### Step 4: Verify Installation

1. **Close and reopen** PowerShell/Command Prompt (important!)

2. Test if Tesseract is accessible:

```powershell
tesseract --version
```

**Expected Output:**
```
tesseract 5.3.3
 leptonica-1.83.1
  libgif 5.2.1 : libjpeg 8d (libjpeg-turbo 2.1.5) : libpng 1.6.40 : libtiff 4.5.1 : zlib 1.2.13 : libwebp 1.3.2 : libopenjp2 2.5.0
 Found AVX2
 Found AVX
 Found FMA
 Found SSE4.1
 Found libarchive 3.6.2 zlib/1.2.13 liblzma/5.4.1 bz2lib/1.0.8 liblz4/1.9.4 libzstd/1.5.2
```

3. Test with Python:

```python
import pytesseract

# Check if it can find tesseract
try:
    version = pytesseract.get_tesseract_version()
    print(f"✓ Tesseract found: Version {version}")
except Exception as e:
    print(f"✗ Error: {e}")
```

## Method 2: Using Chocolatey (Package Manager)

If you have Chocolatey installed:

```powershell
# Run as Administrator
choco install tesseract
```

This automatically adds Tesseract to PATH.

## Method 3: Using Scoop (Package Manager)

If you have Scoop installed:

```powershell
scoop install tesseract
```

## Troubleshooting

### Issue 1: "tesseract is not recognized"

**Cause**: PATH not set correctly or terminal not restarted.

**Solutions**:
1. **Close and reopen** your terminal (very important!)
2. Restart your computer
3. Verify PATH contains `C:\Program Files\Tesseract-OCR`
4. Check if tesseract.exe exists in that folder

**Check PATH:**
```powershell
$env:Path -split ';' | Select-String -Pattern 'Tesseract'
```

### Issue 2: pytesseract can't find tesseract

**Solution 1 - Set in code:**

Add this to the top of your Python script or `app.py`:

```python
import pytesseract

# Windows path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Or if installed in a custom location
pytesseract.pytesseract.tesseract_cmd = r'C:\custom\path\tesseract.exe'
```

**Solution 2 - Environment variable:**

```powershell
# Set permanently for current user
[Environment]::SetEnvironmentVariable(
    "TESSERACT_PATH",
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "User"
)
```

### Issue 3: Permission Denied

**Solution**: Run installer or PowerShell as Administrator
- Right-click → "Run as Administrator"

### Issue 4: Wrong Installation Path

**Check where it's installed:**

```powershell
# Search for tesseract.exe
Get-ChildItem -Path "C:\Program Files" -Recurse -Filter "tesseract.exe" -ErrorAction SilentlyContinue
```

Common locations:
- `C:\Program Files\Tesseract-OCR\`
- `C:\Program Files (x86)\Tesseract-OCR\`
- `C:\Tools\tesseract\`
- `C:\Tesseract-OCR\`

## Verify Complete Setup

Run this verification script:

```python
# test_tesseract.py
import sys

def test_tesseract():
    # Test 1: Command line
    print("Test 1: Command line access")
    import subprocess
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True)
        print(f"✓ Command line: OK")
        print(f"  Version: {result.stdout.split()[1]}")
    except FileNotFoundError:
        print("✗ Command line: FAILED - tesseract not in PATH")
        return False
    
    # Test 2: Python import
    print("\nTest 2: Python pytesseract")
    try:
        import pytesseract
        print("✓ Import pytesseract: OK")
    except ImportError:
        print("✗ Import pytesseract: FAILED - run: pip install pytesseract")
        return False
    
    # Test 3: Get version via Python
    print("\nTest 3: Get version via Python")
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✓ Python access: OK")
        print(f"  Version: {version}")
    except Exception as e:
        print(f"✗ Python access: FAILED - {e}")
        return False
    
    # Test 4: Simple OCR test
    print("\nTest 4: Simple OCR test")
    try:
        from PIL import Image
        import numpy as np
        
        # Create a simple test image with text
        img = np.ones((50, 200, 3), dtype=np.uint8) * 255
        pil_img = Image.fromarray(img)
        
        text = pytesseract.image_to_string(pil_img)
        print(f"✓ OCR test: OK")
    except Exception as e:
        print(f"✗ OCR test: FAILED - {e}")
        return False
    
    print("\n" + "="*50)
    print("✓ All Tesseract tests passed!")
    return True

if __name__ == "__main__":
    success = test_tesseract()
    sys.exit(0 if success else 1)
```

Run it:
```powershell
python test_tesseract.py
```

## Alternative: Portable Installation (No Admin Required)

If you can't install with admin rights:

1. Download Tesseract portable version
2. Extract to a folder (e.g., `C:\Users\YourName\tesseract`)
3. Set PATH for current session only:

```powershell
$env:Path += ";C:\Users\YourName\tesseract"
```

4. Or set in Python code:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\YourName\tesseract\tesseract.exe'
```

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ TESSERACT QUICK REFERENCE                               │
├─────────────────────────────────────────────────────────┤
│ Download: https://github.com/UB-Mannheim/tesseract/wiki│
│ Default Path: C:\Program Files\Tesseract-OCR           │
│ Test Command: tesseract --version                       │
│                                                         │
│ Add to PATH:                                            │
│  1. Windows Key + R → sysdm.cpl                         │
│  2. Advanced → Environment Variables                    │
│  3. Edit PATH → Add: C:\Program Files\Tesseract-OCR    │
│  4. Restart terminal                                    │
│                                                         │
│ Python fallback:                                        │
│  pytesseract.pytesseract.tesseract_cmd = r'C:\...'    │
└─────────────────────────────────────────────────────────┘
```

---

**Need more help?**
- Official docs: https://tesseract-ocr.github.io/
- GitHub issues: https://github.com/tesseract-ocr/tesseract/issues
- pytesseract docs: https://github.com/madmaze/pytesseract
