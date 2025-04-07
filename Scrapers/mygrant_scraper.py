# from bs4 import BeautifulSoup
# import os
# import time
# from dotenv import load_dotenv
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


# def login(driver, logger):
#     """Login to MyGrant website with improved error handling"""
#     logger.info("Logging in to MyGrant")
#     load_dotenv()
#     username = os.getenv('MYGRANT_USER')
#     password = os.getenv('MYGRANT_PASS')

#     try:
#         driver.get('https://www.mygrantglass.com/pages/login.aspx')
#         wait = WebDriverWait(driver, 20)

#         # Check if we're already logged in
#         dashboard_elements = driver.find_elements(By.ID, 'ch_cus_CustomerPage')
#         if dashboard_elements:
#             logger.info("Already logged in")
#             return True

#         # Try to click on login link
#         try:
#             login_link = wait.until(EC.element_to_be_clickable((By.ID, 'ch_cus_LoginLink')))
#             login_link.click()
#             logger.info("Clicked on login link")
#         except TimeoutException:
#             logger.warning("Could not find login link, trying alternative approaches")

#             # Try looking for login form directly
#             try:
#                 username_input = wait.until(EC.presence_of_element_located((By.ID, 'clogin_TxtUsername')))
#                 logger.info("Found username field directly")
#             except TimeoutException:
#                 # Try clicking any login links on the page
#                 login_links = driver.find_elements(By.XPATH,
#                                                    "//a[contains(text(), 'Login')] | //a[contains(text(), 'Sign In')]")
#                 if login_links:
#                     logger.info("Found alternate login link")
#                     login_links[0].click()
#                 else:
#                     raise Exception("Could not find any login links or forms")

#         # Wait for and fill in username and password
#         try:
#             user_input = wait.until(EC.presence_of_element_located((By.ID, 'clogin_TxtUsername')))
#             pass_input = wait.until(EC.presence_of_element_located((By.ID, 'clogin_TxtPassword')))

#             user_input.clear()
#             pass_input.clear()
#             user_input.send_keys(username)
#             pass_input.send_keys(password)

#             # Click login button
#             login_button = wait.until(EC.element_to_be_clickable((By.ID, 'clogin_ButtonLogin')))
#             login_button.click()

#             # Wait for page to load after login
#             wait.until(EC.presence_of_element_located((By.ID, 'ch_cus_CustomerPage')))
#             logger.info("Login successful")
#             return True
#         except TimeoutException:
#             # Try alternative login approach
#             logger.warning("Standard login elements not found, trying alternative approach")

#             # Look for any username/password fields
#             inputs = driver.find_elements(By.TAG_NAME, 'input')
#             text_inputs = [inp for inp in inputs if inp.get_attribute('type') in ['text', 'email', None]]
#             password_inputs = [inp for inp in inputs if inp.get_attribute('type') == 'password']

#             if text_inputs and password_inputs:
#                 text_inputs[0].clear()
#                 password_inputs[0].clear()
#                 text_inputs[0].send_keys(username)
#                 password_inputs[0].send_keys(password)

#                 # Look for login button
#                 buttons = driver.find_elements(By.XPATH,
#                                                "//input[@type='submit'] | //button[contains(text(), 'Login')] | //button[contains(text(), 'Sign In')]")
#                 if buttons:
#                     buttons[0].click()

#                     # Wait for login to complete
#                     time.sleep(5)

#                     # Check if login was successful
#                     if 'login.aspx' not in driver.current_url:
#                         logger.info("Login successful via alternative method")
#                         return True
#                     else:
#                         raise Exception("Login failed - still on login page")
#                 else:
#                     raise Exception("Could not find login button")
#             else:
#                 raise Exception("Could not find username and password fields")

#     except Exception as e:
#         logger.error(f"Login error: {e}")
#         raise


# def MyGrantScraper(partNo, driver, logger):
#     """Scrape part information from MyGrant website with robust error handling"""
#     max_retries = 2
#     retry_count = 0

