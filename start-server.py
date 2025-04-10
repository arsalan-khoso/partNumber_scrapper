#!/usr/bin/env python
"""
Start the Auto Glass Part Scraper application with waitress.
"""

import os
from waitress import serve
from app import app

# Set port (default to 1056)
port = int(os.environ.get('PORT', 1056))

print(f"Starting server on port {port}...")
serve(app, host='0.0.0.0', port=port, threads=8)