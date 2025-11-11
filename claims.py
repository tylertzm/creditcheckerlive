import os
import csv
import sys
import datetime
import time
import random
from playwright.sync_api import sync_playwright

# Parse command line arguments for even/odd filtering
CLAIM_TYPE = "even"  # Default to even
if len(sys.argv) > 1:
    CLAIM_TYPE = sys.argv[1].lower()
    if CLAIM_TYPE not in ["even", "odd"]:
        print(f"❌ Invalid claim type: {CLAIM_TYPE}. Must be 'even' or 'odd'")
        sys.exit(1)

print(f"[INFO] Processing {CLAIM_TYPE} claim IDs only")

# Configuration variables - modify these as needed
EMAIL = 'siu-wang.HUNG@mediaident.com'
PASSWORD = '!Changedpwat0616'
OUTPUT_DIR = "output"
INPUT_CSV = "overall_checked_claims.csv"  # Input: already processed claims
OUTPUT_CSV = f"cases_{CLAIM_TYPE}.csv"  # Output: new cases to process (even/odd specific)

# Scraping limits
MAX_HITS_PER_CLAIM = 2  # Skip claims with 3 or more hits (process only 0, 1, 2 hits)
MAX_CASES_TO_SCRAPE = 300  # Maximum number of cases to process
MAX_PAGES_TO_CHECK = 255 # Maximum number of pages to check for claims
TIMEOUT_MINUTES = 10  # Maximum time to run scraping (10 minutes)

# Track start time for timeout
SCRAPING_START_TIME = time.time()

os.makedirs(OUTPUT_DIR, exist_ok=True)
input_path = os.path.join(OUTPUT_DIR, INPUT_CSV)
output_path = os.path.join(OUTPUT_DIR, OUTPUT_CSV)

def is_csv_file(file_path):
    """Check if the file is a CSV based on extension and content"""
    if not os.path.exists(file_path):
        return False
    
    # Check extension
    if file_path.lower().endswith('.csv'):
        return True
    
    # Check content for CSV format (basic check)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            # If it has commas and doesn't look like a URL, assume CSV
            if ',' in first_line and not first_line.startswith('http'):
                return True
    except:
        pass
    
    return False

def extract_case_id_from_url(url):
    """Extract case ID from claim URL"""
    return url.split('/')[-1].split('?')[0]

def should_process_case_id(case_id):
    """Check if case ID should be processed based on even/odd filter"""
    try:
        # Extract numeric part from case ID (assuming it ends with numbers)
        # Handle different case ID formats
        numeric_part = None
        
        # Try to find the last sequence of digits in the case ID
        import re
        digits = re.findall(r'\d+', case_id)
        if digits:
            numeric_part = int(digits[-1])  # Use the last sequence of digits
        else:
            # If no digits found, try to convert the whole case_id
            numeric_part = int(case_id)
        
        # Check if it matches the required type
        if CLAIM_TYPE == "even":
            return numeric_part % 2 == 0
        else:  # odd
            return numeric_part % 2 == 1
            
    except (ValueError, TypeError):
        # If we can't parse the case ID as a number, skip it
        print(f"[DEBUG] Could not parse case ID '{case_id}' as number, skipping")
        return False

