"""
Rejection tracker to avoid duplicate rejections.
Tracks cases rejected today and cleans up after midnight.
"""

import os
import csv
from datetime import datetime


class RejectionTracker:
    """Tracks rejected cases for today to avoid duplicate rejections"""
    
    def __init__(self, tracker_file='/app/data/rejected_today.csv'):
        """Initialize tracker with file path"""
        self.tracker_file = tracker_file
        self.rejected_cases = set()
        self._load_rejected_cases()
        self._cleanup_if_new_day()
    
    def _load_rejected_cases(self):
        """Load already rejected cases from CSV"""
        if not os.path.exists(self.tracker_file):
            return
        
        try:
            with open(self.tracker_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.rejected_cases.add(row['case_id'])
            print(f"[INFO] 📋 Loaded {len(self.rejected_cases)} already-rejected cases from tracker")
        except Exception as e:
            print(f"[WARNING] ⚠️  Could not load rejection tracker: {e}")
    
    def _cleanup_if_new_day(self):
        """Clean up tracker file if it's a new day"""
        if not os.path.exists(self.tracker_file):
            return
        
        try:
            # Check the date of the first entry
            with open(self.tracker_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                first_row = next(reader, None)
                
                if first_row and 'date' in first_row:
                    tracker_date = first_row['date']
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    if tracker_date != today:
                        print(f"[INFO] 🧹 Cleaning up old rejection tracker (was {tracker_date}, now {today})")
                        self._reset_tracker()
                        self.rejected_cases.clear()
        except Exception as e:
            print(f"[WARNING] ⚠️  Could not check tracker date: {e}")
    
    def _reset_tracker(self):
        """Reset the tracker file"""
        try:
            with open(self.tracker_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['case_id', 'rejection_timestamp', 'date'])
                writer.writeheader()
            print("[INFO] ✅ Tracker file reset")
        except Exception as e:
            print(f"[ERROR] ❌ Could not reset tracker: {e}")
    
    def is_already_rejected(self, case_id):
        """Check if a case was already rejected today"""
        return case_id in self.rejected_cases
    
    def mark_as_rejected(self, case_id):
        """Mark a case as rejected in the tracker"""
        if case_id in self.rejected_cases:
            return  # Already tracked
        
        try:
            # Add to memory
            self.rejected_cases.add(case_id)
            
            # Append to file
            now = datetime.now()
            with open(self.tracker_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['case_id', 'rejection_timestamp', 'date'])
                
                # Write header if file is empty
                if os.path.getsize(self.tracker_file) == 0:
                    writer.writeheader()
                
                writer.writerow({
                    'case_id': case_id,
                    'rejection_timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
                    'date': now.strftime('%Y-%m-%d')
                })
        except Exception as e:
            print(f"[WARNING] ⚠️  Could not track rejection for {case_id}: {e}")
    
    def get_rejected_count(self):
        """Get count of rejected cases today"""
        return len(self.rejected_cases)
