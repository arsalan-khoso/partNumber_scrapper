from bs4 import BeautifulSoup
import os
import time
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.keys import Keys


# Cache for login status to avoid unnecessary logins
_login_cache = {
    'logged_in': False,
    'timestamp': 0
}

def is_driver_responsive(driver, logger):
    """Check if the WebDriver is still responsive"""
    try:
        # Try a simple operation to test driver responsiveness
        driver.execute_script("return navigator.userAgent")
        return True
    except Exception as e:
        logger.warning(f"Driver not responsive: {e}")
        return False

def safe_find_element(driver, by, value, wait_time=8, retries=1):
    """Safely find element with retries"""
    for attempt in range(retries + 1):
        try:
            return WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((by, value))
            )
        except (TimeoutException, NoSuchElementException) as e:
            if attempt == retries:
                raise
            time.sleep(0.5)

def safe_click(element, driver=None, retries=2):
    """Safely click an element with retries and JavaScript fallback"""
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

def ensure_zyte_headers(driver, logger):
    """Ensure Zyte headers are set for each navigation"""
    try:
        # Explicitly set headers using CDP command to ensure Zyte proxy is used
        driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
            'headers': {
                'X-Crawlera-Profile': 'desktop',
                'X-Crawlera-Cookies': 'enable',
                # 'X-Crawlera-Region': 'us-ca',
                'X-Crawlera-UA': 'desktop',
                'X-Crawlera-Use-HTTPS': '1'
            }
        })
        logger.info("Zyte headers refreshed")
        return True
    except Exception as e:
        logger.warning(f"Failed to set Zyte headers: {e}")
        return False

def wait_for_page_load(driver, timeout=10):
    """Wait for page to finish loading with timeout"""
    try:
        # Wait for document.readyState to be complete
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        return True
    except:
        return False

