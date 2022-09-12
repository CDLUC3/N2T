
import pydantic


def parseIdentifier(identifier:str) -> tuple:
    identifier = identifier.strip()
    parts = identifier.split(":", 1)
    scheme = parts[0].strip().lower()
    value = None
    try:
        value = parts[1].strip()
    except IndexError:
        pass
    return scheme, value


def normalizeIdentifier(identifier:str) -> dict:
    res = {
        "original": identifier,
        "normal": None,
        "resolver_key": None,
        "scheme": None,
        "value": None,
        "naan": None,
    }
    res["scheme"], res["value"] = parseIdentifier(identifier)
    _v = res["value"]
    res["resolver_key"] = res["scheme"]
    if res["value"] is not None:
        res["resolver_key"] = f"{res['scheme']}:{res['value']}"

    # Ensure ark identifier values have the form "ark:/..."
    # And get the naan and 
    if res["scheme"] == "ark":
        if _v is not None and len(_v) > 0:
            if _v[0] != "/":
                _v = f"/{_v}"
            res["naan"] = _v[1:]
            try:
                res["naan"], res["suffix"] = _v[1:].split("/",1)
            except ValueError:
                pass
            res['value'] = _v
            res['resolver_key'] = f"{res['scheme']}:{res['value']}"
    #elif res["scheme"] == "doi":
    #    res["resolver_key"] = "doi"
    res["normal"] = f"{res['scheme']}:{res['value']  if res['value'] is not None else ''}"
    return res


class IdentifierPrefix(pydantic.BaseModel):
    id:str
    idtype: str
    redirect: str
    name: typing.Optional[str] = None
    alias: typing.Optional[str] = None
    provider: typing.Optional[str] = None
    provider_id: typing.Optional[str] = None
    description: typing.Optional[str] = None
    subject: typing.Optional[str] = None
    location: typing.Optional[str] = None
    institution: typing.Optional[str] = None
    more: typing.Optional[str] = None
    test: typing.Optional[str] = None

    _primary: int = 1
    _prefixed: int = 0
    _sort_score: int = 1
    _synonym: typing.Optional[str] = None

    class Config:
        underscore_attrs_are_private = True


class IdentifierPrefixes(pydantic.BaseModel):
    pass

