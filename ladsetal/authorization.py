from functools import wraps
from starlette.requests import HTTPConnection
from starlette.authentication import (
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
    AuthCredentials,
    UnauthenticatedUser,
)

from ladsetal import settings

class User(SimpleUser):
    is_authed = True

    def __init__(self, username: str, discord_id: int):
        super().__init__(username)
        self.discord_id = discord_id


class LUnauthenticatedUser(UnauthenticatedUser):
    is_authed = False


def wrap_result_auth(f):
    @wraps(f)
    async def inner(*args, **kwargs):
        r = await f(*args, **kwargs)
        if r is None:
            return AuthCredentials(), LUnauthenticatedUser()
        return r

    return inner


class TokenAuthBackend(AuthenticationBackend):
    @wrap_result_auth
    async def authenticate(self, request: HTTPConnection):
        if "discord_id" not in request.session:
            request.session.pop("user", None)
            return

        user = request.session.get("user")
        if not user:
            uid = request.session["discord_id"]

            if uid not in settings.LADS:
                return
            user = {
                "discord_id": uid,
                "username": request.session["discord_username"],
            }
            request.session["user"] = user

        username, discord_id = (
            user["username"],
            user["discord_id"],
        )

        creds = ["authenticated"]

        return AuthCredentials(creds), User(username, discord_id)


def can_edit(request):
    return request.user.is_authenticated
