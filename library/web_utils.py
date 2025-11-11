"""
Web scraping and driver utilities
"""

import time
import os
from datetime import datetime
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from .unified_driver_utils import setup_driver, create_chrome_options
from PIL import Image, ImageDraw, ImageFont
from .keywords import CREDIT_KEYWORDS
from .credit_checker import matches_keyword_with_word_boundary


def handle_initial_page_setup(driver):
    """Wait for the page body to load."""
    print("Waiting for page to load...")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("Initial page setup completed")


def setup_driver():
    """Setup Chrome driver with unified configuration"""
    print("🔧 Setting up Chrome WebDriver...")
    
    # Load extensions if available
    extensions_loaded = []
    extra_args = []
    
    # Load uBlock Origin unpacked extension
    if os.path.exists("ublock_unpacked"):
        extra_args.append("--load-extension=ublock_unpacked")
        extensions_loaded.append("uBlock Origin")
        print("🔧 Loading uBlock Origin unpacked extension")
    else:
        print("⚠️ uBlock unpacked extension not found (ublock_unpacked directory missing)")
    
        # Load Cookies unpacked extension
    if os.path.exists("cookies_unpacked"):
        if extra_args:
            # Extend existing extension argument
            extra_args[0] += ",cookies_unpacked"
        else:
            extra_args.append("--load-extension=cookies_unpacked")
        extensions_loaded.append("Cookies Extension")
        print("🔧 Loading Cookies unpacked extension")
    else:
        print("⚠️ Cookies unpacked extension not found (cookies_unpacked directory missing)")
    
    if extensions_loaded:
        print(f"🔧 Loaded extensions: {', '.join(extensions_loaded)}")
    else:
        print("⚠️ No unpacked extensions found")
    
    # Use unified driver setup with extensions
    try:
        from .unified_driver_utils import setup_driver as unified_setup
        
        # Enable JavaScript for extensions compatibility
        if extensions_loaded:
            print("[INFO] Enabling JavaScript for extension compatibility")
            extra_args.extend([
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--remote-debugging-port=9222"
            ])
        
        driver = unified_setup(
            headless=True, 
            extra_chrome_args=extra_args
        )        # Verify extensions are loaded
        if extensions_loaded:
            try:
                current_url = driver.current_url
                driver.get("chrome://extensions/")
                time.sleep(2)
                print(f"🔧 Extensions verification completed")
                
                # Return to original page or go to blank
                if current_url and current_url != "data:,":
                    driver.get(current_url)
                else:
                    driver.get("about:blank")
                    
            except Exception as ext_error:
                print(f"⚠️ Extension verification failed: {ext_error}")
            try:
                current_url = driver.current_url
                driver.get("chrome://extensions/")
                time.sleep(2)
                print(f"🔧 Extensions verification completed")
                
                # Return to original page or go to blank
                if current_url and current_url != "data:,":
                    driver.get(current_url)
                else:
                    driver.get("about:blank")
                    
            except Exception as ext_error:
                print(f"⚠️ Extension verification failed: {ext_error}")
        
        print("✅ Chrome WebDriver setup successful!")
        return driver
        
    except Exception as e:
        error_msg = f"Failed to setup Chrome WebDriver: {e}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)
        error_msg = f"Failed to setup Chrome WebDriver: {e}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)


def create_highlighted_credit_link(keywords, found=True, page_url=None, text_content=None):
    """Create a highlighted text link for credit keywords using Chrome's text highlighting feature"""
    if found and keywords and page_url:
        # Create Chrome text highlighting URL using the first keyword found
        first_keyword = keywords[0] if keywords else "Getty Images"
        highlighted_url = f"{page_url}#:~:text={first_keyword}"
        return highlighted_url
    else:
        return page_url if page_url else "#"


def take_full_screenshot_with_timestamp(driver, image_element=None, output_path=None, case_url=None, hit_id=None):
    """Take a full screenshot of the page with timestamp and optional image highlighting"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if not output_path:
            output_path = f"screenshot_{timestamp}.png"
        
        # Take screenshot
        driver.save_screenshot(output_path)
        print(f"📸 Screenshot saved: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Screenshot failed: {e}")
        return None
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


def wait_for_images_to_load(driver):
    """Wait for images to load with a more reasonable timeout"""
    try:
        print("⏳ Waiting for images to load...")
        # Reduced timeout to 10 seconds max
        for attempt in range(10):  # 10 seconds max
            all_loaded = driver.execute_script("""
                var images = document.querySelectorAll('img');
                var loadedCount = 0;
                var totalCount = images.length;
                
                for (var i = 0; i < images.length; i++) {
                    if (images[i].complete && images[i].naturalHeight > 0) {
                        loadedCount++;
                    }
                }
                
                // Consider loaded if 80% of images are loaded or if we have at least 5 loaded images
                return loadedCount >= Math.max(5, totalCount * 0.8);
            """)
            if all_loaded:
                print("✅ Images loaded (80% threshold reached)")
                return
            time.sleep(1)
        print("⚠️ Image loading timed out after 10s, continuing anyway")
    except Exception as e:
        print(f"⚠️ Image loading check failed: {e}")


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


