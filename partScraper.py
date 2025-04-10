# import asyncio
# import json
# import logging
# import os
# from concurrent.futures import ThreadPoolExecutor
# import undetected_chromedriver as uc
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import time
# import tempfile
# import shutil
# from dotenv import load_dotenv
# import signal

# # Set up logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("scraper.log"),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

# # Constants for optimization
# CHROME_VERSION = 134  # Update this to your Chrome version
# MAX_SCRAPER_TIME = 300  # Maximum time a scraper can run (seconds)
# SHARED_DRIVER_POOL_SIZE = 3 # Number of drivers to keep in pool
# IMPLICIT_WAIT = 5  # Reduced from 10
# PAGE_LOAD_TIMEOUT = 30  # Reduced from 60
# SCRIPT_TIMEOUT = 17  # Reduced from 30

# # Driver pool for reuse
# driver_pool = []
# driver_pool_lock = asyncio.Lock()

# async def get_driver_from_pool():
#     """Get a driver from the pool or create a new one if needed"""
#     async with driver_pool_lock:
#         if driver_pool:
#             return driver_pool.pop()
#         else:
#             return setup_chrome_driver()

# async def return_driver_to_pool(driver):
#     """Return a driver to the pool if it's still healthy"""
#     if len(driver_pool) < SHARED_DRIVER_POOL_SIZE:
#         try:
#             # Quick test to see if driver is responsive
#             driver.current_url  # Will throw if driver is unhealthy
#             async with driver_pool_lock:
#                 driver_pool.append(driver)
#             return True
#         except:
#             try:
#                 driver.quit()
#             except:
#                 pass
#             return False
#     else:
#         try:
#             driver.quit()
#         except:
#             pass
#         return False

# def setup_chrome_driver():
#     """Set up Chrome driver with properly configured Zyte proxy in headless mode with explicit California region"""
#     start_time = time.time()
#     try:
#         # Create a temp directory for the driver to avoid path conflicts
#         temp_dir = tempfile.mkdtemp()
#         driver_path = os.path.join(temp_dir, "chromedriver.exe")

#         # Set environment variable to use the temporary path
#         os.environ["UC_CHROMEDRIVER_PATH"] = driver_path

#         # Load Zyte credentials from environment variables
#         zyte_api_key = os.environ.get('ZYTE_API_KEY')
#         if not zyte_api_key:
#             logger.warning("ZYTE_API_KEY not found in environment variables")
            
#         options = uc.ChromeOptions()

        
        
#         # Basic anti-detection settings
#         options.add_argument("--disable-blink-features=AutomationControlled")
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-dev-shm-usage")
        
#         # ENABLE headless mode
#         options.add_argument("--headless=new")
        
#         # Use a standard, common user agent
#         options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')
        
#         # Set up Zyte proxy using a plugin
#         if zyte_api_key:
#             plugin_path = os.path.join(temp_dir, "zyte_proxy_plugin")
#             os.makedirs(plugin_path, exist_ok=True)
            
#             # Create manifest.json for the plugin
#             manifest_json = """
#             {
#                 "version": "1.0.0",
#                 "manifest_version": 2,
#                 "name": "Zyte Proxy",
#                 "permissions": [
#                     "proxy",
#                     "tabs",
#                     "unlimitedStorage",
#                     "storage",
#                     "<all_urls>",
#                     "webRequest",
#                     "webRequestBlocking"
#                 ],
#                 "background": {
#                     "scripts": ["background.js"]
#                 }
#             }
#             """
            
#             # Create background.js with your Zyte proxy config
#             # This is where we set the proxy host and authentication
#             background_js = """
#             // Base proxy configuration
#             var config = {
#                 mode: "fixed_servers",
#                 rules: {
#                     singleProxy: {
#                         scheme: "http",
#                         host: "smartproxy.zyte.com",
#                         port: 8011
#                     },
#                     bypassList: []
#                 }
#             };

#             chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

#             // Authentication callback with API key
#             function callbackFn(details) {
#                 return {
#                     authCredentials: {
#                         username: "%s",
#                         password: ""
#                     }
#                 };
#             }

