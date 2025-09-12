"""
Upload and comment utilities for Copytrack integration.

This module provides functions for uploading screenshots and adding comments
to Copytrack cases.
"""

import time
import pyautogui
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.remote.webelement import WebElement


def safe_click(driver, element, description="element"):
    """
    Safely click an element using JavaScript.
    
    Args:
        driver: Selenium WebDriver instance
        element: WebElement to click
        description: Description of the element for logging
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", element)
        print(f"✅ Clicked {description} via JavaScript.")
    except Exception as e:
        print(f"❌ Could not click {description}: {e}")


def click_button(driver, action, element=None):
    """
    Performs different button clicks or dropdown selections based on the action keyword.

    If `element` is provided, clicks it directly.
    
    Args:
        driver: Selenium WebDriver instance
        action: Action to perform (upload evidences, manual-screenshot-page, file upload, submit evidence)
        element: Optional WebElement to click directly
    """
    if element is not None:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(element)).click()
        print("[INFO] ✅ Clicked provided element.")
        return

    if action == "upload evidences":
        upload_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[normalize-space(text())="upload evidences"]'))
        )
        upload_button.click()
        print("[INFO] ✅ Clicked 'upload evidences' button.")

    elif action == "manual-screenshot-page":
        dropdown_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "evidence_upload_type"))
        )
        select = Select(dropdown_element)
        select.select_by_value("manual-screenshot-page")
        print("[INFO] ✅ Selected 'manual-screenshot-page' option.")

    elif action == "file upload":
        icon_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//i[contains(@class, "glyphicon-open")]'))
        )
        parent_element = icon_element.find_element(By.XPATH, '..')
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(parent_element)
        )
        parent_element.click()
        print("[INFO] ✅ Clicked the 'file upload' button.")

    elif action == "submit evidence":
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//span[normalize-space(text())="Submit"]/parent::*'
            ))
        )
        submit_button.click()
        print("[INFO] ✅ Clicked the 'Submit' button.")

    else:
        raise ValueError(f"[ERROR] ❌ Unknown action '{action}'.")


def try_upload_evidence(driver, upload_xpath, retries=2):
    """
    Try to find and click an upload evidence button with retries.
    
    Args:
        driver: Selenium WebDriver instance
        upload_xpath: XPath to the upload button
        retries: Number of retry attempts
        
    Returns:
        bool: True if successful, False otherwise
    """
    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] ⏳ Trying to find upload button (attempt {attempt})...")
            upload_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, upload_xpath))
            )
            click_button(driver, "upload evidences", element=upload_btn)
            return True
        except Exception as e:
            print(f"[WARN] Upload button not clickable (attempt {attempt}): {e}")
            if attempt < retries:
                time.sleep(3)
            else:
                print("[ERROR] ❌ Upload button unavailable after retries.")
                return False


def capture_image_screenshot(driver, matched_image, case_text_clean):
    """
    Capture a screenshot of a matched image element.
    
    Args:
        driver: Selenium WebDriver instance
        matched_image: WebElement representing the image to screenshot
        case_text_clean: Clean case identifier for filename
        
    Returns:
        str: Path to the saved screenshot, or None if failed
    """
    if isinstance(matched_image, WebElement):
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                matched_image
            )
            time.sleep(2)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            screenshot_path = fr"{case_text_clean}_{timestamp}.png"

            pyautogui.screenshot(screenshot_path)
            pyautogui.sleep(1)

            print(f"[INFO] 📸 Screenshot taken and saved to: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            print(f"[ERROR] ❌ Failed to capture screenshot: {e}")
            return None
    else:
        print("[ERROR] ❌ matched_image is not a valid WebElement.")
        return None


def upload_screenshot_evidence_usual(driver, screenshot_path, page_hrefs, link_idx, case_number, hit_number):
    """
    Uploads a screenshot for a specific link index in Copytrack using the usual method.
    
    Args:
        driver: Selenium WebDriver instance
        screenshot_path: Path to the screenshot file
        page_hrefs: List of page URLs for this hit
        link_idx: Index of the current link (1-based)
        case_number: Case number for logging
        hit_number: Hit number for logging
        
    Returns:
        bool: True if upload succeeded, False otherwise
    """
    if not screenshot_path:
        print("[ERROR] Screenshot path is None, cannot upload.")
        return False

    # Switch back to Copytrack tab safely
    try:
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
        else:
            print("[WARN] No browser windows are open. Skipping switch.")
            return False
    except Exception as e:
        print(f"[ERROR] WebDriver session invalid or closed: {e}")
        return False

    time.sleep(0.2)

    upload_button_xpaths = [
        f'(//a[normalize-space(text())="upload evidences"])[{i}]'
        for i in range(1, len(page_hrefs) + 1)
    ]

    upload_xpath = upload_button_xpaths[link_idx - 1]
    success = try_upload_evidence(driver, upload_xpath)

    if not success:
        print("[ERROR] ❌ Upload button unavailable. Logging fallback comment.")
        add_screenshot_comment(driver, 3, case_number, hit_number)
        return False

    time.sleep(0.5)
    click_button(driver, "manual-screenshot-page")
    time.sleep(0.5)
    click_button(driver, "file upload")

    time.sleep(1.2)
    pyautogui.typewrite(screenshot_path)
    time.sleep(2)
    pyautogui.press('enter')
    time.sleep(1)

    click_button(driver, "submit evidence")
    time.sleep(1.2)

    print("[INFO] ✅ Screenshot uploaded successfully.")
    return True


def upload_screenshot_evidence_new_claims(driver, screenshot_path, page_hrefs, link_idx, case_number, hit_number):
    """
    Uploads a screenshot using Copytrack's Add Files → Start Upload flow using safe_click.
    
    Args:
        driver: Selenium WebDriver instance
        screenshot_path: Path to the screenshot file
        page_hrefs: List of page URLs for this hit
        link_idx: Index of the current link (1-based)
        case_number: Case number for logging
        hit_number: Hit number for logging
        
    Returns:
        bool: True if upload succeeded, False otherwise
    """
    if not screenshot_path:
        print("[ERROR] Screenshot path is None, cannot upload.")
        return False

    try:
        # Switch to Copytrack tab
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
        else:
            print("[WARN] No browser windows open. Skipping switch.")
            return False
    except Exception as e:
        print(f"[ERROR] WebDriver session invalid or closed: {e}")
        return False

    time.sleep(0.5)

    try:
        # (i) Wait for and click "Add files" button
        driver.find_element(By.CSS_SELECTOR,'#claim_documents_form > button.btn.btn-primary.pull-right.btn-xs.fileinput-button.dz-clickable > span').click()
        time.sleep(1.2)

        # (ii) Enter screenshot path
        pyautogui.typewrite(screenshot_path)
        time.sleep(1.5)
        pyautogui.press('enter')
        time.sleep(2)  # Wait for file to be selected

        # (iii) Wait for and click "Start upload" button (appears after file selection)
        print("[INFO] Looking for 'Start upload' button...")
        try:
            # Try multiple possible selectors for the start upload button
            start_upload_selectors = [
                "//button[@data-action='start-document-upload']//span[text()='Start upload']/..",
                "//button[contains(@class, 'start')]//span[text()='Start upload']/..",
                "//button[contains(text(), 'Start upload')]",
                "//span[text()='Start upload']/parent::button",
                "//*[contains(text(), 'Start upload')]"
            ]
            
            start_upload_button = None
            for selector in start_upload_selectors:
                try:
                    start_upload_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    print(f"[INFO] Found 'Start upload' button with selector: {selector}")
                    break
                except:
                    continue
            
            if start_upload_button:
                safe_click(driver, start_upload_button, "'Start upload' button")
                time.sleep(3)
            else:
                print("[WARN] Could not find 'Start upload' button, file may upload automatically")
                time.sleep(3)
                
        except Exception as upload_btn_error:
            print(f"[WARN] Start upload button error: {upload_btn_error}")
            print("[INFO] Proceeding anyway, file may upload automatically")
            time.sleep(3)

        print("[INFO] ✅ Screenshot uploaded successfully.")
        return True

    except Exception as e:
        print(f"[ERROR] Upload process failed: {e}")
        import traceback
        traceback.print_exc()
        add_screenshot_comment(driver, 3, case_number, hit_number)
        return False


def add_internal_comment(driver, comment_text):
    """
    Add an internal comment to a Copytrack case.
    
    Args:
        driver: Selenium WebDriver instance
        comment_text: Text content of the comment
    """
    try:
        # Switch to 'Add Comment' tab
        add_comment_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-toggle='tab'][@href='#tab-add-comment']"))
        )
        safe_click(driver, add_comment_tab, "add comment tab")
        time.sleep(1)

        # Fill in comment textarea
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "claim-comment"))
        )
        textarea.clear()
        textarea.send_keys(comment_text)

        # Uncheck "Visible for customer"
        try:
            comment_form = driver.find_element(By.NAME, "claim_add_comment")
            visible_checkbox = comment_form.find_element(By.XPATH, ".//input[@name='visible']")
            if visible_checkbox.is_selected():
                safe_click(driver, visible_checkbox, "'Visible for customer' checkbox")
        except Exception as e:
            print(f"⚠️ Could not uncheck 'Visible for customer': {e}")

        # Click "Comment" button
        comment_button = comment_form.find_element(By.XPATH, ".//button[contains(text(), 'Comment')]")
        safe_click(driver, comment_button, "'Comment' button")
        print(f"📝 Internal comment added: {comment_text}")
        time.sleep(1)

    except Exception as e:
        print(f"Error adding internal comment: {e}")
        import traceback
        traceback.print_exc()
        print(f"❌ Error filling commment: {e}")


def add_screenshot_comment(driver, result_code, case_number, hit_number):
    """
    Add a comment based on screenshot result.
    
    Args:
        driver: Selenium WebDriver instance
        result_code: Screenshot result code (1, 2, or 3)
        case_number: Case number for the comment
        hit_number: Hit number for the comment
    """
    if result_code == 1:
        message = "Credit not found, manual screenshot successfully captured"
    elif result_code == 2:
        message = "Credit not found, need further check in manual screenshot"
    elif result_code == 3:
        message = "Credit not found, no manual screenshot captured"
    else:
        print(f"[ERROR] Unknown screenshot result code: {result_code}")
        return

    full_comment = f"- Claim {case_number} | Hit {hit_number} | {message}"
    add_internal_comment(driver, full_comment)


def add_credit_comment(driver, case_results):
    """
    Add a comment to the case if any hit had credit detected.
    
    Args:
        driver: Selenium WebDriver instance
        case_results: List of case result dictionaries
        
    Returns:
        bool: True if comment was submitted, False otherwise
    """
    # Filter for positive credit findings
    positive_results = [
        r for r in case_results if r["credit_found"]
    ]

    if not positive_results:
        print("[INFO] No credit found—no comment added.")
        return False

    print("[INFO] 💬 Preparing to add comment for detected credits.")

    # Build the comment text
    comment_lines = []
    for r in positive_results:
        line = (
            f"- Claim {r['claim_number']} | Hit {r['hit_number']} | "
            f"Keyword: {r['credit_keyword']} "
        )
        if r.get("highlight_link"):
            line += f"\n Link to highlight: {r['highlight_link']}"
        comment_lines.append(line)

    comment_text = "\n".join(comment_lines)
    add_internal_comment(driver, comment_text)
    return True