# --- Load already processed cases from overall_checked_claims.csv ---
processed_cases = set()
if os.path.exists(input_path):
    with open(input_path, "r", newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('case_id'):
                processed_cases.add(row['case_id'])
    print(f"[INFO] Found {len(processed_cases)} already processed cases in {INPUT_CSV}")
else:
    print(f"[INFO] No {INPUT_CSV} found - will process all cases")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()

    # --- LOGIN ---
    page.goto("https://app.copytrack.com/")
    page.wait_for_selector('input[name="_email"]', timeout=60000)
    page.fill('input[name="_email"]', EMAIL)
    page.fill('input[name="_password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    # --- DETERMINE SOURCE OF CASE URLs ---
    case_urls = []
    
    print(f"[INFO] Forcing web scraping. Ignoring any input files.")
    # --- NAVIGATE TO REVIEW LIST (START FROM PAGE 1) ---
    current_page = 1
    
    while len(case_urls) < MAX_CASES_TO_SCRAPE:  # Continue until we have enough URLs or no more pages
        # Check timeout first
        elapsed_time = time.time() - SCRAPING_START_TIME
        if elapsed_time > (TIMEOUT_MINUTES * 60):
            print(f"[TIMEOUT] Scraping stopped after {elapsed_time/60:.1f} minutes (limit: {TIMEOUT_MINUTES} minutes)")
            print(f"[TIMEOUT] Processed {len(case_urls)} cases before timeout")
            break
            
        print(f"[INFO] Processing page {current_page} (elapsed: {elapsed_time/60:.1f} min)")
        page.goto(f'https://app.copytrack.com/admin/claim/list/review?customerFeedbackRequired=0&itemsPerPage=100&s=c.createdAt&d=desc&page={current_page}')
        page.wait_for_selector('a[title="View images"]', timeout=60000)

        # --- EXTRACT CASE URLs ---
        view_buttons = page.query_selector_all('a[title="View images"]')
        print(f"[INFO] Found {len(view_buttons)} view buttons on page {current_page}")
        
        # First, collect all qualifying case URLs and hit counts from the current page
        qualifying_cases = []
        page_stats = {
            'total_buttons': len(view_buttons),
            'high_hits': 0,
            'already_processed': 0,
            'wrong_type': 0,
            'qualifying': 0
        }
        
        for btn in view_buttons:
            try:
                claim_row = btn.evaluate_handle('el => el.closest("tr")')
                if not claim_row:
                    continue

                # Extract the hit count from the 12th column (Hit count column)
                hit_count_cell = claim_row.query_selector_all('td')[11]  # 12th column (0-indexed), which is the "Hit count" column
                
                # Ensure the hit count is numeric before converting
                hit_count_text = hit_count_cell.inner_text().strip() if hit_count_cell else '0'
                hit_count = int(hit_count_text) if hit_count_text.isdigit() else 0
                
                print(f"[DEBUG] Hit count: {hit_count_text} -> {hit_count}")

                # Skip claims with too many hits
                if hit_count > MAX_HITS_PER_CLAIM:
                    print(f"[DEBUG] Skipping claim with {hit_count} hits (max allowed: {MAX_HITS_PER_CLAIM})")
                    page_stats['high_hits'] += 1
                    continue

                # Extract the claim URL
                claim_url = btn.get_attribute('href')
                if not claim_url:
                    continue
                    
                # Store case info for processing
                if claim_url.startswith('/'):
                    claim_url = f'https://app.copytrack.com{claim_url}'
                
                case_id = extract_case_id_from_url(claim_url)
                
                # Skip if already processed
                if case_id in processed_cases:
                    print(f"[SKIP] Case {case_id} already processed")
                    page_stats['already_processed'] += 1
                    continue
                
                # Skip if case ID doesn't match the required even/odd filter
                if not should_process_case_id(case_id):
                    print(f"[SKIP] Case {case_id} doesn't match {CLAIM_TYPE} filter")
                    page_stats['wrong_type'] += 1
                    continue
                
                qualifying_cases.append(claim_url)
                page_stats['qualifying'] += 1
                
            except Exception as e:
                print(f"[ERROR] Error processing claim row: {e}")
                continue
        
        # Print page statistics
        print(f"[PAGE {current_page} STATS] Total buttons: {page_stats['total_buttons']}, "
              f"High hits: {page_stats['high_hits']}, Already processed: {page_stats['already_processed']}, "
              f"Wrong type ({CLAIM_TYPE}): {page_stats['wrong_type']}, Qualifying: {page_stats['qualifying']}")
        
        # Now process each qualifying case
        for claim_url in qualifying_cases:
            # Check timeout before processing each case
            elapsed_time = time.time() - SCRAPING_START_TIME
            if elapsed_time > (TIMEOUT_MINUTES * 60):
                print(f"[TIMEOUT] Stopping case processing after {elapsed_time/60:.1f} minutes")
                break
                
            # Check if we've reached the case limit
            if len(case_urls) >= MAX_CASES_TO_SCRAPE:
                print(f"[INFO] Reached maximum cases limit ({MAX_CASES_TO_SCRAPE}). Stopping.")
                break
                
            case_id = extract_case_id_from_url(claim_url)
            print(f"[INFO] Processing case {case_id} (case {len(case_urls) + 1}/{MAX_CASES_TO_SCRAPE}) - {elapsed_time/60:.1f}min elapsed")
            
            # Process this case and add to results
            case_urls.append(claim_url)
            
            # --- Process the case immediately ---
            # --- Add skipCategory parameter if not already present ---
            if "?" not in claim_url:
                case_url_with_skip = claim_url + "?skipCategory=1"
            elif "skipCategory" not in claim_url:
                case_url_with_skip = claim_url + "&skipCategory=1"
            else:
                case_url_with_skip = claim_url

            page.goto(case_url_with_skip)
            page.wait_for_load_state("networkidle")

            hit_h4s = page.query_selector_all('h4:has(input[data-action="hit-mass-action"])')
            print(f"[INFO] Processing case {case_id} with {len(hit_h4s)} hits")

            # --- OPEN CSV FOR WRITING / APPENDING ---
            write_header = not os.path.exists(output_path)
            with open(output_path, "a", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(["case_id", "case_url", "hit_number", "page_url", "image_url"])

                case_rows = []
                for h4 in hit_h4s:
                    checkbox = h4.query_selector('input[data-action="hit-mass-action"]')
                    hit_number = checkbox.get_attribute('data-id') if checkbox else None

                    # --- Skip already processed hits ---
                    # (We already check at case level, but keeping this for safety)

                    container = page.query_selector(f'div#claim-hit-{hit_number}')
                    if not container:
                        continue

                    page_links = container.query_selector_all('th:has(strong:text("Page-URL:")) + td a')
                    page_hrefs = [a.get_attribute('href') for a in page_links if a.get_attribute('href')]

                    image_url_link = container.query_selector('th:has(strong:text("Image-URL:")) + td a')
                    image_url = image_url_link.get_attribute('href') if image_url_link else None

                    if page_hrefs:
                        for href in page_hrefs:
                            case_rows.append([case_id, case_url_with_skip, hit_number, href, image_url])
                    else:
                        case_rows.append([case_id, case_url_with_skip, hit_number, "", image_url])

                    # --- Mark case as processed ---
                    processed_cases.add(case_id)

                # --- Write current case rows to CSV immediately ---
                writer.writerows(case_rows)
                f.flush()
                print(f"[INFO] Finished case {case_id}, {len(case_rows)} rows written to CSV")
        
        # Check if we've reached the limit after processing this page
        if len(case_urls) >= MAX_CASES_TO_SCRAPE:
            print(f"[INFO] Reached maximum cases limit ({MAX_CASES_TO_SCRAPE}). Stopping.")
            break
        
        print(f"[INFO] Processed page {current_page}, total cases so far: {len(case_urls)}")
        
        # Check if this page had any qualifying cases
        if len(qualifying_cases) == 0:
            print(f"[INFO] No qualifying cases found on page {current_page}. Checking next page...")
        
        # Check if this page had any view buttons at all (indicates end of data)
        if len(view_buttons) == 0:
            print(f"[INFO] No view buttons found on page {current_page}. Reached end of data.")
            break
        
        # Check if we've reached the maximum pages limit
        if current_page >= MAX_PAGES_TO_CHECK:
            print(f"[INFO] Reached maximum pages limit ({MAX_PAGES_TO_CHECK}). Stopping.")
            break
            
        # Jump to random page between 20-200
        current_page = random.randint(20, 200)
        print(f"[INFO] Jumping to random page: {current_page}")

    print(f"[INFO] Total cases processed: {len(case_urls)}")

    browser.close()
    
    print(f"\n[COMPLETE] Processing finished!")
    print(f"[COMPLETE] Results saved to: {output_path}")
    print(f"[COMPLETE] Total cases processed: {len(case_urls)}")
    print(f"[COMPLETE] New cases found: {len(case_urls)}")