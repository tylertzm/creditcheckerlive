"""
Web scraping and driver utilities
"""

import time
import os
import requests
from datetime import datetime
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw, ImageFont
from .keywords import CREDIT_KEYWORDS
from .credit_checker import matches_keyword_with_word_boundary


def handle_initial_page_setup(driver):
    """Wait for the page body to load."""
    print("Waiting for page to load...")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("Initial page setup completed")


def setup_driver():
    """Setup Chrome driver with optimized options"""
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Docker-friendly and stability options
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Additional stability options
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-default-apps")
    
    # Memory management
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=4096")
    
    # Add unpacked extensions if they exist
    extensions_loaded = []
    
    # Load uBlock Origin unpacked extension
    if os.path.exists("ublock_unpacked"):
        chrome_options.add_argument("--load-extension=ublock_unpacked")
        extensions_loaded.append("uBlock Origin")
        print("🔧 Loading uBlock Origin unpacked extension")
    else:
        print("⚠️ uBlock unpacked extension not found (ublock_unpacked directory missing)")
    
    # Load Cookies unpacked extension
    if os.path.exists("cookies_unpacked"):
        chrome_options.add_argument("--load-extension=cookies_unpacked")
        extensions_loaded.append("Cookies Extension")
        print("🔧 Loading Cookies unpacked extension")
    else:
        print("⚠️ Cookies unpacked extension not found (cookies_unpacked directory missing)")
    
    if extensions_loaded:
        print(f"🔧 Loaded extensions: {', '.join(extensions_loaded)}")
    else:
        print("⚠️ No unpacked extensions found")
    
    # Use system chromedriver (more reliable in Docker)
    try:
        # Try system chromedriver first (installed via package manager or Docker)
        # Check multiple possible locations
        chromedriver_paths = [
            "/usr/local/bin/chromedriver",  # Docker installed location
            "/usr/bin/chromedriver",        # Package manager location
            "/usr/bin/chromium-driver",     # Chromium driver location
        ]
        
        driver = None
        for chromedriver_path in chromedriver_paths:
            try:
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print(f"✅ Using chromedriver from: {chromedriver_path}")
                break
            except Exception as path_error:
                print(f"Failed to use chromedriver from {chromedriver_path}: {path_error}")
                continue
        
        if driver is None:
            raise Exception("No system chromedriver found in standard locations")
            
    except Exception as e:
        print(f"System chromedriver failed: {e}, trying webdriver-manager...")
        # Fallback to webdriver-manager
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e2:
            raise Exception(f"Failed to setup ChromeDriver: system error: {e}, webdriver-manager error: {e2}")
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Verify extensions are loaded
    try:
        if extensions_loaded:
            current_url = driver.current_url
            driver.get("chrome://extensions/")
            time.sleep(1)
            
            # Get extension info
            extensions_info = driver.execute_script("""
                var extensions = [];
                var manager = document.querySelector('extensions-manager');
                if (manager && manager.shadowRoot) {
                    var items = manager.shadowRoot.querySelectorAll('extensions-item');
                    for (var i = 0; i < items.length; i++) {
                        var item = items[i];
                        if (item.shadowRoot) {
                            var name = item.shadowRoot.querySelector('#name');
                            var toggle = item.shadowRoot.querySelector('#enableToggle');
                            if (name && toggle) {
                                extensions.push({
                                    name: name.textContent.trim(),
                                    enabled: toggle.checked
                                });
                            }
                        }
                    }
                }
                return extensions;
            """)
            
            if extensions_info:
                print("🔧 Loaded extensions:")
                for ext in extensions_info:
                    status = "✅ ENABLED" if ext['enabled'] else "❌ DISABLED"
                    print(f"   {ext['name']}: {status}")
            else:
                print("⚠️ Could not verify extension status")
                
            # Navigate back if we changed URL
            if current_url and current_url != "data:,":
                driver.get(current_url)
                
    except Exception as e:
        print(f"⚠️ Could not verify extensions: {e}")
    
    # Set additional timeouts for stability
    driver.implicitly_wait(10)
    driver.set_script_timeout(30)
    
    return driver


def create_highlighted_credit_link(keywords, found=True, page_url=None, text_content=None):
    """Create a highlighted text link for credit keywords using Chrome's text highlighting feature"""
    if found and keywords and page_url:
        # Create Chrome text highlighting URL using the first keyword found
        first_keyword = keywords[0] if keywords else "Getty Images"
        # URL encode the keyword for the highlight link
        encoded_keyword = first_keyword.replace(" ", "%20")
        highlight_url = f"{page_url}#:~:text={encoded_keyword}"
        return highlight_url
    else:
        # Return empty string for no credits or analysis pending
        return ""


