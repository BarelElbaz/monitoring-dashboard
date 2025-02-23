import time
import json
import logging
import traceback
import base64
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
    NoSuchFrameException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def load_config(config_file='config.json'):
    # First try to load from the same directory as the executable
    import sys
    if getattr(sys, 'frozen', False):
        # Running as a bundled app
        if sys.platform == 'darwin':
            # On macOS, look in the parent directory of the .app bundle
            app_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))))
            config_path = os.path.join(app_path, config_file)
        else:
            # On other platforms, look next to the executable
            app_path = os.path.dirname(sys.executable)
            config_path = os.path.join(app_path, config_file)
    else:
        # Running in development
        config_path = config_file

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        # Expand the user_data_dir if it contains '~'
        if 'user_data_dir' in config:
            config['user_data_dir'] = os.path.expanduser(config['user_data_dir'])
        return config
    except Exception as e:
        logging.error(f"Failed to load config from {config_path}: {str(e)}")
        raise

def configure_logging(log_level, log_file):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def init_driver(config):
    browser = config.get('browser', 'chrome').lower()
    driver = None

    if browser == 'chrome':
        options = ChromeOptions()
        options.add_argument("--start-fullscreen")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-component-update")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        # Remove --incognito to allow session data
        # options.add_argument("--incognito")

        # Add experimental options to hide the automation message
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)

        # Add options to prevent background tab throttling
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")

        # Specify the user data directory and profile
        user_data_dir = config.get('user_data_dir')
        profile_directory = config.get('profile_directory')

        if user_data_dir:
            options.add_argument(f"--user-data-dir={user_data_dir}")
        else:
            logging.error("User data directory is not specified in the configuration.")
            raise ValueError("User data directory is required when using a custom profile.")

        if profile_directory:
            options.add_argument(f"--profile-directory={profile_directory}")
        else:
            logging.error("Profile directory is not specified in the configuration.")
            raise ValueError("Profile directory is required when using a custom profile.")

        chromedriver_path = config.get('chromedriver_path', '')
        if chromedriver_path:
            driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)
        else:
            driver = webdriver.Chrome(options=options)
    elif browser == 'firefox':
        options = FirefoxOptions()
        options.add_argument("--kiosk")
        driver = webdriver.Firefox(options=options)
    else:
        logging.error(f"Unsupported browser specified: {browser}")
        raise ValueError(f"Unsupported browser specified: {browser}")
    driver.set_page_load_timeout(config.get('page_load_timeout', 60))
    return driver

