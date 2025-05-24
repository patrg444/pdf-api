from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import asyncio
import secrets
import time
from datetime import datetime, timedelta
import redis
import stripe
from playwright.async_api import async_playwright
import os
from io import BytesIO
import json

# Initialize FastAPI
app = FastAPI(
    title="Lightning PDF API",
    description="Generate PDFs from HTML, URLs, or templates in milliseconds",
    version="1.0.0"
)

# CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_...")

# Initialize services
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
stripe.api_key = STRIPE_SECRET_KEY

# Request/Response Models
class PDFRequest(BaseModel):
    html: Optional[str] = Field(None, description="HTML content to convert")
    url: Optional[str] = Field(None, description="URL to convert")
    template: Optional[str] = Field(None, description="Template name to use")
    data: Optional[Dict] = Field(None, description="Data for template")
    options: Optional[Dict] = Field(default_factory=dict, description="PDF options")

class APIKeyCreate(BaseModel):
    email: str
    plan: str = Field("basic", description="basic, pro, or enterprise")

# Rate limiting
async def check_rate_limit(api_key: str) -> bool:
    """Check if API key has exceeded rate limit"""
    key = f"rate_limit:{api_key}"
    current = redis_client.get(key)
    
    if current is None:
        redis_client.setex(key, 3600, 1)  # 1 hour expiry
        return True
    
    count = int(current)
    plan = redis_client.hget(f"api_key:{api_key}", "plan") or "basic"
    
    limits = {"basic": 100, "pro": 1000, "enterprise": 10000}
    limit = limits.get(plan, 100)
    
    if count >= limit:
        return False
    
    redis_client.incr(key)
    return True

# API Key validation
async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Verify API key exists and is valid"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    exists = redis_client.exists(f"api_key:{x_api_key}")
    if not exists:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check rate limit
    if not await check_rate_limit(x_api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Update last used
    redis_client.hset(f"api_key:{x_api_key}", "last_used", datetime.now().isoformat())
    redis_client.hincrby(f"api_key:{x_api_key}", "requests", 1)
    
    return x_api_key

# PDF Generation Engine
async def generate_pdf(content: str, options: dict = None) -> bytes:
    """Generate PDF using Playwright"""
    options = options or {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Load content
        if content.startswith(('http://', 'https://')):
            await page.goto(content, wait_until='networkidle')
        else:
            await page.set_content(content, wait_until='networkidle')
        
        # PDF options
        pdf_options = {
            'format': options.get('format', 'A4'),
            'print_background': options.get('print_background', True),
            'margin': options.get('margin', {'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'}),
            'scale': options.get('scale', 1),
        }
        
        if 'header_template' in options:
            pdf_options['display_header_footer'] = True
            pdf_options['header_template'] = options['header_template']
        
        if 'footer_template' in options:
            pdf_options['display_header_footer'] = True
            pdf_options['footer_template'] = options['footer_template']
        
        # Generate PDF
        pdf_bytes = await page.pdf(**pdf_options)
        await browser.close()
        
        return pdf_bytes

# Templates
TEMPLATES = {
    "invoice": """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { display: flex; justify-content: space-between; margin-bottom: 40px; }
            .invoice-title { font-size: 32px; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            .total { font-size: 20px; font-weight: bold; text-align: right; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <div class="invoice-title">INVOICE</div>
                <div>Invoice #: {{invoice_number}}</div>
                <div>Date: {{date}}</div>
            </div>
            <div style="text-align: right;">
                <div><strong>{{company_name}}</strong></div>
                <div>{{company_address}}</div>
            </div>
        </div>
        
        <div style="margin-bottom: 30px;">
            <strong>Bill To:</strong><br>
            {{customer_name}}<br>
            {{customer_address}}
        </div>
        
        <table>
            <tr>
                <th>Description</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Total</th>
            </tr>
            {{#items}}
            <tr>
                <td>{{description}}</td>
                <td>{{quantity}}</td>
                <td>${{price}}</td>
                <td>${{total}}</td>
            </tr>
            {{/items}}
        </table>
        
        <div class="total">
            Total: ${{total_amount}}
        </div>
    </body>
    </html>
    """,
    
    "report": """
    <html>
    <head>
        <style>
            body { font-family: Georgia, serif; margin: 40px; line-height: 1.6; }
            h1 { color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }
            h2 { color: #666; margin-top: 30px; }
            .meta { color: #999; font-style: italic; margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <h1>{{title}}</h1>
        <div class="meta">{{author}} | {{date}}</div>
        
        {{#sections}}
        <h2>{{heading}}</h2>
        <p>{{content}}</p>
        {{/sections}}
    </body>
    </html>
    """
}

def render_template(template_name: str, data: dict) -> str:
    """Simple template rendering"""
    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Template '{template_name}' not found")
    
    # Simple mustache-style replacement
    for key, value in data.items():
        if isinstance(value, list):
            # Handle lists (simplified)
            list_html = ""
            for item in value:
                item_html = template
                for k, v in item.items():
                    item_html = item_html.replace(f"{{{{{k}}}}}", str(v))
                list_html += item_html
            template = template.replace(f"{{{{#{key}}}}}", "").replace(f"{{{{/{key}}}}}", "")
        else:
            template = template.replace(f"{{{{{key}}}}}", str(value))
    
    return template

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Lightning PDF API",
        "docs": "/docs",
        "pricing": {
            "basic": "$29/month - 100 PDFs",
            "pro": "$99/month - 1,000 PDFs",
            "enterprise": "$299/month - 10,000 PDFs"
        }
    }

@app.post("/api/v1/pdf")
async def create_pdf(
    request: PDFRequest,
    api_key: str = Depends(verify_api_key)
):
    """Generate a PDF from HTML, URL, or template"""
    try:
        # Determine content source
        if request.html:
            content = request.html
        elif request.url:
            content = request.url
        elif request.template and request.data:
            content = render_template(request.template, request.data)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Provide either 'html', 'url', or 'template' with 'data'"
            )
        
        # Generate PDF
        pdf_bytes = await generate_pdf(content, request.options)
        
        # Return PDF
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=document.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/templates")
async def list_templates(api_key: str = Depends(verify_api_key)):
    """List available templates"""
    return {
        "templates": list(TEMPLATES.keys()),
        "details": {
            "invoice": "Professional invoice template",
            "report": "Business report template"
        }
    }

