"""
Main Credit Check Workflow
Orchestrates the complete process: scrape claims → check for credits
"""

import os
import sys
import time
from datetime import datetime

# Configuration variables - modify these as needed
SCRAPING_TIMEOUT = 120  # 2 minutes timeout for claims scraping
CHECKING_TIMEOUT = 120  # 2 minutes timeout for credit checking

# Parse command line arguments for even/odd filtering
CLAIM_TYPE = "even"  # Default to even
if len(sys.argv) > 1:
    CLAIM_TYPE = sys.argv[1].lower()
    if CLAIM_TYPE not in ["even", "odd"]:
        print(f"❌ Invalid claim type: {CLAIM_TYPE}. Must be 'even' or 'odd'")
        sys.exit(1)

print(f"[INFO] Processing {CLAIM_TYPE} claim IDs only")

def clean_csv_files():
    """Delete CSV files to ensure clean slate"""
    csv_files = ["output/cases.csv", "output/cases_checked.csv"]
    
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            try:
                os.remove(csv_file)
                print(f"🗑️ Deleted {csv_file}")
            except Exception as e:
                print(f"⚠️ Could not delete {csv_file}: {e}")
        else:
            print(f"ℹ️ {csv_file} does not exist (already clean)")

def check_files_exist():
    """Check if required files exist"""
    required_files = [
        "claims.py",
        "control.py", 
        "checker.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    return True

def run_claims_scraper():
    """Run the claims scraper to get new claim data"""
    print(f"🔍 Step 1: Scraping claims ({CLAIM_TYPE} IDs)...")
    print("=" * 50)
    
    # Clean CSV files before processing
    print("🧹 Cleaning CSV files for fresh start...")
    clean_csv_files()
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, "claims.py", CLAIM_TYPE], 
                              capture_output=True, text=True, timeout=SCRAPING_TIMEOUT)
        
        if result.returncode == 0:
            print(f"✅ Claims scraping completed successfully ({CLAIM_TYPE} IDs)")
            return True
        else:
            print(f"❌ Claims scraping failed:")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Claims scraping timed out ({SCRAPING_TIMEOUT//60} minute limit)")
        return False
    except Exception as e:
        print(f"❌ Error running claims scraper: {e}")
        return False

def run_credit_checker():
    """Run the credit checker to analyze scraped claims"""
    print("\n🎯 Step 2: Checking credits...")
    print("=" * 50)
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, "control.py"], 
                              capture_output=True, text=True, timeout=CHECKING_TIMEOUT)
        
        if result.returncode == 0:
            print("✅ Credit checking completed successfully")
            return True
        else:
            print(f"❌ Credit checking failed:")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Credit checking timed out ({CHECKING_TIMEOUT//60} minute limit)")
        return False
    except Exception as e:
        print(f"❌ Error running credit checker: {e}")
        return False

def check_results():
    """Check the final results"""
    print("\n📊 Step 3: Checking results...")
    print("=" * 50)
    
    input_csv = "output/cases.csv"
    output_csv = "output/cases_checked.csv"
    overall_csv = "output/overall_checked_claims.csv"
    
    # Check if files exist
    if not os.path.exists(input_csv):
        print(f"❌ Input CSV not found: {input_csv}")
        return False
    
    if not os.path.exists(output_csv):
        print(f"❌ Output CSV not found: {output_csv}")
        return False
    
    if not os.path.exists(overall_csv):
        print(f"⚠️ Overall CSV not found: {overall_csv}")
    
    # Count rows
    try:
        import csv
        
        with open(input_csv, 'r') as f:
            input_rows = sum(1 for _ in csv.reader(f)) - 1  # Subtract header
        
        with open(output_csv, 'r') as f:
            output_rows = sum(1 for _ in csv.reader(f)) - 1  # Subtract header
        
        # Count overall rows if file exists
        overall_rows = 0
        if os.path.exists(overall_csv):
            with open(overall_csv, 'r') as f:
                overall_rows = sum(1 for _ in csv.reader(f)) - 1  # Subtract header
        
        print(f"📈 Results Summary:")
        print(f"   Input cases: {input_rows}")
        print(f"   Processed cases: {output_rows}")
        print(f"   Total in overall: {overall_rows}")
        print(f"   Success rate: {(output_rows/input_rows*100):.1f}%" if input_rows > 0 else "   Success rate: N/A")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking results: {e}")
        return False

def main():
    """Main workflow function"""
    print("🚀 Credit Check Workflow Starting...")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Processing {CLAIM_TYPE} claim IDs only")
    print("=" * 60)
    
    # Check prerequisites
    if not check_files_exist():
        return
    
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)
    
    # Step 1: Scrape claims
    if not run_claims_scraper():
        print("\n❌ Workflow failed at claims scraping step")
        return
    
    # Step 2: Check credits
    if not run_credit_checker():
        print("\n❌ Workflow failed at credit checking step")
        return
    
    # Step 3: Check results
    if not check_results():
        print("\n❌ Workflow completed but results check failed")
        return
    
    # Success
    print("\n🎉 Workflow completed successfully!")
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📁 Check the following files:")
    print("   - output/cases.csv (scraped cases)")
    print("   - output/cases_checked.csv (checked cases)")
    print("   - output/overall_checked_claims.csv (all processed cases)")

if __name__ == "__main__":
    main()
