import logging
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional,Iterable
import lib_n2t.prefixes

META_ACCEPT = "application/json;profile=https://rslv.xyz/info"
PREFIX_SOURCE = "data/prefixes.json"

#logging.basicConfig(level=logging.DEBUG)
#L = logging.getLogger(__name__)

app = FastAPI(
    title="Micro N2T",
    version="0.2.0",
)

prefixes = lib_n2t.prefixes.PrefixList(fn_src=PREFIX_SOURCE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", ],
    allow_credentials=True,
    allow_methods=["GET","HEAD"],
    allow_headers=["*"],
)

@app.get(
    "/",
    summary="Return list of available resolver prefixes",
)
async def list_prefixes() -> Iterable[str]:
    return [
        row for row in prefixes.prefixes()
    ]

@app.get("/favicon.ico")
async def favicon():
    raise HTTPException(status_code=404)

@app.get(
    "/diagnostic/echo",
    summary="Echo the request as a JSON response"
)
async def echo_request(request:Request):
    return JSONResponse(
        {
            "url": str(request.url),
            "path": str(request.url.path),
            "query": {k: v for k,v in request.query_params.items()},
            "headers": {k: v for k,v in request.headers.items()},
        },
        status_code=200
    )

@app.get(
    "/about/{identifier:path}",
    summary="Get information about the resolver for the provided identifier"
)
async def get_prefix(
    request:Request,
    identifier: str=None,
    accept:Optional[str]=Header(None)
):
    '''Resolve identifier
    '''
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        return RedirectResponse("/docs")
    normalized, resolver_key, resolver = prefixes.resolve(identifier)
    if resolver_key is None:
        return JSONResponse(
            {
                "error": f"No resolver available for {identifier}",
                "detail": normalized
            },
            status_code = 404
        )
    return JSONResponse(
        resolver,
        status_code=200
    )


@app.get(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information."
)
async def resolve_prefix(
    request:Request, 
    identifier: str=None, 
    accept:Optional[str]=Header(None)
):
    '''Resolve identifier
    '''
    _inflection = False
    rurl = str(request.url)
    if rurl.endswith("?") or rurl.endswith("??"):
        _inflection = True
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        return RedirectResponse("/docs")
    normalized, resolver_key, resolver = prefixes.resolve(identifier)
    if resolver_key is None:
        return JSONResponse(
            {
                "error": f"No resolver available for {identifier}",
                "detail": normalized
            },
            status_code = 404
        )
    if _inflection:
        return JSONResponse(
            resolver,
            status_code=200
        )
    _url = normalized.get("url", None)
    if _url is None:
        return JSONResponse(
            {
                "error": f"No redirect information available for {identifier}",
                "resolver": resolver
            },
            status_code=404
        )
        raise HTTPException(status_code=404, detail=f"No redirect available for: {identifier}")

    if accept == META_ACCEPT:
        return {
            "resolver": resolver,
            "redirect": _url,
        }        
    return RedirectResponse(_url)
