import contextlib
import functools
import typing

import fastapi
import fastapi.staticfiles
import fastapi.templating
import sqlalchemy.orm
import rslv.routers.resolver

from .config import get_settings
from . import __version__


@functools.lru_cache(maxsize=None)
def get_engine(dbcnstr: str) -> sqlalchemy.engine.base.Engine:
    return sqlalchemy.create_engine(dbcnstr, pool_pre_ping=True)


@contextlib.contextmanager
def get_dbsession(dbengine) -> typing.Iterator[sqlalchemy.orm.Session]:
    dbsession = sqlalchemy.orm.sessionmaker(bind=dbengine)()
    try:
        yield dbsession
    except Exception:
        dbsession.rollback()
        raise
    finally:
        dbsession.close()


def create_application()->fastapi.FastAPI:

    @contextlib.asynccontextmanager
    async def dbengine_lifespan(app: fastapi):
        dbcnstr = app.state.settings.db_connection_string
        app.state.dbengine = get_engine(dbcnstr)
        yield
        if app.state.dbengine is not None:
            app.state.dbengine.dispose()



    app = fastapi.FastAPI(
        title="N2T",
        description=__doc__,
        version=__version__,
        contact={"name": "Dave Vieglais", "url": "https://github.com/datadavev/"},
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/license/mit/",
        },
        lifespan=dbengine_lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api",
    )


    app.state.settings = get_settings()


    @app.middleware("http")
    async def add_db_session_middleware(request: fastapi.Request, call_next):
        with get_dbsession(request.app.state.dbengine) as dbsession:
            request.state.dbsession = dbsession
            response = await call_next(request)
            return response


    app.mount(
        "/static",
        fastapi.staticfiles.StaticFiles(directory=app.state.settings.static_dir),
        name="static",
    )


    templates = fastapi.templating.Jinja2Templates(directory=app.state.settings.template_dir)


    @app.get("/favicon.ico", include_in_schema=False)
    async def get_favicon():
        raise fastapi.HTTPException(status_code=404, detail="Not found")


    @app.get("/", include_in_schema=False)
    async def redirect_docs(request: fastapi.Request):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "environment": app.state.settings.environment,
                "version": __version__
            }
        )

    @app.get("/_{page:path}", include_in_schema=False)
    async def human_pages(request: fastapi.Request, page:str):
        return templates.TemplateResponse(
            page,
            {
                "request": request,
                "environment": app.state.settings.environment,
                "version": __version__
            }
        )

    app.include_router(
        rslv.routers.resolver.router,
    )

    return app

app = create_application()
