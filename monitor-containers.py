#!/usr/bin/env python3
"""
Container Monitor Script
Monitors daily CSV file activity and restarts containers if no activity for 10 minutes
"""

import os
import time
import subprocess
import datetime
from pathlib import Path

# Configuration
CHECK_INTERVAL = 60  # Check every 60 seconds
INACTIVITY_THRESHOLD = 600  # 10 minutes in seconds
DAILY_CSV_PATTERN = "daily_claims_*.csv"

def get_latest_daily_csv():
    """Get the most recent daily CSV file"""
    csv_files = list(Path(".").glob(DAILY_CSV_PATTERN))
    if not csv_files:
        return None
    
    # Sort by modification time and get the most recent
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    return latest_file

def get_file_last_modified(file_path):
    """Get the last modification time of a file"""
    if not file_path or not file_path.exists():
        return None
    return file_path.stat().st_mtime

def is_container_running():
    """Check if dual scraping containers are running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=credit-checker-even", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
        even_running = "credit-checker-even" in result.stdout
        
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=credit-checker-odd", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
        odd_running = "credit-checker-odd" in result.stdout
        
        return even_running and odd_running
    except Exception as e:
        print(f"[ERROR] Failed to check container status: {e}")
        return False

def restart_containers():
    """Restart the dual scraping containers"""
    try:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Restarting containers due to inactivity...")
        
        # Run the restart command
        result = subprocess.run(
            ["./run-dual-scraping.sh", "restart"],
            capture_output=True, text=True, timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Containers restarted successfully")
            return True
        else:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Failed to restart containers: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Restart command timed out")
        return False
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error restarting containers: {e}")
        return False

def monitor_activity():
    """Main monitoring loop"""
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Starting container monitor...")
    print(f"[INFO] Check interval: {CHECK_INTERVAL} seconds")
    print(f"[INFO] Inactivity threshold: {INACTIVITY_THRESHOLD} seconds ({INACTIVITY_THRESHOLD//60} minutes)")
    
    last_activity_time = None
    last_restart_time = 0
    
    while True:
        try:
            current_time = time.time()
            
            # Get the latest daily CSV file
            latest_csv = get_latest_daily_csv()
            
            if not latest_csv:
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ No daily CSV files found, waiting...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Get the last modification time of the CSV file
            last_modified = get_file_last_modified(latest_csv)
            
            if last_modified is None:
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Could not get modification time for {latest_csv}")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Check if containers are running
            if not is_container_running():
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Containers not running, attempting restart...")
                restart_containers()
                last_restart_time = current_time
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Check for activity
            time_since_activity = current_time - last_modified
            
            if last_activity_time != last_modified:
                # File was modified since last check
                last_activity_time = last_modified
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Activity detected in {latest_csv} ({time_since_activity:.0f}s ago)")
            else:
                # No new activity
                if time_since_activity > INACTIVITY_THRESHOLD:
                    # Check if we haven't restarted too recently (avoid restart loops)
                    time_since_restart = current_time - last_restart_time
                    if time_since_restart > INACTIVITY_THRESHOLD:
                        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ No activity for {time_since_activity:.0f}s in {latest_csv}")
                        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Restarting containers...")
                        
                        if restart_containers():
                            last_restart_time = current_time
                            last_activity_time = None  # Reset to detect new activity after restart
                        else:
                            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Restart failed, will retry in {CHECK_INTERVAL}s")
                    else:
                        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏳ No activity for {time_since_activity:.0f}s, but restarted recently ({time_since_restart:.0f}s ago)")
                else:
                    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 Monitoring {latest_csv} - last activity {time_since_activity:.0f}s ago")
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🛑 Monitor stopped by user")
            break
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error in monitor loop: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor_activity()
