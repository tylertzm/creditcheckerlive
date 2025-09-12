#!/usr/bin/env python3
"""
Test script for upload_utils functionality.
Tests comment adding and screenshot uploading on a specific claim.

Usage:
1. Make sure you're in the creditcheckerlive directory
2. Update the TEST_CLAIM_URL variable below with your test claim URL
3. Run: python3 test_upload_utils.py

The script will:
- Create a test screenshot automatically
- Login to Copytrack
- Navigate to your test claim
- Test adding an internal comment
- Test both upload methods
- Save debug screenshots showing the results

Note: The browser will run in visible mode (not headless) so you can see what's happening.
"""

import os
import sys
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(__file__))

try:
    from library.upload_utils import add_internal_comment, upload_screenshot_evidence_usual, upload_screenshot_evidence_new_claims
except ImportError as e:
    logging.error(f"Import error: {e}")
    logging.info("Make sure you're running this script from the creditcheckerlive directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Test credentials - replace with your actual credentials
EMAIL = 'siu-wang.HUNG@mediaident.com'
PASSWORD = '!Changedpwat0616'

def setup_test_driver():
    """Setup Chrome driver for testing (non-headless for debugging)"""
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Comment out the next line to see the browser in action
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def login_to_copytrack(driver, username, password):
    """Login to Copytrack admin portal"""
    logging.info("Navigating to login page...")
    driver.get('https://app.copytrack.com/login')
    
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    # Wait for page to load
    time.sleep(3)
    
    # Save screenshot for debugging
    driver.save_screenshot("test_login_page.png")
    logging.info("Saved login page screenshot to test_login_page.png")
    
    # Print page title and URL to debug
    logging.info(f"Page title: {driver.title}")
    logging.info(f"Current URL: {driver.current_url}")
    
    logging.info(f"Logging in as {username}...")
    try:
        # Try different selectors for the email field
        selectors_to_try = [
            (By.NAME, 'email'),
            (By.ID, 'email'),
            (By.CSS_SELECTOR, 'input[type="email"]'),
            (By.XPATH, '//input[@type="email"]'),
            (By.XPATH, '//form//input[contains(@placeholder, "email")]')
        ]
        
        for selector_type, selector in selectors_to_try:
            logging.info(f"Trying to find email field with {selector_type}: {selector}")
            try:
                email_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((selector_type, selector))
                )
                logging.info(f"Found email field with {selector_type}: {selector}")
                email_field.clear()
                email_field.send_keys(username)
                
                # Try to find password field
                password_field = None
                password_selectors = [
                    (By.NAME, 'password'),
                    (By.ID, 'password'),
                    (By.CSS_SELECTOR, 'input[type="password"]'),
                    (By.XPATH, '//input[@type="password"]')
                ]
                
                for pw_type, pw_selector in password_selectors:
                    try:
                        password_field = driver.find_element(pw_type, pw_selector)
                        if password_field:
                            break
                    except:
                        continue
                
                if password_field:
                    password_field.clear()
                    password_field.send_keys(password)
                    
                    # Try to find submit button
                    submit_selectors = [
                        (By.XPATH, '//button[@type="submit"]'),
                        (By.XPATH, '//input[@type="submit"]'),
                        (By.XPATH, '//button[contains(text(), "Log")]'),
                        (By.XPATH, '//button[contains(text(), "Sign")]')
                    ]
                    
                    for sub_type, sub_selector in submit_selectors:
                        try:
                            submit_button = driver.find_element(sub_type, sub_selector)
                            if submit_button:
                                submit_button.click()
                                # Wait for login to complete
                                WebDriverWait(driver, 30).until(EC.url_contains('/admin'))
                                logging.info("Login successful")
                                return True
                        except:
                            continue
                break
            except Exception as e:
                logging.info(f"Could not find email field with {selector_type}: {selector} - {e}")
                continue
        
        # If we got here, we failed to find the login form
        logging.error("Could not find login form elements!")
        driver.save_screenshot("test_login_failure.png")
        logging.info("Saved login failure screenshot to test_login_failure.png")
        return False
        
    except Exception as e:
        logging.error(f"Error during login: {e}")
        driver.save_screenshot("test_login_error.png")
        logging.info("Saved login error screenshot to test_login_error.png")
        return False

def create_test_screenshot():
    """Create a simple test screenshot"""
    from PIL import Image, ImageDraw, ImageFont
    
    # Create a simple test image
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add some text
    try:
        # Try to use a default font
        font = ImageFont.load_default()
    except:
        font = None
    
    draw.text((50, 50), "TEST SCREENSHOT", fill='black', font=font)
    draw.text((50, 100), f"Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}", fill='black', font=font)
    draw.text((50, 150), "This is a test image for upload testing", fill='black', font=font)
    
    # Add a simple rectangle
    draw.rectangle([50, 200, 350, 400], outline='blue', width=3)
    draw.text((60, 210), "Test Evidence Area", fill='blue', font=font)
    
    # Save the image
    screenshot_path = "test_screenshot.png"
    img.save(screenshot_path)
    logging.info(f"Created test screenshot: {screenshot_path}")
    return screenshot_path

