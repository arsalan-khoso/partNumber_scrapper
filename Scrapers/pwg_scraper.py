
import os
import time
import re
import pickle
import pathlib
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.common.exceptions import UnexpectedAlertPresentException

# File path for storing cookies
COOKIE_FILE = "pgw_cookies.pkl"

def save_cookies(driver, logger):
    """Save cookies to file for future sessions"""
    try:
        cookies = driver.get_cookies()
        pathlib.Path(os.path.dirname(COOKIE_FILE)).mkdir(parents=True, exist_ok=True)
        with open(COOKIE_FILE, "wb") as file:
            pickle.dump(cookies, file)
        logger.info(f"Saved {len(cookies)} cookies to {COOKIE_FILE}")
        return True
    except Exception as e:
        logger.warning(f"Failed to save cookies: {e}")
        return False

def load_cookies(driver, logger):
    """Load cookies from file to avoid login"""
    try:
        # Check if cookie file exists
        if not os.path.exists(COOKIE_FILE):
            logger.info("No cookie file found")
            return False
            
        # Check if cookie file is fresh (less than 4 hours old)
        cookie_age = time.time() - os.path.getmtime(COOKIE_FILE)
        if cookie_age > 14400:  # 4 hours in seconds
            logger.info(f"Cookie file is too old ({cookie_age/3600:.1f} hours)")
            return False
            
        # Need to be on the domain before adding cookies
        current_url = driver.current_url
        if "buypgwautoglass.com" not in current_url:
            logger.info("Navigating to PGW domain to apply cookies")
            driver.get("https://buypgwautoglass.com/")
            
            # Handle any alerts
            try:
                alert = driver.switch_to.alert
                logger.info(f"Alert during cookie navigation: {alert.text}")
                alert.accept()
            except:
                pass
                
        # Load cookies
        with open(COOKIE_FILE, "rb") as file:
            cookies = pickle.load(file)
            
        # Add cookies to driver
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.debug(f"Couldn't add cookie {cookie.get('name')}: {e}")
                
        logger.info(f"Loaded {len(cookies)} cookies from file")
        
        # Refresh to apply cookies
        driver.refresh()
        
        # Handle any alerts after refresh
        try:
            alert = driver.switch_to.alert
            logger.info(f"Alert after cookie refresh: {alert.text}")
            alert.accept()
        except:
            pass
            
        # Check if we're logged in
        if "PartSearch" in driver.current_url:
            logger.info("Successfully logged in with cookies")
            return True
        else:
            logger.info("Cookie login failed, will try regular login")
            return False
    except Exception as e:
        logger.warning(f"Failed to load cookies: {e}")
        return False

