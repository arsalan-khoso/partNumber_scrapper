from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
import logging
import time
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = 'https://importglasscorp.com'
SEARCH_URL = f'{BASE_URL}/product/search/'
LOGIN_TIMEOUT = 3
SEARCH_TIMEOUT = 2
CONCURRENT_REQUESTS = 10  # Increased concurrency for bs4 (lighter weight)

# Cache for storing session
SESSION = None

def login(driver):
    """Login to Import Glass Corp website and create a requests session with cookies"""
    global SESSION
    start_time = time.time()
    logger.info("Attempting login to Import Glass Corp")
    
    load_dotenv()
    username = os.getenv('IGC_USER')
    password = os.getenv('IGC_PASS')
    cn = os.getenv('IGC_CN')
    
    if not all([username, password, cn]):
        logger.error("Missing login credentials in .env file")
        raise ValueError("Missing login credentials")
    
    try:
        wait = WebDriverWait(driver, LOGIN_TIMEOUT)
        driver.get(BASE_URL)
        
        # Use JavaScript to fill form fields directly - much faster
        driver.execute_script("""
            document.getElementById('email-address').value = arguments[0];
            document.getElementById('customer-number').value = arguments[1];
            document.getElementById('password').value = arguments[2];
        """, username, cn, password)
        
        # Use JS to submit form
        driver.execute_script("""
            document.querySelector('button').click();
        """)

        # Wait for login to complete by checking URL change
        wait.until(EC.url_changes(BASE_URL))
        
        # Create a requests session and add cookies from selenium
        SESSION = requests.Session()
        for cookie in driver.get_cookies():
            SESSION.cookies.set(cookie['name'], cookie['value'])
        
        elapsed = time.time() - start_time
        logger.info(f"Login successful in {elapsed:.2f} seconds")
        return True

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Login failed after {elapsed:.2f} seconds: {str(e)}")
        raise

def check_login_status(driver):
    """Check if we need to login and do so if necessary"""
    login_indicators = [
        "login" in driver.current_url.lower(),
        len(driver.find_elements(By.ID, "email-address")) > 0
    ]
    
    if any(login_indicators):
        logger.info("Login required - authenticating")
        login(driver)
        return True
    return False

def search_parts_with_requests(part_number):
    """Perform search for parts using requests instead of Selenium"""
    global SESSION
    start_time = time.time()
    
    if not SESSION:
        logger.error("No active session. Login required.")
        return []
    
    try:
        # Create search payload
        search_data = {'search': part_number}
        
        # Send search request
        response = SESSION.post(SEARCH_URL, data=search_data)
        
        if response.status_code != 200:
            logger.error(f"Search request failed with status code {response.status_code}")
            return []
        
        # Parse search results with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all tables
        tables = soup.find_all('table')
        
        search_results = []
        for table in tables:
            # Try to find category from previous h4
            category = "Unknown"
            prev = table.find_previous('h4')
            if prev:
                category = prev.get_text(strip=True)
            
            # Find all rows in table
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                
                part_link = cells[0].find('a')
                if not part_link:
                    continue
                
                part_number = part_link.get_text(strip=True)
                part_url = part_link.get('href')
                # Make sure URL is absolute
                if part_url and not part_url.startswith('http'):
                    part_url = BASE_URL + ('' if part_url.startswith('/') else '/') + part_url
                
                description = cells[1].get_text(strip=True)
                
                search_results.append({
                    'part_number': part_number,
                    'description': description,
                    'category': category,
                    'url': part_url
                })
        
        elapsed = time.time() - start_time
        logger.info(f"Found {len(search_results)} parts in search results in {elapsed:.2f} seconds")
        return search_results
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Search failed after {elapsed:.2f} seconds: {str(e)}")
        return []

def fetch_detail_page(url):
    """Fetch a detail page using requests session"""
    global SESSION
    if not SESSION:
        logger.error("No active session. Login required.")
        return None
    
    try:
        response = SESSION.get(url)
        if response.status_code == 200:
            return response.text
        else:
            logger.warning(f"Failed to fetch {url}, status code: {response.status_code}")
            return None
    except Exception as e:
        logger.warning(f"Error fetching {url}: {str(e)}")
        return None