def scroll_page(driver, config, scrollable_element_selector=None):
    """
    Scrolls the page (or a scrollable container if selector is provided) while
    handling potential 'StaleElementReferenceException'.
    """
    try:
        scroll_pause_at_top = config.get('scroll_pause_at_top', 2)
        scroll_pause_at_bottom = config.get('scroll_pause_at_bottom', 5)
        scroll_step_duration = config.get('scroll_step_duration', 0.01)

        logging.debug(f"Pausing at the top of the page for {scroll_pause_at_top} seconds.")
        time.sleep(scroll_pause_at_top)

        # Locate scrollable element if a selector is provided
        scrollable_element = None
        if scrollable_element_selector:
            try:
                scrollable_element = driver.find_element(By.CSS_SELECTOR, scrollable_element_selector)
            except NoSuchElementException:
                logging.error(f"Could not find the scrollable container using selector: {scrollable_element_selector}")

        # Determine the total scrollable height
        if scrollable_element:
            total_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_element)
            client_height = driver.execute_script("return arguments[0].clientHeight", scrollable_element)
        else:
            total_height = driver.execute_script("return document.body.scrollHeight") or 1000
            client_height = driver.execute_script("return window.innerHeight") or 800

        max_scroll_distance = total_height - client_height
        is_scrollable = max_scroll_distance > 0 # Check if the page is scrollable
        display_time = calculate_display_time(total_height, config, is_scrollable)

        if not is_scrollable:
            logging.info(f"Page is not scrollable. Skipping scrolling. Pausing for {display_time} seconds.")
            time.sleep(display_time)
            return  # Exit the function since there's nothing to scroll

        steps = max(int(display_time / scroll_step_duration), 1)
        scroll_increment = max_scroll_distance / steps

        logging.info(f"Total height: {total_height}px")
        logging.info(f"Client height: {client_height}px")
        logging.info(f"Max scroll distance: {max_scroll_distance}px")
        logging.info(f"Display time: {display_time:.2f}s")
        logging.info(f"Number of steps: {steps}")
        logging.info(f"Scroll increment: {scroll_increment:.2f}px per step")

        current_position = 0
        for _ in range(steps):
            try:
                # Re-locate if we have a selector
                if scrollable_element_selector:
                    scrollable_element = driver.find_element(By.CSS_SELECTOR, scrollable_element_selector)
                    driver.execute_script("arguments[0].scrollTop = arguments[1];",
                                          scrollable_element, current_position)
                else:
                    driver.execute_script(f"window.scrollTo(0, {current_position});")

                current_position += scroll_increment
                time.sleep(scroll_step_duration)

            except StaleElementReferenceException:
                logging.warning("Encountered StaleElementReferenceException while scrolling. Re-locating element.")
                # Re-locate or simply break depending on your needs
                if scrollable_element_selector:
                    try:
                        scrollable_element = driver.find_element(By.CSS_SELECTOR, scrollable_element_selector)
                        # Optionally retry the same scroll step
                        driver.execute_script("arguments[0].scrollTop = arguments[1];",
                                              scrollable_element, current_position)
                    except NoSuchElementException:
                        logging.error("Scroll element disappeared entirely. Stopping scroll.")
                        break
                else:
                    # If there's no specific container, just continue with window scroll
                    driver.execute_script(f"window.scrollTo(0, {current_position});")

            except NoSuchElementException:
                logging.error("Scroll element no longer exists. Stopping scroll.")
                break

        # Ensure we reach the bottom
        try:
            if scrollable_element_selector:
                scrollable_element = driver.find_element(By.CSS_SELECTOR, scrollable_element_selector)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable_element)
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception as e:
            logging.error(f"Error ensuring we reach bottom: {e}")

        logging.debug(f"Pausing at the bottom of the page for {scroll_pause_at_bottom} seconds.")
        time.sleep(scroll_pause_at_bottom)

    except Exception as e:
        logging.error(f"Error in scroll_page: {e}")
        logging.debug(traceback.format_exc())
        raise

def calculate_display_time(total_height, config, is_scrollable=True):
    min_display_time = config.get('min_display_time', 30)
    max_display_time = config.get('max_display_time', 120)
    scaling_factor = config.get('scaling_factor', 0.02)

    if not is_scrollable:
        return min_display_time

    display_time = total_height * scaling_factor
    display_time = max(min_display_time, min(display_time, max_display_time))
    logging.debug(f"Calculated display time: {display_time:.2f} seconds for page height: {total_height}px.")
    return display_time

def refresh_session_if_needed(driver, last_refresh_time, config, current_url):
    refresh_interval = config.get('refresh_interval', 3600)
    current_time = time.time()
    if current_time - last_refresh_time > refresh_interval:
        logging.info(f"Refreshing the browser session to prevent timeout. [{current_url}]")
        success = load_url(driver, current_url, config)
        if not success:
            logging.error(f"Failed to reload URL: {current_url}")
        return current_time
    return last_refresh_time

def wait_for_page_load(driver, timeout, check_element_xpath=None):
    try:
        # Wait until document is completely loaded
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        logging.debug("Initial page load complete (document.readyState == 'complete').")

        if check_element_xpath:
            # If a specific element is provided, wait for that element to be visible
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, check_element_xpath))
            )
            logging.debug(f"Element located and visible: {check_element_xpath}")

        logging.info("Page fully loaded and ready.")
    except TimeoutException:
        logging.warning(f"Page load timed out after {timeout} seconds but continuing.")
    except Exception as e:
        logging.error(f"Error while waiting for page load: {e}")
        logging.debug(traceback.format_exc())