#             // Listen for authentication challenges
#             chrome.webRequest.onAuthRequired.addListener(
#                 callbackFn,
#                 {urls: ["<all_urls>"]},
#                 ['blocking']
#             );

#             // Add headers for every request to set California region
#             chrome.webRequest.onBeforeSendHeaders.addListener(
#                 function(details) {
#                     // Add Zyte-specific headers for California geolocation
#                     details.requestHeaders.push({name: "X-Crawlera-Region", value: "us-ca"});
#                     details.requestHeaders.push({name: "X-Crawlera-Profile", value: "desktop"});
#                     details.requestHeaders.push({name: "X-Crawlera-Cookies", value: "enable"});
#                     return {requestHeaders: details.requestHeaders};
#                 },
#                 {urls: ["<all_urls>"]},
#                 ["blocking", "requestHeaders"]
#             );
#             """ % zyte_api_key
            
#             # Write the plugin files
#             with open(os.path.join(plugin_path, "manifest.json"), "w") as f:
#                 f.write(manifest_json)
#             with open(os.path.join(plugin_path, "background.js"), "w") as f:
#                 f.write(background_js)
                
#             # Add the plugin to Chrome
#             options.add_argument(f'--load-extension={plugin_path}')
#             logger.info(f"Zyte proxy plugin created with California (US-CA) region at {plugin_path}")
        
#         # Basic performance options
#         options.add_argument("--disable-extensions")
#         options.add_argument("--disable-popup-blocking")
#         options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images for better performance
        
#         # Add user data dir
#         user_data_dir = os.path.join(temp_dir, "user-data")
#         options.add_argument(f"--user-data-dir={user_data_dir}")
        
#         # Memory optimization
#         options.add_argument("--js-flags=--expose-gc")
#         options.add_argument("--aggressive-cache-discard")
#         options.add_argument("--disable-cache")
        
#         # Create driver with optimized timeouts
#         driver = uc.Chrome(version_main=CHROME_VERSION, options=options)
        
#         # Anti-detection script - run after driver creation
#         driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
#             'source': '''
#             Object.defineProperty(navigator, 'webdriver', {
#                 get: () => false,
#             });
#             Object.defineProperty(navigator, 'languages', {
#                 get: () => ['en-US', 'en'],
#             });
#             '''
#         })
        
#         # Also explicitly set headers using CDP command for any site that doesn't get headers from the plugin
#         driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
#             'headers': {
#                 'X-Crawlera-Profile': 'desktop',
#                 'X-Crawlera-Cookies': 'enable',
#                 'X-Crawlera-Region': 'us-ca',
#                 'X-Crawlera-UA': 'desktop',
#                 'X-Crawlera-Use-HTTPS': '1'
#             }
#         })
        
#         # Set timeouts
#         driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
#         driver.set_script_timeout(SCRIPT_TIMEOUT)
#         driver.implicitly_wait(IMPLICIT_WAIT)
        
#         # Verify proxy is working by visiting an IP checker
#         try:
#             # Try multiple IP check services
#             driver.get("https://api.myip.com/")
#             time.sleep(3)  # Give it time to load
            
#             ip_text = driver.find_element("tag name", "body").text
#             logger.info(f"IP info: {ip_text}")
            
#             # Try another IP service as backup
#             driver.get("https://httpbin.org/ip")
#             time.sleep(3)
#             ip_text = driver.find_element("tag name", "body").text
#             logger.info(f"IP from httpbin: {ip_text}")
            
#             # Check for geolocation specifically
#             driver.get("https://ipinfo.io/json")
#             time.sleep(3)
#             geo_text = driver.find_element("tag name", "body").text
#             logger.info(f"Geolocation info: {geo_text}")
            
#             # If we get here without errors, the proxy is working correctly
#             logger.info("Zyte proxy verification successful with California region")
            
#         except Exception as e:
#             logger.error(f"Failed to check IP: {e}")
        
#         elapsed = time.time() - start_time
#         logger.info(f"Chrome driver set up in {elapsed:.2f}s with Zyte proxy (California region) in headless mode")
#         return driver
#     except Exception as e:
#         elapsed = time.time() - start_time
#         logger.error(f"Driver setup failed after {elapsed:.2f}s: {e}")
#         raise


