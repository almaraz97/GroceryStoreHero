"""empty message

Revision ID: af756d8b6de8
Revises: ad5bfd33081b
Create Date: 2020-12-17 16:54:34.218555

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'af756d8b6de8'
down_revision = 'ad5bfd33081b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('actions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('titles', sa.String(length=250), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user__pub_rec', schema=None) as batch_op:
        batch_op.alter_column('downloaded_dates',
               existing_type=sqlite.JSON(),
               nullable=False)
        batch_op.alter_column('downloaded',
               existing_type=sa.BOOLEAN(),
               nullable=False)
        batch_op.alter_column('borrowed_dates',
               existing_type=sqlite.JSON(),
               nullable=False)
        batch_op.alter_column('borrowed',
               existing_type=sa.BOOLEAN(),
               nullable=False)

    with op.batch_alter_table('pub__rec', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.VARCHAR(length=64), nullable=False))
        batch_op.alter_column('ogusername',
               existing_type=sa.VARCHAR(length=64),
               nullable=True)

    with op.batch_alter_table('actions', schema=None) as batch_op:
        batch_op.alter_column('recipe_ids',
               existing_type=sqlite.JSON(),
               nullable=False,
               existing_server_default=sa.text("'[]'"))
        batch_op.drop_column('title')

    # ### end Alembic commands ###