# app/dependencies.py
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Generator

from .utils.database import get_db as get_db_session
from .auth import get_current_user

# Re-export for convenience
get_db = get_db_session
