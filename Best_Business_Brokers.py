# import requests
# from bs4 import BeautifulSoup
# import pandas as pd
# import time
# import csv
# from urllib.parse import urljoin
# import re

# class B3BrokersScraper:
#     def __init__(self):
#         self.base_url = "https://b3brokers.com"
#         self.session = requests.Session()
#         # Set headers to mimic a real browser
#         self.session.headers.update({
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
#             'Accept-Language': 'en-US,en;q=0.5',
#             'Accept-Encoding': 'gzip, deflate',
#             'Connection': 'keep-alive',
#         })
#         # Track seen listing IDs to prevent duplicates
#         self.seen_listing_ids = set()
        
#     def get_page_content(self, url):
#         """Fetch page content with error handling"""
#         try:
#             response = self.session.get(url, timeout=30)
#             response.raise_for_status()
#             return response.text
#         except requests.RequestException as e:
#             print(f"Error fetching {url}: {e}")
#             return None
    
#     def clean_text(self, text):
#         """Clean and normalize text"""
#         if not text:
#             return ""
#         return re.sub(r'\s+', ' ', text.strip())
    
#     def extract_price(self, price_text):
#         """Extract numeric price from price text"""
#         if not price_text:
#             return None
#         # Remove currency symbols and commas, extract numbers
#         price_match = re.search(r'[\$]?([\d,]+)', price_text.replace(',', ''))
#         if price_match:
#             return price_match.group(1).replace(',', '')
#         return price_text
    
#     def scrape_business_listings(self, url):
#         """Scrape business listings from the given URL"""
#         html_content = self.get_page_content(url)
#         if not html_content:
#             print(f"Failed to fetch content from {url}")
#             return []
        
#         soup = BeautifulSoup(html_content, 'html.parser')
#         listings = []
        
#         # Find all listing boxes
#         listing_boxes = soup.find_all('div', class_='listing-box')
        
#         print(f"Found {len(listing_boxes)} business listings on this page")
        
#         for idx, listing_box in enumerate(listing_boxes, 1):
#             try:
#                 listing_data = self.extract_listing_data(listing_box)
#                 if listing_data:
#                     # Check for duplicates using listing_id
#                     listing_id = listing_data.get('listing_id')
#                     if listing_id and listing_id in self.seen_listing_ids:
#                         print(f"Skipping duplicate listing {idx}: {listing_data.get('title', 'Unknown')} (ID: {listing_id})")
#                         continue
                    
#                     # If no listing_id, use URL as fallback identifier
#                     listing_url = listing_data.get('listing_url')
#                     if not listing_id and listing_url and listing_url in self.seen_listing_ids:
#                         print(f"Skipping duplicate listing {idx}: {listing_data.get('title', 'Unknown')} (URL duplicate)")
#                         continue
                    
#                     # Add to seen set
#                     if listing_id:
#                         self.seen_listing_ids.add(listing_id)
#                     elif listing_url:
#                         self.seen_listing_ids.add(listing_url)
                    
#                     listings.append(listing_data)
#                     print(f"Added new listing {idx}: {listing_data.get('title', 'Unknown')}")
#             except Exception as e:
#                 print(f"Error extracting listing {idx}: {e}")
#                 continue
        
#         return listings
    
#     def extract_listing_data(self, listing_box):
#         """Extract data from a single listing box"""
#         data = {}
        
#         # Extract title and link
#         title_element = listing_box.find('div', class_='listing-title')
#         if title_element:
#             title_link = title_element.find('a')
#             if title_link:
#                 data['title'] = self.clean_text(title_link.get_text())
#                 data['listing_url'] = urljoin(self.base_url, title_link.get('href', ''))
        
#         # Extract price
#         price_element = listing_box.find('span', class_='price-description-value')
#         if price_element:
#             data['price'] = self.clean_text(price_element.get_text())
#             data['price_numeric'] = self.extract_price(data['price'])
        
#         # Extract business details
#         description_elements = listing_box.find_all('div')
#         for element in description_elements:
#             text = element.get_text(strip=True)
#             if 'Industry:' in text:
#                 industry_span = element.find('span', class_='description-value')
#                 if industry_span:
#                     data['industry'] = self.clean_text(industry_span.get_text())
#             elif 'Location:' in text:
#                 location_span = element.find('span', class_='description-value')
#                 if location_span:
#                     data['location'] = self.clean_text(location_span.get_text())
#             elif 'Listing ID:' in text:
#                 id_span = element.find('span', class_='description-value')
#                 if id_span:
#                     data['listing_id'] = self.clean_text(id_span.get_text())
#             elif 'Total Sales:' in text:
#                 sales_span = element.find('span', class_='description-value')
#                 if sales_span:
#                     data['total_sales'] = self.clean_text(sales_span.get_text())
        