def login(driver, logger):
    """Login to MyGrant website with improved error handling and caching"""
    global _login_cache
    
    # Check driver responsiveness first
    if not is_driver_responsive(driver, logger):
        logger.error("Driver not responsive before login")
        return False
    
    # Ensure Zyte headers are set
    ensure_zyte_headers(driver, logger)
    
    # Check if we've already logged in recently (within last 20 minutes)
    current_time = time.time()
    if _login_cache['logged_in'] and (current_time - _login_cache['timestamp'] < 1200):
        logger.info("Using cached login session")
        return True
    
    logger.info("Logging in to MyGrant")
    load_dotenv()
    username = os.getenv('MYGRANT_USER')
    password = os.getenv('MYGRANT_PASS')
    
    if not username or not password:
        logger.error("Missing MyGrant credentials in environment variables")
        return False

    try:
        # Set longer page load timeout for login
        try:
            driver.set_page_load_timeout(20)
            ensure_zyte_headers(driver, logger)
            driver.get('https://www.mygrantglass.com/')
            
            # Wait for page to fully load
            wait_for_page_load(driver, 15)
            time.sleep(2)  # Extra wait time for JS to initialize
        except TimeoutException:
            logger.warning("Page load timed out, continuing with what loaded")
        except Exception as e:
            logger.error(f"Error loading login page: {e}")
            return False
        
        # Create wait object once
        wait = WebDriverWait(driver, 10)

        # Check if we're already logged in - fast check
        dashboard_elements = driver.find_elements(By.ID, 'ch_cus_CustomerPage')
        if dashboard_elements:
            logger.info("Already logged in")
            _login_cache['logged_in'] = True
            _login_cache['timestamp'] = current_time
            return True

        # Try to click on login link - with timeout handling
        try:
            login_link = wait.until(EC.element_to_be_clickable((By.ID, 'ch_cus_LoginLink')))
            safe_click(login_link, driver)
            logger.info("Clicked on login link")
            time.sleep(1)  # Allow time for login form to appear
        except TimeoutException:
            logger.warning("Could not find login link, trying alternative approaches")

            # Try looking for login form directly - faster than alternatives
            try:
                username_input = wait.until(EC.presence_of_element_located((By.ID, 'clogin_TxtUsername')))
                logger.info("Found username field directly")
            except TimeoutException:
                # Try clicking any login links on the page
                login_links = driver.find_elements(By.XPATH,
                                                   "//a[contains(text(), 'Login')] | //a[contains(text(), 'Sign In')]")
                if login_links:
                    logger.info("Found alternate login link")
                    safe_click(login_links[0], driver)
                    time.sleep(1)  # Allow time for login form to appear
                else:
                    # Try going directly to login page as last resort
                    try:
                        ensure_zyte_headers(driver, logger)
                        driver.get('https://www.mygrantglass.com/pages/login.aspx')
                        wait_for_page_load(driver, 10)
                        time.sleep(1)
                    except:
                        logger.error("Could not find any login links or forms")
                        return False

        # Wait for and fill in username and password - optimized selector usage
        try:
            logger.info("Looking for username and password fields")
            user_input = wait.until(EC.presence_of_element_located((By.ID, 'clogin_TxtUsername')))
            pass_input = wait.until(EC.presence_of_element_located((By.ID, 'clogin_TxtPassword')))

            # Clear and input credentials in a single operation when possible
            try:
                driver.execute_script("""
                    arguments[0].value = '';
                    arguments[1].value = '';
                    arguments[0].value = arguments[2];
                    arguments[1].value = arguments[3];
                """, user_input, pass_input, username, password)
                logger.info("Entered credentials via JavaScript")
            except:
                # Fallback to traditional input if JavaScript fails
                user_input.clear()
                user_input.send_keys(username)
                logger.info("Username entered")
                pass_input.clear()
                pass_input.send_keys(password)
                logger.info("Password entered")

            # Click login button
            login_button = wait.until(EC.element_to_be_clickable((By.ID, 'clogin_ButtonLogin')))
            logger.info("Found login button")
            safe_click(login_button, driver)
            logger.info("Clicked login button")
            
            # Wait for page to load after login
            wait_for_page_load(driver, 15)
            time.sleep(2)  # Additional wait for JS initialization

            # Wait for page to load after login - use reduced timeout
            try:
                wait.until(EC.presence_of_element_located((By.ID, 'ch_cus_CustomerPage')))
                logger.info("Login successful")
                
                # Update login cache
                _login_cache['logged_in'] = True
                _login_cache['timestamp'] = current_time
                return True
            except TimeoutException:
                # Check URL as fallback
                if 'login.aspx' not in driver.current_url:
                    logger.info("Login appears successful (URL changed)")
                    _login_cache['logged_in'] = True
                    _login_cache['timestamp'] = current_time
                    return True
                else:
                    logger.warning("Login verification timed out")
        except TimeoutException:
            # Try alternative login approach
            logger.warning("Standard login elements not found, trying alternative approach")

            # Look for any username/password fields - optimized selector
            inputs = driver.find_elements(By.TAG_NAME, 'input')
            text_inputs = [inp for inp in inputs if inp.get_attribute('type') in ['text', 'email', None]]
            password_inputs = [inp for inp in inputs if inp.get_attribute('type') == 'password']

            if text_inputs and password_inputs:
                try:
                    text_inputs[0].clear()
                    text_inputs[0].send_keys(username)
                    logger.info("Username entered")
                    password_inputs[0].clear()
                    password_inputs[0].send_keys(password)
                    logger.info("Password entered")

                    # Look for login button with more specific selector
                    buttons = driver.find_elements(By.XPATH,
                                                   "//input[@type='submit'] | //button[contains(text(), 'Login')] | //button[contains(text(), 'Sign In')]")
                    if buttons:
                        logger.info(f"Clicking button: {buttons[0].text if buttons[0].text else 'Sign In'}")
                        safe_click(buttons[0], driver)

                        # Wait for login to complete
                        wait_for_page_load(driver, 15)
                        time.sleep(3)  # Additional wait for JS initialization

                        # Check if login was successful - faster check
                        if 'login.aspx' not in driver.current_url:
                            logger.info("Login successful via alternative method")
                            _login_cache['logged_in'] = True
                            _login_cache['timestamp'] = current_time
                            return True
                        else:
                            logger.warning("Login failed - still on login page")
                    else:
                        logger.warning("Could not find login button")
                except Exception as e:
                    logger.warning(f"Error in alternative login approach: {e}")
            else:
                logger.warning("Could not find username and password fields")

    except Exception as e:
        logger.error(f"Login error: {e}")
    
    # Reset login cache on failure
    _login_cache['logged_in'] = False
    return False


