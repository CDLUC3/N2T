'''
MicroN2T - General purpose identifier resolver service
'''
import json
import logging.config
import typing
import urllib.parse

import config
import uvicorn
import fastapi
import fastapi.responses
import fastapi.middleware.cors

import routers.resolver

INFO_PROFILE: str = "https://rslv.xyz/info/"
META_ACCEPT: str = "application/json;profile=https://rslv.xyz/info/"
PREFIX_SOURCE: str = "data/config.json"
VERSION = "0.6.0"
URL_SAFE_CHARS = ":/%#?=@[]!$&'()*+,;"

logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
L = logging.getLogger("resolver")

# Intialize the application
app = fastapi.FastAPI(
    title="Micro N2T",
    description=__doc__,
    version=VERSION,
    contact={"name": "Dave Vieglais", "url": "https://github.com/datadavev/"},
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/mit/",
    },
)

# Enables CORS for UIs on different domains
app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "HEAD",
    ],
    allow_headers=[
        "*",
    ],
)


@app.get(
    "/",
    include_in_schema=False
)
async def redirect_docs():
    return fastapi.responses.RedirectResponse(url='/docs')


app.include_router(routers.resolver.router)



if __name__ == "__main__":
    uvicorn.run("app:app", port=config.settings.port, host=config.settings.host)