#     while retry_count < max_retries:
#         try:
#             # URL for part search
#             url = f'https://www.mygrantglass.com/pages/search.aspx?q={partNo}&sc=r&do=Search'
#             parts = []

#             logger.info(f"Searching part in MyGrant: {partNo}")
#             driver.get(url)

#             # Check if login is required
#             current_url = driver.current_url
#             if 'login.aspx' in current_url:
#                 logger.info("Login required")
#                 login(driver, logger)
#                 driver.get(url)

#             # Wait for search results to load
#             wait = WebDriverWait(driver, 15)

#             # First try to see if we have results at all
#             try:
#                 # Wait for either results div or "no results" message
#                 wait.until(EC.presence_of_element_located((
#                     By.XPATH,
#                     "//div[@id='cpsr_DivParts'] | //div[contains(text(), 'No results')] | //div[contains(@class, 'no-results')]"
#                 )))

#                 # Check for "no results" message
#                 no_results = driver.find_elements(By.XPATH,
#                                                   "//div[contains(text(), 'No results')] | //div[contains(@class, 'no-results')]")
#                 if no_results:
#                     logger.info(f"No results found for part {partNo}")
#                     return []

#                 # Get page source for BeautifulSoup parsing
#                 page_source = driver.page_source
#                 soup = BeautifulSoup(page_source, 'html.parser')

#                 # Find the parts results div
#                 div = soup.find('div', {'id': 'cpsr_DivParts'})

#                 # If div is None, try different selectors
#                 if not div:
#                     logger.warning("Could not find results div by ID, trying alternate selectors")
#                     div = soup.find('div', {'class': 'results'})

#                     if not div:
#                         div = soup.find('div', {'class': 'product-results'})

#                     if not div:
#                         # Try searching for tables directly
#                         tables = soup.find_all('table')
#                         if tables:
#                             logger.info(f"Found {len(tables)} tables directly")

#                             # Process using tables directly
#                             location = "Unknown"  # Default location

#                             for table in tables:
#                                 rows = table.find_all('tr')
#                                 if len(rows) <= 1:  # Skip tables without data rows
#                                     continue

#                                 for row in rows[1:]:  # Skip header row
#                                     cells = row.find_all('td')
#                                     if len(cells) < 3:  # Need minimum number of cells
#                                         continue

#                                     try:
#                                         # Look for part number in cells
#                                         part_number = None
#                                         for cell in cells:
#                                             cell_text = cell.text.strip()
#                                             if partNo.lower() in cell_text.lower():
#                                                 part_number = cell_text
#                                                 break

#                                         if part_number:
#                                             # Extract other data
#                                             availability = cells[0].text.strip() if len(cells) > 0 else "Unknown"
#                                             price = cells[2].text.strip() if len(cells) > 2 else "Unknown"

#                                             parts.append([
#                                                 part_number,  # Part Number
#                                                 availability,  # Availability
#                                                 price,  # Price
#                                                 location  # Location
#                                             ])
#                                     except Exception as e:
#                                         logger.warning(f"Error processing row: {e}")
#                                         continue

#                             # If we found parts, return them
#                             if parts:
#                                 return parts

#                         # If we still don't have any results, try extracting from page text
#                         logger.warning("Could not find results using HTML parsing, trying text extraction")

#                         # Get text containing part number
#                         if partNo.lower() in page_source.lower():
#                             logger.info(f"Found part number {partNo} in page source, creating basic result")
#                             parts.append([
#                                 partNo,  # Part Number
#                                 "Unknown",  # Availability
#                                 "Unknown",  # Price
#                                 "Unknown"  # Location
#                             ])
#                             return parts

#                         logger.warning("No results div found and no part number in page source")
#                         return []

#                 # If we have a valid div, proceed with normal parsing
#                 if div:
#                     # Find all location headings (h3 elements)
#                     locations = div.find_all('h3')

#                     # If no locations found, try other heading elements
#                     if not locations:
#                         locations = div.find_all(['h2', 'h4', 'strong'])

