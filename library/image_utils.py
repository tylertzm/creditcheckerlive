"""
Image processing and similarity utilities
"""

import time
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from selenium.webdriver.common.by import By
from concurrent.futures import ThreadPoolExecutor, as_completed

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def find_image_by_url(driver, target_image_url):
    """Find an image element by matching its src URL or filename"""
    try:
        # Safely extract filename from URL
        if not target_image_url:
            return None
        url_parts = target_image_url.split('/')
        if url_parts:
            filename_with_query = url_parts[-1]
            target_filename = filename_with_query.split('?')[0] if filename_with_query else ""
        else:
            target_filename = ""
            
        images = driver.find_elements(By.TAG_NAME, "img")
        for img in images:
            src = img.get_attribute("src") or ""
            srcset = img.get_attribute("srcset") or ""
            if target_image_url in src or target_image_url in srcset or (target_filename and target_filename in src) or (target_filename and target_filename in srcset):
                return img
        return None
    except Exception as e:
        print(f"Error finding image by URL: {e}")
        return None


def dhash(image, hash_size=8):
    """Compute difference hash (dHash) for perceptual image similarity"""
    try:
        # Convert to grayscale and resize
        image = image.convert('L').resize((hash_size + 1, hash_size), Image.LANCZOS)
        
        # Convert to numpy array
        pixels = list(image.getdata())
        
        # Compute the difference hash
        diff = []
        for row in range(hash_size):
            for col in range(hash_size):
                pixel_left = pixels[row * (hash_size + 1) + col]
                pixel_right = pixels[row * (hash_size + 1) + (col + 1)]
                diff.append(pixel_left > pixel_right)
        
        # Convert to hex string
        decimal_value = 0
        hex_string = []
        for index, value in enumerate(diff):
            if value:
                decimal_value += 2**(index % 8)
            if (index % 8) == 7:
                hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
                decimal_value = 0
        
        return ''.join(hex_string)
    except Exception as e:
        print(f"⚠️ Could not compute dHash: {e}")
        return None


def ahash(image, hash_size=8):
    """Compute average hash (aHash) for perceptual image similarity"""
    try:
        # Resize and convert to grayscale
        image = image.convert('L').resize((hash_size, hash_size), Image.LANCZOS)
        
        # Get pixel data and compute average
        pixels = list(image.getdata())
        avg = sum(pixels) / len(pixels)
        
        # Create hash based on pixels above/below average
        bits = [1 if pixel >= avg else 0 for pixel in pixels]
        
        # Convert to hex string
        hex_string = []
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            decimal_value = sum([bit * (2 ** (7-j)) for j, bit in enumerate(byte)])
            hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
        
        return ''.join(hex_string)
    except Exception as e:
        print(f"⚠️ Could not compute aHash: {e}")
        return None


def hamming_distance(hash1, hash2):
    """Calculate Hamming distance between two hashes"""
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return float('inf')
    
    try:
        # Convert hex strings to binary and count differences
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    except:
        return float('inf')


def download_image_as_pil(url):
    """Download image from URL and return as PIL Image"""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception as e:
        print(f"⚠️ Could not download image {url}: {e}")
        return None


def calculate_image_similarity_batch(target_url, compare_urls, similarity_threshold=0.85, max_workers=10):
    """
    Calculate similarity between target image and multiple comparison images in parallel
    Returns list of (url, similarity_score, is_match) tuples
    """
    if not compare_urls:
        return []
    
    print(f"🚀 Starting parallel similarity check for {len(compare_urls)} images with {max_workers} workers")
    
    # Download target image once
    target_img = download_image_as_pil(target_url)
    if not target_img:
        print(f"⚠️ Could not download target image: {target_url}")
        return []
    
    # Pre-calculate target hashes once
    target_dhash = dhash(target_img)
    target_ahash = ahash(target_img)
    
    if not target_dhash or not target_ahash:
        print("⚠️ Could not calculate target image hashes")
        return []
    
    def check_single_similarity(compare_url):
        """Check similarity for a single image"""
        try:
            compare_img = download_image_as_pil(compare_url)
            if not compare_img:
                return (compare_url, 0.0, False)
            
            compare_dhash = dhash(compare_img)
            compare_ahash = ahash(compare_img)
            
            if not compare_dhash or not compare_ahash:
                return (compare_url, 0.0, False)
            
            # Calculate Hamming distances
            dhash_distance = hamming_distance(target_dhash, compare_dhash)
            ahash_distance = hamming_distance(target_ahash, compare_ahash)
            
            # Convert to similarity scores
            max_distance = len(target_dhash) * 4
            dhash_similarity = 1 - (dhash_distance / max_distance)
            ahash_similarity = 1 - (ahash_distance / max_distance)
            
            # Average the similarity scores
            avg_similarity = (dhash_similarity + ahash_similarity) / 2
            is_match = avg_similarity >= similarity_threshold
            
            print(f"🔍 {compare_url[:60]}... → Similarity: {avg_similarity:.3f} {'✅' if is_match else '❌'}")
            
            return (compare_url, avg_similarity, is_match)
            
        except Exception as e:
            print(f"⚠️ Error checking similarity for {compare_url}: {e}")
            return (compare_url, 0.0, False)
    
    # Process images in parallel
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_url = {executor.submit(check_single_similarity, url): url for url in compare_urls}
        
        # Collect results as they complete
        for future in as_completed(future_to_url):
            result = future.result()
            results.append(result)
            
            # Early exit if we found a match
            if result[2]:  # is_match
                print(f"🎯 Found match! Cancelling remaining tasks...")
                # Cancel remaining futures
                for f in future_to_url:
                    if not f.done():
                        f.cancel()
                break
    
    # Sort by similarity score (highest first)
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def calculate_image_similarity(target_url, compare_url, similarity_threshold=0.85):
    """
    Calculate similarity between two images using perceptual hashing
    Returns True if images are similar above threshold
    """
    results = calculate_image_similarity_batch(target_url, [compare_url], similarity_threshold, max_workers=1)
    if results:
        return results[0][2]  # Return is_match boolean
    return False


