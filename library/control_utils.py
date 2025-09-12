"""
Control utilities for processing CSV files and managing credit checking workflows
"""

import csv
import re
import os
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


def normalize_image_url(url: str) -> str:
    """
    Normalize image URLs:
    - Strip whitespace
    - Ensure scheme is present
    - Remove path-based size segments (e.g., /400x800/)
    - Remove filename size suffixes (e.g., _400x800 or -768x512)
    - Remove query parameters related to size/format
    """
    if not url:
        return url

    url = url.strip()
    parsed = urlparse(url)

    scheme = parsed.scheme or "https"
    netloc = parsed.netloc
    path = parsed.path

    # Remove path segments like /400x800/
    path = re.sub(r'/\d+x\d+/', '/', path)

    # Remove filename suffixes like _400x800 or -768x512
    path = re.sub(r'[_-](\d+)x(\d+)(?=\.[a-zA-Z]+$)', '', path)

    # Remove query parameters related to size or format
    query = parse_qs(parsed.query)
    for param in ["w", "h", "width", "height", "format", "q"]:
        query.pop(param, None)
    query_string = urlencode(query, doseq=True)

    normalized_url = urlunparse((scheme, netloc, path, "", query_string, ""))
    return normalized_url


def process_hits(input_csv, output_csv, check_image_credits_func):
    """
    Read the input CSV, process each hit with check_image_credits,
    and write results to an output CSV including image detection,
    credit keywords, and error statuses.
    """
    # Check if input CSV exists
    if not os.path.exists(input_csv):
        print(f"Input CSV '{input_csv}' not found. Please ensure the file exists.")
        return
    
    # Read input CSV
    with open(input_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames + ["image_found", "keyword_found", "keywords_list", "keyword_highlight", "error_status"]
        rows = list(reader)

    # Load already processed hits from output CSV if it exists
    processed_hits = set()
    existing_results = {}
    if os.path.exists(output_csv):
        with open(output_csv, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                case_id = row.get('case_id')
                hit_number = row.get('hit_number')
                error_status = row.get('error_status', '')
                
                # Consider a hit processed if it has any error_status (including "Success")
                if case_id and hit_number and error_status:
                    hit_key = (case_id, hit_number)
                    processed_hits.add(hit_key)
                    existing_results[hit_key] = row
        
        print(f"Found {len(processed_hits)} already processed hits. Skipping these...")
    else:
        print("No existing output CSV found. Processing all hits...")
    
    # Filter out already processed hits
    unprocessed_rows = []
    for row in rows:
        case_id = row.get('case_id')
        hit_number = row.get('hit_number')
        hit_key = (case_id, hit_number)
        
        if hit_key not in processed_hits:
            unprocessed_rows.append(row)
        else:
            print(f"Skipping already processed hit: case {case_id}, hit {hit_number}")
    
    print(f"Processing {len(unprocessed_rows)} unprocessed hits out of {len(rows)} total hits")

    # Write output CSV incrementally - start with existing results and add new ones as processed
    with open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        
        # First write all existing results, then process new ones incrementally
        for row in rows:
            case_id = row.get('case_id')
            hit_number = row.get('hit_number')
            hit_key = (case_id, hit_number)
            
            if hit_key in processed_hits:
                # Write existing result immediately
                existing_row = existing_results[hit_key]
                writer.writerow(existing_row)
                f_out.flush()  # Ensure data is written to disk
            else:
                # Process this row
                # Normalize image URL and get page URL
                target_image_url = normalize_image_url(row.get("image_url"))
                page_url = row.get("page_url")

                # Debug logging for missing data
                print(f"[DEBUG] Row data: case_id={row.get('case_id')}, hit_number={row.get('hit_number')}")
                print(f"[DEBUG] image_url='{row.get('image_url')}' -> normalized='{target_image_url}'")
                print(f"[DEBUG] page_url='{row.get('page_url')}'")

                # Handle missing data
                if not target_image_url or not page_url:
                    print(f"[ERROR] Missing data - target_image_url: {bool(target_image_url)}, page_url: {bool(page_url)}")
                    row.update({
                        "image_found": False,
                        "keyword_found": False,
                        "keywords_list": "",
                        "keyword_highlight": "",
                        "error_status": "Missing URL data"
                    })
                    writer.writerow(row)
                    f_out.flush()
                    continue

                try:
                    # Check image credits using the provided function
                    # Pass case information for overall CSV logging
                    case_id = row.get("case_id", "")
                    case_url = row.get("case_url", "")
                    hit_number = row.get("hit_number", "")
                    
                    results = check_image_credits_func(
                        target_image_url, 
                        page_url, 
                        case_url=case_url, 
                        hit_id=hit_number
                    )

                    row["image_found"] = results.get("image_found", False)
                    row["keyword_found"] = bool(results.get("credit_keywords"))
                    row["keywords_list"] = ", ".join(results.get("credit_keywords", []))
                    # Only set highlight_link if keywords were found, otherwise leave blank
                    if results.get("credit_keywords"):
                        row["keyword_highlight"] = results.get("highlight_url", "")
                    else:
                        row["keyword_highlight"] = ""

                    # Error handling
                    error_msg = results.get("error", "")
                    if error_msg:
                        if "404" in error_msg or "Not Found" in error_msg or "Page title indicates error" in error_msg:
                            row["error_status"] = "404 - Page Not Found"
                        elif "timeout" in error_msg.lower():
                            row["error_status"] = "Timeout Error"
                        elif "connection" in error_msg.lower():
                            row["error_status"] = "Connection Error"
                        elif "Browser session failed" in error_msg:
                            row["error_status"] = "Browser Session Error"
                        elif "Image not found" in error_msg:
                            row["error_status"] = "Image Not Found"
                        else:
                            row["error_status"] = f"Error: {error_msg}"
                    else:
                        row["error_status"] = "Success"

                except Exception as e:
                    # Catch unexpected exceptions per row
                    row.update({
                        "image_found": False,
                        "keyword_found": False,
                        "keywords_list": "",
                        "keyword_highlight": "",
                        "error_status": f"Unexpected Error: {e}"
                    })

                # Write result immediately after processing
                writer.writerow(row)
                f_out.flush()  # Ensure data is written to disk immediately
                print(f"Processed case {row.get('case_id')}, hit {row.get('hit_number')} -> "
                      f"image_found={row['image_found']}, keyword_found={row['keyword_found']}, "
                      f"keywords={row['keywords_list']}, status={row['error_status']}")

    print(f"\nProcessing complete. Results saved to {output_csv}")


def reprocess_error_rows(output_csv, check_image_credits_func):
    """
    Reprocess only the rows that have "Error: list index out of range" status
    to see if the zalando.py fix resolved the issue.
    """
    # Check if output CSV exists, if not create it first
    if not os.path.exists(output_csv):
        print(f"Output CSV '{output_csv}' not found. Creating it first by processing all hits...")
        # This would need to be called with proper parameters
        return
    
    # Read the current output CSV
    with open(output_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Filter rows that need reprocessing
    error_rows = [row for row in rows if "list index out of range" in row.get("error_status", "")]
    
    if not error_rows:
        print("No rows with 'list index out of range' errors found.")
        return

    print(f"Found {len(error_rows)} rows with 'list index out of range' errors. Reprocessing...")

    # Reprocess error rows
    updated_rows = []
    for i, row in enumerate(rows):
        if "list index out of range" in row.get("error_status", ""):
            print(f"\nReprocessing row {i+1}: case {row.get('case_id')}, hit {row.get('hit_number')}")
            
            # Normalize image URL and get page URL
            target_image_url = normalize_image_url(row.get("image_url"))
            page_url = row.get("page_url")

            # Handle missing data
            if not target_image_url or not page_url:
                row.update({
                    "image_found": False,
                    "keyword_found": False,
                    "keywords_list": "",
                    "keyword_highlight": "",
                    "error_status": "Missing URL data"
                })
                updated_rows.append(row)
                continue

            try:
                # Check image credits using the provided function
                # Pass case information for overall CSV logging
                case_id = row.get("case_id", "")
                case_url = row.get("case_url", "")
                hit_number = row.get("hit_number", "")
                
                results = check_image_credits_func(
                    target_image_url, 
                    page_url, 
                    case_url=case_url, 
                    hit_id=hit_number
                )

                row["image_found"] = results.get("image_found", False)
                row["keyword_found"] = bool(results.get("credit_keywords"))
                row["keywords_list"] = ", ".join(results.get("credit_keywords", []))
                # Only set highlight_link if keywords were found, otherwise leave blank
                if results.get("credit_keywords"):
                    row["keyword_highlight"] = results.get("highlight_url", "")
                else:
                    row["keyword_highlight"] = ""

                # Error handling
                error_msg = results.get("error", "")
                if error_msg:
                    if "404" in error_msg or "Not Found" in error_msg or "Page title indicates error" in error_msg:
                        row["error_status"] = "404 - Page Not Found"
                    elif "timeout" in error_msg.lower():
                        row["error_status"] = "Timeout Error"
                    elif "connection" in error_msg.lower():
                        row["error_status"] = "Connection Error"
                    elif "Browser session failed" in error_msg:
                        row["error_status"] = "Browser Session Error"
                    elif "Image not found" in error_msg:
                        row["error_status"] = "Image Not Found"
                    else:
                        row["error_status"] = f"Error: {error_msg}"
                else:
                    row["error_status"] = "Success"

            except Exception as e:
                # Catch unexpected exceptions per row
                row.update({
                    "image_found": False,
                    "keyword_found": False,
                    "keywords_list": "",
                    "keyword_highlight": "",
                    "error_status": f"Unexpected Error: {e}"
                })

            print(f"Reprocessed -> image_found={row['image_found']}, keyword_found={row['keyword_found']}, "
                  f"keywords={row['keywords_list']}, status={row['error_status']}")
        
        updated_rows.append(row)

    # Write the updated CSV back
    with open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"\nReprocessing complete. Updated CSV saved to {output_csv}")


def reprocess_no_keyword_hits(output_csv, check_image_credits_func):
    """
    Reprocess only the rows that have successful status but no keywords found.
    This is useful when you've improved the keyword detection algorithm and want
    to re-check images that previously showed no credits.
    """
    # Check if output CSV exists
    if not os.path.exists(output_csv):
        print(f"Output CSV '{output_csv}' not found. Creating it first by processing all hits...")
        # This would need to be called with proper parameters
        return
    
    # Read the current output CSV
    with open(output_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Filter rows that need reprocessing: hits where image was found but no keywords detected
    no_keyword_rows = [
        row for row in rows 
        if (row.get("image_found", "").lower() == "true" and
            row.get("keyword_found", "").lower() == "false")
    ]
    
    if not no_keyword_rows:
        print("No hits with found images but missing keywords.")
        return

    print(f"Found {len(no_keyword_rows)} hits with images found but no keywords detected. Reprocessing with enhanced detection...")

    # Reprocess no-keyword rows
    updated_rows = []
    reprocessed_count = 0
    newly_found_keywords = 0
    
    for i, row in enumerate(rows):
        # Check if this row needs reprocessing
        should_reprocess = (
            row.get("image_found", "").lower() == "true" and
            row.get("keyword_found", "").lower() == "false"
        )
        
        if should_reprocess:
            reprocessed_count += 1
            print(f"\nReprocessing {reprocessed_count}/{len(no_keyword_rows)}: case {row.get('case_id')}, hit {row.get('hit_number')}")
            
            # Normalize image URL and get page URL
            target_image_url = normalize_image_url(row.get("image_url"))
            page_url = row.get("page_url")

            # Handle missing data
            if not target_image_url or not page_url:
                row.update({
                    "image_found": False,
                    "keyword_found": False,
                    "keywords_list": "",
                    "keyword_highlight": "",
                    "error_status": "Missing URL data"
                })
                updated_rows.append(row)
                continue

            try:
                # Check image credits using enhanced detection (viewport + OCR)
                # Pass case information for overall CSV logging
                case_id = row.get("case_id", "")
                case_url = row.get("case_url", "")
                hit_number = row.get("hit_number", "")
                
                results = check_image_credits_func(
                    target_image_url, 
                    page_url, 
                    case_url=case_url, 
                    hit_id=hit_number
                )

                # Store previous values for comparison
                previous_keywords = row.get("keywords_list", "")
                
                row["image_found"] = results.get("image_found", False)
                row["keyword_found"] = bool(results.get("credit_keywords"))
                row["keywords_list"] = ", ".join(results.get("credit_keywords", []))
                # Only set highlight_link if keywords were found, otherwise leave blank
                if results.get("credit_keywords"):
                    row["keyword_highlight"] = results.get("highlight_url", "")
                else:
                    row["keyword_highlight"] = ""

                # Check if we found new keywords
                if row["keyword_found"] and not previous_keywords:
                    newly_found_keywords += 1
                    print(f"✅ NEW KEYWORDS FOUND: {row['keywords_list']}")
                elif row["keyword_found"]:
                    print(f"✅ Keywords confirmed: {row['keywords_list']}")
                else:
                    print("   No keywords found (confirmed clean)")

                # Error handling
                error_msg = results.get("error", "")
                if error_msg:
                    if "404" in error_msg or "Not Found" in error_msg or "Page title indicates error" in error_msg:
                        row["error_status"] = "404 - Page Not Found"
                    elif "timeout" in error_msg.lower():
                        row["error_status"] = "Timeout Error"
                    elif "connection" in error_msg.lower():
                        row["error_status"] = "Connection Error"
                    elif "Browser session failed" in error_msg:
                        row["error_status"] = "Browser Session Error"
                    elif "Image not found" in error_msg:
                        row["error_status"] = "Image Not Found"
                    else:
                        row["error_status"] = f"Error: {error_msg}"
                else:
                    row["error_status"] = "Success (Reprocessed)"

            except Exception as e:
                # Catch unexpected exceptions per row
                row.update({
                    "image_found": False,
                    "keyword_found": False,
                    "keywords_list": "",
                    "keyword_highlight": "",
                    "error_status": f"Unexpected Error: {e}"
                })
        
        updated_rows.append(row)

    # Write the updated CSV back
    with open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"\n🎉 Reprocessing complete!")
    print(f"   Reprocessed: {reprocessed_count} hits")
    print(f"   New keywords found: {newly_found_keywords} hits")
    print(f"   Updated CSV saved to {output_csv}")


def reprocess_all_successful_hits(output_csv, check_image_credits_func):
    """
    Reprocess ALL successful hits (with and without keywords) to take advantage
    of improved detection algorithms.
    """
    # Check if output CSV exists
    if not os.path.exists(output_csv):
        print(f"Output CSV '{output_csv}' not found. Creating it first by processing all hits...")
        # This would need to be called with proper parameters
        return
    
    # Read the current output CSV
    with open(output_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Filter rows that need reprocessing: all hits where images were found
    successful_rows = [
        row for row in rows 
        if row.get("image_found", "").lower() == "true"
    ]
    
    if not successful_rows:
        print("No hits with found images to reprocess.")
        return

    print(f"Found {len(successful_rows)} hits with found images. Reprocessing all with enhanced detection...")

    # Reprocess successful rows
    updated_rows = []
    reprocessed_count = 0
    improved_results = 0
    
    for i, row in enumerate(rows):
        # Check if this row needs reprocessing
        should_reprocess = row.get("image_found", "").lower() == "true"
        
        if should_reprocess:
            reprocessed_count += 1
            print(f"\nReprocessing {reprocessed_count}/{len(successful_rows)}: case {row.get('case_id')}, hit {row.get('hit_number')}")
            
            # Store previous values for comparison
            previous_keywords = row.get("keywords_list", "")
            previous_keyword_found = row.get("keyword_found", "").lower() == "true"
            
            # Normalize image URL and get page URL
            target_image_url = normalize_image_url(row.get("image_url"))
            page_url = row.get("page_url")

            try:
                # Check image credits using enhanced detection (viewport + OCR)
                results = check_image_credits_func(target_image_url, page_url)

                row["image_found"] = results.get("image_found", False)
                row["keyword_found"] = bool(results.get("credit_keywords"))
                row["keywords_list"] = ", ".join(results.get("credit_keywords", []))
                # Only set highlight_link if keywords were found, otherwise leave blank
                if results.get("credit_keywords"):
                    row["keyword_highlight"] = results.get("highlight_url", "")
                else:
                    row["keyword_highlight"] = ""

                # Check if results improved
                if row["keyword_found"] and not previous_keyword_found:
                    improved_results += 1
                    print(f"✅ NEW KEYWORDS FOUND: {row['keywords_list']}")
                elif row["keyword_found"] and previous_keywords != row["keywords_list"]:
                    improved_results += 1
                    print(f"🔄 KEYWORDS UPDATED: {previous_keywords} → {row['keywords_list']}")
                elif row["keyword_found"]:
                    print(f"✅ Keywords confirmed: {row['keywords_list']}")
                else:
                    print("   No keywords found")

                # Error handling
                error_msg = results.get("error", "")
                if error_msg:
                    if "404" in error_msg or "Not Found" in error_msg or "Page title indicates error" in error_msg:
                        row["error_status"] = "404 - Page Not Found"
                    elif "timeout" in error_msg.lower():
                        row["error_status"] = "Timeout Error"
                    elif "connection" in error_msg.lower():
                        row["error_status"] = "Connection Error"
                    elif "Browser session failed" in error_msg:
                        row["error_status"] = "Browser Session Error"
                    elif "Image not found" in error_msg:
                        row["error_status"] = "Image Not Found"
                    else:
                        row["error_status"] = f"Error: {error_msg}"
                else:
                    row["error_status"] = "Success (Reprocessed)"

            except Exception as e:
                # Catch unexpected exceptions per row
                row.update({
                    "image_found": False,
                    "keyword_found": False,
                    "keywords_list": "",
                    "keyword_highlight": "",
                    "error_status": f"Unexpected Error: {e}"
                })
        
        updated_rows.append(row)

    # Write the updated CSV back
    with open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"\n🎉 Reprocessing complete!")
    print(f"   Reprocessed: {reprocessed_count} hits")
    print(f"   Improved results: {improved_results} hits")
    print(f"   Updated CSV saved to {output_csv}")
