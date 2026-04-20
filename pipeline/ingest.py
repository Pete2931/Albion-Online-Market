import requests
import argparse
from datetime import datetime, timedelta, timezone
import pipeline.items as items

def main():
    parser = argparse.ArgumentParser(description = "AlbionEdge Data Pipeline")
    parser.add_argument(
        "--backfill",
        type = int,
        default = None,
        help = "Number of days to backfill (e.g. 90) + today"
    )
    parser.add_argument(
        "--dry-run",
        action = "store_true",
        help = "Only Fetch Data, but doesn't write to database"
    )
    args = parser.parse_args()

    today = datetime.now(timezone.utc)

    if args.backfill:
        start_date = (today - timedelta(days=args.backfill)).strftime("%Y-%m-%d")
    else:
        start_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    
    end_date = today.strftime("%Y-%m-%d")
    
    item_list = items.getAllItemsList()
    item_s = ",".join(item_list)
    api_construct = f"https://west.albion-online-data.com/api/v2/stats/history/{item_s}.json?date={start_date}&end_date={end_date}&time-scale=24"

if __name__ == "__main__":
    main()