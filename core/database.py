
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env vars explicitly from root
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

def get_supabase_client() -> Client:
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print(f"⚠️ Error: Missing Supabase Credentials. URL defined: {bool(url)}, Key defined: {bool(key)}")
        # Return None or raise? Let's trying to return generic client but it will likely fail if no key
    
    return create_client(url, key)

# Singleton instance for easy import
db = get_supabase_client()
