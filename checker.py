"""
Main credit checker module - imports all functionality from library modules
"""

import time
import re
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
from io import BytesIO
from scipy.spatial.distance import hamming
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# OCR imports
try:
    import pytesseract
    OCR_AVAILABLE = True
    print("✓ OCR (Tesseract) available for image text detection")
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ OCR not available - install pytesseract and tesseract-ocr for image text detection")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
    print("✓ EasyOCR available for enhanced image text detection")
except ImportError:
    EASYOCR_AVAILABLE = False
    print("⚠️ EasyOCR not available - install easyocr for enhanced image text detection")

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

# Overall results CSV file
# OVERALL_CSV constant removed - CSV writing handled by scraping.py

# Import all functionality from library modules
from library import (
    # Keywords
    CREDIT_KEYWORDS,
    # OCR functions
    check_image_ocr_for_credits, _ocr_scroll_impressum_page,
    # Image utilities
    find_image_by_url, dhash, ahash, hamming_distance, download_image_as_pil,
    calculate_image_similarity_batch, calculate_image_similarity,
    find_image_by_similarity, scroll_and_search_image,
    # Web utilities
    handle_initial_page_setup, setup_driver, create_highlighted_credit_link,
    take_full_screenshot_with_timestamp, wait_for_images_to_load,
    check_for_404_or_page_errors,
    # Credit checking
    matches_keyword_with_word_boundary, check_credit_keywords_in_parents,
    check_caption_elements_for_credits, check_impressum_for_credits,
    # Upload utilities
    add_internal_comment, upload_screenshot_evidence_new_claims
)


