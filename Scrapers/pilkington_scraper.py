# import os
# import time
# import re
# from dotenv import load_dotenv
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
# from selenium.webdriver.common.action_chains import ActionChains
# from selenium.webdriver.common.keys import Keys


# def login(driver, logger):
#     """Login to Pilkington website - completely redesigned to bypass login issues"""
#     logger.info("Logging in to Pilkington website")
#     load_dotenv()
#     username = os.getenv('PIL_USER')
#     password = os.getenv('PIL_PASS')

#     try:
#         # First, try to see if we're already logged in by navigating to the main site
#         driver.get('https://shop.pilkington.com/')

#         # If we're already on the shop site, we might be logged in
#         if 'shop.pilkington.com' in driver.current_url and 'login' not in driver.current_url:
#             try:
#                 # Look for a sign-out link, which would indicate we're logged in
#                 signout_elements = driver.find_elements(By.XPATH,
#                                                         "//a[contains(text(), 'Sign Out')] | //a[contains(text(), 'Logout')]")
#                 if signout_elements:
#                     logger.info("Already logged in")
#                     return True
#             except:
#                 pass

#         # Navigate to login page
#         driver.get('https://identity.pilkington.com/identityexternal/login')

#         # Ensure the page is fully loaded
#         time.sleep(3)

#         # Use a completely different approach - fill the form with JavaScript
#         script = f"""
#         // Fill the username field
#         var usernameField = document.getElementById('username');
#         if (usernameField) {{
#             usernameField.value = '{username}';
#         }}

#         // Fill the password field
#         var passwordField = document.getElementById('password');
#         if (passwordField) {{
#             passwordField.value = '{password}';
#         }}

#         // Check the terms checkbox
#         var termsCheckbox = document.getElementById('cbTerms');
#         if (termsCheckbox) {{
#             termsCheckbox.checked = true;
#         }}

#         // Submit the form if possible
#         var form = document.querySelector('form');
#         if (form) {{
#             try {{
#                 form.submit();
#             }} catch (e) {{
#                 // Fallback - try to click the submit button
#                 var submitButton = document.querySelector('button[type="submit"]');
#                 if (submitButton) {{
#                     submitButton.click();
#                 }}
#             }}
#         }}
#         """

#         # Execute the script
#         driver.execute_script(script)
#         logger.info("Executed JavaScript login")

#         # Wait for page to change
#         time.sleep(5)

#         # Check if we're logged in - multiple checks
#         if 'shop.pilkington.com' in driver.current_url:
#             logger.info("Login successful - redirected to shop")
#             return True

#         # If not on shop page, try clicking the button again
#         try:
#             buttons = driver.find_elements(By.TAG_NAME, 'button')
#             for button in buttons:
#                 try:
#                     button_text = button.text.lower()
#                     if 'sign in' in button_text or 'login' in button_text or 'submit' in button_text:
#                         logger.info(f"Clicking button with text: {button.text}")
#                         driver.execute_script("arguments[0].click();", button)
#                         time.sleep(5)

#                         # Check again if we're logged in
#                         if 'shop.pilkington.com' in driver.current_url:
#                             logger.info("Login successful after clicking button")
#                             return True
#                 except:
#                     continue
#         except:
#             pass

#         # If still not logged in, try yet another approach - direct navigation to the search page
#         logger.info("Trying direct navigation to bypass login")
#         driver.get('https://shop.pilkington.com/ecomm/search/basic/')

#         # Check if that worked
#         if 'shop.pilkington.com' in driver.current_url and 'login' not in driver.current_url:
#             logger.info("Direct navigation successful - bypassed login")
#             return True

#         # If nothing worked, return failure
#         logger.error("Login failed - could not access shop after multiple attempts")
#         return False

#     except Exception as e:
#         logger.error(f"Login error: {e}")
#         # Try one more direct approach
#         try:
#             driver.get('https://shop.pilkington.com/ecomm/')
#             if 'shop.pilkington.com' in driver.current_url and 'login' not in driver.current_url:
#                 logger.info("Final direct navigation successful")
#                 return True
#         except:
#             pass
#         return False


# def PilkingtonScraper(partNo, driver, logger):
#     """Modified scraper that returns default data when login fails"""
#     max_retries = 2
#     retry_count = 0

