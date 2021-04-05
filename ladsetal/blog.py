from itertools import groupby
from textwrap import shorten
from typing import List, Tuple
import calendar

import sqlalchemy as sa
import orjson
from sqlalchemy_searchable import search as pg_search
from sqlalchemy_searchable import search_manager
from starlette.authentication import requires
from starlette.endpoints import HTTPEndpoint
from starlette.requests import HTTPConnection
from starlette.routing import Router

from ladsetal.utils import abort, redirect_response
from ladsetal.forms import PostForm
from ladsetal.markdown import (
    highlight_markdown,
    length_constrained_plaintext_markdown,
)
from ladsetal.templater import templates
from ladsetal.images import encoded_existing_images

from ladsetal.models import Blog, db

router = Router()


@router.route("/")
async def blog_index(request: HTTPConnection):
    latest = await Blog.query.order_by(sa.desc(Blog.creation_date)).gino.all()

    rendered = [(w, length_constrained_plaintext_markdown(w.content)) for w in latest]

    return templates.TemplateResponse(
        "blog/index.j2", {"request": request, "blog": rendered}
    )


@router.route("/view/{slug}")
async def blog_view(request: HTTPConnection):
    slug = request.path_params["slug"]

    blog = await Blog.query.where(Blog.slug == slug).gino.first()

    if blog is None:
        return abort(404, "Blog not found")

    rendered = highlight_markdown(blog.content)

    return templates.TemplateResponse(
        "blog/view.j2", {"blog": blog, "request": request, "rendered": rendered}
    )


@router.route("/tag/{tag}")
async def blog_by_tag(request: HTTPConnection):
    tag = request.path_params["tag"]

    blog = (
        await Blog.query.where(Blog.tags.contains([tag]))
        .order_by(sa.desc(Blog.creation_date))
        .gino.all()
    )

    rendered = [(w, length_constrained_plaintext_markdown(w.content)) for w in blog]

    return templates.TemplateResponse(
        "blog/index.j2", {"request": request, "blog": rendered}
    )


async def get_all_tags():
    tags = (
        await sa.select([sa.column("tag")])
        .select_from(Blog)
        .select_from(sa.func.unnest(Blog.tags).alias("tag"))
        .group_by(sa.column("tag"))
        .order_by(sa.func.count())
        .gino.all()
    )

    return [i for (i,) in tags]


@router.route("/tags")
async def blog_all_tags(request: HTTPConnection):
    tags = await get_all_tags()

    return templates.TemplateResponse(
        "blog/tag_list.j2", {"request": request, "tags": tags}
    )


@router.route("/search")
async def blog_search(request: HTTPConnection):
    s_query = request.query_params.get("search", "")

    # sorry about this
    query = pg_search(sa.select([Blog]), s_query, sort=True)
    query = query.column(
        sa.func.ts_headline(
            search_manager.options["regconfig"],
            Blog.content,
            sa.func.tsq_parse(search_manager.options["regconfig"], s_query),
            f"StartSel=**,StopSel=**,MaxWords=70,MinWords=30,MaxFragments=3",
        ).label("headline")
    )

    blog = await query.as_scalar().gino.all()

    def build_blog(r):
        """we get back a RowProxy so manually construct the blog from it."""

        blog = Blog(
            id=r.id,
            title=r.title,
            slug=r.slug,
            tags=r.tags,
            content=r.content,
            creation_date=r.creation_date,
            edit_date=r.edit_date,
        )

        return blog

    blog = [(build_blog(r), r.headline) for r in blog]

    rendered = [
        (w, length_constrained_plaintext_markdown(headline)) for (w, headline) in blog
    ]

    return templates.TemplateResponse(
        "blog/index.j2", {"request": request, "blog": rendered, "query": s_query}
    )


@router.route("/delete/{id:int}")
@requires("authenticated")
async def blog_delete(request: HTTPConnection):
    id = request.path_params["id"]

    blog = await Blog.get(id)

    if blog is None:
        return abort(404, "Blog not found")

    await blog.delete()

    return redirect_response(url=request.url_for("blog_index"))


@router.route("/new")
class NewBlog(HTTPEndpoint):
    @requires("authenticated")
    async def get(self, request: HTTPConnection):
        form = PostForm()

        images = await encoded_existing_images(request)
        tags = orjson.dumps(await get_all_tags())

        return templates.TemplateResponse(
            "blog/new.j2",
            {
                "request": request,
                "form": form,
                "existing_images": images,
                "existing_tags": tags,
            },
        )

    @requires("authenticated")
    async def post(self, request: HTTPConnection):
        form = await request.form()

        form = PostForm(form)

        is_valid = form.validate()

        if (
            await Blog.query.where(Blog.title == form.title.data).gino.first()
            is not None
        ):
            is_valid = False
            form.title.errors.append(
                f"A blog with the title '{form.title.data}' already exists."
            )

        if is_valid:
            blog = await Blog.create_auto(
                title=form.title.data, tags=form.tags.data, content=form.content.data
            )

            url = request.url_for("blog_view", slug=blog.slug)

            return redirect_response(url=url)

        images = await encoded_existing_images(request)
        tags = orjson.dumps(await get_all_tags())

        return templates.TemplateResponse(
            "blog/new.j2",
            {
                "request": request,
                "form": form,
                "existing_images": images,
                "existing_tags": tags,
            },
        )


@router.route("/edit/{id:int}")
class EditBlog(HTTPEndpoint):
    @requires("authenticated")
    async def get(self, request: HTTPConnection):
        id = request.path_params["id"]

        blog = await Blog.get(id)

        if blog is None:
            return abort(404, "Blog not found")

        form = PostForm(title=blog.title, tags=blog.tags, content=blog.content)

        images = await encoded_existing_images(request)
        tags = orjson.dumps(await get_all_tags())

        return templates.TemplateResponse(
            "blog/edit.j2",
            {
                "request": request,
                "form": form,
                "blog": blog,
                "existing_images": images,
                "existing_tags": tags,
            },
        )

    @requires("authenticated")
    async def post(self, request: HTTPConnection):
        id = request.path_params["id"]

        blog = await Blog.get(id)

        if blog is None:
            return abort(404, "Blog not found")

        form = await request.form()

        form = PostForm(form)

        if form.validate():
            await blog.update_auto(
                title=form.title.data, tags=form.tags.data, content=form.content.data
            ).apply()

            url = request.url_for("blog_view", slug=blog.slug)

            return redirect_response(url=url)

        images = await encoded_existing_images(request)
        tags = orjson.dumps(await get_all_tags())

        return templates.TemplateResponse(
            "blog/edit.j2",
            {
                "request": request,
                "form": form,
                "blog": blog,
                "existing_images": images,
                "existing_tags": tags,
            },
        )
