import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard import build_app

dash_app = build_app()
app = dash_app.server  # must be named 'app' for Vercel's Python runtime
