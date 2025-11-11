"""
Credit checking utilities for detecting stock photo watermarks/credits
"""

import time
import re
from selenium.webdriver.common.by import By
from .keywords import CREDIT_KEYWORDS


def matches_keyword_with_word_boundary(keyword, text):
    """
    Check if keyword matches in text using word boundaries to avoid false positives.
    This prevents matching 'vii' within 'viitoare' but allows matching 'vii' in '(vii)' or 'vii,'.
    
    Args:
        keyword (str): The keyword to search for
        text (str): The text to search in
    
    Returns:
        bool: True if keyword is found as a whole word, False otherwise
    """
    if not keyword or not text:
        return False
    
    # Use standard word boundaries which are more reliable
    # \b matches between word characters (alphanumeric + underscore) and non-word characters
    # This should properly handle cases like "dpa" in "/dpa/" while avoiding "vii" in "viitoare"
    escaped_keyword = re.escape(keyword.lower())
    pattern = r'\b' + escaped_keyword + r'\b'
    
    # Search case-insensitively
    return bool(re.search(pattern, text, re.IGNORECASE))


def check_credit_keywords_in_parents(driver, image_element):
    """Check for credit keywords in all viewport text and grandparent elements."""
    try:
        found_keywords = []
        found_texts = []
        
        # First, scroll the image into view to ensure it's in the viewport
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", image_element)
        time.sleep(0.5)  # Allow scroll to complete
        
        # Method 1: Search text elements by scrolling 0.5 page up and down from image (primary method)
        try:
            print("🔍 Searching text by scrolling 0.5 page up/down from image for credit keywords...")
            
            # Get viewport height and current scroll position
            viewport_height = driver.execute_script("return window.innerHeight")
            scroll_step = viewport_height * 0.5  # 0.5 page length
            
            # Get image position and scroll to center it
            image_rect = driver.execute_script("return arguments[0].getBoundingClientRect();", image_element)
            current_scroll = driver.execute_script("return window.pageYOffset")
            image_absolute_y = current_scroll + image_rect['y']
            
            # Calculate scroll positions: 0.5 page up and 0.5 page down from image
            scroll_up_position = max(0, image_absolute_y - scroll_step)
            scroll_down_position = image_absolute_y + scroll_step
            
            # Collect all text elements while scrolling through the area
            all_texts = []
            scroll_positions = []
            
            # Create scroll positions array (up to down)
            current_pos = scroll_up_position
            while current_pos <= scroll_down_position:
                scroll_positions.append(current_pos)
                current_pos += viewport_height * 0.3  # Overlap scrolls for complete coverage
            
            print(f"   Scrolling through {len(scroll_positions)} positions covering {scroll_step:.0f}px above/below image")
            
            # Scroll through each position and collect text
            for i, scroll_pos in enumerate(scroll_positions):
                driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                time.sleep(0.2)  # Brief pause for content to load
                
                # Get all visible text elements at this scroll position
                visible_texts = driver.execute_script("""
                    var texts = [];
                    var walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    var node;
                    while (node = walker.nextNode()) {
                        var text = node.textContent.trim();
                        if (text.length > 2) {
                            var parent = node.parentElement;
                            if (parent) {
                                var rect = parent.getBoundingClientRect();
                                // Only include text that's currently visible in viewport
                                if (rect.width > 0 && rect.height > 0 && 
                                    rect.bottom >= 0 && rect.top <= window.innerHeight &&
                                    rect.right >= 0 && rect.left <= window.innerWidth) {
                                    
                                    texts.push({
                                        text: text,
                                        scrollPosition: arguments[0],
                                        element: parent.tagName || 'UNKNOWN'
                                    });
                                }
                            }
                        }
                    }
                    return texts;
                """, scroll_pos)
                
                all_texts.extend(visible_texts)
            
            print(f"   Collected {len(all_texts)} text elements from scrolling")
            
            # Check all collected text for credit keywords
            for text_data in all_texts:
                text_content = text_data['text']
                for keyword in CREDIT_KEYWORDS:
                    if matches_keyword_with_word_boundary(keyword, text_content):
                        found_keywords.append(f"Scrolled Text: {keyword}")
                        found_texts.append(f"Scrolled Text ({text_data['element']}): {text_content[:200]}...")
                        print(f"   Found '{keyword}' in scrolled text: {text_content[:100]}...")
                        break  # Only count once per text element
            
        except Exception as e:
            print(f"   ⚠️ Error in scroll-based text search: {e}")
        
        # Method 2: Search in parent and grandparent elements of the image
        try:
            print("🔍 Searching parent and grandparent elements for credit keywords...")
            
            parent_keywords = driver.execute_script("""
                var image = arguments[0];
                var keywords = arguments[1];
                var found = [];
                
                // Check parent element
                if (image.parentElement) {
                    var parentText = image.parentElement.textContent || '';
                    for (var i = 0; i < keywords.length; i++) {
                        var keyword = keywords[i];
                        var regex = new RegExp('\\\\b' + keyword.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\b', 'i');
                        if (regex.test(parentText)) {
                            found.push({
                                keyword: keyword,
                                text: parentText.substring(0, 200),
                                location: 'parent'
                            });
                        }
                    }
                }
                
                // Check grandparent element
                if (image.parentElement && image.parentElement.parentElement) {
                    var grandparentText = image.parentElement.parentElement.textContent || '';
                    for (var i = 0; i < keywords.length; i++) {
                        var keyword = keywords[i];
                        var regex = new RegExp('\\\\b' + keyword.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\b', 'i');
                        if (regex.test(grandparentText)) {
                            found.push({
                                keyword: keyword,
                                text: grandparentText.substring(0, 200),
                                location: 'grandparent'
                            });
                        }
                    }
                }
                
                return found;
            """, image_element, CREDIT_KEYWORDS)
            
            for result in parent_keywords:
                found_keywords.append(f"Parent Element: {result['keyword']}")
                found_texts.append(f"Parent Element ({result['location']}): {result['text']}...")
                print(f"   Found '{result['keyword']}' in {result['location']} element: {result['text'][:100]}...")
                
        except Exception as e:
            print(f"   ⚠️ Error searching parent elements: {e}")
        
        print(f"📍 Found {len(found_keywords)} credit keywords in parent elements and scrolled text")
        
    except Exception as e:
        print(f"⚠️ Error checking credit keywords in parents: {e}")
    
    return found_keywords, found_texts


