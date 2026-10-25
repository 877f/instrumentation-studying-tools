"""Gunicorn settings for hosting (Render etc.). Picked up automatically by `gunicorn app:app`."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
# One process so progress.json writes stay behind a single lock; threads handle concurrent requests.
workers = 1
threads = 4
