# import time
# import csv
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.action_chains import ActionChains
# from selenium.webdriver.chrome.options import Options
# from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException

# # -----------------------------------------------------------------------------
# # Setup ChromeDriver
# # -----------------------------------------------------------------------------
# options = Options()
# options.add_argument("--start-maximized")
# # options.add_argument("--headless")
# driver = webdriver.Chrome(options=options)
# driver.get("https://www.firststreetbusinessbrokers.com/opportunities/larger-companies-for-sale/")
# time.sleep(3)

# # -----------------------------------------------------------------------------
# # Extract 'Detailed Information' section
# # -----------------------------------------------------------------------------
# def extract_detail_info():
#     fields = {
#         "Business Price": "",
#         "Revenues": "",
#         "Sellers Discretionary Income": "",
#         "Furniture, Fixtures & Equipment": "",
#         "Inventory": ""
#     }

#     try:
#         container = driver.find_element(By.CSS_SELECTOR, ".job_description")
#         paragraphs = container.find_elements(By.TAG_NAME, "p")
#         for p in paragraphs:
#             text = p.text.strip()
#             for key in fields:
#                 if text.startswith(f"{key}:"):
#                     fields[key] = text.split(":", 1)[1].strip()
#     except Exception as e:
#         print("[WARN] Could not extract detailed info:", e)

#     return fields

# # -----------------------------------------------------------------------------
# # Process all listings on current page
# # -----------------------------------------------------------------------------
# all_data = []

# def process_current_page():
#     time.sleep(2)
#     listings = driver.find_elements(By.CSS_SELECTOR, ".job_listings .job_listing")
#     total = len(listings)

#     for i in range(total):
#         try:
#             listings = driver.find_elements(By.CSS_SELECTOR, ".job_listings .job_listing")
#             if i >= len(listings):  # sanity check
#                 print(f"[WARN] Skipping index {i} — listings not fully reloaded")
#                 continue

#             item = listings[i]

#             try:
#                 title = item.find_element(By.CSS_SELECTOR, ".position h3").text.strip()
#             except:
#                 title = "No Title"
#             try:
#                 location = item.find_element(By.CSS_SELECTOR, ".job-location").text.strip()
#             except:
#                 location = ""

#             print(f"[INFO] Clicking: {title} — {location}")
#             ActionChains(driver).move_to_element(item).click().perform()
#             time.sleep(3)

#             # Extract info
#             detail_data = extract_detail_info()
#             detail_data["Title"] = title
#             detail_data["Location"] = location
#             all_data.append(detail_data)

#         except Exception as e:
#             print(f"[ERROR] Could not process listing #{i}: {e}")

#         # Return to listings page
#         driver.back()
#         time.sleep(3)

#         # Wait for listings to reappear before continuing
#         try:
#             driver.find_element(By.CSS_SELECTOR, ".job_listings .job_listing")
#         except:
#             print("[WARN] Listings not found after back. Waiting extra.")
#             time.sleep(3)

# # -----------------------------------------------------------------------------
# # Paginate using the "→" button
# # -----------------------------------------------------------------------------
# def go_through_all_pages():
#     page = 1
#     while True:
#         print(f"[INFO] Scraping Page {page}")
#         process_current_page()

#         try:
#             next_button = driver.find_element(By.XPATH, "//a[contains(text(),'→')]")
#             driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
#             time.sleep(1)

#             if not next_button.is_displayed():
#                 print("[INFO] → button not visible. Stopping.")
#                 break

#             next_button.click()
#             page += 1
#             time.sleep(3)

#         except NoSuchElementException:
#             print("[INFO] No more pages.")
#             break
#         except ElementNotInteractableException:
#             print("[INFO] → button not interactable. Possibly last page.")
#             break

# # -----------------------------------------------------------------------------
# # Run and Save
# # -----------------------------------------------------------------------------
# go_through_all_pages()
# driver.quit()

# output_file = "first_street_business_listings.csv"
# keys = ["Title", "Location", "Business Price", "Revenues",
#         "Sellers Discretionary Income", "Furniture, Fixtures & Equipment", "Inventory"]

# with open(output_file, "w", newline="", encoding="utf-8") as f:
#     writer = csv.DictWriter(f, fieldnames=keys)
#     writer.writeheader()
#     writer.writerows(all_data)

