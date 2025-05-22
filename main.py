from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import re
from datetime import datetime
from urllib.parse import unquote, urlparse
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import requests

# Platform identification mapping (unchanged)
PLATFORM_MAPPING = {
    ("https://static.xx.fbcdn.net/rsrc.php/v4/yV/r/OLar8kmsCmm.png", "0px -1188px"): "Facebook",
    ("https://static.xx.fbcdn.net/rsrc.php/v4/yV/r/OLar8kmsCmm.png", "0px -1201px"): "Instagram",
    ("https://static.xx.fbcdn.net/rsrc.php/v4/yO/r/ZuVkzM77JQ-.png", "-68px -189px"): "Audience Network",
    ("https://static.xx.fbcdn.net/rsrc.php/v4/y5/r/7Ia52m_bDk0.png", "-246px -280px"): "Messenger",
    ("https://static.xx.fbcdn.net/rsrc.php/v4/yO/r/ZuVkzM77JQ-.png", "-56px -206px"): "Financial products and services",
    ("https://static.xx.fbcdn.net/rsrc.php/v4/yV/r/OLar8kmsCmm.png", "0px -1214px"): "Thread"
}
CATEGORY_MAPPING = {
    ("https://static.xx.fbcdn.net/rsrc.php/v4/y5/r/7Ia52m_bDk0.png", "-189px -384px"): "Employment",
    ("https://static.xx.fbcdn.net/rsrc.php/v4/y5/r/7Ia52m_bDk0.png", "-32px -401px"): "Housing",
    ("https://static.xx.fbcdn.net/rsrc.php/v4/yO/r/ZuVkzM77JQ-.png", "-56px -206px"): "Financial products and services",
}