# async def scrape_with_driver(part_no, scraper_class, keys, name, timeout=MAX_SCRAPER_TIME):
#     """Run an individual scraper with its own driver and timeout"""
#     driver = None
#     start_time = time.time()
    
#     # Create a task for the actual scraper execution
#     try:
#         # Get a driver from the pool or create a new one
#         driver = await get_driver_from_pool()
        
#         # Add wait capability for the scraper to use
#         wait = WebDriverWait(driver, 10)
        
#         # Log the search attempt
#         logger.info(f"Searching part in {name}: {part_no}")
        
#         # Call the scraper function - wrap with timeout
#         try:
#             # Create a future for the scraper execution
#             loop = asyncio.get_event_loop()
#             scraper_future = loop.run_in_executor(None, lambda: scraper_class(part_no, driver, logger))
            
#             # Wait for scraper to complete with timeout
#             data = await asyncio.wait_for(scraper_future, timeout=timeout)
            
#             # Process results
#             if data:
#                 # Format data as dictionaries
#                 if isinstance(data, list) and all(isinstance(item, list) for item in data):
#                     data_dicts = [dict(zip(keys, item)) for item in data]
#                     result = {name: data_dicts}
#                 else:
#                     result = {name: data}
#             else:
#                 result = {name: []}
                
#             elapsed = time.time() - start_time
#             logger.info(f"{name} scraper completed in {elapsed:.2f}s")
#             return result
            
#         except asyncio.TimeoutError:
#             elapsed = time.time() - start_time
#             logger.warning(f"{name} scraper timed out after {elapsed:.2f}s")
#             return {name: []}
            
#         except Exception as e:
#             elapsed = time.time() - start_time
#             logger.error(f"{name} scraper failed after {elapsed:.2f}s: {e}")
#             return {name: []}

#     except Exception as e:
#         elapsed = time.time() - start_time
#         logger.error(f"Error in {name} scraper setup after {elapsed:.2f}s: {e}")
#         return {name: []}
#     finally:
#         # Return the driver to the pool if possible
#         if driver:
#             try:
#                 driver_reused = await return_driver_to_pool(driver)
#                 if driver_reused:
#                     logger.debug(f"Returned driver to pool for {name}")
#                 else:
#                     logger.debug(f"Driver disposed for {name}")
#             except Exception as e:
#                 logger.error(f"Error returning driver to pool for {name}: {e}")
#                 try:
#                     driver.quit()
#                 except:
#                     pass

# async def run_scrapers_concurrently(part_no):
#     """Run all scrapers concurrently and yield results as soon as they complete"""
#     # Import scrapers here to avoid circular imports
#     try:
#         start_time = time.time()
        
#         # Dynamically import all scrapers
#         from Scrapers.igc_scraper import IGCScraper
#         from Scrapers.pwg_scraper import PWGScraper
#         from Scrapers.pilkington_scraper import PilkingtonScraper
#         from Scrapers.mygrant_scraper import MyGrantScraper

#         # Load environment variables for credentials
#         load_dotenv()

#         # Define scrapers with their keys and individual timeouts
#         scrapers = [
#             ('IGC', IGCScraper, ["Part Number", "Availability", "Price", "Location"], 170),
#             ('PGW', PWGScraper, ["Part Number", "Availability", "Price", "Location", "Description"], 170),
#             ('Pilkington', PilkingtonScraper, ["Part Number", "Part Name", "Price", "Location"], 170),
#             ('MyGrant', MyGrantScraper, ["Part Number", "Availability", "Price", "Location"], 170),
#         ]

#         # Create tasks for each scraper with individual timeouts
#         tasks = {
#             asyncio.create_task(scrape_with_driver(part_no, scraper_class, keys, name, timeout)): name
#             for name, scraper_class, keys, timeout in scrapers
#         }
        
#         # Track which scrapers we've processed
#         pending = set(tasks.keys())
        