def take_full_screenshot_with_timestamp(driver, image_element=None, output_path=None, case_url=None, hit_id=None):
    """Take a full screenshot of the page with timestamp and optional image highlighting"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_path is None:
            # Create filename with case URL and hit ID if provided
            filename_parts = [timestamp]
            
            if case_url:
                # Extract domain from case URL for cleaner filename
                parsed_url = urlparse(case_url)
                domain = parsed_url.netloc.replace('www.', '').replace('.', '_')
                filename_parts.append(domain)
            
            if hit_id:
                filename_parts.append(f"hit_{hit_id}")
            
            output_path = f"{'_'.join(filename_parts)}.png"

        # Get image coordinates before taking screenshot if image_element is provided
        image_coords = None
        if image_element:
            try:
                # Scroll the image into view instantly
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", image_element)

                # Dynamic wait: wait for scroll to complete
                try:
                    WebDriverWait(driver, 0.5).until(
                        lambda d: d.execute_script("""
                            var rect = arguments[0].getBoundingClientRect();
                            var viewportHeight = window.innerHeight;
                            return rect.top >= 0 && rect.bottom <= viewportHeight;
                        """, image_element)
                    )
                except:
                    pass  # Continue if element is already in view
                
                # Get element bounding rectangle using JavaScript for more accurate coordinates
                rect = driver.execute_script("""
                    var rect = arguments[0].getBoundingClientRect();
                    return {
                        left: rect.left,
                        top: rect.top,
                        width: rect.width,
                        height: rect.height
                    };
                """, image_element)
                
                # Get device pixel ratio
                pixel_ratio = driver.execute_script("return window.devicePixelRatio")
                
                # Get current scroll position
                scroll_x = driver.execute_script("return window.pageXOffset || document.documentElement.scrollLeft || document.body.scrollLeft || 0")
                scroll_y = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0")
                
                image_coords = {
                    'left': rect['left'],
                    'top': rect['top'],
                    'width': rect['width'],
                    'height': rect['height'],
                    'pixel_ratio': pixel_ratio
                }
                
                print(f"Bounding rect coordinates: ({rect['left']}, {rect['top']})")
                print(f"Scroll position: ({scroll_x}, {scroll_y})")
                print(f"Element size: {rect['width']}x{rect['height']}")
                print(f"Pixel ratio: {pixel_ratio}")
                
            except Exception as e:
                print(f"Could not capture coordinates for highlighting: {e}")
                import traceback
                traceback.print_exc()

        # Take viewport screenshot while image is still in view
        driver.save_screenshot(output_path)
        
        # Add timestamp and highlighting to screenshot
        screenshot = Image.open(output_path)
        draw = ImageDraw.Draw(screenshot)

        # Add timestamp and page URL at bottom right
        timestamp_text = f"Screenshot: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Get current page URL
        try:
            current_url = driver.current_url
            # Truncate URL if too long for display
            if len(current_url) > 80:
                current_url = current_url[:77] + "..."
            page_url_text = f"URL: {current_url}"
        except:
            page_url_text = "URL: Unknown"
        
        try:
            if os.name == 'nt':  # Windows
                font = ImageFont.truetype("arial.ttf", 20)
            else:  # Mac/Linux
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Calculate text dimensions
        timestamp_bbox = draw.textbbox((0, 0), timestamp_text, font=font)
        url_bbox = draw.textbbox((0, 0), page_url_text, font=font)
        
        timestamp_w = timestamp_bbox[2] - timestamp_bbox[0]
        timestamp_h = timestamp_bbox[3] - timestamp_bbox[1]
        url_w = url_bbox[2] - url_bbox[0]
        url_h = url_bbox[3] - url_bbox[1]
        
        # Calculate total height needed for both texts
        total_height = timestamp_h + url_h + 20  # 20px spacing between texts
        max_width = max(timestamp_w, url_w)
        
        # Position at bottom right with some padding
        padding = 15
        text_x = screenshot.width - max_width - padding
        text_y = screenshot.height - total_height - padding
        
        # Draw background rectangle with black border
        bg_x1 = text_x - 10
        bg_y1 = text_y - 10
        bg_x2 = screenshot.width - 5
        bg_y2 = screenshot.height - 5
        
        # Draw black background
        draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(0, 0, 0))
        
        # Draw white border around the background
        draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], outline=(255, 255, 255), width=2)
        
        # Draw timestamp text (white with black outline for better visibility)
        draw.text((text_x, text_y), timestamp_text, fill=(255, 255, 255), font=font)
        
        # Draw page URL text below timestamp
        draw.text((text_x, text_y + timestamp_h + 10), page_url_text, fill=(255, 255, 255), font=font)

        # Highlight target image if coordinates were captured
        if image_coords:
            try:
                # Use the pixel ratio that was captured earlier
                pixel_ratio = image_coords.get('pixel_ratio', 1.0)
                
                # Apply pixel ratio to coordinates
                left = int(image_coords['left'] * pixel_ratio)
                top = int(image_coords['top'] * pixel_ratio)
                right = int((image_coords['left'] + image_coords['width']) * pixel_ratio)
                bottom = int((image_coords['top'] + image_coords['height']) * pixel_ratio)
                
                print(f"Screenshot dimensions: {screenshot.width}x{screenshot.height}")
                print(f"Calculated highlight coordinates: ({left}, {top}) to ({right}, {bottom})")
                
                # Ensure coordinates are within screenshot bounds
                left = max(0, min(left, screenshot.width - 1))
                top = max(0, min(top, screenshot.height - 1))
                right = max(left + 1, min(right, screenshot.width))
                bottom = max(top + 1, min(bottom, screenshot.height))
                
                print(f"Bounded highlight coordinates: ({left}, {top}) to ({right}, {bottom})")
                
                # Add a test marker at top-left corner to verify coordinate system
                test_marker_size = 10
                draw.rectangle([0, 0, test_marker_size, test_marker_size], fill=(0, 255, 0))  # Green test marker
                
                # Draw a thicker, more visible red border
                border_width = 6
                for i in range(border_width):
                    draw.rectangle([left - i, top - i, right + i, bottom + i], outline=(255, 0, 0), width=2)
                
                # Add a more prominent label
                label_text = "TARGET IMAGE"
                label_bbox = draw.textbbox((0, 0), label_text, font=font)
                label_w = label_bbox[2] - label_bbox[0]
                label_h = label_bbox[3] - label_bbox[1]
                
                # Position label above the image with better visibility
                label_x = left
                label_y = max(10, top - label_h - 15)
                
                # Draw label background with better contrast
                draw.rectangle([label_x - 8, label_y - 5, label_x + label_w + 8, label_y + label_h + 5], 
                             fill=(255, 0, 0), outline=(255, 255, 255), width=2)
                draw.text((label_x, label_y), label_text, fill=(255, 255, 255), font=font)
                
                # Add corner markers for better visibility
                marker_size = 20
                # Top-left corner
                draw.rectangle([left - marker_size, top - marker_size, left, top], fill=(255, 0, 0))
                # Top-right corner
                draw.rectangle([right, top - marker_size, right + marker_size, top], fill=(255, 0, 0))
                # Bottom-left corner
                draw.rectangle([left - marker_size, bottom, left, bottom + marker_size], fill=(255, 0, 0))
                # Bottom-right corner
                draw.rectangle([right, bottom, right + marker_size, bottom + marker_size], fill=(255, 0, 0))
                
                print(f"Target image successfully highlighted with red border and corner markers")
                
            except Exception as e:
                print(f"Error highlighting target: {e}")
                import traceback
                traceback.print_exc()

        screenshot.save(output_path)
        print(f"✅ Screenshot saved: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ Error taking screenshot: {e}")
        return None


def wait_for_images_to_load(driver, timeout=10):
    """Wait for all images on the page to finish loading"""
    try:
        print("⏳ Waiting for images to load...")
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("""
                var images = document.querySelectorAll('img');
                for (var i = 0; i < images.length; i++) {
                    if (!images[i].complete || images[i].naturalHeight === 0) {
                        return false;
                    }
                }
                return true;
            """)
        )
        print("✅ All images loaded successfully")
    except TimeoutException:
        print("⚠️ Timeout waiting for images to load, proceeding anyway...")
    except Exception as e:
        print(f"⚠️ Error waiting for images: {e}")


def check_for_404_or_page_errors(driver):
    """Check if the page shows 404 or other error indicators"""
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        error_indicators = [
            "404", "not found", "page not found", "page doesn't exist",
            "error 404", "http 404", "file not found", "page unavailable",
            "this page could not be found", "the page you requested was not found",
            "sorry, the page you are looking for doesn't exist",
            "oops! that page can't be found", "404 error"
        ]
        
        for indicator in error_indicators:
            if indicator in page_text:
                return f"Page shows '{indicator}' error"
        
        # Check page title for error indicators
        title = driver.title.lower()
        title_errors = ["404", "not found", "error"]
        for error in title_errors:
            if error in title:
                return f"Page title indicates error: '{driver.title}'"
                
        return None
    except Exception as e:
        print(f"⚠️ Error checking for 404/page errors: {e}")
        return None


def quick_requests_based_credit_check(page_url, timeout=10):
    """
    Quick preliminary check using requests to fetch page HTML and search for credit keywords.
    This is much faster than launching a browser and can help identify potential credits early.
    
    Args:
        page_url (str): URL of the webpage to check
        timeout (int): Request timeout in seconds
    
    Returns:
        list: Found credit keywords (empty list if none found or if request fails)
    """
    found_keywords = []
    
    try:
        print(f"   📡 Fetching page content from {page_url[:60]}...")
        
        # Set up headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Fetch the page content
        response = requests.get(page_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Get the page content
        page_content = response.text
        print(f"   📄 Retrieved {len(page_content)} characters of HTML content")
        
        # Search for credit keywords in the HTML content
        keywords_found = 0
        for keyword in CREDIT_KEYWORDS:
            if matches_keyword_with_word_boundary(keyword, page_content):
                found_keywords.append(keyword)
                keywords_found += 1
                print(f"   🎯 Found potential credit keyword: '{keyword}'")
        
        if keywords_found > 0:
            print(f"   ✅ Preliminary check found {keywords_found} potential credit keywords")
        else:
            print(f"   ⚠️ Preliminary check found no credit keywords in HTML")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    except Exception as e:
        print(f"   ❌ Preliminary check error: {e}")
    
    return found_keywords
