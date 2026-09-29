from fastapi import HTTPException, Header
from app.core.supabase import get_supabase


async def get_current_user(authorization: str = Header(...)) -> dict:
    """
    Validate Supabase JWT from Authorization header.
    Frontend sends: Authorization: Bearer <supabase_access_token>
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")

    token = authorization.split(" ", 1)[1]
    supabase = get_supabase()

    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(401, "Invalid or expired token")
        return {"id": user.user.id, "email": user.user.email}
    except Exception:
        raise HTTPException(401, "Authentication failed")
