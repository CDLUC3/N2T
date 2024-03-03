import fastapi
import fastapi.staticfiles
import fastapi.templating

import rslv.routers.resolver

from .config import settings
from . import __version__

app = fastapi.FastAPI(
    title="N2T",
    description=__doc__,
    version=__version__,
    contact={"name": "Dave Vieglais", "url": "https://github.com/datadavev/"},
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/mit/",
    },
    # Need to add this here because adding to the router has no effect.
    lifespan=rslv.routers.resolver.resolver_lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api",
)

app.mount(
    "/static",
    fastapi.staticfiles.StaticFiles(directory=settings.static_dir),
    name="static",
)


templates = fastapi.templating.Jinja2Templates(
    directory=settings.template_dir
)
@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    raise fastapi.HTTPException(status_code=404, detail="Not found")

@app.get("/", include_in_schema=False)
async def redirect_docs(request:fastapi.Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.include_router(rslv.routers.resolver.router)