def parse_detail_page(html_content, part_info):
    """Parse detail page HTML with BeautifulSoup and extract part information"""
    if not html_content:
        return None
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check location - find warehouse mention
        location = "Unknown"
        location_elements = soup.find_all('b')
        for element in location_elements:
            text = element.get_text()
            if "Locka" in text or "Warehouse" in text:
                location = text
                break
        
        # Skip if not in Opa-Locka
        if location != "Unknown" and "Opa-Locka" not in location:
            logger.debug(f"Part {part_info['part_number']} not available in Opa-Locka")
            return None
        
        # Find tables
        tables = soup.find_all('table')
        if not tables:
            return None
        
        # Check rows for part data
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 5:  # Need minimum columns
                    continue
                
                # Check if part number matches
                row_part_number = cells[0].get_text(strip=True)
                if part_info['part_number'] not in row_part_number:
                    continue
                
                # Find price - check several cells
                price = "Unknown"
                for i in range(2, min(5, len(cells))):
                    price_elements = cells[i].find_all('b')
                    for p_elem in price_elements:
                        price_text = p_elem.get_text(strip=True)
                        if "$" in price_text or any(c.isdigit() for c in price_text):
                            price = price_text
                            break
                
                # Check availability
                availability = "No"
                for cell in cells:
                    cell_text = cell.get_text()
                    if "In Stock" in cell_text:
                        availability = "Yes"
                        break
                
                return [
                    part_info["part_number"],
                    availability,
                    price,
                    location
                ]
        
        # If we didn't find a matching row
        return None
    
    except Exception as e:
        logger.warning(f"Error parsing detail page for {part_info['part_number']}: {str(e)}")
        return [
            part_info["part_number"],
            "Unknown",
            "Unknown",
            "Unknown"
        ]

def process_part_details(part_info):
    """Process a single part's details page"""
    start_time = time.time()
    
    try:
        html_content = fetch_detail_page(part_info['url'])
        result = parse_detail_page(html_content, part_info)
        
        elapsed = time.time() - start_time
        if result:
            logger.debug(f"Processed {part_info['part_number']} in {elapsed:.2f}s")
        else:
            logger.debug(f"No matching data for {part_info['part_number']} in {elapsed:.2f}s")
        
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(f"Error processing {part_info['part_number']} after {elapsed:.2f}s: {str(e)}")
        return None

def process_all_parts(search_results):
    """Process all parts in parallel using BS4 and requests"""
    start_time = time.time()
    
    if not search_results:
        return []
    
    try:
        # Process in parallel with increased concurrency (BS4 is lightweight)
        with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
            # Map is more memory efficient than gathering all futures
            result_generator = executor.map(process_part_details, search_results)
            
            # Filter out None results
            results = [r for r in result_generator if r]
        
        elapsed = time.time() - start_time
        logger.info(f"Processed {len(results)}/{len(search_results)} parts in {elapsed:.2f} seconds")
        return results
    
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Failed to process parts after {elapsed:.2f} seconds: {str(e)}")
        return []

def IGCScraper(partNo, driver, logger):
    """Ultra-fast scraper using Selenium only for login, then BS4+requests"""
    overall_start = time.time()
    logger.info(f"Starting search for part: {partNo}")
    
    try:
        # Navigate to the search page - just to check login status
        driver.get(SEARCH_URL)
        
        # Check if login is needed
        try:
            check_login_status(driver)
        except Exception as e:
            logger.warning(f"Login check error: {str(e)}")
            return []
            
        # From this point, we use requests+BS4 instead of Selenium
        # Search for parts using requests
        search_results = search_parts_with_requests(partNo)
        
        if not search_results:
            logger.warning(f"No parts found matching '{partNo}'")
            return []
        
        # Process all details in parallel with BS4
        final_results = process_all_parts(search_results)
        
        overall_elapsed = time.time() - overall_start
        logger.info(f"Completed search for '{partNo}' - Found {len(final_results)} parts in {overall_elapsed:.2f} seconds")
        
        return final_results
    
    except Exception as e:
        overall_elapsed = time.time() - overall_start
        logger.error(f"Error in main scraper for '{partNo}' after {overall_elapsed:.2f} seconds: {str(e)}")
        return []


# Example of how to use the scraper
if __name__ == "__main__":
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    import sys
    
    # Get part number from command line or use default
    part_to_search = sys.argv[1] if len(sys.argv) > 1 else "2000"
    
    # Very minimal Selenium settings - we only need it for login
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--disable-extensions")
    
    # Initialize the driver with minimal options (just for login)
    start_time = time.time()
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(10)
    
    try:
        # Search for part
        logger.info(f"Starting scrape for part: {part_to_search}")
        results = IGCScraper(part_to_search, driver, logger)
        
        # Print results
        if results:
            print(f"Found {len(results)} results for {part_to_search}:")
            for part in results:
                print(f"Part: {part[0]}, Available: {part[1]}, Price: {part[2]}, Location: {part[3]}")
        else:
            print(f"No results found for {part_to_search}")
            
        elapsed = time.time() - start_time
        logger.info(f"Total execution time: {elapsed:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
    finally:
        # Close the driver since we don't need it anymore after login
        driver.quit()