"""Add blast_name to ScheduledBlast

Revision ID: a0bbc39409c1
Revises: 1327fffbdc61
Create Date: 2024-10-19 04:12:23.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a0bbc39409c1'
down_revision = '1327fffbdc61'
branch_labels = None
depends_on = None


def upgrade():
    # Add blast_name column as nullable
    op.add_column('scheduled_blast', sa.Column('blast_name', sa.String(100), nullable=True))
    
    # Update existing rows with a default value
    op.execute("UPDATE scheduled_blast SET blast_name = 'Unnamed Blast' WHERE blast_name IS NULL")
    
    # Make the column non-nullable
    op.alter_column('scheduled_blast', 'blast_name', nullable=False)


def downgrade():
    op.drop_column('scheduled_blast', 'blast_name')
