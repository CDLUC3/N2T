'''
MicroN2T - General purpose identifier resolver service
'''
import json
import logging.config
import typing
import urllib.parse

import fastapi
import fastapi.responses
import fastapi.middleware.cors
import opentelemetry.instrumentation.fastapi
import uptrace

import lib_n2t.prefixes

INFO_PROFILE:str = "https://rslv.xyz/info/"
META_ACCEPT:str = "application/json;profile=https://rslv.xyz/info/"
PREFIX_SOURCE:str  = "data/prefixes.json"
VERSION = "0.5.0"
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
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
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

# Add telemetry for performance metrics
uptrace.configure_opentelemetry(service_name="n2t_resolver",service_version=VERSION)
opentelemetry.instrumentation.fastapi.FastAPIInstrumentor.instrument_app(app)

prefixes = lib_n2t.prefixes.PrefixList(fn_src=PREFIX_SOURCE)


@app.get(
    "/",
    include_in_schema=False
)
async def redirect_docs():
    return fastapi.responses.RedirectResponse(url='/docs')


@app.get(
    "/.info",
    summary="Return list of available resolver prefixes",
)
async def list_prefixes() -> typing.Iterable[str]:
    return [
        row for row in prefixes.prefixes()
    ]

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    raise fastapi.HTTPException(status_code=404)

'''
@app.get(
    "/diagnostic/echo/{path_val:path}",
    summary="Echo the request as a JSON response"
)
async def echo_request(request:fastapi.Request, path_val:str=None):
    return fastapi.responses.JSONResponse(
        {
            "url": str(request.url),
            "path": str(request.url.path),
            "path_val": path_val,
            "query_str": request.url.query,
            "query": {k: v for k,v in request.query_params.items()},
            "headers": {k: v for k,v in request.headers.items()},
        },
        status_code=200
    )
'''

@app.get(
    "/.info/{identifier:path}",
    summary="Present resolver information for the provided identifier or part thereof",
    response_model=lib_n2t.IdentifierResolution,
    response_model_exclude_none=True
)
async def get_prefix(
    request:fastapi.Request,
    identifier: str=None,
    accept:typing.Optional[str]=fastapi.Header(default=None)
):
    '''Get resolver
    '''
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        raise fastapi.HTTPException(status_code=404)
    res = prefixes.info(identifier)
    _link = [
        f'<{request.url}>; rel="canonical"',
        f'</.info/{res.input.normal}>; type="application/json"; rel="alternate" profile="{INFO_PROFILE}"'
    ]
    headers = {"Link": ", ".join(_link)}
    if len(res.resolution) == 0:
        return fastapi.responses.JSONResponse(
            {
                "error": f"No resolvers available for {identifier}",
                #"detail": normalized
            },
            status_code = 404,
            headers=headers
        )
    return res


@app.get(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information.",
    response_model=lib_n2t.IdentifierResolution
)
async def resolve_prefix(
    request:fastapi.Request, 
    identifier: str=None, 
    accept:typing.Optional[str]=fastapi.Header(None)
):
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        return fastapi.responses.RedirectResponse("/docs")
    rurl = str(request.url)
    if rurl.endswith("?") or rurl.endswith("??"):
        return get_prefix(request, identifier, accept)
    res = prefixes.info(identifier)
    _link = [
        f'<{request.url}>; rel="canonical"',
        f'</.info/{res.input.normal}>; type="application/json"; rel="alternate" profile="{INFO_PROFILE}"'
    ]
    headers = {"Link": ", ".join(_link)}
    if len(res.resolution) == 0:
        return fastapi.responses.JSONResponse(
            {
                "error": f"No resolvers available for {identifier}",
                "detail": res.dict(exclude_none=True)
            },
            status_code = 404,
            headers=headers
        )
    for target in res.resolution:
        if target.url is not None:
            headers["Location"] = urllib.parse.quote(target.url, safe=URL_SAFE_CHARS)
            return fastapi.responses.Response(
                content=target.json(exclude_none=True),
                status_code=307,
                headers=headers,
                media_type="application/json",
            )
    # Fallback - return what we found out
    return res

