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
# Helper Functions: Business listing extraction and parsing
# ---------------------------------------------------------------------------

def is_likely_title(line: str) -> bool:
    """Determine if a line is likely a business title"""
    line = line.strip()
    
    # Skip obvious non-titles
    if (line.upper().startswith(('LOCATION:', 'PRICE:', 'ASK:', 'REVENUE:', 'F20', '-')) or
        len(line) < 10 or
        re.match(r'^\d+', line) or
        '$' in line):
        return False
    
    # Positive indicators
    business_keywords = [
        'COMPANY', 'BUSINESS', 'CORP', 'INC', 'LLC', 'LTD', 'SERVICES', 'GROUP',
        'CENTRE', 'CENTER', 'STORE', 'SHOP', 'DISTRIBUTION', 'MANUFACTURING',
        'RETAIL', 'WHOLESALE', 'CLEANING', 'MEDICAL', 'AUTOMOTIVE', 'FIRE',
        'SAFETY', 'ENGINEERING', 'TRANSPORT', 'PLUMBING', 'HVAC', 'PET'
    ]
    
    line_upper = line.upper()
    has_business_keyword = any(keyword in line_upper for keyword in business_keywords)
    
    # Check if it's all caps (common for titles on this site)
    is_caps = line.isupper()
    
    # Check length and word count
    word_count = len(line.split())
    
    return (has_business_keyword or is_caps) and 2 <= word_count <= 10

def clean_title(title: str) -> str:
    """Clean and format business title"""
    # Remove SOLD! prefix if present
    title = re.sub(r'^SOLD!\s*-?\s*', '', title, flags=re.IGNORECASE)
    
    # Convert to title case if all caps
    if title.isupper():
        title = title.title()
        # Fix common acronyms
        title = re.sub(r'\bHvac\b', 'HVAC', title)
        title = re.sub(r'\bGta\b', 'GTA', title)
        title = re.sub(r'\bPet\b', 'Pet', title)
    
    return title.strip()

