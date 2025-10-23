import pandas as pd
import logging
import time
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# Helper Function: Extract Listings from the BC Brokers Page
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> pd.DataFrame:
    url = config["listing_url"]
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.get(url)
    actions = ActionChains(driver)

    # Load all listings by clicking the "Load More Posts" button
    while True:
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            load_more = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'fusion-load-more-button')]")))
            actions.move_to_element(load_more).click().perform()
            logging.info("Clicked 'Load More Posts' button.")
            time.sleep(3)
        except Exception as e:
            logging.info("No more 'Load More Posts' button found or all posts loaded.")
            break

    articles = driver.find_elements(By.CSS_SELECTOR, "article.fusion-portfolio-post")
    logging.info("Total listings found: %d", len(articles))
    data = []

    for article in articles:
        try:
            title = article.find_element(By.CSS_SELECTOR, "h2.entry-title").text.strip()
            link = article.find_element(By.CSS_SELECTOR, "h2.entry-title a").get_attribute("href")
            content = article.text
            lines = content.splitlines()

            def extract_field(field_names):
                for name in field_names:
                    for line in lines:
                        if name.lower() in line.lower():
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                return parts[1].strip()
                return "N/A"

            asking_price = extract_field(["Asking Price"])
            region = extract_field(["Region"])
            status = extract_field(["Status", "Sold"])
            description = extract_field(["Description"])
            cash_flow = extract_field(["Cash Flow", "Net Cash Flow"])
            revenue = extract_field(["Revenue", "Sales Revenue"])
            broker = extract_field(["Broker"])
            listing_id = extract_field(["Listing ID"])

            data.append({
                "listing_id": listing_id,
                "href": link,
                "title": title,
                "price_box": asking_price,
                "pub_date": "",
                "description": description,
                "location": region,
                "business_type": "N/A",
                "revenue": revenue,
                "ebitda": cash_flow,
                "contact_name": broker,
                "contact_number": "N/A",
                "status": "Sold" if "sold" in status.lower() else "Available"
            })
        except Exception as e:
            logging.warning("Error parsing article: %s", e)
            continue

    driver.quit()
    logging.info("Extracted %d listings from page.", len(data))
    return data

# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    listings = get_list_links(config)
    records = []

    for item in listings:
        records.append({
            "Broker Name": config.get("broker", ""),
            "Extraction Phase": config.get("phase", ""),
            "Link to Deal": item["href"],
            "Listing ID": item["listing_id"],
            "Published Date": item["pub_date"],
            "Opportunity/Listing Name": item["title"],
            "Opportunity/Listing Description": item["description"],
            "City": "check",
            "State/Province": item["location"],
            "Country": "Canada",
            "Business Type": item["business_type"],
            "Asking Price": item["price_box"],
            "Revenue/Sales": item["revenue"],
            "Down Payment": "check",
            "EBITDA/Cash Flow/Net Income": item["ebitda"],
            "Status": item["status"],
            "Contact Name": item["contact_name"],
            "Contact Number": item["contact_number"],
            "Manual Validation": True
        })

    return pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    default_config = {
        "listing_url": "https://bcbusinessbroker.ca/businesses-for-sale/",
        "headers": {},
        "history": pd.DataFrame(),
        "broker": "BC Business Broker",
        "phase": "initial",
        "contact_name": "",
        "contact_number": "",
    }

    df = scrape(default_config)
    print(df.head())
    df.to_csv("bc_bussiness_brokers_all_listings.csv", index=False)
    logging.info("✅ Data saved to bcbrokers_all_listings.csv")
