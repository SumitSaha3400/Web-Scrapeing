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
    soup = BeautifulSoup(response.content, "html.parser")
    listings = soup.find_all("div", class_="listing")
    logging.info("Found %d listing containers", len(listings))

    # Loop over each listing container
    for listing in listings:
        # Find all h3 tags (business titles) within each listing
        business_sections = listing.find_all("h3")
        
        for h3 in business_sections:
            if not h3.get_text(strip=True):  # Skip empty h3 tags
                continue
            
            # Initialize default values
            business_title = h3.get_text(strip=True)
            listing_number = "N/A"
            price = "N/A"
            net_income = "N/A"
            status = "Available"
            description = "N/A"
            
            # Look for status indicators (Under Contract, Sold, etc.)
            status_span = h3.find_next('span', style=lambda x: x and 'color: #ff0000' in x)
            if status_span:
                status_text = status_span.get_text(strip=True)
                status = "Sold" if "sold" in status_text.lower() or "contract" in status_text.lower() else "Available"
            
            # Find the paragraph with listing details
            detail_paragraph = h3.find_next('p')
            listing_details = []
            
            while detail_paragraph:
                text = detail_paragraph.get_text(strip=True)
                
                # Check if this paragraph contains listing number, price, and nets
                if 'Listing #' in text and ('Price:' in text or 'Nets' in text):
                    listing_details.append(text)
                    break
                
                # Move to next paragraph
                detail_paragraph = detail_paragraph.find_next_sibling('p')
                if not detail_paragraph or detail_paragraph.find_previous('h3') != h3:
                    break
            
            # Extract listing number, price, and net income
            if listing_details:
                details_text = ' '.join(listing_details)
                
                # Extract listing number
                listing_match = re.search(r'Listing #(\d+)', details_text)
                if listing_match:
                    listing_number = listing_match.group(1)
                
                # Extract price
                price_patterns = [
                    r'Price:\s*\$?([\d,]+)',
                    r'Price:\s*([^<\n]+)',
                    r'Price:\s*(.+?)(?:Nets|$)'
                ]
                for pattern in price_patterns:
                    price_match = re.search(pattern, details_text, re.IGNORECASE)
                    if price_match:
                        price = price_match.group(1).strip()
                        break
                
                # Extract net income
                net_patterns = [
                    r'Nets?\s*\$?([\d,]+)',
                    r'Nets?\s*([^<\n]+)'
                ]
                for pattern in net_patterns:
                    net_match = re.search(pattern, details_text, re.IGNORECASE)
                    if net_match:
                        net_income = net_match.group(1).strip()
                        break
            
            # Find business description
            desc_paragraph = h3.find_next('p')
            while desc_paragraph:
                text = desc_paragraph.get_text(strip=True)
                
                # Skip paragraphs with just listing details or status
                if ('Listing #' not in text and 
                    'Price:' not in text and 
                    'Nets' not in text and 
                    text not in ['Under Contract!', 'Sold!'] and
                    len(text) > 50):  # Get substantial description
                    description = text[:500] + "..." if len(text) > 500 else text
                    break
                
                desc_paragraph = desc_paragraph.find_next_sibling('p')
                if not desc_paragraph or desc_paragraph.find_previous('h3') != h3:
                    break
            
            # Only add if we have meaningful data
            if business_title and (listing_number != "N/A" or price != "N/A" or description != "N/A"):
                posts.append({
                    "listing_id": listing_number,
                    "href": config["listing_url"],  # Base URL since individual links not available
                    "title": business_title,
                    "price_box": price,
                    "pub_date": "",  # No date available
                    "description": description,
                    "location": "N/A",  # Not available in current structure
                    "business_type": "N/A",  # Not available in current structure
                    "revenue": "N/A",  # Not available in current structure
                    "ebitda": net_income,
                    "contact_name": "N/A",  # Not available in current structure
                    "contact_number": "N/A",  # Not available in current structure
                    "status": status,
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
        # Use the status from extraction or determine from title
        status = pdata.get('status', 'Available')
        if any(keyword in title_lower for keyword in sold_keywords):
            status = "Sold"

        # Prepare the record for the DataFrame
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

    # Return as a DataFrame
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Additional Helper Functions
# ---------------------------------------------------------------------------
def save_to_csv(df: pd.DataFrame, filename: str = 'Phil_Resse_Cbi.csv') -> None:
    """
    Save DataFrame to CSV file
    """
    if not df.empty:
        df.to_csv(filename, index=False, encoding='utf-8')
        logging.info("Data saved to %s", filename)
    else:
        logging.warning("No data to save")


def display_data(df: pd.DataFrame) -> None:
    """
    Display extracted data in a formatted way
    """
    if df.empty:
        logging.info("No data found")
        return
    
    for i, row in df.iterrows():
        print(f"\n{'='*60}")
        print(f"BUSINESS #{i+1}")
        print(f"{'='*60}")
        
        for key, value in row.items():
            if pd.notna(value) and value != "N/A":  # Only print non-empty values
                print(f"{key}: {value}")
        
        print(f"{'='*60}")


def scrape_from_html_file(file_path: str, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Scrape business listings from a local HTML file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Update config to use local content instead of URL
        local_config = config.copy()
        local_config["html_content"] = html_content
        
        return scrape_local_html(local_config)
        
    except Exception as e:
        logging.error("Error reading HTML file: %s", e)
        return pd.DataFrame()


def scrape_local_html(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Scrape from HTML content provided in config
    """
    html_content = config.get("html_content", "")
    if not html_content:
        logging.error("No HTML content provided")
        return pd.DataFrame()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    listings = soup.find_all('div', class_='listing')
    posts = []
    
    for listing in listings:
        business_sections = listing.find_all('h3')
        
        for h3 in business_sections:
            if not h3.get_text(strip=True):
                continue
            
            business_title = h3.get_text(strip=True)
            # ... (same extraction logic as in get_list_links)
            
            posts.append({
                "listing_id": "N/A",
                "href": "local_file",
                "title": business_title,
                "price_box": "N/A",
                "pub_date": "",
                "description": "N/A",
                "location": "N/A",
                "business_type": "N/A",
                "revenue": "N/A",
                "ebitda": "N/A",
                "contact_name": "N/A",
                "contact_number": "N/A",
                "status": "Available",
            })
    
    # Convert to DataFrame using the same structure
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
            "Status": pdata["status"],
            "Contact Name": pdata["contact_name"],
            "Contact Number": pdata["contact_number"],
            "Manual Validation": True,
        })
    
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Example usage: Run this script standalone to test scraping
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Default configuration
    default_config: Dict[str, Any] = {
        "listing_url": "https://www.philsellsbiz.com/listings/",
        "base_url": "https://www.philsellsbiz.com",
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
        "broker": "Phil Sells Biz",
        "phase": "initial",
        "contact_name": "Phil",
        "contact_number": "555-1234",
    }

    # Merge defaults and overrides
    config = {**default_config, **overrides}

    print("Starting web scraping...")
    print(f"Target URL: {config['listing_url']}")
    print("-" * 50)

    # Run the scraper and show results
    try:
        df = scrape(config)
        
        if not df.empty:
            print(f"\nSuccessfully extracted {len(df)} business listings!")
            
            # Display the data
            display_data(df)
            
            # Save to CSV
            save_to_csv(df)
            
            # Display summary statistics
            print(f"\nSUMMARY:")
            print(f"Total businesses scraped: {len(df)}")
            print(f"Businesses with status: {len(df[df['Status'] != 'Available'])}")
            print(f"Businesses with prices: {len(df[df['Asking Price'] != 'N/A'])}")
            print(f"Businesses with EBITDA: {len(df[df['EBITDA/Cash Flow/Net Income'] != 'N/A'])}")
        else:
            print("No data could be extracted. Please check the website structure or your internet connection.")
            
    except Exception as e:
        logging.error("Scraping failed: %s", e)
        print("Scraping failed. Check logs for details.")

    # Uncomment the line below to scrape from a local HTML file instead
    # df = scrape_from_html_file('paste.txt', config)