# ------------------ CDP Functions ------------------
def set_nagios_basic_auth(driver, nagios_username, nagios_password):
    logging.debug("Setting HTTP Basic Authentication headers for Nagios via CDP.")
    try:
        # Enable the Network domain
        driver.execute_cdp_cmd("Network.enable", {})
        
        # Encode credentials
        credentials = f"{nagios_username}:{nagios_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        # Set the Authorization header
        driver.execute_cdp_cmd(
            "Network.setExtraHTTPHeaders",
            {"headers": {"Authorization": f"Basic {encoded_credentials}"}}
        )
        logging.info("HTTP Basic Authentication headers set via CDP.")
    except Exception as e:
        logging.error(f"Failed to set HTTP Basic Authentication headers for Nagios: {e}")
        driver.save_screenshot("error_cdp_auth_nagios.png")
        logging.debug(traceback.format_exc())

def reset_extra_http_headers(driver):
    logging.debug("Resetting HTTP Extra Headers via CDP.")
    try:
        driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": {}})
        logging.info("HTTP Extra Headers have been reset.")
    except Exception as e:
        logging.error(f"Failed to reset HTTP Extra Headers: {e}")
        logging.debug(traceback.format_exc())


# ------------------ Pre-Action Functions ------------------

def pre_action_nagios(driver):
    """
    Navigate to 'AVANAN Alerts' and click on 'Critical'.
    Assumes that HTTP Basic Authentication is already handled via CDP.
    """
    try:
        driver.switch_to.frame("side")
    except NoSuchFrameException:
        logging.error("Could not switch to the left frame. It might not exist.")
        driver.save_screenshot("error_switch_to_left_frame.png")

    # Proceed to click "AVANAN Alerts" sidebar link
    try:
        logging.debug("Attempting to locate the 'AVANAN Alerts' sidebar link.")
        avan_alerts_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//a[contains(@href, '/nagios/cgi-bin/status.cgi') and .//b[contains(text(), 'AVANAN Alerts')]]"
            ))
        )
        avan_alerts_link.click()
        logging.info("Clicked 'AVANAN Alerts' sidebar link.")
        
        # Switch back to default content
        driver.switch_to.default_content()
        
        # Switch to the main frame where the content is loaded
        driver.switch_to.frame("main")
        
        # Wait for the page to load after clicking
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//th[contains(@class, 'serviceTotals')]"
            ))
        )
    except TimeoutException:
        logging.error("Could not find the 'AVANAN Alerts' sidebar link.")
        driver.save_screenshot("error_avan_alerts_link.png")
        logging.debug(traceback.format_exc())
    except (ElementClickInterceptedException, ElementNotInteractableException) as e:
        logging.error(f"Could not click the 'AVANAN Alerts' sidebar link: {e}")
        driver.save_screenshot("error_avan_alerts_click.png")
        logging.debug(traceback.format_exc())
    except Exception as e:
        logging.error(f"Unexpected error while clicking 'AVANAN Alerts' sidebar link: {e}")
        driver.save_screenshot("error_avan_alerts_unexpected.png")
        logging.debug(traceback.format_exc())

    # Proceed to click "Critical" link in service totals
    try:
        logging.debug("Attempting to locate the 'Critical' link in service totals.")
        critical_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//th[contains(@class, 'serviceTotals')]//a[contains(text(), 'Critical')]"
            ))
        )
        critical_link.click()
        logging.info("Clicked 'Critical' link in service totals.")
        time.sleep(1)
    except TimeoutException:
        logging.error("Could not find the 'Critical' link in service totals.")
        driver.save_screenshot("error_critical_link.png")
        logging.debug(traceback.format_exc())
    except (ElementClickInterceptedException, ElementNotInteractableException) as e:
        logging.error(f"Could not click the 'Critical' link: {e}")
        driver.save_screenshot("error_critical_click.png")
        logging.debug(traceback.format_exc())
    except Exception as e:
        logging.error(f"Unexpected error while clicking 'Critical' link: {e}")
        driver.save_screenshot("error_critical_unexpected.png")
        logging.debug(traceback.format_exc())

    wait_for_page_load(driver, timeout=60, check_element_xpath="//table[@class='status']/tbody")


