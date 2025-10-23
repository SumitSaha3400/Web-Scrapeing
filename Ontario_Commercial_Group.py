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
    existing_urls = set(history_df.get("Link to Deal", []))
    posts: List[Dict[str, str]] = []

    # Parse the page with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    listing_boxes = soup.find_all("div", class_="listing-box")
    logging.info("Found %d listing boxes", len(listing_boxes))

    if not listing_boxes:
        logging.warning("No business listings found with the class 'listing-box'. The HTML structure might have changed.")
        return []

    # Loop over each listing box
    for listing in listing_boxes:
        # Initialize default values
        title = "N/A"
        image_url = "N/A"
        industry = "N/A"
        location = "N/A"
        listing_id = "N/A"
        cash_flow = "N/A"
        price = "N/A"
        excerpt = "N/A"
        learn_more_link = "N/A"

        # Extract Title and Learn More Link
        title_tag = listing.find('div', class_='listing-title')
        if title_tag and title_tag.find('a'):
            title = title_tag.find('a').get_text(strip=True)
            learn_more_link = title_tag.find('a')['href']
            
            # Ensure the URL is absolute
            if learn_more_link and not learn_more_link.startswith(('http://', 'https://')):
                learn_more_link = f"https://www.ontario-commercial.com{learn_more_link}"

        # Extract Image URL
        image_tag = listing.find('div', class_='ftrdimg')
        if image_tag and image_tag.find('img'):
            # Websites often use 'data-src' for lazy-loaded images, fallback to 'src'
            image_url = image_tag.find('img').get('data-src') or image_tag.find('img').get('src')
            # Ensure the URL is absolute
            if image_url and not image_url.startswith(('http://', 'https://')):
                image_url = f"https://www.ontario-commercial.com{image_url}"

        # Extract details like Industry, Location, Listing ID, Cash Flow
        # These are within description-name/description-value pairs
        description_items = listing.find_all('div')
        for item in description_items:
            name_span = item.find('span', class_='description-name')
            value_span = item.find('span', class_='description-value')

            if name_span and value_span:
                name = name_span.get_text(strip=True)
                value = value_span.get_text(strip=True)

                if name == "Industry:":
                    industry = value
                elif name == "Location:":
                    location = value
                elif name == "Listing ID:":
                    listing_id = value
                elif name == "Cash Flow:":
                    cash_flow = value

        # Extract Price (it has a different class for its spans)
        price_tag = listing.find('div', class_='listing-price')
        if price_tag:
            # Check for both 'price-description-name' and 'price-description-value'
            price_name = price_tag.find('span', class_='price-description-name')
            price_value = price_tag.find('span', class_='price-description-value')
            if price_name and price_value:
                price = price_value.get_text(strip=True)

        # Extract Excerpt/Description
        excerpt_tag = listing.find('div', class_='listing-excerpt')
        if excerpt_tag:
            excerpt = excerpt_tag.get_text(strip=True)

        # Skip if this URL already exists in history
        if learn_more_link in existing_urls:
            logging.debug("Skipping duplicate listing: %s", title)
            continue

        # Append the extracted data to the list
        posts.append({
            "listing_id": listing_id,
            "href": learn_more_link,
            "title": title,
            "image_url": image_url,
            "industry": industry,
            "location": location,
            "cash_flow": cash_flow,
            "price": price,
            "description": excerpt,
            "pub_date": "",  # No date available on this page
        })

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

    sold_keywords = config.get("sold_keywords", ["sold", "under contract", "closed"])

    for pdata in posts:
        title_lower = pdata['title'].lower()
        status = "Sold" if any(keyword in title_lower for keyword in sold_keywords) else "Available"

        # Prepare the record for the DataFrame
        records.append({
            "Broker Name": config["broker"],
            "Extraction Phase": config["phase"],
            "Link to Deal": pdata["href"],
            "Listing ID": pdata["listing_id"],
            "Published Date": pdata["pub_date"],
            "Opportunity/Listing Name": pdata["title"],
            "Opportunity/Listing Description": pdata["description"],
            "City": "check",  # Not available in current structure
            "State/Province": pdata["location"],
            "Country": "Canada",  # Ontario is in Canada
            "Business Type": pdata["industry"],
            "Asking Price": pdata["price"],
            "Revenue/Sales": "N/A",  # Not available in current structure
            "Down Payment": "check",  # Not available in current structure
            "EBITDA/Cash Flow/Net Income": pdata["cash_flow"],
            "Status": status,
            "Contact Name": config["contact_name"],
            "Contact Number": config["contact_number"],
            "Manual Validation": True,
        })

    # Return as a DataFrame
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# CSV Export Function
# ---------------------------------------------------------------------------
def save_to_csv(df: pd.DataFrame, filename: str = "ontario_businesses.csv") -> None:
    """
    Saves a DataFrame to a CSV file.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        filename (str): The name of the CSV file to save.
    """
    if df.empty:
        logging.warning("No data to save to CSV.")
        return

    try:
        df.to_csv(filename, index=False, encoding='utf-8')
        logging.info("Data successfully saved to %s", filename)
    except IOError as e:
        logging.error("Error saving data to CSV file %s: %s", filename, e)


# ---------------------------------------------------------------------------
# Example usage: Run this script standalone to test scraping
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Default configuration
    default_config: Dict[str, Any] = {
        "listing_url": "https://www.ontario-commercial.com/businesses-for-sale/",
        "base_url": "https://www.ontario-commercial.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        "history": pd.DataFrame(),
        "broker": "",          # Will be overridden
        "phase": "",           # Will be overridden
        "contact_name": "",    # Will be overridden
        "contact_number": "",  # Will be overridden
    }

    # User-provided overrides
    overrides = {
        "broker": "Ontario Commercial",
        "phase": "initial",
        "contact_name": "N/A",  # Contact info not available on listing page
        "contact_number": "N/A",  # Contact info not available on listing page
    }

    # Merge defaults and overrides
    config = {**default_config, **overrides}

    # Run the scraper and show results
    df = scrape(config)
    print(f"Found {len(df)} business listings.")
    print(df.head())
    
    # Save to CSV
    if not df.empty:
        save_to_csv(df, "ontario_businesses_group.csv")
    else:
        print("No business listings were extracted to save.")