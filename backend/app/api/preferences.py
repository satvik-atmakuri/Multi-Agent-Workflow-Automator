from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pydantic import BaseModel
from typing import List, Dict

from app.database import get_db
from app.models import UserPreference

router = APIRouter()

class PreferenceModel(BaseModel):
    key: str
    value: str

class PreferenceListResponse(BaseModel):
    preferences: Dict[str, str]

@router.get("/", response_model=PreferenceListResponse)
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """List all user preferences"""
    stmt = select(UserPreference)
    result = await db.execute(stmt)
    prefs = result.scalars().all()
    return {"preferences": {p.key: p.value for p in prefs}}

@router.post("/", response_model=PreferenceModel)
async def set_preference(pref: PreferenceModel, db: AsyncSession = Depends(get_db)):
    """Create or update a preference"""
    # Check if exists
    stmt = select(UserPreference).where(UserPreference.key == pref.key)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.value = pref.value
        await db.commit()
        await db.refresh(existing)
        return PreferenceModel(key=existing.key, value=existing.value)
    else:
        new_pref = UserPreference(key=pref.key, value=pref.value)
        db.add(new_pref)
        await db.commit()
        await db.refresh(new_pref)
        return PreferenceModel(key=new_pref.key, value=new_pref.value)

@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preference(key: str, db: AsyncSession = Depends(get_db)):
    """Delete a preference"""
    stmt = select(UserPreference).where(UserPreference.key == key)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Preference not found")
        
    await db.delete(existing)
    await db.commit()
