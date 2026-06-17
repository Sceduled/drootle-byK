from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
from core.config import settings
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.models import User
from passlib.context import CryptContext

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginPayload(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(payload: LoginPayload, db: AsyncSession = Depends(get_db)):
    # Fallback to Super Admin logic
    if payload.username == settings.DASHBOARD_USERNAME and payload.password == settings.DASHBOARD_PASSWORD:
        expiration = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)
        token = jwt.encode(
            {"sub": payload.username, "role": "admin", "exp": expiration},
            settings.JWT_SECRET,
            algorithm="HS256"
        )
        return {"access_token": token, "token_type": "bearer", "role": "admin"}

    # Database lookup for Sales Reps
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalars().first()
    
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    expiration = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    token = jwt.encode(
        {"sub": user.username, "role": user.role, "exp": expiration},
        settings.JWT_SECRET,
        algorithm="HS256"
    )
    return {"access_token": token, "token_type": "bearer", "role": user.role}

@router.get("/verify")
async def verify(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return {"valid": True, "username": payload.get("sub"), "role": payload.get("role", "sales_rep")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return {"username": payload.get("sub"), "role": payload.get("role", "sales_rep")}
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")
