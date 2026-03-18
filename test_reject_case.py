"""
Test script to reject case 1799177 with a comment
"""
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add library to path
sys.path.insert(0, '/root/creditcheckerlive')
from library.unified_driver_utils import setup_driver
from library.upload_utils import reject_case_with_comment


def test_reject_case_1799177():
    """Test rejecting case 1799177"""
    
    print("=" * 60)
    print("TEST: Reject Case 1799177")
    print("=" * 60)
    
    # Setup driver
    driver = setup_driver(headless=False)  # Set to False to see the browser
    
    try:
        case_url = "https://app.copytrack.com/admin/claim/1799177"
        print(f"[INFO] Navigating to case: {case_url}")
        driver.get(case_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("[INFO] ✅ Case page loaded")
        time.sleep(2)
        
        # Call the rejection function
        success = reject_case_with_comment(
            driver, 
            comment_text="credit found by credit checker tool"
        )
        
        if success:
            print("\n" + "=" * 60)
            print("✅ TEST PASSED: Case 1799177 rejected successfully!")
            print("=" * 60)
            time.sleep(5)  # Keep browser open for inspection
        else:
            print("\n" + "=" * 60)
            print("❌ TEST FAILED: Case rejection failed")
            print("=" * 60)
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(5)
        
    finally:
        driver.quit()
        print("[INFO] Browser closed")


if __name__ == "__main__":
    test_reject_case_1799177()
