# 🔐 Railway Environment Variables

Add these in Railway → Your Service → Variables tab:

## Required Variables:

### 1. SECRET_KEY
```
SECRET_KEY=high-five-43234
```
**Important**: Change this to a random string! You can generate one here: https://randomkeygen.com/

### 2. Rate Limits
```
RATE_LIMIT_BASIC=100
RATE_LIMIT_PRO=1000
RATE_LIMIT_ENTERPRISE=10000
```

### 3. File Settings
```
MAX_UPLOAD_SIZE=52428800
TEMP_DIR=/tmp/pdf-api
```

### 4. API Settings
```
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 5. CORS (Optional but recommended)
```
BACKEND_CORS_ORIGINS=["*"]
```

## After RapidAPI Setup (Add Later):

### 6. RapidAPI Secret
```
RAPIDAPI_PROXY_SECRET=your-secret-from-rapidapi
```
You'll get this from RapidAPI Provider Dashboard after signing up.

## Redis (Auto-configured):

Railway will automatically add:
```
REDIS_URL=redis://...
```
when you add the Redis database.

---

## 📋 Copy-Paste Ready:

Here's all variables in one block for easy copying:

```
SECRET_KEY=high-five-43234
RATE_LIMIT_BASIC=100
RATE_LIMIT_PRO=1000
RATE_LIMIT_ENTERPRISE=10000
MAX_UPLOAD_SIZE=52428800
TEMP_DIR=/tmp/pdf-api
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_CORS_ORIGINS=["*"]
```

## ⚠️ Important Notes:

1. **Change SECRET_KEY**: Don't use the example value!
2. **Redis Required**: Make sure to add Redis database (New → Database → Redis)
3. **RAPIDAPI_PROXY_SECRET**: Add this after you sign up at https://rapidapi.com/provider

Your API won't work properly without these variables!
