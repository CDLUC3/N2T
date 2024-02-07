"""FastAPI router implementing identifier resolver functionality.
"""
import os
import typing
import fastapi
import lib_n2t.model
import lib_n2t.pidparse
import lib_n2t.pidconfig
import micron2t.config


router = fastapi.APIRouter(
    tags=["resolve"],
)

settings = micron2t.config.settings

pid_parser = lib_n2t.pidparse.BasePidParser(
    config=lib_n2t.pidconfig.PidConfig(settings.prefix_base_config)
)


@router.get(
    "/.info/{identifier:path}",
    summary="Retrieve information about the provided identifier.",
)
def get_info(
        request: fastapi.Request,
        identifier: typing.Optional[str] = None,
):
    request_url = str(request.url)
    raw_identifier = request_url[request_url.find(identifier):]
    return {
        "identifier": identifier,
        "raw_identifier": raw_identifier,
    }


@router.get(
    "/{identifier:path}",
    summary="Redirect to the identified resource or present resolver information.",
)
def get_resolve(
    request: fastapi.Request,
    identifier: typing.Optional[str] = None,
):
    # ARK resolvers have wierd behavior of providing an
    # introspection ("inflection") when the URL ends with
    # "?", "??", or "?info". Need to examine the raw URL
    # to determine these.
    is_introspection = False
    request_url = str(request.url)
    for check in ("?", "??", "?info"):
        if request_url.endswith(check):
            is_introspection = True
            break
    # Get the raw identifier, i.e. the identifier with any accoutrements
    raw_identifier = request_url[request_url.find(identifier):]
    pid = lib_n2t.model.ParsedPid(raw_identifier)
    parsed_pid = pid_parser.parse(pid)
    return {
        "identifier": identifier,
        "raw_identifier": raw_identifier,
        "is_introspection": is_introspection,
        "prefix_base_config": os.path.abspath(settings.prefix_base_config),
        "parsed_pid": parsed_pid,
        "target": parsed_pid.target,
    }
