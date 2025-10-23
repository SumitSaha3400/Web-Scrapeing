import pandas as pd
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Helper Function: Parse Listings from HTML
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract all business listings from the local HTML file.
    """
    file_path = config.get("local_html_file")
    base_url = config.get("base_url", "")
    history_df = config.get("history", pd.DataFrame())

    # Load HTML from file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except Exception as e:
        logging.error("Failed to open HTML file: %s", e)
        return []

    posts = []
    listings = soup.find_all("div", id="businessDetails")
    logging.info("Found %d business listings", len(listings))

    for div in listings:
        try:
            title = div.find("label", text="Title:").find_next("strong").get_text(strip=True)
            industry = div.find("label", text="Industry:").find_next("strong").get_text(strip=True)
            location = div.find("label", text="Location:").find_next("strong").get_text(strip=True)
            listing_number = div.find("label", text="Listing Number:").find_next("a").get_text(strip=True)

            # Use listing number to reconstruct a dummy URL
            full_url = f"{base_url}?listing={listing_number}"

            financials = div.find_all("div", class_="col-2")
            selling_price = revenue = ebitda = "N/A"

            for section in financials:
                if section.find("label", text="Selling Price:"):
                    selling_price = section.find("label", text="Selling Price:").next_sibling.strip()
                if section.find("label", text="Revenue:"):
                    revenue = section.find("label", text="Revenue:").next_sibling.strip()
                if section.find("label", text="Adjusted EBITDA:"):
                    ebitda = section.find("label", text="Adjusted EBITDA:").next_sibling.strip()

            posts.append({
                "listing_id": listing_number,
                "href": full_url,
                "title": title,
                "price_box": selling_price,
                "pub_date": "",
                "description": "",
                "location": location,
                "business_type": industry,
                "revenue": revenue,
                "ebitda": ebitda,
                "contact_name": config.get("contact_name", "N/A"),
                "contact_number": config.get("contact_number", "N/A"),
            })

        except Exception as e:
            logging.warning("Error parsing a listing block: %s", e)

    return posts


# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Process business listings and return a structured DataFrame.
    """
    required_keys = [
        "local_html_file", "listing_url", "base_url",
        "broker", "phase", "contact_name", "contact_number"
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    posts = get_list_links(config)
    records = []

    for pdata in posts:
        status = "Available" if "sold" not in pdata["title"].lower() else "Sold"

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

    df = pd.DataFrame(records)
    df.to_csv("Southern_Mergers & Acquisitions_listings.csv", index=False)
    logging.info("Saved %d listings to charlotte_business_listings.csv", len(df))
    return df


# ---------------------------------------------------------------------------
# Run as script
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    config = {
        "local_html_file": "SouthernMergers&Acquisitions_raw.html",
        "listing_url": "https://charlotte-business-broker.com/business-forSale-charlotteNC.asp",
        "base_url": "https://charlotte-business-broker.com/business-forSale-charlotteNC.asp",
        "broker": "Southern Mergers & Acquisitions",
        "phase": "initial",
        "contact_name": "Bill Law",
        "contact_number": "704-897-8232",
        "history": pd.DataFrame(),
    }

    df = scrape(config)
    print(df.head())
