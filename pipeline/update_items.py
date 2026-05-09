import pipeline.items as items
import pandas as pd
from supabase import create_client

def main():
    df = pd.DataFrame(items.getAllItemDetailsDict())
    print(df.head())

    with open('pipeline/supabase_api_key.txt','r') as file:
        supabase_api_key = file.read()
    
    with open('pipeline/supabase_admin_link.txt','r') as file:
        supabase_link = file.read()

    db = create_client(supabase_link,supabase_api_key)
    db.table("items").upsert(
        df.to_dict(orient="records"),
        on_conflict="item_id"
    ).execute()

if __name__ == "__main__":
    main()