"""
Rejection logic module for automatically rejecting cases with found credits.
Reads from daily CSV files and rejects cases where both image_found and keyword_found are True.
"""

import os
import csv
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Configuration
EMAIL = 'proof@copytrack.com'
PASSWORD = 'legal2024'

def login_to_copytrack(driver):
    """Login to Copytrack admin interface"""
    try:
        print("[INFO] 🔐 Logging in to Copytrack...")
        driver.get('https://app.copytrack.com/')
        
        # Wait for and fill email
        email_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "_email"))
        )
        email_field.click()
        email_field.send_keys(EMAIL)
        
        # Fill password
        password_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "_password"))
        )
        password_field.click()
        password_field.send_keys(PASSWORD)
        
        # Click login button
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))
        )
        submit_button.click()
        
        # Wait for successful login
        time.sleep(5)
        
        # Verify login succeeded
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/admin"]'))
            )
            print("[INFO] ✅ Login successful")
            return True
        except:
            print("[WARN] Login verification failed")
            return False
        
    except Exception as e:
        print(f"[ERROR] ❌ Login failed: {e}")
        return False


def reject_case_simple(driver, case_id, credit_name="unknown credit"):
    """
    Reject a Copytrack case with a credit note comment.
    
    Args:
        driver: Selenium WebDriver instance
        case_id: The case ID to reject
        credit_name: Name of the credit found (from keywords_list)
        
    Returns:
        bool: True if rejection succeeded, False otherwise
    """
    # Create comment text with credit name
    comment_text = f"Credit Note: As {credit_name} is credited, for now we close this claim. If you are sure that the opponent does not have a license, please let us know - we're happy to re-open the claim! Thank you in advance."
    try:
        print(f"[INFO] 🔴 Rejecting case {case_id}...")
        
        # Navigate to the case
        case_url = f"https://app.copytrack.com/admin/claim/{case_id}"
        driver.get(case_url)
        
        # Wait for page to load
        time.sleep(3)
        
        # 1. Add internal comment
        print("[INFO] Adding internal comment...")
        try:
            # Click "Add new comment" tab
            add_comment_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="#comment-new"]'))
            )
            driver.execute_script("arguments[0].click();", add_comment_tab)
            
            # Uncheck "Visible for customer" checkbox
            visible_checkbox = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "claim-comment-visible"))
            )
            if visible_checkbox.is_selected():
                driver.execute_script("arguments[0].click();", visible_checkbox)
            
            # Fill comment text
            comment_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "claim-comment-comment"))
            )
            comment_field.clear()
            comment_field.send_keys(comment_text)
            
            # Click "Comment" button
            comment_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-action="claim-comment"]'))
            )
            driver.execute_script("arguments[0].click();", comment_button)
            
            time.sleep(2)
            print("[INFO] ✅ Internal comment added")
            
        except Exception as e:
            print(f"[WARN] Failed to add comment: {e}")
            # Continue with rejection even if comment fails
        
        # 2. Change state to reject
        print("[INFO] Changing state to reject...")
        
        # Select "reject" from dropdown (find option containing "reject")
        state_dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "change-state-select"))
        )
        select = Select(state_dropdown)
        
        # Find and select option containing "reject" (case-insensitive)
        reject_option_found = False
        for option in select.options:
            option_value = option.get_attribute("value").lower()
            option_text = option.text.lower()
            if "reject" in option_value or "reject" in option_text:
                select.select_by_value(option.get_attribute("value"))
                print(f"[INFO] ✅ Selected rejection state: '{option.text}'")
                reject_option_found = True
                break
        
        if not reject_option_found:
            print("[WARN] ⚠️  'reject' option not available for this case - skipping")
            return False
        
        print("[INFO] ✅ Rejection state selected")
        
        # Fill state comment field
        time.sleep(1)
        state_comment = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='state-comment']"))
        )
        state_comment.clear()
        state_comment.send_keys("Rejected - credits found")
        print("[INFO] ✅ State comment added")
        
        # Wait for Change button to become enabled
        time.sleep(3)
        
        # 3. Click "Change" button
        print("[INFO] Clicking 'Change' button...")
        change_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "claim-change-state"))
        )
        change_button.click()
        
        # 4. Handle confirmation modal
        print("[INFO] Waiting for confirmation modal...")
        time.sleep(2)
        
        # Wait for confirm button and click it
        confirm_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.confirm"))
        )
        
        print("[INFO] Clicking confirm button...")
        confirm_button.click()
        
        # Wait for modal to close and action to complete
        time.sleep(3)
        
        print(f"[INFO] ✅ Case {case_id} rejected successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] ❌ Failed to reject case {case_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_cases_to_reject_from_csv(csv_file):
    """
    Extract case IDs and their credit info from CSV where both image_found=True and keyword_found=True.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        dict: Dictionary mapping case_id to credit name (keywords_list)
    """
    cases_to_reject = {}
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                case_id = row.get('case_id', '').strip('"')
                image_found = row.get('image_found', '').strip('"')
                keyword_found = row.get('keyword_found', '').strip('"')
                keywords_list = row.get('keywords_list', '').strip('"')
                
                # Check if both are True
                if image_found == 'True' and keyword_found == 'True':
                    # Use first keyword as credit name
                    credit_name = keywords_list.split(',')[0].strip() if keywords_list else "unknown credit"
                    cases_to_reject[case_id] = credit_name
        
        print(f"[INFO] 📋 Found {len(cases_to_reject)} cases to reject in {csv_file}")
        return cases_to_reject
        
    except Exception as e:
        print(f"[ERROR] ❌ Error reading {csv_file}: {e}")
        return {}


def get_daily_csv_files(start_date=None, end_date=None, directory='.'):
    """
    Get list of daily CSV files to process.
    
    Args:
        start_date: Start date (datetime object), optional
        end_date: End date (datetime object), optional
        directory: Directory to search for CSV files
        
    Returns:
        list: List of CSV file paths
    """
    csv_files = []
    
    # If no dates specified, process all available daily CSV files
    if not start_date and not end_date:
        for filename in os.listdir(directory):
            if filename.startswith('daily_claims_') and filename.endswith('.csv'):
                if 'backup' not in filename:
                    csv_files.append(os.path.join(directory, filename))
    else:
        # Process specific date range
        from datetime import timedelta
        current_date = start_date
        while current_date <= end_date:
            filename = f"daily_claims_{current_date.strftime('%Y-%m-%d')}.csv"
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                csv_files.append(filepath)
            current_date += timedelta(days=1)
    
    return sorted(csv_files)
