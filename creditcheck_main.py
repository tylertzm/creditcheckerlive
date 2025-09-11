from selenium.common import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from gettext import npgettext
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.devtools.v135.indexed_db import Key
from urllib.parse import urlparse
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import unquote
import os 
from datetime import datetime
from pynput.keyboard import Key, Controller
from selenium.webdriver.support.ui import Select
import sys
if sys.platform == "win32":
    from pywinauto.application import Application
    from pywinauto import Desktop
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement

# --------- CREDIT KEYWORDS ---------
CREDIT_KEYWORDS = [
    "getty", "reuters", "ap photo", "asso ciated press", "cnn photo", "freedigitalphotos.net", "favim",
    "nytimes", "imago", "panthermedia", "thinkstock", "bigstock", "hikevent", "icon sport", "clipdealer", "vector image",
    "shutterstock", "istock", "i stock", "alamy", "fotolia", "123rf", "deposit photos", "depositphotos", "depositphoto", "freepik",
    "freepik.com", "adobe stock", "alphaspirit", "alphaspirit.it", "alamy stock photo", "vector stock", "pose t bernard custodio",
    "pixabay", "pexels", "unsplash", "pexel", "mostphotos", "stock.adobe.com", "garrett photography", "istockphoto.com", "jcoahgne",
    "journey era", "profimedia", "fr.depositphotos.com", "fotolia.com", "tagstiles.com", "www.shutterstock.com", "fr.freepik.com", "can stock photo", "canstockphoto", "123rf.com"

]

email = 'siu-wang.HUNG@mediaident.com'
password = '!Changedpwat0616'
threshold = 48

def Mouse_position():
    # Mouse positioning removed - not needed in headless mode
    pass

def Open_Chrome():
    options = Options()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-insecure-localhost')
    options.add_argument('--no-sandbox')
    return webdriver.Chrome(options=options)


def login_and_navigate_to_New(driver):
    """
    Logs into Copytrack and navigates directly to the 'New' claims page with desired filters.
    """
    driver.get('https://app.copytrack.com/')
    driver.implicitly_wait(30)

    # Login
    driver.find_element(By.ID, 'email').send_keys(email)
    driver.find_element(By.ID, 'password').send_keys(password)
    driver.find_element(By.CSS_SELECTOR, 'body > div > div:nth-child(2) > div > div.ibox-content > form > button').click()
    time.sleep(2)

    # Navigate directly to the filtered 'New' claims page
    driver.get('https://app.copytrack.com/admin/claim/list/new?itemsPerPage=100&s=hitCount&d=desc&page=1')
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//a[@title="View images"]'))
    )
    print("[INFO] ✅ Successfully logged in and navigated to filtered 'New' claims page.")

import ahocorasick

# Build automaton once
automaton = ahocorasick.Automaton()
for idx, keyword in enumerate(CREDIT_KEYWORDS):
    automaton.add_word(keyword.lower(), (idx, keyword))
automaton.make_automaton()

def contains_credit(text):
    if not text:
        return False, None
    text = text.lower()
    for end_idx, (idx, kw) in automaton.iter(text):
        print(f"[DEBUG] Credit match found: '{kw}'")
        return True, kw
    return False, None




def locate_all_images_by_url(driver, target_image_url):
    """
    Locate **all** image elements matching the target image URL (by filename).
    """
    target_filename = urlparse(target_image_url).path.split('/')[-1].lower()

    # Wait for page load
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
    except Exception:
        print("[WARN] Page did not reach readyState=complete within 30s; continuing anyway.")

    time.sleep(1)

    # Scroll slowly to trigger lazy loading
    scroll_height = driver.execute_script("return document.body.scrollHeight")
    for y in range(0, scroll_height, 400):
        driver.execute_script(f"window.scrollTo(0, {y});")
        time.sleep(0.3)

    images = driver.find_elements(By.TAG_NAME, 'img')
    print(f"[INFO] Found {len(images)} images on the page after scrolling.")

    matched_images = []
    for idx, img in enumerate(images):
        try:
            attrs = [
                img.get_attribute("src"),
                img.get_attribute("srcset"),
                img.get_attribute("data-src"),
                img.get_attribute("data-lazy-src"),
                img.get_attribute("data-srcset"),
                img.get_attribute("data-lazy-srcset"),
            ]
            combined = " ".join([a for a in attrs if a]).lower()
            if target_filename in combined:
                print(f"[INFO] ✅ Match found for image at index {idx}")
                matched_images.append(img)
        except Exception as e:
            print(f"[DEBUG] Failed to inspect image at index {idx}: {e}")

    if not matched_images:
        print("[INFO] ❌ No matching images found.")
    return matched_images