def get_current_ip():
    """Get the current public IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json')
        return response.json()['ip']
    except Exception as e:
        return f"Error getting IP: {str(e)}"

# Helper function to process a single ad (extracted from main loop)
def process_single_ad(ad_element):
    ad_data = {}
    try:
        # Extract all the same fields as the main ad processing
        # Library ID
        library_id_element = ad_element.find_element(By.XPATH, './/div[contains(@class, "x1rg5ohu x67bb7w")]/span[contains(text(), "Library ID:")]')
        ad_data["library_id"] = library_id_element.text.replace("Library ID: ", "").strip()
        
        # Started running date
        try:
            started_running_element = ad_element.find_element(By.XPATH, './/span[contains(text(), "Started running on")]')
            full_text = started_running_element.text.strip()
            started_running_match = re.search(r'Started running on (.*?)(?:·|$)', full_text)
            if started_running_match:
                started_running_text = started_running_match.group(1).strip()
                try:
                    ad_data["started_running"] = datetime.strptime(started_running_text, "%b %d, %Y").strftime("%Y-%m-%d")
                except ValueError:
                    ad_data["started_running"] = datetime.strptime(started_running_text, "%d %b %Y").strftime("%Y-%m-%d")
        except:
            ad_data["started_running"] = None
        
        # [Add all other field extractions from main ad processing...]
        
        # URL & CTA
        try:
            link_container = ad_element.find_element(By.XPATH, './/a[contains(@class, "x1hl2dhg") and contains(@class, "x1lku1pv")]')
            # Look for the CTA text within the link container
            cta_text_element = link_container.find_element(By.XPATH, './/div[contains(@class, "x8t9es0") and contains(@class, "x1fvot60") and contains(@class, "xxio538")]')
            cta_text = cta_text_element.text.strip()
            
            if cta_text:
                ad_data["cta_button_text"] = cta_text
            else:
                # Fallback to older method if the text is empty
                raise NoSuchElementException("Empty CTA text")
                
        except NoSuchElementException:
            # Fallback to the original method if we can't find CTA in the link container
            try:
                cta_container = child_div.find_element(By.XPATH, './/div[contains(@class, "x6s0dn4") and contains(@class, "x2izyaf")]')
                cta_div = cta_container.find_element(By.XPATH, './/div[contains(@class, "x2lah0s")]')
                cta_text_element = cta_div.find_element(By.XPATH, './/div[contains(@class, "x8t9es0") and contains(@class, "x1fvot60")]')
                cta_text = cta_text_element.text.strip()
                ad_data["cta_button_text"] = cta_text
            except NoSuchElementException:
                ad_data["cta_button_text"] = None
        
        return ad_data
    except Exception as e:
        print(f"Error processing ad: {str(e)}")
        return None
    

def scrape_facebook_ads(url, output_file=None, headless=True):
    """
    Scrape Facebook Ads Library for a given page URL.
    
    Args:
        url (str): The Facebook Ads Library URL to scrape
        output_file (str, optional): Path to save the JSON output. If None, won't save to file
        headless (bool): Whether to run Chrome in headless mode
    
    Returns:
        dict: Dictionary containing the scraped ads data
    """
    start_time = time.time()
    
    # Get starting IP address
    starting_ip = get_current_ip()
    print(f"\n🌐 Starting IP Address: {starting_ip}")
    
    # Chrome options
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # Initialize driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)

    try:
        print(f"Navigating to {url}...")
        driver.get(url)

        print("Waiting for initial ad content to load...")
        initial_content_locator = (By.CSS_SELECTOR, 'div[class="xrvj5dj x18m771g x1p5oq8j xbxaen2 x18d9i69 x1u72gb5 xtqikln x1na6gtj x1jr1mh3 xm39877 x7sq92a xxy4fzi"]')
        try:
            wait.until(EC.presence_of_element_located(initial_content_locator))
            print("✅ Initial content loaded.")
        except TimeoutException:
            print("⚠️ Timed out waiting for initial content. Proceeding anyway...")

        # Target XPaths for end-of-list marker
        target_xpaths = [
            "/html/body/div[1]/div/div/div/div/div/div/div[1]/div/div/div/div[5]/div[2]/div[9]/div[3]/div[2]/div",
            "/html/body/div[1]/div/div/div/div/div/div[1]/div/div/div/div[6]/div[2]/div[9]/div[3]/div[2]/div"
        ]

        print("Starting scroll loop to load all ads...")
        scroll_count = 0
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_pause_time = 0.7
        max_scroll_attempts_at_bottom = 3
        attempts_at_bottom = 0

        # scrolling part
        while attempts_at_bottom < max_scroll_attempts_at_bottom:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            scroll_count += 1
            
            # --- Optimization: Shorter, dynamic wait ---
            time.sleep(scroll_pause_time) # Wait briefly for page to load

            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            element_found = False
            # Let's only check for the end element when the height hasn't changed
            if new_height == last_height:
              for xpath in target_xpaths:
                  try:
                      # Use a very short wait for the end element check
                      WebDriverWait(driver, 0.5).until(EC.presence_of_element_located((By.XPATH, xpath)))
                      print(f"✅ End-of-list element found using XPath: {xpath}")
                      element_found = True
                      break
                  except (NoSuchElementException, TimeoutException):
                      continue

            if element_found:
                print(f"✅ End-of-list element found after {scroll_count} scrolls. Stopping scroll.")
                break

            if new_height == last_height:
                attempts_at_bottom += 1
                print(f"Scroll height ({new_height}) hasn't changed. Attempt {attempts_at_bottom}/{max_scroll_attempts_at_bottom} at bottom...")
            else:
                attempts_at_bottom = 0 # Reset counter if height changed
                print(f"Scrolled {scroll_count} time(s). New height: {new_height}")

            last_height = new_height

            # Optional safety break: Prevent infinite loops
            if scroll_count > 500: # Adjust limit as needed
                print("⚠️ Reached maximum scroll limit (500). Stopping scroll.")
                break

        if not element_found and attempts_at_bottom >= max_scroll_attempts_at_bottom:
             print("🏁 Reached bottom of page (height stabilized).")

        scroll_time = time.time()
        print(f"Scrolling finished in {scroll_time - start_time:.2f} seconds.")

        print("Waiting briefly for final elements to render...")
        time.sleep(1) # Short pause just in case rendering is slightly delayed

        # Count divs with the first class (unchanged selector logic)
        target_class_1 = "x6s0dn4 x78zum5 xdt5ytf xl56j7k x1n2onr6 x1ja2u2z x19gl646 xbumo9q"
        try:
            divs_1 = driver.find_elements(By.CSS_SELECTOR, f'div[class="{target_class_1}"]')
            print(f"Total <div> elements with target class 1: {len(divs_1)}")
        except Exception as e:
            print(f"Error finding elements with target class 1: {e}")
            divs_1 = []

        # Count divs with the second class (unchanged selector logic)
        target_class_2 = "xrvj5dj x18m771g x1p5oq8j xbxaen2 x18d9i69 x1u72gb5 xtqikln x1na6gtj x1jr1mh3 xm39877 x7sq92a xxy4fzi"
        try:
            divs_2 = driver.find_elements(By.CSS_SELECTOR, f'div[class="{target_class_2}"]')
            print(f"Total <div> elements (ad groups) with target class 2: {len(divs_2)}")
        except Exception as e:
            print(f"Error finding elements with target class 2: {e}")
            divs_2 = []


        # Dictionary to store all ads data
        ads_data = {}
        total_processed = 0
        total_child_ads_found = 0

        # For each target_class_2 div, count xh8yej3 children and process them (unchanged logic, potential speedup from faster page load/scrolling)
        print("\nProcessing ads...")
        for i, div in enumerate(divs_2, 1):
            try:
                child_divs = div.find_elements(By.XPATH, './div[contains(@class, "xh8yej3")]')
                num_children = len(child_divs)
                total_child_ads_found += num_children

                # Process each xh8yej3 child
                for j, child_div in enumerate(child_divs, 1):
                    current_ad_id_for_logging = f"Group {i}, Ad {j}"
                    library_id = None # Initialize library_id for potential error logging
                    try:
                        main_container = child_div.find_element(By.XPATH, './/div[contains(@class, "x78zum5 xdt5ytf x2lwn1j xeuugli")]')

                        # Extract Library ID
                        library_id_element = main_container.find_element(By.XPATH, './/div[contains(@class, "x1rg5ohu x67bb7w")]/span[contains(text(), "Library ID:")]')
                        library_id = library_id_element.text.replace("Library ID: ", "").strip()
                        current_ad_id_for_logging = library_id # Update logging ID once found

                        # if library_id in ads_data:
                        #     # print(f"Skipping duplicate Library ID: {library_id}")
                        #     continue

                        # Initialize ad data with library_id
                        ad_data = {"library_id": library_id}

                        # Extract started_running, total_active_time
                        try:
                            started_running_element = main_container.find_element(By.XPATH, './/span[contains(text(), "Started running on")]')
                            full_text = started_running_element.text.strip()
                            
                            # Extract the started running date
                            started_running_match = re.search(r'Started running on (.*?)(?:·|$)', full_text)
                            if started_running_match:
                                started_running_text = started_running_match.group(1).strip()
                                # Try parsing with comma first, then without if that fails
                                try:
                                    started_running_date = datetime.strptime(started_running_text, "%b %d, %Y").strftime("%Y-%m-%d")
                                except ValueError:
                                    started_running_date = datetime.strptime(started_running_text, "%d %b %Y").strftime("%Y-%m-%d")
                                ad_data["started_running"] = started_running_date
                            else:
                                ad_data["started_running"] = None
                            
                            # Extract the total active time if present
                            active_time_match = re.search(r'Total active time\s+(.+?)(?:$|\s*·)', full_text)
                            if active_time_match:
                                active_time = active_time_match.group(1).strip()
                                ad_data["total_active_time"] = active_time
                            else:
                                ad_data["total_active_time"] = None
                                
                        except NoSuchElementException:
                            # print(f"Started running date not found for ad {current_ad_id_for_logging}")
                            ad_data["started_running"] = None
                            ad_data["total_active_time"] = None
                        except Exception as e:
                            print(f"⚠️ Error parsing started running date for ad {current_ad_id_for_logging}: {str(e)}")
                            ad_data["started_running"] = None
                            ad_data["total_active_time"] = None

                        # Extract Platforms icons
                        platforms_data = []
                        try:
                            platforms_div = main_container.find_element(By.XPATH, './/span[contains(text(), "Platforms")]/following-sibling::div[1]') # Use [1] for immediate sibling
                            platform_icons = platforms_div.find_elements(By.XPATH, './/div[contains(@class, "xtwfq29")]')

                            for icon in platform_icons:
                                try:
                                    style = icon.get_attribute("style")
                                    if not style: continue # Skip if no style attribute
                                    mask_image_match = re.search(r'mask-image: url\("([^"]+)"\)', style)
                                    mask_pos_match = re.search(r'mask-position: ([^;]+)', style)
                                    mask_image = mask_image_match.group(1) if mask_image_match else None
                                    mask_position = mask_pos_match.group(1).strip() if mask_pos_match else None # Added strip()

                                    # Identify platform name
                                    platform_name = PLATFORM_MAPPING.get((mask_image, mask_position)) # More direct lookup

                                    # platforms_data.append({
                                    #     # "style": style, # Usually not needed in final data
                                    #     "mask_image": mask_image,
                                    #     "mask_position": mask_position,
                                    #     "platform_name": platform_name if platform_name else "Unknown"
                                    # })
                                    platforms_data.append(
                                        # "style": style, # Usually not needed in final data
                                        platform_name 
                                    )
                                except Exception as e:
                                    # print(f"Could not process a platform icon for ad {current_ad_id_for_logging}: {str(e)}")
                                    continue
                        except NoSuchElementException:
                            # print(f"Platforms section not found for ad {current_ad_id_for_logging}")
                            pass # okay if this section is missing
                        except Exception as e:
                             print(f"Error extracting platforms for ad {current_ad_id_for_logging}: {str(e)}")

                        ad_data["platforms"] = platforms_data

                        # Extract Categories icon
                        category_data = []
                        try:
                            # Find the Categories span first
                            categories_span = main_container.find_element(By.XPATH, './/span[contains(text(), "Categories")]')
                            
                            # Find all sibling divs with class x1rg5ohu x67bb7w that come after the Categories span
                            category_divs = categories_span.find_elements(By.XPATH, './following-sibling::div[contains(@class, "x1rg5ohu") and contains(@class, "x67bb7w")]')
                            
                            for category_div in category_divs:
                                try:
                                    # Find the icon div within each category div
                                    icon_div = category_div.find_element(By.XPATH, './/div[contains(@class, "xtwfq29")]')
                                    style = icon_div.get_attribute("style")
                                    
                                    if style:
                                        mask_image_match = re.search(r'mask-image: url\("([^"]+)"\)', style)
                                        mask_pos_match = re.search(r'mask-position: ([^;]+)', style)
                                        mask_image = mask_image_match.group(1) if mask_image_match else None
                                        mask_position = mask_pos_match.group(1).strip() if mask_pos_match else None
                                        
                                        # Identify category name from mapping
                                        category_name = CATEGORY_MAPPING.get((mask_image, mask_position), "Unknown")
                                        
                                        # category_data.append({
                                        #     "mask_image": mask_image,
                                        #     "mask_position": mask_position,
                                        #     "category_name": category_name
                                        # })
                                        category_data.append(
                                            category_name
                                        )
                                except Exception as e:
                                    print(f"Could not process a category icon: {str(e)}")
                                    continue
                                
                        except NoSuchElementException:
                            pass  # No categories section found
                        except Exception as e:
                            print(f"Error extracting categories: {str(e)}")

                        ad_data["categories"] = category_data
                        
                        # Extract Ads count
                        try:
                            # Adjusted XPath to be more specific to the 'N ads use this creative and text.' structure
                            ads_count_element = main_container.find_element(By.XPATH, './/div[contains(@class, "x6s0dn4 x78zum5 xsag5q8")]//strong')
                            ads_count = ads_count_element.text.strip() # Should just be the number
                            number_match = re.search(r'(\d+)', ads_count)
                            if number_match:
                                ads_count = number_match.group(1)  # This will be just "4"
                            else:
                                ads_count = None
                                
                            ad_data["ads_count"] = ads_count

                            # if ads count avalible, check for nested ads
                            if ads_count and int(ads_count) > 1:
                                ad_data["nested_ads"] = {}
                                try:
                                    # Click the "See summary details" button
                                    see_details_button = child_div.find_element(By.XPATH, './/div[contains(@class, "x193iq5w")]//div[@role="button"]//div[contains(text(), "See summary details")]')
                                    driver.execute_script("arguments[0].click();", see_details_button)
                                    time.sleep(2)  # Wait for popup to appear
                                    
                                    # Find the popup container
                                    popup_container = see_details_button.find_element(By.XPATH, '//div[contains(@class, "x78zum5 xdt5ytf x1t137rt x71s49j x1ja2u2z x9ri80z xofcydl x6o7n8i xnnyp6c x12w9bfk xnn1q72 x1ey2m1c x13a6bvl xlv8yqo xixxii4 x1i64zmx x1emribx")]')

                                    # Find the scrollable container with the specific CSS class
                                    scrollable_container = popup_container.find_element(
                                        By.XPATH,
                                        '/html/body/div[6]/div[1]/div[1]/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div'
                                    )

                                    # Get the initial count of nested ads (Number of ads written in pop-up heading)
                                    nested_sub_ads_element = driver.find_element(
                                        By.XPATH, 
                                        '/html/body/div[6]/div[1]/div[1]/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div/div/div/div[2]/span[1]'
                                    )
                                    nested_sub_ads_element_count = nested_sub_ads_element.text.strip()
                                    number_matched_nested_sub_ads_count = re.search(r'(\d+)', nested_sub_ads_element_count)
                                    int_nested_sub_ads_count = int(number_matched_nested_sub_ads_count.group(1)) if number_matched_nested_sub_ads_count else 0

                                    # Scroll to load all nested ads
                                    last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_container)
                                    attempts = 0
                                    attempts_continue = True
                                    # max_attempts = 5  # Prevent infinite scrolling

                                    while attempts_continue:

                                        # Scroll to bottom
                                        driver.execute_script(
                                            "arguments[0].scrollTo(0, arguments[0].scrollHeight)", 
                                            scrollable_container
                                        )
                                        time.sleep(1)  # Wait for content to load
                                        
                                        # Check if we've loaded all ads
                                        nested_ads = driver.find_elements(
                                            By.XPATH,
                                            '/html/body/div[6]/div[1]/div[1]/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div/div/div/div[3]/div/div[1]/div[1]/div'
                                        )
                                        
                                        if len(nested_ads) == int_nested_sub_ads_count:
                                            break
                                            
                                        # Check if we've reached the bottom
                                        new_height = driver.execute_script(
                                            "return arguments[0].scrollHeight", 
                                            scrollable_container
                                        )
                                        # if new_height == last_height:
                                        #     break
                                        last_height = new_height
                                        
                                        attempts += 1

                                    print(f"Total attempts to scroll: {attempts}")
                                    # Process the nested ads
                                    for nested_ad in nested_ads[1:]:
                                        try:
                                            nested_ad_data = process_single_ad(nested_ad)
                                            if nested_ad_data:
                                                ad_data["nested_ads"][nested_ad_data["library_id"]] = nested_ad_data
                                        except Exception as e:
                                            print(f"Error processing nested ad: {str(e)}")
                                            continue

                                    # Close the popup by pressing ESC key (more reliable than finding close button)
                                    from selenium.webdriver.common.keys import Keys
                                    actions = ActionChains(driver)
                                    actions.send_keys(Keys.ESCAPE).perform()
                                    time.sleep(1)  # Small delay to ensure popup closes
                                    
                                    print(f"Error processing nested ads for {library_id}: {str(e)}")
                                    # Try to close popup if it might be open
                                    try:
                                        from selenium.webdriver.common.keys import Keys
                                        actions = ActionChains(driver)
                                        actions.send_keys(Keys.ESCAPE).perform()
                                    except:
                                        pass
                                except Exception as e:
                                    print(f"Error processing nested ads for {library_id}: {str(e)}")
                
                        except NoSuchElementException:
                            ad_data["ads_count"] = None
                        except Exception as e:
                            print(f"Error extracting ads count for ad {current_ad_id_for_logging}: {str(e)}")
                            ad_data["ads_count"] = None

                        # Add to main dictionary with library_id as key
                        ads_data[library_id] = ad_data
                        total_processed += 1

                        # Extract Ad Text Content
                        try:
                            # Find the parent div containing the text first, more reliable
                            ad_text_container = child_div.find_element(By.XPATH, './/div[@data-ad-preview="message" or contains(@style, "white-space: pre-wrap")]')
                            # Get all text within, handles cases with multiple spans or line breaks better
                            ad_data["ad_text"] = ad_text_container.text.strip()
                        except NoSuchElementException:
                            # print(f"Ad text not found for ad {current_ad_id_for_logging}")
                            ad_data["ad_text"] = None
                        except Exception as e:
                             print(f"Error extracting ad text for ad {current_ad_id_for_logging}: {str(e)}")
                             ad_data["ad_text"] = None

                        # extract media
                        try:
                            # First find the xh8yej3 div inside child_div if we're not already looking at it
                            # xh8yej3_div = child_div
                            # if "xh8yej3" not in child_div.get_attribute("class"):
                            
                            # Try to find the link container first as it often contains both media and CTA
                            link_container = child_div.find_element(By.XPATH, './/a[contains(@class, "x1hl2dhg") and contains(@class, "x1lku1pv")]')
                            
                            # Extract and store the link URL
                            link_url = link_container.get_attribute('href')
                            decoded_url = unquote(link_url)
                            
                            # Parse the URL to get the 'u' parameter value
                            parsed_url = urlparse(decoded_url)
                            query_params = parsed_url.query
                            if 'u=' in query_params:
                                # Get the full URL from the u parameter (properly decoded)
                                actual_url = unquote(query_params.split('u=')[1].split('&')[0])
                            else:
                                # Try another method if u= isn't in the query params
                                actual_url = unquote(decoded_url.split('u=')[1].split('&')[0]) if 'u=' in decoded_url else decoded_url
                            
                            ad_data["destination_url"] = actual_url if actual_url else None

                            # Extract media from this link container
                            ad_data["media_type"] = None
                            ad_data["media_url"] = None
                            ad_data["thumbnail_url"] = None
                            
                            # Check for video within the link container
                            try:
                                video_element = child_div.find_element(By.XPATH, './/video')
                                media_url = video_element.get_attribute('src')
                                if media_url: # Ensure src is not empty
                                   ad_data["media_type"] = "video"
                                   ad_data["media_url"] = media_url
                                   poster_url = video_element.get_attribute('poster')
                                   if poster_url:
                                       ad_data["thumbnail_url"] = poster_url
                            except NoSuchElementException:
                                # If no video, try image with more specific targeting
                                try:
                                    img_element = link_container.find_element(By.XPATH, './/img[contains(@class, "x168nmei") or contains(@class, "_8nqq")]')
                                    media_url = img_element.get_attribute('src')
                                    if media_url:
                                        ad_data["media_type"] = "image"
                                        ad_data["media_url"] = media_url
                                except NoSuchElementException:
                                    # Fallback to any image within the link container
                                    try:
                                        img_element = link_container.find_element(By.XPATH, './/img')
                                        media_url = img_element.get_attribute('src')
                                        if media_url:
                                            ad_data["media_type"] = "image"
                                            ad_data["media_url"] = media_url
                                    except NoSuchElementException:
                                        pass  # No media found
                        
                            # Extract CTA Button text - look within the same link container first
                            try:
                                # Look for the CTA text within the link container
                                cta_text_element = link_container.find_element(By.XPATH, './/div[contains(@class, "x8t9es0") and contains(@class, "x1fvot60") and contains(@class, "xxio538")]')
                                cta_text = cta_text_element.text.strip()
                                
                                if cta_text:
                                    ad_data["cta_button_text"] = cta_text
                                else:
                                    # Fallback to older method if the text is empty
                                    raise NoSuchElementException("Empty CTA text")
                                    
                            except NoSuchElementException:
                                # Fallback to the original method if we can't find CTA in the link container
                                try:
                                    cta_container = child_div.find_element(By.XPATH, './/div[contains(@class, "x6s0dn4") and contains(@class, "x2izyaf")]')
                                    cta_div = cta_container.find_element(By.XPATH, './/div[contains(@class, "x2lah0s")]')
                                    cta_text_element = cta_div.find_element(By.XPATH, './/div[contains(@class, "x8t9es0") and contains(@class, "x1fvot60")]')
                                    cta_text = cta_text_element.text.strip()
                                    ad_data["cta_button_text"] = cta_text
                                except NoSuchElementException:
                                    ad_data["cta_button_text"] = None
                            except Exception as e:
                                print(f"Error extracting media or CTA for ad {current_ad_id_for_logging}: {str(e)}")
                                # Initialize with None if not already set
                                if "media_type" not in ad_data:
                                    ad_data["media_type"] = None
                                if "media_url" not in ad_data:
                                    ad_data["media_url"] = None
                                if "thumbnail_url" not in ad_data:
                                    ad_data["thumbnail_url"] = None
                                if "cta_button_text" not in ad_data:
                                    ad_data["cta_button_text"] = None
                            except Exception as e:
                                 print(f"Error extracting media for ad {current_ad_id_for_logging}: {str(e)}")

                            # Extract CTA Button text
                            try:
                                # Find the div with the specific class that contains the CTA button
                                cta_container = child_div.find_element(By.XPATH, './/div[contains(@class, "x6s0dn4 x2izyaf x78zum5 x1qughib x168nmei x13lgxp2 x30kzoy x9jhf4c xexx8yu x1sxyh0 xwib8y2 xurb0ha")]')
                                
                                # Look for the button text within the second div (with class x2lah0s)
                                cta_div = cta_container.find_element(By.XPATH, './/div[contains(@class, "x2lah0s")]')
                                
                                # Find the text content within the button element
                                # This targets the text that's inside the button's visible content area
                                cta_text_element = cta_div.find_element(By.XPATH, './/div[contains(@class, "x8t9es0 x1fvot60 xxio538 x1heor9g xuxw1ft x6ikm8r x10wlt62 xlyipyv x1h4wwuj x1pd3egz xeuugli")]')
                                cta_text = cta_text_element.text.strip()
                                
                                ad_data["cta_button_text"] = cta_text
                            except NoSuchElementException:
                                # print(f"CTA button not found for ad {current_ad_id_for_logging}")
                                ad_data["cta_button_text"] = None
                            except Exception as e:
                                print(f"Error extracting CTA button text for ad {current_ad_id_for_logging}: {str(e)}")
                                ad_data["cta_button_text"] = None

                            # Add to main dictionary with library_id as key
                            ads_data[library_id] = ad_data
                            total_processed += 1
                            # Reduce console noise: print progress periodically instead of every ad
                            if total_processed % 50 == 0:
                                print(f"Processed {total_processed}/{total_child_ads_found} ads...")

                        except NoSuchElementException as e:
                            # This might happen if the structure is unexpected, often failure to find library ID
                            print(f"Critical element missing for ad {current_ad_id_for_logging}, skipping. Error: {e.msg}")
                            continue # Skip this child_div entirely if critical info (like ID) is missing
                        except Exception as e:
                            print(f"Unexpected error processing ad {current_ad_id_for_logging}: {str(e)}")
                            continue # Skip this child_div on unexpected errors
                    except Exception as e:
                        print(f"Error processing ad {current_ad_id_for_logging}: {str(e)}")
                        continue
            except Exception as e:
                print(f"Error finding or processing xh8yej3 children for div group {i}: {str(e)}")
                continue

        processing_time = time.time()
        print(f"\nData extraction finished in {processing_time - scroll_time:.2f} seconds.")

        # Create final output
        final_output = {
            "total_ads_found": total_child_ads_found,
            "total_ads_processed": len(ads_data),
            "ads_data": ads_data,
            "scraping_time": time.time() - start_time,
            "starting_ip": starting_ip,
            "ending_ip": get_current_ip()  # Get ending IP
        }

        # Save to JSON file if output_file is provided
        if output_file:
            try:
                with open(output_file, "w", encoding='utf-8') as f:
                    json.dump(final_output, f, indent=4, ensure_ascii=False)
                print(f"Data saved to {output_file}")
            except Exception as e:
                print(f"Error saving data to JSON file: {e}")

        # Get and print ending IP address
        ending_ip = get_current_ip()
        print(f"\n🌐 Ending IP Address: {ending_ip}")
        
        return final_output

    except Exception as e:
        print(f"An error occurred during scraping: {str(e)}")
        # Get IP even if there's an error
        ending_ip = get_current_ip()
        print(f"\n🌐 Ending IP Address (after error): {ending_ip}")
        return {
            "error": str(e),
            "total_ads_found": 0,
            "total_ads_processed": 0,
            "ads_data": {},
            "scraping_time": time.time() - start_time,
            "starting_ip": starting_ip,
            "ending_ip": ending_ip
        }
        # ...
    finally:
        driver.quit()

# Example usage when run directly
if __name__ == "__main__":
    test_url = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&source=page-transparency-widget&view_all_page_id=101111318763935"
    result = scrape_facebook_ads(
        url=test_url,
        output_file="ads_data_optimized.json",
        headless=False
    )
    print(f"\nTotal ads processed: {result['total_ads_processed']}")
    print(f"Total scraping time: {result['scraping_time']:.2f} seconds")
    print(f"Starting IP: {result['starting_ip']}")
    print(f"Ending IP: {result['ending_ip']}")

