# 🚀 Railway Domain Setup - Do This First!

## Step 1: Generate Domain in Railway

1. Go to your Railway dashboard
2. Click on your main service (not Redis)
3. Go to **Settings** tab
4. Scroll to **Networking** section
5. Under **Public Networking**, click **Generate Domain**
6. Railway will create a URL like: `peaceful-smile-production.up.railway.app`

## Step 2: Add PORT Variable (Important!)

If Railway doesn't automatically set PORT:
1. Go to **Variables** tab
2. Add: `PORT=8000`
3. Save

## Step 3: Verify All Variables

Make sure you have:
- `PORT=8000`
- `SECRET_KEY=your-secret-key`
- `REDIS_URL` (auto-set by Redis)
- `RAPIDAPI_PROXY_SECRET=501d39e59fmsh9d1dcf017099874p12f8ecjsn32ca60a4d2cb`
- All the rate limit variables

## Step 4: Trigger Redeploy

After generating domain and setting PORT:
1. Go to **Deployments** tab
2. Click the three dots on latest deployment
3. Click **Redeploy**

## Why This Matters:
- Railway needs a domain to properly configure networking
- Without a domain, PORT variable might not be set correctly
- The domain generation triggers proper port assignment

Once you've done this, your API should deploy successfully!