def checking_for_credit(driver, matched_img, max_text_length=5000):
    def safe_trimmed_text(text):
        if not text:
            return ""
        text = text.strip()
        return text if len(text) <= max_text_length else ""

    def extract_nearby_texts(img):
        texts = []

        # Alt attribute
        try:
            alt = safe_trimmed_text(img.get_attribute('alt'))
            if alt:
                texts.append(alt)
                print("[DEBUG] Alt text collected.")
        except Exception as e:
            print(f"[ERROR] Alt attribute: {e}")

        # Parent and grandparent
        try:
            parent = img.find_element(By.XPATH, './..')
            text = safe_trimmed_text(parent.get_attribute("innerText"))
            if text:
                texts.append(text)
                print("[DEBUG] Parent text collected.")

            grandparent = parent.find_element(By.XPATH, './..')
            text = safe_trimmed_text(grandparent.get_attribute("innerText"))
            if text:
                texts.append(text)
                print("[DEBUG] Grandparent text collected.")
        except Exception as e:
            print(f"[ERROR] Parent/grandparent: {e}")

        # Nearby figure or div/span container
        try:
            container = img.find_element(By.XPATH, './ancestor::*[self::figure or self::div or self::span][1]')
            text = safe_trimmed_text(container.get_attribute("innerText"))
            if text:
                texts.append(text)
                print("[DEBUG] Container text collected.")
        except Exception as e:
            print(f"[ERROR] Ancestor container: {e}")

        # Nearby caption-like elements (within ~500px vertically)
        try:
            nearby_captions = (
                driver.find_elements(By.TAG_NAME, 'figcaption') +
                driver.find_elements(By.CLASS_NAME, 'img_caption') +
                driver.find_elements(By.CLASS_NAME, 'caption') +
                driver.find_elements(By.TAG_NAME, 'font') +
                driver.find_elements(By.TAG_NAME, 'span') +
                driver.find_elements(By.TAG_NAME, 'p')
            )
            print(f"[DEBUG] Found {len(nearby_captions)} potential captions.")
            img_y = img.location['y']
            for el in nearby_captions:
                try:
                    y = el.location['y']
                    if abs(y - img_y) < 500:
                        text = safe_trimmed_text(el.get_attribute("textContent"))
                        if text:
                            texts.append(text)
                except:
                    continue
        except Exception as e:
            print(f"[ERROR] Nearby captions: {e}")

        return texts

    # === Main Execution ===
    print("[DEBUG] checking_for_credit: Extracting all nearby texts...")
    collected_texts = extract_nearby_texts(matched_img)

    print(f"[DEBUG] Total text blocks collected: {len(collected_texts)}")

    combined_text = " ".join(collected_texts).lower()
    found, keyword = contains_credit(combined_text)
    if found:
        print(f"[INFO] ✅ Credit detected in combined text. Keyword: {keyword}")
        return True, keyword, "combined_text"
    return False, None, None


def add_credit_comment(driver, case_results):
    """
    Adds a comment to the case if any hit had credit detected.
    Returns True if comment was submitted, False otherwise.
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
            #f"URL: {r['page_url']} | Credit: True | "
            f"Keyword: {r['credit_keyword']} "
            #f"| Method: {r['credit_method']}"
        )
        if r.get("highlight_link"):
            line += f"\n Link to highlight: {r['highlight_link']}"
        comment_lines.append(line)

    comment_text = "\n".join(comment_lines)
    add_internal_comment(driver, comment_text)
    return True



def safe_click(driver, element, description="element"):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", element)
        print(f"✅ Clicked {description} via JavaScript.")
    except Exception as e:
        print(f"❌ Could not click {description}: {e}")


def add_internal_comment(driver, comment_text):
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
    Adds a comment based on screenshot result:
    1 - Screenshot captured and passed threshold
    2 - Screenshot captured but did not pass threshold
    3 - Screenshot not captured
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





def capture_image_screenshot(driver, matched_image, case_text_clean):
    if isinstance(matched_image, WebElement):
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                matched_image
            )
            time.sleep(2)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            screenshot_path = fr"{case_text_clean}_{timestamp}.png"

            # Use Selenium to take screenshot instead of pyautogui
            driver.save_screenshot(screenshot_path)
            time.sleep(1)

            print(f"[INFO] 📸 Screenshot taken and saved to: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            print(f"[ERROR] ❌ Failed to capture screenshot: {e}")
            return None
    else:
        print("[ERROR] ❌ matched_image is not a valid WebElement.")
        return None


def click_button(driver, action, element=None):
    """
    Performs different button clicks or dropdown selections based on the action keyword.

    If `element` is provided, clicks it directly.
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

