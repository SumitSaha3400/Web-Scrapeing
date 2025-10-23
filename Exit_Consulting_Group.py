# import time
# import csv
# import re
# import html
# import json
# import pandas as pd
# import logging
# from bs4 import BeautifulSoup
# from typing import Dict, Any, List
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager

# # ---------------------------------------------------------------------------
# # Logging Setup
# # ---------------------------------------------------------------------------
# logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# # ---------------------------------------------------------------------------
# # Selenium Setup Function
# # ---------------------------------------------------------------------------
# def init_driver() -> webdriver.Chrome:
#     options = Options()
#     options.add_argument("--headless")
#     options.add_argument("--window-size=1920,1080")
#     return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# # ---------------------------------------------------------------------------
# # Click "Load More" Until Done
# # ---------------------------------------------------------------------------
# def click_load_more(driver, max_wait=10):
#     wait = WebDriverWait(driver, max_wait)
#     while True:
#         try:
#             btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Load More')]")))
#             driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
#             time.sleep(0.5)
#             driver.execute_script("arguments[0].click();", btn)
#             logging.info("Clicked 'Load More'")
#             time.sleep(3)
#         except TimeoutException:
#             logging.info("No more 'Load More' button.")
#             break

# # ---------------------------------------------------------------------------
# # Get All Listing Links from Page
# # ---------------------------------------------------------------------------
# def get_listing_links(driver, base_url: str) -> List[str]:
#     soup = BeautifulSoup(driver.page_source, "html.parser")
#     cards = soup.select("a[href*='/listings/']")
#     visited = set()
#     links = []

#     for card in cards:
#         href = card.get("href")
#         if href and "/listings/" in href and href not in visited:
#             full_url = href if href.startswith("http") else base_url.rstrip("/") + href
#             visited.add(full_url)
#             links.append(full_url)

#     logging.info("Found %d unique listings", len(links))
#     return links

# # ---------------------------------------------------------------------------
# # Extract Listing Details
# # ---------------------------------------------------------------------------
# def extract_listing_data(driver, url: str) -> Dict[str, Any]:
#     driver.get(url)
#     time.sleep(2)

#     result = {
#         "Status": "For Sale",
#         "Business Name": "N/A",
#         "Listing ID": "N/A",
#         "Location": "N/A",
#         "Revenue": "N/A",
#         "SDE": "N/A",
#         "URL": url
#     }

#     try:
#         soup = BeautifulSoup(driver.page_source, "html.parser")
#         full_text = soup.get_text().lower()

#         if "sold" in full_text:
#             result["Status"] = "Sold"
#         elif "pending" in full_text:
#             result["Status"] = "Pending"

#         # Business Name
#         meta_title = soup.find("meta", property="og:title")
#         if meta_title and meta_title.get("content"):
#             result["Business Name"] = meta_title["content"].split("|")[0].strip()

#         # Listing ID from Vue :acf
#         vue_tags = soup.find_all(lambda tag: tag.has_attr(":acf"))
#         for tag in vue_tags:
#             try:
#                 raw_acf = html.unescape(tag[":acf"])
#                 acf_json = json.loads(raw_acf)
#                 if "listing_id" in acf_json:
#                     result["Listing ID"] = f"#{acf_json['listing_id']}"
#             except:
#                 continue

#         # Location
#         for li in soup.find_all("li"):
#             if "located in" in li.text.lower():
#                 match = re.search(r"located in\s+(.+)", li.text, re.IGNORECASE)
#                 if match:
#                     result["Location"] = match.group(1).strip()
#                     break

#         # Revenue & SDE
#         for row in soup.find_all("tr"):
#             cols = row.find_all("td")
#             if len(cols) >= 5:
#                 if "revenue" in cols[0].text.lower():
#                     result["Revenue"] = cols[4].text.strip()
#                 if "sde" in cols[0].text.lower():
#                     result["SDE"] = cols[4].text.strip()

#     except Exception as e:
#         logging.error("Error processing %s: %s", url, e)

#     return result

# # ---------------------------------------------------------------------------
# # Main Scraper Function
# # ---------------------------------------------------------------------------
# def scrape_exit_consulting(config: Dict[str, Any]) -> pd.DataFrame:
#     driver = init_driver()
#     driver.get(config["listing_url"])
#     time.sleep(3)

#     click_load_more(driver)
#     listing_links = get_listing_links(driver, config["base_url"])

#     listings = []
#     for url in listing_links:
#         data = extract_listing_data(driver, url)
#         listings.append(data)

#     driver.quit()
#     return pd.DataFrame(listings)

# # ---------------------------------------------------------------------------
# # Main Runner
# # ---------------------------------------------------------------------------
# if __name__ == "__main__":
#     config = {
#         "listing_url": "https://exitconsultinggroup.com/listings/",
#         "base_url": "https://exitconsultinggroup.com"
#     }

