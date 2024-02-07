
import logging
import typing

import pydantic
import sqlmodel

L = logging.getLogger("lib_n2t")

SCHEME_DELIMITER = ":"


def get_scheme(identifier: str) -> tuple[str, typing.Optional[str]]:
    """
    Splits an identifier into scheme, value.

    The delimiting character is a colon (":") and it is assumed the input
    identifier string has been pre-processed. For example, a DOI identifier
    will often be expressed as a URL like "https://doi.org/10.12345/foo"
    instead of the expected form of "doi:10.12345/foo". A preprocessor
    should be used to convert to the expected form.

    Scheme is always returned as lower case with white space trimmed from the start and end.

    Args:
        identifier: An identifier string

    Returns: (scheme, value)

    """
    identifier = identifier.strip()
    parts = identifier.split(SCHEME_DELIMITER, 1)
    scheme = parts[0].strip().lower()
    value = None
    try:
        value = parts[1].strip()
    except IndexError:
        pass
    return scheme, value


class IdentifierNAA(sqlmodel.SQLModel, table=True):
    prefix: str = sqlmodel.Field(primary_key=True)
    parent: typing.Optional[str] = None
    delimiter: typing.Optional[str]
    max_split: int = 1

    def split_value(self, v: str) -> tuple[str, typing.Optional[str]]:
        """
        Split the identifier value v into parts according to scheme rules.

        Args:
            v: the value part of an identifier (portion after scheme)

        Returns: tuple of identifier parts
        """
        if self.delimiter is None:
            return (v, )
        return v.split(self.delimiter, self.max_split)


class NormalizedIdentifier(pydantic.BaseModel):
    original: str
    normal: str
    value: typing.Optional[str] = None
    scheme: typing.Optional[str] = None
    naan: typing.Optional[str] = None
    url: typing.Optional[str] = None


class IdentifierResolver(pydantic.BaseModel):
    id: str
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


def normalize_identifier(identifier: str) -> [NormalizedIdentifier, str]:
    """

    Args:
        identifier:

    Returns:

    """
    _scheme, _value = get_scheme(identifier)
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



