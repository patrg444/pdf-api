# Quick Setup Guide: Deploy with Stripe & RapidAPI

## 🚀 Step 1: Deploy Your API

### Option A: Railway (Fastest)
1. Fork/clone this repository
2. Install Railway CLI: `npm install -g @railway/cli`
3. Deploy:
```bash
railway login
railway init
railway up
railway add redis
```
4. Set environment variables in Railway dashboard

### Option B: Heroku
```bash
heroku create your-pdf-api
heroku addons:create heroku-redis:hobby-dev
git push heroku main
```

### Option C: Docker on VPS
```bash
# On your VPS (DigitalOcean, Linode, etc.)
git clone <your-repo>
cd pdf-api
docker-compose up -d
```

## 💳 Step 2: Configure Stripe

### 2.1 Create Stripe Products
1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to Products → Add Product
3. Create 3 products:
   - **Basic Plan**: $29/month
   - **Pro Plan**: $99/month  
   - **Enterprise Plan**: $299/month

### 2.2 Get Price IDs
For each product, copy the price ID (looks like `price_1234...`)

### 2.3 Configure Webhook
1. Go to Developers → Webhooks
2. Add endpoint: `https://your-api.com/stripe/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
4. Copy the webhook signing secret

### 2.4 Update Environment Variables
```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_BASIC=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_ENTERPRISE=price_...
```

## 🌐 Step 3: List on RapidAPI

### 3.1 Prepare Your API
1. Ensure your API is publicly accessible
2. Test all endpoints work correctly
3. Have documentation ready

### 3.2 Submit to RapidAPI
1. Go to [RapidAPI Provider](https://rapidapi.com/provider)
2. Click "Add New API"
3. Fill in details:
   - **Name**: Lightning PDF API
   - **Category**: Tools
   - **Base URL**: `https://your-deployed-api.com`

### 3.3 Configure Endpoints
Use the OpenAPI spec from `/openapi.json` or manually add:
- Each endpoint path
- Request/response examples
- Required parameters

### 3.4 Set Up Pricing
Configure your pricing tiers to match:
- **Basic** (Free): 100 requests/day
- **Pro** ($29): 3,000 requests/month
- **Ultra** ($99): 30,000 requests/month
- **Mega** ($299): 300,000 requests/month

### 3.5 Add RapidAPI Secret
1. Get your RapidAPI proxy secret from the dashboard
2. Add to environment variables:
```env
RAPIDAPI_PROXY_SECRET=your-secret-here
```

## ✅ Step 4: Testing

### Test Direct API Access
```bash
# Create API key via Stripe checkout
curl -X POST https://your-api.com/create-checkout-session \
  -H "Content-Type: application/json" \
  -d '{"plan": "basic"}'

# Use the API key
curl -X POST https://your-api.com/api/v1/pdf/generate \
  -H "X-API-Key: pdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"html": "<h1>Test</h1>"}'
```

### Test RapidAPI Access
```bash
curl -X POST "https://lightning-pdf-api.p.rapidapi.com/api/v1/pdf/generate" \
  -H "X-RapidAPI-Key: YOUR-RAPIDAPI-KEY" \
  -H "X-RapidAPI-Host: lightning-pdf-api.p.rapidapi.com" \
  -H "Content-Type: application/json" \
  -d '{"html": "<h1>Test</h1>"}'
```

## 🎯 Revenue Flow

1. **Direct Sales (via Stripe)**
   - Users visit your website
   - Purchase subscription via Stripe Checkout
   - Receive API key via email
   - Use API directly

2. **RapidAPI Sales**
   - Users discover API on RapidAPI
   - Subscribe through RapidAPI
   - RapidAPI handles billing
   - Users access API through RapidAPI proxy

## 📈 Monitoring

### Set up monitoring for:
- API health: `/health` endpoint
- Stripe webhooks processing
- RapidAPI request volume
- Error rates and response times

### Recommended Tools:
- **Sentry**: Error tracking
- **New Relic**: Performance monitoring
- **Datadog**: Infrastructure monitoring
- **Stripe Dashboard**: Payment analytics
- **RapidAPI Analytics**: API usage stats

## 🆘 Troubleshooting

### Common Issues:

**Stripe webhook not working:**
- Check webhook signing secret
- Ensure HTTPS is enabled
- Verify webhook endpoint is public

**RapidAPI requests failing:**
- Verify RAPIDAPI_PROXY_SECRET
- Check CORS settings
- Ensure all endpoints are accessible

**Redis connection errors:**
- Check REDIS_URL is correct
- Ensure Redis is running
- Check firewall rules

## 📞 Support Channels

1. **Direct Customers**: 
   - Email: support@yourapi.com
   - Dashboard: https://yourapi.com/dashboard

2. **RapidAPI Users**:
   - RapidAPI discussion forum
   - In-app messaging

## 🎉 Launch Checklist

- [ ] API deployed and accessible
- [ ] Stripe products created
- [ ] Webhook configured and tested
- [ ] RapidAPI listing submitted
- [ ] Documentation complete
- [ ] Support email set up
- [ ] Monitoring configured
- [ ] Backup strategy in place
- [ ] Rate limiting tested
- [ ] Security headers configured

Ready to launch! 🚀
