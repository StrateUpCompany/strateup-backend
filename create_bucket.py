import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

bucket_name = "projects"

try:
    print(f"Creating bucket '{bucket_name}'...")
    # Try different signatures
    try:
        res = supabase.storage.create_bucket(bucket_name, options={"public": True})
        print(f"Bucket created (Method A): {res}")
    except Exception as e:
        print(f"Method A failed: {e}")
        res = supabase.storage.create_bucket(bucket_name, public=True)
        print(f"Bucket created (Method B): {res}")
except Exception as e:
    print(f"Error creating bucket: {e}")

# Verify
try:
    buckets = supabase.storage.list_buckets()
    exists = any(b.name == bucket_name for b in buckets)
    print(f"Bucket '{bucket_name}' exists: {exists}")
except Exception as e:
    print(f"List error: {e}")
