import pandas as pd
import logging
from typing import Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
import time

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Helper Function: Extract Listings with Selenium
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    options = Options()
    # options.add_argument("--headless")  # Uncomment to run in headless mode
    driver = webdriver.Chrome(service=Service(), options=options)
    driver.get(config["listing_url"])
    wait = WebDriverWait(driver, 10)
    actions = ActionChains(driver)

    listings = []
    page = 1

    def extract_listings():
        cards = driver.find_elements(By.CSS_SELECTOR, "ul.listings > li")
        for card in cards:
            try: title = card.find_element(By.CSS_SELECTOR, "h4 a").text.strip()
            except: title = ""
            try: price = card.find_element(By.XPATH, ".//td[contains(text(),'PRICE:')]/following-sibling::td").text.strip()
            except: price = ""
            try: revenue = card.find_element(By.XPATH, ".//td[contains(text(),'REVENUE:')]/following-sibling::td").text.strip()
            except: revenue = ""
            try: profit = card.find_element(By.XPATH, ".//td[contains(text(),'PROFIT:')]/following-sibling::td").text.strip()
            except: profit = ""
            try: location = card.find_element(By.XPATH, ".//td[contains(text(),'LOCATION:')]/following-sibling::td").text.strip()
            except: location = ""
            try: listed_by = card.find_element(By.XPATH, ".//td[contains(text(),'LISTED BY:')]/following-sibling::td").text.strip()
            except: listed_by = ""

            listings.append({
                "listing_id": "",  # Not available
                "href": "",        # No individual deal links on this site
                "title": title,
                "price_box": price,
                "pub_date": "",
                "description": "",
                "location": location,
                "business_type": "",
                "revenue": revenue,
                "ebitda": profit,
                "contact_name": listed_by,
                "contact_number": "",
            })

    while True:
        logging.info(f"Extracting page {page}")
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "ul.listings > li")) > 0)
        first_title = driver.find_element(By.CSS_SELECTOR, "ul.listings h4 a").text.strip()
        extract_listings()

        try:
            # Detect and click the “Next” → pagination button
            next_button = None
            for a in driver.find_elements(By.CSS_SELECTOR, "div.pagination a"):
                if "→" in a.text and a.is_displayed():
                    next_button = a
                    break

            if not next_button:
                logging.info("No 'Next' button found. Pagination complete.")
                break

            actions.move_to_element(next_button).perform()
            next_button.click()
            WebDriverWait(driver, 10).until(
                lambda d: d.find_element(By.CSS_SELECTOR, "ul.listings h4 a").text.strip() != first_title
            )
            time.sleep(1)
            page += 1

        except Exception as e:
            logging.warning("Stopping pagination due to error or end: %s", e)
            break

    driver.quit()
    logging.info("Extracted %d listings across all pages.", len(listings))
    return listings


# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    posts = get_list_links(config)
    records = []

    sold_keywords = config.get("sold_keywords", ["sold", "under contract", "closed"])

    for pdata in posts:
        title_lower = pdata['title'].lower()
        status = "Sold" if any(k in title_lower for k in sold_keywords) else "Available"

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
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    default_config: Dict[str, Any] = {
        "listing_url": "https://scottmckenzie.dealrelations.com/listing_feeds/11",
        "base_url": "https://scottmckenzie.dealrelations.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        },
        "history": pd.DataFrame(),
        "broker": "National M&A Group",
        "phase": "initial",
        "contact_name": "N/A",
        "contact_number": "N/A",
        "sold_keywords": ["sold", "under contract", "closed"]
    }

    df = scrape(default_config)
    print(df.head())
    df.to_csv("National_Mergers_and_Acquisition_Group.csv", index=False)
    print("✅ Saved to national_mergers_listings.csv")

