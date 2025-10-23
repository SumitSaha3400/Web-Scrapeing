# import time
# import logging
# import pandas as pd
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.action_chains import ActionChains
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# # -----------------------------------------------------------------------------
# # Configuration
# # -----------------------------------------------------------------------------
# BASE_URL = "https://salehgroup.com/category/listings/"
# OUTPUT_CSV = "salehgroup_businesses.csv"

# # -----------------------------------------------------------------------------
# # Logging Setup
# # -----------------------------------------------------------------------------
# logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# # -----------------------------------------------------------------------------
# # WebDriver Setup
# # -----------------------------------------------------------------------------
# options = webdriver.ChromeOptions()
# options.add_argument("--headless")  # Remove this for visual debugging
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
# wait = WebDriverWait(driver, 15)
# actions = ActionChains(driver)

# # -----------------------------------------------------------------------------
# # Extraction Logic
# # -----------------------------------------------------------------------------
# def extract_listing_data(soup: BeautifulSoup) -> dict:
#     def extract_field(label: str) -> str:
#         # First try: find a <li> tag directly containing the label
#         tag = soup.find("li", string=lambda s: s and label in s)
#         if tag:
#             return tag.get_text(strip=True).replace(label, "").strip()

#         # Fallback: find <strong> label and get its sibling
#         strong = soup.find("strong", string=lambda s: s and label in s)
#         if strong and strong.next_sibling:
#             return str(strong.next_sibling).strip()
#         elif strong:
#             # Fallback to text from parent <li> or similar
#             return strong.parent.get_text(strip=True).replace(strong.get_text(strip=True), "").strip()
#         else:
#             return ""

#     title = soup.find("h1", class_="entry-title")
#     return {
#         "SG Number": extract_field("SG Number:"),
#         "Business Type": extract_field("Business Type:"),
#         "Listing Name": title.get_text(strip=True) if title else "",
#         "Listing Price": extract_field("Listing Price:"),
#         "Down Payment": extract_field("Down Payment:"),
#         "Financing": extract_field("Proposed Seller Financing Availability:"),
#         "Inventory Value": extract_field("Inventory Value:"),
#         "Annual Gross Sales": extract_field("Annual Gross Sales:"),
#         "Annual Owner Profits": extract_field("Annual Owner Profits:"),
#         "Monthly Rent": extract_field("Monthly Rent Payment:"),
#         "Employees/Management": extract_field("# of Employees/Management:"),
#         "Hours of Operation": extract_field("Hours of Operation:"),
#         "State": extract_field("State:"),
#         "Country": extract_field("Country:")
#     }

# # -----------------------------------------------------------------------------
# # Scraping Logic
# # -----------------------------------------------------------------------------
# def scrape_salehgroup_listings():
#     all_listings = []
#     driver.get(BASE_URL)

#     while True:
#         logging.info("🔄 Processing a listings page...")
#         link_selector = "h1.entry-title > a"
#         wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, link_selector)))
#         listing_count = len(driver.find_elements(By.CSS_SELECTOR, link_selector))
#         logging.info(f"📝 Found {listing_count} listings.")

#         for i in range(listing_count):
#             current_links = driver.find_elements(By.CSS_SELECTOR, link_selector)
#             if i >= len(current_links):
#                 logging.warning("⚠️ DOM changed, skipping rest of listings.")
#                 break
#             link = current_links[i]

#             try:
#                 actions.move_to_element(link).pause(0.3).click(link).perform()
#                 wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.entry-title")))
#                 soup = BeautifulSoup(driver.page_source, "html.parser")
#                 data = extract_listing_data(soup)
#                 all_listings.append(data)
#                 logging.info(f"✅ Scraped: {data.get('Listing Name', 'Unknown')}")
#             except Exception as e:
#                 logging.error(f"❌ Error scraping listing: {str(e)}")

#             # Return to listings
#             driver.back()
#             wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, link_selector)))
#             time.sleep(1)

#         # Handle pagination
#         try:
#             prev = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Previous posts")))
#             actions.move_to_element(prev).pause(0.3).click(prev).perform()
#             logging.info("➡️ Clicked 'Previous posts'")
#             time.sleep(2)
#         except Exception:
#             logging.info("❌ No more 'Previous posts'. Scraping complete.")
#             break

#     return all_listings

# # -----------------------------------------------------------------------------
# # Run
# # -----------------------------------------------------------------------------
# if __name__ == "__main__":
#     try:
#         results = scrape_salehgroup_listings()
#         df = pd.DataFrame(results)
#         df.to_csv(OUTPUT_CSV, index=False)
#         logging.info(f"🎉 Finished! {len(df)} listings saved to {OUTPUT_CSV}")
#     finally:
#         driver.quit()



