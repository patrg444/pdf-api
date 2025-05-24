from fastapi import HTTPException, Depends, Header, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import redis
from datetime import datetime
import os

from app.core.config import settings


# Initialize Redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Security scheme
security = HTTPBearer()


async def check_rate_limit(api_key: str) -> bool:
    """Check if API key has exceeded rate limit"""
    key = f"rate_limit:{api_key}"
    current = redis_client.get(key)
    
    if current is None:
        redis_client.setex(key, 3600, 1)  # 1 hour expiry
        return True
    
    count = int(current)
    plan = redis_client.hget(f"api_key:{api_key}", "plan") or "basic"
    
    limits = {
        "basic": settings.RATE_LIMIT_BASIC,
        "pro": settings.RATE_LIMIT_PRO,
        "enterprise": settings.RATE_LIMIT_ENTERPRISE
    }
    limit = limits.get(plan, settings.RATE_LIMIT_BASIC)
    
    if count >= limit:
        return False
    
    redis_client.incr(key)
    return True


async def verify_api_key(x_api_key: str = Header(None)) -> str:
    """Verify API key exists and is valid"""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if API key exists
    exists = redis_client.exists(f"api_key:{x_api_key}")
    if not exists:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if API key is active
    is_active = redis_client.hget(f"api_key:{x_api_key}", "active")
    if is_active != "true":
        raise HTTPException(
            status_code=403,
            detail="API key is inactive"
        )
    
    # Check rate limit
    if not await check_rate_limit(x_api_key):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please upgrade your plan or try again later."
        )
    
    # Update usage statistics
    redis_client.hset(f"api_key:{x_api_key}", "last_used", datetime.now().isoformat())
    redis_client.hincrby(f"api_key:{x_api_key}", "requests", 1)
    
    return x_api_key


async def verify_rapidapi_key(
    x_rapidapi_proxy_secret: str = Header(None),
    x_rapidapi_user: str = Header(None),
    x_rapidapi_subscription: str = Header(None)
) -> str:
    """Verify RapidAPI request and create/update user's API key"""
    # Check if this is a RapidAPI request
    if not x_rapidapi_proxy_secret:
        # Not a RapidAPI request, fall back to regular API key auth
        return await verify_api_key(Header(None))
    
    # Verify RapidAPI proxy secret
    rapidapi_secret = os.getenv("RAPIDAPI_PROXY_SECRET", "")
    if x_rapidapi_proxy_secret != rapidapi_secret:
        raise HTTPException(
            status_code=403,
            detail="Invalid RapidAPI proxy secret"
        )
    
    if not x_rapidapi_user:
        raise HTTPException(
            status_code=400,
            detail="Missing RapidAPI user header"
        )
    
    # Map RapidAPI subscription tiers to our plans
    plan_mapping = {
        "BASIC": "basic",
        "PRO": "pro",
        "ULTRA": "enterprise",
        "MEGA": "enterprise"
    }
    
    plan = plan_mapping.get(x_rapidapi_subscription, "basic")
    
    # Create consistent API key for RapidAPI user
    api_key = f"rapid_{x_rapidapi_user}"
    
    # Check if key exists, create/update if needed
    key_exists = redis_client.exists(f"api_key:{api_key}")
    
    if not key_exists:
        # Create new key for RapidAPI user
        redis_client.hset(f"api_key:{api_key}", mapping={
            "email": f"{x_rapidapi_user}@rapidapi.com",
            "plan": plan,
            "created": datetime.now().isoformat(),
            "requests": 0,
            "active": "true",
            "source": "rapidapi",
            "rapidapi_user": x_rapidapi_user
        })
    else:
        # Update plan if changed
        current_plan = redis_client.hget(f"api_key:{api_key}", "plan")
        if current_plan != plan:
            redis_client.hset(f"api_key:{api_key}", "plan", plan)
    
    # Check rate limit for this API key
    if not await check_rate_limit(api_key):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please upgrade your RapidAPI subscription."
        )
    
    # Update usage
    redis_client.hset(f"api_key:{api_key}", "last_used", datetime.now().isoformat())
    redis_client.hincrby(f"api_key:{api_key}", "requests", 1)
    
    return api_key


