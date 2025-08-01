"""create coach table

Revision ID: 518770b79653
Revises: bd40c932d853
Create Date: 2025-05-27 22:05:02.719137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '518770b79653'
down_revision: Union[str, None] = 'bd40c932d853'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('coaches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('firstname', sa.String(length=100), nullable=True),
    sa.Column('lastname', sa.String(length=100), nullable=True),
    sa.Column('age', sa.Integer(), nullable=True),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('birth_place', sa.String(length=100), nullable=True),
    sa.Column('birth_country', sa.String(length=100), nullable=True),
    sa.Column('nationality', sa.String(length=100), nullable=True),
    sa.Column('height', sa.String(length=20), nullable=True),
    sa.Column('weight', sa.String(length=20), nullable=True),
    sa.Column('photo_url', sa.String(length=255), nullable=True),
    sa.Column('team_id', sa.Integer(), nullable=True),
    sa.Column('career', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_coaches_id'), 'coaches', ['id'], unique=False)
    op.create_index(op.f('ix_coaches_lastname'), 'coaches', ['lastname'], unique=False)
    op.create_index(op.f('ix_coaches_name'), 'coaches', ['name'], unique=False)
    op.create_index(op.f('ix_coaches_team_id'), 'coaches', ['team_id'], unique=False)
    op.create_table('coaches_careers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('coach_id', sa.Integer(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('team_name', sa.String(length=150), nullable=False),
    sa.Column('logo_url', sa.String(length=255), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['coach_id'], ['coaches.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_coaches_careers_coach_id'), 'coaches_careers', ['coach_id'], unique=False)
    op.create_index(op.f('ix_coaches_careers_id'), 'coaches_careers', ['id'], unique=False)
    op.create_index(op.f('ix_coaches_careers_team_id'), 'coaches_careers', ['team_id'], unique=False)
    op.create_index(op.f('ix_coaches_careers_team_name'), 'coaches_careers', ['team_name'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_coaches_careers_team_name'), table_name='coaches_careers')
    op.drop_index(op.f('ix_coaches_careers_team_id'), table_name='coaches_careers')
    op.drop_index(op.f('ix_coaches_careers_id'), table_name='coaches_careers')
    op.drop_index(op.f('ix_coaches_careers_coach_id'), table_name='coaches_careers')
    op.drop_table('coaches_careers')
    op.drop_index(op.f('ix_coaches_team_id'), table_name='coaches')
    op.drop_index(op.f('ix_coaches_name'), table_name='coaches')
    op.drop_index(op.f('ix_coaches_lastname'), table_name='coaches')
    op.drop_index(op.f('ix_coaches_id'), table_name='coaches')
    op.drop_table('coaches')
    # ### end Alembic commands ###
