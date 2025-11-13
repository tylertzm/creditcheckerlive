"""
Unified ChromeDriver Setup for Production
========================================

This module provides a single, reliable way to set up ChromeDriver across all components
of the credit checking system. It handles both Docker and local environments automatically.

Features:
- Environment detection (Docker vs local)
- Architecture compatibility (x86_64, ARM64)
- Proper fallback mechanisms
- Comprehensive error handling
- Production-ready logging
"""

import os
import sys
import time
import platform
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException

def detect_environment():
    """Detect if we're running in Docker or local environment"""
    # Check for Docker indicators
    docker_indicators = [
        os.path.exists('/.dockerenv'),
        os.path.exists('/proc/1/cgroup') and any('docker' in line for line in open('/proc/1/cgroup', 'r').readlines()),
        os.environ.get('DOCKER_CONTAINER') == 'true'
    ]
    
    is_docker = any(docker_indicators)
    return 'docker' if is_docker else 'local'

def get_system_info():
    """Get comprehensive system information for debugging"""
    info = {
        'environment': detect_environment(),
        'platform': platform.platform(),
        'architecture': platform.architecture(),
        'machine': platform.machine(),
        'python_version': sys.version
    }
    
    # Add Docker-specific info
    try:
        result = subprocess.run(['dpkg', '--print-architecture'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info['dpkg_arch'] = result.stdout.strip()
    except:
        pass
    
    return info

def find_chrome_binary():
    """Find the Chrome binary for the current environment"""
    chrome_paths = [
        # macOS paths
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        # Linux/Docker paths
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/opt/google/chrome/chrome',  # Alternative Docker location
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path) and os.access(chrome_path, os.X_OK):
            try:
                # Test that Chrome can be executed
                result = subprocess.run([chrome_path, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return chrome_path
            except:
                continue
    
    return None

def find_chromedriver():
    """Find a working ChromeDriver binary"""
    env = detect_environment()
    
    # Priority order: system first, then webdriver-manager locations
    if env == 'docker':
        chromedriver_paths = [
            '/usr/bin/chromedriver',           # Primary Ubuntu package location
            '/usr/local/bin/chromedriver',     # Symlink location
            '/usr/bin/chromium-driver',        # Alternative name
            '/opt/chromedriver/chromedriver',  # Custom installation
        ]
    else:
        chromedriver_paths = [
            '/usr/local/bin/chromedriver',     # Homebrew on macOS
            '/usr/bin/chromedriver',           # Linux package manager
            '/opt/homebrew/bin/chromedriver',  # Apple Silicon Homebrew
            # Additional macOS paths
            '/Applications/Google Chrome.app/Contents/MacOS/chromedriver',
            '/usr/local/share/chromedriver',
            '/opt/homebrew/share/chromedriver',
        ]
    
    working_drivers = []
    
    for driver_path in chromedriver_paths:
        if os.path.exists(driver_path) and os.access(driver_path, os.X_OK):
            try:
                # Test ChromeDriver execution
                result = subprocess.run([driver_path, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    working_drivers.append({
                        'path': driver_path,
                        'version': result.stdout.strip()
                    })
            except Exception as e:
                print(f"[DEBUG] ChromeDriver test failed for {driver_path}: {e}")
                continue
    
    # If no system ChromeDriver found, try to find it in common locations
    if not working_drivers:
        print("[DEBUG] No system ChromeDriver found, searching common locations...")
        try:
            # Try to find ChromeDriver using which command
            result = subprocess.run(['which', 'chromedriver'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                chromedriver_path = result.stdout.strip()
                if os.path.exists(chromedriver_path) and os.access(chromedriver_path, os.X_OK):
                    try:
                        version_result = subprocess.run([chromedriver_path, '--version'], 
                                                      capture_output=True, text=True, timeout=10)
                        if version_result.returncode == 0:
                            working_drivers.append({
                                'path': chromedriver_path,
                                'version': version_result.stdout.strip()
                            })
                    except:
                        pass
        except:
            pass
    
    return working_drivers

def create_chrome_options(headless=True, extra_args=None):
    """Create standardized Chrome options for all environments"""
    options = Options()
    
    # Basic headless configuration
    if headless:
        options.add_argument('--headless')
    
    # Essential arguments for containerized environments
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ipc-flooding-protection')
    
    # Window and display settings
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    # Performance optimizations
    options.add_argument('--memory-pressure-off')
    options.add_argument('--max_old_space_size=4096')
    
    # Security and privacy
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    # Only disable images and JavaScript when running in headless mode to
    # improve speed in CI/container environments. For a visible (headful)
    # browser we want images and JS enabled so pages render correctly.
    if headless:
        options.add_argument('--disable-images')  # Faster loading
        options.add_argument('--disable-javascript')  # Only if not needed
    
    # Docker-specific optimizations
    env = detect_environment()
    if env == 'docker':
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-default-apps')
    
    # Add extra arguments if provided
    if extra_args:
        for arg in extra_args:
            options.add_argument(arg)
    
    # Set Chrome binary if found
    chrome_binary = find_chrome_binary()
    if chrome_binary:
        options.binary_location = chrome_binary
    
    return options

def setup_driver(headless=False, extra_chrome_args=None):
    """
    Set up ChromeDriver with unified configuration
    
    Args:
        headless (bool): Run Chrome in headless mode
        extra_chrome_args (list): Additional Chrome arguments
    
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
    
    Raises:
        Exception: If ChromeDriver setup fails
    """
    system_info = get_system_info()
    print(f"[INFO] Setting up ChromeDriver for {system_info['environment']} environment")
    print(f"[INFO] Platform: {system_info['platform']}")
    print(f"[INFO] Architecture: {system_info['machine']}")
    
    # Find Chrome binary
    chrome_binary = find_chrome_binary()
    if not chrome_binary:
        raise Exception("Chrome browser not found. Please install Google Chrome or Chromium.")
    
    print(f"[INFO] Chrome binary: {chrome_binary}")
    
    # Find ChromeDriver
    working_drivers = find_chromedriver()
    if not working_drivers:
        # Try webdriver-manager as fallback for local environments only
        if system_info['environment'] == 'local':
            print("[INFO] No system ChromeDriver found, trying webdriver-manager...")
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                print("[INFO] Installing ChromeDriver via webdriver-manager...")
                driver_path = ChromeDriverManager().install()
                print(f"[INFO] ChromeDriver installed at: {driver_path}")
                
                # Verify the installed driver works
                try:
                    result = subprocess.run([driver_path, '--version'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        working_drivers = [{'path': driver_path, 'version': result.stdout.strip()}]
                        print(f"[INFO] ✅ ChromeDriver verified: {result.stdout.strip()}")
                    else:
                        raise Exception("Installed ChromeDriver failed version check")
                except Exception as verify_error:
                    raise Exception(f"ChromeDriver verification failed: {verify_error}")
                    
            except ImportError:
                raise Exception("webdriver-manager not installed. Install with: pip install webdriver-manager")
            except Exception as e:
                raise Exception(f"No ChromeDriver found and webdriver-manager failed: {e}")
        else:
            raise Exception("No ChromeDriver found. In Docker, ensure ChromeDriver is properly installed.")
    
    # Use the first working driver
    driver_info = working_drivers[0]
    chromedriver_path = driver_info['path']
    print(f"[INFO] Using ChromeDriver: {chromedriver_path}")
    print(f"[INFO] ChromeDriver version: {driver_info['version']}")
    
    # Create Chrome options
    chrome_options = create_chrome_options(headless=headless, extra_args=extra_chrome_args)
    
    # Suppress Chrome crash dumps and logging to prevent pollution of CSV files
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument('--log-level=3')  # Fatal errors only
    chrome_options.add_argument('--silent')
    
    # Create WebDriver service with log suppression
    import os
    service = Service(
        chromedriver_path,
        log_output=os.devnull  # Redirect ChromeDriver logs to /dev/null
    )
    
    # Initialize WebDriver
    driver = None
    start_time = time.time()
    
    try:
        print("[INFO] Initializing WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set reasonable implicit wait
        driver.implicitly_wait(10)
        
        # Set page load timeout to 5 minutes (300 seconds)
        driver.set_page_load_timeout(300)
        
        # Anti-detection measures
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[INFO] ✅ ChromeDriver setup successful!")
        return driver
        
    except Exception as e:
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        elapsed = time.time() - start_time
        error_msg = f"ChromeDriver setup failed after {elapsed:.1f}s: {e}"
        print(f"[ERROR] {error_msg}")
        
        # Provide troubleshooting information
        print("\n[DEBUG] Troubleshooting Information:")
        print(f"  - Environment: {system_info['environment']}")
        print(f"  - Chrome binary: {chrome_binary}")
        print(f"  - ChromeDriver path: {chromedriver_path}")
        print(f"  - Available drivers: {len(working_drivers)}")
        
        raise Exception(error_msg)

def test_driver_setup():
    """Test the driver setup with a simple page load"""
    try:
        print("[TEST] Testing ChromeDriver setup...")
        driver = setup_driver(headless=True)
        
        # Test basic functionality
        driver.get("https://www.google.com")
        title = driver.title
        
        driver.quit()
        
        print(f"[TEST] ✅ SUCCESS! Loaded Google with title: {title}")
        return True
        
    except Exception as e:
        print(f"[TEST] ❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    # Run test when executed directly
    success = test_driver_setup()
    sys.exit(0 if success else 1)
