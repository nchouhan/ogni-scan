"""Add openai_file_id column to resumes table

Revision ID: 0c48650a9428
Revises: 
Create Date: 2025-07-08 09:44:08.847962

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0c48650a9428'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Only add the openai_file_id column to the resumes table
    op.add_column('resumes', sa.Column('openai_file_id', sa.String(length=255), nullable=True), schema='cogni')

def downgrade() -> None:
    # Remove the openai_file_id column from the resumes table
    op.drop_column('resumes', 'openai_file_id', schema='cogni') 