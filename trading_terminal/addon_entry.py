"""Home Assistant add-on entry point: add-on options -> environment variables -> start the app.

The app reads its settings from environment variables (the same names as in .env), so each
option is exported upper-cased, e.g. finnhub_api_key -> FINNHUB_API_KEY.
"""
import json
import os
import sys
from pathlib import Path

options_file = Path(os.getenv("OPTIONS_PATH", "/data/options.json"))
options = json.loads(options_file.read_text()) if options_file.exists() else {}
for key, value in options.items():
    if value not in (None, ""):
        os.environ[key.upper()] = str(value).lower() if isinstance(value, bool) else str(value)
os.environ.setdefault("DATA_DIR", "/data")
Path(os.environ["DATA_DIR"]).mkdir(parents=True, exist_ok=True)

port = os.getenv("PORT", "8501")
os.execvp(sys.executable, [
    sys.executable, "-m", "streamlit", "run", "app.py",
    "--server.address=0.0.0.0", f"--server.port={port}", "--server.headless=true",
    # Home Assistant's ingress proxy sits in front of the app and handles the login, so the
    # browser never talks to Streamlit directly; these checks would reject the proxied requests.
    "--server.enableCORS=false", "--server.enableXsrfProtection=false",
    "--browser.gatherUsageStats=false",
])