def login(driver, logger):
    """Login to Buy PGW Auto Glass website with improved alert handling and performance"""
    start_time = time.time()
    logger.info("Logging in to Buy PGW Auto Glass")
    load_dotenv()
    username = os.getenv('PGW_USER')
    password = os.getenv('PGW_PASS')

    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            # Try to use cookies first if we're not already on login page
            if "Default.asp" not in driver.current_url and "login" not in driver.current_url.lower():
                if load_cookies(driver, logger):
                    elapsed = time.time() - start_time
                    logger.info(f"Login via cookies successful in {elapsed:.2f}s")
                    return True

            # Clear cookies if cookies didn't work
            driver.delete_all_cookies()

            # Go to the login page directly
            logger.info("Navigating to login page")
            driver.get('https://buypgwautoglass.com/')

            # Handle any alert that might be present
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text
                logger.info(f"Alert present: {alert_text}")
                alert.accept()
            except:
                pass

            # Check if we're already logged in by URL
            if "PartSearch" in driver.current_url:
                elapsed = time.time() - start_time
                logger.info(f"Already logged in (detected from URL) in {elapsed:.2f}s")
                
                # Save cookies for future use
                save_cookies(driver, logger)
                
                return True

            # Use shorter wait time for better performance
            wait = WebDriverWait(driver, 15)

            # Wait for the username field - this is the most reliable indicator
            try:
                # Try finding username field directly first
                user_input_elements = driver.find_elements(By.ID, 'txtUsername')
                pass_input_elements = driver.find_elements(By.ID, 'txtPassword')
                
                if user_input_elements and pass_input_elements:
                    user_input = user_input_elements[0]
                    pass_input = pass_input_elements[0]
                else:
                    # If not found directly, wait
                    user_input = wait.until(EC.presence_of_element_located((By.ID, 'txtUsername')))
                    pass_input = wait.until(EC.presence_of_element_located((By.ID, 'txtPassword')))

                # Use JavaScript for faster form filling
                driver.execute_script("""
                    arguments[0].value = '';
                    arguments[1].value = '';
                    arguments[0].value = arguments[2];
                    arguments[1].value = arguments[3];
                """, user_input, pass_input, username, password)

                # Find and click login button without waiting if possible
                login_button_elements = driver.find_elements(By.ID, 'button1')
                if login_button_elements:
                    login_button = login_button_elements[0]
                else:
                    login_button = wait.until(EC.element_to_be_clickable((By.ID, 'button1')))
                
                login_button.click()

                # Handle any alert that might appear after login
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    logger.info(f"Login alert: {alert_text}")
                    alert.accept()
                except:
                    pass

                # Handle the agreement screen if it appears - use shorter sleep
                time.sleep(1)  # Brief pause to let the page update

                # Look for the I Agree button or any button with "agree" text
                agree_buttons = driver.find_elements(By.XPATH,
                                                    "//input[@value='I Agree'] | //button[contains(text(), 'Agree')]")
                if agree_buttons:
                    agree_buttons[0].click()
                    logger.info("Clicked 'I Agree' button")
                else:
                    logger.info("No agreement screen found")

                # Wait for successful login with shorter timeout
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".header, .menu")))
                    elapsed = time.time() - start_time
                    logger.info(f"Login successful in {elapsed:.2f}s")
                    
                    # Save cookies for future use
                    save_cookies(driver, logger)
                    
                    return True
                except TimeoutException:
                    # Check if we're on the part search page anyway
                    if "PartSearch" in driver.current_url:
                        elapsed = time.time() - start_time
                        logger.info(f"Login successful (detected from URL) in {elapsed:.2f}s")
                        
                        # Save cookies for future use
                        save_cookies(driver, logger)
                        
                        return True
                    else:
                        raise TimeoutException("Login verification failed")

            except TimeoutException:
                # Try alternative login approach if standard elements not found
                logger.warning("Standard login elements not found, trying alternative approach")

                # Try looking for any login form
                inputs = driver.find_elements(By.TAG_NAME, 'input')
                if len(inputs) >= 2:
                    # Look for username and password fields
                    for i in range(len(inputs) - 1):
                        if inputs[i].get_attribute('type') == 'text' and inputs[i + 1].get_attribute(
                                'type') == 'password':
                            # Use JavaScript for faster form filling
                            driver.execute_script("""
                                arguments[0].value = '';
                                arguments[1].value = '';
                                arguments[0].value = arguments[2];
                                arguments[1].value = arguments[3];
                            """, inputs[i], inputs[i + 1], username, password)

                            # Find a button to click
                            buttons = driver.find_elements(By.TAG_NAME, 'button')
                            if buttons:
                                buttons[0].click()

                                # Handle any alert
                                try:
                                    alert = driver.switch_to.alert
                                    alert_text = alert.text
                                    logger.info(f"Alternative login alert: {alert_text}")
                                    alert.accept()
                                except:
                                    pass

                                # Wait for page change with shorter timeout
                                time.sleep(3)

                                # Check if login succeeded
                                if "PartSearch" in driver.current_url:
                                    elapsed = time.time() - start_time
                                    logger.info(f"Login successful via alternative method in {elapsed:.2f}s")
                                    
                                    # Save cookies for future use
                                    save_cookies(driver, logger)
                                    
                                    return True

                if attempt < max_attempts - 1:
                    logger.warning(f"Login attempt {attempt + 1} failed, retrying...")
                    time.sleep(1)  # Shorter wait between attempts
                else:
                    raise Exception("Could not find login elements after multiple attempts")

        except Exception as e:
            if attempt < max_attempts - 1:
                logger.warning(f"Login attempt {attempt + 1} failed with error: {e}, retrying...")
                time.sleep(1)  # Shorter wait between attempts
            else:
                elapsed = time.time() - start_time
                logger.error(f"Login error after {elapsed:.2f}s: {e}")
                raise


