import requests
import os
import argparse
from datetime import datetime, timedelta, timezone
import pipeline.items as items
from supabase import create_client
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

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

    end_date = today.strftime("%Y-%m-%d")
    
    item_list = items.getAllItemsList()
    item_s = ",".join(item_list)

    if args.backfill:
        start_date = (today - timedelta(days=args.backfill)).strftime("%Y-%m-%d")
        api_url_construct = f"https://west.albion-online-data.com/api/v2/stats/history/{item_s}.json?date={start_date}&end_date={end_date}&time-scale=24"
    else:
        start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        api_url_construct = f"https://west.albion-online-data.com/api/v2/stats/history/{item_s}.json?date={start_date}&end_date={end_date}&time-scale=6"

    supabase_api_key = os.environ["SUPABASE_API_KEY"]
    
    response = requests.get(api_url_construct)
    if response.status_code != 200:
        raise ValueError(f"Failed with status code : {response.status_code}")

    response_json = response.json()

    final_dict = {
        "item_id" : [],
        "city" : [],
        "quality" : [],
        "timestamp" : [],
        "avg_price" : [],
        "item_count" : []
    }

    for cat in response_json:
        for t in cat['data']:
            final_dict['item_id'].append(cat['item_id'])
            final_dict['city'].append(cat['location'])
            final_dict['quality'].append(cat['quality'])
            final_dict['timestamp'].append(t['timestamp'])
            final_dict['avg_price'].append(t['avg_price'])
            final_dict['item_count'].append(t['item_count'])
    
    df = pd.DataFrame(final_dict)

    supabase_link = os.environ["SUPABASE_ADMIN_URL"]

    if not args.dry_run:
        db = create_client(supabase_link,supabase_api_key)
        db.table("price_history").upsert(
            df.to_dict(orient="records"),
            on_conflict="item_id,city,quality,timestamp"
        ).execute()


if __name__ == "__main__":
    main()