# print(f"[✅ DONE] Extracted {len(all_data)} listings and saved to '{output_file}'")



import pandas as pd
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Helper Function: Extract 'Detailed Information' section
# ---------------------------------------------------------------------------
def extract_detail_info(driver):
    """Extract detailed information from current page - EXACT copy from code 1"""
    fields = {
        "Business Price": "",
        "Revenues": "",
        "Sellers Discretionary Income": "",
        "Furniture, Fixtures & Equipment": "",
        "Inventory": ""
    }

    try:
        container = driver.find_element(By.CSS_SELECTOR, ".job_description")
        paragraphs = container.find_elements(By.TAG_NAME, "p")
        for p in paragraphs:
            text = p.text.strip()
            for key in fields:
                if text.startswith(f"{key}:"):
                    fields[key] = text.split(":", 1)[1].strip()
    except Exception as e:
        print("[WARN] Could not extract detailed info:", e)

    return fields


# ---------------------------------------------------------------------------
# Helper Function: Process all listings on current page - EXACT copy from code 1
# ---------------------------------------------------------------------------
def process_current_page(driver, all_data):
    """Process current page listings - EXACT copy from code 1"""
    time.sleep(2)
    listings = driver.find_elements(By.CSS_SELECTOR, ".job_listings .job_listing")
    total = len(listings)

    for i in range(total):
        try:
            listings = driver.find_elements(By.CSS_SELECTOR, ".job_listings .job_listing")
            if i >= len(listings):  # sanity check
                print(f"[WARN] Skipping index {i} — listings not fully reloaded")
                continue

            item = listings[i]

            try:
                title = item.find_element(By.CSS_SELECTOR, ".position h3").text.strip()
            except:
                title = "No Title"
            try:
                location = item.find_element(By.CSS_SELECTOR, ".job-location").text.strip()
            except:
                location = ""

            print(f"[INFO] Clicking: {title} — {location}")
            ActionChains(driver).move_to_element(item).click().perform()
            time.sleep(3)

            # Extract info
            detail_data = extract_detail_info(driver)
            detail_data["Title"] = title
            detail_data["Location"] = location
            all_data.append(detail_data)

        except Exception as e:
            print(f"[ERROR] Could not process listing #{i}: {e}")

        # Return to listings page
        driver.back()
        time.sleep(3)

        # Wait for listings to reappear before continuing
        try:
            driver.find_element(By.CSS_SELECTOR, ".job_listings .job_listing")
        except:
            print("[WARN] Listings not found after back. Waiting extra.")
            time.sleep(3)


