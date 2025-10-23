# from bs4 import BeautifulSoup
# import pandas as pd

# # Load saved HTML content
# with open("frontrangebussiness_raw.html", "r", encoding="utf-8") as file:
#     soup = BeautifulSoup(file, "html.parser")

# listings = []

# # Find each listing box
# for box in soup.select("div.listingBox"):
#     # Status (NEW or ACTIVE)
#     status_div = box.select_one(".topLeft .activeButton")
#     status = status_div.get_text(strip=True) if status_div else None

#     # Title
#     title_tag = box.select_one(".listingTitle h2")
#     title = title_tag.get_text(strip=True) if title_tag else None

#     # Industry
#     industry_tag = box.select_one(".listingIndustry .descriptionValue")
#     industry = industry_tag.get_text(strip=True) if industry_tag else None

#     # Location
#     location_tag = box.select_one(".listingLocation .descriptionValue")
#     location = location_tag.get_text(strip=True) if location_tag else None

#     # Internal ID
#     id_tag = box.select_one(".internalID .descriptionValue")
#     internal_id = id_tag.get_text(strip=True) if id_tag else None

#     # Price
#     price_tag = box.select_one(".listingPrice .priceDescriptionValue")
#     price = price_tag.get_text(strip=True) if price_tag else None

#     listings.append({
#         "Status": status,
#         "Title": title,
#         "Industry": industry,
#         "Location": location,
#         "Internal ID": internal_id,
#         "Price": price
#     })

# # Save to CSV
# df = pd.DataFrame(listings)
# df.to_csv("frontrange_businesses_all_listings.csv", index=False, encoding="utf-8")

# print("✅ Extracted and saved all listings to 'frontrange_businesses_all_listings.csv'.")



import pandas as pd
import requests
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Helper Function: Extract Listings from Front Range Business
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    url = config["listing_url"]
    headers = config.get("headers", {})
    history_df = config.get("history", pd.DataFrame())

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        logging.error("Failed to fetch listing directory: %s", e)
        return []

    existing_urls = set(history_df.get("Link to Deal", []))
    soup = BeautifulSoup(response.text, "html.parser")
    boxes = soup.select("div.listingBox")
    logging.info("Found %d listings", len(boxes))

    posts = []
    for box in boxes:
        status = box.select_one(".topLeft .activeButton")
        title = box.select_one(".listingTitle h2")
        industry = box.select_one(".listingIndustry .descriptionValue")
        location = box.select_one(".listingLocation .descriptionValue")
        internal_id = box.select_one(".internalID .descriptionValue")
        price = box.select_one(".listingPrice .priceDescriptionValue")
        link_tag = box.select_one("a.listingButton")
        full_url = link_tag['href'] if link_tag else None

        posts.append({
            "listing_id": internal_id.get_text(strip=True) if internal_id else "N/A",
            "href": full_url,
            "title": title.get_text(strip=True) if title else "N/A",
            "price_box": price.get_text(strip=True) if price else "N/A",
            "pub_date": "",
            "description": "",  # No detail description unless second page is fetched
            "location": location.get_text(strip=True) if location else "N/A",
            "business_type": industry.get_text(strip=True) if industry else "N/A",
            "revenue": "N/A",  # Not present
            "ebitda": "N/A",   # Not present
            "contact_name": config.get("contact_name", ""),
            "contact_number": config.get("contact_number", "")
        })

    return posts


# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    required_keys = [
        "listing_url", "base_url", "headers", "history",
        "broker", "phase", "contact_name", "contact_number"
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    posts = get_list_links(config)
    records = []

    for pdata in posts:
        title_lower = pdata['title'].lower()
        status = "Available" if "sold" not in title_lower else "Sold"

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
            "Manual Validation": True
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    default_config: Dict[str, Any] = {
        "listing_url": "https://frontrangebusiness.com/businesses-for-sale/",
        "base_url": "https://frontrangebusiness.com",
        "headers": {
            "User-Agent": "Mozilla/5.0"
        },
        "history": pd.DataFrame(),
        "broker": "Front Range Business, Inc.",
        "phase": "initial",
        "contact_name": "Team FRB",
        "contact_number": "N/A"
    }

    df = scrape(default_config)
    df.to_csv("frontrange_businesses_full.csv", index=False)
    print("✅ Scraping complete. Saved to 'frontrange_businesses_full.csv'")
