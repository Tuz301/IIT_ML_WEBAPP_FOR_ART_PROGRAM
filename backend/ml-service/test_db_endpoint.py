"""
Simple test to check if the get_db dependency works
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models import User

router = APIRouter()

@router.get("/test-db")
def test_db_endpoint(db: Session = Depends(get_db)):
    """Test endpoint to check if database dependency works"""
    try:
        # Simple query
        user_count = db.query(User).count()
        return {"status": "success", "user_count": user_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/test-user/{username}")
def test_user_endpoint(username: str, db: Session = Depends(get_db)):
    """Test endpoint to check if user query works"""
    try:
        from sqlalchemy.orm import joinedload
        user = db.query(User).options(joinedload(User.roles)).filter(
            User.username == username
        ).first()
        if user:
            return {
                "status": "success",
                "username": user.username,
                "email": user.email,
                "roles": [r.name for r in user.roles]
            }
        else:
            return {"status": "error", "message": "User not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