import time
import logging
import pandas as pd
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Any

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -----------------------------------------------------------------------------
# Helper Function: Extract data from the listing detail page
# -----------------------------------------------------------------------------
def extract_listing_data(soup: BeautifulSoup) -> Dict[str, str]:
    def extract_field(label: str) -> str:
        tag = soup.find("li", string=lambda s: s and label in s)
        if tag:
            return tag.get_text(strip=True).replace(label, "").strip()
        strong = soup.find("strong", string=lambda s: s and label in s)
        if strong and strong.next_sibling:
            return str(strong.next_sibling).strip()
        elif strong:
            return strong.parent.get_text(strip=True).replace(strong.get_text(strip=True), "").strip()
        return ""

    title = soup.find("h1", class_="entry-title")
    return {
        "Listing Name": title.get_text(strip=True) if title else "",
        "SG Number": extract_field("SG Number:"),
        "Business Type": extract_field("Business Type:"),
        "Listing Price": extract_field("Listing Price:"),
        "Down Payment": extract_field("Down Payment:"),
        "Financing": extract_field("Proposed Seller Financing Availability:"),
        "Inventory Value": extract_field("Inventory Value:"),
        "Annual Gross Sales": extract_field("Annual Gross Sales:"),
        "Annual Owner Profits": extract_field("Annual Owner Profits:"),
        "Monthly Rent": extract_field("Monthly Rent Payment:"),
        "Employees/Management": extract_field("# of Employees/Management:"),
        "Hours of Operation": extract_field("Hours of Operation:"),
        "State": extract_field("State:"),
        "Country": extract_field("Country:")
    }

# -----------------------------------------------------------------------------
# Helper Function: Use Selenium to extract all listings from all paginated pages
# -----------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    listing_url = config["listing_url"]
    driver_options = webdriver.ChromeOptions()
    driver_options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=driver_options)
    wait = WebDriverWait(driver, 15)
    actions = ActionChains(driver)

    all_data = []
    try:
        driver.get(listing_url)
        while True:
            link_selector = "h1.entry-title > a"
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, link_selector)))
            listing_count = len(driver.find_elements(By.CSS_SELECTOR, link_selector))
            logging.info("Found %d listings on current page.", listing_count)

            for i in range(listing_count):
                current_links = driver.find_elements(By.CSS_SELECTOR, link_selector)
                if i >= len(current_links):
                    break
                link = current_links[i]

                try:
                    actions.move_to_element(link).pause(0.3).click(link).perform()
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.entry-title")))
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    data = extract_listing_data(soup)
                    data["Link"] = driver.current_url
                    all_data.append(data)
                    logging.info("Scraped: %s", data["Listing Name"])
                except Exception as e:
                    logging.warning("Error scraping listing: %s", e)

                driver.back()
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, link_selector)))
                time.sleep(1)

            # Move to previous page
            try:
                prev = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Previous posts")))
                actions.move_to_element(prev).pause(0.3).click(prev).perform()
                logging.info("Navigated to previous page.")
                time.sleep(2)
            except Exception:
                logging.info("No more 'Previous posts'.")
                break

    finally:
        driver.quit()
    return all_data

# -----------------------------------------------------------------------------
# Core Scraper Function
# -----------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    required_keys = ["listing_url", "broker", "phase", "contact_name", "contact_number"]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    listings = get_list_links(config)
    records = []

    for data in listings:
        title = data.get("Listing Name", "").lower()
        status = "Sold" if "sold" in title else "Available"

        records.append({
            "Broker Name": config["broker"],
            "Extraction Phase": config["phase"],
            "Link to Deal": data.get("Link", ""),
            "Listing ID": data.get("SG Number", ""),
            "Published Date": "",  # Not available
            "Opportunity/Listing Name": data.get("Listing Name", ""),
            "Opportunity/Listing Description": "",  # No description field
            "City": "check",
            "State/Province": data.get("State", ""),
            "Country": data.get("Country", "United States"),
            "Business Type": data.get("Business Type", ""),
            "Asking Price": data.get("Listing Price", ""),
            "Revenue/Sales": data.get("Annual Gross Sales", ""),
            "Down Payment": data.get("Down Payment", ""),
            "EBITDA/Cash Flow/Net Income": data.get("Annual Owner Profits", ""),
            "Status": status,
            "Contact Name": config["contact_name"],
            "Contact Number": config["contact_number"],
            "Manual Validation": True
        })

    return pd.DataFrame(records)

# -----------------------------------------------------------------------------
# Example usage
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    config: Dict[str, Any] = {
        "listing_url": "https://salehgroup.com/category/listings/",
        "broker": "The Saleh Group",
        "phase": "initial",
        "contact_name": "Nidal Saleh",
        "contact_number": "N/A",
    }

    df = scrape(config)
    df.to_csv("salehgroup_businesses.csv", index=False)
    print(df.head())
