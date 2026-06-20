from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, exchange_google_code, get_current_user
from app.db import _new_uuid, get_db
from app.models_db import User

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleCodeRequest(BaseModel):
    code: str
    redirect_uri: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    lang: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/google", response_model=TokenResponse)
async def google_auth(req: GoogleCodeRequest, db: AsyncSession = Depends(get_db)):
    try:
        userinfo = await exchange_google_code(req.code, req.redirect_uri)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Google authorization code")

    result = await db.execute(select(User).where(User.google_id == userinfo["id"]))
    user = result.scalar_one_or_none()

    if user:
        user.email = userinfo["email"]
        user.name = userinfo["name"]
    else:
        user = User(
            id=_new_uuid(),
            google_id=userinfo["id"],
            email=userinfo["email"],
            name=userinfo["name"],
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut(id=user.id, email=user.email, name=user.name, lang=user.lang),
    )


@router.get("/me", response_model=UserOut)
async def get_me(user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(id=user.id, email=user.email, name=user.name, lang=user.lang)


@router.delete("/me", status_code=204)
async def delete_me(user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        await db.commit()
