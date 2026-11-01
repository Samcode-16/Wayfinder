import os

# Offline-friendly defaults for tests: no keys, short timeouts -> demo providers + graceful fallbacks.
os.environ.setdefault("HTTP_TIMEOUT", "2")
for k in ("GROQ_API_KEY", "GOOGLE_API_KEY", "HF_TOKEN", "SERPAPI_API_KEY"):
    os.environ[k] = ""
