from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from contextlib import asynccontextmanager
import stripe
import os
from datetime import datetime
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.core.dependencies import redis_client, verify_api_key
from app.api.v1 import pdf_generation, pdf_manipulation, pdf_extraction
from app.models.requests import APIKeyCreate
from app.models.responses import (
    APIKeyResponse, 
    UsageResponse, 
    HealthCheckResponse,
    ErrorResponse
)


# Create temp directory on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    yield
    # Shutdown (cleanup if needed)


# Initialize FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="Comprehensive PDF API for generation, manipulation, and extraction",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            details={"status_code": exc.status_code}
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            details={"error": str(exc)}
        ).dict()
    )


# Include routers
app.include_router(
    pdf_generation.router,
    prefix=f"{settings.API_V1_STR}",
    tags=["PDF Generation"]
)

app.include_router(
    pdf_manipulation.router,
    prefix=f"{settings.API_V1_STR}",
    tags=["PDF Manipulation"]
)

app.include_router(
    pdf_extraction.router,
    prefix=f"{settings.API_V1_STR}",
    tags=["PDF Extraction"]
)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "pricing": {
            "basic": "$29/month - 100 PDFs/hour",
            "pro": "$99/month - 1,000 PDFs/hour",
            "enterprise": "$299/month - 10,000 PDFs/hour"
        },
        "features": {
            "generation": "Convert HTML/URLs to PDF, use templates",
            "manipulation": "Merge, split, compress, rotate, watermark, secure PDFs",
            "extraction": "Extract text, images, and metadata from PDFs",
            "conversion": "Convert PDFs to images and images to PDFs"
        }
    }


# API Key Management
@app.post(f"{settings.API_V1_STR}/keys", response_model=APIKeyResponse)
async def create_api_key(request: APIKeyCreate):
    """
    Create a new API key (typically called after Stripe payment).
    
    In production, this endpoint should be protected and only called
    by your payment processing system.
    """
    # Generate unique API key
    api_key = f"pdf_{'live' if settings.STRIPE_SECRET_KEY.startswith('sk_live') else 'test'}_{secrets.token_urlsafe(32)}"
    
    # Store in Redis
    redis_client.hset(f"api_key:{api_key}", mapping={
        "email": request.email,
        "plan": request.plan,
        "created": datetime.now().isoformat(),
        "requests": 0,
        "active": "true"
    })
    
    return APIKeyResponse(
        api_key=api_key,
        plan=request.plan,
        email=request.email,
        message="API key created successfully"
    )


@app.get(f"{settings.API_V1_STR}/usage", response_model=UsageResponse)
async def check_usage(api_key: str = Depends(verify_api_key)):
    """Check API key usage and limits"""
    key_data = redis_client.hgetall(f"api_key:{api_key}")
    plan = key_data.get("plan", "basic")
    requests_used = int(key_data.get("requests", 0))
    
    # Get rate limit info
    rate_key = f"rate_limit:{api_key}"
    current_hour_usage = redis_client.get(rate_key)
    current_hour_usage = int(current_hour_usage) if current_hour_usage else 0
    
    limits = {
        "basic": settings.RATE_LIMIT_BASIC,
        "pro": settings.RATE_LIMIT_PRO,
        "enterprise": settings.RATE_LIMIT_ENTERPRISE
    }
    
    limit = limits.get(plan, settings.RATE_LIMIT_BASIC)
    
    # Calculate reset time (next hour)
    from datetime import datetime, timedelta
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    return UsageResponse(
        plan=plan,
        requests_used=current_hour_usage,
        requests_limit=limit,
        reset_date=next_hour,
        percentage_used=(current_hour_usage / limit * 100) if limit > 0 else 0,
        message="Usage retrieved successfully"
    )


# Stripe Checkout
@app.post("/create-checkout-session")
async def create_checkout_session(plan: str):
    """
    Create a Stripe checkout session for purchasing API access.
    
    Plans: basic ($29), pro ($99), enterprise ($299)
    """
    if plan not in ["basic", "pro", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    # In production, these would be your actual Stripe price IDs
    price_ids = {
        "basic": os.getenv("STRIPE_PRICE_BASIC", "price_basic_monthly"),
        "pro": os.getenv("STRIPE_PRICE_PRO", "price_pro_monthly"),
        "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_monthly")
    }
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_ids[plan],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=os.getenv("STRIPE_SUCCESS_URL", "https://yourapi.com/success?session_id={CHECKOUT_SESSION_ID}"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL", "https://yourapi.com/cancel"),
            metadata={
                'plan': plan
            }
        )
        
        return {"checkout_url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Stripe Webhook (Improved)
@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks for automatic API key creation.
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle checkout completion
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Create API key for customer
        email = session.get('customer_email')
        plan = session['metadata']['plan']
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        
        if email:
            # Create API key
            api_key = f"pdf_{'live' if settings.STRIPE_SECRET_KEY.startswith('sk_live') else 'test'}_{secrets.token_urlsafe(32)}"
            
            # Store with Stripe metadata
            redis_client.hset(f"api_key:{api_key}", mapping={
                "email": email,
                "plan": plan,
                "created": datetime.now().isoformat(),
                "requests": 0,
                "active": "true",
                "stripe_customer_id": customer_id or "",
                "stripe_subscription_id": subscription_id or ""
            })
            
            # Send API key via email
            try:
                await send_api_key_email(email, api_key, plan)
            except Exception as e:
                print(f"Failed to send email: {e}")
    
    # Handle subscription cancellation
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        
        # Find and deactivate API key
        for key in redis_client.scan_iter("api_key:*"):
            key_data = redis_client.hgetall(key)
            if key_data.get("stripe_subscription_id") == subscription['id']:
                redis_client.hset(key, "active", "false")
                break
    
    return {"status": "success"}


async def send_api_key_email(email: str, api_key: str, plan: str):
    """Send API key to customer via email"""
    # In production, use a proper email service like SendGrid
    subject = "Your Lightning PDF API Key"
    body = f"""
    Welcome to Lightning PDF API!
    
    Your API key: {api_key}
    Plan: {plan.capitalize()}
    
    Get started:
    1. Include your API key in the X-API-Key header
    2. Check out our documentation at https://yourapi.com/docs
    3. View usage at https://yourapi.com/dashboard
    
    Happy PDF processing!
    """
    
    # This is a placeholder - use proper email service in production
    print(f"Email would be sent to {email} with API key")


# Health check
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check health status of the API and its dependencies"""
    
    # Check Redis connection
    try:
        redis_client.ping()
        redis_status = True
    except:
        redis_status = False
    
    # Check Stripe
    try:
        stripe.Account.retrieve()
        stripe_status = True
    except:
        stripe_status = False
    
    services = {
        "redis": redis_status,
        "stripe": stripe_status,
        "pdf_service": True  # Always true if we got this far
    }
    
    overall_status = "healthy" if all(services.values()) else "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        services=services
    )


# API Documentation customization
app.openapi_tags = [
    {
        "name": "PDF Generation",
        "description": "Generate PDFs from HTML, URLs, or templates"
    },
    {
        "name": "PDF Manipulation",
        "description": "Merge, split, compress, rotate, watermark, and secure PDFs"
    },
    {
        "name": "PDF Extraction",
        "description": "Extract text, images, and metadata from PDFs"
    }
]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
