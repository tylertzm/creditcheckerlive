"""
Control module for processing CSV files
"""

import os
import sys
from library import process_hits
from checker import check_image_credits_with_timeout

# Parse command line arguments for even/odd filtering
CLAIM_TYPE = "even"  # Default to even
if len(sys.argv) > 1:
    CLAIM_TYPE = sys.argv[1].lower()
    if CLAIM_TYPE not in ["even", "odd"]:
        print(f"❌ Invalid claim type: {CLAIM_TYPE}. Must be 'even' or 'odd'")
        sys.exit(1)

print(f"[INFO] Processing {CLAIM_TYPE} claim IDs only")

# Configuration variables - modify these as needed
INPUT_CSV = f"output/cases_{CLAIM_TYPE}.csv"  # Input: cases from claims.py (even/odd specific)
OUTPUT_CSV = f"output/cases_checked_{CLAIM_TYPE}.csv"  # Output: checked cases (even/odd specific)
OVERALL_CSV = "output/overall_checked_claims.csv"  # Overall results (shared)

# Processing limits (set to None for no limit)
MAX_HITS_TO_PROCESS = 100 # Maximum number of hits to process (None = no limit)
BATCH_SIZE = 100  # Process hits in batches of this size (for memory management)

# Ensure output directory exists
os.makedirs("output", exist_ok=True)


def main():
    """Main function for processing hits"""
    print("Processing hits from cases.csv...")
    process_hits(INPUT_CSV, OUTPUT_CSV, check_image_credits_with_timeout)
    
    # Also update the overall_checked_claims.csv
    print("Updating overall_checked_claims.csv...")
    # The checker.py already handles this automatically


if __name__ == "__main__":
    main()
