"""
API testing script.

Simple script to test the invoice extraction API with a sample URL.
"""

import requests
import json
import sys
from typing import Optional


def test_health_check(base_url: str = "http://localhost:8000") -> bool:
    """Test the health check endpoint."""
    print("Testing health check endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        response.raise_for_status()
        print(f"✓ Health check passed: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_extraction(
    document_url: str,
    base_url: str = "http://localhost:8000"
) -> Optional[dict]:
    """Test the extraction endpoint."""
    print(f"\nTesting extraction with URL: {document_url}")
    print("-" * 70)
    
    try:
        payload = {"document": document_url}
        
        print("Sending request...")
        response = requests.post(
            f"{base_url}/extract-bill-data",
            json=payload,
            timeout=120  # Allow up to 2 minutes for processing
        )
        
        print(f"Status code: {response.status_code}")
        
        result = response.json()
        
        if response.status_code == 200:
            print("\n✓ Extraction successful!")
            print("\nResponse summary:")
            
            if result.get('is_success'):
                data = result.get('data', {})
                print(f"  - Total items: {data.get('total_item_count', 0)}")
                print(f"  - Reconciled amount: ${data.get('reconciled_amount', 0):.2f}")
                print(f"  - Reported total: ${data.get('reported_total', 0):.2f}")
                print(f"  - Deviation: ${data.get('deviation', 0):.2f}")
                print(f"  - Avg confidence: {data.get('average_confidence', 0):.1f}%")
                print(f"  - Manual review: {data.get('requires_manual_review', False)}")
                
                if data.get('warnings'):
                    print(f"\n  Warnings:")
                    for warning in data['warnings']:
                        print(f"    - {warning}")
                
                print(f"\n  Line items by page:")
                pagewise = data.get('pagewise_line_items', {})
                for page, items in pagewise.items():
                    print(f"\n    Page {page}: {len(items)} items")
                    for item in items[:3]:  # Show first 3 items
                        desc = item.get('description', 'N/A')[:50]
                        amt = item.get('amount', 0)
                        conf = item.get('confidence', 0)
                        print(f"      - {desc:50s} ${amt:>8.2f} ({conf:.1f}%)")
                    if len(items) > 3:
                        print(f"      ... and {len(items) - 3} more items")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
            
            return result
        else:
            print(f"\n✗ Extraction failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return result
            
    except requests.Timeout:
        print("✗ Request timed out (took longer than 2 minutes)")
        return None
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return None


def save_result(result: dict, filename: str = "extraction_result.json"):
    """Save the extraction result to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Result saved to: {filename}")
    except Exception as e:
        print(f"\n✗ Failed to save result: {e}")


def main():
    """Main test function."""
    print("=" * 70)
    print("INVOICE EXTRACTION API - Test Script")
    print("=" * 70)
    print()
    
    base_url = "http://localhost:8000"
    
    # Test 1: Health check
    if not test_health_check(base_url):
        print("\n⚠ Server might not be running!")
        print("Start the server with: python app.py")
        return 1
    
    # Test 2: Extraction
    print("\n" + "=" * 70)
    
    # Use a sample invoice URL (you can replace with your own)
    sample_url = input("\nEnter invoice PDF URL (or press Enter for demo): ").strip()
    
    if not sample_url:
        # Demo URL - public invoice template
        sample_url = "https://templates.invoicehome.com/invoice-template-us-neat-750px.png"
        print(f"Using demo URL: {sample_url}")
    
    result = test_extraction(sample_url, base_url)
    
    if result:
        save_result(result, "test_extraction_result.json")
        print("\n" + "=" * 70)
        print("✓ Test complete!")
        print("\nFull response saved to: test_extraction_result.json")
        print()
        return 0
    else:
        print("\n" + "=" * 70)
        print("✗ Test failed!")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
