import pandas as pd
import requests
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Helper Function: Fetch listing links
# ---------------------------------------------------------------------------

def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Fetch listing page and extract summary data for each listing.

    Returns:
        A list of dictionaries, one per listing, each containing title, link,
        financials, and other metadata.
    """
    listing_url = config["listing_url"]
    headers = config.get("headers", {})
    history = config.get("history", pd.DataFrame())
    sold_keywords = config.get("sold_keywords", ["sold", "under contract", "closed"])

    try:
        response = requests.get(listing_url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        logging.error("Failed to fetch listing page: %s", e)
        return []

    existing_urls = set(history.get("Link to Deal", []).dropna())
    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("li", class_=["b-listing", "open"])

    posts = []

    for post in cards:
        # Default values
        listing_id = "N/A"
        title_only = "N/A"
        business_type = "N/A"
        description = "N/A"
        price = down_payment = cash_flow = gross_revenue = location = "N/A"

        # Extract title and listing ID
        title_tag = post.find("h3")
        if title_tag and (span := title_tag.find("span")):
            full_title = span.get_text(strip=True)
            match = re.match(r'[#]?(\d+)\s*[-–—]\s*(.+)', full_title)
            if match:
                listing_id = match.group(1)
                title_only = match.group(2)
            else:
                title_only = full_title

        # Extract listing link
        link_tag = post.find("a", href=True)
        full_url = link_tag["href"].strip() if link_tag else "N/A"

        # Extract business type
        bt_tag = post.find("div", class_="listing-unit-text")
        if bt_tag and (bt_match := re.search(r"Business Type:\s*(.+)", bt_tag.get_text())):
            business_type = bt_match.group(1)

        # Extract description
        content_div = post.find("div", class_="the-content")
        if content_div and (desc := content_div.find("p")):
            description = desc.get_text(strip=True)

        # Extract financial and location details
        details_list = post.find("ul", class_="location-details")
        if details_list:
            for li in details_list.find_all("li"):
                label = li.find("h4").get_text(strip=True) if li.find("h4") else ""
                value = li.find("span", class_="detail").get_text(strip=True) if li.find("span", class_="detail") else ""

                if "Price" in label:
                    price = value
                elif "Down Payment" in label:
                    down_payment = value
                elif "Cash Flow" in label:
                    cash_flow = value
                elif "Gross Revenue" in label:
                    gross_revenue = value
                elif "Location" in label:
                    location = value

        # Determine status from full post text
        full_post_text = post.get_text(separator=' ', strip=True).lower()
        status = "Sold" if any(re.search(rf"\b{re.escape(kw)}\b", full_post_text) for kw in sold_keywords) else "Available"

        # Add this listing's data to the list
        posts.append({
            "listing_id": listing_id,
            "href": full_url,
            "title": title_only,
            "price_box": price,
            "pub_date": "",  # No publish date available
            "description": description,
            "location": location,
            "business_type_tag": business_type,
            "revenue_span": gross_revenue,
            "ebitda_span": cash_flow,
            "down_payment": down_payment,
            "status": status,
        })

    logging.info("Extracted %d listings", len(posts))
    return posts

# ---------------------------------------------------------------------------
# Main Scraper Function
# ---------------------------------------------------------------------------

def scrape(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Main function to scrape all listings and return a structured DataFrame.

    Required config keys:
        - listing_url
        - base_url
        - headers
        - history
        - broker
        - phase
        - contact_name
        - contact_number
    """
    required_keys = [
        "listing_url", "base_url", "headers", "history",
        "broker", "phase", "contact_name", "contact_number"
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing config keys: {', '.join(missing)}")

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
            "City": "check",  # Placeholder, could be improved with parsing
            "State/Province": pdata["location"],
            "Country": "United States",
            "Business Type": pdata["business_type_tag"],
            "Asking Price": pdata["price_box"],
            "Revenue/Sales": pdata["revenue_span"],
            "Down Payment": pdata["down_payment"],
            "EBITDA/Cash Flow/Net Income": pdata["ebitda_span"],
            "Status": pdata["status"],
            "Contact Name": config["contact_name"],
            "Contact Number": "215-357-9694",
            "Manual Validation": True,
        })

    return pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Default config
    default_config = {
        "listing_url": "https://www.jackimwoods.com/active-engagements/",
        "base_url": "https://www.jackimwoods.com",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "history": pd.DataFrame(),
        "broker": "",          # to be overridden
        "phase": "",           # to be overridden
        "contact_name": "",    # to be overridden
        "contact_number": "215-357-9694",
        "sold_keywords": ["sold", "under contract", "closed"],  # Customizable
    }

    # Custom overrides for this run
    overrides = {
        "broker": "Jack Im Woods",
        "phase": "initial",
        "contact_name": "Jane Doe",
        "contact_number": "555-1234",
    }

    # Merge config and run
    config = {**default_config, **overrides}
    df = scrape(config)
    print(df.head())
