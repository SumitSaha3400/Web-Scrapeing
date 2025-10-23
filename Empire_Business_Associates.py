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
    
    # Get the main content area
    content_text = soup.get_text()
    
    # Split the content into sections - each business listing appears to be separated
    business_pattern = r"([A-Z\s]+(?:FIRM|COMPANY|CONTRACTOR|BUSINESS|MANUFACTURING|TRUCKING|REPAIR))\s*([^\n]*(?:\n[^\n]*)*?)(?=(?:[A-Z\s]+(?:FIRM|COMPANY|CONTRACTOR|BUSINESS|MANUFACTURING|TRUCKING|REPAIR))|$)"
    
    # Also look for SOLD listings
    sold_pattern = r"-------SOLD-------\s*([A-Z\s]+(?:FIRM|COMPANY|CONTRACTOR|BUSINESS|MANUFACTURING|TRUCKING|REPAIR))\s*([^\n]*(?:\n[^\n]*)*?)(?=(?:-------SOLD-------|[A-Z\s]+(?:FIRM|COMPANY|CONTRACTOR|BUSINESS|MANUFACTURING|TRUCKING|REPAIR))|$)"
    
    listing_cards = []
    
    # Find all active listings
    for match in re.finditer(business_pattern, content_text):
        business_type = match.group(1).strip()
        description = match.group(2).strip()
        
        # Skip if it's actually a section header or generic text
        if business_type in ["THINKING OF SELLING", "LOOKING FOR A BUSINESS", "EMAIL ALERT"]:
            continue
            
        listing_cards.append({
            'business_type': business_type,
            'description': description,
            'is_sold': False
        })
    
    # Find all SOLD listings
    for match in re.finditer(sold_pattern, content_text):
        business_type = match.group(1).strip()
        description = match.group(2).strip()
        
        listing_cards.append({
            'business_type': business_type,
            'description': description,
            'is_sold': True
        })
    
    logging.info("Found %d potential listing cards", len(listing_cards))

    # Loop over each listing card
    for post in listing_cards:
        # Initialize default values
        ad_id = "N/A"
        business_type = post.get('business_type', 'N/A')
        description = post.get('description', 'N/A')
        is_sold = post.get('is_sold', False)
        price_match = None
        revenue_match = None
        ebitda_match = None
        contact_name = "N/A"
        contact_number = "N/A"
        location = "Cleveland, OH"  # Default location based on the page
        title = business_type

        # Extract price information from description
        price_patterns = [
            r"Sales\s*\$\s*([\d,]+)",
            r"Price\s*\$\s*([\d,]+)",
            r"Asking\s*\$\s*([\d,]+)",
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, description, re.IGNORECASE)
            if price_match:
                break

        # Extract revenue information
        revenue_patterns = [
            r"Revenue[:\s]*\$\s*([\d,]+)",
            r"Annual\s*Revenue[:\s]*\$\s*([\d,]+)",
            r"Gross\s*Revenue[:\s]*\$\s*([\d,]+)",
        ]
        for pattern in revenue_patterns:
            revenue_match = re.search(pattern, description, re.IGNORECASE)
            if revenue_match:
                break

        # Look for "Contact Now" or similar links in the original HTML
        contact_links = soup.find_all("a", string=re.compile("Contact", re.IGNORECASE))
        full_url = None
        
        if contact_links:
            # Use the first contact link found
            link = contact_links[0]
            href = link.get("href", "").strip()
            if href:
                if href.startswith("/"):
                    full_url = config["base_url"].rstrip("/") + href
                elif href.startswith("http"):
                    full_url = href
                else:
                    full_url = config["base_url"].rstrip("/") + "/" + href

        # Skip if already processed
        if full_url and full_url in existing_urls:
            continue

        # Try to get more details if we have a contact URL
        if full_url:
            try:
                detail_resp = requests.get(full_url, headers=headers, timeout=15)
                detail_resp.raise_for_status()
                detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                detail_text = detail_soup.get_text()

                # Extract contact information from detail page
                contact_patterns = [
                    r"Contact[:\s]*([^\n]+)",
                    r"Broker[:\s]*([^\n]+)",
                    r"Agent[:\s]*([^\n]+)",
                ]
                for pattern in contact_patterns:
                    match = re.search(pattern, detail_text, re.IGNORECASE)
                    if match:
                        contact_name = match.group(1).strip()
                        break

                # Extract phone number
                phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", detail_text)
                if phone_match:
                    contact_number = phone_match.group(0)

                # Extract EBITDA/Cash Flow
                ebitda_patterns = [
                    r"EBITDA[:\s]*\$\s*([\d,]+)",
                    r"Cash\s*Flow[:\s]*\$\s*([\d,]+)",
                    r"Net\s*Income[:\s]*\$\s*([\d,]+)",
                ]
                for pattern in ebitda_patterns:
                    ebitda_match = re.search(pattern, detail_text, re.IGNORECASE)
                    if ebitda_match:
                        break

            except Exception as e:
                logging.warning("Failed to fetch detail page for %s: %s", full_url, e)

        # Format extracted values
        price_formatted = f"${price_match.group(1)}" if price_match else "N/A"
        revenue_formatted = f"${revenue_match.group(1)}" if revenue_match else "N/A"
        ebitda_formatted = f"${ebitda_match.group(1)}" if ebitda_match else "N/A"

        # Append the extracted data to the list
        posts.append(
            {
                "listing_id": ad_id,
                "href": full_url if full_url else "N/A",
                "title": title,
                "price_box": price_formatted,
                "pub_date": "",  # No date available on this page
                "description": description,
                "location": location,
                "business_type": business_type,
                "revenue": revenue_formatted,
                "ebitda": ebitda_formatted,
                "contact_name": contact_name,
                "contact_number": contact_number,
                "is_sold": is_sold,  # Add sold status flag
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

    sold_keywords = config.get("sold_keywords", ["sold", "under contract", "closed"])

    for pdata in posts:
        title_lower = pdata['title'].lower()
        # Use the is_sold flag from card parsing if available, otherwise check keywords
        if 'is_sold' in pdata:
            status = "Sold" if pdata['is_sold'] else "Available"
        else:
            status = "Sold" if any(keyword in title_lower for keyword in sold_keywords) else "Available"

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
        "listing_url": "https://www.businessbrokerclevelandoh.com/businesses-currently-for-sale-cleveland-oh",
        "base_url": "https://www.businessbrokerclevelandoh.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        },
        "history": pd.DataFrame(),
        "broker": "",          # Will be overridden
        "phase": "",           # Will be overridden
        "contact_name": "",    # Will be overridden
        "contact_number": "",  # Will be overridden
    }

    # User-provided overrides
    overrides = {
        "broker": "Empire Business Advisors",
        "phase": "initial",
        "contact_name": "Empire Business Advisor",
        "contact_number": "555-0123",
    }

    # Merge defaults and overrides
    config = {**default_config, **overrides}

    # Run the scraper and show results
    try:
        df = scrape(config)
        print(f"Successfully scraped {len(df)} listings")
        print("\nFirst few listings:")
        print(df.head())
        
        # Save to CSV for inspection
        df.to_csv("empire_businesses_assiociate.csv", index=False)
        print("\nData saved to 'empire_businesses_listings.csv'")
        
    except Exception as e:
        logging.error("Error running scraper: %s", e)
        print(f"Error: {e}")