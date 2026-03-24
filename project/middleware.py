"""
Authentication and Authorization Middleware for FastAPI
Handles JWT token validation from Supabase and role-based access control
""" 

import os
import jwt
from fastapi import HTTPException, Header, Depends
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Get Supabase JWT secret from environment
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

class AuthUser:
    """Represents an authenticated user"""
    def __init__(self, user_id: str, email: str, role: str):
        self.user_id = user_id
        self.email = email
        self.role = role
    
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == "admin"


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None)
) -> Optional[AuthUser]:
    """
    Extract and validate JWT token from Authorization header
    Gets role from X-User-Role header (sent by frontend)
    Returns AuthUser if valid, None if no token provided
    Raises HTTPException if token is invalid
    """
    if not authorization:
        return None
    
    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    # Validate JWT token
    try:
        # Decode the JWT token using Supabase JWT secret
        # Try with multiple algorithms as Supabase may use different ones
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256", "HS384", "HS512"],  # Support multiple HMAC algorithms
            audience="authenticated",
            options={"verify_aud": False}  # Make audience verification optional
        )
        
        # Extract user information from token
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        # Get role from header (sent by frontend after querying profiles table)
        # Default to "user" if not provided
        role = x_user_role if x_user_role else "user"
        
        return AuthUser(user_id=user_id, email=email, role=role)
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        # More lenient - just print the error but don't fail completely
        print(f"JWT validation warning: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        print(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def require_auth(
    authorization: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None)
) -> AuthUser:
    """
    Dependency that requires authentication
    Raises 401 if user is not authenticated
    """
    user = await get_current_user(authorization, x_user_role)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_admin(user: AuthUser = Depends(require_auth)) -> AuthUser:
    """
    Dependency that requires admin role
    Raises 403 if user is not an admin
    """
    if not user.is_admin():
        raise HTTPException(
            status_code=403,
            detail="Admin access required. Only administrators can perform this action."
        )
    return user
