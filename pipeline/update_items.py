import pipeline.items as items
import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def main():
    df = pd.DataFrame(items.getAllItemDetailsDict())

    supabase_api_key = os.environ["SUPABASE_API_KEY"]
    
    supabase_link = os.environ["SUPABASE_ADMIN_URL"]

    db = create_client(supabase_link,supabase_api_key)
    db.table("items").upsert(
        df.to_dict(orient="records"),
        on_conflict="item_id"
    ).execute()

if __name__ == "__main__":
    main()