#                     # Skip first heading if it's not a location
#                     if locations and not (' - ' in locations[0].text):
#                         locations = locations[1:]

#                     # If still no locations, use a default
#                     if not locations:
#                         locations = ["Unknown Location"]

#                     # Find all tables
#                     tables = div.find_all('tbody')

#                     # If no tbody elements, look for tables directly
#                     if not tables:
#                         tables = div.find_all('table')

#                     # Process each table (each location has a table)
#                     for i, table in enumerate(tables):
#                         current_location = "Unknown"
#                         if i < len(locations):
#                             location_text = locations[i].text.strip()
#                             if ' - ' in location_text:
#                                 current_location = location_text.split(' - ')[0].strip()
#                             else:
#                                 current_location = location_text

#                         # Process rows in the table
#                         rows = table.find_all('tr')
#                         if len(rows) <= 1:
#                             continue  # Skip table if only has header row

#                         rows = rows[1:]  # Skip header row

#                         for row in rows:
#                             data = row.find_all('td')
#                             if len(data) <= 1:
#                                 continue

#                             try:
#                                 # Get part number from link or text
#                                 part_number = None
#                                 part_element = None

#                                 # Try to find a link containing part number
#                                 for idx, cell in enumerate(data):
#                                     links = cell.find_all('a')
#                                     if links:
#                                         link_text = links[0].text.strip()
#                                         if partNo.lower() in link_text.lower():
#                                             part_number = link_text
#                                             part_element = cell
#                                             break

#                                 # If no link found, try cell text
#                                 if not part_number:
#                                     for idx, cell in enumerate(data):
#                                         cell_text = cell.text.strip()
#                                         if partNo.lower() in cell_text.lower():
#                                             part_number = cell_text
#                                             part_element = cell
#                                             break

#                                 # Skip if part number not found
#                                 if not part_number:
#                                     continue

#                                 # Find the index of the part element
#                                 part_idx = data.index(part_element) if part_element else -1

#                                 # Get availability (usually in first cell)
#                                 availability = "Unknown"
#                                 try:
#                                     avail_cell = data[0]
#                                     availability_span = avail_cell.find('span')
#                                     if availability_span:
#                                         availability = availability_span.text.strip()
#                                     else:
#                                         availability = avail_cell.text.strip()
#                                 except (IndexError, AttributeError):
#                                     pass

#                                 # Get price (usually in third cell)
#                                 price = "Unknown"
#                                 try:
#                                     if len(data) > 2:
#                                         price = data[2].text.strip()
#                                 except IndexError:
#                                     pass

#                                 # Add to parts list
#                                 parts.append([
#                                     part_number,  # Part Number
#                                     availability,  # Availability
#                                     price,  # Price
#                                     current_location  # Location
#                                 ])
#                                 logger.info(f"Found part: {part_number} at {current_location}")
#                             except Exception as e:
#                                 logger.warning(f"Error processing row: {e}")
#                                 continue

#                 # Return the parts we found
#                 return parts

#             except TimeoutException:
#                 logger.warning("Timeout waiting for search results")

#                 # Try a more basic approach
#                 if partNo.lower() in driver.page_source.lower():
#                     logger.info(f"Found part number {partNo} in page source")
#                     parts.append([
#                         partNo,  # Part Number
#                         "Unknown",  # Availability
#                         "Unknown",  # Price
#                         "Unknown"  # Location
#                     ])
#                     return parts

#                 return []

#         except Exception as e:
#             logger.error(f"Error in MyGrant scraper (attempt {retry_count + 1}/{max_retries}): {e}")
#             retry_count += 1

#             if retry_count < max_retries:
#                 logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
#                 time.sleep(2)  # Brief pause before retry
#             else:
#                 logger.error(f"Failed after {max_retries} attempts")
#                 return []  # Return empty list instead of None


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
#         results = MyGrantScraper("FW4202", driver, logger)

