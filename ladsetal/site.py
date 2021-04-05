from pathlib import Path
from typing import List, Tuple

from starlette.applications import Starlette
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.authentication import requires
from starlette.endpoints import HTTPEndpoint
from starlette.routing import Mount, Route
from starlette.requests import HTTPConnection
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.config import Config

from ladsetal.authorization import TokenAuthBackend, can_edit
from ladsetal.templater import templates
from ladsetal.images import router as images_router
from ladsetal.blog import router as blog_router
from ladsetal.oauth import router as oauth_router
from ladsetal.middleware import BlockerMiddleware, CSPMiddleware, HSTSMiddleware, WebSecMiddleware
from ladsetal import settings

from ladsetal.models import init_db


root_dir = Path(__file__).parent

app = Starlette(
    routes=[
        Mount("/images", app=images_router),
        Mount("/oauth", app=oauth_router),
    ]
)

app.add_middleware(HSTSMiddleware)
app.add_middleware(WebSecMiddleware)
app.add_middleware(
    CSPMiddleware,
    script_src=(
        "'self'",
        "www.googletagmanager.com",
        "www.google-analytics.com",
        "'sha256-gUOO8cVce0Qg1lxrPgv8NIo//GS1rTLlhFvALeuQ3kg='"
    ),
    connect_src=(
        "'self'",
        "www.google-analytics.com"
    ),
    default_src=(
        "'self'",
        "use.fontawesome.com",
        "unpkg.com",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
    ),
    style_src=("'self'", "use.fontawesome.com", "unpkg.com", "fonts.googleapis.com", "cdn.jsdelivr.net"),
)
app.add_middleware(AuthenticationMiddleware, backend=TokenAuthBackend())
app.add_middleware(SessionMiddleware, secret_key=settings.TOKEN_SECRET)
app.add_middleware(BlockerMiddleware, checks=[lambda h: "httrack" not in h["user-agent"].lower()], fail=Response("who thought this was a good idea?", 418))

class CacheHeaderStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        r = await super().get_response(path, scope)
        r.headers.append("Cache-Control", "public")
        r.headers.append("Cache-Control", "must-revalidate")
        r.headers.append("Cache-Control", "max-age=360")

        return r

statics = CacheHeaderStaticFiles(directory=str(root_dir / "static"))
app.mount("/static", statics, name="static")
app.mount("/", blog_router)

templates.env.globals.update(can_edit=can_edit)

@app.route("/robots.txt")
async def view_robots(request: HTTPConnection):
    return await statics.get_response("robots.txt", request.scope)

@app.on_event("startup")
async def startup():
    await init_db()
