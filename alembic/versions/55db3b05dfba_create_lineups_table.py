"""create lineups table

Revision ID: 55db3b05dfba
Revises: 23070c56b986
Create Date: 2025-05-20 19:56:21.968134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '55db3b05dfba'
down_revision: Union[str, None] = '23070c56b986'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('match_lineups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('match_id', sa.Integer(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('team_name', sa.String(length=100), nullable=False),
    sa.Column('formation', sa.String(length=20), nullable=True),
    sa.Column('startXI', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('substitutes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('coach_id', sa.Integer(), nullable=True),
    sa.Column('coach_name', sa.String(length=100), nullable=True),
    sa.Column('coach_photo', sa.String(length=200), nullable=True),
    sa.Column('team_colors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['match_id'], ['matches.match_id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_match_lineups_id'), 'match_lineups', ['id'], unique=False)
    op.create_index(op.f('ix_match_lineups_match_id'), 'match_lineups', ['match_id'], unique=False)
    op.create_index(op.f('ix_match_lineups_team_id'), 'match_lineups', ['team_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_match_lineups_team_id'), table_name='match_lineups')
    op.drop_index(op.f('ix_match_lineups_match_id'), table_name='match_lineups')
    op.drop_index(op.f('ix_match_lineups_id'), table_name='match_lineups')
    op.drop_table('match_lineups')
    # ### end Alembic commands ###
