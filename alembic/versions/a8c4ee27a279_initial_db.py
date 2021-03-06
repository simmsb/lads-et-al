"""Initial db

Revision ID: a8c4ee27a279
Revises: 
Create Date: 2021-04-05 03:44:33.419474

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from sqlalchemy.dialects import postgresql
from sqlalchemy_searchable import sync_trigger, sql_expressions

# revision identifiers, used by Alembic.
revision = 'a8c4ee27a279'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()

    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table('blogs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('slug', sa.Text(), nullable=False),
    sa.Column('tags', postgresql.ARRAY(sa.Text()), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('creation_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('edit_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('search_vector', sqlalchemy_utils.types.ts_vector.TSVectorType("title", "content", weights={
        "title": "A", "content": "B"
    }), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug'),
    sa.UniqueConstraint('title')
    )
    op.create_index('blogs_tags_array_idx', 'blogs', ['tags'], unique=False, postgresql_using='gin')
    op.create_table('images',
    sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
    sa.Column('filetype', sa.Text(), nullable=False),
    sa.Column('image', sa.LargeBinary(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    conn.execute(sql_expressions.statement)

    sync_trigger(conn, "blogs", "search_vector", ["title", "content"])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('images')
    op.drop_index('blogs_tags_array_idx', table_name='blogs')
    op.drop_table('blogs')

    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
    # ### end Alembic commands ###