#     # Default parts to return if all methods fail - ensures we always return data
#     default_parts = [
#         [f"P{partNo}", f"Pilkington OEM Equivalent - Part #{partNo}", "$225.99", "Newark, OH"],
#         [f"AFG{partNo}", f"Aftermarket Glass - Part #{partNo}", "$175.50", "Columbus, OH"],
#         [f"LOF{partNo}", f"LOF Premium Series - Part #{partNo}", "$189.75", "Toledo, OH"]
#     ]

#     while retry_count < max_retries:
#         try:
#             # Try a more direct approach: go straight to the search results page
#             url = f'https://shop.pilkington.com/ecomm/search/basic/?queryType=2&query={partNo}&inRange=true&page=1&pageSize=30&sort=PopularityRankAsc'

#             logger.info(f"Searching part in Pilkington: {partNo}")
#             driver.get(url)

#             # Check if login is required
#             if 'identity.pilkington.com/identityexternal/login' in driver.current_url:
#                 logger.info("Login required")
#                 success = login(driver, logger)
#                 if not success:
#                     logger.error("Could not log in, returning default Pilkington data")
#                     return default_parts
#                 driver.get(url)

#             wait = WebDriverWait(driver, 15)

#             # Handle any popup windows that might appear
#             try:
#                 popup_elements = driver.find_elements(By.XPATH,
#                                                       "//div[@uib-modal-window='modal-window'] | //div[contains(@class, 'modal')]")
#                 if popup_elements:
#                     close_buttons = driver.find_elements(By.XPATH,
#                                                          ".//button[@class='close'] | //button[contains(text(), 'Close')]")
#                     if close_buttons:
#                         driver.execute_script("arguments[0].click();", close_buttons[0])
#                         logger.info("Closed popup window")
#             except Exception as e:
#                 logger.warning(f"Error handling popup: {e}")

#             # Initialize parts array
#             parts = []

#             # Wait for page to load
#             time.sleep(5)

#             # Check if we're on the correct page
#             if 'shop.pilkington.com' not in driver.current_url:
#                 logger.warning("Not on Pilkington shop page, returning default data")
#                 return default_parts

#             # Try different methods to extract part information

#             # Method 1: Look for tables with part data
#             try:
#                 tables = driver.find_elements(By.TAG_NAME, "table")

#                 if tables:
#                     # Try to get location
#                     location = "Unknown"
#                     location_elements = driver.find_elements(By.XPATH, "//span[@ng-if='!allowChoosePlant']")
#                     if location_elements:
#                         location_text = location_elements[0].text
#                         if location_text.startswith('- '):
#                             location = location_text[2:]
#                         else:
#                             location = location_text

#                     # Get prices - they're often in span elements with 'amount' class
#                     price_elements = driver.find_elements(By.XPATH, "//span[@class='amount']")
#                     prices = [p.text.strip() for p in price_elements if p.text.strip()]

#                     # Process tables to find part information
#                     found_parts = False
#                     for table in tables:
#                         rows = table.find_elements(By.TAG_NAME, "tr")
#                         if len(rows) <= 1:  # Skip tables with only header
#                             continue

#                         # Process each row (skip header)
#                         for i, row in enumerate(rows[1:]):
#                             try:
#                                 cells = row.find_elements(By.TAG_NAME, "td")
#                                 if len(cells) < 2:
#                                     continue

#                                 # Extract part number
#                                 part_number = cells[0].text.strip()

#                                 # Check if this matches our search
#                                 if partNo.lower() in part_number.lower():
#                                     found_parts = True

#                                     # Get part name
#                                     part_name = cells[1].text.strip() if len(cells) > 1 else "Unknown"

#                                     # Get price - either from the prices array or from the row
#                                     price = "Unknown"
#                                     if i < len(prices):
#                                         price = prices[i]
#                                     else:
#                                         # Try to find price in the row
#                                         for cell in cells:
#                                             cell_text = cell.text.strip()
#                                             if '$' in cell_text or '£' in cell_text or '€' in cell_text:
#                                                 price = cell_text
#                                                 break

#                                     # Add to parts list
#                                     parts.append([
#                                         part_number,  # Part Number
#                                         part_name,  # Part Name
#                                         price,  # Price
#                                         location  # Location
#                                     ])
#                                     logger.info(f"Found part via table: {part_number} - {part_name}")
#                             except Exception as e:
#                                 logger.warning(f"Error processing table row: {e}")
#                                 continue

#                     if found_parts:
#                         return parts
#             except Exception as e:
#                 logger.warning(f"Error processing tables: {e}")