#         # Extract image URL
#         image_element = listing_box.find('img')
#         if image_element:
#             img_src = image_element.get('data-src') or image_element.get('src')
#             if img_src and not img_src.startswith('data:'):
#                 data['image_url'] = urljoin(self.base_url, img_src)
        
#         # Extract description/excerpt
#         excerpt_element = listing_box.find_next_sibling('div', class_='listing-excerpt')
#         if excerpt_element:
#             data['description'] = self.clean_text(excerpt_element.get_text())
        
#         # Extract status (Available, New, Under Contract, etc.)
#         status_elements = listing_box.find_all('div', class_=['available-button', 'new-button'])
#         if status_elements:
#             data['status'] = self.clean_text(status_elements[0].get_text())
        
#         return data if data else None
    
#     def scrape_all_pages(self, base_url, max_pages=None):
#         """Scrape all pages of listings"""
#         all_listings = []
#         page = 1
#         consecutive_empty_pages = 0
        
#         while True:
#             if max_pages and page > max_pages:
#                 break
                
#             # Construct URL for current page
#             if page == 1:
#                 url = base_url
#             else:
#                 url = f"{base_url}?wpv_paged={page}"
            
#             print(f"\nScraping page {page}: {url}")
            
#             listings = self.scrape_business_listings(url)
            
#             # If no new listings found, increment counter
#             if not listings:
#                 consecutive_empty_pages += 1
#                 print(f"No new listings found on page {page}")
                
#                 # Stop if we've hit 2 consecutive empty pages
#                 if consecutive_empty_pages >= 2:
#                     print(f"Stopping after {consecutive_empty_pages} consecutive empty pages")
#                     break
#             else:
#                 consecutive_empty_pages = 0  # Reset counter
#                 all_listings.extend(listings)
#                 print(f"Added {len(listings)} new listings from page {page}")
            
#             print(f"Total unique listings collected so far: {len(all_listings)}")
            
#             page += 1
#             time.sleep(2)  # Be respectful to the server
        
#         return all_listings
    
#     def remove_duplicates_from_list(self, listings):
#         """Remove duplicates from a list of listings based on listing_id or title"""
#         seen = set()
#         unique_listings = []
        
#         for listing in listings:
#             # Create a unique identifier
#             identifier = listing.get('listing_id') or listing.get('title') or listing.get('listing_url')
            
#             if identifier and identifier not in seen:
#                 seen.add(identifier)
#                 unique_listings.append(listing)
#             else:
#                 print(f"Removing duplicate: {listing.get('title', 'Unknown')}")
        
#         return unique_listings
    
#     def save_to_csv(self, listings, filename='b3_brokers_listings.csv'):
#         """Save listings to CSV file"""
#         if not listings:
#             print("No listings to save")
#             return
        
#         # Remove any remaining duplicates as a final check
#         unique_listings = self.remove_duplicates_from_list(listings)
        
#         # Get all unique keys from all listings
#         all_keys = set()
#         for listing in unique_listings:
#             all_keys.update(listing.keys())
        
#         fieldnames = ['title', 'price', 'price_numeric', 'industry', 'location', 
#                      'listing_id', 'total_sales', 'status', 'description', 
#                      'image_url', 'listing_url']
        
#         # Add any additional keys that might exist
#         for key in all_keys:
#             if key not in fieldnames:
#                 fieldnames.append(key)
        
#         with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
#             writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#             writer.writeheader()
#             for listing in unique_listings:
#                 writer.writerow(listing)
        
#         print(f"Saved {len(unique_listings)} unique listings to {filename}")
    
#     def save_to_excel(self, listings, filename='b3_brokers_listings.xlsx'):
#         """Save listings to Excel file"""
#         if not listings:
#             print("No listings to save")
#             return
        
#         # Remove any remaining duplicates as a final check
#         unique_listings = self.remove_duplicates_from_list(listings)
        
#         df = pd.DataFrame(unique_listings)
#         df.to_excel(filename, index=False)
#         print(f"Saved {len(unique_listings)} unique listings to {filename}")

# # Main execution
# def main():
#     scraper = B3BrokersScraper()
    
#     # URL to scrape
#     url = "https://b3brokers.com/businesses-for-sale/"
    
#     print("Starting B3 Brokers scraping...")
#     print(f"Target URL: {url}")
    
#     # Scrape all pages (set max_pages=None for all pages, or a number to limit)
#     listings = scraper.scrape_all_pages(url, max_pages=5)  # Limit to 5 pages for testing
    
#     if listings:
#         print(f"\nScraping completed! Found {len(listings)} total unique listings")
        
#         # Save to both CSV and Excel
#         scraper.save_to_csv(listings)
#         scraper.save_to_excel(listings)
        