#     df = scrape_exit_consulting(config)
#     df.to_csv("exit_consulting_listings.csv", index=False)
#     print("\n✅ Done! Listings saved to 'exit_consulting_listings.csv'")


import pandas as pd
import logging
import re
import time
import html
import json
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Helper Function: Extract Listings from the Directory Page
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Fetch the directory page and extract all listing links and details using Selenium.

    Returns:
        A list of dictionaries, each representing a listing.
    """
    driver = config["driver"]
    wait = WebDriverWait(driver, 10)

    # Load initial page
    driver.get(config["listing_url"])
    time.sleep(3)

    # Click all 'Load More' buttons
    while True:
        try:
            load_more = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Load More')]")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more)
            time.sleep(1)
            load_more.click()
            logging.info("Clicked 'Load More'")
            time.sleep(3)
        except TimeoutException:
            logging.info("No more 'Load More' button.")
            break

    # Parse the fully loaded page
    soup = BeautifulSoup(driver.page_source, "html.parser")
    listing_cards = soup.select("a[href*='/listings/']")
    visited = set()
    posts = []

    for tag in listing_cards:
        href = tag.get("href")
        if href and "/listings/" in href and href not in visited:
            full_url = href if href.startswith("http") else config["base_url"].rstrip("/") + href
            visited.add(full_url)

            # Visit each listing
            driver.get(full_url)
            time.sleep(2)
            sub_soup = BeautifulSoup(driver.page_source, "html.parser")

            data = {
                "listing_id": "N/A",
                "href": full_url,
                "title": "N/A",
                "description": "N/A",
                "location": "N/A",
                "business_type": "N/A",
                "price_box": "N/A",
                "revenue": "N/A",
                "ebitda": "N/A",
                "contact_name": "N/A",
                "contact_number": "N/A",
                "pub_date": "",
            }

            # Status from body
            full_text = sub_soup.get_text().lower()
            data["status_flag"] = "sold" if "sold" in full_text else "available"

            # Title
            meta_title = sub_soup.find("meta", property="og:title")
            if meta_title:
                data["title"] = meta_title.get("content", "N/A").split("|")[0].strip()

            # Listing ID
            vue_tags = sub_soup.find_all(lambda tag: tag.has_attr(":acf"))
            for tag in vue_tags:
                try:
                    acf_raw = html.unescape(tag[":acf"])
                    acf_json = json.loads(acf_raw)
                    data["listing_id"] = f"#{acf_json.get('listing_id', 'N/A')}"
                except:
                    pass

            # Location
            for li in sub_soup.find_all("li"):
                if "located in" in li.text.lower():
                    match = re.search(r"located in\s+(.+)", li.text, re.IGNORECASE)
                    if match:
                        data["location"] = match.group(1).strip()
                    break

            # Revenue and SDE/EBITDA
            for row in sub_soup.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 5:
                    if "revenue" in cols[0].text.lower():
                        data["revenue"] = cols[4].text.strip()
                    if "sde" in cols[0].text.lower():
                        data["ebitda"] = cols[4].text.strip()

            posts.append(data)

    logging.info("Extracted %d listings", len(posts))
    return posts


# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Scrape listings using Selenium and return a structured DataFrame.
    """
    required_keys = [
        "listing_url", "base_url", "driver", "broker",
        "phase", "contact_name", "contact_number", "headers", "history"
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    posts = get_list_links(config)
    records = []

    for post in posts:
        status = "Sold" if post.get("status_flag", "") == "sold" else "Available"
        records.append({
            "Broker Name": config["broker"],
            "Extraction Phase": config["phase"],
            "Link to Deal": post["href"],
            "Listing ID": post["listing_id"],
            "Published Date": post["pub_date"],
            "Opportunity/Listing Name": post["title"],
            "Opportunity/Listing Description": post["description"],
            "City": "check",
            "State/Province": post["location"],
            "Country": "United States",
            "Business Type": post["business_type"],
            "Asking Price": post["price_box"],
            "Revenue/Sales": post["revenue"],
            "Down Payment": "check",
            "EBITDA/Cash Flow/Net Income": post["ebitda"],
            "Status": status,
            "Contact Name": config["contact_name"],
            "Contact Number": config["contact_number"],
            "Manual Validation": True,
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Setup Selenium driver
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    default_config: Dict[str, Any] = {
        "listing_url": "https://exitconsultinggroup.com/listings/",
        "base_url": "https://exitconsultinggroup.com",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "history": pd.DataFrame(),
        "broker": "Exit Consulting Group",
        "phase": "initial",
        "contact_name": "N/A",
        "contact_number": "N/A",
        "driver": driver
    }

    df = scrape(default_config)
    driver.quit()

    df.to_csv("exit_consulting_listings.csv", index=False)
    print("\n✅ Done! Saved to 'exit_consulting_listings.csv'")