def find_image_by_similarity(driver, target_image_url, similarity_threshold=0.85, max_workers=10):
    """Find an image element by visual similarity using parallel processing"""
    print(f"🔍 Searching for similar images to: {target_image_url}")
    
    images = driver.find_elements(By.TAG_NAME, "img")
    print(f"📊 Found {len(images)} image elements on page")
    
    # Collect all URLs to check
    urls_to_check = []
    url_to_element = {}  # Map URLs back to their elements
    
    for i, img in enumerate(images):
        src = img.get_attribute("src") or ""
        if src.lower().endswith(VALID_EXTENSIONS):
            urls_to_check.append(src)
            url_to_element[src] = img

        srcset = img.get_attribute("srcset") or ""
        for s in srcset.split(","):
            parts = s.strip().split()
            if parts:  # Check if split() returned any parts
                url = parts[0]
                if url.lower().endswith(VALID_EXTENSIONS):
                    urls_to_check.append(url)
                    url_to_element[url] = img
    
    if not urls_to_check:
        print("❌ No valid image URLs found on page")
        return None
    
    print(f"🔍 Checking {len(urls_to_check)} images in parallel...")
    
    # Process all images in parallel
    results = calculate_image_similarity_batch(target_image_url, urls_to_check, similarity_threshold, max_workers)
    
    # Find the first match (results are sorted by similarity score)
    for url, similarity, is_match in results:
        if is_match:
            print(f"✅ Found similar image above threshold {similarity_threshold}: {url}")
            return url_to_element.get(url)
    
    print(f"❌ No similar images found above threshold {similarity_threshold}")
    
    # Print top 3 closest matches for debugging
    if results:
        print("🔍 Top 3 closest matches:")
        for i, (url, similarity, is_match) in enumerate(results[:3]):
            print(f"   {i+1}. {similarity:.3f} - {url[:80]}...")
    
    return None


def scroll_and_search_image(driver, target_image_url, max_scrolls=10, wait_per_scroll=1.0, similarity_threshold=0.85, max_workers=10):
    """
    Scroll page in increments and search for target image using visual similarity.
    Note: URL matching should be done before calling this function for optimization.
    """
    # Try visual similarity search with parallel processing
    print(f"🔍 Starting visual similarity search (threshold: {similarity_threshold}, workers: {max_workers})...")
    driver.execute_script("window.scrollTo(0, 0);")
    viewport_height = driver.execute_script("return window.innerHeight")
    scroll_step = viewport_height * 0.8
    current_position = 0

    for scroll_attempt in range(max_scrolls):
        print(f"🔍 Similarity search attempt {scroll_attempt + 1}/{max_scrolls}")
        image_element = find_image_by_similarity(driver, target_image_url, similarity_threshold, max_workers)
        if image_element:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", image_element)
            time.sleep(0.3)
            return image_element

        current_position += scroll_step
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        time.sleep(wait_per_scroll)

        scroll_height = driver.execute_script("return document.body.scrollHeight")
        if current_position >= scroll_height:
            break

    # Final attempt at bottom of page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(wait_per_scroll)
    
    # Try similarity method one more time at the bottom
    return find_image_by_similarity(driver, target_image_url, similarity_threshold, max_workers)
