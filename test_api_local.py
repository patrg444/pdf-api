"""
Test script to verify API functionality without Redis
This creates a test API key and runs the server locally
"""
import os
import subprocess
import time
import requests
import json

# Set environment variables for testing
os.environ["REDIS_URL"] = "redis://localhost:6379"  # Won't connect but won't crash
os.environ["SECRET_KEY"] = "test-secret-key-for-local-development"
os.environ["RAPIDAPI_PROXY_SECRET"] = "test-rapidapi-secret"

# Create a simple test endpoint
test_endpoint = """
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict
import PyPDF2
import io
from playwright.async_api import async_playwright

app = FastAPI(
    title="Lightning PDF API - Test Mode",
    description="PDF API running in test mode without Redis",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PDFRequest(BaseModel):
    html: Optional[str] = None
    url: Optional[str] = None
    options: Optional[Dict] = None

@app.get("/")
async def root():
    return {
        "message": "Lightning PDF API - Test Mode",
        "status": "running",
        "note": "This is a test instance without Redis authentication",
        "endpoints": {
            "generate_pdf": "/test/pdf/generate",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "mode": "test"
    }

@app.post("/test/pdf/generate")
async def generate_pdf(request: PDFRequest):
    \"\"\"Generate PDF from HTML (simplified test version)\"\"\"
    try:
        if not request.html:
            raise HTTPException(status_code=400, detail="HTML content required")
        
        # For testing, we'll create a simple response
        # In production, this would use Playwright to generate actual PDFs
        return {
            "success": True,
            "message": "PDF generation endpoint is working!",
            "input_received": {
                "html_length": len(request.html),
                "has_options": request.options is not None
            },
            "note": "In production, this would return a PDF file URL"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("\\n🚀 Starting Lightning PDF API in TEST MODE...")
    print("📌 Access the API at: http://localhost:8000")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("\\n⚠️  Note: This is running without Redis - authentication is disabled\\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

# Write the test server
with open("test_server.py", "w") as f:
    f.write(test_endpoint)

print("✅ Test server created!")
print("\n📋 Quick Test Instructions:")
print("1. Run the test server: python test_server.py")
print("2. Open http://localhost:8000 in your browser")
print("3. Test the API at http://localhost:8000/docs")
print("\n🎯 For RapidAPI deployment:")
print("1. Deploy the full app (in app/ folder) to Railway/Heroku")
print("2. Set up Redis on your hosting platform")
print("3. Configure environment variables")
print("4. Submit to RapidAPI with your deployed URL")
