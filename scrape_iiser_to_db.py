#!/usr/bin/env python3
"""
Official IISER Cutoff Scraper and Database Ingestion Script
Fetches closing ranks directly from official IISER admission portal:
https://www.iiseradmission.in/pages/closing_ranks.html
Stores scraped data in the dedicated iiser.db database.
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.services.scrape_iiser_official import run_iiser_scraper, DEFAULT_IISER_URL

def main():
    parser = argparse.ArgumentParser(description="Scrape official IISER closing ranks into dedicated iiser.db")
    parser.add_argument("--url", default=DEFAULT_IISER_URL, help="URL to official IISER closing ranks page")
    parser.add_argument("--year", type=int, default=2024, help="Admission year (default: 2024)")
    args = parser.parse_args()

    print(f"[*] Starting IISER Scraper for year {args.year} from: {args.url}")
    result = run_iiser_scraper(url=args.url, default_year=args.year)
    if result.get("success"):
        print(f"[+] SUCCESS: {result.get('message')}")
        print(f"[+] Total cutoffs: {result.get('records_count')} across {result.get('total_rounds')} rounds in {result.get('duration_seconds')}s")
        sys.exit(0)
    else:
        print(f"[!] FAILED: {result.get('message') or result.get('error')}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
