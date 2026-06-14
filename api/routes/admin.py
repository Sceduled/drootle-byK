from fastapi import APIRouter, Depends, Header, HTTPException
from core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

async def verify_admin_secret(x_admin_secret: str = Header(...)):
    if not settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Admin functionality disabled")
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Invalid admin secret")
    return True

@router.get("/health", dependencies=[Depends(verify_admin_secret)])
async def admin_health():
    """
    Called by central admin db to verify client node is alive and configured.
    """
    return {
        "status": "ok",
        "client_id": settings.CLIENT_ID,
        "client_name": settings.CLIENT_NAME,
        "version": "1.0.0"
    }