from PIL import Image
import imagehash
import requests
from io import BytesIO
import os

def compare_screenshot_to_image_url(screenshot_path, image_url, threshold):
    """
    Compare screenshot with image downloaded from Image-URL using perceptual hashing.
    Returns (is_match, score)
    """

    try:
        # ✅ Step 1: Load screenshot
        if not os.path.exists(screenshot_path):
            print(f"[ERROR] Screenshot not found at: {screenshot_path}")
            return False, None
        img1 = Image.open(screenshot_path).convert("RGB")
        hash1 = imagehash.phash(img1)

        # ✅ Step 2: Download and open image from URL
        response = requests.get(image_url, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR] Failed to download image from: {image_url}")
            return False, None
        img2 = Image.open(BytesIO(response.content)).convert("RGB")
        hash2 = imagehash.phash(img2)

        # ✅ Step 3: Compare
        score = hash1 - hash2
        is_match = score <= threshold
        print(f"[INFO] 🧮 Image hash score: {score} (Match: {is_match})")

        return is_match, score

    except Exception as e:
        print(f"[ERROR] ❌ Image comparison failed: {e}")
        return False, None

def try_upload_evidence(driver, upload_xpath, retries=2):
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

#-------------------------------------- We have 2 screenshot upload function here----------------------------------------------------------------------------
def upload_screenshot_evidence_usual(driver, screenshot_path, page_hrefs, link_idx, case_number, hit_number):
    """
    Uploads a screenshot for a specific link index in Copytrack.
    Returns True if upload succeeded, False otherwise.
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
    
    # Use Selenium file upload instead of pyautogui
    try:
        file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
        file_input.send_keys(screenshot_path)
        time.sleep(2)
    except Exception as e:
        print(f"[ERROR] Could not find file input element: {e}")
        # Fallback: try clicking the upload button and hope there's a file input
        click_button(driver, "file upload")
        time.sleep(1.2)
        try:
            file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
            file_input.send_keys(screenshot_path)
            time.sleep(2)
        except Exception as e2:
            print(f"[ERROR] Could not upload file even with fallback: {e2}")
            return False

    click_button(driver, "submit evidence")
    time.sleep(1.2)

    print("[INFO] ✅ Screenshot uploaded successfully.")
    return True

def upload_screenshot_evidence_new_claims(driver, screenshot_path, page_hrefs, link_idx, case_number, hit_number):
    """
    Uploads a screenshot using Copytrack's Add Files → Start Upload flow using safe_click.
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
        # (i) Look for file input element first, then try clicking "Add files" button if needed
        file_input = None
        try:
            file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
        except:
            # If no file input found, click "Add files" button and try again
            driver.find_element(By.CSS_SELECTOR,'#claim_documents_form > button.btn.btn-primary.pull-right.btn-xs.fileinput-button.dz-clickable > span').click()
            time.sleep(1.2)
            try:
                file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
            except Exception as e:
                print(f"[ERROR] Could not find file input after clicking Add files: {e}")
                return False

        # (ii) Upload file using Selenium instead of pyautogui
        if file_input:
            file_input.send_keys(screenshot_path)
            time.sleep(2)
        else:
            print("[ERROR] No file input element found")
            return False

        # (iii) Wait for and click "Start upload" button
        start_upload_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-action='start-document-upload']//span[text()='Start upload']/.."))
        )
        safe_click(driver, start_upload_button, "'Start upload' button")
        time.sleep(3)

        print("[INFO] ✅ Screenshot uploaded successfully.")
        return True

    except Exception as e:
        print(f"[ERROR] Upload process failed: {e}")
        import traceback
        traceback.print_exc()
        add_screenshot_comment(driver, 3, case_number, hit_number)
        return False


