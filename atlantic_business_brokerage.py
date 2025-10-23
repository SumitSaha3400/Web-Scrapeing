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
    """
    Fetch the directory page and extract all listing links and basic details.

    Returns:
        A list of dictionaries, each representing a listing.
    """
    listing_url = config["listing_url"]
    headers = config.get("headers", {})
    history_df = config.get("history", pd.DataFrame())

    # Fetch the HTML page
    try:
        response = requests.get(listing_url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        logging.error("Failed to fetch listing directory: %s", e)
        return []

    # Existing listing URLs (to avoid duplicates)
    existing_urls = set(history_df.get("Link to Deal", []).dropna())
    posts: List[Dict[str, str]] = []

    # Parse the page with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    listing_cards = soup.find_all("div", class_="listing-right-box")
    logging.info("Found %d listing cards", len(listing_cards))

    # Loop over each listing card
    for post in listing_cards:
        # Initialize default values
        ad_id = "N/A"
        business_type = "N/A"
        price_match = None
        revenue_match = None
        ebitda_match = None
        contact_name = "N/A"
        contact_number = "N/A"


        # Extract the title
        title_tag = post.find("h2")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        # Extract the full listing link (href)
        link_tag = post.find("a", href=True) if title_tag else None
        full_url = link_tag["href"].strip() if link_tag else None

        # Extract the Ad ID
        listing_info_tag = post.find("div", class_="listing-unit-text")
        if listing_info_tag:
            text = listing_info_tag.get_text()
            match = re.search(r"Ad ID:\s*(\d+)", text)
            if match:
                ad_id = match.group(1)

        # Extract the Business Type
        if listing_info_tag:
            match = re.search(r"Business Type:\s*(.+)", listing_info_tag.get_text())
            if match:
                business_type = match.group(1)

        # Extract the Location
        location = "N/A"
        if listing_info_tag:
            lines = listing_info_tag.get_text(separator="\n").split("\n")
            for line in lines:
                if "Location:" in line:
                    match = re.search(r"Location:\s*(.*)", line)
                    if match:
                        extracted = match.group(1).strip()
                        location = extracted if extracted else "N/A"
                    break


        # Extract the price (Asking Price)
        price_box = post.find("div", class_="price-box")
        if price_box:
            price_match = re.search(r"\$[\d,]+", price_box.get_text())

        # Extract the description
        description = "N/A"
        if full_url:
            try:
                detail_resp = requests.get(full_url, headers=headers, timeout=15)
                detail_resp.raise_for_status()
                detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

                # Attempt to grab the full content inside the post
                desc_section = detail_soup.find("div", class_="listing-inner-sec fran-info")
                if desc_section:
                    paragraphs = desc_section.find_all("p")
                    description = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
            except Exception as e:
                logging.warning("Failed to fetch detail page for %s: %s", full_url, e)

         # Extract Contact Info
        contact_header = detail_soup.find("h2", string=re.compile(r"Contact Information", re.IGNORECASE))
        if contact_header:
            for sibling in contact_header.find_next_siblings("p"):
                text = sibling.get_text(strip=True)
                name_match = re.search(r"Name:\s*(.+)", text)
                phone_match = re.search(r"\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}", text)

                if name_match:
                    contact_name = name_match.group(1)
                if phone_match:
                    contact_number = phone_match.group(0)


        # Extract Annual Gross Revenue
        revenue_strong = post.find("strong", string=re.compile("Annual Gross Revenue"))
        if revenue_strong and revenue_strong.parent:
            revenue_match = re.search(r"\$[\d,]+", revenue_strong.parent.text)

        # Extract Annual EBITDA/Cash Flow
        ebitda_strong = post.find("strong", string=re.compile("Annual EBITDA/Cash Flow"))
        if ebitda_strong and ebitda_strong.parent:
            ebitda_match = re.search(r"\$[\d,]+", ebitda_strong.parent.text)

        

        # Append the extracted data to the list
        posts.append(
            {
                "listing_id": ad_id,
                "href": full_url,
                "title": title,
                "price_box": price_match.group() if price_match else "N/A",
                "pub_date": "",  # No date available on this page
                "description": description,
                "location": location,
                "business_type": business_type,
                "revenue": revenue_match.group() if revenue_match else "N/A",
                "ebitda": ebitda_match.group() if ebitda_match else "N/A",
                "contact_name": contact_name,
                "contact_number": contact_number,
            }
        )

    logging.info("Extracted %d listings from page.", len(posts))
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
        "listing_url": "https://www.jackimwoods.com/active-engagements/",
        "base_url": "https://www.jackimwoods.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        "history": pd.DataFrame(),
        "broker": "",          # Will be overridden
        "phase": "",           # Will be overridden
        "contact_name": "",    # Will be overridden
        "contact_number": "",  # Will be overridden
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
    print(df.head())
