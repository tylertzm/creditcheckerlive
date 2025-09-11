"""
Automated Scheduler for Credit Check Workflow
- Every hour at :30 - Scrape new claims
- Every hour at :00 - Check credits for hits
"""

import schedule
import time
import subprocess
import sys
import os
from datetime import datetime
import threading
import fcntl

# Global variable to track claim type (even/odd)
current_claim_type = "even"  # Default to even

# Parse command line arguments for initial claim type
if len(sys.argv) > 1:
    initial_type = sys.argv[1].lower()
    if initial_type in ["even", "odd"]:
        current_claim_type = initial_type
        print(f"[INFO] Starting with {current_claim_type} claim IDs")
    else:
        print(f"❌ Invalid claim type: {initial_type}. Must be 'even' or 'odd'")
        print("Usage: python scheduler.py [even|odd]")
        sys.exit(1)

def log_message(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def safe_update_overall_csv(claim_type):
    """Safely update overall_checked_claims.csv with file locking"""
    overall_csv = "output/overall_checked_claims.csv"
    checked_csv = f"output/cases_checked_{claim_type}.csv"
    
    if not os.path.exists(checked_csv):
        log_message(f"⚠️ No checked CSV found for {claim_type}, skipping overall update")
        return
    
    lock_file = f"output/.overall_csv.lock"
    max_wait = 30  # Maximum wait time in seconds
    
    try:
        # Create lock file
        with open(lock_file, 'w') as lock_f:
            # Try to acquire exclusive lock
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            log_message(f"🔒 Acquired lock for overall CSV update ({claim_type})")
            
            # Read existing overall data
            existing_data = []
            if os.path.exists(overall_csv):
                with open(overall_csv, 'r', newline='', encoding='utf-8') as f:
                    import csv
                    reader = csv.DictReader(f)
                    existing_data = list(reader)
            
            # Read new checked data
            new_data = []
            with open(checked_csv, 'r', newline='', encoding='utf-8') as f:
                import csv
                reader = csv.DictReader(f)
                new_data = list(reader)
            
            # Merge data (avoid duplicates)
            existing_case_ids = {row.get('case_id', '') for row in existing_data}
            merged_data = existing_data.copy()
            
            added_count = 0
            for row in new_data:
                if row.get('case_id', '') not in existing_case_ids:
                    merged_data.append(row)
                    added_count += 1
            
            # Write back to overall CSV
            if merged_data:
                with open(overall_csv, 'w', newline='', encoding='utf-8') as f:
                    import csv
                    fieldnames = merged_data[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(merged_data)
                
                log_message(f"✅ Updated overall CSV: +{added_count} new {claim_type} cases")
            else:
                log_message(f"ℹ️ No new {claim_type} cases to add to overall CSV")
            
    except BlockingIOError:
        log_message(f"⏳ Overall CSV is locked by another process, waiting...")
        # Wait for lock to be released
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(1)
            wait_time += 1
            try:
                with open(lock_file, 'w') as lock_f:
                    fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # If we get here, lock is available
                    break
            except BlockingIOError:
                continue
        
        if wait_time >= max_wait:
            log_message(f"❌ Could not acquire lock for overall CSV update ({claim_type}) after {max_wait}s")
            return
        else:
            # Retry the update
            safe_update_overall_csv(claim_type)
    
    except Exception as e:
        log_message(f"❌ Error updating overall CSV ({claim_type}): {e}")
    
    finally:
        # Clean up lock file
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except:
            pass

def clean_csv_files(claim_type):
    """Delete CSV files to ensure clean slate for specific claim type"""
    csv_files = [
        f"output/cases_{claim_type}.csv", 
        f"output/cases_checked_{claim_type}.csv"
    ]
    
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            try:
                os.remove(csv_file)
                log_message(f"🗑️ Deleted {csv_file}")
            except Exception as e:
                log_message(f"⚠️ Could not delete {csv_file}: {e}")
        else:
            log_message(f"ℹ️ {csv_file} does not exist (already clean)")

def run_claims_scraper(claim_type):
    """Run the claims scraper for specific claim type"""
    log_message(f"🔄 Starting scheduled claims scraping ({claim_type} IDs)...")
    
    # Clean CSV files before processing
    log_message(f"🧹 Cleaning CSV files for fresh start ({claim_type})...")
    clean_csv_files(claim_type)
    
    try:
        result = subprocess.run([sys.executable, "claims.py", claim_type], 
                              capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            log_message(f"✅ Claims scraping completed successfully ({claim_type} IDs)")
        else:
            log_message(f"❌ Claims scraping failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        log_message("❌ Claims scraping timed out (5 minute limit)")
    except Exception as e:
        log_message(f"❌ Error running claims scraper: {e}")

def run_credit_checker(claim_type):
    """Run the credit checker for specific claim type"""
    log_message(f"🎯 Starting scheduled credit checking ({claim_type} IDs)...")
    try:
        result = subprocess.run([sys.executable, "control.py", claim_type], 
                              capture_output=True, text=True, timeout=600)  # 10 minute timeout
        
        if result.returncode == 0:
            log_message(f"✅ Credit checking completed successfully ({claim_type} IDs)")
            # Safely update the overall CSV file
            safe_update_overall_csv(claim_type)
        else:
            log_message(f"❌ Credit checking failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        log_message("❌ Credit checking timed out (10 minute limit)")
    except Exception as e:
        log_message(f"❌ Error running credit checker: {e}")

def check_files_exist():
    """Check if required files exist before starting"""
    required_files = ["claims.py", "control.py", "checker.py"]
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        log_message(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    return True

def main():
    """Main scheduler function"""
    log_message("🚀 Credit Check Scheduler Starting...")
    log_message("📅 Schedule:")
    log_message("   - Claims scraping: Even IDs at :30, Odd IDs at :35")
    log_message("   - Credit checking: Even IDs at :00, Odd IDs at :05")
    log_message("🎯 Running both even and odd claim processing simultaneously")
    
    # Check prerequisites
    if not check_files_exist():
        log_message("❌ Prerequisites check failed. Exiting.")
        return
    
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)
    
    # Schedule the jobs - run both even and odd processes separately
    schedule.every().hour.at(":30").do(run_claims_scraper, "even")
    schedule.every().hour.at(":35").do(run_claims_scraper, "odd")
    schedule.every().hour.at(":00").do(run_credit_checker, "even")
    schedule.every().hour.at(":05").do(run_credit_checker, "odd")
    
    # Run initial check to see what's next
    next_claims = schedule.next_run()
    next_credits = schedule.get_jobs()[1].next_run
    log_message(f"⏰ Next claims scraping: {next_claims}")
    log_message(f"⏰ Next credit checking: {next_credits}")
    
    log_message("🔄 Scheduler is now running. Press Ctrl+C to stop.")
    
    # Keep the scheduler running with error handling
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    try:
        while True:
            try:
                schedule.run_pending()
                consecutive_errors = 0  # Reset error counter on success
                time.sleep(60)  # Check every minute
            except Exception as e:
                consecutive_errors += 1
                log_message(f"❌ Scheduler error #{consecutive_errors}: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    log_message(f"❌ Too many consecutive errors ({consecutive_errors}), restarting scheduler...")
                    # Reset error counter and continue
                    consecutive_errors = 0
                    time.sleep(30)  # Wait before continuing
                else:
                    time.sleep(10)  # Short wait before retry
                    
    except KeyboardInterrupt:
        log_message("🛑 Scheduler stopped by user")
    except Exception as e:
        log_message(f"❌ Fatal scheduler error: {e}")
        log_message("🔄 Scheduler will restart in 30 seconds...")
        time.sleep(30)
        # Restart the scheduler
        main()

if __name__ == "__main__":
    main()
