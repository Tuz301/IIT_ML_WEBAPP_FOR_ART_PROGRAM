"""rename metadata to extra_metadata

Revision ID: rename_metadata_cols
Revises:
Create Date: 2025-01-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'rename_metadata_cols'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Rename metadata column to extra_metadata in interventions table
    op.alter_column('interventions', 'metadata', new_column_name='extra_metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename metadata column to extra_metadata in alerts table
    op.alter_column('alerts', 'metadata', new_column_name='extra_metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename metadata column to extra_metadata in communications table
    op.alter_column('communications', 'metadata', new_column_name='extra_metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename metadata column to extra_metadata in workflow_templates table
    op.alter_column('workflow_templates', 'metadata', new_column_name='extra_metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename metadata column to extra_metadata in follow_ups table
    op.alter_column('follow_ups', 'metadata', new_column_name='extra_metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename metadata column to extra_metadata in escalation_rules table
    op.alter_column('escalation_rules', 'metadata', new_column_name='extra_metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)


def downgrade():
    # Rename extra_metadata column back to metadata in interventions table
    op.alter_column('interventions', 'extra_metadata', new_column_name='metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename extra_metadata column back to metadata in alerts table
    op.alter_column('alerts', 'extra_metadata', new_column_name='metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename extra_metadata column back to metadata in communications table
    op.alter_column('communications', 'extra_metadata', new_column_name='metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename extra_metadata column back to metadata in workflow_templates table
    op.alter_column('workflow_templates', 'extra_metadata', new_column_name='metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename extra_metadata column back to metadata in follow_ups table
    op.alter_column('follow_ups', 'extra_metadata', new_column_name='metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)

    # Rename extra_metadata column back to metadata in escalation_rules table
    op.alter_column('escalation_rules', 'extra_metadata', new_column_name='metadata',
                    existing_type=postgresql.JSONB, existing_nullable=True)
