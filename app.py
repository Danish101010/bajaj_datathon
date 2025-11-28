"""
FastAPI application for invoice data extraction.

Provides REST API endpoints to extract structured line item data from
invoice PDFs using OCR, table detection, and ILP reconciliation.
"""

import os
import re
import logging
from typing import List, Dict, Optional
from io import BytesIO

import requests
import numpy as np
import pytesseract
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

# Import custom modules
from preprocess import convert_pdf_bytes_to_images, deskew_and_illum_correction, save_debug_image
from table_detect import detect_tables, segment_table_into_rows_and_cols
from candidates import assemble_candidates_from_table, merge_wrapped_rows
from dedupe import deduplicate_candidates, repeated_header_footer_filter
from reconcile import ilp_reconcile, make_duplicate_groups_from_candidates
from text_based_extraction import extract_candidates_text_based, extract_reported_total_text_based


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Invoice Extraction API",
    description="Extract structured line item data from invoice PDFs",
    version="1.0.0"
)

# Configure CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ExtractionRequest(BaseModel):
    """Request model for invoice extraction."""
    document: str = Field(..., description="URL to the PDF invoice document")
    
    @validator('document')
    def validate_document_url(cls, v):
        """Validate document URL format."""
        if not v or not isinstance(v, str):
            raise ValueError("Document URL must be a non-empty string")
        
        # Basic URL validation
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Document URL must start with http:// or https://")
        
        return v


class LineItem(BaseModel):
    """Model for a single line item."""
    id: int
    description: str
    amount: Optional[float]
    quantity: Optional[int] = None
    rate: Optional[float] = None
    confidence: float
    page: int


class ExtractionResponse(BaseModel):
    """Response model for invoice extraction."""
    is_success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "service": "Invoice Extraction API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/extract-bill-data", response_model=ExtractionResponse)
