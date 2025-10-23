import pandas as pd
import logging
import importlib
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("scraper_debug.log"),
        logging.StreamHandler()
    ]
)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
}

def load_scraper(site_name):
    try:
        module_name = f"scrapers.{site_name.lower().split('&')[0].strip().replace(' ', '_')}"
        scraper_module = importlib.import_module(module_name)
        return scraper_module.scrape
    except (ModuleNotFoundError, AttributeError) as e:
        logging.error(f"{module_name}.py not found for {site_name}: {e}")
        return None

def main():
    sitelist_path = "sitelist.csv"
    master_db_path = "master_db.xlsx"
    now = datetime.now()
    monthly_output_path = f"{now.strftime('%Y-%m')}_listings.xlsx"

    # Load sitelist
    try:
        sitelist = pd.read_csv(sitelist_path)
    except Exception as e:
        logging.critical(f"Failed to load sitelist: {e}")
        return

    # Load master db
    try:
        master_db = pd.read_excel(master_db_path)
    except FileNotFoundError:
        logging.warning(f"{master_db_path} not found. Starting with empty master db.")
        master_db = pd.DataFrame()

    # Primary keys for identifying unique listings
    primary_keys = ["Link to Deal", "Broker Name", "Listing ID", "Published Date"]

    new_rows = []
    status_updates = []
    update_counts = []
    token = now.strftime('%b-%y')

    for idx, row in sitelist.iterrows():
        if str(row['to_scrape']).strip().upper() != "TRUE":
            update_counts.append("0")
            status_updates.append((idx, "skipped"))
            continue

        site_name = row["Site Name"]
        site_url = row["Listing URL"]
        base_url = row["Base URL"]
        contact = row["Contact Name"]
        contact_num = row["Contact Number"]
        mode = row.get("mode", "default")

        logging.info(f"Scraping {site_name} ({site_url})")

        scraper_func = load_scraper(site_name)
        if scraper_func is None:
            status_updates.append((idx, "scraper_not_found"))
            update_counts.append("0")
            continue

        # Filter master db history for this broker
        if not master_db.empty:
            history = master_db[master_db["Broker Name"] == site_name][primary_keys]
        else:
            history = pd.DataFrame(columns=primary_keys)

        try:
            config: Dict[str, Any] = {
                "listing_url": site_url,
                "base_url": base_url,
                "headers": headers,
                "history": history,
                "mode": mode,
                "broker": contact,
                "phase": token,
                "contact_name": contact,
                "contact_number": contact_num,
            }

            new_listings = scraper_func(config)
            if isinstance(new_listings, pd.DataFrame) and not new_listings.empty:
                logging.debug(f"{site_name}: Scraped {len(new_listings)} listings")
                new_rows.append(new_listings)
                status_updates.append((idx, "success"))
                update_counts.append(len(new_listings))
            else:
                logging.warning(f"{site_name}: No new listings or invalid result")
                status_updates.append((idx, "no_new_listings"))
                update_counts.append("0")
        except Exception as e:
            logging.exception(f"Exception during scraping {site_name}: {e}")
            status_updates.append((idx, "exception"))
            update_counts.append("0")

    # Save new listings for the month (only if new rows exist)
    if new_rows:
        all_new = pd.concat(new_rows, ignore_index=True)
        all_new.to_excel(monthly_output_path, index=False)
        logging.info(f"Written {len(all_new)} new listings to {monthly_output_path}")

        # Update master db: add new listings and drop duplicates
        combined_master = pd.concat([master_db, all_new], ignore_index=True)
        updated_master = combined_master.drop_duplicates(subset=primary_keys, keep='last')

        try:
            updated_master.to_excel(master_db_path, index=False)
            logging.info(f"Updated master database written to {master_db_path}")
        except Exception as e:
            logging.error(f"Failed to write master database: {e}")
    else:
        logging.info("No new listings this month. Master DB not updated.")

    # Update sitelist statuses and counts
    for idx, status in status_updates:
        sitelist.at[idx, "Status"] = status
        sitelist.at[idx, "Count"] = int(update_counts[idx])
    sitelist.to_csv(sitelist_path, index=False)
    logging.info("Updated sitelist with statuses and counts.")

if __name__ == "__main__":
    main()