# ---------------------------------------------------------------------------
# Helper Function: Paginate using the "→" button - EXACT copy from code 1
# ---------------------------------------------------------------------------
def go_through_all_pages(driver, all_data):
    """Navigate through all pages - EXACT copy from code 1"""
    page = 1
    while True:
        print(f"[INFO] Scraping Page {page}")
        process_current_page(driver, all_data)

        try:
            next_button = driver.find_element(By.XPATH, "//a[contains(text(),'→')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(1)

            if not next_button.is_displayed():
                print("[INFO] → button not visible. Stopping.")
                break

            next_button.click()
            page += 1
            time.sleep(3)

        except NoSuchElementException:
            print("[INFO] No more pages.")
            break
        except ElementNotInteractableException:
            print("[INFO] → button not interactable. Possibly last page.")
            break


# ---------------------------------------------------------------------------
# Helper Function: Extract Listings from the Directory Page
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Fetch the directory page and extract all listing links and basic details.
    This function wraps your original code 1 logic.

    Returns:
        A list of dictionaries, each representing a listing.
    """
    listing_url = config["listing_url"]
    headers = config.get("headers", {})
    history_df = config.get("history", pd.DataFrame())

    # Existing listing URLs (to avoid duplicates)
    existing_urls = set(history_df.get("Link to Deal", []))
    
    # Setup ChromeDriver - EXACT copy from code 1
    options = Options()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    
    all_data = []  # This will store the raw data from code 1
    
    try:
        driver.get(listing_url)
        time.sleep(3)

        # Run your exact code 1 logic
        go_through_all_pages(driver, all_data)
        
    finally:
        driver.quit()

    print(f"[✅ DONE] Extracted {len(all_data)} listings")

    # Convert code 1 format to code 2 format
    posts = []
    for data in all_data:
        posts.append({
            "listing_id": "N/A",
            "href": "N/A",  # Individual URLs not captured in original
            "title": data.get("Title", "N/A"),
            "price_box": data.get("Business Price", "N/A"),
            "pub_date": "",
            "description": "N/A",
            "location": data.get("Location", "N/A"),
            "business_type": "N/A",
            "revenue": data.get("Revenues", "N/A"),
            "ebitda": data.get("Sellers Discretionary Income", "N/A"),
            "contact_name": "N/A",
            "contact_number": "N/A",
            "furniture_fixtures": data.get("Furniture, Fixtures & Equipment", "N/A"),
            "inventory": data.get("Inventory", "N/A"),
        })

    logging.info("Extracted %d listings from page.", len(posts))
    return posts


# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Scrape listings from the provided configuration.

    Args:
        config (Dict[str, Any]): Configuration with required keys:
            listing_url, base_url, headers, history, broker,
            phase, contact_name, contact_number

    Returns:
        DataFrame: A pandas DataFrame containing scraped listings.
    """
    # Check if config has all required keys
    required_keys = [
        "listing_url",
        "base_url",
        "headers",
        "history",
        "broker",
        "phase",
        "contact_name",
        "contact_number",
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    # Fetch the listing posts using your exact code 1 logic
    posts = get_list_links(config)
    records = []

    sold_keywords = config.get("sold_keywords", ["sold", "under contract", "closed"])

    for pdata in posts:
        title_lower = pdata['title'].lower()
        status = "Sold" if any(keyword in title_lower for keyword in sold_keywords) else "Available"

        # Prepare the record for the DataFrame
        records.append({
            "Broker Name": config["broker"],
            "Extraction Phase": config["phase"],
            "Link to Deal": pdata["href"],
            "Listing ID": pdata["listing_id"],
            "Published Date": pdata["pub_date"],
            "Opportunity/Listing Name": pdata["title"],
            "Opportunity/Listing Description": pdata["description"],
            "City": "check",
            "State/Province": pdata["location"],
            "Country": "United States",
            "Business Type": pdata["business_type"],
            "Asking Price": pdata["price_box"],
            "Revenue/Sales": pdata["revenue"],
            "Down Payment": "check",
            "EBITDA/Cash Flow/Net Income": pdata["ebitda"],
            "Status": status,
            "Contact Name": pdata["contact_name"],
            "Contact Number": pdata["contact_number"],
            "Manual Validation": True,
            # Additional fields from your original extraction
            "Furniture, Fixtures & Equipment": pdata.get("furniture_fixtures", "N/A"),
            "Inventory": pdata.get("inventory", "N/A"),
        })

    # Return as a DataFrame
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Example usage: Run this script standalone to test scraping
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Default configuration
    default_config: Dict[str, Any] = {
        "listing_url": "https://www.firststreetbusinessbrokers.com/opportunities/larger-companies-for-sale/",
        "base_url": "https://www.firststreetbusinessbrokers.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        "history": pd.DataFrame(),
        "broker": "",          # Will be overridden
        "phase": "",           # Will be overridden
        "contact_name": "",    # Will be overridden
        "contact_number": "",  # Will be overridden
    }

    # User-provided overrides
    overrides = {
        "broker": "First Street Business Brokers",
        "phase": "initial",
        "contact_name": "First Street Team",
        "contact_number": "555-0000",
    }

    # Merge defaults and overrides
    config = {**default_config, **overrides}

    # Run the scraper and show results
    df = scrape(config)
    print(df.head())
    
    # Save to CSV (optional - same as your original code)
    output_file = "first_street_business_listings.csv"
    keys = ["Broker Name", "Extraction Phase", "Link to Deal", "Listing ID", "Published Date",
            "Opportunity/Listing Name", "Opportunity/Listing Description", "City", "State/Province", 
            "Country", "Business Type", "Asking Price", "Revenue/Sales", "Down Payment", 
            "EBITDA/Cash Flow/Net Income", "Status", "Contact Name", "Contact Number", "Manual Validation"]
    
    df[keys].to_csv(output_file, index=False)
    print(f"[✅ DONE] Extracted {len(df)} listings and saved to '{output_file}'")