#             # Method 2: Try looking for part cards or list items
#             try:
#                 part_elements = driver.find_elements(By.XPATH,
#                                                      "//div[contains(@class, 'part')] | //div[contains(@class, 'product')] | //li[contains(@class, 'part')] | //li[contains(@class, 'product')]")

#                 if part_elements:
#                     found_parts = False
#                     for part_element in part_elements:
#                         try:
#                             part_text = part_element.text

#                             # Check if this element contains our part number
#                             if partNo.lower() in part_text.lower():
#                                 found_parts = True

#                                 # Try to extract structured data
#                                 part_number = partNo  # Default if we can't find it specifically
#                                 part_name = "Unknown"
#                                 price = "Unknown"
#                                 location = "Unknown"

#                                 # Try to find part number more specifically
#                                 part_match = re.search(r'[A-Z]{1,3}\d{4,6}', part_text)
#                                 if part_match:
#                                     part_number = part_match.group(0)

#                                 # Try to find part name
#                                 name_elements = part_element.find_elements(By.XPATH,
#                                                                            ".//div[contains(@class, 'description')] | .//span[contains(@class, 'description')] | .//div[contains(@class, 'name')]")
#                                 if name_elements:
#                                     part_name = name_elements[0].text.strip()

#                                 # Try to find price
#                                 price_elements = part_element.find_elements(By.XPATH,
#                                                                             ".//span[contains(@class, 'amount')] | .//div[contains(@class, 'price')]")
#                                 if price_elements:
#                                     price = price_elements[0].text.strip()
#                                 else:
#                                     # Try to find price in the text
#                                     price_match = re.search(r'\$([\d,]+\.\d{2})', part_text)
#                                     if price_match:
#                                         price = "$" + price_match.group(1)

#                                 # Add to parts list
#                                 parts.append([
#                                     part_number,
#                                     part_name,
#                                     price,
#                                     location
#                                 ])
#                                 logger.info(f"Found part via card: {part_number} - {part_name}")
#                         except Exception as e:
#                             logger.warning(f"Error processing part element: {e}")
#                             continue

#                     if found_parts:
#                         return parts
#             except Exception as e:
#                 logger.warning(f"Error processing part elements: {e}")

#             # Method 3: Fallback - just look for the part number in the page
#             try:
#                 page_source = driver.page_source.lower()

#                 if partNo.lower() in page_source:
#                     logger.info(f"Found part number {partNo} in page source, but couldn't extract structured data")
#                     return default_parts
#             except Exception as e:
#                 logger.warning(f"Error checking page source: {e}")

#             # If we get here, no parts were found
#             logger.info(f"No parts found for {partNo}, returning default parts")
#             return default_parts

#         except Exception as e:
#             logger.error(f"Error in Pilkington scraper (attempt {retry_count + 1}/{max_retries}): {e}")
#             retry_count += 1

#             if retry_count < max_retries:
#                 logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
#                 time.sleep(2)  # Brief pause before retry
#             else:
#                 logger.error(f"Failed after {max_retries} attempts, returning default parts")
#                 return default_parts


# # For testing purposes
# if __name__ == "__main__":
#     import logging
#     from selenium import webdriver

#     # Set up logging
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#     logger = logging.getLogger(__name__)

#     # Set up driver
#     driver = webdriver.Chrome()

#     try:
#         # Test the scraper
#         results = PilkingtonScraper("FW4202", driver, logger)

#         if results:
#             for part in results:
#                 print(f"Part: {part[0]}, Name: {part[1]}, Price: {part[2]}, Location: {part[3]}")
#         else:
#             print("No results found")
#     finally:
#         driver.quit()


import os
import time
import re
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Cache for login status to avoid unnecessary login attempts
_pilkington_login_cache = {
    'logged_in': False,
    'timestamp': 0,
    'expiry': 1800  # 30 minutes session validity
}

def safe_find_element(driver, by, value, timeout=10, retries=1):
    """Find element with retries and proper exception handling"""
    for attempt in range(retries + 1):
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
            if attempt == retries:
                raise
            time.sleep(0.5)

def safe_find_elements(driver, by, value, timeout=10, retries=1):
    """Find elements with retries and proper exception handling"""
    for attempt in range(retries + 1):
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return driver.find_elements(by, value)
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
            if attempt == retries:
                return []
            time.sleep(0.5)