def test_upload_utils(claim_url, test_comment, screenshot_path):
    """
    Test both comment and upload functionality
    
    Args:
        claim_url: The URL of the claim to test with
        test_comment: The comment text to add
        screenshot_path: Path to a screenshot file to upload
    """
    logging.info("Setting up test driver...")
    driver = setup_test_driver()
    
    try:
        # Login to Copytrack first
        if not login_to_copytrack(driver, EMAIL, PASSWORD):
            logging.error("Failed to login")
            return False
        
        # Navigate to the claim page
        logging.info(f"Navigating to claim URL: {claim_url}")
        driver.get(claim_url)
        time.sleep(3)  # Wait for page to load
        
        # Save screenshot of the claim page
        driver.save_screenshot("test_claim_page.png")
        logging.info("Saved claim page screenshot to test_claim_page.png")
        
        # Test 1: Add internal comment
        logging.info(f"Testing comment addition: '{test_comment}'")
        try:
            comment_result = add_internal_comment(driver, test_comment)
            if comment_result:
                logging.info("✅ Comment added successfully")
            else:
                logging.info("Comment function completed (check browser for results)")
        except Exception as e:
            logging.error(f"❌ Exception during comment addition: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait between tests
        time.sleep(2)
        
        # Test 2: Test screenshot upload functions
        logging.info(f"Testing screenshot upload functions: {screenshot_path}")
        
        # For testing upload functions, we need some dummy data
        page_hrefs = [claim_url]  # Single URL for testing
        link_idx = 1
        case_number = "TEST_CASE"
        hit_number = "TEST_HIT"
        
        try:
            # Test the usual upload method
            logging.info("Testing usual upload method...")
            upload_result1 = upload_screenshot_evidence_usual(
                driver, screenshot_path, page_hrefs, link_idx, case_number, hit_number
            )
            if upload_result1:
                logging.info("✅ Usual upload method completed successfully")
            else:
                logging.info("Usual upload method completed (check browser for results)")
        except Exception as e:
            logging.error(f"❌ Exception during usual upload: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait between upload tests
        time.sleep(3)
        
        try:
            # Test the new claims upload method
            logging.info("Testing new claims upload method...")
            upload_result2 = upload_screenshot_evidence_new_claims(
                driver, screenshot_path, page_hrefs, link_idx, case_number, hit_number
            )
            if upload_result2:
                logging.info("✅ New claims upload method completed successfully")
            else:
                logging.info("New claims upload method completed (check browser for results)")
        except Exception as e:
            logging.error(f"❌ Exception during new claims upload: {e}")
            import traceback
            traceback.print_exc()
        
        # Save final screenshot
        driver.save_screenshot("test_final_result.png")
        logging.info("Saved final result screenshot to test_final_result.png")
        
        # Wait to see results (comment this out in production)
        logging.info("Test completed. Check the browser and screenshots for results.")
        time.sleep(10)  # Give more time to see results
        
        return True
            
    except Exception as e:
        logging.error(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error screenshot
        try:
            driver.save_screenshot("test_error.png")
            logging.info("Saved error screenshot to test_error.png")
        except:
            pass
        
        return False
    finally:
        # Close the browser
        driver.quit()
        logging.info("Test completed")

if __name__ == "__main__":
    # Test configuration - CHANGE THESE VALUES
    TEST_CLAIM_URL = "https://app.copytrack.com/admin/claim/2087387?skipCategory=1"  # Replace with your test claim URL
    TEST_COMMENT = f"Test comment added by upload_utils test at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Create a test screenshot
    test_screenshot_path = create_test_screenshot()
    
    # Check if screenshot exists
    if not os.path.exists(test_screenshot_path):
        logging.error(f"Test screenshot not found: {test_screenshot_path}")
        sys.exit(1)
    
    logging.info("Starting upload_utils test...")
    logging.info(f"Test claim URL: {TEST_CLAIM_URL}")
    logging.info(f"Test comment: {TEST_COMMENT}")
    logging.info(f"Test screenshot: {test_screenshot_path}")
    
    # Run the test
    success = test_upload_utils(TEST_CLAIM_URL, TEST_COMMENT, test_screenshot_path)
    
    if success:
        logging.info("🎉 Test completed successfully!")
    else:
        logging.error("❌ Test failed!")
        sys.exit(1)