#         # Process results as they complete - don't wait for all to finish
#         while pending:
#             # Wait for the next result to complete
#             done, pending = await asyncio.wait(
#                 pending, 
#                 return_when=asyncio.FIRST_COMPLETED  # Process one at a time as they complete
#             )
            
#             # Handle completed tasks immediately
#             for done_task in done:
#                 try:
#                     result = done_task.result()
#                     yield json.dumps(result)
#                 except Exception as e:
#                     name = tasks[done_task]
#                     logger.error(f"Error processing {name} result: {e}")
#                     # Return empty result on error
#                     yield json.dumps({tasks[done_task]: []})
        
#         # Log total execution time
#         elapsed = time.time() - start_time
#         logger.info(f"All scrapers completed in {elapsed:.2f}s")

#     except Exception as e:
#         logger.error(f"Error in run_scrapers_concurrently: {e}")
#         yield json.dumps({"error": str(e)})
#     finally:
#         # Clean up any remaining drivers in the pool
#         async with driver_pool_lock:
#             for driver in driver_pool:
#                 try:
#                     driver.quit()
#                 except:
#                     pass
#             driver_pool.clear()

# def runScraper(part_no):
#     """Flask-compatible generator function that yields results as they become available"""
#     # Set up a new event loop for this request
#     try:
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)

#         # Create async generator - immediately yield results as they arrive
#         async def async_generator():
#             async for result in run_scrapers_concurrently(part_no):
#                 yield result

#         # Run the async generator in the event loop - yield each result immediately
#         gen = async_generator()
#         try:
#             while True:
#                 try:
#                     # Get next result from async generator
#                     result = loop.run_until_complete(gen.__anext__())
#                     yield result
#                 except StopAsyncIteration:
#                     # Generator is done
#                     break
#                 except Exception as e:
#                     logger.error(f"Error yielding result: {e}")
#                     yield json.dumps({"error": str(e)})
#         finally:
#             # Clean up
#             loop.close()

#     except Exception as e:
#         logger.error(f"Error in runScraper: {e}")
#         yield json.dumps({"error": str(e)})


# # For direct testing
# if __name__ == "__main__":
#     import sys

#     if len(sys.argv) > 1:
#         part_no = sys.argv[1]
#     else:
#         part_no = "2000"  # Default test part number

#     print(f"Testing scraper with part number: {part_no}")

#     # Set up signal handler for graceful termination
#     def signal_handler(sig, frame):
#         print("Stopping scrapers gracefully...")
#         sys.exit(0)
    
#     signal.signal(signal.SIGINT, signal_handler)

#     # Run the scraper and print results as they come in
#     total_start = time.time()
#     results_count = 0
    
#     for result in runScraper(part_no):
#         elapsed = time.time() - total_start
#         print(f"[{elapsed:.2f}s] {result}")
#         results_count += 1
    
#     total_time = time.time() - total_start
#     print(f"Scraped {results_count} sources in {total_time:.2f} seconds")	

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import tempfile
import shutil
from dotenv import load_dotenv
import signal

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants for optimization
CHROME_VERSION = 134  # Update this to your Chrome version
MAX_SCRAPER_TIME = 300  # Maximum time a scraper can run (seconds)
SHARED_DRIVER_POOL_SIZE = 3 # Number of drivers to keep in pool
IMPLICIT_WAIT = 5  # Reduced from 10
PAGE_LOAD_TIMEOUT = 30  # Reduced from 60
SCRIPT_TIMEOUT = 17  # Reduced from 30

# Driver pool for reuse
driver_pool = []
driver_pool_lock = asyncio.Lock()

async def get_driver_from_pool():
    """Get a driver from the pool or create a new one if needed"""
    async with driver_pool_lock:
        if driver_pool:
            return driver_pool.pop()
        else:
            return setup_chrome_driver()

