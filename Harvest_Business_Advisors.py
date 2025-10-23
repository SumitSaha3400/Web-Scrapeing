import pandas as pd
import requests
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# Helper Function: Extract Listings from the Directory Page (Selenium-Based)
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    options = Options()
    options.headless = True
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(config["listing_url"])
        time.sleep(5)  # wait for initial load

        # Infinite scroll to load all listings
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        soup = BeautifulSoup(driver.page_source, "html.parser")

    finally:
        driver.quit()

    listings = []
    cards = soup.find_all("div", class_="gallery-item-common-info")
    logging.info("Found %d listings", len(cards))

    for card in cards:
        try:
            title_tag = card.find("h2", class_="bD0vt9 KNiaIk")
            title = title_tag.get_text(strip=True) if title_tag else "N/A"

            link_tag = card.find("a", href=True)
            href = link_tag["href"].strip() if link_tag else "N/A"
            full_url = href if href.startswith("http") else config["base_url"].rstrip("/") + "/" + href.lstrip("/")

            desc_tag = card.find("div", class_="BOlnTh")
            description = desc_tag.get_text(" ", strip=True) if desc_tag else "N/A"

            # Extract key financials
            asking_price = re.search(r"Asking Price:\s*\$[\d,]+", description)
            gross_revenue = re.search(r"Gross Revenue:\s*\$[\d,]+", description)
            profit = re.search(r"(Adjusted Profit|Seller[’']?s Discretionary Earnings):\s*\$[\d,]+", description)

            listings.append({
                "listing_id": "N/A",
                "href": full_url,
                "title": title,
                "price_box": asking_price.group().split(":")[1].strip() if asking_price else "N/A",
                "pub_date": "",
                "description": description,
                "location": "N/A",
                "business_type": "N/A",
                "revenue": gross_revenue.group().split(":")[1].strip() if gross_revenue else "N/A",
                "ebitda": profit.group().split(":")[1].strip() if profit else "N/A",
                "contact_name": config.get("contact_name", ""),
                "contact_number": config.get("contact_number", "")
            })
        except Exception as e:
            logging.warning("Failed to parse listing: %s", e)
            continue

    return listings

# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    required_keys = [
        "listing_url", "base_url", "headers", "history", "broker",
        "phase", "contact_name", "contact_number"
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

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
        "listing_url": "https://www.harvestbusiness.com/s-projects-basic",
        "base_url": "https://www.harvestbusiness.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        "history": pd.DataFrame(),
        "broker": "Harvest Business",
        "phase": "initial",
        "contact_name": "John Doe",
        "contact_number": "123-456-7890",
    }

    df = scrape(default_config)
    df.to_csv("harvestbusiness_all_listings.csv", index=False, encoding="utf-8")
    print(f"Scraping complete. {len(df)} listings saved to 'harvestbusiness_all_listings.csv'")




