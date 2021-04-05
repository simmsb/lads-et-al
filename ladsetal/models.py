from gino import Gino
from slug import slug
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_utils.types import TSVectorType

from ladsetal import settings

db = Gino()

async def init_db():
    await db.set_bind(settings.DB_URL)

class Image(db.Model):
    __tablename__ = "images"

    id = db.Column(UUID(), primary_key=True, server_default=func.uuid_generate_v4())

    filetype = db.Column(db.Text(), nullable=False)
    image = db.Column(db.LargeBinary(), nullable=False)


class Blog(db.Model):
    __tablename__ = "blogs"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.Text(), nullable=False, unique=True)
    slug = db.Column(db.Text(), nullable=False, unique=True)

    tags = db.Column(ARRAY(db.Text()), nullable=False)
    content = db.Column(db.Text(), nullable=False)

    creation_date = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    edit_date = db.Column(
        db.DateTime,
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    search_vector = db.Column(
        TSVectorType("title", "content", weights={"title": "A", "content": "B"})
    )

    _tags_idx = db.Index("blogs_tags_array_idx", "tags", postgresql_using="gin")

    @classmethod
    def create_auto(cls, *args, **kwargs):
        if "slug" not in kwargs:
            kwargs["slug"] = slug(kwargs["title"])
        return cls.create(*args, **kwargs)

    def update_auto(self, *args, **kwargs):
        if "slug" not in kwargs:
            kwargs["slug"] = slug(kwargs["title"])
        return self.update(*args, **kwargs)