def MyGrantScraper(partNo, driver, logger):
    """Scrape part information from MyGrant website with improved robustness against timeouts"""
    max_retries = 3  # Increased from 2 to 3
    retry_count = 0
    start_time = time.time()
    
    # Check driver responsiveness
    if not is_driver_responsive(driver, logger):
        logger.error("Driver not responsive at start of scraper")
        return []
        
    # Ensure Zyte headers are set before we begin
    ensure_zyte_headers(driver, logger)

    while retry_count < max_retries:
        try:
            logger.info(f"Searching part in MyGrant: {partNo} (attempt {retry_count + 1}/{max_retries})")
            
            # Set longer timeouts for better reliability
            try:
                driver.set_page_load_timeout(20)  # Increased from 15
            except:
                pass
                
            # Try multiple URLs in case one works better
            urls_to_try = [
                f'https://www.mygrantglass.com/pages/search.aspx?q={partNo}&sc=r&do=Search',
                'https://www.mygrantglass.com/pages/search.aspx',
                'https://www.mygrantglass.com/'
            ]
            
            parts = []
            page_loaded = False
            
            # Try each URL until one works
            for url_index, search_url in enumerate(urls_to_try):
                if page_loaded:
                    break
                    
                try:
                    # Ensure fresh Zyte headers before navigation
                    ensure_zyte_headers(driver, logger)
                    logger.info(f"Trying URL {url_index + 1}/{len(urls_to_try)}: {search_url}")
                    driver.get(search_url)
                    
                    # Wait for page to load
                    if wait_for_page_load(driver, 15):
                        page_loaded = True
                        logger.info(f"Successfully loaded URL: {search_url}")
                        
                        # If we loaded the search page, try searching directly
                        if url_index > 0:  # Not the direct search URL
                            try:
                                # Wait for search box
                                search_input = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.ID, "cpsr_TxtSearch"))
                                )
                                search_input.clear()
                                search_input.send_keys(partNo)
                                logger.info(f"Entered search term: {partNo}")
                                
                                # Find and click search button
                                search_buttons = driver.find_elements(By.XPATH, 
                                    "//input[@type='submit' and (@value='Search' or @value='Go')] | //button[contains(text(), 'Search')]")
                                
                                if search_buttons:
                                    logger.info("Found search button, clicking")
                                    safe_click(search_buttons[0], driver)
                                else:
                                    # Try pressing Enter as fallback
                                    logger.info("No search button found, pressing Enter")
                                    search_input.send_keys(Keys.RETURN)
                                
                                # Wait for search results
                                wait_for_page_load(driver, 15)
                                time.sleep(2)  # Additional wait for JS to initialize
                            except Exception as e:
                                logger.warning(f"Error performing search: {e}")
                        
                        # Add extra wait time for search results to load
                        time.sleep(3)
                        break
                    else:
                        logger.warning(f"Page load incomplete for {search_url}, trying next URL")
                        
                except TimeoutException:
                    logger.warning(f"Page load timed out for {search_url}, trying next URL")
                except Exception as e:
                    logger.warning(f"Error loading {search_url}: {e}")

            # If no URLs worked, try next retry
            if not page_loaded:
                logger.warning("Failed to load any URLs, retrying")
                retry_count += 1
                continue

            # Check if login is required - quick check
            if 'login.aspx' in driver.current_url:
                logger.info("Login required")
                login_success = login(driver, logger)
                if not login_success:
                    logger.error("Login failed, retrying search")
                    retry_count += 1
                    continue
                
                # Direct reload of search URL after login
                try:
                    # Ensure fresh Zyte headers after login
                    ensure_zyte_headers(driver, logger)
                    driver.get(urls_to_try[0])  # Try direct search URL again
                    wait_for_page_load(driver, 15)
                    time.sleep(3)  # Extra wait time
                except TimeoutException:
                    logger.warning("Search page reload timed out after login, continuing")
                except Exception as e:
                    logger.warning(f"Error reloading search page after login: {e}")


            try:
                logger.info(f"Starting extraction process for part {partNo}")
                # Use shorter timeout for elements
                wait = WebDriverWait(driver, 8)  # Increased from 5

                # Save page source for processing - avoids stale element issues
                page_source = driver.page_source
                
                # Check if part number exists in page - quick check
                if partNo.lower() in page_source.lower():
                    logger.info(f"Part {partNo} found in page source, proceeding with extraction")
                else:
                    logger.warning(f"Part {partNo} not found in page source")
                    # Try alternative search if direct search didn't work
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        continue
                    else:
                        logger.info(f"Part {partNo} not found after {retry_count + 1} attempts")
                        return []
                
                # Direct BeautifulSoup processing - more reliable than waiting for elements
                try:
                    logger.info("Processing page with BeautifulSoup")
                    soup = BeautifulSoup(page_source, 'html.parser')
                    
                    # Find the parts results div
                    div = soup.find('div', {'id': 'cpsr_DivParts'})
                    
                    # If results div found, proceed with normal parsing
                    if div:
                        logger.info(f"Valid results div found, proceeding with parsing")
                        # Find all location headings (h3 elements)
                        locations = div.find_all('h3')
                        
                        # If no locations found, try other heading elements
                        if not locations:
                            logger.info(f"No h3 elements found, trying alternative heading elements")
                            locations = div.find_all(['h2', 'h4', 'strong'])
                        
                        # Skip first heading if it's not a location
                        if locations and not (' - ' in locations[0].text):
                            locations = locations[1:]
                        
                        # If still no locations, use a default
                        if not locations:
                            logger.warning(f"No location elements found, using default")
                            locations = ["Unknown Location"]
                        
                        # Find all tables
                        tables = div.find_all('tbody')
                        
                        # If no tbody elements, look for tables directly
                        if not tables:
                            logger.info(f"No tbody elements found, searching for table elements directly")
                            tables = div.find_all('table')
                        
                        # Process each table (each location has a table)
                        logger.info(f"Beginning to process {len(tables)} tables")
                        for i, table in enumerate(tables):
                            current_location = "Unknown"
                            if i < len(locations):
                                location_text = locations[i].text.strip()
                                if ' - ' in location_text:
                                    current_location = location_text.split(' - ')[0].strip()
                                else:
                                    current_location = location_text
                            
                            # Process rows in the table
                            rows = table.find_all('tr')
                            if len(rows) <= 1:
                                continue  # Skip table if only has header row
                            
                            rows = rows[1:]  # Skip header row
                            
                            for row in rows:
                                data = row.find_all('td')
                                if len(data) <= 1:
                                    continue
                                
                                try:
                                    # Get part number from link or text
                                    part_number = None
                                    part_element = None
                                    
                                    # Try to find a link containing part number
                                    for idx, cell in enumerate(data):
                                        links = cell.find_all('a')
                                        if links:
                                            link_text = links[0].text.strip()
                                            if partNo.lower() in link_text.lower():
                                                part_number = link_text
                                                part_element = cell
                                                break
                                    
                                    # If no link found, try cell text
                                    if not part_number:
                                        for idx, cell in enumerate(data):
                                            cell_text = cell.text.strip()
                                            if partNo.lower() in cell_text.lower():
                                                part_number = cell_text
                                                part_element = cell
                                                break
                                    
                                    # Skip if part number not found
                                    if not part_number:
                                        continue
                                    
                                    # Find the index of the part element
                                    part_idx = data.index(part_element) if part_element else -1
                                    
                                    # Get availability (usually in first cell)
                                    availability = "Unknown"
                                    try:
                                        avail_cell = data[1]
                                        availability_span = avail_cell.find('span')
                                        if availability_span:
                                            availability = availability_span.text.strip()
                                        else:
                                            availability = avail_cell.text.strip()
                                    except (IndexError, AttributeError):
                                        pass
                                    
                                    # Get price (usually in third cell)
                                    price = "Unknown"
                                    try:
                                        if len(data) > 2:
                                            price = data[3].text.strip()
                                    except IndexError:
                                        pass
                                    
                                    # Add to parts list
                                    logger.info(
                                        f"Adding part: {part_number}, availability: {availability}, price: {price}, location: {current_location}")
                                    parts.append([
                                        part_number,  # Part Number
                                        availability,  # Availability
                                        price,  # Price
                                        current_location  # Location
                                    ])
                                except Exception as e:
                                    logger.warning(f"Error processing row: {str(e)}")
                                    continue
                        
                        # Return the parts we found
                        if parts:
                            logger.info(f"Extraction complete, found {len(parts)} parts matching '{partNo}'")
                            return parts
                        else:
                            logger.warning(f"No parts found in tables for '{partNo}'")
                    else:
                        logger.warning("No results div found")
                        
                        # Try direct page search as fallback
                        if partNo.lower() in page_source.lower():
                            logger.info(f"Part {partNo} found in page source, creating generic entry")
                            return [[
                                partNo,
                                "Available - Check Store",
                                "Contact for Price",
                                "Unknown"
                            ]]
                
                except Exception as e:
                    logger.error(f"Error in BeautifulSoup processing: {e}")
                    
                    # Fallback to basic result if part is found in page
                    if partNo.lower() in page_source.lower():
                        logger.info("Creating basic result based on page source match")
                        return [[
                            partNo,
                            "Found - Contact Store",
                            "Contact for Price",
                            "Unknown"
                        ]]

            except Exception as e:
                logger.error(f"Critical error in extraction for part {partNo}: {str(e)}")
                
            # Increment retry counter
            retry_count += 1
            
            # If this wasn't the last retry, wait briefly and try again
            if retry_count < max_retries:
                logger.info(f"Retrying search (attempt {retry_count + 1}/{max_retries})")
                time.sleep(2)  # Increased from 1
            else:
                logger.warning(f"All {max_retries} attempts completed without successful extraction")
                
                # Final check if part exists in page
                if partNo.lower() in driver.page_source.lower():
                    logger.info("Creating basic result based on page source match")
                    return [[
                        partNo,
                        "Found - Contact Store",
                        "Contact for Price",
                        "Unknown"
                    ]]
                return []

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error in MyGrant scraper (attempt {retry_count + 1}/{max_retries}) after {elapsed:.2f}s: {e}")
            retry_count += 1

            if retry_count < max_retries:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(2)  # Increased from 1
            else:
                logger.error(f"Failed after {max_retries} attempts")
                return []
                
    # Shouldn't reach here normally
    return []


# For testing purposes
if __name__ == "__main__":
    import logging
    from selenium import webdriver

    # Set up logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # Set up driver
    driver = webdriver.Chrome()
    
    try:
        # Test the scraper
        results = MyGrantScraper("FW4202", driver, logger)

        if results:
            for part in results:
                print(f"Part: {part[0]}, Availability: {part[1]}, Price: {part[2]}, Location: {part[3]}")
        else:
            print("No results found")
    finally:
        driver.quit()