if __name__ == "__main__":
    # --------- TEST USAGE ---------
    driver = Open_Chrome()
    Mouse_position()
    login_and_navigate_to_New(driver)

    # Keep track of processed case numbers
    processed_case_numbers = set()

    # Dealing with case
    while True:
        # Always re-fetch all "View images" buttons and URLs
        view_buttons = driver.find_elements(By.XPATH, '//a[@title="View images"]')
        if not view_buttons:
            print("[INFO] ✅ No more cases found. All done.")
            break

        print(f"[INFO] 🔄 Found {len(view_buttons)} case buttons. Checking which are unprocessed...")

        unprocessed_idx = None
        unprocessed_case_number = None

        # Pre-read all case URLs without clicking
        for idx, btn in enumerate(view_buttons):
            href = btn.get_attribute("href")
            if not href:
                continue
            # Extract the case number from URL
            case_number = href.rstrip('/').split('/')[-1]
            if case_number not in processed_case_numbers:
                unprocessed_idx = idx
                unprocessed_case_number = case_number
                print(f"[INFO] 👉 First unprocessed case found: {case_number}")
                break

        if unprocessed_idx is None:
            print("[INFO] ✅ No unprocessed cases found on this page.")

            # Try to find the Next button
            try:
                next_button = driver.find_element(By.XPATH, '//a[@rel="next"]')
                if next_button.is_displayed():
                    next_href = next_button.get_attribute("href")
                    print(f"[INFO] 🔄 Navigating to next page: {next_href}")
                    next_button.click()
                    time.sleep(3)  # Allow the next page to load
                    continue  # Start the while loop again on the new page
                else:
                    print("[INFO] No more pages to process. Exiting.")
                    break
            except Exception:
                print("[INFO] No Next button found. All cases completed.")
                break

        # Navigate to modified case detail URL with skipCategory=1
        btn_to_click = view_buttons[unprocessed_idx]
        case_url = btn_to_click.get_attribute("href")
        modified_url = case_url + "?skipCategory=1"
        driver.get(modified_url)
        time.sleep(2)

        case_number = unprocessed_case_number

        # === Process the current case ===

        # 1️⃣ Get target image URL (same as before)
        try:
            image_url_element = driver.find_element(By.XPATH,
                                                    '//th[.//strong[text()="Image-URL:"]]/following-sibling::td//a')
            target_image_url = unquote(image_url_element.get_attribute("href")).strip()
        except Exception:
            print(f"[WARN] Couldn't extract image URL for {case_number}. Marking as processed and skipping case.")
            processed_case_numbers.add(case_number)
            driver.back()
            time.sleep(2)
            continue

        # 2️⃣ Find all hits
        hit_h4s = driver.find_elements(By.XPATH, '//h4[input[@data-action="hit-mass-action"]]')
        print(f"[INFO] Found {len(hit_h4s)} hits for case {case_number}")



        # 3️⃣ Result collection
        case_results = []

        # 4️⃣ Loop through hits
        for hit_h4 in hit_h4s:
            try:
                # Extract Hit number from data-id attribute
                checkbox = hit_h4.find_element(By.XPATH, './/input[@data-action="hit-mass-action"]')
                hit_number = checkbox.get_attribute('data-id').strip()
            except Exception:
                print("[WARN] Could not extract hit number; skipping this hit.")
                continue

            print(f"[INFO] Processing Hit #{hit_number}")

            # Expand the hit if collapsed
            try:
                toggle_button = hit_h4.find_element(By.XPATH, './/a[@data-toggle="collapse"]')
                if toggle_button.get_attribute("aria-expanded") == "false":
                    driver.execute_script("arguments[0].click();", toggle_button)
                    time.sleep(1)
            except Exception:
                pass

            # 5️⃣ Collect Page URLs within this hit
            # Build XPath for container div
            hit_container_id = f"claim-hit-{hit_number}"
            container_xpath = f'//div[@id="{hit_container_id}"]'

            page_url_elements = driver.find_elements(By.XPATH,
                                                     f'{container_xpath}//th[.//strong[text()="Page-URL:"]]/following-sibling::td//a')
            page_hrefs = [el.get_attribute("href") for el in page_url_elements]

            if not page_hrefs:
                print(f"[WARN] No Page URLs found in Hit #{hit_number}")
                continue

            print(f"[INFO] Found {len(page_hrefs)} Page URLs in Hit #{hit_number}")

            # 6️⃣ Loop through Page URLs in this hit
            for link_idx, href in enumerate(page_hrefs, start=1):
                print(f"[INFO] 🔗 [{link_idx}] Page URL: {href}")

                # Open in new tab
                driver.execute_script("window.open(arguments[0]);", href)
                time.sleep(2)
                driver.switch_to.window(driver.window_handles[-1])

                # Locate images
                matched_images = locate_all_images_by_url(driver, target_image_url)

                credit_found = False
                credit_keyword = None
                credit_method = None

                for i, img in enumerate(matched_images):
                    found, keyword, method = checking_for_credit(driver, img)
                    if found:
                        credit_found = True
                        credit_keyword = keyword
                        credit_method = method
                        print(f"[RESULT] ✅ Credit found for image #{i + 1}: Keyword '{keyword}' via method '{method}'")
                        break

                # Perform screenshot here
                if not credit_found:
                    print("[RESULT] ❌ No credit detected in this Page URL.")
                    # Add screenshot function here---------------------------------------------------------------------------------------------------
                    # Locate image and take screenshot
                    Mouse_position()
                    # Locate image, take screenshot
                    time.sleep(1.3)
                    # Always re-locate fresh to avoid stale reference
                    if matched_images:
                        screenshot_path = capture_image_screenshot(driver, matched_images[0], f"{case_number}_{hit_number}_{link_idx}")
                    else:
                        print("[ERROR] ❌ No matched image to screenshot.")
                        screenshot_path = None

                    # Close tab
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    time.sleep(10)

                    upload_screenshot_evidence_new_claims(driver, screenshot_path, page_hrefs, link_idx, case_number, hit_number)

                    compare_screenshot_to_image_url(screenshot_path, target_image_url, threshold)

                    is_match, score = compare_screenshot_to_image_url(screenshot_path, target_image_url, threshold)

                    if matched_images:
                        if is_match:
                            add_screenshot_comment(driver, 1, case_number, hit_number)
                        elif score is not None:
                            add_screenshot_comment(driver, 2, case_number, hit_number)
                        else:
                            add_screenshot_comment(driver, 3, case_number, hit_number)
                    else:
                        add_screenshot_comment(driver, 3, case_number, hit_number)

                    # Open in new tab
                    driver.execute_script("window.open(arguments[0]);", href)
                    time.sleep(2)
                    driver.switch_to.window(driver.window_handles[-1])

                else:
                    print("[ERROR] Screenshot path is None, skipping upload.")

                    # Open in new tab
                    driver.execute_script("window.open(arguments[0]);", href)
                    time.sleep(2)
                    driver.switch_to.window(driver.window_handles[-1])



                #----------------------------------------------------------------------------------------------------------------
                # Here is inside the hit page
                # Append result
                highlight_link = None
                if credit_found and credit_keyword:
                    encoded_text = credit_keyword.replace(" ", "%20")
                    highlight_link = f"{href}#:~:text={encoded_text}"

                case_results.append({
                    "claim_number": case_number,
                    "hit_number": hit_number,
                    "page_url": href,
                    "credit_found": credit_found,
                    "credit_keyword": credit_keyword,
                    "credit_method": credit_method,
                    "highlight_link": highlight_link
                })

                # Close tab
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)

        # After all hits processed
        processed_case_numbers.add(case_number)

        # Output collected results for this case
        print("[SUMMARY] Results for case:", case_number)
        for r in case_results:
            print(
                f"- Claim {r['claim_number']} | Hit {r['hit_number']} | "
                f"URL: {r['page_url']} | Credit: {r['credit_found']} | Keyword: {r['credit_keyword']}"
            )
        add_credit_comment(driver, case_results)
        time.sleep(5)

        # In future: you can yield/return case_results to store to a file
        driver.back()
        time.sleep(3)

    print("[INFO] 🎉 All cases done.")


    input("Press Enter to exit...")

    driver.quit()