#         if results:
#             for part in results:
#                 print(f"Part: {part[0]}, Availability: {part[1]}, Price: {part[2]}, Location: {part[3]}")
#         else:
#             print("No results found")
#     finally:
#         driver.quit()

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


def login(driver, logger):
    """Login to MyGrant website with improved error handling and caching"""
    global _login_cache
    
    # Check driver responsiveness first
    if not is_driver_responsive(driver, logger):
        logger.error("Driver not responsive before login")
        return False
    
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
        # Use faster page load strategy
        try:
            driver.set_page_load_timeout(15)
            driver.get('https://www.mygrantglass.com/pages/login.aspx')
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
                else:
                    logger.error("Could not find any login links or forms")
                    return False

        # Wait for and fill in username and password - optimized selector usage
        try:
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
            except:
                # Fallback to traditional input if JavaScript fails
                user_input.clear()
                user_input.send_keys(username)
                pass_input.clear()
                pass_input.send_keys(password)

            # Click login button
            login_button = wait.until(EC.element_to_be_clickable((By.ID, 'clogin_ButtonLogin')))
            safe_click(login_button, driver)

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
                    password_inputs[0].clear()
                    password_inputs[0].send_keys(password)

                    # Look for login button with more specific selector
                    buttons = driver.find_elements(By.XPATH,
                                                   "//input[@type='submit'] | //button[contains(text(), 'Login')] | //button[contains(text(), 'Sign In')]")
                    if buttons:
                        safe_click(buttons[0], driver)

                        # Wait for login to complete - reduced wait time
                        time.sleep(2)

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
    max_retries = 2
    retry_count = 0
    start_time = time.time()
    
    # Check driver responsiveness
    if not is_driver_responsive(driver, logger):
        logger.error("Driver not responsive at start of scraper")
        return []

    while retry_count < max_retries:
        try:
            logger.info(f"Searching part in MyGrant: {partNo} (attempt {retry_count + 1}/{max_retries})")
            
            # Set shorter timeouts to prevent hangs
            try:
                driver.set_page_load_timeout(15)
            except:
                pass
                
            # Direct URL for part search - faster than navigating through site
            search_url = f'https://www.mygrantglass.com/pages/search.aspx?q={partNo}&sc=r&do=Search'
            parts = []

            # Try to load the search page
            try:
                driver.get(search_url)
            except TimeoutException:
                logger.warning("Page load timed out, continuing with what loaded")
            except Exception as e:
                logger.warning(f"Error loading search page: {e}")
                if retry_count == max_retries - 1:
                    # Try simpler URL on last retry
                    try:
                        driver.get('https://www.mygrantglass.com/pages/search.aspx')
                        # Try to search directly using form
                        try:
                            search_box = driver.find_element(By.ID, "cpsr_TxtSearch")
                            search_box.clear()
                            search_box.send_keys(partNo)
                            search_box.send_keys(Keys.RETURN)
                            logger.info("Used search form directly")
                        except:
                            logger.warning("Could not use search form")
                    except:
                        logger.error("Could not load simple search page")
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
                    driver.get(search_url)
                except TimeoutException:
                    logger.warning("Search page reload timed out after login, continuing")
                except Exception as e:
                    logger.warning(f"Error reloading search page after login: {e}")


            try:
                logger.info(f"Starting extraction process for part {partNo}")
                # Use shorter timeout for elements
                wait = WebDriverWait(driver, 5)
                logger.debug(f"Created WebDriverWait with timeout of 5 seconds")

                # Wait for either results div or "no results" message
                try:
                    logger.info(f"Waiting for results elements to appear on page")
                    # Wait for either results div or "no results" message
                    wait.until(EC.presence_of_element_located((
                        By.XPATH,
                        "//div[@id='cpsr_DivParts'] | //div[contains(text(), 'No results')] | //div[contains(@class, 'no-results')]"
                    )))
                    logger.debug(f"Found either results div or 'no results' message")

                    # Check for "no results" message
                    logger.debug(f"Checking for 'no results' message")
                    no_results = driver.find_elements(By.XPATH,
                                                      "//div[contains(text(), 'No results')] | //div[contains(@class, 'no-results')]")
                    if no_results:
                        logger.info(f"No results found for part {partNo}")
                        return []

                    # Get page source for BeautifulSoup parsing
                    logger.debug(f"Getting page source for BeautifulSoup parsing")
                    page_source = driver.page_source
                    logger.debug(f"Page source length: {len(page_source)} characters")
                    soup = BeautifulSoup(page_source, 'html.parser')
                    logger.debug(f"BeautifulSoup object created")

                    # Find the parts results div
                    logger.debug(f"Searching for parts results div with id 'cpsr_DivParts'")
                    div = soup.find('div', {'id': 'cpsr_DivParts'})
                    logger.debug(f"Parts results div found: {div is not None}")

                    # If we have a valid div, proceed with normal parsing
                    if div:
                        logger.info(f"Valid results div found, proceeding with parsing")
                        # Find all location headings (h3 elements)
                        logger.debug(f"Searching for location headings (h3 elements)")
                        locations = div.find_all('h3')
                        logger.debug(f"Found {len(locations)} h3 elements")

                        # If no locations found, try other heading elements
                        if not locations:
                            logger.info(f"No h3 elements found, trying alternative heading elements")
                            locations = div.find_all(['h2', 'h4', 'strong'])
                            logger.debug(f"Found {len(locations)} alternative heading elements")

                        # Skip first heading if it's not a location
                        if locations and not (' - ' in locations[0].text):
                            logger.debug(f"First heading does not appear to be a location, skipping")
                            locations = locations[1:]
                            logger.debug(f"After skipping, {len(locations)} locations remain")

                        # If still no locations, use a default
                        if not locations:
                            logger.warning(f"No location elements found, using default")
                            locations = ["Unknown Location"]
                            logger.debug(f"Using default location: 'Unknown Location'")

                        # Find all tables
                        logger.debug(f"Searching for tables (tbody elements)")
                        tables = div.find_all('tbody')
                        logger.debug(f"Found {len(tables)} tbody elements")

                        # If no tbody elements, look for tables directly
                        if not tables:
                            logger.info(f"No tbody elements found, searching for table elements directly")
                            tables = div.find_all('table')
                            logger.debug(f"Found {len(tables)} table elements")

                        # Process each table (each location has a table)
                        logger.info(f"Beginning to process {len(tables)} tables")
                        for i, table in enumerate(tables):
                            logger.debug(f"Processing table {i + 1} of {len(tables)}")
                            current_location = "Unknown"
                            if i < len(locations):
                                location_text = locations[i].text.strip()
                                logger.debug(f"Location text: '{location_text}'")
                                if ' - ' in location_text:
                                    current_location = location_text.split(' - ')[0].strip()
                                    logger.debug(f"Extracted location: '{current_location}'")
                                else:
                                    current_location = location_text
                                    logger.debug(f"Using whole text as location: '{current_location}'")
                            else:
                                logger.debug(f"No matching location for table {i + 1}, using 'Unknown'")

                            # Process rows in the table
                            logger.debug(f"Finding rows in table {i + 1}")
                            rows = table.find_all('tr')
                            logger.debug(f"Found {len(rows)} rows in table {i + 1}")
                            if len(rows) <= 1:
                                logger.warning(f"Table {i + 1} has {len(rows)} rows (possibly only header), skipping")
                                continue  # Skip table if only has header row

                            rows = rows[1:]  # Skip header row
                            logger.debug(f"After skipping header, processing {len(rows)} rows")

                            for row_idx, row in enumerate(rows):
                                logger.debug(f"Processing row {row_idx + 1} of {len(rows)}")
                                data = row.find_all('td')
                                logger.debug(f"Found {len(data)} cells in row {row_idx + 1}")
                                if len(data) <= 1:
                                    logger.warning(f"Row {row_idx + 1} has only {len(data)} cell(s), skipping")
                                    continue

                                try:
                                    logger.debug(f"Attempting to extract part information from row {row_idx + 1}")
                                    # Get part number from link or text
                                    part_number = None
                                    part_element = None

                                    # Try to find a link containing part number
                                    logger.debug(f"Searching for part number in links")
                                    for idx, cell in enumerate(data):
                                        links = cell.find_all('a')
                                        if links:
                                            logger.debug(f"Found {len(links)} links in cell {idx + 1}")
                                            link_text = links[0].text.strip()
                                            logger.debug(f"Link text: '{link_text}'")
                                            if partNo.lower() in link_text.lower():
                                                part_number = link_text
                                                part_element = cell
                                                logger.debug(f"Found matching part number '{part_number}' in link")
                                                break

                                    # If no link found, try cell text
                                    if not part_number:
                                        logger.debug(f"No matching part in links, searching cell text")
                                        for idx, cell in enumerate(data):
                                            cell_text = cell.text.strip()
                                            logger.debug(f"Cell {idx + 1} text: '{cell_text}'")
                                            if partNo.lower() in cell_text.lower():
                                                part_number = cell_text
                                                part_element = cell
                                                logger.debug(f"Found matching part number '{part_number}' in cell text")
                                                break

                                    # Skip if part number not found
                                    if not part_number:
                                        logger.warning(
                                            f"Part number '{partNo}' not found in row {row_idx + 1}, skipping")
                                        continue

                                    # Find the index of the part element
                                    part_idx = data.index(part_element) if part_element else -1
                                    logger.debug(f"Part element found at index {part_idx}")

                                    # Get availability (usually in first cell)
                                    availability = "Unknown"
                                    try:
                                        logger.debug(f"Attempting to extract availability")
                                        avail_cell = data[1]
                                        availability_span = avail_cell.find('span')
                                        if availability_span:
                                            availability = availability_span.text.strip()
                                            logger.debug(f"Extracted availability from span: '{availability}'")
                                        else:
                                            availability = avail_cell.text.strip()
                                            logger.debug(f"Extracted availability from cell text: '{availability}'")
                                    except (IndexError, AttributeError) as e:
                                        logger.warning(f"Error extracting availability: {e}")
                                        pass

                                    # Get price (usually in third cell)
                                    price = "Unknown"
                                    try:
                                        logger.debug(f"Attempting to extract price")
                                        if len(data) > 2:
                                            price = data[3].text.strip()
                                            logger.debug(f"Extracted price: '{price}'")
                                    except IndexError as e:
                                        logger.warning(f"Error extracting price: {e}")
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
                                    logger.info(f"Found part: {part_number} at {current_location}")
                                except Exception as e:
                                    logger.warning(f"Error processing row {row_idx + 1}: {str(e)}")
                                    logger.debug(f"Exception details:", exc_info=True)
                                    continue

                        # Return the parts we found
                        logger.info(f"Extraction complete, found {len(parts)} parts matching '{partNo}'")
                        return parts

                except TimeoutException:
                    logger.warning(f"Timeout waiting for search results elements for part {partNo}")

                    # Final check of page source
                    logger.debug(f"Performing final check of page source for part {partNo}")
                    if partNo.lower() in driver.page_source.lower():
                        logger.info(f"Part {partNo} found in page despite timeout, creating generic entry")
                        return [[
                            partNo,
                            "Available - Check Store",
                            "Contact for Price",
                            "Unknown"
                        ]]
                    else:
                        logger.warning(f"Part {partNo} not found in page source after timeout")

            except Exception as e:
                logger.error(f"Critical error in structured extraction for part {partNo}: {str(e)}")
                logger.debug(f"Exception details:", exc_info=True)
            # Increment retry counter
            retry_count += 1
            
            # If this wasn't the last retry, wait briefly and try again
            if retry_count < max_retries:
                logger.info(f"Retrying search (attempt {retry_count + 1}/{max_retries})")
                time.sleep(1)
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
                time.sleep(1)  # Brief pause before retry
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