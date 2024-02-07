
# Add telemetry for performance metrics

#uptrace.configure_opentelemetry(service_name="n2t_resolver",service_version=VERSION)
#opentelemetry.instrumentation.fastapi.FastAPIInstrumentor.instrument_app(app)

prefixes = lib_n2t.prefixes.PrefixList(fn_src=PREFIX_SOURCE)

pid_parser = lib_n2t.pidparse.BasePidParser(
    config=lib_n2t.pidconfig.PidConfig(PREFIX_SOURCE)
)


def trace_url(url, params=None, headers=None):
    raise NotImplementedError("trace_identifier is not implemented.")


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


@app.get(
    "/diagnostic/echo/{path_val:path}",
    summary="Echo the request as a JSON response"
)
async def echo_request(request: fastapi.Request, path_val: str = None):
    return fastapi.responses.JSONResponse(
        {
            "url": str(request.url),
            "path": str(request.url.path),
            "path_val": path_val,
            "query_str": request.url.query,
            "query": {k: v for k, v in request.query_params.items()},
            "headers": {k: v for k, v in request.headers.items()},
        },
        status_code=200
    )

@app.get(
    "/.trace",
    summary="Attempt to trace resolution of the provided identifier"
)
async def trace_identifier(
        request: fastapi.Request,
        identifier: typing.Optional[str] = None,
        accept: typing.Optional[str] = fastapi.Header(default=None)
):
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        raise fastapi.HTTPException(status_code=404)
    resinfo = prefixes.info(identifier)
    _link = [
        f'<{request.url}>; rel="canonical"',
        f'</.info/{res.input.normal}>; type="application/json"; rel="alternate" profile="{INFO_PROFILE}"'
    ]
    headers = {"Link": ", ".join(_link)}
    if len(resinfo.resolution) == 0:
        return fastapi.responses.JSONResponse(
            {
                "error": f"No resolvers available for {identifier}",
                #"detail": res.dict(exclude_none=True)
            },
            status_code = 404,
            headers=headers
        )
    for target in res.resolution:
        if target.url is not None:
            _trace = trace_url(target.url)
            return {

            }
            headers["Location"] = urllib.parse.quote(target.url, safe=URL_SAFE_CHARS)
            return fastapi.responses.Response(
                content=target.json(exclude_none=True),
                status_code=307,
                headers=headers,
                media_type="application/json",
            )
    res = {"trace":identifier}
    return res


@app.get(
    "/.info/{identifier:path}",
    summary="Present resolver information for the provided identifier or part thereof",
    response_model=lib_n2t.IdentifierResolution,
    response_model_exclude_none=True
)
async def get_prefix(
    request: fastapi.Request,
    identifier: typing.Optional[str] = None,
    accept: typing.Optional[str] = fastapi.Header(default=None)
):
    """

    Args:
        request:
        identifier:
        accept:

    Returns:

    """
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        raise fastapi.HTTPException(status_code=404)

    pid = lib_n2t.model.ParsedPid(identifier)
    parsed_pid = pid_parser.parse(pid)

    _link = [
        f'<{request.url}>; rel="canonical"',
        f'</.info/{parsed_pid.canonical}>; type="application/json"; rel="alternate" profile="{INFO_PROFILE}"'
    ]
    headers = {"Link": ", ".join(_link)}
    return parsed_pid


@app.get(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information.",
    #response_model=lib_n2t.IdentifierResolution
)
async def resolve_prefix(
    request: fastapi.Request,
    identifier: typing.Optional[str]=None,
    accept: typing.Optional[str] = fastapi.Header(None)
):
    if identifier is None or len(identifier) < 1:
        # should never reach this, but just in case...
        return fastapi.responses.RedirectResponse("/docs")
    rurl = str(request.url)
    if rurl.endswith("?") or rurl.endswith("??"):
        return await get_prefix(request, identifier, accept)
    pid = lib_n2t.model.ParsedPid(identifier)
    parsed_pid = pid_parser.parse(pid)
    _link = [
        f'<{request.url}>; rel="canonical"',
        f'</.info/{parsed_pid.canonical}>; type="application/json"; rel="alternate" profile="{INFO_PROFILE}"'
    ]
    headers = {"Link": ", ".join(_link)}
    headers["Location"] = urllib.parse.quote(parsed_pid.target, safe=URL_SAFE_CHARS)
    return fastapi.responses.Response(
        content=json.dumps(parsed_pid.json_dict(), indent=2),
        status_code=307,
        headers=headers,
        media_type="application/json",
    )