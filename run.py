#!/usr/bin/env python3
"""Smart Invoice Generator - Run Script"""
import uvicorn
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting Smart Invoice Generator on http://0.0.0.0:{port}")
    print("Admin login: mobile=01700000000 password=Admin@SmartInvoice2026")
    print("(Change via ADMIN_MOBILE and ADMIN_PASSWORD env vars)")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