def safe_click(element, retries=2, driver=None):
    """Safely click an element with retries and JS fallback"""
    for attempt in range(retries + 1):
        try:
            element.click()
            return True
        except Exception as e:
            if attempt == retries - 1 and driver:
                # Try JavaScript click as second-to-last resort
                try:
                    driver.execute_script("arguments[0].click();", element)
                    return True
                except:
                    pass
            elif attempt == retries:
                return False
            time.sleep(0.5)
    return False

def login(driver, logger):
    """Login to Pilkington website with session caching and optimized approach"""
    global _pilkington_login_cache
    
    # Check if we've already logged in recently
    current_time = time.time()
    # if _pilkington_login_cache['logged_in'] and (current_time - _pilkington_login_cache['timestamp'] < _pilkington_login_cache['expiry']):
    #     logger.info("Using cached Pilkington login session")
    #     return True
    
    logger.info("Logging in to Pilkington website")
    load_dotenv()
    username = os.getenv('PIL_USER')
    password = os.getenv('PIL_PASS')

    try:
        # Set faster page load strategy
        driver.set_page_load_timeout(20)
        
        # First, check if we're already logged in by going straight to the shop
        driver.get('https://shop.pilkington.com/')

        # Quick check if we're already on shop page
        if 'shop.pilkington.com' in driver.current_url and 'login' not in driver.current_url:
            # Look for signout elements - faster check
            try:
                signout_elements = safe_find_elements(driver, By.XPATH, 
                    "//a[contains(text(), 'Sign Out')] | //a[contains(text(), 'Logout')]", timeout=10)
                if signout_elements:
                    logger.info("Already logged in")
                    _pilkington_login_cache['logged_in'] = True
                    _pilkington_login_cache['timestamp'] = current_time
                    return True
            except:
                pass

        # Go directly to login page
        login_button = driver.find_element(By.XPATH, "//button[@ng-click='lpVm.login()']")
        login_button.click()

        # Wait shorter time for page load

        # Try multiple login approaches in sequence for better reliability



        # Approach 2: Try finding and clicking buttons - optimized with early exit
        try:
            # Use more efficient button selection
            # Find username field and enter username
            username_field = driver.find_element(By.ID, "username")
            username_field.clear()
            username_field.send_keys(username)
            print("Username entered")

            # Find password field and enter password
            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)
            print("Password entered")

            # Check the "I agree to the Terms and Conditions" checkbox
            terms_checkbox = driver.find_element(By.ID, "cbTerms")
            if not terms_checkbox.is_selected():
                terms_checkbox.click()
                print("Terms and conditions accepted")

            submit_buttons = safe_find_elements(driver, By.XPATH, 
                "//button[contains(text(), 'Sign In')] | //button[contains(text(), 'Login')] | " +
                "//button[@type='submit'] | //input[@type='submit']", timeout=10)
            
            for button in submit_buttons:
                try:
                    logger.info(f"Clicking button: {button.text}")
                    if safe_click(button, driver=driver):
                        # Wait shorter time for login to complete
                        time.sleep(3)
                        
                        # Check if we're now on shop page - early exit
                        if 'shop.pilkington.com' in driver.current_url:
                            logger.info("Login successful after clicking button")
                            _pilkington_login_cache['logged_in'] = True
                            _pilkington_login_cache['timestamp'] = current_time
                            return True
                except:
                    continue
        except:
            pass

        # Approach 3: Try direct navigation to search page (often works even if login fails)
        logger.info("Trying direct navigation to bypass login")
        driver.get('https://shop.pilkington.com/ecomm/search/basic/')

        # Quick check if navigation worked
        if 'shop.pilkington.com' in driver.current_url and 'login' not in driver.current_url:
            logger.info("Direct navigation successful - bypassed login")
            _pilkington_login_cache['logged_in'] = True
            _pilkington_login_cache['timestamp'] = current_time
            return True

        # Approach 4: Final fallback - try ecomm root
        logger.info("Trying final direct navigation approach")
        driver.get('https://shop.pilkington.com/ecomm/')
        if 'shop.pilkington.com' in driver.current_url and 'login' not in driver.current_url:
            logger.info("Final direct navigation successful")
            _pilkington_login_cache['logged_in'] = True
            _pilkington_login_cache['timestamp'] = current_time
            return True

        # If all methods failed, return failure
        logger.error("Login failed - could not access shop after multiple attempts")
        _pilkington_login_cache['logged_in'] = False
        return False

    except Exception as e:
        logger.error(f"Login error: {e}")
        _pilkington_login_cache['logged_in'] = False
        # Try one more direct approach
        try:
            driver.get('https://shop.pilkington.com/ecomm/')
            if 'shop.pilkington.com' in driver.current_url and 'login' not in driver.current_url:
                logger.info("Emergency fallback navigation successful")
                _pilkington_login_cache['logged_in'] = True
                _pilkington_login_cache['timestamp'] = current_time
                return True
        except:
            pass
        return False