def pre_action_example(driver):
    """
    Placeholder for additional website-specific pre-actions.
    """
    # Implement other pre-actions as needed
    pass

# ------------------ Pre-Actions Mapping ------------------

PRE_ACTIONS = {
    'nagios': pre_action_nagios,
    # Add more mappings as needed, e.g.,
    # 'another_site_identifier': pre_action_another_site,
}

def load_url(driver, url, config):
    reset_extra_http_headers(driver)

    if "nagios" in url.lower():
        # Retrieve Nagios credentials from config
        nagios_credentials = config.get('nagios_credentials', {})
        nagios_username = nagios_credentials.get('username', '')
        nagios_password = nagios_credentials.get('password', '')
        if nagios_username and nagios_password:
            set_nagios_basic_auth(driver, nagios_username, nagios_password)
        else:
            logging.error("Nagios username and password are required for HTTP Basic Authentication.")
            return False  # Indicate failure to load URL
    driver.get(url)
    wait_for_page_load(driver, config.get('page_load_timeout', 60))
    time.sleep(5)  # Additional wait time for dynamic content
    return True  # Indicate success

def execute_pre_actions(driver, url, config):
    if config.get('run_pre_actions', False):
        executed_pre_action = False
        for site_identifier, pre_action in PRE_ACTIONS.items():
            if site_identifier in url.lower():
                logging.debug(f"Executing pre-action for site: {site_identifier}")
                pre_action(driver)
                executed_pre_action = True
                break  # Assuming one pre-action per URL
        if not executed_pre_action:
            logging.debug("No pre-action defined for this URL.")


def handle_scrolling(driver, url, config):
    scrollable_element_selector = None

    if "grafana" in url.lower():
        # For Grafana dashboards, find the scrollable container
        try:
            scrollable_element_selector = 'div.scrollbar-view'
            logging.debug("Found Grafana scrollable container.")
        except NoSuchElementException:
            logging.error("Could not find the Grafana scrollable container. Using default scrolling.")

    # Scroll the page
    scroll_page(driver, config, scrollable_element_selector)

# ------------------ Tab Management Functions ------------------

def refresh_tab(driver, url, config):
    """Attempt to refresh a tab with fallback mechanisms."""
    try:
        logging.info(f"Attempting to refresh tab for URL: {url}")
        driver.refresh()
        wait_for_page_load(driver, config.get('page_load_timeout', 60))
        return True
    except Exception as e:
        logging.error(f"Failed to refresh tab for {url}: {e}")
        try:
            # Fallback: Try full page reload
            return load_url(driver, url, config)
        except Exception as reload_error:
            logging.error(f"Failed to reload URL {url}: {reload_error}")
            return False

def recreate_tab(driver, url, config):
    """Create a new tab for the given URL and close the old one."""
    try:
        current_handle = driver.current_window_handle
        # Open new tab
        driver.execute_script("window.open('')")
        driver.switch_to.window(driver.window_handles[-1])
        
        # Load URL in new tab
        success = load_url(driver, url, config)
        if success:
            # Close old tab
            driver.switch_to.window(current_handle)
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
            return driver.current_window_handle
        else:
            # If failed, close new tab and return to original
            driver.close()
            driver.switch_to.window(current_handle)
            return None
    except Exception as e:
        logging.error(f"Failed to recreate tab for {url}: {e}")
        return None

def check_tab_health(driver, url, config, last_refresh_time):
    """Check tab health and refresh/recreate if needed."""
    current_time = time.time()
    tab_lifetime = current_time - last_refresh_time
    max_tab_lifetime = config.get('max_tab_lifetime', 3600)
    tab_refresh_interval = config.get('tab_refresh_interval', 1800)
    
    # Check if tab needs periodic refresh
    if tab_lifetime > tab_refresh_interval:
        logging.info(f"Tab refresh interval reached for {url}")
        if refresh_tab(driver, url, config):
            return current_time
    
    # Check if tab exceeded lifetime
    if tab_lifetime > max_tab_lifetime:
        logging.warning(f"Tab lifetime exceeded for {url}, attempting recreation")
        new_handle = recreate_tab(driver, url, config)
        if new_handle:
            return current_time
    
    return last_refresh_time