def check_caption_elements_for_credits(driver, image_element=None):
    """
    Check caption elements (figcaption, caption, etc.) for credit keywords.
    If image_element is provided, prioritize captions near that image.
    
    Args:
        driver: Selenium WebDriver instance
        image_element: Optional image element to find nearby captions
    
    Returns:
        tuple: (found_keywords, found_texts)
    """
    found_keywords = []
    found_texts = []
    
    try:
        # Define caption selectors to search for
        caption_selectors = [
            'figcaption',  # HTML5 figure captions
            'caption',     # Table captions 
            '.caption',    # Common caption class
            '.photo-caption',  # Photo caption class
            '.image-caption',  # Image caption class
            '.credit',     # Credit class
            '.photo-credit',   # Photo credit class
            '.image-credit',   # Image credit class
            '[class*="caption"]',  # Any class containing "caption"
            '[class*="credit"]',   # Any class containing "credit"
        ]
        
        # If we have a specific image element, try to find captions near it first
        if image_element:
            print("   Searching for captions near the target image...")
            try:
                # Look for captions in the same parent container
                nearby_captions = driver.execute_script("""
                    var image = arguments[0];
                    var captions = [];
                    var selectors = arguments[1];
                    
                    // Search in parent and grandparent containers
                    var containers = [image.parentElement];
                    if (image.parentElement && image.parentElement.parentElement) {
                        containers.push(image.parentElement.parentElement);
                    }
                    
                    containers.forEach(function(container) {
                        if (container) {
                            selectors.forEach(function(selector) {
                                try {
                                    var elements = container.querySelectorAll(selector);
                                    for (var i = 0; i < elements.length; i++) {
                                        var text = elements[i].textContent.trim();
                                        if (text.length > 5) {  // Only consider meaningful text
                                            captions.push({
                                                text: text,
                                                selector: selector,
                                                location: 'near-image'
                                            });
                                        }
                                    }
                                } catch (e) {
                                    // Skip invalid selectors
                                }
                            });
                        }
                    });
                    
                    return captions;
                """, image_element, caption_selectors)
                
                # Check these nearby captions first
                for caption_data in nearby_captions:
                    text_content = caption_data['text']
                    for keyword in CREDIT_KEYWORDS:
                        if matches_keyword_with_word_boundary(keyword, text_content):
                            found_keywords.append(f"Image Caption: {keyword}")
                            found_texts.append(f"Image Caption ({caption_data['selector']}): {text_content[:200]}...")
                            print(f"   Found '{keyword}' in image caption: {text_content[:100]}...")
                            break  # Only count once per caption
                            
            except Exception as e:
                print(f"   ⚠️ Error searching captions near image: {e}")
        
        # Search all caption elements on the page
        print("   Searching all caption elements on page...")
        all_captions = driver.execute_script("""
            var captions = [];
            var selectors = arguments[0];
            
            selectors.forEach(function(selector) {
                try {
                    var elements = document.querySelectorAll(selector);
                    for (var i = 0; i < elements.length; i++) {
                        var text = elements[i].textContent.trim();
                        if (text.length > 5) {  // Only consider meaningful text
                            captions.push({
                                text: text,
                                selector: selector,
                                location: 'page-wide'
                            });
                        }
                    }
                } catch (e) {
                    // Skip invalid selectors
                }
            });
            
            return captions;
        """, caption_selectors)
        
        # Check all captions for keywords
        page_caption_count = 0
        for caption_data in all_captions:
            text_content = caption_data['text']
            for keyword in CREDIT_KEYWORDS:
                if matches_keyword_with_word_boundary(keyword, text_content):
                    keyword_entry = f"Page Caption: {keyword}"
                    if keyword_entry not in found_keywords:  # Avoid duplicates
                        found_keywords.append(keyword_entry)
                        found_texts.append(f"Page Caption ({caption_data['selector']}): {text_content[:200]}...")
                        page_caption_count += 1
                        print(f"   Found '{keyword}' in page caption: {text_content[:100]}...")
                        break  # Only count once per caption
        
        print(f"📍 Found {len(found_keywords)} credit keywords in caption elements")
        
    except Exception as e:
        print(f"⚠️ Error checking caption elements: {e}")
    
    return found_keywords, found_texts


