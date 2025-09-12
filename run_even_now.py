#!/usr/bin/env python3
"""
Quick script to run even cases immediately - ONLY 10 CLAIMS
"""
import subprocess
import sys
import os
from datetime import datetime

def log_message(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def run_even_cases_limited():
    """Run even cases immediately - scrape ONLY 10 claims then check credits"""
    log_message("🚀 Starting immediate even cases processing (LIMITED TO 10 CLAIMS)...")
    
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)
    
    # Step 1: Create a custom claims script that only scrapes 10 cases
    log_message("🔄 Step 1: Creating custom limited claims scraper...")
    
    # Read the original claims.py and modify it
    with open("claims.py", "r") as f:
        claims_content = f.read()
    
    # Replace the MAX_CASES_TO_SCRAPE value
    modified_content = claims_content.replace(
        "MAX_CASES_TO_SCRAPE = 300",
        "MAX_CASES_TO_SCRAPE = 10"
    )
    
    # Write the modified version
    with open("claims_limited.py", "w") as f:
        f.write(modified_content)
    
    log_message("✅ Created limited claims scraper (10 cases max)")
    
    # Step 2: Run limited claims scraping
    log_message("🔄 Step 2: Scraping 10 even claims...")
    try:
        result = subprocess.run([sys.executable, "claims_limited.py", "even"], 
                              capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            log_message("✅ Limited claims scraping completed successfully")
            if result.stdout:
                print("STDOUT:", result.stdout[-1000:])  # Show last 1000 chars
        else:
            log_message("❌ Limited claims scraping failed")
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        log_message("⏰ Claims scraping timed out after 10 minutes")
        return False
    except Exception as e:
        log_message(f"❌ Error running claims scraper: {e}")
        return False
    
    # Step 3: Check if we got data
    cases_csv = "output/cases_even.csv"
    if not os.path.exists(cases_csv):
        log_message("❌ No cases CSV found, cannot proceed with credit checking")
        return False
    
    try:
        with open(cases_csv, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) <= 1:
                log_message("❌ Cases CSV is empty, cannot proceed with credit checking")
                return False
        log_message(f"✅ Found {len(lines)-1} cases to check")
    except Exception as e:
        log_message(f"❌ Error reading cases CSV: {e}")
        return False
    
    # Step 4: Run credit checking
    log_message("🎯 Step 3: Running credit checking for even cases...")
    try:
        result = subprocess.run([sys.executable, "control.py", "even"], 
                              capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            log_message("✅ Credit checking completed successfully")
            if result.stdout:
                print("STDOUT:", result.stdout[-1000:])  # Show last 1000 chars
            return True
        else:
            log_message("❌ Credit checking failed")
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        log_message("⏰ Credit checking timed out after 10 minutes")
        return False
    except Exception as e:
        log_message(f"❌ Error running credit checker: {e}")
        return False

if __name__ == "__main__":
    success = run_even_cases_limited()
    if success:
        log_message("🎉 Limited even cases processing (10 claims) completed successfully!")
    else:
        log_message("❌ Limited even cases processing failed!")
        sys.exit(1)
