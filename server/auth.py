# Authentication utilities for the Trading Platform
# This matches the same pattern as keep-in-touch-chat
import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from fastapi import HTTPException, status, Request
from typing import Optional

# JWT secret from environment
JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-jwt-key-here')

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # Generate salt and hash password
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_token(user_id: int, username: str) -> str:
    """Generate a JWT token for a user"""
    payload = {
        'userId': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(days=7)  # Token expires in 7 days
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError('Token has expired')
    except jwt.InvalidTokenError:
        raise ValueError('Invalid token')

def get_token_from_request(request: Request) -> Optional[str]:
    """Extract JWT token from request headers"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    # Check if it's a Bearer token
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    return None

# FastAPI dependency for authentication
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """FastAPI dependency to get current user from JWT token"""
    token = credentials.credentials
    
    try:
        payload = verify_token(token)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

# Decorator for compatibility (but FastAPI uses dependencies instead)
def require_auth(f):
    """Decorator to require authentication - but FastAPI uses Depends(get_current_user) instead"""
    # This is kept for compatibility but FastAPI endpoints should use Depends(get_current_user)
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # Try to find request in args
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            raise HTTPException(status_code=401, detail="Request not found")
        
        token = get_token_from_request(request)
        if not token:
            raise HTTPException(status_code=401, detail="Access token required")
        
        try:
            payload = verify_token(token)
            # Store in kwargs
            kwargs['_current_user'] = payload
            return await f(*args, **kwargs)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=str(e))
    
    return decorated_function

# Alias for compatibility
get_password_hash = hash_password
