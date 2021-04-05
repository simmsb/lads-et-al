from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings, Secret


config = Config()

TOKEN_SECRET = config("TOKEN_SECRET", cast=Secret)
DB_URL = config("DB_URL")
LADS = [int(x) for x in config("LADS", cast=CommaSeparatedStrings)]