def PilkingtonScraper(partNo, driver, logger):
    """Optimized scraper for Pilkington with default data fallback"""
    max_retries = 2
    retry_count = 0
    start_time = time.time()

    # Default parts to return if all methods fail - ensures we always return data
    default_parts = [
        [f"Not Found ", "Not Found ", "Not Found "],
    ]

    while retry_count < max_retries:
        try:
            # Direct approach: go straight to the search results page with optimized URL
            url = f'https://shop.pilkington.com/ecomm/search/basic/?queryType=2&query={partNo}&inRange=true&page=1&pageSize=30&sort=PopularityRankAsc'

            logger.info(f"Searching part in Pilkington: {partNo}")
            
            # Set shorter page load timeout
            driver.set_page_load_timeout(15)
            driver.get(url)

            # Check if login is required - faster check
            if 'identity.pilkington.com/identityexternal/login' in driver.current_url:
                logger.info("Login required")
                success = login(driver, logger)
                if not success:
                    logger.error("Could not log in, returning default Pilkington data")
                    return default_parts
                # Go directly back to search URL
                driver.get(url)

            # Create wait object once
            wait = WebDriverWait(driver, 10)

            # Handle any popup windows more efficiently
            try:
                # Combined selector for common popup types
                popup_elements = safe_find_elements(driver, By.XPATH,
                    "//div[@uib-modal-window='modal-window'] | //div[contains(@class, 'modal')]", timeout=10)
                    
                if popup_elements:
                    # Try to find close buttons more efficiently
                    close_buttons = safe_find_elements(driver, By.XPATH,
                        ".//button[@class='close'] | //button[contains(text(), 'Close')]", timeout=10)
                    if close_buttons:
                        # Try JavaScript click for more reliability
                        driver.execute_script("arguments[0].click();", close_buttons[0])
                        logger.info("Closed popup window")
                        # Brief pause for popup to fully close
                        time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Error handling popup: {e}")

            # Initialize parts array
            parts = []

            # Shorter wait for page load
            time.sleep(2)

            # Quick check if we're on the correct page
            if 'shop.pilkington.com' not in driver.current_url:
                logger.warning("Not on Pilkington shop page, returning default data")
                return default_parts

            # Try multiple data extraction methods in parallel where possible

            # Method 1: Look for tables with part data - optimized
            tables_found = False
            try:
                # Find tables more efficiently
                tables = safe_find_elements(driver, By.TAG_NAME, "table", timeout=10)
                tables_found = len(tables) > 0

                if tables:
                    # Try to get location more efficiently
                    location = "Unknown"
                    location_elements = safe_find_elements(driver, By.XPATH, "//span[@ng-if='!allowChoosePlant']", timeout=10)
                    if location_elements:
                        location_text = location_elements[0].text.strip()
                        if location_text.startswith('- '):
                            location = location_text[2:]
                        else:
                            location = location_text

                    # Get prices more efficiently - fetch all at once
                    price_elements = safe_find_elements(driver, By.XPATH, "//span[@class='amount']", timeout=10)
                    prices = [p.text.strip() for p in price_elements if p.text.strip()]

                    # Process all tables in one pass
                    found_parts = False
                    for table in tables:
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        if len(rows) <= 1:  # Skip tables with only header
                            continue

                        # Process all rows in one batch
                        for i, row in enumerate(rows[1:]):
                            try:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) < 2:
                                    continue

                                # Extract part number
                                part_number = cells[0].text.strip()

                                # Early exit if not matching our search
                                if partNo.lower() not in part_number.lower():
                                    continue
                                    
                                found_parts = True

                                # Get part name
                                part_name = cells[1].text.strip() if len(cells) > 1 else "Unknown"

                                # Get price efficiently - try multiple sources
                                price = "Unknown"
                                if i < len(prices):
                                    price = prices[i]
                                else:
                                    # Try to find price in the row - scan once
                                    for cell in cells:
                                        cell_text = cell.text.strip()
                                        if '$' in cell_text or '£' in cell_text or '€' in cell_text:
                                            price = cell_text
                                            break

                                # Add to parts list
                                parts.append([
                                    part_number,  # Part Number
                                    part_name,  # Part Name
                                    price,  # Price
                                    location  # Location
                                ])
                                logger.info(f"Found part via table: {part_number} - {part_name}")
                            except Exception as e:
                                logger.debug(f"Error processing table row: {e}")
                                continue

                    # Early return if we found parts
                    if found_parts:
                        logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds")
                        return parts
            except Exception as e:
                logger.warning(f"Error processing tables: {e}")

            # Method 2: Look for part cards or list items - optimized
            try:
                # More efficient selector for part elements
                part_elements = safe_find_elements(driver, By.XPATH,
                    "//div[contains(@class, 'part')] | //div[contains(@class, 'product')] | " +
                    "//li[contains(@class, 'part')] | //li[contains(@class, 'product')]", timeout=10)

                if part_elements:
                    found_parts = False
                    
                    # Process all elements in one pass
                    for part_element in part_elements:
                        try:
                            # Get text only once
                            part_text = part_element.text.lower()

                            # Early exit if not matching
                            if partNo.lower() not in part_text:
                                continue
                                
                            found_parts = True

                            # Set default values
                            part_number = partNo  # Default if we can't find it specifically
                            part_name = "Unknown"
                            price = "Unknown"
                            location = "Unknown"

                            # Try to find part number - use compiled regex for speed
                            part_pattern = re.compile(r'[A-Z]{1,3}\d{4,6}', re.IGNORECASE)
                            part_match = part_pattern.search(part_text)
                            if part_match:
                                part_number = part_match.group(0)

                            # Try to find part name more efficiently
                            name_elements = part_element.find_elements(By.XPATH,
                                ".//div[contains(@class, 'description')] | .//span[contains(@class, 'description')] | " +
                                ".//div[contains(@class, 'name')]")
                            if name_elements:
                                part_name = name_elements[0].text.strip()

                            # Try to find price more efficiently
                            price_elements = part_element.find_elements(By.XPATH,
                                ".//span[contains(@class, 'amount')] | .//div[contains(@class, 'price')]")
                            if price_elements:
                                price = price_elements[0].text.strip()
                            else:
                                # Use compiled regex for speed
                                price_pattern = re.compile(r'\$([\d,]+\.\d{2})')
                                price_match = price_pattern.search(part_element.text)
                                if price_match:
                                    price = "$" + price_match.group(1)

                            # Add to parts list
                            parts.append([
                                part_number,
                                part_name,
                                price,
                                location
                            ])
                            logger.info(f"Found part via card: {part_number} - {part_name}")
                        except Exception as e:
                            logger.debug(f"Error processing part element: {e}")
                            continue

                    # Early return if we found parts
                    if found_parts:
                        logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds")
                        return parts
            except Exception as e:
                logger.warning(f"Error processing part elements: {e}")

            # Method 3: Fallback - quick check for part number in the page
            try:
                # Check if part number exists in page - quick check
                if partNo.lower() in driver.page_source.lower():
                    logger.info(f"Found part number {partNo} in page source, but couldn't extract structured data")
                    logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds (default data)")
                    return default_parts
            except Exception as e:
                logger.warning(f"Error checking page source: {e}")

            # No parts found after all methods
            logger.info(f"No parts found for {partNo}, returning default parts")
            logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds (default data)")
            return default_parts

        except Exception as e:
            logger.error(f"Error in Pilkington scraper (attempt {retry_count + 1}/{max_retries}): {e}")
            retry_count += 1

            if retry_count < max_retries:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(1)  # Shorter pause before retry
            else:
                logger.error(f"Failed after {max_retries} attempts, returning default parts")
                logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds (default data)")
                return default_parts


# For testing purposes
if __name__ == "__main__":
    import logging
    from selenium import webdriver

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # Set up driver
    driver = webdriver.Chrome()

    try:
        # Test the scraper
        results = PilkingtonScraper("FW4202", driver, logger)

        if results:
            for part in results:
                print(f"Part: {part[0]}, Name: {part[1]}, Price: {part[2]}, Location: {part[3]}")
        else:
            print("No results found")
    finally:
        driver.quit()