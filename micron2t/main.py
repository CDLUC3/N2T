'''
MicroN2T - General purpose identifier resolver service
'''
import logging.config
import typing

import fastapi
import fastapi.responses
import fastapi.middleware.cors
import opentelemetry.instrumentation.fastapi
import uptrace

import lib_n2t.prefixes

META_ACCEPT:str = "application/json;profile=https://rslv.xyz/info"
PREFIX_SOURCE:str  = "data/prefixes.json"
VERSION = "0.5.0"

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
    summary="Return list of available resolver prefixes",
)
async def list_prefixes() -> typing.Iterable[str]:
    return [
        row for row in prefixes.prefixes()
    ]

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    raise fastapi.HTTPException(status_code=404)


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

@app.get(
    "/.info/{identifier:path}",
    summary="Present resolver information for the provided identifier"
)
async def get_prefix(
    request:fastapi.Request,
    identifier: str=None,
    #accept:typing.Optional[str]=fastapi.responses.Headers(None)
    accept:typing.Optional[str]=fastapi.Header(default=None)
):
    '''Resolve identifier
    '''
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        return fastapi.responses.RedirectResponse("/docs")
    normalized, resolver_keys, resolvers = prefixes.resolve(identifier)
    if len(resolver_keys) == 0:
        return fastapi.responses.JSONResponse(
            {
                "error": f"No resolvers available for {identifier}",
                "detail": normalized
            },
            status_code = 404
        )
    return fastapi.responses.JSONResponse(
        {
            "resolver_keys": resolver_keys,
            "resolvers":resolvers,
            "identifier": normalized,
        },
        status_code=200
    )


@app.get(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information."
)
async def resolve_prefix(
    request:fastapi.Request, 
    identifier: str=None, 
    accept:typing.Optional[str]=fastapi.Header(None)
):
    _inflection = False
    rurl = str(request.url)
    if rurl.endswith("?") or rurl.endswith("??"):
        _inflection = True
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        return fastapi.responses.RedirectResponse("/docs")
    normalized, resolver_keys, resolvers = prefixes.resolve(identifier)
    if len(resolver_keys) == 0:
        return fastapi.responses.JSONResponse(
            {
                "error": f"No resolver available for {identifier}",
                "detail": normalized
            },
            status_code = 404
        )
    if _inflection or resolver_keys[0] == normalized['normal'] :
        return fastapi.responses.JSONResponse(
            resolvers,
            status_code=200
        )
    _url = normalized.get("url", None)
    if _url is None:
        return fastapi.responses.JSONResponse(
            {
                "error": f"No redirect information available for {identifier}",
                "resolver": resolvers
            },
            status_code=404
        )

    if accept == META_ACCEPT:
        return {
            "resolver": resolvers,
            "redirect": _url,
        }        
    return fastapi.responses.RedirectResponse(_url)

