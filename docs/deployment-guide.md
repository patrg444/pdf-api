# Deployment & Distribution Guide

## 🚀 Hosting Options

### 1. Railway.app (Recommended for Quick Start)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up

# Add Redis
railway add redis

# Set environment variables
railway variables set SECRET_KEY="your-production-secret"
railway variables set STRIPE_SECRET_KEY="sk_live_..."
```

### 2. Google Cloud Run
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/pdf-api

# Deploy to Cloud Run
gcloud run deploy pdf-api \
  --image gcr.io/PROJECT_ID/pdf-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars REDIS_URL=$REDIS_URL,STRIPE_SECRET_KEY=$STRIPE_KEY
```

### 3. AWS ECS with Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI
docker build -t pdf-api .
docker tag pdf-api:latest $ECR_URI/pdf-api:latest
docker push $ECR_URI/pdf-api:latest

# Deploy using AWS CLI or Console
aws ecs create-service \
  --cluster pdf-api-cluster \
  --service-name pdf-api \
  --task-definition pdf-api:1 \
  --desired-count 2 \
  --launch-type FARGATE
```

### 4. Heroku
```bash
# Create Heroku app
heroku create your-pdf-api

# Add Redis
heroku addons:create heroku-redis:hobby-dev

# Set environment variables
heroku config:set SECRET_KEY="your-production-secret"
heroku config:set STRIPE_SECRET_KEY="sk_live_..."

# Deploy
git push heroku main
```

## 💳 Stripe Integration

### 1. Setup Stripe Dashboard
1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Create Products:
   - Basic Plan: $29/month
   - Pro Plan: $99/month
   - Enterprise Plan: $299/month
3. Get API keys from Developers section

### 2. Create Stripe Checkout Session
```python
# Add this endpoint to your API
@app.post("/create-checkout-session")
async def create_checkout_session(plan: str):
    price_ids = {
        "basic": "price_basic_monthly_id",
        "pro": "price_pro_monthly_id",
        "enterprise": "price_enterprise_monthly_id"
    }
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': price_ids[plan],
            'quantity': 1,
        }],
        mode='subscription',
        success_url='https://yourapi.com/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='https://yourapi.com/cancel',
        metadata={
            'plan': plan
        }
    )
    
    return {"checkout_url": session.url}
```

### 3. Handle Webhook Events
Update `app/main.py` webhook handler:
```python
@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
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
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Create API key for customer
        email = session.get('customer_email')
        plan = session['metadata']['plan']
        
        # Create and email API key
        api_key = await create_api_key(APIKeyCreate(email=email, plan=plan))
        # Send email with API key
        
    return {"status": "success"}
```

## 🌐 RapidAPI Integration

### 1. Prepare Your API

Create `rapidapi-config.json`:
```json
{
  "name": "Lightning PDF API",
  "description": "Comprehensive PDF generation, manipulation, and extraction API",
  "category": "Tools",
  "website": "https://yourapi.com",
  "terms": "https://yourapi.com/terms",
  "endpoints": [
    {
      "name": "Generate PDF",
      "path": "/api/v1/pdf/generate",
      "method": "POST",
      "description": "Generate PDF from HTML, URL, or template"
    },
    {
      "name": "Merge PDFs",
      "path": "/api/v1/pdf/merge",
      "method": "POST",
      "description": "Merge multiple PDF files"
    }
  ],
  "pricing": [
    {
      "name": "Basic",
      "price": 29,
      "requests": 3000,
      "rate_limit": "100 requests per hour"
    },
    {
      "name": "Pro",
      "price": 99,
      "requests": 30000,
      "rate_limit": "1000 requests per hour"
    },
    {
      "name": "Ultra",
      "price": 299,
      "requests": 300000,
      "rate_limit": "10000 requests per hour"
    }
  ]
}
```

### 2. RapidAPI Middleware

Add RapidAPI authentication to `app/core/dependencies.py`:
```python
async def verify_rapidapi_key(
    x_rapidapi_proxy_secret: str = Header(None),
    x_rapidapi_user: str = Header(None),
    x_rapidapi_subscription: str = Header(None)
) -> str:
    """Verify RapidAPI request"""
    if x_rapidapi_proxy_secret != settings.RAPIDAPI_PROXY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid RapidAPI proxy secret")
    
    # Map RapidAPI subscription to your plans
    plan_mapping = {
        "BASIC": "basic",
        "PRO": "pro",
        "ULTRA": "enterprise"
    }
    
    plan = plan_mapping.get(x_rapidapi_subscription, "basic")
    
    # Create or get API key for RapidAPI user
    api_key = f"rapid_{x_rapidapi_user}"
    
    # Check if key exists, create if not
    if not redis_client.exists(f"api_key:{api_key}"):
        redis_client.hset(f"api_key:{api_key}", mapping={
            "email": f"{x_rapidapi_user}@rapidapi.com",
            "plan": plan,
            "created": datetime.now().isoformat(),
            "requests": 0,
            "active": "true",
            "source": "rapidapi"
        })
    
    return api_key
```

### 3. Submit to RapidAPI

1. Go to [RapidAPI Provider Dashboard](https://rapidapi.com/provider)
2. Click "Add New API"
3. Fill in details:
   - API Name: Lightning PDF API
   - Base URL: https://your-deployed-api.com
   - Category: Tools
4. Add endpoints from your OpenAPI spec
5. Configure pricing plans
6. Add documentation and examples
7. Submit for review

### 4. Testing RapidAPI Integration

```bash
# Test through RapidAPI
curl -X POST "https://lightning-pdf-api.p.rapidapi.com/api/v1/pdf/generate" \
  -H "x-rapidapi-key: YOUR_RAPIDAPI_KEY" \
  -H "x-rapidapi-host: lightning-pdf-api.p.rapidapi.com" \
  -H "content-type: application/json" \
  -d '{
    "html": "<h1>Test PDF</h1>",
    "options": {"format": "A4"}
  }'
```

## 📊 Monitoring & Analytics

### 1. Add Logging
```python
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

### 2. Add Sentry for Error Tracking
```python
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    traces_sample_rate=0.1,
)

app.add_middleware(SentryAsgiMiddleware)
```

### 3. Add Metrics
```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
pdf_generated = Counter('pdf_generated_total', 'Total PDFs generated')
pdf_processing_time = Histogram('pdf_processing_seconds', 'PDF processing time')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 🔒 Production Security Checklist

- [ ] Use strong SECRET_KEY
- [ ] Enable HTTPS only
- [ ] Set up CORS properly
- [ ] Implement request signing for webhooks
- [ ] Use environment variables for all secrets
- [ ] Enable rate limiting
- [ ] Set up DDoS protection (Cloudflare)
- [ ] Regular security updates
- [ ] Backup Redis data
- [ ] Monitor for anomalies

## 🚦 Load Testing

```bash
# Install k6
brew install k6

# Run load test
k6 run load-test.js
```

Create `load-test.js`:
```javascript
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 0 },
  ],
};

export default function() {
  let response = http.post(
    'https://your-api.com/api/v1/pdf/generate',
    JSON.stringify({
      html: '<h1>Load Test</h1>',
      options: { format: 'A4' }
    }),
    {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'test_key'
      }
    }
  );
  
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 2000ms': (r) => r.timings.duration < 2000,
  });
}
