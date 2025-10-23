import pandas as pd
import requests
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Helper Function: Extract Listings from the Directory Page
# ---------------------------------------------------------------------------
def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    listing_url = config["listing_url"]
    headers = config.get("headers", {})
    history_df = config.get("history", pd.DataFrame())

    try:
        response = requests.get(listing_url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        logging.error("Failed to fetch listing directory: %s", e)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("table tbody tr")
    logging.info("Found %d table rows", len(rows))

    existing_urls = set(history_df.get("Link to Deal", []))
    posts = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue  # Skip incomplete rows

        title = cols[0].get_text(strip=True)
        verticals = cols[1].get_text(separator=" ", strip=True)
        location = cols[2].get_text(strip=True)
        revenue = cols[3].get_text(strip=True)
        ebitda = cols[4].get_text(strip=True)

        posts.append({
            "listing_id": "N/A",
            "href": config["listing_url"],
            "title": title,
            "price_box": "N/A",  # Not available
            "pub_date": "",
            "description": f"Verticals: {verticals}",
            "location": location,
            "business_type": verticals,
            "revenue": revenue,
            "ebitda": ebitda,
            "contact_name": config.get("contact_name", "N/A"),
            "contact_number": config.get("contact_number", "N/A"),
        })

    logging.info("Extracted %d listings from Trep Advisors page.", len(posts))
    return posts


# ---------------------------------------------------------------------------
# Core Scraper Function
# ---------------------------------------------------------------------------
def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Scrape listings from the provided configuration.

    Args:
        config (Dict[str, Any]): Configuration with required keys:
            listing_url, base_url, headers, history, broker,
            phase, contact_name, contact_number

    Returns:
        DataFrame: A pandas DataFrame containing scraped listings.
    """
    # Check if config has all required keys
    required_keys = [
        "listing_url",
        "base_url",
        "headers",
        "history",
        "broker",
        "phase",
        "contact_name",
        "contact_number",
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    # Fetch the listing posts
    posts = get_list_links(config)
    records = []

    sold_keywords = config.get("sold_keywords", ["sold", "under contract", "closed"])   #checking status


    for pdata in posts:
        title_lower = pdata['title'].lower()
        status = "Sold" if "sold" in title_lower else "Available"

        # Prepare the record for the DataFrame
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

    # Return as a DataFrame
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Example usage: Run this script standalone to test scraping
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Default configuration
    default_config: Dict[str, Any] = {
      "listing_url": "https://trepadvisors.com/acquisition-opportunities/",
       "base_url": "https://trepadvisors.com",
        "headers": {
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
       },
       "history": pd.DataFrame(),
      "broker": "Trep Advisors",
      "phase": "initial",
      "contact_name": "N/A",
        "contact_number": "N/A",
    }

    # User-provided overrides
    overrides = {
        "broker": "Jackim Woods",
        "phase": "initial",
        "contact_name": "Jane Doe",
        "contact_number": "555-1234",
    }

    # Merge defaults and overrides
    config = {**default_config, **overrides}

    # Run the scraper and show results
    df = scrape(config)
    output_file = "trep_advisors_opportunities.csv"
    df.to_csv(output_file, index=False)
    print(f"Saved scraped data to {output_file}")