async def return_driver_to_pool(driver):
    """Return a driver to the pool if it's still healthy"""
    if len(driver_pool) < SHARED_DRIVER_POOL_SIZE:
        try:
            # Quick test to see if driver is responsive
            driver.current_url  # Will throw if driver is unhealthy
            
            # Refresh Zyte headers before returning to pool
            try:
                driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                    'headers': {
                        'X-Crawlera-Profile': 'desktop',
                        'X-Crawlera-Cookies': 'enable',
                        # 'X-Crawlera-Region': 'us-ca',
                        'X-Crawlera-UA': 'desktop',
                        'X-Crawlera-Use-HTTPS': '1'
                    }
                })
            except Exception as e:
                logger.warning(f"Could not refresh Zyte headers before returning to pool: {e}")
            
            async with driver_pool_lock:
                driver_pool.append(driver)
            return True
        except:
            try:
                driver.quit()
            except:
                pass
            return False
    else:
        try:
            driver.quit()
        except:
            pass
        return False

def ensure_zyte_headers(driver):
    """Ensure Zyte headers are set for a driver - can be called before each navigation"""
    try:
        # Explicitly set headers using CDP command to ensure Zyte proxy is used
        driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
            'headers': {
                'X-Crawlera-Profile': 'desktop',
                'X-Crawlera-Cookies': 'enable',
                'X-Crawlera-Region': 'us-ca',
                'X-Crawlera-UA': 'desktop',
                'X-Crawlera-Use-HTTPS': '1'
            }
        })
        return True
    except Exception as e:
        logger.warning(f"Failed to set Zyte headers: {e}")
        return False

