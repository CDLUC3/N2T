import re
import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from databases import Database
from typing import Iterable

database = Database(f"sqlite:///data/prefixes.sqlite")

app = FastAPI(
    title="Micro N2T",
    version="0.1.5",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", ],
    allow_credentials=True,
    allow_methods=["GET","HEAD"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def database_connect():
    await database.connect()

@app.on_event("shutdown")
async def database_disconnect():
    await database.disconnect()

@app.get("/")
async def db_read_keys() -> Iterable[str]:
    def _getkey(row):
        return row['id']

    sql = "SELECT id FROM prefix WHERE ptype = 'scheme' ORDER BY id"
    return [
        _getkey(row) async for row in database.iterate(query=sql)
    ]

@app.get("/{identifier:path}")
async def db_resolve_prefix(request:Request, identifier: str=None):
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        return RedirectResponse("/docs")
    pfx = identifier
    val = None
    try:
        pfx,val = identifier.split(":",1)
    except ValueError as e:
        # Perhaps we received a string with no colon, see if it matches a prefix
        if not identifier in data.PREFIXES:
            return HTTPException(status_code=500, detail="Expected prefix:value")
    sql = "SELECT * FROM prefix WHERE id=:_id"
    resolver = await database.fetch_one(query=sql, values={"_id": pfx})
    return resolver

''' to be removed
@app.get("/_I/")
async def read_root():
    res = list(data.PREFIXES.keys())
    res.sort()
    return res


@app.get("/_I/{identifier:path}")
async def resolve_prefix(request:Request, identifier: str = None):
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        return RedirectResponse("/docs")
    pfx = identifier
    val = None
    try:
        pfx,val = identifier.split(":",1)
    except ValueError as e:
        # Perhaps we received a string with no colon, see if it matches a prefix
        if not identifier in data.PREFIXES:
            return HTTPException(status_code=500, detail="Expected prefix:value")
    pfx = pfx.lower()
    # Get the resolver by looking up the prefix.
    resolver = data.PREFIXES.get(pfx, None)
    if resolver is None:
        raise HTTPException(status_code=404, detail=f"No resolver for {pfx}")
    # If no value was provided then return the prefix info
    if val is None or len(val) < 1:
        return resolver
    ptype = resolver.get("type", "scheme")
    if ptype == "synonym":
        pfor = resolver.get("for", None)
        if pfor is None:
            raise HTTPException(status_code=404, detail=f"No resolver for {pfx}")
        try:
            resolver = data.PREFIXES[pfor]
        except KeyError as e:
            raise HTTPException(status_code=404, detail=f"No resolver {pfor} for synonym {pfx}")
    elif ptype == "shoulder":
        raise NotImplementedError("No support for shoulders yet")
    elif ptype == "naan":
        raise NotImplementedError("No support for NAANs yet")
    # Handle scheme types
    _pattern = resolver.get("pattern", None)
    _redirect = resolver.get("redirect", None)
    if _redirect is None:
        raise HTTPException(status_code=500, detail=f"No redirect is available for prefix {pfx}.")
    # If there's no pattern to match then just redirect
    if _pattern is None:
        return RedirectResponse(_redirect.format(id=val))
    if re.match(_pattern, val):
        return RedirectResponse(_redirect.format(id=val))
    raise HTTPException(status_code=404, detail=f"Invalid identifier value for {pfx}: {val}")

'''
