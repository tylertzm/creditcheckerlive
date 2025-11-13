"""
OCR (Optical Character Recognition) utilities for image text extraction
"""

import time
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from .keywords import CREDIT_KEYWORDS
from .credit_checker import matches_keyword_with_word_boundary, find_credit_keywords_in_text

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


def check_image_ocr_for_credits(image_url, max_attempts=2):
    """
    Use OCR to extract text from an image and check for credit keywords.
    
    Args:
        image_url (str): URL of the image to analyze
        max_attempts (int): Maximum attempts to download and process the image
    
    Returns:
        tuple: (found_keywords, extracted_text)
    """
    if not (OCR_AVAILABLE or EASYOCR_AVAILABLE):
        print("⚠️ OCR not available - skipping image text analysis")
        return [], ""
    
    found_keywords = []
    extracted_text = ""
    
    for attempt in range(max_attempts):
        try:
            print(f"📷 Downloading image for OCR analysis (attempt {attempt + 1}/{max_attempts})...")
            
            # Download the image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Convert to PIL Image
            image = Image.open(BytesIO(response.content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            print(f"🔍 Analyzing image text with OCR...")
            
            # Try EasyOCR first (generally more accurate)
            if EASYOCR_AVAILABLE:
                try:
                    # Initialize EasyOCR reader (English)
                    reader = easyocr.Reader(['en'])
                    
                    # Convert PIL image to numpy array for EasyOCR
                    img_array = np.array(image)
                    
                    # Extract text
                    results = reader.readtext(img_array)
                    text_parts = [result[1] for result in results if result[2] > 0.3]  # confidence > 0.3
                    extracted_text = ' '.join(text_parts)
                    
                    print(f"✓ EasyOCR extracted text: {extracted_text[:100]}..." if len(extracted_text) > 100 else f"✓ EasyOCR extracted text: {extracted_text}")
                    
                except Exception as e:
                    print(f"⚠️ EasyOCR failed: {e}")
                    extracted_text = ""
            
            # Fallback to Tesseract if EasyOCR failed or isn't available
            if not extracted_text and OCR_AVAILABLE:
                try:
                    # Use Tesseract OCR
                    extracted_text = pytesseract.image_to_string(image)
                    print(f"✓ Tesseract extracted text: {extracted_text[:100]}..." if len(extracted_text) > 100 else f"✓ Tesseract extracted text: {extracted_text}")
                    
                except Exception as e:
                    print(f"⚠️ Tesseract OCR failed: {e}")
                    extracted_text = ""
            
            # Check for credit keywords in extracted text (optimized)
            if extracted_text:
                found_in_ocr = find_credit_keywords_in_text(extracted_text)
                for keyword in found_in_ocr:
                    found_keywords.append(f"OCR: {keyword}")
                    print(f"🎯 Found credit keyword in image text: {keyword}")
            
            # Success - break out of retry loop
            break
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Failed to download image (attempt {attempt + 1}): {e}")
            if attempt == max_attempts - 1:
                print("❌ Could not download image for OCR analysis")
        except Exception as e:
            print(f"⚠️ OCR analysis error (attempt {attempt + 1}): {e}")
            if attempt == max_attempts - 1:
                print("❌ OCR analysis failed")
    
    return found_keywords, extracted_text


def _ocr_scroll_impressum_page(driver, impressum_type, max_scrolls=10, case_url=None, hit_id=None):
    """
    Scroll through impressum page and use OCR to extract text from screenshots.
    This is used as a fallback when HTML text extraction doesn't find credits.
    Screenshots are automatically deleted after OCR processing.
    """
    from .web_utils import take_full_screenshot_with_timestamp
    
    found_keywords = []
    extracted_texts = []
    screenshot_paths = []  # Track all screenshot paths for cleanup
    
    try:
        print(f"🔍 Using OCR to scan {impressum_type} page for credits...")
        
        # Take initial screenshot
        screenshot_path = take_full_screenshot_with_timestamp(
            driver, 
            output_path=f"output/impressum_ocr_{impressum_type}_{hit_id or 'unknown'}.png",
            case_url=case_url,
            hit_id=hit_id
        )
        
        if screenshot_path and os.path.exists(screenshot_path):
            screenshot_paths.append(screenshot_path)
            # Process the screenshot with OCR
            keywords, text = check_image_ocr_for_credits(f"file://{os.path.abspath(screenshot_path)}")
            if keywords:
                found_keywords.extend(keywords)
                extracted_texts.append(text)
        
        # Scroll and take additional screenshots
        for scroll_num in range(max_scrolls):
            try:
                # Scroll down
                driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
                time.sleep(1)  # Allow content to load
                
                # Take screenshot
                screenshot_path = take_full_screenshot_with_timestamp(
                    driver,
                    output_path=f"output/impressum_ocr_{impressum_type}_{hit_id or 'unknown'}_scroll_{scroll_num + 1}.png",
                    case_url=case_url,
                    hit_id=hit_id
                )
                
                if screenshot_path and os.path.exists(screenshot_path):
                    screenshot_paths.append(screenshot_path)
                    # Process the screenshot with OCR
                    keywords, text = check_image_ocr_for_credits(f"file://{os.path.abspath(screenshot_path)}")
                    if keywords:
                        found_keywords.extend(keywords)
                        extracted_texts.append(text)
                
            except Exception as e:
                print(f"⚠️ Error during OCR scroll {scroll_num + 1}: {e}")
                continue
        
        if found_keywords:
            print(f"🎯 OCR found {len(found_keywords)} credit keywords in {impressum_type} page")
        else:
            print(f"❌ No credit keywords found via OCR in {impressum_type} page")
            
    except Exception as e:
        print(f"⚠️ OCR impressum scanning failed: {e}")
    
    finally:
        # Clean up OCR screenshots after processing
        deleted_count = 0
        for screenshot_path in screenshot_paths:
            try:
                if os.path.exists(screenshot_path):
                    os.remove(screenshot_path)
                    deleted_count += 1
            except Exception as e:
                print(f"⚠️ Could not delete OCR screenshot {screenshot_path}: {e}")
        
        if deleted_count > 0:
            print(f"🗑️ Cleaned up {deleted_count} OCR screenshots")
    
    return found_keywords, extracted_texts
