from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

import httpx

from config import get_settings

security = HTTPBearer(auto_error=False)
_jwks_cache = None


def _settings():
    return get_settings()


async def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        settings = _settings()
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.CLERK_ISSUER}/.well-known/jwks.json")
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


async def verify_clerk_token(token: str) -> dict:
    """Verify Clerk JWT token and return payload."""
    settings = _settings()
    try:
        jwks = await get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid token: key not found")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.CLERK_PUBLISHABLE_KEY,
            issuer=settings.CLERK_ISSUER,
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract user_id from Clerk JWT (or a fixed dev user when bypassed)."""
    settings = _settings()

    if settings.DEV_AUTH_BYPASS and not settings.is_production:
        return settings.DEV_USER_ID

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    payload = await verify_clerk_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: no subject")
    return user_id


async def get_current_user_id_from_api_key(request: Request) -> str:
    """Get user_id from request state (set by API key middleware)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in request")
    return user_id
