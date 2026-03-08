"""add soft deletes to core models

Revision ID: add_soft_deletes
Revises: rename_metadata_to_extra_metadata
Create Date: 2025-03-05 16:09:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision = 'add_soft_deletes'
down_revision = 'rename_metadata_to_extra_metadata'
branch_labels = None
depends_on = None


def upgrade():
    """Add soft delete columns to core models."""
    
    # Check if we're using PostgreSQL or SQLite
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    # Add deleted_at column to patients table
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if dialect == 'postgresql':
            batch_op.create_index('idx_patients_deleted_at', 'patients', ['deleted_at'])
        else:
            # SQLite doesn't support concurrent index creation
            op.create_index('idx_patients_deleted_at', 'patients', ['deleted_at'])
    
    # Add deleted_at column to visits table
    with op.batch_alter_table('visits', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if dialect == 'postgresql':
            batch_op.create_index('idx_visits_deleted_at', 'visits', ['deleted_at'])
        else:
            op.create_index('idx_visits_deleted_at', 'visits', ['deleted_at'])
    
    # Add deleted_at column to iit_predictions table
    with op.batch_alter_table('iit_predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if dialect == 'postgresql':
            batch_op.create_index('idx_preds_deleted_at', 'iit_predictions', ['deleted_at'])
        else:
            op.create_index('idx_preds_deleted_at', 'iit_predictions', ['deleted_at'])


def downgrade():
    """Remove soft delete columns from core models."""
    
    # Remove indexes first
    op.drop_index('idx_patients_deleted_at', table_name='patients')
    op.drop_index('idx_visits_deleted_at', table_name='visits')
    op.drop_index('idx_preds_deleted_at', table_name='iit_predictions')
    
    # Remove columns
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
    
    with op.batch_alter_table('visits', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
    
    with op.batch_alter_table('iit_predictions', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