# Universal auth dependency that works with both direct API keys and RapidAPI
async def verify_auth(
    x_api_key: str = Header(None),
    x_rapidapi_proxy_secret: str = Header(None),
    x_rapidapi_user: str = Header(None),
    x_rapidapi_subscription: str = Header(None)
) -> str:
    """Universal authentication that supports both direct API keys and RapidAPI"""
    if x_rapidapi_proxy_secret:
        # This is a RapidAPI request
        return await verify_rapidapi_key(
            x_rapidapi_proxy_secret,
            x_rapidapi_user,
            x_rapidapi_subscription
        )
    else:
        # Direct API key authentication
        return await verify_api_key(x_api_key)


async def verify_api_key_bearer(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify API key from Bearer token"""
    return await verify_api_key(credentials.credentials)


def validate_file_extension(filename: str, allowed_extensions: set = None) -> bool:
    """Validate file extension"""
    if not allowed_extensions:
        allowed_extensions = settings.ALLOWED_EXTENSIONS
    
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def validate_file_size(file_size: int) -> bool:
    """Validate file size"""
    return file_size <= settings.MAX_UPLOAD_SIZE


async def validate_pdf_file(file: UploadFile = File(...)) -> bytes:
    """Validate and return PDF file content"""
    # Check file extension
    if not validate_file_extension(file.filename, {".pdf"}):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are allowed."
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if not validate_file_size(len(content)):
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    # Basic PDF validation
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file"
        )
    
    return content


async def validate_image_file(file: UploadFile = File(...)) -> bytes:
    """Validate and return image file content"""
    # Check file extension
    allowed_image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}
    if not validate_file_extension(file.filename, allowed_image_extensions):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed types: JPG, PNG, GIF, BMP, TIFF"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if not validate_file_size(len(content)):
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    return content


async def validate_multiple_pdf_files(files: List[UploadFile] = File(...)) -> List[bytes]:
    """Validate multiple PDF files"""
    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files provided"
        )
    
    if len(files) > 20:  # Reasonable limit
        raise HTTPException(
            status_code=400,
            detail="Too many files. Maximum 20 files allowed."
        )
    
    pdf_contents = []
    for file in files:
        content = await validate_pdf_file(file)
        pdf_contents.append(content)
    
    return pdf_contents


async def validate_multiple_image_files(files: List[UploadFile] = File(...)) -> List[bytes]:
    """Validate multiple image files"""
    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files provided"
        )
    
    if len(files) > 50:  # Reasonable limit for images
        raise HTTPException(
            status_code=400,
            detail="Too many files. Maximum 50 images allowed."
        )
    
    image_contents = []
    for file in files:
        content = await validate_image_file(file)
        image_contents.append(content)
    
    return image_contents


def get_user_plan(api_key: str = Depends(verify_api_key)) -> str:
    """Get user's subscription plan"""
    plan = redis_client.hget(f"api_key:{api_key}", "plan")
    return plan or "basic"


def check_feature_access(required_plan: str):
    """Decorator to check if user has access to a feature based on their plan"""
    plan_hierarchy = {
        "basic": 0,
        "pro": 1,
        "enterprise": 2
    }
    
    async def dependency(user_plan: str = Depends(get_user_plan)):
        user_level = plan_hierarchy.get(user_plan, 0)
        required_level = plan_hierarchy.get(required_plan, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires {required_plan} plan or higher. Current plan: {user_plan}"
            )
        
        return True
    
    return dependency


# Feature access dependencies
require_pro_plan = check_feature_access("pro")
require_enterprise_plan = check_feature_access("enterprise")


class PaginationParams:
    """Common pagination parameters"""
    def __init__(
        self,
        skip: int = 0,
        limit: int = 10,
        max_limit: int = 100
    ):
        self.skip = skip
        self.limit = min(limit, max_limit)


def get_file_url(file_path: str) -> str:
    """Generate URL for accessing a file"""
    # In production, this would return a CDN URL or S3 presigned URL
    # For now, return a local endpoint
    file_name = os.path.basename(file_path)
    return f"/api/v1/files/{file_name}"


async def log_api_request(
    api_key: str,
    endpoint: str,
    method: str,
    status_code: int,
    processing_time: float
):
    """Log API request for analytics"""
    log_data = {
        "api_key": api_key,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "processing_time": processing_time,
        "timestamp": datetime.now().isoformat()
    }
    
    # Store in Redis with expiry for analytics
    log_key = f"api_log:{api_key}:{datetime.now().strftime('%Y%m%d')}:{endpoint}"
    redis_client.lpush(log_key, str(log_data))
    redis_client.expire(log_key, 86400 * 30)  # Keep logs for 30 days