# ------------------ Main Function ------------------
def main():
    config = load_config()
    urls = config.get('urls', [])
    if not urls:
        logging.error("No URLs provided in the configuration.")
        return

    configure_logging(config.get('log_level', 'INFO'), config.get('log_file', 'dashboard_rotator.log'))
    logging.info("Starting the dashboard rotator script.")

    while True:  # Outer loop for browser session management
        try:
            session_start_time = time.time()
            max_browser_lifetime = config.get('max_browser_lifetime', 43200)  # 12 hours default
            driver = init_driver(config)
            
            mode = config.get('mode', 'SingleTab').lower()
            if mode == 'multitab':
                # Multi-tab mode: open each URL in a separate tab
                tabs = {}
                last_refresh_times = {}

                # Open each URL in a separate tab
                for idx, url in enumerate(urls):
                    try:
                        if idx == 0:
                            logging.info(f"Loading URL in initial tab: {url}")
                            success = load_url(driver, url, config)
                        else:
                            logging.info(f"Opening new tab for URL: {url}")
                            driver.execute_script("window.open('');")
                            driver.switch_to.window(driver.window_handles[-1])
                            success = load_url(driver, url, config)

                        if success:
                            tabs[url] = driver.current_window_handle
                            last_refresh_times[url] = time.time()
                        else:
                            logging.error(f"Failed to load URL: {url}")
                            if idx > 0:
                                driver.close()  # Close the failed tab
                                driver.switch_to.window(driver.window_handles[0])
                    except Exception as e:
                        logging.error(f"Error initializing tab for {url}: {e}")
                        if idx > 0:
                            try:
                                driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                            except:
                                pass

                # Main loop to rotate between tabs
                while True:
                    current_time = time.time()
                    
                    # Check if browser session needs reset
                    if current_time - session_start_time > max_browser_lifetime:
                        logging.info("Browser session lifetime exceeded, initiating reset")
                        raise Exception("Browser session lifetime exceeded")

                    for url in urls:
                        if url not in tabs:
                            continue

                        try:
                            logging.info(f"Processing URL: {url}")
                            driver.switch_to.window(tabs[url])

                            # Check tab health and refresh if needed
                            new_refresh_time = check_tab_health(driver, url, config, last_refresh_times[url])
                            if new_refresh_time != last_refresh_times[url]:
                                last_refresh_times[url] = new_refresh_time
                                # Skip other operations if tab was just refreshed
                                continue

                            # Perform pre-actions and handle scrolling
                            execute_pre_actions(driver, url, config)
                            handle_scrolling(driver, url, config)

                        except Exception as e:
                            logging.error(f"Error processing {url}: {e}")
                            try:
                                # Attempt to recreate the problematic tab
                                new_handle = recreate_tab(driver, url, config)
                                if new_handle:
                                    tabs[url] = new_handle
                                    last_refresh_times[url] = time.time()
                            except Exception as tab_error:
                                logging.error(f"Failed to recover tab for {url}: {tab_error}")
                                if url in tabs:
                                    del tabs[url]

            else:
                # Single-tab mode implementation remains unchanged
                while True:
                    current_time = time.time()
                    if current_time - session_start_time > max_browser_lifetime:
                        logging.info("Browser session lifetime exceeded, initiating reset")
                        raise Exception("Browser session lifetime exceeded")

                    for url in urls:
                        logging.info(f"Loading URL: {url}")
                        success = load_url(driver, url, config)
                        if success:
                            execute_pre_actions(driver, url, config)
                            handle_scrolling(driver, url, config)

        except Exception as e:
            logging.error(f"Browser session error: {e}")
            logging.debug(traceback.format_exc())
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as quit_error:
                    logging.error(f"Error closing browser: {quit_error}")
            
            logging.info("Waiting before starting new browser session...")
            time.sleep(5)  # Wait before starting new session


if __name__ == "__main__":
    main()