def searchPart(driver, partNo, logger):
    """Search for part on PGW website with better performance and data extraction"""
    start_time = time.time()
    max_retries = 2
    retry_count = 0

    # Default parts to return if all else fails - this ensures we always return something
    default_parts = [
        ["Not Found", "Not Found", "Not Found", "Not Found", "Not Found"],

    ]

    # Set shorter timeout for better performance
    original_page_load_timeout = driver.timeouts.page_load
    original_script_timeout = driver.timeouts.script
    
    try:
        # Set shorter timeouts
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(15)
        
        while retry_count < max_retries:
            try:
                logger.info(f"Searching part in PWG: {partNo}")

                # Try both search URLs to improve reliability
                url =  'https://buypgwautoglass.com/PartSearch/default.asp'


                # Try each URL
                try:
                    url_start = time.time()
                    driver.get(url)

                    # Handle any alert that might appear
                    try:
                        alert = driver.switch_to.alert
                        alert_text = alert.text
                        logger.info(f"Navigation alert: {alert_text}")
                        alert.accept()

                        # If there was an alert, it's likely we need to login
                        if "login" in alert_text.lower() or "password" in alert_text.lower():
                            login_start = time.time()
                            if not login(driver, logger):
                                continue
                            logger.info(f"Login completed in {time.time() - login_start:.2f}s")
                            driver.get(url)
                    except:
                        pass

                    # Check if we need to login
                    login_check_start = time.time()
                    if "default.asp" in driver.current_url:
                        logger.info("Login required")
                        login_start = time.time()
                        if not login(driver, logger):
                            continue
                        logger.info(f"Login completed in {time.time() - login_start:.2f}s")
                        driver.get(url)
                    logger.info(f"Login check completed in {time.time() - login_check_start:.2f}s")

                    # Use shorter wait time for better performance
                    wait = WebDriverWait(driver, 10)

                    # Proceed with part search
                    try:
                        search_start = time.time()
                        # # Find and click the Part Number radio button
                        # try:
                        #     # Check if element exists directly first
                        #     type_select_elements = driver.find_elements(By.ID, "PartTypeA")
                        #     if type_select_elements:
                        #         type_select_elements[0].click()
                        #     else:
                        #         # If not found directly, try with wait
                        #         type_select = wait.until(EC.element_to_be_clickable((By.ID, "PartTypeA")))
                        #         type_select.click()
                        # except:
                        #     logger.warning("Could not find Part Type radio button, continuing anyway")

                        # Enter part number in the search field
                        try:
                            # Try to find element directly first
                            part_no_inputs = driver.find_elements(By.ID, "PartNo")
                            if part_no_inputs:
                                part_no_input = part_no_inputs[0]
                            else:
                                part_no_input = wait.until(EC.presence_of_element_located((By.ID, "PartNo")))

                            # Use JavaScript for faster input
                            driver.execute_script("""
                                arguments[0].value = '';
                                arguments[0].value = arguments[1];
                            """, part_no_input, partNo)

                            # Press Enter for faster submission
                            part_no_input.send_keys(Keys.RETURN)

                            logger.info(f"Search form submitted in {time.time() - search_start:.2f}s")

                            # Handle any alert that might appear after search
                            try:
                                alert = driver.switch_to.alert
                                alert_text = alert.text
                                logger.info(f"Search alert: {alert_text}")
                                alert.accept()

                                # If we get an alert about login, try logging in again
                                if "login" in alert_text.lower() or "password" in alert_text.lower():
                                    if login(driver, logger):
                                        driver.get(url)
                                        continue
                            except:
                                pass

                        except:
                            # Try alternate search field
                            alt_search_start = time.time()
                            search_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                            if search_fields:
                                # Use JavaScript for faster input
                                driver.execute_script("""
                                    arguments[0].value = '';
                                    arguments[0].value = arguments[1];
                                """, search_fields[0], partNo)

                                search_fields[0].send_keys(Keys.RETURN)
                                logger.info(f"Alternate search completed in {time.time() - alt_search_start:.2f}s")

                                # Handle any alert
                                try:
                                    alert = driver.switch_to.alert
                                    alert_text = alert.text
                                    logger.info(f"Alternate search alert: {alert_text}")
                                    alert.accept()
                                except:
                                    pass
                            else:
                                raise Exception("Could not find search field")

                        # Wait for results with shorter timeout
                        time.sleep(2)

                        # Process results
                        parse_start = time.time()
                        parts = []

                        # Quick check if part is in page source for faster decision
                        if partNo not in driver.page_source:
                            logger.info(f"Part number {partNo} not found in page source, skipping detailed parsing")
                            continue  # Try next URL

                        logger.info(f"Found part number {partNo} in page source, proceeding with parsing")
                        time.sleep(2)





                        # Process tables if found
                        location = "Unknown"
                        try:
                            location_elements = driver.find_elements(By.XPATH, "//span[@class='b2btext']")
                            if location_elements:
                                location_text = location_elements[0].text
                                if "::" in location_text:
                                    location = location_text.split(":: ")[1].strip()
                        except:
                            pass
                        try:
                            # Check if "Quotes" button exists
                            quote_button = driver.find_element(By.ID, "btnQuote")

                            # Verify it's the correct button by checking the onclick attribute
                            onclick_value = quote_button.get_attribute("onclick")
                            if "quotes_on" in onclick_value:
                                # Click the button if it exists and has the right onclick value
                                quote_button.click()

                                # Find the input field and enter "1313"
                                pin_input = driver.find_element(By.CSS_SELECTOR, "input")
                                pin_input.send_keys("1313")

                                # Find and click the submit button
                                submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                                submit_button.click()

                        except NoSuchElementException:
                            print("Quote button not found or is not in the expected format")
                            # Try to find product table - various approachesprice
                        tables = driver.find_elements(By.TAG_NAME, "table")
                        found_parts = False
                        for table in tables:
                            logger.info(f"TRY TO BE HERE")

                            rows = table.find_elements(By.TAG_NAME, "tr")
                            if len(rows) <= 1:
                                logger.info(f"Skipping table with {len(rows)} rows (needs more than 1)")
                                continue  # Skip tables with only headers

                            logger.info(f"Processing table with {len(rows)} rows")
                            logger.info(f"TRY TO BE HERE 1")


                            for row in rows[1:]:  # Skip header row
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) < 3:
                                    logger.info(f"Skipping row with insufficient cells: {len(cells)}")
                                    continue
                                logger.info(f"TRY TO BE HERE 2")

                                # Extract part number
                                part_text = ""
                                # Try various ways to get part number
                                part_elements = row.find_elements(By.TAG_NAME, "font")
                                if part_elements:
                                    part_text = part_elements[0].text
                                    logger.info(f"Found part text from font element: {part_text}")

                                if not part_text:
                                    part_text = cells[2].text
                                    logger.info(f"Found part text from cell: {part_text}")
                                logger.info(f"TRY TO BE HERE 4")

                                # If part number matches our search
                                if partNo.lower() in part_text.lower():
                                    found_parts = True
                                    logger.info(
                                        f"MATCH FOUND: Part number {part_text} matches search criteria {partNo}")
                                    try:
                                        check_button = driver.find_element(By.CSS_SELECTOR, "button.button.check")
                                        check_button.click()
                                    except:
                                        pass

                                    # Extract other information
                                    availability = "Unknown"
                                    avail_elements = cells[1].find_elements(By.TAG_NAME, "font")
                                    if avail_elements:
                                        availability = avail_elements[0].text
                                        logger.info(f"Availability from font: {availability}")
                                    else:
                                        availability = cells[1].text
                                        logger.info(f"Availability from cell: {availability}")
                                    logger.info(f"TRY TO BE HERE 5")

                                    price = cells[3].find_elements(By.TAG_NAME, "font")[0].text
                                    logger.info(f"Price element found: {price}")

                                    description = "No description"
                                    desc_elements = row.find_elements(By.XPATH, ".//div[@class='options']")
                                    if desc_elements:
                                        description = desc_elements[0].text.replace('»', '').strip()
                                        logger.info(f"Description found: {description}")
                                    else:
                                        logger.info("No description element found")

                                    # Add to parts list
                                    parts.append([
                                        part_text,  # Part Number
                                        availability,  # Availability
                                        price,  # Price
                                        location,  # Location
                                        description  # Description
                                    ])
                                    print("032243",parts)
                                    logger.info(
                                        f"Added part to results list: {part_text}, {availability}, {price}, {location}, {description}")
                                else:
                                    logger.info(f"Part number {part_text} does not match search criteria {partNo}")
                        if found_parts:
                            elapsed = time.time() - start_time
                            logger.info(f"Found {len(parts)} parts via tables in {elapsed:.2f}s")
                            return parts
                        else:
                            # If we searched but found no matches, try to extract from the page content
                            page_source = driver.page_source.lower()
                            if partNo.lower() in page_source:
                                elapsed = time.time() - start_time
                                logger.info(f"Found part number {partNo} in page source, using default parts after {elapsed:.2f}s")
                                return default_parts

                    except UnexpectedAlertPresentException as e:
                        # Handle unexpected alerts during search
                        logger.warning(f"Unexpected alert during search: {e}")
                        try:
                            alert = driver.switch_to.alert
                            alert_text = alert.text
                            logger.info(f"Handling unexpected alert: {alert_text}")
                            alert.accept()

                            # If it's a login alert, try logging in again
                            if "login" in alert_text.lower() or "password" in alert_text.lower():
                                if login(driver, logger):
                                    continue
                        except:
                            pass

                    except Exception as e:
                        logger.warning(f"Error during search on {url}: {e}")
                        # Continue to next URL if this one fails

                except UnexpectedAlertPresentException:
                    # Handle unexpected alerts during navigation
                    try:
                        alert = driver.switch_to.alert
                        alert_text = alert.text
                        logger.info(f"Navigation alert: {alert_text}")
                        alert.accept()
                    except:
                        pass

                except Exception as e:
                    logger.warning(f"Error accessing {url}: {e}")
                    continue

                # If we get here, we've tried all URLs without success
                logger.warning(f"Could not find part {partNo} on any PWG URLs")
                elapsed = time.time() - start_time
                logger.info(f"Returning default parts after {elapsed:.2f}s")
                return default_parts

            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"Error searching for part number {partNo} on PWG (attempt {retry_count + 1}/{max_retries}) after {elapsed:.2f}s: {e}")
                retry_count += 1

                if retry_count < max_retries:
                    logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(1)  # Brief pause before retry
                else:
                    logger.error(f"Failed after {max_retries} attempts")
                    elapsed = time.time() - start_time
                    logger.info(f"Returning default parts after {elapsed:.2f}s")
                    return default_parts  # Return default parts when all methods fail
    
    finally:
        # Restore original timeouts
        try:
            driver.set_page_load_timeout(original_page_load_timeout)
            driver.set_script_timeout(original_script_timeout)
        except:
            pass

def PWGScraper(partNo, driver, logger):
    """Main PGW scraper function with performance metrics"""
    start_time = time.time()
    try:
        logger.info(f"Starting PWG scraper for part: {partNo}")
        result = searchPart(driver, partNo, logger)
        elapsed = time.time() - start_time
        logger.info(f"PWG scraper completed in {elapsed:.2f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in PWG scraper after {elapsed:.2f}s: {e}")
        # Return default parts on error to ensure we always return something
        return [
            [f"NOT FOUND ", "NOT FOUND ", "NOT FOUND ", "NOT FOUND ", "NOT FOUND "],

        ]