#!/usr/bin/env python3
"""
Test script to verify ChromeDriver installation and compatibility
"""

import os
import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def check_chrome_installation():
    """Check if Chrome is installed and get version"""
    print("🔍 Checking Chrome installation...")
    
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable", 
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser"
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            try:
                result = subprocess.run([chrome_path, "--version"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ Found Chrome: {chrome_path}")
                    print(f"   Version: {result.stdout.strip()}")
                    return chrome_path
            except Exception as e:
                print(f"❌ Error checking {chrome_path}: {e}")
    
    print("❌ No Chrome installation found")
    return None

def check_chromedriver_installation():
    """Check if ChromeDriver is installed and get version"""
    print("\n🔍 Checking ChromeDriver installation...")
    
    chromedriver_paths = [
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromedriver", 
        "/usr/bin/chromium-driver"
    ]
    
    working_drivers = []
    
    for driver_path in chromedriver_paths:
        print(f"🔍 Checking: {driver_path}")
        
        if os.path.exists(driver_path):
            try:
                # Check if file is executable
                if os.access(driver_path, os.X_OK):
                    print(f"   ✅ File exists and is executable")
                    
                    # Get version
                    result = subprocess.run([driver_path, "--version"], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        print(f"   ✅ Version: {version}")
                        working_drivers.append((driver_path, version))
                    else:
                        print(f"   ❌ Failed to get version: {result.stderr}")
                else:
                    print(f"   ❌ File exists but is not executable")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            print(f"   ❌ File does not exist")
    
    return working_drivers

def test_selenium_webdriver():
    """Test if Selenium can create a WebDriver instance"""
    print("\n🔍 Testing Selenium WebDriver creation...")
    
    # Configure Chrome options for headless operation
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Try each ChromeDriver path
    chromedriver_paths = [
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromedriver", 
        "/usr/bin/chromium-driver"
    ]
    
    for driver_path in chromedriver_paths:
        if os.path.exists(driver_path):
            try:
                print(f"🔍 Testing WebDriver with: {driver_path}")
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Test basic functionality
                driver.get("https://www.google.com")
                title = driver.title
                driver.quit()
                
                print(f"   ✅ SUCCESS! WebDriver works with {driver_path}")
                print(f"   ✅ Successfully loaded Google, title: {title}")
                return driver_path
                
            except Exception as e:
                print(f"   ❌ FAILED with {driver_path}: {e}")
    
    print("❌ No working ChromeDriver found for Selenium")
    return None

def check_system_architecture():
    """Check system architecture"""
    print("\n🔍 Checking system architecture...")
    
    try:
        # Check Python platform
        import platform
        print(f"✅ Python platform: {platform.platform()}")
        print(f"✅ Python architecture: {platform.architecture()}")
        print(f"✅ Machine type: {platform.machine()}")
        
        # Check dpkg architecture (if available)
        try:
            result = subprocess.run(["dpkg", "--print-architecture"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ dpkg architecture: {result.stdout.strip()}")
        except:
            pass
            
        # Check uname
        try:
            result = subprocess.run(["uname", "-m"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ uname -m: {result.stdout.strip()}")
        except:
            pass
            
    except Exception as e:
        print(f"❌ Error checking architecture: {e}")

def main():
    """Main test function"""
    print("🚀 ChromeDriver Installation Test")
    print("=" * 50)
    
    # Check system architecture
    check_system_architecture()
    
    # Check Chrome installation
    chrome_path = check_chrome_installation()
    
    # Check ChromeDriver installation
    working_drivers = check_chromedriver_installation()
    
    # Test Selenium WebDriver
    working_selenium_driver = test_selenium_webdriver()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    
    if chrome_path:
        print(f"✅ Chrome: {chrome_path}")
    else:
        print("❌ Chrome: Not found")
    
    if working_drivers:
        print(f"✅ ChromeDriver: {len(working_drivers)} working driver(s) found")
        for path, version in working_drivers:
            print(f"   - {path}: {version}")
    else:
        print("❌ ChromeDriver: No working drivers found")
    
    if working_selenium_driver:
        print(f"✅ Selenium: Works with {working_selenium_driver}")
    else:
        print("❌ Selenium: Cannot create WebDriver instance")
    
    # Overall status
    if chrome_path and working_drivers and working_selenium_driver:
        print("\n🎉 ALL TESTS PASSED! ChromeDriver setup is working correctly.")
        return 0
    else:
        print("\n❌ TESTS FAILED! ChromeDriver setup needs attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
