import pandas as pd
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import os

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# Helper Function: Extract Listings from Local HTML Files
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Parse local HTML files and extract all business listings.
    """
    html_files = config.get("html_files", [])
    posts: List[Dict[str, str]] = []

    for file_path in html_files:
        if not os.path.exists(file_path):
            logging.error("HTML file not found: %s", file_path)
            continue

        with open(file_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")
            listings = soup.select("li.type-rent.col-md-12")
            logging.info("Found %d listings in %s", len(listings), file_path)

            for li in listings:
                title_tag = li.select_one("h3 a")
                title = title_tag.get_text(strip=True) if title_tag else "N/A"
                full_url = "N/A"
                location_tag = li.select_one("span.location")
                location = location_tag.get_text(strip=True) if location_tag else "N/A"
                price_tag = li.select_one("div.price span")
                price = price_tag.get_text(strip=True) if price_tag else "N/A"

                revenue = cashflow = description = "N/A"
                for span in li.select("div.property-amenities span"):
                    text = span.get_text(strip=True).upper()
                    if "REVENUE" in text:
                        revenue = text.replace("REVENUE", "").strip()
                    elif "CASH FLOW" in text:
                        cashflow = text.replace("CASH FLOW", "").strip()

                # Append extracted data
                posts.append(
                    {
                        "listing_id": "N/A",
                        "href": full_url,
                        "title": title,
                        "price_box": price,
                        "pub_date": "",
                        "description": description,
                        "location": location,
                        "business_type": "N/A",
                        "revenue": revenue,
                        "ebitda": cashflow,
                        "contact_name": config.get("contact_name", ""),
                        "contact_number": config.get("contact_number", ""),
                    }
                )

    logging.info("Extracted total %d listings from HTML files.", len(posts))
    return posts


# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Scrape listings from local HTML files.
    """
    required_keys = [
        "html_files", "history", "broker", "phase", "contact_name", "contact_number"
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    posts = get_list_links(config)
    records = []
    sold_keywords = config.get("sold_keywords", ["sold", "under contract", "closed"])

    for pdata in posts:
        title_lower = pdata['title'].lower()
        status = "Sold" if any(word in title_lower for word in sold_keywords) else "Available"

        records.append(
            {
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
            }
        )

    df = pd.DataFrame(records)
    # Save to CSV
    df.to_csv("Golden_Gate_Business_Advisors.csv", index=False)
    logging.info("Saved extracted listings to ggba_extracted_listings.csv")
    return df


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    default_config: Dict[str, Any] = {
        "html_files": [
            "Golden_Gate_Business_Advisors_page1.html",
            "Golden_Gate_Business_Advisors_page2.html"
        ],
        "history": pd.DataFrame(),
        "broker": "Golden Gate Business Advisors",
        "phase": "initial",
        "contact_name": "N/A",
        "contact_number": "N/A",
    }

    df = scrape(default_config)
    print(df.head())
