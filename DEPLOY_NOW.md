# 🚀 DEPLOY YOUR PDF API NOW!

Your API is ready! Here's how to get it live on RapidAPI:

## Option 1: Railway (via Web Interface)

Since the CLI upload timed out, use the web interface:

1. **Open Railway Dashboard**
   - Go to: https://railway.com/project/71bdd401-4c38-4bbe-9883-535c5733f438
   - This is YOUR project that we just created!

2. **Add a Service**
   - Click "New Service"
   - Select "GitHub Repo" or "Empty Service"
   - If GitHub: Connect your repo
   - If Empty: Drag and drop your project folder

3. **Add Redis**
   - Click "New" → "Database" → "Redis"
   - It will automatically connect

4. **Set Environment Variables**
   Click on your service → Variables → Add these:
   ```
   SECRET_KEY=your-super-secret-key-change-this
   REDIS_URL=(auto-filled by Railway)
   RAPIDAPI_PROXY_SECRET=(get from RapidAPI later)
   RATE_LIMIT_BASIC=100
   RATE_LIMIT_PRO=1000
   RATE_LIMIT_ENTERPRISE=10000
   ```

5. **Deploy**
   - Railway will auto-deploy
   - Get your URL from Settings → Domains
   - It will be something like: `pdf-api-production.up.railway.app`

## Option 2: Render.com (Free Tier!)

1. **Go to Render.com**
   - Sign up at https://render.com
   - Click "New +" → "Web Service"

2. **Connect GitHub**
   - Push your code to GitHub first:
   ```bash
   git init
   git add .
   git commit -m "PDF API ready for deployment"
   git remote add origin YOUR_GITHUB_REPO
   git push -u origin main
   ```

3. **Configure Service**
   - Name: `pdf-api`
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Add Redis**
   - New → Redis
   - Copy the Redis URL

5. **Environment Variables**
   Same as Railway above

## Option 3: Quick Heroku Deploy

```bash
# Install Heroku CLI first
# Then:
heroku create your-pdf-api
heroku addons:create heroku-redis:mini
git push heroku main
heroku config:set SECRET_KEY="your-secret-key"
heroku open
```

## 🎯 After Deployment: Submit to RapidAPI

1. **Test Your Deployed API**
   ```bash
   curl https://YOUR-DEPLOYED-URL/health
   ```

2. **Go to RapidAPI Provider Dashboard**
   - https://rapidapi.com/provider
   - Sign up/Login

3. **Get Your RapidAPI Secret**
   - Settings → Security → Copy "Proxy Secret"
   - Add to your deployed app's environment variables

4. **Add New API**
   - Click "Add New API"
   - Fill in:
     - Name: Lightning PDF API
     - Category: Tools
     - Base URL: Your deployed URL

5. **Add Endpoints**
   Copy from `rapidapi-config.json`:
   - `/api/v1/pdf/generate` - POST
   - `/api/v1/pdf/merge` - POST
   - `/api/v1/pdf/split` - POST
   - etc. (all 14 endpoints)

6. **Set Pricing**
   - Basic (Free): 100/day
   - Pro ($29): 3,000/month
   - Ultra ($99): 30,000/month
   - Mega ($299): Unlimited

7. **Submit for Review**

## 📱 Quick Links

- **Your Railway Project**: https://railway.com/project/71bdd401-4c38-4bbe-9883-535c5733f438
- **RapidAPI Provider**: https://rapidapi.com/provider
- **Test Your API**: Use the `/docs` endpoint on your deployed URL

## ⚡ Deployment Checklist

- [ ] Deploy to Railway/Render/Heroku
- [ ] Add Redis
- [ ] Set environment variables
- [ ] Test health endpoint
- [ ] Get RapidAPI proxy secret
- [ ] Submit to RapidAPI
- [ ] Wait for approval (1-3 days)

## 🆘 Troubleshooting

**"Module not found" errors**
- Make sure you're using Python 3.8+
- Check requirements.txt is complete

**"Redis connection failed"**
- Ensure REDIS_URL is set correctly
- Check Redis service is running

**"Invalid proxy secret"**
- Double-check RAPIDAPI_PROXY_SECRET matches

## 🎉 You're Almost There!

Just deploy (Railway web interface is easiest) and submit to RapidAPI. Your API will be making money within days!
