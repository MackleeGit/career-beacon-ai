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

SUPABASE_URL = os.getenv("SUPABASE_URL", "")

# In-memory JWKS cache (refreshed every hour)
_jwks_cache: Optional[dict] = None
_jwks_fetched_at: float = 0
_JWKS_TTL = 3600  # seconds

EXCLUDED_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


def _needs_refresh() -> bool:
    return _jwks_cache is None or (time.time() - _jwks_fetched_at) > _JWKS_TTL


async def _fetch_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    if not _needs_refresh():
        return _jwks_cache
    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
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

            # Build RSA public key from JWK
            from jwt.algorithms import RSAAlgorithm
            public_key = RSAAlgorithm.from_jwk(json.dumps(key_dict))

            # Verify token
            payload = pyjwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience="authenticated",
            )

            # Attach to request for downstream handlers
            request.state.user = payload

        except pyjwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token expired"})
        except Exception as exc:
            return JSONResponse(status_code=401, content={"detail": f"Invalid token: {exc}"})

        return await call_next(request)
