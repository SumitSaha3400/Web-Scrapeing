import pandas as pd
import logging
from typing import Dict, Any, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Helper Function: Extract Listings with Selenium
# ---------------------------------------------------------------------------
def get_listings_with_selenium(config: Dict[str, Any]) -> List[Dict[str, str]]:
    url = config["listing_url"]
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    wait = WebDriverWait(driver, 20)
    time.sleep(5)

    # Try clicking "View More"
    try:
        view_more = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'View More')]")))
        logging.info("Clicking 'View More' to load all listings...")
        view_more.click()
        time.sleep(5)
    except Exception as e:
        logging.warning("'View More' not found or already clicked: %s", e)

    cards = driver.find_elements(By.CSS_SELECTOR, "a.bl-jump-down")
    logging.info("Total listings found: %d", len(cards))

    results = []

    def safe_text(card, by, value):
        try:
            element = card.find_element(by, value)
            text = element.text.strip()
            return text if text else "N/A"
        except:
            return "N/A"

    for card in cards:
        entry = {
            "Title": safe_text(card, By.CSS_SELECTOR, "div.bl-h3"),
            "Location": safe_text(card, By.CSS_SELECTOR, "div.bl-h5.bl-txt-dark-blue"),
            "Tagline": safe_text(card, By.XPATH, ".//span[@ng-bind='listing.actionPhrase']"),
            "Price": safe_text(card, By.CSS_SELECTOR, "div.bl-h3.sp-w-6-of-10"),
            "Total Sales": safe_text(card, By.XPATH, ".//div[contains(text(),'Total Sales')]/following-sibling::div"),
            "Income": safe_text(card, By.XPATH, ".//div[contains(text(),'Income')]/following-sibling::div"),
            "Listing ID": safe_text(card, By.XPATH, ".//span[contains(text(),'Listing #')]/following-sibling::span"),
            "Tags": safe_text(card, By.XPATH, ".//div[contains(@class,'sp-grid-item-grow')]")
        }

        if entry["Title"] != "N/A":
            results.append(entry)

    driver.quit()
    return results


# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    posts = get_listings_with_selenium(config)
    records = []

    for pdata in posts:
        status = "Sold" if "sold" in pdata['Title'].lower() else "Available"

        records.append({
            "Broker Name": config.get("broker", ""),
            "Extraction Phase": config.get("phase", ""),
            "Link to Deal": "https://www.blbrokers.com/businesses-for-sale",  # No per-listing link available
            "Listing ID": pdata["Listing ID"],
            "Published Date": "",  # Not available
            "Opportunity/Listing Name": pdata["Title"],
            "Opportunity/Listing Description": pdata["Tagline"],
            "City": "check",
            "State/Province": pdata["Location"],
            "Country": "United States",
            "Business Type": pdata["Tags"],
            "Asking Price": pdata["Price"],
            "Revenue/Sales": pdata["Total Sales"],
            "Down Payment": "check",
            "EBITDA/Cash Flow/Net Income": pdata["Income"],
            "Status": status,
            "Contact Name": config.get("contact_name", ""),
            "Contact Number": config.get("contact_number", ""),
            "Manual Validation": True
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Run as standalone script
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    default_config: Dict[str, Any] = {
        "listing_url": "https://www.blbrokers.com/businesses-for-sale",
        "base_url": "https://www.blbrokers.com",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "history": pd.DataFrame(),
        "broker": "BottomLine Business Brokers",
        "phase": "initial",
        "contact_name": "Jane Doe",
        "contact_number": "555-1234",
    }

    df = scrape(default_config)
    print(df.head())
    df.to_csv("BottomLine_Business_Brokers.csv", index=False)
    print("✅ Listings saved to 'blbrokers_all_19_cleaned.csv'")
