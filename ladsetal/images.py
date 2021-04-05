import imghdr
from typing import List, Tuple

import orjson
import sqlalchemy as sa
from starlette.endpoints import HTTPEndpoint
from starlette.requests import HTTPConnection
from starlette.responses import Response, JSONResponse
from starlette.authentication import requires
from starlette.routing import Router

from ladsetal.models import Image

from ladsetal.utils import abort
from ladsetal import converters

# magick happens here
converters.inject()

router = Router()


class ORJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return orjson.dumps(content)


@router.route("/{file_name:file}", name="images")
class Images(HTTPEndpoint):
    async def get(self, request: HTTPConnection):
        uuid, ext = request.path_params["file_name"]

        image = await Image.get(uuid)

        if image is None or image.filetype != ext:
            return abort(404)

        headers = {
            "Cache-Control": "public, max-age=604800, immutable",
        }

        return Response(image.image, media_type=f"image/{image.filetype}", headers=headers)

    @requires("authenticated")
    async def delete(self, request: HTTPConnection):
        uuid, ext = request.path_params["file_name"]

        image = await Image.get(uuid)

        if image.filetype != ext:
            return abort(404)

        await image.delete()

        return Response()


@router.route("/upload", methods=["POST"])
@requires("authenticated")
async def image_upload(request: HTTPConnection):
    form = await request.form()

    file_contents = await form["file"].read()

    filetype = imghdr.what("dynamic", file_contents)
    if filetype not in {"png", "jpeg", "gif", "webp"}:
        return abort(400, "Bad image type")

    file = await Image.create(
        filetype=filetype, image=file_contents
    )

    return ORJSONResponse({"filename": f"{file.id}.{filetype}"})


async def get_existing_images() -> List[Tuple[str, str]]:
    return (
        await sa.select([Image.id, Image.filetype])
        .gino.all()
    )


async def encoded_existing_images(request: HTTPConnection) -> bytes:
    images = await get_existing_images()
    images = [
        {
            "filename": f"{id}.{ext}",
            "path": request.url_for("images", file_name=(id, ext)),
        }
        for (id, ext) in images
    ]
    return orjson.dumps(images)
