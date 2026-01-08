import os
import mimetypes
from pathlib import Path
from backend.utils.logger import logger
from supabase import create_client, Client

class StorageManager:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials missing")
        self.supabase: Client = create_client(url, key)
        self.bucket_name = "cloned-sites"

    def upload_project_files(self, project_id: str, local_path: Path):
        """
        Uploads all files from local_path to Supabase Storage under project_id folder.
        Returns the public URL of the index.html.
        """
        uploaded_count = 0
        errors = []
        
        # Ensure path is Path object
        local_path = Path(local_path)
        
        if not local_path.exists():
            return {"error": "Local path does not exist"}

        # Walk through directory
        for file_path in local_path.rglob("*"):
            if file_path.is_file():
                # Calculate relative path for storage key
                # e.g. /Users/.../project_1/index.html -> project_1/index.html
                relative_path = file_path.relative_to(local_path)
                storage_path = f"{project_id}/{relative_path}"
                
                # Guess mime type
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "application/octet-stream"
                # Fix for CSS/JS sometimes guessing wrong on some systems
                if str(file_path).endswith(".css"): mime_type = "text/css"
                if str(file_path).endswith(".js"): mime_type = "application/javascript"
                if str(file_path).endswith(".html"): mime_type = "text/html"

                try:
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                        
                    # Upload (upsert=True to overwrite)
                    self.supabase.storage.from_(self.bucket_name).upload(
                        path=storage_path,
                        file=file_bytes,
                        file_options={"content-type": mime_type, "upsert": "true"}
                    )
                    uploaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to upload {relative_path}: {e}")
                    errors.append(str(e))

        # Get Public URL for index.html
        public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(f"{project_id}/index.html")
        
        return {
            "uploaded": uploaded_count,
            "errors": errors,
            "public_url": public_url
        }