def extract_location(text: str) -> str:
    """Extract location information"""
    patterns = [
        r'Location:\s*([^\n]+)',
        r'LOCATION:\s*([^\n]+)',
        r'Location\s*([^\n]+)',
        r'LOCATION\s*([^\n]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Clean up location
            location = re.sub(r'^:?\s*', '', location)
            return location
    
    return ""

def extract_price(text: str) -> str:
    """Extract price/asking price information"""
    patterns = [
        r'Price:\s*\$\s*([\d,]+)',
        r'PRICE:\s*\$\s*([\d,]+)',
        r'Ask:\s*\$\s*([\d,]+)',
        r'ASK:\s*\$\s*([\d,]+)',
        r'Asking:\s*\$\s*([\d,]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"${match.group(1)}"
    
    return ""

def extract_financial_metric(text: str, metric: str) -> str:
    """Extract specific financial metrics"""
    patterns = {
        'revenue': [
            r'F20\d{2}\s+revenue.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)',
            r'revenue.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)',
            r'sales.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)'
        ],
        'ebitda': [
            r'EBITDA.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)',
            r'ebitda.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)'
        ],
        'cash flow': [
            r'normalized cash flow.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)',
            r'cash flow.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)'
        ],
        'sde': [
            r'SDE.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)',
            r'Seller\'s Discretionary Earnings.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)',
            r'discretionary earnings.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)'
        ],
        'gross profit': [
            r'gross profit.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)'
        ],
        'ebit': [
            r'EBIT.*?\$\s*([\d,]+(?:\.\d+)?(?:mm|k)?)'
        ]
    }
    
    metric_key = metric.lower()
    if metric_key not in patterns:
        return ""
    
    for pattern in patterns[metric_key]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1)
            return format_financial_value(value)
    
    return ""

def format_financial_value(value: str) -> str:
    """Format financial values consistently"""
    if 'mm' in value.lower():
        return f"${value}"
    elif 'k' in value.lower():
        return f"${value}"
    else:
        return f"${value}"

def extract_year_founded(text: str) -> str:
    """Extract founding year"""
    patterns = [
        r'founded in (\d{4})',
        r'established in (\d{4})',
        r'incorporated in.*?(\d{4})',
        r'founded.*?(\d{4})',
        r'established.*?(\d{4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return ""

def extract_employees(text: str) -> str:
    """Extract employee information"""
    employee_info = []
    
    # Look for various employee mentions
    patterns = [
        r'(\d+)\s+(?:F/T|full.time|full-time)\s+employees?',
        r'(\d+)\s+(?:P/T|part.time|part-time)\s+employees?',
        r'staff.*?(\d+)',
        r'employees?.*?(\d+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            employee_info.append(match)
    
    if employee_info:
        return ', '.join(set(employee_info)) + ' employees'
    
    return ""

def infer_industry(title: str) -> str:
    """Infer industry from business title"""
    title_upper = title.upper()
    
    industry_keywords = {
        'Manufacturing': ['MANUFACTURING', 'ENGINEERING', 'MACHINERY'],
        'Medical/Healthcare': ['MEDICAL', 'HEALTHCARE', 'HOME CARE', 'HEALTH'],
        'Fire Safety': ['FIRE', 'SAFETY', 'SPRINKLER', 'PROTECTION'],
        'Automotive': ['AUTOMOTIVE', 'AUTO'],
        'Cleaning/Janitorial': ['CLEANING', 'JANITORIAL'],
        'Distribution': ['DISTRIBUTION', 'WHOLESALE', 'SUPPLY'],
        'Retail': ['RETAIL', 'STORE', 'SHOP', 'LAUNDROMAT', 'CAFE'],
        'Transportation': ['TRANSPORT', 'FLEET'],
        'Construction/Trade': ['PLUMBING', 'HVAC', 'CONSTRUCTION'],
        'Services': ['SERVICES', 'COMPANY'],
        'Food/Hospitality': ['RESTAURANT', 'CAFE', 'FOOD'],
        'Pet Services': ['PET'],
        'Technology': ['TECH', 'SOFTWARE', 'IT'],
        'Agriculture': ['AGRICULTURAL', 'FARM']
    }
    
    for industry, keywords in industry_keywords.items():
        if any(keyword in title_upper for keyword in keywords):
            return industry
    
    return "Other"

def create_description(text: str) -> str:
    """Create a brief description from key points"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Find the most descriptive lines (avoiding financial data and addresses)
    descriptive_lines = []
    for line in lines:
        line_clean = line.strip()
        if (len(line_clean) > 30 and 
            not line_clean.upper().startswith(('LOCATION:', 'PRICE:', 'F20', 'ASK:', '-')) and
            not re.search(r'\$[\d,]+', line_clean) and
            not line_clean.isupper()):
            descriptive_lines.append(line_clean)
            if len(descriptive_lines) >= 2:  # Limit to first 2 descriptive lines
                break
    
    return ' '.join(descriptive_lines)[:300] + "..." if descriptive_lines else ""

def parse_listing_block(block: str) -> Dict[str, Any]:
    """Parse individual business listing block"""
    lines = [line.strip() for line in block.split('\n') if line.strip()]
    
    if not lines:
        return None
    
    listing = {
        "Title": "",
        "Status": "",
        "Location": "",
        "Price": "",
        "Revenue": "",
        "Cash Flow": "",
        "EBITDA": "",
        "SDE": "",
        "Gross Profit": "",
        "EBIT": "",
        "Description": "",
        "Year Founded": "",
        "Employees": "",
        "Industry": ""
    }
    
    # Extract status from first line if present
    first_line = lines[0].upper()
    status_keywords = ['NEW', 'SOLD', 'IN NEGOTIATION', 'SUSPENDED']
    
    start_index = 0
    for keyword in status_keywords:
        if first_line.startswith(keyword):
            listing['Status'] = keyword
            start_index = 1
            break
        elif keyword in first_line:
            listing['Status'] = keyword
            # Don't increment start_index as title might be on same line
            break
    
    # Extract title - usually the first or second line depending on status
    title_found = False
    for i in range(start_index, min(len(lines), 3)):
        line = lines[i].strip()
        if is_likely_title(line):
            listing['Title'] = clean_title(line)
            title_found = True
            break
    
    if not title_found and lines:
        # Fallback: use first substantial line as title
        for line in lines[:3]:
            if len(line) > 10 and not line.upper().startswith(('LOCATION:', 'PRICE:', 'ASK:')):
                listing['Title'] = clean_title(line)
                break
    
    # Join all lines for comprehensive text search
    full_text = ' '.join(lines)
    
    # Extract location
    listing['Location'] = extract_location(full_text)
    
    # Extract price/ask
    listing['Price'] = extract_price(full_text)
    
    # Extract financial metrics
    listing['Revenue'] = extract_financial_metric(full_text, 'revenue')
    listing['Cash Flow'] = extract_financial_metric(full_text, 'cash flow')
    listing['EBITDA'] = extract_financial_metric(full_text, 'ebitda')
    listing['SDE'] = extract_financial_metric(full_text, 'sde')
    listing['Gross Profit'] = extract_financial_metric(full_text, 'gross profit')
    listing['EBIT'] = extract_financial_metric(full_text, 'ebit')
    
    # Extract other details
    listing['Year Founded'] = extract_year_founded(full_text)
    listing['Employees'] = extract_employees(full_text)
    listing['Industry'] = infer_industry(listing['Title'])
    
    # Create description from key points
    listing['Description'] = create_description(full_text)
    
    return listing

# ---------------------------------------------------------------------------
# Helper Function: Fetch listing data from webpage
# ---------------------------------------------------------------------------

def get_list_links(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Fetch listing page and extract business data from Business Buy Sell Ontario.

    Returns:
        A list of dictionaries, one per listing, each containing title, financials,
        and other metadata.
    """
    listing_url = config["listing_url"]
    headers = config.get("headers", {})
    history = config.get("history", pd.DataFrame())
    sold_keywords = config.get("sold_keywords", ["sold", "under contract", "closed", "contingent"])

    try:
        response = requests.get(listing_url, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully fetched listing page: {response.status_code}")
        logger.info(f"Page size: {len(response.text):,} characters")
    except Exception as e:
        logger.error("Failed to fetch listing page: %s", e)
        return []

    existing_urls = set(history.get("Link to Deal", []).dropna()) if not history.empty else set()
    
    # Extract business listings from the specific website structure
    soup = BeautifulSoup(response.text, "html.parser")
    text_content = soup.get_text()
    
    # Split the content by common separators used on this site
    # The site uses underscores and multiple lines as separators
    raw_blocks = re.split(r'_{5,}|_{3,}\n', text_content)
    
    posts = []
    
    for idx, block in enumerate(raw_blocks):
        block = block.strip()
        if len(block) < 50:  # Skip very short blocks
            continue
            
        listing = parse_listing_block(block)
        if listing and listing.get('Title'):
            # Generate listing ID
            listing_id = f"BBSO-{idx+1:03d}"
            
            # Parse location for city/state if possible
            location_parts = listing["Location"].split(",") if listing["Location"] else ["", ""]
            city = location_parts[0].strip() if len(location_parts) > 0 else "N/A"
            state = location_parts[1].strip() if len(location_parts) > 1 else "Ontario"
            
            # Determine status
            status = listing.get('Status', 'Available')
            if not status or status == "":
                status = "Available"
                # Check if sold based on keywords
                full_text = listing.get('Description', '') + ' ' + listing.get('Title', '')
                for keyword in sold_keywords:
                    if keyword.lower() in full_text.lower():
                        status = "Sold"
                        break
            
            posts.append({
                "listing_id": listing_id,
                "href": config["listing_url"],  # Main page URL since individual URLs not available
                "title": listing["Title"],
                "price_box": listing["Price"] if listing["Price"] else "N/A",
                "pub_date": "",  # Not available on this site
                "description": listing["Description"],
                "location": listing["Location"] if listing["Location"] else "N/A",
                "city": city,
                "state": state,
                "business_type_tag": listing["Industry"],
                "revenue_span": listing["Revenue"] if listing["Revenue"] else "N/A",
                "ebitda_span": listing["EBITDA"] if listing["EBITDA"] else "N/A",
                "cash_flow_span": listing["Cash Flow"] if listing["Cash Flow"] else "N/A",
                "sde_span": listing["SDE"] if listing["SDE"] else "N/A",
                "gross_profit_span": listing["Gross Profit"] if listing["Gross Profit"] else "N/A",
                "ebit_span": listing["EBIT"] if listing["EBIT"] else "N/A",
                "year_founded": listing["Year Founded"] if listing["Year Founded"] else "N/A",
                "employees": listing["Employees"] if listing["Employees"] else "N/A",
                "status": status,
            })

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
        records.append({
            "Broker Name": config["broker"],
            "Extraction Phase": config["phase"],
            "Link to Deal": pdata["href"],
            "Listing ID": pdata["listing_id"],
            "Published Date": pdata["pub_date"],
            "Opportunity/Listing Name": pdata["title"],
            "Opportunity/Listing Description": pdata["description"],
            "City": pdata["city"],
            "State/Province": pdata["state"],
            "Country": "Canada",
            "Business Type": pdata["business_type_tag"],
            "Asking Price": pdata["price_box"],
            "Revenue/Sales": pdata["revenue_span"],
            "Down Payment": "N/A",  # Not extracted from this site
            "EBITDA/Cash Flow/Net Income": pdata["ebitda_span"],
            "Cash Flow": pdata["cash_flow_span"],
            "SDE": pdata["sde_span"],
            "Gross Profit": pdata["gross_profit_span"],
            "EBIT": pdata["ebit_span"],
            "Year Founded": pdata["year_founded"],
            "Employees": pdata["employees"],
            "Status": pdata["status"],
            "Contact Name": config["contact_name"],
            "Contact Number": config["contact_number"],
            "Manual Validation": True,
        })

    return pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Display and Analysis Functions
# ---------------------------------------------------------------------------

def display_comprehensive_summary(df: pd.DataFrame) -> None:
    """Display comprehensive summary of extracted data"""
    print(f"\n📊 EXTRACTION SUMMARY:")
    print(f"✅ Successfully extracted {len(df)} unique business listings")
    print(f"📍 Listings with locations: {df['City'].notna().sum()}")
    print(f"💰 Listings with prices: {(df['Asking Price'] != 'N/A').sum()}")
    print(f"📈 Listings with revenue data: {(df['Revenue/Sales'] != 'N/A').sum()}")
    print(f"💵 Listings with EBITDA data: {(df['EBITDA/Cash Flow/Net Income'] != 'N/A').sum()}")
    print(f"💸 Listings with Cash Flow data: {(df['Cash Flow'] != 'N/A').sum()}")
    print(f"🏪 Listings with SDE data: {(df['SDE'] != 'N/A').sum()}")
    print(f"📊 Listings with Gross Profit data: {(df['Gross Profit'] != 'N/A').sum()}")
    print(f"💼 Listings with EBIT data: {(df['EBIT'] != 'N/A').sum()}")
    
    # Status breakdown
    status_counts = df['Status'].value_counts()
    print(f"\n📋 STATUS BREAKDOWN:")
    for status, count in status_counts.items():
        print(f"   {status}: {count}")
    
    # Industry breakdown
    industry_counts = df['Business Type'].value_counts()
    print(f"\n🏭 INDUSTRY BREAKDOWN:")
    for industry, count in industry_counts.head(5).items():
        print(f"   {industry}: {count}")

def display_sample_listings(df: pd.DataFrame, num_samples: int = 3) -> None:
    """Display detailed sample listings"""
    print(f"\n📋 DETAILED SAMPLE LISTINGS:")
    print("=" * 100)
    
    for i in range(min(num_samples, len(df))):
        row = df.iloc[i]
        print(f"\n{i+1}. {row['Opportunity/Listing Name']}")
        
        # Display all non-empty fields
        for key, value in row.items():
            if key != 'Opportunity/Listing Name' and value and str(value) != 'N/A' and str(value) != 'nan':
                print(f"   {key}: {value}")
        print("-" * 80)

def display_financial_summary(df: pd.DataFrame) -> None:
    """Show financial summary for listings with complete data"""
    financial_complete = df[
        (df['Asking Price'] != 'N/A') & 
        (df['Revenue/Sales'] != 'N/A') & 
        (df['EBITDA/Cash Flow/Net Income'] != 'N/A')
    ]
    
    if len(financial_complete) > 0:
        print(f"\n💰 FINANCIAL SUMMARY ({len(financial_complete)} listings with complete financial data):")
        print("=" * 60)
        for idx, row in financial_complete.head(3).iterrows():
            print(f"\n• {row['Opportunity/Listing Name']}")
            print(f"  Price: {row['Asking Price']}")
            print(f"  Revenue: {row['Revenue/Sales']}")
            print(f"  EBITDA: {row['EBITDA/Cash Flow/Net Income']}")
            if row['SDE'] != 'N/A':
                print(f"  SDE: {row['SDE']}")

# ---------------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Business Buy Sell Ontario specific config
    bbso_config = {
        "listing_url": "https://businessbuysellontario.com/businesses-for-sale",
        "base_url": "https://businessbuysellontario.com",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
        "history": pd.DataFrame(),
        "broker": "Business Buy Sell Ontario",
        "phase": "initial_extraction",
        "contact_name": "Business Buy Sell Ontario Team",
        "contact_number": "Contact via website",
        "sold_keywords": ["sold", "under contract", "closed", "contingent", "suspended", "in negotiation"],
    }

    try:
        logger.info("🔍 Starting Business Buy Sell Ontario scraping...")
        df = scrape(bbso_config)
        
        if not df.empty:
            print(f"\n🎉 Successfully scraped {len(df)} listings!")
            
            # Display comprehensive analysis
            display_comprehensive_summary(df)
            display_sample_listings(df)
            display_financial_summary(df)
            
            # Save to CSV
            output_file = "keystonebussinessbrokers.csv"
            df.to_csv(output_file, index=False)
            print(f"\n💾 Complete data saved to '{output_file}'")
            
            print(f"\n🎉 Scraping completed successfully!")
            print(f"📊 Total listings extracted: {len(df)}")
            
        else:
            print("❌ No business listings found")
            print("The website structure may have changed or there are no listings available.")
            
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        print(f"❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()