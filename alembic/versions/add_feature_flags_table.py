"""add feature flags table

Revision ID: add_feature_flags
Revises: rename_metadata_cols
Create Date: 2025-02-28 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_feature_flags'
down_revision = 'rename_metadata_cols'
branch_labels = None
depends_on = None


def upgrade():
    """Create the feature_flags table with support for SQLite and PostgreSQL"""
    
    # Check if we're using PostgreSQL for native array support
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        # PostgreSQL version with native ARRAY type
        op.create_table(
            'feature_flags',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('user_percentage', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('user_whitelist', postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column('environment_override', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index('idx_feature_flags_name', 'feature_flags', ['name'], unique=True)
    else:
        # SQLite version - user_whitelist stored as JSON string
        op.create_table(
            'feature_flags',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('user_percentage', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('user_whitelist', sa.JSON(), nullable=True),
            sa.Column('environment_override', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index('idx_feature_flags_name', 'feature_flags', ['name'], unique=True)


def downgrade():
    """Drop the feature_flags table"""
    op.drop_index('idx_feature_flags_name', table_name='feature_flags')
    op.drop_table('feature_flags')