async def extract_bill_data(request: ExtractionRequest):
    """
    Extract structured line item data from an invoice PDF.
    
    Process:
    1. Download PDF from provided URL
    2. Convert to images and preprocess
    3. Detect tables and extract candidates
    4. Deduplicate and reconcile against reported total
    5. Return structured JSON response
    
    Args:
        request: ExtractionRequest with document URL
    
    Returns:
        ExtractionResponse with extracted data or error
    """
    logger.info(f"Starting extraction for document: {request.document}")
    
    try:
        # Step 1: Download PDF
        logger.info("Step 1: Downloading PDF...")
        pdf_bytes = download_pdf(request.document)
        logger.info(f"Downloaded {len(pdf_bytes)} bytes")
        
        # Step 2: Convert PDF to images
        logger.info("Step 2: Converting PDF to images...")
        pages_images_pil = convert_pdf_bytes_to_images(pdf_bytes, dpi=300)
        logger.info(f"Converted to {len(pages_images_pil)} page(s)")
        
        # Step 3: Process each page
        logger.info("Step 3: Processing pages and extracting candidates...")
        all_candidates = []
        pages_images_bgr = []
        
        for page_no, pil_img in enumerate(pages_images_pil, start=1):
            logger.info(f"  Processing page {page_no}...")
            
            # Preprocess: deskew and illumination correction
            img_bgr = deskew_and_illum_correction(pil_img)
            pages_images_bgr.append(img_bgr)
            
            # Save debug image
            if os.environ.get('DEBUG', '').lower() == 'true':
                save_debug_image(img_bgr, f"/tmp/page_{page_no}_preprocessed.png")
            
            # Use text-based extraction directly (more reliable for modern digital invoices)
            logger.info("    Using text-based extraction...")
            page_candidates = extract_candidates_text_based(img_bgr, page_no)
            logger.info(f"    Extracted {len(page_candidates)} candidate(s)")
            
            all_candidates.extend(page_candidates)
        
        logger.info(f"Total candidates extracted: {len(all_candidates)}")
        
        # Step 4: Merge wrapped rows
        logger.info("Step 4: Merging wrapped rows...")
        all_candidates = merge_wrapped_rows(all_candidates)
        logger.info(f"After merge: {len(all_candidates)} candidate(s)")
        
        # Step 5: Filter repeated headers/footers
        logger.info("Step 5: Filtering repeated headers/footers...")
        if len(pages_images_bgr) > 1:
            all_candidates, filtered = repeated_header_footer_filter(
                all_candidates,
                pages_images_bgr
            )
            logger.info(f"Filtered {len(filtered)} header/footer item(s)")
        
        # Step 6: Deduplicate candidates
        logger.info("Step 6: Deduplicating candidates...")
        # Lower threshold from 88 to 85 to avoid over-aggressive deduplication
        deduped_candidates = deduplicate_candidates(all_candidates, ratio_thresh=85)
        logger.info(f"After deduplication: {len(deduped_candidates)} candidate(s)")
        
        # Debug: Log candidate details
        for idx, cand in enumerate(deduped_candidates[:10], 1):
            logger.info(f"  Candidate {idx}: desc='{cand.get('description', 'N/A')}', amount={cand.get('amount', 'N/A')}, conf={cand.get('confidence', 'N/A')}")
        
        # Step 7: Extract reported total from document
        logger.info("Step 7: Extracting reported total...")
        reported_total = extract_reported_total(pages_images_bgr)
        
        # Fallback to text-based total extraction if needed
        if reported_total is None and pages_images_bgr:
            logger.info("    Using text-based fallback for reported total...")
            for img_bgr in pages_images_bgr:
                total = extract_reported_total_text_based(img_bgr)
                if total:
                    reported_total = total
                    break
        
        # Final fallback: use sum of candidates if no reported total found
        # This handles invoices without explicit totals
        if reported_total is None and deduped_candidates:
            candidates_sum = sum(c.get('amount', 0.0) or 0.0 for c in deduped_candidates)
            if candidates_sum > 0:
                reported_total = candidates_sum
                logger.info(f"No reported total found, using sum of candidates: {reported_total}")
        
        logger.info(f"Reported total: {reported_total}")
        
        # Step 8: Run ILP reconciliation
        logger.info("Step 8: Running ILP reconciliation...")
        duplicate_groups = make_duplicate_groups_from_candidates(deduped_candidates)
        logger.info(f"Duplicate groups: {len(duplicate_groups)}")
        
        # Calculate sum of all candidates
        candidates_sum = sum(c.get('amount', 0.0) or 0.0 for c in deduped_candidates)
        
        # Decide whether to use reported total based on confidence
        use_reported_total = None
        tolerance = 5.0
        
        if reported_total and candidates_sum > 0:
            deviation_ratio = abs(reported_total - candidates_sum) / reported_total
            
            if deviation_ratio <= 0.02:  # Within 2% - very close match
                use_reported_total = reported_total
                logger.info(f"Using reported total {reported_total} (close match: {deviation_ratio:.1%} deviation)")
            elif deviation_ratio > 0.5:  # Deviation > 50% - likely wrong total or partial extraction
                logger.info(f"Large deviation detected ({deviation_ratio:.1%}), ignoring reported total")
                use_reported_total = None
            else:  # Moderate deviation - use reported total with tolerance
                use_reported_total = reported_total
                tolerance = max(tolerance, abs(reported_total - candidates_sum))
                logger.info(f"Using reported total {reported_total} with increased tolerance {tolerance}")
        else:
            logger.info("No valid reported total found, selecting all valid candidates")
        
        reconcile_result = ilp_reconcile(
            deduped_candidates,
            reported_total=use_reported_total,
            duplicate_groups=duplicate_groups,
            tolerance=tolerance
        )
        
        logger.info(f"Reconciliation status: {reconcile_result['status']}")
        logger.info(f"Selected {len(reconcile_result['selected_ids'])} item(s)")
        logger.info(f"Total: {reconcile_result['selected_total']}, Deviation: {reconcile_result['deviation']}")
        
        # Step 9: Build response
        logger.info("Step 9: Building response...")
        response_data = build_response(
            deduped_candidates,
            reconcile_result,
            reported_total
        )
        
        logger.info("Extraction completed successfully")
        
        return ExtractionResponse(
            is_success=True,
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}", exc_info=True)
        
        return ExtractionResponse(
            is_success=False,
            error=str(e)
        )


def download_pdf(url: str, timeout: int = 30) -> bytes:
    """
    Download PDF from URL.
    
    Args:
        url: PDF document URL
        timeout: Request timeout in seconds
    
    Returns:
        PDF content as bytes
    
    Raises:
        HTTPException: If download fails
    """
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 Invoice Extractor'}
        )
        response.raise_for_status()
        
        # Verify content type
        content_type = response.headers.get('Content-Type', '').lower()
        if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
            logger.warning(f"Content-Type is '{content_type}', proceeding anyway")
        
        return response.content
        
    except requests.Timeout:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="PDF download timed out"
        )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to download PDF: {str(e)}"
        )


