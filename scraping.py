import os
import csv
import sys
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Import credit checking functionality
from checker import check_image_credits

# Import upload utilities
from library.upload_utils import add_internal_comment

# Configuration
EMAIL = 'siu-wang.HUNG@mediaident.com'
PASSWORD = '!Changedpwat0616'
OUTPUT_CSV = "claims.csv"

MAX_HITS_PER_CLAIM = 3
OVERALL_CSV = "overall_checked_claims.csv"

def load_processed_claims():
    """Load already processed claims from overall_checked_claims.csv with file locking"""
    import fcntl
    import time
    
    processed_claims = set()
    
    if not os.path.exists(OVERALL_CSV):
        print(f"[INFO] No {OVERALL_CSV} found, will process all claims")
        return processed_claims
    
    # Retry mechanism for file locking
    max_retries = 5
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            # Create a lock file path
            lock_file = f"{OVERALL_CSV}.lock"
            
            # Try to acquire shared lock for reading
            with open(lock_file, 'w') as lock_f:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_SH)  # Shared lock
                
                with open(OVERALL_CSV, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        case_id = row.get('case_id', '').strip()
                        hit_number = row.get('hit_number', '').strip()
                        if case_id and hit_number:
                            processed_claims.add(f"{case_id}_{hit_number}")
                
                print(f"[INFO] Loaded {len(processed_claims)} already processed claims from {OVERALL_CSV}")
                return processed_claims
                
        except (IOError, OSError) as e:
            if attempt < max_retries - 1:
                print(f"[WARN] File locked, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"[WARN] Could not acquire lock after {max_retries} attempts: {e}")
                return processed_claims
        except Exception as e:
            print(f"[WARN] Error loading processed claims: {e}")
            return processed_claims
    
    return processed_claims

# Get number of claims from command line argument
if len(sys.argv) < 2:
    print("Usage: python scraping.py <number_of_claims>")
    sys.exit(1)

try:
    CLAIMS_TO_SCRAPE = int(sys.argv[1])
    print(f"[INFO] Will scrape {CLAIMS_TO_SCRAPE} claims")
except ValueError:
    print("Error: Please provide a valid number")
    sys.exit(1)

def setup_chrome_driver():
    """Setup Chrome driver with options and extensions"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Load extensions
    extensions_dir = os.path.abspath(".")
    cookies_extension = os.path.join(extensions_dir, "cookies_unpacked")
    ublock_extension = os.path.join(extensions_dir, "ublock_unpacked")
    
    extensions_to_load = []
    
    # Check if extension directories exist
    if os.path.exists(cookies_extension):
        extensions_to_load.append(cookies_extension)
        print(f"[INFO] 🍪 Found cookies extension: {cookies_extension}")
    else:
        print(f"[WARN] ⚠️ Cookies extension not found at: {cookies_extension}")
    
    if os.path.exists(ublock_extension):
        extensions_to_load.append(ublock_extension)
        print(f"[INFO] 🛡️ Found uBlock extension: {ublock_extension}")
    else:
        print(f"[WARN] ⚠️ uBlock extension not found at: {ublock_extension}")
    
    # Load all found extensions
    if extensions_to_load:
        extensions_path = ",".join(extensions_to_load)
        chrome_options.add_argument(f"--load-extension={extensions_path}")
        print(f"[INFO] 🔧 Loading extensions: {', '.join([os.path.basename(ext) for ext in extensions_to_load])}")
    else:
        print(f"[WARN] ⚠️ No extensions found to load")
    
    # Use the unified driver setup instead of ChromeDriverManager
    from library.unified_driver_utils import setup_driver as unified_setup
    
    # Create Chrome options for the unified setup
    extra_args = []
    if extensions_to_load:
        extensions_path = ",".join(extensions_to_load)
        extra_args.append(f"--load-extension={extensions_path}")
        print("[INFO] ⏳ Waiting for extensions to load...")
        time.sleep(5)
    
    # Use unified driver setup
    driver = unified_setup(headless=True, extra_chrome_args=extra_args)
    
    return driver

def extract_case_id_from_url(url):
    """Extract case ID from claim URL"""
    return url.split('/')[-1].split('?')[0]

def login(driver):
    """Login to Copytrack"""
    print("[INFO] Logging in to Copytrack...")
    driver.get("https://app.copytrack.com/")
    
    # Wait for email field to be clickable
    email_field = WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable((By.NAME, "_email"))
    )
    email_field.click()
    email_field.send_keys(EMAIL)
    
    # Wait for password field to be clickable
    password_field = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.NAME, "_password"))
    )
    password_field.click()
    password_field.send_keys(PASSWORD)
    
    # Click submit button
    submit_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))
    )
    submit_button.click()
    
    # Wait a moment for login to process
    time.sleep(3)
    print("[INFO] Login completed, proceeding to claims...")

def get_qualifying_cases(driver, target_count, processed_claims, filter_type=None):
    """Get qualifying cases from the review list"""
    qualifying_cases = []
    current_page = 1
    
    while len(qualifying_cases) < target_count:
        print(f"[INFO] Processing page {current_page}")
        
        url = f'https://app.copytrack.com/admin/claim/list/review?customerFeedbackRequired=0&itemsPerPage=100&s=c.createdAt&d=desc&page={current_page}'
        driver.get(url)
        
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[title="View images"]'))
        )
        
        view_buttons = driver.find_elements(By.CSS_SELECTOR, 'a[title="View images"]')
        print(f"[INFO] Found {len(view_buttons)} view buttons on page {current_page}")
        
        for btn in view_buttons:
            if len(qualifying_cases) >= target_count:
                break
                
            try:
                claim_row = btn.find_element(By.XPATH, "./ancestor::tr")
                hit_count_cells = claim_row.find_elements(By.TAG_NAME, "td")
                
                if len(hit_count_cells) > 11:
                    hit_count_text = hit_count_cells[11].text.strip()
                    hit_count = int(hit_count_text) if hit_count_text.isdigit() else 0
                    
                    if hit_count > MAX_HITS_PER_CLAIM:
                        print(f"[SKIP] Skipping claim with {hit_count} hits")
                        continue
                    
                    claim_url = btn.get_attribute('href')
                    if claim_url.startswith('/'):
                        claim_url = f'https://app.copytrack.com{claim_url}'
                    
                    case_id = extract_case_id_from_url(claim_url)
                    
                    # Apply even/odd filtering if specified
                    if filter_type:
                        case_id_num = int(case_id) if case_id.isdigit() else 0
                        if filter_type == "even" and case_id_num % 2 != 0:
                            print(f"[SKIP] Skipping odd case {case_id} (even filter)")
                            continue
                        elif filter_type == "odd" and case_id_num % 2 == 0:
                            print(f"[SKIP] Skipping even case {case_id} (odd filter)")
                            continue
                    
                    # Note: We don't skip entire cases here - we'll check individual hits later
                    
                    print(f"[INFO] Found qualifying case: {case_id} with {hit_count} hits")
                    qualifying_cases.append(claim_url)
                    
            except Exception as e:
                print(f"[ERROR] Error processing claim row: {e}")
                continue
        
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 'a[rel="next"]')
            if not next_button or not next_button.is_enabled():
                break
        except:
            break
            
        current_page += 1
        
        if current_page > 50:
            break
    
    return qualifying_cases

def process_case(driver, claim_url, case_id, processed_claims):
    """Process a single case and extract hit information with immediate credit checking"""
    print(f"[INFO] Processing case {case_id}")
    
    case_url_with_skip = claim_url + ("?skipCategory=1" if "?" not in claim_url else "&skipCategory=1")
    driver.get(case_url_with_skip)
    
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h4')))
    
    hit_h4s = driver.find_elements(By.XPATH, '//h4[.//input[@data-action="hit-mass-action"]]')
    print(f"[INFO] Found {len(hit_h4s)} hits in case {case_id}")
    
    case_rows = []
    for h4 in hit_h4s:
        try:
            checkbox = h4.find_element(By.CSS_SELECTOR, 'input[data-action="hit-mass-action"]')
            hit_number = checkbox.get_attribute('data-id')
            
            # Check if this hit has already been processed
            claim_key = f"{case_id}_{hit_number}"
            if claim_key in processed_claims:
                print(f"[SKIP] Hit {hit_number} in case {case_id} already processed, skipping...")
                continue
            
            container = driver.find_element(By.ID, f'claim-hit-{hit_number}')
            
            try:
                page_links = container.find_elements(By.XPATH, './/th[strong[contains(text(), "Page-URL:")]]/following-sibling::td//a')
                page_hrefs = [a.get_attribute('href') for a in page_links if a.get_attribute('href')]
            except:
                page_hrefs = []
            
            try:
                image_url_link = container.find_element(By.XPATH, './/th[strong[contains(text(), "Image-URL:")]]/following-sibling::td//a')
                image_url = image_url_link.get_attribute('href')
            except:
                image_url = None
            
            # Check credits immediately for each hit
            credit_results = {}
            if page_hrefs and image_url:
                print(f"[INFO] 🔍 Checking credits for hit {hit_number}...")
                for href in page_hrefs:
                    try:
                        # Perform credit check for this specific page and image
                        credit_results = check_image_credits(
                            target_image_url=image_url,
                            page_url=href,
                            case_url=case_url_with_skip,
                            hit_id=hit_number
                        )
                        print(f"[INFO] Credit check completed for hit {hit_number}: {len(credit_results.get('credit_keywords', []))} keywords found")
                        
                        # Handle comment based on credit check results
                        try:
                            if credit_results.get('credit_keywords'):
                                # Keywords found - add comment
                                print(f"[INFO] 💬 Adding comment for found credits in hit {hit_number}...")
                                comment_text = f"Credit keywords found for hit {hit_number}:\n"
                                for keyword in credit_results.get('credit_keywords', []):
                                    comment_text += f"- {keyword}\n"
                                if credit_results.get('highlight_url'):
                                    comment_text += f"Highlight URL: {credit_results['highlight_url']}"
                                
                                add_internal_comment(driver, comment_text)
                                print(f"[INFO] ✅ Comment added successfully for hit {hit_number}")
                                
                            else:
                                # No keywords found - add comment
                                print(f"[INFO] 💬 Adding comment for no credits found in hit {hit_number}...")
                                comment_text = f"No credit keywords found for hit {hit_number} after comprehensive analysis."
                                
                                add_internal_comment(driver, comment_text)
                                print(f"[INFO] ✅ Comment added successfully for hit {hit_number}")
                            
                            # Clean up screenshot after processing
                            screenshot_path = credit_results.get('screenshot_path')
                            if screenshot_path and os.path.exists(screenshot_path):
                                try:
                                    os.remove(screenshot_path)
                                    print(f"[INFO] 🗑️ Deleted screenshot: {screenshot_path}")
                                except Exception as e:
                                    print(f"[WARN] Could not delete screenshot {screenshot_path}: {e}")
                                    
                        except Exception as e:
                            print(f"[ERROR] Error handling comment for hit {hit_number}: {e}")
                        
                        break  # Only check the first page URL for now
                    except Exception as e:
                        print(f"[ERROR] Credit check failed for hit {hit_number}: {e}")
                        credit_results = {'error': str(e)}
            elif not page_hrefs:
                print(f"[INFO] ⚠️ No page URLs found for hit {hit_number}, skipping credit check")
                credit_results = {'error': 'No page URLs available'}
            elif not image_url:
                print(f"[INFO] ⚠️ No image URL found for hit {hit_number}, skipping credit check")
                credit_results = {'error': 'No image URL available'}
            
            # Add credit results to the row data
            if page_hrefs:
                for href in page_hrefs:
                    case_rows.append([
                        case_id, 
                        case_url_with_skip, 
                        hit_number, 
                        href, 
                        image_url,
                        credit_results.get('image_found', False),
                        len(credit_results.get('credit_keywords', [])) > 0,
                        ', '.join(credit_results.get('credit_keywords', [])),
                        credit_results.get('highlight_url', ''),
                        credit_results.get('error', ''),
                        credit_results.get('screenshot_path', ''),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ])
            else:
                case_rows.append([
                    case_id, 
                    case_url_with_skip, 
                    hit_number, 
                    "", 
                    image_url,
                    credit_results.get('image_found', False),
                    len(credit_results.get('credit_keywords', [])) > 0,
                    ', '.join(credit_results.get('credit_keywords', [])),
                    credit_results.get('highlight_url', ''),
                    credit_results.get('error', ''),
                    credit_results.get('screenshot_path', ''),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ])
                
        except Exception as e:
            print(f"[ERROR] Error processing hit: {e}")
            continue
    
    return case_rows


def main():
    """Main execution function with continuous processing"""
    import sys
    import time
    
    # Get filter type from command line argument
    filter_type = None
    if len(sys.argv) > 2:
        filter_type = sys.argv[2].lower()
        if filter_type not in ["even", "odd"]:
            print(f"[ERROR] Invalid filter type: {filter_type}. Use 'even' or 'odd'")
            sys.exit(1)
        print(f"[INFO] Filtering for {filter_type} case IDs")
    
    print(f"\n[INFO] ===== Starting Continuous Credit Checking =====")
    print(f"[INFO] No cycles - continuous processing mode")
    
    # Load already processed claims once at startup
    processed_claims = load_processed_claims()
    print(f"[INFO] Loaded {len(processed_claims)} already processed claims from overall_checked_claims.csv")
    
    # Setup browser driver once
    driver = setup_chrome_driver()
    
    try:
        # Login once
        login(driver)
        
        # Continuous processing loop
        while True:
            print(f"\n[INFO] ===== Checking for new claims =====")
            
            # Get qualifying cases (this will automatically skip already processed ones)
            qualifying_cases = get_qualifying_cases(driver, CLAIMS_TO_SCRAPE, processed_claims, filter_type)
            
            if not qualifying_cases:
                print(f"[INFO] No new qualifying cases found. Waiting 10 seconds before next check...")
                time.sleep(10)
                continue
            
            print(f"[INFO] Found {len(qualifying_cases)} new qualifying cases to process")
            
            # Process each case
            all_rows = []
            with open(OUTPUT_CSV, "a", newline='', encoding='utf-8') as f:  # Append mode instead of write
                writer = csv.writer(f)
                
                # Write header only if file is empty
                if f.tell() == 0:
                    writer.writerow([
                        "case_id", "case_url", "hit_number", "page_url", "image_url",
                        "image_found", "keyword_found", "keywords_list", "keyword_highlight", 
                        "error_status", "screenshot_path", "processed_at"
                    ])
                
                for i, claim_url in enumerate(qualifying_cases, 1):
                    case_id = extract_case_id_from_url(claim_url)
                    print(f"[INFO] Processing case {i}/{len(qualifying_cases)}: {case_id}")
                    
                    try:
                        case_rows = process_case(driver, claim_url, case_id, processed_claims)
                        
                        if case_rows:  # Only process if we have results
                            writer.writerows(case_rows)
                            f.flush()
                            all_rows.extend(case_rows)
                            
                            # Update processed_claims set with all hits from this case
                            for row in case_rows:
                                hit_number = row[2]  # hit_number is the 3rd column
                                claim_key = f"{case_id}_{hit_number}"
                                processed_claims.add(claim_key)
                            
                            # Update overall_checked_claims.csv immediately after processing this case
                            print(f"[INFO] Updating overall_checked_claims.csv with {len(case_rows)} rows from case {case_id}")
                            update_overall_checked_claims(case_rows)
                            
                            print(f"[INFO] Finished case {case_id}, {len(case_rows)} rows written")
                        else:
                            print(f"[INFO] No new hits processed for case {case_id}")
                        
                        time.sleep(1)  # Small delay between cases
                        
                    except Exception as e:
                        print(f"[ERROR] Error processing case {case_id}: {e}")
                        continue
            
            print(f"[INFO] ✅ Processed {len(qualifying_cases)} cases, {len(all_rows)} total rows")
            print(f"[INFO] Waiting 5 seconds before checking for more claims...")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n[INFO] Stopping continuous processing...")
    except Exception as e:
        print(f"[ERROR] Fatal error in continuous processing: {e}")
        raise
    finally:
        driver.quit()

if __name__ == "__main__":
    main()