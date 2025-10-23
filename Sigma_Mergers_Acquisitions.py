import pandas as pd
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Helper Function: Parse Saved HTML File for Sigma Mergers
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Parse saved HTML file and extract business listings from Sigma Mergers.
    Returns:
        A list of dictionaries, each representing a listing.
    """
    html_file = config["html_file"]
    posts: List[Dict[str, str]] = []

    try:
        with open(html_file, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")
    except Exception as e:
        logging.error("Failed to load HTML file: %s", e)
        return []

    cards = soup.select("div[data-elementor-type='loop-item']")
    logging.info("Found %d listing cards", len(cards))

    for card in cards:
        # Title
        title_tag = card.select_one("h2 span.elementor-headline-plain-text")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        # Status
        sold_banner = card.find("div", class_=lambda c: c and "sold" in c.lower()) if card else None
        text_blob = card.get_text(strip=True).lower()
        status = "Sold" if sold_banner or "sold" in text_blob else "Available"

        # Location
        location = "N/A"
        loc_heading = card.find("h4", string=lambda t: t and "Location" in t)
        if loc_heading:
            loc_span = loc_heading.find_next("span")
            location = loc_span.get_text(strip=True) if loc_span else "N/A"

        # Asking Price
        ask_price = "N/A"
        ask_heading = card.find("h4", string=lambda t: t and "Asking Price" in t)
        if ask_heading:
            price_span = ask_heading.find_next("span")
            ask_price = price_span.get_text(strip=True) if price_span else "N/A"

        # Cash Flow
        cash_flow = "N/A"
        cash_heading = card.find("h4", string=lambda t: t and "Cash Flow" in t)
        if cash_heading:
            flow_span = cash_heading.find_next("span")
            cash_flow = flow_span.get_text(strip=True) if flow_span else "N/A"

        posts.append({
            "listing_id": "N/A",
            "href": "N/A",  # No link in static HTML
            "title": title,
            "price_box": ask_price,
            "pub_date": "",
            "description": "",
            "location": location,
            "business_type": "N/A",
            "revenue": "N/A",
            "ebitda": cash_flow,
            "contact_name": config.get("contact_name", "N/A"),
            "contact_number": config.get("contact_number", "N/A"),
            "status_flag": status,
        })

    return posts


# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    required_keys = [
        "html_file", "broker", "phase", "contact_name", "contact_number"
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    posts = get_list_links(config)
    records = []

    for pdata in posts:
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
            "Status": pdata["status_flag"],
            "Contact Name": pdata["contact_name"],
            "Contact Number": pdata["contact_number"],
            "Manual Validation": True,
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    default_config: Dict[str, Any] = {
        "html_file": "sigmamergersaquisition_raw.html",
        "broker": "Sigma Mergers",
        "phase": "initial",
        "contact_name": "Sigma Team",
        "contact_number": "N/A",
    }

    df = scrape(default_config)
    df.to_csv("sigmamergers_final_listings.csv", index=False)
    print("Scraped data saved to 'sigmamergers_final_listings.csv'")
