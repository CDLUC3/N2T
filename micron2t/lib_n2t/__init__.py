
import logging
import typing
import pydantic

L = logging.getLogger("lib_n2t")


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


class NormalizedIdentifier(pydantic.BaseModel):
    original: str
    normal: str
    value: typing.Optional[str] = None
    scheme: typing.Optional[str] = None
    naan: typing.Optional[str] = None
    url: typing.Optional[str] = None


class IdentifierResolver(pydantic.BaseModel):
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


class ResolverTarget(pydantic.BaseModel):
    url: typing.Optional[str]
    resolver: IdentifierResolver

    def set_url(self, nid: NormalizedIdentifier):
        if self.resolver.redirect is not None and nid.value is not None:
            try:
                self.url = self.resolver.redirect.format(id=nid.value, nlid=nid.value)
            except KeyError as e:
                L.exception(e)


class IdentifierResolution(pydantic.BaseModel):
    input: NormalizedIdentifier
    resolution: typing.List[ResolverTarget]


def normalizeIdentifier(identifier:str) -> [NormalizedIdentifier, str]:
    _scheme, _value = parseIdentifier(identifier)
    _resolver_key = _scheme
    if _value is not None:
        _resolver_key = f"{_scheme}:{_value}"

    # Ensure ark identifier values have the form "ark:/..."
    # And get the naan and
    _naan = None
    if _scheme == "ark":
        if _value is not None and len(_value) > 0:
            if _value[0] != "/":
                _value = f"/{_value}"
            _naan = _value[1:]
            try:
                _naan, _suffix = _value[1:].split("/",1)
            except ValueError:
                pass
            _resolver_key = f"{_scheme}:{_value}"
    #elif res["scheme"] == "doi":
    #    res["resolver_key"] = "doi"
    _normal = f"{_scheme}:{_value  if _value is not None else ''}"
    res = NormalizedIdentifier(
        original=identifier,
        normal=_normal,
        value=_value,
        scheme=_scheme,
        naan=_naan
    )
    return res, _resolver_key






