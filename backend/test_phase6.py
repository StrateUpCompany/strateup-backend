import asyncio
import os
import uuid
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv()

from backend.core.supabase_manager import SupabaseManager
from backend.core.storage import StorageManager
from backend.core.security_scanner import SecurityScanner

async def run_tests():
    print("🚀 Starting Phase 6 Verification Suite...")
    
    # 1. Initialize Managers
    try:
        db = SupabaseManager()
        storage = StorageManager()
        scanner = SecurityScanner()
        print("✅ Managers Initialized")
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    # 2. Test DB Operations
    print("\n📊 Testing Supabase Database...")
    test_uuid = str(uuid.uuid4())[:8]
    project_data = {
        "url": f"https://example.com/{test_uuid}",
        "mode": "test",
        "local_path": f"/tmp/test_project_{test_uuid}",
        "status": "pending"
    }
    
    try:
        # Create
        pid = db.create_project(
            url=project_data['url'],
            mode=project_data['mode'],
            local_path=project_data['local_path']
        )
        print(f"   ✅ Created Project ID: {pid}")
        
        # Read
        p = db.get_by_id(pid)
        assert p['url'] == project_data['url']
        print("   ✅ Read Project Verified")
        
        # Update
        db.update_project(pid, status="verified")
        p2 = db.get_by_id(pid)
        assert p2['status'] == "verified"
        print("   ✅ Update Project Verified")
        
    except Exception as e:
        print(f"   ❌ DB Tests Failed: {e}")
        return

    # 3. Test Storage Upload
    print("\n📦 Testing Supabase Storage...")
    try:
        # Create dummy file
        local_dir = Path(f"/tmp/test_project_{test_uuid}")
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "index.html").write_text("<h1>Hello Cloud</h1>")
        
        # Upload
        print(f"   Uploading from {local_dir}...")
        result = storage.upload_project_files(str(pid), local_dir)
        
        if result['errors']:
            print(f"   ⚠️ Upload Warnings: {result['errors']}")
        
        url = result['public_url']
        print(f"   ✅ Uploaded. Public URL: {url}")
        
        # Verify URL reachable
        r = requests.get(url)
        if r.status_code == 200 and "Hello Cloud" in r.text:
            print("   ✅ Public URL Verified (HTTP 200 & Content Match)")
        else:
            print(f"   ❌ Public URL Validaton Failed: {r.status_code}")
            
    except Exception as e:
        print(f"   ❌ Storage Tests Failed: {e}")
    finally:
        # Cleanup local
        import shutil
        if local_dir.exists():
            shutil.rmtree(local_dir)

    # 4. Test Security Scanner
    print("\n🛡️ Testing Security Scanner...")
    try:
        scan_res = scanner.scan("https://example.com")
        print(f"   ✅ Create Scan Complete. Score: {scan_res['score']}")
        assert 'headers' in scan_res
        assert 'issues' in scan_res
        print("   ✅ Scan Structure Valid")
    except Exception as e:
        print(f"   ❌ Security Scan Failed: {e}")

    # 5. Cleanup DB
    print("\n🧹 Cleanup...")
    try:
        db.delete_project(pid)
        print("   ✅ Test Project Deleted")
    except Exception as e:
        print(f"   ⚠️ Cleanup Failed: {e}")

    print("\n🎉 All Tests Completed!")

if __name__ == "__main__":
    asyncio.run(run_tests())
