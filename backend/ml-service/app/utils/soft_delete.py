"""
Soft Delete Utility for SQLAlchemy Models

Provides soft delete functionality for models with a deleted_at column.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import inspect
from sqlalchemy.sql import and_


class SoftDeleteMixin:
    """
    Mixin class for models that support soft deletes.
    
    Models using this mixin should have a `deleted_at` column.
    """
    
    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted"""
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Mark the record as deleted"""
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore a soft deleted record"""
        self.deleted_at = None


class SoftDeleteQuery:
    """
    Query helper for soft delete operations.
    
    Provides methods to filter out soft deleted records from queries.
    """
    
    @staticmethod
    def filter_not_deleted(model):
        """
        Filter query to exclude soft deleted records.
        
        Args:
            model: SQLAlchemy model class with deleted_at column
            
        Returns:
            SQLAlchemy filter expression
        """
        if hasattr(model, 'deleted_at'):
            return model.deleted_at.is_(None)
        return True  # No filtering if model doesn't have deleted_at
    
    @staticmethod
    def filter_deleted(model):
        """
        Filter query to only include soft deleted records.
        
        Args:
            model: SQLAlchemy model class with deleted_at column
            
        Returns:
            SQLAlchemy filter expression
        """
        if hasattr(model, 'deleted_at'):
            return model.deleted_at.isnot(None)
        return False  # No records if model doesn't have deleted_at
    
    @staticmethod
    def include_deleted(query):
        """
        Modify query to include both active and soft deleted records.
        
        Args:
            query: SQLAlchemy query object
            
        Returns:
            Modified query
        """
        return query  # Return query as-is (no filtering)
    
    @staticmethod
    def only_deleted(query, model):
        """
        Modify query to only return soft deleted records.
        
        Args:
            query: SQLAlchemy query object
            model: SQLAlchemy model class
            
        Returns:
            Modified query
        """
        if hasattr(model, 'deleted_at'):
            return query.filter(model.deleted_at.isnot(None))
        return query.filter(False)  # Return no records if model doesn't have deleted_at


def soft_delete_model(model_class, session, record_id):
    """
    Soft delete a record by ID.
    
    Args:
        model_class: SQLAlchemy model class
        session: SQLAlchemy session
        record_id: ID of the record to soft delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        record = session.query(model_class).get(record_id)
        if record and hasattr(record, 'deleted_at'):
            record.deleted_at = datetime.utcnow()
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e


def restore_model(model_class, session, record_id):
    """
    Restore a soft deleted record by ID.
    
    Args:
        model_class: SQLAlchemy model class
        session: SQLAlchemy session
        record_id: ID of the record to restore
        
    Returns:
        True if successful, False otherwise
    """
    try:
        record = session.query(model_class).get(record_id)
        if record and hasattr(record, 'deleted_at'):
            record.deleted_at = None
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e


def permanently_delete_model(model_class, session, record_id):
    """
    Permanently delete a record (hard delete).
    
    This should be used with caution and typically only by administrators.
    
    Args:
        model_class: SQLAlchemy model class
        session: SQLAlchemy session
        record_id: ID of the record to permanently delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        record = session.query(model_class).get(record_id)
        if record:
            session.delete(record)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