#         # Display first few listings
#         print("\nFirst 3 listings:")
#         for i, listing in enumerate(listings[:3], 1):
#             print(f"\n--- Listing {i} ---")
#             for key, value in listing.items():
#                 print(f"{key}: {value}")
#     else:
#         print("No listings found!")

# if __name__ == "__main__":
#     main()



import pandas as pd
import requests
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from urllib.parse import urljoin
import time

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
    max_pages = config.get("max_pages", None)

    # Existing listing URLs (to avoid duplicates)
    existing_urls = set(history_df.get("Link to Deal", []))
    posts: List[Dict[str, str]] = []
    seen_listing_ids = set()
    
    page = 1
    consecutive_empty_pages = 0

    while True:
        if max_pages and page > max_pages:
            break
            
        # Construct URL for current page
        if page == 1:
            url = listing_url
        else:
            url = f"{listing_url}?wpv_paged={page}"
        
        logging.info("Scraping page %d: %s", page, url)

        # Fetch the HTML page
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except Exception as e:
            logging.error("Failed to fetch listing directory page %d: %s", page, e)
            consecutive_empty_pages += 1
            if consecutive_empty_pages >= 2:
                break
            page += 1
            continue

        # Parse the page with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        listing_cards = soup.find_all("div", class_="listing-box")
        logging.info("Found %d listing cards on page %d", len(listing_cards), page)

        page_listings = []

        # Loop over each listing card
        for post in listing_cards:
            try:
                # Initialize default values
                listing_id = "N/A"
                title = "N/A"
                full_url = None
                price = "N/A"
                price_numeric = None
                industry = "N/A"
                location = "N/A"
                total_sales = "N/A"
                status = "Available"
                description = "N/A"
                image_url = "N/A"

                # Extract title and link
                title_element = post.find("div", class_="listing-title")
                if title_element:
                    title_link = title_element.find("a")
                    if title_link:
                        title = _clean_text(title_link.get_text())
                        full_url = urljoin(config["base_url"], title_link.get("href", ""))

                # Extract price
                price_element = post.find("span", class_="price-description-value")
                if price_element:
                    price = _clean_text(price_element.get_text())
                    price_numeric = _extract_price(price)

                # Extract business details
                description_elements = post.find_all("div")
                for element in description_elements:
                    text = element.get_text(strip=True)
                    if "Industry:" in text:
                        industry_span = element.find("span", class_="description-value")
                        if industry_span:
                            industry = _clean_text(industry_span.get_text())
                    elif "Location:" in text:
                        location_span = element.find("span", class_="description-value")
                        if location_span:
                            location = _clean_text(location_span.get_text())
                    elif "Listing ID:" in text:
                        id_span = element.find("span", class_="description-value")
                        if id_span:
                            listing_id = _clean_text(id_span.get_text())
                    elif "Total Sales:" in text:
                        sales_span = element.find("span", class_="description-value")
                        if sales_span:
                            total_sales = _clean_text(sales_span.get_text())

                # Extract image URL
                image_element = post.find("img")
                if image_element:
                    img_src = image_element.get("data-src") or image_element.get("src")
                    if img_src and not img_src.startswith("data:"):
                        image_url = urljoin(config["base_url"], img_src)

                # Extract description/excerpt
                excerpt_element = post.find_next_sibling("div", class_="listing-excerpt")
                if excerpt_element:
                    description = _clean_text(excerpt_element.get_text())

                # Extract status
                status_elements = post.find_all("div", class_=["available-button", "new-button"])
                if status_elements:
                    status = _clean_text(status_elements[0].get_text())

                # Check for duplicates
                identifier = listing_id if listing_id != "N/A" else full_url
                if identifier and identifier in seen_listing_ids:
                    logging.debug("Skipping duplicate listing: %s", title)
                    continue
                
                if identifier:
                    seen_listing_ids.add(identifier)

                # Skip if URL already exists in history
                if full_url and full_url in existing_urls:
                    logging.debug("Skipping existing listing: %s", title)
                    continue

                # Append the extracted data to the list
                page_listings.append({
                    "listing_id": listing_id,
                    "href": full_url,
                    "title": title,
                    "price": price,
                    "price_numeric": price_numeric,
                    "industry": industry,
                    "location": location,
                    "total_sales": total_sales,
                    "status": status,
                    "description": description,
                    "image_url": image_url,
                })

            except Exception as e:
                logging.warning("Error extracting listing: %s", e)
                continue

        # Check if we found any listings on this page
        if not page_listings:
            consecutive_empty_pages += 1
            logging.info("No new listings found on page %d", page)
            
            # Stop if we've hit 2 consecutive empty pages
            if consecutive_empty_pages >= 2:
                logging.info("Stopping after %d consecutive empty pages", consecutive_empty_pages)
                break
        else:
            consecutive_empty_pages = 0  # Reset counter
            posts.extend(page_listings)
            logging.info("Added %d new listings from page %d", len(page_listings), page)

        logging.info("Total unique listings collected so far: %d", len(posts))
        
        page += 1
        time.sleep(2)  # Be respectful to the server

    logging.info("Extracted %d total listings from all pages.", len(posts))
    return posts


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def _clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.strip())


