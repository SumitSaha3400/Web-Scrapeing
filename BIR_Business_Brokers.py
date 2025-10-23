import pandas as pd
import logging
import re
import time
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# Helper Function: Extract Listings from the Directory Page
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(service=Service(), options=options)
    driver.get(config['listing_url'])

    posts = []

    def extract_fields(text: str) -> Dict[str, str]:
        fields = {
            'Monthly Sales': '',
            'Net Profit': '',
            'Asking Price': '',
            'Location': '',
            'Description': ''
        }

        sales = re.search(r'Monthly Sales:\s*(.*?)(?:\n|$)', text, re.IGNORECASE)
        profit = re.search(r'Net Profit:\s*(.*?)(?:\n|$)', text, re.IGNORECASE)
        price = re.search(r'Asking Price:\s*(.*?)(?:\n|$)', text, re.IGNORECASE)
        location = re.search(r'Location:\s*(.*?)(?:\n|$)', text, re.IGNORECASE)

        if sales: fields['Monthly Sales'] = sales.group(1).strip()
        if profit: fields['Net Profit'] = profit.group(1).strip()
        if price: fields['Asking Price'] = price.group(1).strip()
        if location: fields['Location'] = location.group(1).strip()

        cleaned = re.sub(r'(Monthly Sales|Net Profit|Asking Price|Location):.*?(?:\n|$)', '', text, flags=re.IGNORECASE)
        fields['Description'] = cleaned.strip()

        return fields

    while True:
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        listings = soup.find_all('div', class_='epl-property-blog-entry-wrapper')
        logging.info("Found %d listings on this page", len(listings))

        for listing in listings:
            title_tag = listing.find('h3', class_='entry-title')
            title = title_tag.get_text(strip=True) if title_tag else ''

            desc_tag = listing.find('div', class_='epl-excerpt-content')
            full_text = desc_tag.get_text(separator='\n', strip=True) if desc_tag else ''
            fields = extract_fields(full_text)

            posts.append({
                "listing_id": "N/A",
                "href": "N/A",
                "title": title,
                "price_box": fields['Asking Price'],
                "pub_date": "",
                "description": fields['Description'],
                "location": fields['Location'],
                "business_type": "N/A",
                "revenue": fields['Monthly Sales'],
                "ebitda": fields['Net Profit'],
                "contact_name": config.get('contact_name', ''),
                "contact_number": config.get('contact_number', '')
            })

        try:
            next_btn = driver.find_element(By.LINK_TEXT, 'Next Page »')
            driver.execute_script("arguments[0].scrollIntoView();", next_btn)
            time.sleep(1)
            next_btn.click()
        except NoSuchElementException:
            break

    driver.quit()
    logging.info("Extracted total %d listings.", len(posts))
    return posts

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

    for pdata in posts:
        status = "Sold" if "sold" in pdata['title'].lower() else "Available"

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
# Example usage: Run this script standalone to test scraping
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    default_config: Dict[str, Any] = {
        "listing_url": "https://businessbrokersorangecounty.com/listings/?pagination_id=1&instance_id=1",
        "base_url": "https://businessbrokersorangecounty.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        "history": pd.DataFrame(),
        "broker": "BIR Business Brokers",
        "phase": "initial",
        "contact_name": "Ken Krantz",
        "contact_number": "888-400-4030",
    }

    df = scrape(default_config)
    df.to_csv("bir_business_brokers_clean.csv", index=False)
    print(df.head())