def save_case_to_daily_csv(case_id, case_url, hit_number, page_url, image_url, results):
    """Save case information to daily CSV file with file locking"""
    import fcntl
    import tempfile
    import shutil
    from datetime import datetime
    
    # Create daily CSV filename with date
    today = datetime.now().strftime('%Y-%m-%d')
    daily_csv = f"daily_claims_{today}.csv"
    
    # Create the daily CSV file if it doesn't exist
    if not os.path.exists(daily_csv):
        print(f"📅 Creating new daily CSV file: {daily_csv}")
        with open(daily_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'case_id', 'case_url', 'hit_number', 'page_url', 'image_url',
                'image_found', 'keyword_found', 'keywords_list', 'credit_texts', 'keyword_highlight', 
                'error_status', 'screenshot_path', 'processed_at'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
    
    try:
        # Create a lock file path
        lock_file = f"{daily_csv}.lock"
        
        # Use file locking to prevent concurrent writes
        with open(lock_file, 'w') as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
            
            try:
                # Check if file exists to determine if we need headers
                file_exists = os.path.exists(daily_csv)
                
                # Read existing data
                existing_data = []
                if file_exists:
                    with open(daily_csv, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        existing_data = list(reader)
                
                # Prepare new row data
                fieldnames = [
                    'case_id', 'case_url', 'hit_number', 'page_url', 'image_url',
                    'image_found', 'keyword_found', 'keywords_list', 'credit_texts', 'keyword_highlight', 
                    'error_status', 'screenshot_path', 'processed_at'
                ]
                
                # Ensure all values are properly handled
                credit_keywords = results.get('credit_keywords', []) or []
                credit_texts = results.get('credit_texts', []) or []
                error_msg = results.get('error', '') or ''
                
                # Truncate error message to prevent CSV row overflow
                if error_msg and len(str(error_msg)) > 200:
                    error_msg = str(error_msg)[:200] + "..."
                
                row_data = {
                    'case_id': str(case_id) if case_id else '',
                    'case_url': str(case_url) if case_url else '',
                    'hit_number': str(hit_number) if hit_number else '',
                    'page_url': str(page_url) if page_url else '',
                    'image_url': str(image_url) if image_url else '',
                    'image_found': bool(results.get('image_found', False)),
                    'keyword_found': bool(credit_keywords),
                    'keywords_list': ', '.join(str(k) for k in credit_keywords) if credit_keywords else '',
                    'credit_texts': ', '.join(str(t) for t in credit_texts) if credit_texts else '',
                    'keyword_highlight': str(results.get('highlight_url', '')) if results.get('highlight_url') else '',
                    'error_status': 'Success' if not error_msg else str(error_msg),
                    'screenshot_path': str(results.get('screenshot_path', '')) if results.get('screenshot_path') else '',
                    'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Add new row to existing data
                existing_data.append(row_data)
                
                # Write to temporary file first (atomic operation)
                temp_file = f"{daily_csv}.tmp"
                with open(temp_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(existing_data)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                
                # Atomically replace the original file
                shutil.move(temp_file, daily_csv)
                
                print(f"📅 Case {case_id} hit {hit_number} saved to {daily_csv}")
                
            finally:
                # Lock is automatically released when the file is closed
                pass
                
    except Exception as e:
        print(f"❌ Error saving case to daily CSV: {e}")
        # Clean up temp file if it exists
        temp_file = f"{daily_csv}.tmp"
        if os.path.exists(temp_file):
            os.remove(temp_file)


# Removed save_case_to_overall_csv function to prevent duplicate CSV entries
# CSV writing is now handled by scraping.py to avoid double-writes


def check_image_credits(target_image_url, page_url, output_path=None, similarity_threshold=0.85, max_workers=10, case_url=None, hit_id=None):
    """
    Check for credit keywords in images on a webpage and generate highlighted screenshots.

    Args:
        target_image_url (str): URL of the target image to search for
        page_url (str): URL of the webpage to search on
        output_path (str, optional): Path for the screenshot output
        similarity_threshold (float): Threshold for image similarity matching (0.0-1.0, default 0.85)
        max_workers (int): Number of parallel workers for image similarity checking (default 10)
        case_url (str, optional): Case URL to include in screenshot filename
        hit_id (str, optional): Hit ID to include in screenshot filename

    Returns:
        dict: Results containing:
            - 'image_found': bool
            - 'credit_keywords': list of found keywords
            - 'credit_texts': list of text contexts where keywords were found
            - 'screenshot_path': str path to generated screenshot
            - 'highlight_url': str URL with text highlighting
            - 'error': str error message if any
    """
    driver = None
    results = {
        'image_found': False,
        'credit_keywords': [],
        'credit_texts': [],
        'screenshot_path': None,
        'highlight_url': '',
        'error': None
    }
    
    try:
        print(f"🔍 Starting credit check for image: {target_image_url}")
        print(f"🌐 Page URL: {page_url}")
        # Setup Chrome driver
        print("🚀 Setting up Chrome driver...")
        driver = setup_driver()
        
        # Navigate to the page
        print(f"🌐 Navigating to page: {page_url}")
        driver.get(page_url)
        handle_initial_page_setup(driver)
        
        # Check for page errors
        error_msg = check_for_404_or_page_errors(driver)
        if error_msg:
            results['error'] = f"Page error: {error_msg}"
            print(f"❌ {error_msg}")
            return results
        
        # Wait for images to load
        wait_for_images_to_load(driver)
        
        # Find the target image on the page
        print("🔍 Searching for target image on page...")
        
        # First try: Find by exact URL match
        image_element = find_image_by_url(driver, target_image_url)
        if image_element:
            print("✅ Found image by URL match")
            results['image_found'] = True
        else:
            print("⚠️ Image not found by URL, trying visual similarity search...")
            # Second try: Find by visual similarity
            image_element = scroll_and_search_image(
                driver, target_image_url, 
                max_scrolls=10, 
                similarity_threshold=similarity_threshold, 
                max_workers=max_workers
            )
            if image_element:
                print("✅ Found image by visual similarity")
                results['image_found'] = True
            else:
                print("❌ Image not found on page")
                results['error'] = "Target image not found on page"
                return results
        
        # Scroll image into view and take screenshot
        if image_element:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", image_element)
            time.sleep(0.5)
            
            # Take screenshot with highlighting
            screenshot_path = take_full_screenshot_with_timestamp(
                driver, 
                image_element, 
                output_path, 
                case_url, 
                hit_id
            )
            results['screenshot_path'] = screenshot_path
        
        # Comprehensive credit checking
        print("🔍 Starting comprehensive credit analysis...")
        all_keywords = []
        all_texts = []
        
        # 1. Check parent elements and scrolled text around image
        if image_element:
            print("📍 Checking parent elements and nearby text...")
            parent_keywords, parent_texts = check_credit_keywords_in_parents(driver, image_element)
            all_keywords.extend(parent_keywords)
            all_texts.extend(parent_texts)
        
        # 2. Check caption elements
        print("📍 Checking caption elements...")
        caption_keywords, caption_texts = check_caption_elements_for_credits(driver, image_element)
        all_keywords.extend(caption_keywords)
        all_texts.extend(caption_texts)
        
        # 4. Check image OCR (if image found)
        if image_element:
            print("📍 Checking image OCR...")
            try:
                image_src = image_element.get_attribute("src")
                if image_src:
                    ocr_keywords, ocr_text = check_image_ocr_for_credits(image_src)
                    all_keywords.extend(ocr_keywords)
                    if ocr_text:
                        all_texts.append(f"OCR extracted text: {ocr_text[:200]}...")
            except Exception as e:
                print(f"⚠️ OCR analysis failed: {e}")
        
        # 5. Check impressum/legal page as fallback
        if not all_keywords:
            print("📍 No credits found on main page, checking impressum/legal page...")
            impressum_keywords, impressum_texts = check_impressum_for_credits(driver, page_url, case_url, hit_id)
            all_keywords.extend(impressum_keywords)
            all_texts.extend(impressum_texts)
        
        # Store results
        results['credit_keywords'] = all_keywords
        results['credit_texts'] = all_texts
        
        # Create highlight URL
        if all_keywords:
            results['highlight_url'] = create_highlighted_credit_link(all_keywords, True, page_url)
        
        # Print summary
        if all_keywords:
            print(f"🎯 Found {len(all_keywords)} credit keywords:")
            for keyword in all_keywords:
                print(f"   • {keyword}")
        else:
            print("❌ No credit keywords found")
        
        # Note: Comment and upload handling is done by the calling script
        # since we need to be on the Copytrack case page for those operations
        
        print("✅ Credit check completed successfully")
        
    except Exception as e:
        error_msg = f"Credit check failed: {str(e)}"
        print(f"❌ {error_msg}")
        results['error'] = error_msg
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            try:
                driver.quit()
                print("🔒 Chrome driver closed")
            except Exception as e:
                print(f"⚠️ Error closing driver: {e}")
        
        # Note: CSV writing is handled by the calling function (scraping.py)
        # to avoid duplicate entries
    
    return results


def main():
    """Main function for testing the credit checker"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python checker.py <image_url> <page_url> [output_path]")
        print("Example: python checker.py 'https://example.com/image.jpg' 'https://example.com/page'")
        sys.exit(1)
    
    target_image_url = sys.argv[1]
    page_url = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    print("🔍 Credit Checker - Testing Mode")
    print("=" * 50)
    
    results = check_image_credits(
        target_image_url=target_image_url,
        page_url=page_url,
        output_path=output_path,
        similarity_threshold=0.85,
        max_workers=10
    )
    
    print("\n📊 Results Summary:")
    print("=" * 50)
    print(f"Image Found: {results['image_found']}")
    print(f"Credit Keywords: {len(results['credit_keywords'])}")
    print(f"Screenshot: {results['screenshot_path']}")
    print(f"Highlight URL: {results['highlight_url']}")
    if results['error']:
        print(f"Error: {results['error']}")
    
    if results['credit_keywords']:
        print("\n🎯 Found Keywords:")
        for keyword in results['credit_keywords']:
            print(f"  • {keyword}")
    
    return results


if __name__ == "__main__":
    main()