def _extract_price(price_text):
    """Extract numeric price from price text"""
    if not price_text:
        return None
    # Remove currency symbols and commas, extract numbers
    price_match = re.search(r'[\$]?([\d,]+)', price_text.replace(',', ''))
    if price_match:
        return price_match.group(1).replace(',', '')
    return price_text


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
        status = "Sold" if any(keyword in title_lower for keyword in sold_keywords) else pdata.get('status', 'Available')

        # Prepare the record for the DataFrame
        records.append({
            "Broker Name": config["broker"],
            "Extraction Phase": config["phase"],
            "Link to Deal": pdata["href"],
            "Listing ID": pdata["listing_id"],
            "Published Date": "",  # No date available on this page
            "Opportunity/Listing Name": pdata["title"],
            "Opportunity/Listing Description": pdata["description"],
            "City": "check",
            "State/Province": pdata["location"],
            "Country": "United States",
            "Business Type": pdata["industry"],
            "Asking Price": pdata["price"],
            "Revenue/Sales": pdata["total_sales"],
            "Down Payment": "check",
            "EBITDA/Cash Flow/Net Income": "N/A",
            "Status": status,
            "Contact Name": config["contact_name"],
            "Contact Number": config["contact_number"],
            "Manual Validation": True,
            "Image URL": pdata["image_url"],
            "Price Numeric": pdata["price_numeric"],
        })

    # Return as a DataFrame
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Helper Function: Save DataFrame to CSV
# ---------------------------------------------------------------------------
def save_to_csv(df: pd.DataFrame, filename: str = "b3_brokers_listings.csv") -> None:
    """
    Save the DataFrame to a CSV file.
    
    Args:
        df (pd.DataFrame): The DataFrame to save
        filename (str): The filename for the CSV file
    """
    if df.empty:
        logging.warning("No data to save to CSV")
        return
    
    try:
        df.to_csv(filename, index=False, encoding='utf-8')
        logging.info("Saved %d listings to %s", len(df), filename)
        print(f"Successfully saved {len(df)} listings to {filename}")
    except Exception as e:
        logging.error("Failed to save CSV file: %s", e)
        print(f"Error saving CSV file: {e}")


# ---------------------------------------------------------------------------
# Helper Function: Save DataFrame to Excel
# ---------------------------------------------------------------------------
def save_to_excel(df: pd.DataFrame, filename: str = "b3_brokers_listings.xlsx") -> None:
    """
    Save the DataFrame to an Excel file.
    
    Args:
        df (pd.DataFrame): The DataFrame to save
        filename (str): The filename for the Excel file
    """
    if df.empty:
        logging.warning("No data to save to Excel")
        return
    
    try:
        df.to_excel(filename, index=False)
        logging.info("Saved %d listings to %s", len(df), filename)
        print(f"Successfully saved {len(df)} listings to {filename}")
    except Exception as e:
        logging.error("Failed to save Excel file: %s", e)
        print(f"Error saving Excel file: {e}")


# ---------------------------------------------------------------------------
# Example usage: Run this script standalone to test scraping
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Default configuration
    default_config: Dict[str, Any] = {
        "listing_url": "https://b3brokers.com/businesses-for-sale/",
        "base_url": "https://b3brokers.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        },
        "history": pd.DataFrame(),
        "max_pages": 5,  # Limit to 5 pages for testing
        "broker": "",          # Will be overridden
        "phase": "",           # Will be overridden
        "contact_name": "",    # Will be overridden
        "contact_number": "",  # Will be overridden
    }

    # User-provided overrides
    overrides = {
        "broker": "B3 Brokers",
        "phase": "initial",
        "contact_name": "B3 Brokers Team",
        "contact_number": "555-B3BROKER",
    }

    # Merge defaults and overrides
    config = {**default_config, **overrides}

    # Run the scraper and show results
    print("Starting B3 Brokers scraping...")
    df = scrape(config)
    
    if not df.empty:
        print(f"\nScraping completed! Found {len(df)} total listings")
        print("\nFirst 3 listings:")
        print(df.head(3))
        
        # Save to both CSV and Excel formats
        save_to_csv(df, "best_bussiness_brokers.csv")
 
        
        # Display summary statistics
        print(f"\nSummary:")
        print(f"- Total listings: {len(df)}")
        print(f"- Unique brokers: {df['Broker Name'].nunique()}")
        print(f"- Available listings: {len(df[df['Status'] == 'Available'])}")
        print(f"- Sold listings: {len(df[df['Status'] == 'Sold'])}")
    else:
        print("No listings found!")