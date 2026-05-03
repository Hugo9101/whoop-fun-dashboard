import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard import build_app

app = build_app()
server = app.server  # Vercel needs the Flask WSGI object
