#!/usr/bin/env python3
"""
Official BITSAT Cutoff Scraper and Database Ingestion Script
Fetches cutoffs directly from official BITS Pilani admission portal:
https://admissions.bits-pilani.ac.in/FD/BITSAT_cutOffs.html
Stores scraped data in the dedicated bits.db database.
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.services.scrape_bits_official import run_bits_scraper, DEFAULT_BITS_URL, TARGET_YEARS

def main():
    parser = argparse.ArgumentParser(description="Scrape official BITSAT cutoffs into dedicated bits.db")
    parser.add_argument("--url", default=DEFAULT_BITS_URL, help="URL to official BITSAT cutoffs page")
    parser.add_argument("--years", nargs="+", default=TARGET_YEARS, help="Academic years to scrape (default: 2026-2027 2025-2026)")
    parser.add_argument("--wipe", action="store_true", help="Wipe bits.db database before scraping")
    args = parser.parse_args()

    if args.wipe:
        from app.bits_db import wipe_bits_database
        print("[*] Wiping existing BITS database...")
        wipe_bits_database()
        print("[+] BITS database wiped.")

    print(f"[*] Starting BITSAT Scraper for years {args.years} from: {args.url}")
    result = run_bits_scraper(url=args.url, target_years=args.years)
    if result.get("success"):
        print(f"[+] SUCCESS: {result.get('message')}")
        print(f"[+] Total cutoffs: {result.get('records_count')} across {result.get('years_count')} years in {result.get('duration_seconds')}s")
        sys.exit(0)
    else:
        print(f"[!] FAILED: {result.get('message') or result.get('error')}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
