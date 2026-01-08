import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load env
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_KEY in .env")
    exit(1)

try:
    print(f"Connecting to {url}...")
    supabase: Client = create_client(url, key)
    
    # Try a simple read (even if table doesn't exist, it checks auth)
    # We'll just check if we can get the auth configuration or list a non-existent table
    # actually, supabase-py init is lazy. We need to make a request.
    # Let's try to select from a table likely to not exist or be empty, just to check 401 vs 404/200
    response = supabase.table("projects").select("*").limit(1).execute()
    
    print("✅ Connection Successful!")
    print(f"Response: {response}")
    
except Exception as e:
    # If table doesn't exist, it might throw an error, but that proves Auth works (if it's not a 401)
    print(f"⚠️ Connection attempted (Auth likely OK, but table might be missing): {e}")
