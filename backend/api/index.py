
from backend.main import app

# Vercel requires a handler variable, but FastAPI works with the app instance properly configured
# ensuring main.py is in PYTHONPATH or importable