def setup_chrome_driver():
    """Set up Chrome driver with properly configured Zyte proxy in headless mode with explicit California region"""
    start_time = time.time()
    try:
        # Create a temp directory for the driver to avoid path conflicts
        temp_dir = tempfile.mkdtemp()
        driver_path = os.path.join(temp_dir, "chromedriver.exe")

        # Set environment variable to use the temporary path
        os.environ["UC_CHROMEDRIVER_PATH"] = driver_path

        # Load Zyte credentials from environment variables
        zyte_api_key = os.environ.get('ZYTE_API_KEY')
        if not zyte_api_key:
            logger.warning("ZYTE_API_KEY not found in environment variables")
            
        options = uc.ChromeOptions()
        
        # Basic anti-detection settings
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # ENABLE headless mode
        options.add_argument("--headless=new")
        
        # Use a standard, common user agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')
        
        # Set up Zyte proxy using a plugin
        if zyte_api_key:
            plugin_path = os.path.join(temp_dir, "zyte_proxy_plugin")
            os.makedirs(plugin_path, exist_ok=True)
            
            # Create manifest.json for the plugin
            manifest_json = """
            {
                "version": "1.0.0",
                "manifest_version": 2,
                "name": "Zyte Proxy",
                "permissions": [
                    "proxy",
                    "tabs",
                    "unlimitedStorage",
                    "storage",
                    "<all_urls>",
                    "webRequest",
                    "webRequestBlocking"
                ],
                "background": {
                    "scripts": ["background.js"]
                }
            }
            """
            
            # Create background.js with your Zyte proxy config
            # This is where we set the proxy host and authentication
            background_js = """
            // Base proxy configuration
            var config = {
                mode: "fixed_servers",
                rules: {
                    singleProxy: {
                        scheme: "http",
                        host: "smartproxy.zyte.com",
                        port: 8011
                    },
                    bypassList: []
                }
            };

            chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

            // Authentication callback with API key
            function callbackFn(details) {
                return {
                    authCredentials: {
                        username: "%s",
                        password: ""
                    }
                };
            }

            // Listen for authentication challenges
            chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
            );

            // Add headers for every request to set California region
            chrome.webRequest.onBeforeSendHeaders.addListener(
                function(details) {
                    // Add Zyte-specific headers for California geolocation
                    details.requestHeaders.push({name: "X-Crawlera-Region", value: "us-ca"});
                    details.requestHeaders.push({name: "X-Crawlera-Profile", value: "desktop"});
                    details.requestHeaders.push({name: "X-Crawlera-Cookies", value: "enable"});
                    return {requestHeaders: details.requestHeaders};
                },
                {urls: ["<all_urls>"]},
                ["blocking", "requestHeaders"]
            );
            """ % zyte_api_key
            
            # Write the plugin files
            with open(os.path.join(plugin_path, "manifest.json"), "w") as f:
                f.write(manifest_json)
            with open(os.path.join(plugin_path, "background.js"), "w") as f:
                f.write(background_js)
                
            # Add the plugin to Chrome
            options.add_argument(f'--load-extension={plugin_path}')
            logger.info(f"Zyte proxy plugin created with California (US-CA) region at {plugin_path}")
        
        # Basic performance options
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images for better performance
        
        # Add user data dir
        user_data_dir = os.path.join(temp_dir, "user-data")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # Memory optimization
        options.add_argument("--js-flags=--expose-gc")
        options.add_argument("--aggressive-cache-discard")
        options.add_argument("--disable-cache")
        
        # Create driver with optimized timeouts
        driver = uc.Chrome(version_main=CHROME_VERSION, options=options)
        
        # Anti-detection script - run after driver creation
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            '''
        })
        
        # Also explicitly set headers using CDP command for any site that doesn't get headers from the plugin
        ensure_zyte_headers(driver)
        
        # Set timeouts
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.set_script_timeout(SCRIPT_TIMEOUT)
        driver.implicitly_wait(IMPLICIT_WAIT)
        
        # Verify proxy is working by visiting an IP checker
        try:
            # Try multiple IP check services
            driver.get("https://api.myip.com/")
            time.sleep(1.5)
            
            ip_text = driver.find_element("tag name", "body").text
            logger.info(f"IP info: {ip_text}")
            
            # Try another IP service as backup
            driver.get("https://httpbin.org/ip")
            time.sleep(1.5)
            ip_text = driver.find_element("tag name", "body").text
            logger.info(f"IP from httpbin: {ip_text}")
            
            # Check for geolocation specifically
            driver.get("https://ipinfo.io/json")
            time.sleep(1.5)
            geo_text = driver.find_element("tag name", "body").text
            logger.info(f"Geolocation info: {geo_text}")
            
            # If we get here without errors, the proxy is working correctly
            logger.info("Zyte proxy verification successful with California region")
            
        except Exception as e:
            logger.error(f"Failed to check IP: {e}")
        
        elapsed = time.time() - start_time
        logger.info(f"Chrome driver set up in {elapsed:.2f}s with Zyte proxy (California region) in headless mode")
        return driver
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Driver setup failed after {elapsed:.2f}s: {e}")
        raise


async def scrape_with_driver(part_no, scraper_class, keys, name, timeout=MAX_SCRAPER_TIME):
    """Run an individual scraper with its own driver and timeout"""
    driver = None
    start_time = time.time()
    
    # Create a task for the actual scraper execution
    try:
        # Get a driver from the pool or create a new one
        driver = await get_driver_from_pool()
        
        # Add wait capability for the scraper to use
        wait = WebDriverWait(driver, 10)
        
        # Ensure Zyte headers are set before the scraper runs
        ensure_zyte_headers(driver)
        
        # Log the search attempt
        logger.info(f"Searching part in {name}: {part_no}")
        
        # Call the scraper function - wrap with timeout
        try:
            # Create a future for the scraper execution
            loop = asyncio.get_event_loop()
            scraper_future = loop.run_in_executor(None, lambda: scraper_class(part_no, driver, logger))
            
            # Wait for scraper to complete with timeout
            data = await asyncio.wait_for(scraper_future, timeout=timeout)
            
            # Process results
            if data:
                # Format data as dictionaries
                if isinstance(data, list) and all(isinstance(item, list) for item in data):
                    data_dicts = [dict(zip(keys, item)) for item in data]
                    result = {name: data_dicts}
                else:
                    result = {name: data}
            else:
                result = {name: []}
                
            elapsed = time.time() - start_time
            logger.info(f"{name} scraper completed in {elapsed:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.warning(f"{name} scraper timed out after {elapsed:.2f}s")
            return {name: []}
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{name} scraper failed after {elapsed:.2f}s: {e}")
            return {name: []}

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in {name} scraper setup after {elapsed:.2f}s: {e}")
        return {name: []}
    finally:
        # Return the driver to the pool if possible
        if driver:
            try:
                driver_reused = await return_driver_to_pool(driver)
                if driver_reused:
                    logger.debug(f"Returned driver to pool for {name}")
                else:
                    logger.debug(f"Driver disposed for {name}")
            except Exception as e:
                logger.error(f"Error returning driver to pool for {name}: {e}")
                try:
                    driver.quit()
                except:
                    pass

async def run_scrapers_concurrently(part_no):
    """Run all scrapers concurrently and yield results as soon as they complete"""
    # Import scrapers here to avoid circular imports
    try:
        start_time = time.time()
        
        # Dynamically import all scrapers
        from Scrapers.igc_scraper import IGCScraper
        from Scrapers.pwg_scraper import PWGScraper
        from Scrapers.pilkington_scraper import PilkingtonScraper
        from Scrapers.mygrant_scraper import MyGrantScraper

        # Load environment variables for credentials
        load_dotenv()

        # Define scrapers with their keys and individual timeouts
        scrapers = [
            ('IGC', IGCScraper, ["Part Number", "Availability", "Price", "Location"], 170),
            ('PGW', PWGScraper, ["Part Number", "Availability", "Price", "Location", "Description"], 170),
            ('Pilkington', PilkingtonScraper, ["Part Number", "Part Name", "Price", "Location"], 170),
            ('MyGrant', MyGrantScraper, ["Part Number", "Availability", "Price", "Location"], 170),
        ]

        # Create tasks for each scraper with individual timeouts
        tasks = {
            asyncio.create_task(scrape_with_driver(part_no, scraper_class, keys, name, timeout)): name
            for name, scraper_class, keys, timeout in scrapers
        }
        
        # Track which scrapers we've processed
        pending = set(tasks.keys())
        
        # Process results as they complete - don't wait for all to finish
        while pending:
            # Wait for the next result to complete
            done, pending = await asyncio.wait(
                pending, 
                return_when=asyncio.FIRST_COMPLETED  # Process one at a time as they complete
            )
            
            # Handle completed tasks immediately
            for done_task in done:
                try:
                    result = done_task.result()
                    yield json.dumps(result)
                except Exception as e:
                    name = tasks[done_task]
                    logger.error(f"Error processing {name} result: {e}")
                    # Return empty result on error
                    yield json.dumps({tasks[done_task]: []})
        
        # Log total execution time
        elapsed = time.time() - start_time
        logger.info(f"All scrapers completed in {elapsed:.2f}s")

    except Exception as e:
        logger.error(f"Error in run_scrapers_concurrently: {e}")
        yield json.dumps({"error": str(e)})
    finally:
        # Clean up any remaining drivers in the pool
        async with driver_pool_lock:
            for driver in driver_pool:
                try:
                    driver.quit()
                except:
                    pass
            driver_pool.clear()

def runScraper(part_no):
    """Flask-compatible generator function that yields results as they become available"""
    # Set up a new event loop for this request
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create async generator - immediately yield results as they arrive
        async def async_generator():
            async for result in run_scrapers_concurrently(part_no):
                yield result

        # Run the async generator in the event loop - yield each result immediately
        gen = async_generator()
        try:
            while True:
                try:
                    # Get next result from async generator
                    result = loop.run_until_complete(gen.__anext__())
                    yield result
                except StopAsyncIteration:
                    # Generator is done
                    break
                except Exception as e:
                    logger.error(f"Error yielding result: {e}")
                    yield json.dumps({"error": str(e)})
        finally:
            # Clean up
            loop.close()

    except Exception as e:
        logger.error(f"Error in runScraper: {e}")
        yield json.dumps({"error": str(e)})


# For direct testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        part_no = sys.argv[1]
    else:
        part_no = "2000"  # Default test part number

    print(f"Testing scraper with part number: {part_no}")

    # Set up signal handler for graceful termination
    def signal_handler(sig, frame):
        print("Stopping scrapers gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

    # Run the scraper and print results as they come in
    total_start = time.time()
    results_count = 0
    
    for result in runScraper(part_no):
        elapsed = time.time() - total_start
        print(f"[{elapsed:.2f}s] {result}")
        results_count += 1
    
    total_time = time.time() - total_start
    print(f"Scraped {results_count} sources in {total_time:.2f} seconds")