def extract_reported_total(pages_images: List[np.ndarray]) -> Optional[float]:
    """
    Extract reported total from invoice pages.
    
    Scans for common patterns like "Total:", "Grand Total:", etc.
    
    Args:
        pages_images: List of preprocessed page images
    
    Returns:
        Extracted total amount or None
    """
    if not pages_images:
        return None
    
    # Common patterns for total amount (more specific, exclude category totals)
    total_patterns = [
        r'(?:grand|final|invoice)\s+total\s*[:\-]?\s*(?:rs\.?|₹|\$)?\s*([0-9,]+\.?\d*)',
        r'total\s+(?:amount|due|payable)\s*[:\-]?\s*(?:rs\.?|₹|\$)?\s*([0-9,]+\.?\d*)',
        r'net\s+(?:total|amount)\s*[:\-]?\s*(?:rs\.?|₹|\$)?\s*([0-9,]+\.?\d*)',
        r'balance\s*due\s*[:\-]?\s*(?:rs\.?|₹|\$)?\s*([0-9,]+\.?\d*)',
        r'amount\s+payable\s*[:\-]?\s*(?:rs\.?|₹|\$)?\s*([0-9,]+\.?\d*)',
    ]
    
    # Check last page first (most likely location)
    for img_bgr in reversed(pages_images):
        try:
            # Extract text from bottom portion of page
            height = img_bgr.shape[0]
            bottom_portion = img_bgr[int(height * 0.6):, :]
            
            # OCR the region
            from PIL import Image
            import cv2
            img_rgb = cv2.cvtColor(bottom_portion, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            text = pytesseract.image_to_string(pil_img)
            
            # Search for total patterns
            for pattern in total_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Skip if this is a category/sub total
                    full_match = match.group(0).lower()
                    if 'category' in full_match or 'sub' in full_match:
                        continue
                    
                    amount_str = match.group(1)
                    amount_str = amount_str.replace(',', '')
                    
                    try:
                        amount = float(amount_str)
                        if amount > 0:
                            logger.info(f"Found reported total: {amount}")
                            return amount
                    except ValueError:
                        continue
        
        except Exception as e:
            logger.warning(f"Error extracting reported total: {str(e)}")
            continue
    
    return None


def build_response(
    candidates: List[Dict],
    reconcile_result: Dict,
    reported_total: Optional[float]
) -> Dict:
    """
    Build structured response JSON matching problem statement format.
    
    Args:
        candidates: All deduped candidates
        reconcile_result: ILP reconciliation result
        reported_total: Reported total from document
    
    Returns:
        Structured response dictionary in required format
    """
    # Get selected candidates
    selected_ids = set(reconcile_result['selected_ids'])
    selected_candidates = [c for c in candidates if c['id'] in selected_ids]
    
    # Group by page and format according to problem statement
    pagewise_items = {}
    for candidate in selected_candidates:
        page = str(candidate.get('page', 1))  # Convert to string as per format
        if page not in pagewise_items:
            pagewise_items[page] = []
        
        # Extract fields with proper defaults
        desc = candidate.get('description') or candidate.get('desc', '')
        amount = candidate.get('amount')
        qty = candidate.get('quantity')
        rate = candidate.get('rate')
        
        # Build item dict matching expected format
        item = {
            'item_name': desc.strip(),
            'item_amount': round(amount, 2) if amount is not None else None,
            'item_rate': round(rate, 2) if rate is not None else None,
            'item_quantity': qty if qty is not None else None
        }
        
        # Add optional fields if available
        if 'confidence' in candidate or 'conf' in candidate:
            item['confidence'] = round(candidate.get('confidence') or candidate.get('conf', 0), 2)
        
        pagewise_items[page].append(item)
    
    # Convert to list format for response
    pagewise_list = [
        {
            'page_no': page_no,
            'bill_items': items
        }
        for page_no, items in sorted(pagewise_items.items(), key=lambda x: int(x[0]))
    ]
    
    # Calculate metrics
    total_count = len(selected_candidates)
    reconciled_amount = round(reconcile_result['selected_total'], 2)
    
    # Build response matching problem statement format EXACTLY
    response = {
        'pagewise_line_items': pagewise_list,
        'total_item_count': total_count,
        'reconciled_amount': reconciled_amount
    }
    
    return response


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "is_success": False,
            "error": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "is_success": False,
            "error": "Internal server error occurred during extraction"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    logger.info("Starting Invoice Extraction API...")
    logger.info("Debug mode: " + os.environ.get('DEBUG', 'false'))
    logger.info("=== TEXT-BASED EXTRACTION MODE - NO MORPHOLOGICAL DETECTION ===")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
