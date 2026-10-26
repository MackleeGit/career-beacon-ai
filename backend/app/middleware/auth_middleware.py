import os
import json
import time
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import httpx

# ---------------------------------------------------------------------------
# JWT Auth Middleware for FastAPI
# ---------------------------------------------------------------------------
# Validates the Supabase-issued JWT on every /api/* request.
# Public endpoints (/, /health, /docs, /openapi.json) are excluded.
#
# HOW IT WORKS:
#   1. On first request, fetches the JWKS (JSON Web Key Set) from Supabase.
#      This contains the RSA public keys used to sign JWTs.
#   2. Extracts the Bearer token from the Authorization header.
#   3. Decodes the JWT header to find the kid (key ID).
#   4. Looks up the matching RSA public key from JWKS.
#   6. Attaches the decoded payload to request.state.user.
# ---------------------------------------------------------------------------

from app.core.config import settings

SUPABASE_URL = settings.supabase_url or os.getenv("SUPABASE_URL", "")

# In-memory JWKS cache (refreshed every hour)
_jwks_cache: Optional[dict] = None
_jwks_fetched_at: float = 0
_JWKS_TTL = 3600  # seconds

EXCLUDED_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


def get_verified_user_id(request: Request) -> str:
    """Extracts and validates caller identity from JWT middleware state."""
    user = getattr(request.state, "user", None)
    if not user or not user.get("sub"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Missing or invalid Bearer token.",
        )
    return str(user["sub"])



def _needs_refresh() -> bool:
    return _jwks_cache is None or (time.time() - _jwks_fetched_at) > _JWKS_TTL


async def _fetch_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    if not _needs_refresh():
        return _jwks_cache
    supabase_url = settings.supabase_url or os.getenv("SUPABASE_URL", "")
    url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=8)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.time()
    return _jwks_cache


def _find_key(kid: str, jwks: dict) -> dict:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise ValueError(f"No JWKS key found for kid={kid}")


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validates Supabase JWTs on protected /api/* routes.

    Usage in main.py::

        from app.middleware.auth_middleware import JWTAuthMiddleware
        app.add_middleware(JWTAuthMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        # Allow CORS preflight requests through without authentication
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip public endpoints
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Only enforce on /api/* routes
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or malformed Authorization header"},
            )

        token = auth.split(" ", 1)[1]

        try:
            import jwt as pyjwt

            # Decode header to get kid
            unverified = pyjwt.get_unverified_header(token)
            kid = unverified.get("kid")

            # Fetch / use cached JWKS
            jwks = await _fetch_jwks()
            key_dict = _find_key(kid, jwks)

            # Build public key from JWK (supports both EC/ES256 and RSA/RS256)
            public_key = pyjwt.PyJWK.from_dict(key_dict).key

            # Verify token
            payload = pyjwt.decode(
                token,
                public_key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
                issuer=f"{SUPABASE_URL.rstrip('/')}/auth/v1",
            )

            # Attach to request for downstream handlers
            request.state.user = payload

        except pyjwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token expired"})
        except pyjwt.PyJWTError as jwt_err:
            return JSONResponse(status_code=401, content={"detail": f"Invalid authentication token: {jwt_err}"})
        except Exception as exc:
            import logging
            logging.getLogger("uvicorn.error").error(f"Internal auth error: {exc}", exc_info=True)
            return JSONResponse(status_code=500, content={"detail": "Internal error verifying authentication"})

        return await call_next(request)