@app.post("/api/v1/keys")
async def create_api_key(request: APIKeyCreate):
    """Create a new API key (called after Stripe payment)"""
    # Generate unique API key
    api_key = f"pdf_{'live' if STRIPE_SECRET_KEY.startswith('sk_live') else 'test'}_{secrets.token_urlsafe(32)}"
    
    # Store in Redis
    redis_client.hset(f"api_key:{api_key}", mapping={
        "email": request.email,
        "plan": request.plan,
        "created": datetime.now().isoformat(),
        "requests": 0,
        "active": "true"
    })
    
    return {
        "api_key": api_key,
        "plan": request.plan,
        "email": request.email
    }

@app.get("/api/v1/usage")
async def check_usage(api_key: str = Depends(verify_api_key)):
    """Check API key usage"""
    key_data = redis_client.hgetall(f"api_key:{api_key}")
    
    return {
        "plan": key_data.get("plan", "basic"),
        "requests": int(key_data.get("requests", 0)),
        "created": key_data.get("created"),
        "last_used": key_data.get("last_used")
    }

# Stripe Webhook
@app.post("/stripe/webhook")
async def stripe_webhook(request: dict):
    """Handle Stripe webhooks for automatic API key creation"""
    # Verify webhook signature (simplified for demo)
    
    if request.get("type") == "checkout.session.completed":
        session = request["data"]["object"]
        
        # Create API key for the customer
        email = session.get("customer_email")
        plan = session.get("metadata", {}).get("plan", "basic")
        
        if email:
            result = await create_api_key(APIKeyCreate(email=email, plan=plan))
            
            # TODO: Send API key via email
            print(f"Created API key for {email}: {result['api_key']}")
    
    return {"received": True}

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)