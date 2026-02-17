#!/usr/bin/env python3
"""Test endpoint to verify database access"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models import User

router = APIRouter(prefix="/test", tags=["test"])

@router.get("/db")
async def test_db(db: Session = Depends(get_db)):
    """Test database access"""
    users = db.query(User).all()
    return {
        "status": "ok",
        "user_count": len(users),
        "users": [{"username": u.username, "email": u.email} for u in users]
    }

@router.get("/db-roles")
async def test_db_roles(db: Session = Depends(get_db)):
    """Test database access with roles"""
    from sqlalchemy.orm import joinedload
    users = db.query(User).options(joinedload(User.roles)).all()
    return {
        "status": "ok",
        "user_count": len(users),
        "users": [
            {
                "username": u.username,
                "email": u.email,
                "roles": [r.name for r in u.roles]
            } for u in users
        ]
    }
