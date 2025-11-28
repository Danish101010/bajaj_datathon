"""
Image preprocessing module for invoice extraction.

Handles PDF conversion, deskewing, illumination correction, and contrast enhancement
to prepare images for OCR and table detection.
"""

import os
import sys
from typing import List

import numpy as np
import cv2
from PIL import Image
from pdf2image import convert_from_bytes


def convert_pdf_bytes_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[Image.Image]:
    """
    Convert PDF bytes or image bytes to a list of PIL Images.
    
    Handles both PDF files and direct image formats (PNG, JPG, etc.).
    
    Args:
        pdf_bytes: PDF or image file content as bytes
        dpi: Resolution for rendering PDFs (default: 300)
    
    Returns:
        List of PIL Image objects, one per page (or single image)
    
    Raises:
        Exception: If conversion fails
    """
    # First, try to open as a direct image (PNG, JPG, etc.)
    try:
        from io import BytesIO
        img = Image.open(BytesIO(pdf_bytes))
        # If successful, return as single-page list
        return [img]
    except Exception:
        # Not a direct image, try PDF conversion
        pass
    
    # Try PDF conversion
    try:
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        return images
    except Exception as e:
        raise Exception(f"Failed to convert PDF to images: {str(e)}")


def deskew_and_illum_correction(pil_img: Image.Image) -> np.ndarray:
    """
    Apply deskewing and illumination correction to prepare image for OCR.
    
    For modern clean invoices, minimal processing is best.
    Only apply preprocessing if image quality is poor.
    
    Args:
        pil_img: Input PIL Image
    
    Returns:
        Preprocessed image as BGR numpy array
    
    Raises:
        ValueError: If image is invalid or empty
    """
    if pil_img is None:
        raise ValueError("Input image is None")
    
    # Convert PIL to OpenCV BGR
    img_rgb = np.array(pil_img.convert('RGB'))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    
    if img_bgr.size == 0:
        raise ValueError("Image is empty")
    
    # For modern digital invoices, return as-is
    # Aggressive preprocessing (deskewing, thresholding) often damages clean text
    return img_bgr


def _deskew_image(img_bgr: np.ndarray) -> np.ndarray:
    """
    Detect and correct image skew using contour analysis.
    
    Args:
        img_bgr: Input BGR image
    
    Returns:
        Deskewed BGR image
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Threshold to get dark pixels (text)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find contours to detect text regions
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return img_bgr
    
    # Combine all contours to find overall orientation
    all_points = np.vstack(contours)
    
    # Get minimum area rectangle
    rect = cv2.minAreaRect(all_points)
    angle = rect[-1]
    
    # Correct angle orientation
    # minAreaRect returns angle in [-90, 0)
    if angle < -45:
        angle = 90 + angle
    
    # Only correct if angle is significant (> 0.5 degrees)
    if abs(angle) < 0.5:
        return img_bgr
    
    # Rotate image to correct skew
    h, w = img_bgr.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate new image dimensions to avoid cropping
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    
    # Adjust rotation matrix for new dimensions
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]
    
    rotated = cv2.warpAffine(
        img_bgr,
        rotation_matrix,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    
    return rotated


def _correct_illumination(img_bgr: np.ndarray) -> np.ndarray:
    """
    Correct uneven illumination using background estimation.
    
    Args:
        img_bgr: Input BGR image
    
    Returns:
        Illumination-corrected BGR image
    """
    # Convert to LAB color space for better illumination handling
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Estimate background using large Gaussian blur
    kernel_size = max(img_bgr.shape[0], img_bgr.shape[1]) // 10
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel_size = max(kernel_size, 51)  # Minimum kernel size
    
    background = cv2.GaussianBlur(l_channel, (kernel_size, kernel_size), 0)
    
    # Divide to normalize illumination
    # Add small constant to avoid division by zero
    l_corrected = cv2.divide(
        l_channel.astype(np.float32),
        background.astype(np.float32) + 1e-6,
        scale=255
    )
    l_corrected = np.clip(l_corrected, 0, 255).astype(np.uint8)
    
    # Merge channels back
    lab_corrected = cv2.merge([l_corrected, a_channel, b_channel])
    img_corrected = cv2.cvtColor(lab_corrected, cv2.COLOR_LAB2BGR)
    
    return img_corrected


def _apply_clahe(img_bgr: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        img_bgr: Input BGR image
    
    Returns:
        Contrast-enhanced BGR image
    """
    # Convert to LAB and apply CLAHE to L channel only
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Create CLAHE object
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l_channel)
    
    # Merge channels
    lab_clahe = cv2.merge([l_clahe, a_channel, b_channel])
    img_clahe = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
    
    return img_clahe


def save_debug_image(img_bgr: np.ndarray, path: str) -> None:
    """
    Save debug image to disk if DEBUG environment variable is set.
    
    Args:
        img_bgr: BGR image to save
        path: Output file path
    
    Raises:
        IOError: If image save fails
    """
    debug_enabled = os.environ.get('DEBUG', '').lower() == 'true'
    
    if not debug_enabled:
        return
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        success = cv2.imwrite(path, img_bgr)
        if not success:
            raise IOError(f"Failed to write image to {path}")
        print(f"Debug image saved: {path}")
    except Exception as e:
        raise IOError(f"Error saving debug image: {str(e)}")


def main():
    """
    Test preprocessing pipeline with a sample file.
    
    Usage:
        python preprocess.py <filepath>
    """
    if len(sys.argv) < 2:
        print("Usage: python preprocess.py <filepath>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    print(f"Processing: {filepath}")
    
    try:
        # Read file
        with open(filepath, 'rb') as f:
            file_bytes = f.read()
        
        # Convert PDF to images
        print("Converting PDF to images...")
        images = convert_pdf_bytes_to_images(file_bytes, dpi=300)
        print(f"Converted {len(images)} page(s)")
        
        # Process each page
        for idx, pil_img in enumerate(images):
            print(f"\nProcessing page {idx + 1}...")
            print(f"  Original size: {pil_img.size}")
            
            # Apply preprocessing
            processed = deskew_and_illum_correction(pil_img)
            print(f"  Processed shape: {processed.shape}")
            
            # Save debug image
            debug_path = f"/tmp/debug_page_{idx + 1}.png"
            save_debug_image(processed, debug_path)
        
        print("\nProcessing complete!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
