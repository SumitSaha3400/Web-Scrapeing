import pandas as pd
import requests
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper Function: Fetch listing links
# ---------------------------------------------------------------------------

def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Fetch listing page and extract summary data for each listing from Coast Business Brokerage.

    Returns:
        A list of dictionaries, one per listing, each containing title, link,
        financials, and other metadata.
    """
    listing_url = config["listing_url"]
    headers = config.get("headers", {})
    history = config.get("history", pd.DataFrame())
    sold_keywords = config.get("sold_keywords", ["sold", "under contract", "closed", "contingent"])

    try:
        response = requests.get(listing_url, headers=headers, timeout=20)
        response.raise_for_status()
        logger.info(f"Successfully fetched listing page: {response.status_code}")
    except Exception as e:
        logger.error("Failed to fetch listing page: %s", e)
        return []

    existing_urls = set(history.get("Link to Deal", []).dropna()) if not history.empty else set()
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Look for listing containers - these may vary, so we'll try multiple selectors
    listings = []
    
    # Try different possible selectors for Coast Business Brokerage
    possible_selectors = [
        "div.listing-item",
        "div.business-listing",
        "div.listing",
        "article.listing",
        "div.property-item",
        "div.listing-card",
        ".listing-container",
        ".business-item"
    ]
    
    for selector in possible_selectors:
        listings = soup.select(selector)
        if listings:
            logger.info(f"Found {len(listings)} listings using selector: {selector}")
            break
    
    # If no specific listing containers found, look for common patterns
    if not listings:
        # Look for divs that might contain business listings
        listings = soup.find_all("div", class_=re.compile(r"listing|business|property", re.I))
        if not listings:
            # Fallback: look for any divs with links that might be listings
            listings = soup.find_all("div", string=re.compile(r"asking|price|revenue|cash flow", re.I))
        logger.info(f"Found {len(listings)} potential listings using fallback method")

    posts = []

    for idx, post in enumerate(listings):
        try:
            # Default values
            listing_id = f"CBB-{idx+1:03d}"  # Generate ID if not available
            title_only = "N/A"
            business_type = "N/A"
            description = "N/A"
            price = down_payment = cash_flow = gross_revenue = location = "N/A"
            status = "Available"

            # Extract title - look for headings or prominent text
            title_selectors = ["h1", "h2", "h3", "h4", ".title", ".listing-title", ".business-name"]
            for selector in title_selectors:
                title_element = post.find(selector)
                if title_element:
                    title_text = title_element.get_text(strip=True)
                    if title_text and len(title_text) > 3:  # Avoid empty or very short titles
                        title_only = title_text
                        break

            # Extract listing link
            link_element = post.find("a", href=True)
            if link_element:
                href = link_element["href"]
                if href.startswith("/"):
                    full_url = config["base_url"] + href
                elif href.startswith("http"):
                    full_url = href
                else:
                    full_url = config["base_url"] + "/" + href
            else:
                full_url = "N/A"

            # Extract business type - look for specific patterns
            post_text = post.get_text()
            business_type_patterns = [
                r"Business Type:\s*([^\n\r]+)",
                r"Industry:\s*([^\n\r]+)",
                r"Category:\s*([^\n\r]+)",
                r"Type:\s*([^\n\r]+)"
            ]
            
            for pattern in business_type_patterns:
                match = re.search(pattern, post_text, re.IGNORECASE)
                if match:
                    business_type = match.group(1).strip()
                    break

            # Extract financial information
            financial_patterns = {
                "price": [
                    r"Asking Price:\s*\$?([0-9,]+)",
                    r"Price:\s*\$?([0-9,]+)",
                    r"List Price:\s*\$?([0-9,]+)",
                    r"\$([0-9,]+)(?:\s*asking|\s*price)"
                ],
                "revenue": [
                    r"Gross Revenue:\s*\$?([0-9,]+)",
                    r"Revenue:\s*\$?([0-9,]+)",
                    r"Sales:\s*\$?([0-9,]+)",
                    r"Annual Revenue:\s*\$?([0-9,]+)"
                ],
                "cash_flow": [
                    r"Cash Flow:\s*\$?([0-9,]+)",
                    r"EBITDA:\s*\$?([0-9,]+)",
                    r"Net Income:\s*\$?([0-9,]+)",
                    r"Earnings:\s*\$?([0-9,]+)"
                ],
                "down_payment": [
                    r"Down Payment:\s*\$?([0-9,]+)",
                    r"Initial Investment:\s*\$?([0-9,]+)",
                    r"Minimum Down:\s*\$?([0-9,]+)"
                ]
            }

            for field, patterns in financial_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, post_text, re.IGNORECASE)
                    if match:
                        value = "$" + match.group(1)
                        if field == "price":
                            price = value
                        elif field == "revenue":
                            gross_revenue = value
                        elif field == "cash_flow":
                            cash_flow = value
                        elif field == "down_payment":
                            down_payment = value
                        break

            # Extract location
            location_patterns = [
                r"Location:\s*([^\n\r]+)",
                r"City:\s*([^\n\r]+)",
                r"Area:\s*([^\n\r]+)"
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, post_text, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    break

            # Extract description - look for paragraph text
            desc_element = post.find("p")
            if desc_element:
                desc_text = desc_element.get_text(strip=True)
                if len(desc_text) > 20:  # Ensure it's substantial
                    description = desc_text[:500]  # Limit length

            # Determine status
            post_text_lower = post_text.lower()
            for keyword in sold_keywords:
                if keyword in post_text_lower:
                    status = "Sold"
                    break

            # Extract listing ID from URL or title if available
            if "listing" in full_url:
                id_match = re.search(r"listing[/-](\d+)", full_url)
                if id_match:
                    listing_id = f"CBB-{id_match.group(1)}"

            posts.append({
                "listing_id": listing_id,
                "href": full_url,
                "title": title_only,
                "price_box": price,
                "pub_date": "",  # Coast Business Brokerage may not show publish dates on listing page
                "description": description,
                "location": location,
                "business_type_tag": business_type,
                "revenue_span": gross_revenue,
                "ebitda_span": cash_flow,
                "down_payment": down_payment,
                "status": status,
            })

        except Exception as e:
            logger.warning(f"Error processing listing {idx}: {e}")
            continue

    logger.info("Extracted %d listings", len(posts))
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
        # Parse location for city/state if possible
        location_parts = pdata["location"].split(",") if pdata["location"] != "N/A" else ["", ""]
        city = location_parts[0].strip() if len(location_parts) > 0 else "N/A"
        state = location_parts[1].strip() if len(location_parts) > 1 else "N/A"

        records.append({
            "Broker Name": config["broker"],
            "Extraction Phase": config["phase"],
            "Link to Deal": pdata["href"],
            "Listing ID": pdata["listing_id"],
            "Published Date": pdata["pub_date"],
            "Opportunity/Listing Name": pdata["title"],
            "Opportunity/Listing Description": pdata["description"],
            "City": city,
            "State/Province": state,
            "Country": "United States",
            "Business Type": pdata["business_type_tag"],
            "Asking Price": pdata["price_box"],
            "Revenue/Sales": pdata["revenue_span"],
            "Down Payment": pdata["down_payment"],
            "EBITDA/Cash Flow/Net Income": pdata["ebitda_span"],
            "Status": pdata["status"],
            "Contact Name": config["contact_name"],
            "Contact Number": config["contact_number"],
            "Manual Validation": True,
        })

    return pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Coast Business Brokerage specific config
    coast_config = {
        "listing_url": "https://coastbusinessbrokerage.com/businesses-for-sale/",
        "base_url": "https://coastbusinessbrokerage.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        },
        "history": pd.DataFrame(),
        "broker": "Coast Business Brokerage",
        "phase": "initial_extraction",
        "contact_name": "Coast Business Brokerage Team",
        "contact_number": "Contact via website",
        "sold_keywords": ["sold", "under contract", "closed", "contingent", "pending"],
    }

    try:
        logger.info("Starting Coast Business Brokerage scraping...")
        df = scrape(coast_config)
        
        if not df.empty:
            print(f"\nSuccessfully scraped {len(df)} listings!")
            print("\nFirst few records:")
            print(df.head())
            
            # Save to CSV
            output_file = "coast_business_listings.csv"
            df.to_csv(output_file, index=False)
            print(f"\nData saved to {output_file}")
            
            # Display summary
            print(f"\nSummary:")
            print(f"Total listings: {len(df)}")
            print(f"Available: {len(df[df['Status'] == 'Available'])}")
            print(f"Sold: {len(df[df['Status'] == 'Sold'])}")
            
        else:
            print("No listings found. The website structure may have changed.")
            
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        print(f"Error: {e}")