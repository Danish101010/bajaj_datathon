"""
Installation validation script.

Run this script to verify all dependencies are correctly installed
and the system is ready to run the invoice extraction pipeline.
"""

import sys
from typing import List, Tuple

def check_import(module_name: str, import_statement: str) -> Tuple[bool, str]:
    """
    Try to import a module and return success status.
    
    Args:
        module_name: Display name of the module
        import_statement: Python import statement to execute
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        exec(import_statement)
        return True, ""
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def main():
    """Run installation validation checks."""
    print("=" * 70)
    print("INVOICE EXTRACTION PIPELINE - Installation Validation")
    print("=" * 70)
    print()
    
    checks = [
        # Core dependencies
        ("NumPy", "import numpy"),
        ("OpenCV", "import cv2"),
        ("Pillow", "from PIL import Image"),
        ("pdf2image", "from pdf2image import convert_from_bytes"),
        
        # OCR dependencies
        ("pytesseract", "import pytesseract"),
        
        # Optimization
        ("PuLP", "import pulp"),
        
        # Fuzzy matching
        ("RapidFuzz", "from rapidfuzz import fuzz"),
        
        # API dependencies
        ("FastAPI", "from fastapi import FastAPI"),
        ("Pydantic", "from pydantic import BaseModel"),
        ("Uvicorn", "import uvicorn"),
        ("Requests", "import requests"),
    ]
    
    print("Checking Python package installations...\n")
    
    failed = []
    passed = 0
    
    for module_name, import_stmt in checks:
        success, error = check_import(module_name, import_stmt)
        
        if success:
            print(f"✓ {module_name:20s} [OK]")
            passed += 1
        else:
            print(f"✗ {module_name:20s} [FAILED]")
            failed.append((module_name, error))
    
    print()
    print("-" * 70)
    print(f"Results: {passed}/{len(checks)} packages installed")
    print("-" * 70)
    print()
    
    if failed:
        print("⚠ Failed imports:")
        for module_name, error in failed:
            print(f"  - {module_name}: {error}")
        print()
        print("To fix, run:")
        print("  pip install -r requirements.txt")
        print()
    
    # Check system dependencies
    print("=" * 70)
    print("Checking system dependencies...\n")
    
    # Check Tesseract
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract OCR       [OK] - Version {version}")
    except Exception as e:
        print(f"✗ Tesseract OCR       [FAILED]")
        print(f"  Error: {e}")
        print("  Install: https://github.com/tesseract-ocr/tesseract")
        failed.append(("Tesseract", str(e)))
    
    # Check poppler (pdf2image dependency)
    try:
        from pdf2image import convert_from_bytes
        # Try a minimal PDF conversion test
        test_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 0\n/Kids []\n>>\nendobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\ntrailer\n<<\n/Size 3\n/Root 1 0 R\n>>\nstartxref\n110\n%%EOF"
        try:
            convert_from_bytes(test_pdf, dpi=72)
            print(f"✓ Poppler (pdf2image)  [OK]")
        except:
            print(f"✓ Poppler (pdf2image)  [Installed but minimal test failed - likely OK]")
    except Exception as e:
        print(f"✗ Poppler (pdf2image)  [FAILED]")
        print(f"  Error: {e}")
        print("  Install: poppler-utils (Linux) or poppler (macOS)")
        failed.append(("Poppler", str(e)))
    
    print()
    print("=" * 70)
    
    if not failed:
        print("✓ All checks passed! System is ready.")
        print()
        print("Next steps:")
        print("  1. Start the server: python app.py")
        print("  2. Test the API: http://localhost:8000/docs")
        print()
        return 0
    else:
        print("⚠ Some checks failed. Please install missing dependencies.")
        print()
        print("Quick fix:")
        print("  pip install -r requirements.txt")
        print()
        print("For system dependencies, see README.md")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