def check_impressum_for_credits(driver, original_url, case_url=None, hit_id=None):
    """
    Find and scrape the impressum/imprint/legal notice page for image credits.
    This is used as a final fallback when no credits are found on the main page.
    If no keywords are found in HTML text, scroll through the page taking screenshots and using OCR.
    """
    from .ocr import _ocr_scroll_impressum_page
    
    impressum_keywords = []
    impressum_texts = []
    
    try:
        print("🔍 Searching for impressum/imprint/legal notice page...")
        
        # Common impressum link patterns (multilingual)
        impressum_selectors = [
            # German
            "a[href*='impressum']", "a[href*='Impressum']", 
            "a:contains('Impressum')", "a:contains('impressum')",
            # English
            "a[href*='imprint']", "a[href*='Imprint']",
            "a:contains('Imprint')", "a:contains('imprint')",
            "a:contains('Licenses')", "a:contains('licenses')",
            "a:contains('License')", "a:contains('license')",

            "a[href*='legal']", "a[href*='Legal']",
            "a:contains('Legal Notice')", "a:contains('legal notice')",
            # French
            "a[href*='mentions']", "a[href*='Mentions']",
            "a:contains('Mentions légales')", "a:contains('mentions légales')",
            # Spanish
            "a[href*='aviso']", "a[href*='Aviso']",
            "a:contains('Aviso legal')", "a:contains('aviso legal')",
            # Italian
            "a[href*='note']", "a[href*='Note']",
            "a:contains('Note legali')", "a:contains('note legali')",
            # Generic
            "a:contains('Credits')", "a:contains('credits')",
            "a:contains('Attribution')", "a:contains('attribution')"
        ]
        
        impressum_link = None
        impressum_type = "unknown"
        
        # Try to find impressum link using JavaScript (more reliable than CSS selectors)
        impressum_info = driver.execute_script("""
            var links = document.getElementsByTagName('a');
            var impressumPatterns = [
                'impressum', 'imprint', 'legal notice', 'legal', 'mentions légales', 
                'mentions legales', 'aviso legal', 'note legali', 'credits', 'attribution'
            ];
            
            for (var i = 0; i < links.length; i++) {
                var link = links[i];
                var href = (link.href || '').toLowerCase();
                var text = (link.textContent || '').toLowerCase().trim();
                
                for (var j = 0; j < impressumPatterns.length; j++) {
                    var pattern = impressumPatterns[j];
                    if (href.includes(pattern) || text.includes(pattern)) {
                        return {
                            url: link.href,
                            text: link.textContent.trim(),
                            pattern: pattern
                        };
                    }
                }
            }
            return null;
        """)
        
        if impressum_info:
            impressum_link = impressum_info['url']
            impressum_type = impressum_info['pattern']
            print(f"✓ Found {impressum_type} page: {impressum_info['text']}")
        else:
            print("⚠️ No impressum/legal notice page found")
            return impressum_keywords, impressum_texts
        
        # Navigate to impressum page
        print(f"🌐 Navigating to {impressum_type} page...")
        current_url = driver.current_url
        
        try:
            driver.get(impressum_link)
            time.sleep(2)  # Allow page to load
            
            # Check if page loaded successfully
            if "404" in driver.title.lower() or "not found" in driver.title.lower():
                print(f"❌ {impressum_type.title()} page not found (404)")
                return impressum_keywords, impressum_texts
            
            print(f"✓ Successfully loaded {impressum_type} page: {driver.title}")
            
            # First attempt: Extract all text content from the impressum page
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Check for credit keywords in the impressum text
            found_count = 0
            for keyword in CREDIT_KEYWORDS:
                if matches_keyword_with_word_boundary(keyword, page_text):
                    impressum_keywords.append(keyword)  # Return clean keyword for CSV integration
                    found_count += 1
            
            if found_count > 0:
                print(f"🎯 Found {found_count} credit keywords in {impressum_type} page HTML text!")
                # Add a snippet of the impressum text for reference
                impressum_snippet = page_text[:500] + "..." if len(page_text) > 500 else page_text
                impressum_texts.append(f"Impressum page content: {impressum_snippet}")
            else:
                print(f"✓ No credit keywords found in {impressum_type} page HTML text")
                print("🔍 Attempting OCR scroll analysis of impressum page...")
                
                # Fallback: Scroll through the page taking screenshots and using OCR
                try:
                    from .ocr import OCR_AVAILABLE, EASYOCR_AVAILABLE
                    if OCR_AVAILABLE or EASYOCR_AVAILABLE:
                        ocr_keywords, ocr_texts = _ocr_scroll_impressum_page(driver, impressum_type, 10, case_url, hit_id)
                        impressum_keywords.extend(ocr_keywords)
                        impressum_texts.extend(ocr_texts)
                        
                        if ocr_keywords:
                            print(f"🎯 Found {len(ocr_keywords)} credit keywords via OCR in {impressum_type} page!")
                        else:
                            print(f"✓ No credit keywords found via OCR in {impressum_type} page")
                    else:
                        print("⚠️ OCR not available - cannot perform deep impressum analysis")
                except ImportError:
                    print("⚠️ OCR module not available - cannot perform deep impressum analysis")
            
        except Exception as e:
            print(f"⚠️ Error accessing {impressum_type} page: {e}")
            
        finally:
            # Navigate back to original page
            try:
                print("🔙 Returning to original page...")
                driver.get(current_url)
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ Could not return to original page: {e}")
    
    except Exception as e:
        print(f"⚠️ Impressum search failed: {e}")
    
    return impressum_keywords, impressum_texts



