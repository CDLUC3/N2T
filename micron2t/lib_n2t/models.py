import datetime
import typing
import sqlmodel
import urllib.parse


class Prefix(sqlmodel.SQLModel, table=True):

    id: str = sqlmodel.Field(default=None, primary_key=True)
    ptype: str
    name: typing.Optional[str] = None
    alias: typing.Optional[str] = None
    provider: typing.Optional[str] = None
    pprimary: typing.Optional[int] = None
    redirect: typing.Optional[str] = None
    test: typing.Optional[str] = None
    probe: typing.Optional[str] = None
    more: typing.Optional[str] = None
    forward: typing.Optional[str] = None
    description: typing.Optional[str] = None
    location: typing.Optional[str] = None
    institution: typing.Optional[str] = None
    prefixed: typing.Optional[int] = None
    provider_id: typing.Optional[str] = None
    sort_score: int = sqlmodel.Field(default=0)
    subject: typing.Optional[str] = None
    synonym: typing.Optional[str] = None
    pattern: typing.Optional[str] = None
    state: typing.Optional[str] = None
    manager: typing.Optional[str] = None
    norm: typing.Optional[str] = None
    pdate: typing.Optional[datetime.date] = None
    minter: typing.Optional[str] = None
    na_policy: typing.Optional[str] = None
    how: typing.Optional[str] = None
    registration_agency: typing.Optional[str] = None
    is_supershoulder: typing.Optional[int] = None
    datacenter: typing.Optional[str] = None
    prefix_shares_datacenter: typing.Optional[int] = None
    active: typing.Optional[int] = None
    pfor: typing.Optional[str] = None

    _field_map = {
        "ptype": "type",
        "pprimary": "primary",
        "pdate": "date",
        "pfor": "for",
    }

    @classmethod
    def fieldMap(cls):
        return cls._field_map

    @classmethod
    def inverseFieldMap(cls):
        res = {}
        for k, v in cls._field_map.items():
            res[v] = k
        return res

    @classmethod
    def columns(cls):
        res = []
        for c in cls.metadata.tables["prefix"].columns:
            res.append(c.name)
        return res

    def asDict(self, original_field_names=False):
        res = {}
        if original_field_names:
            for c in self.metadata.tables["prefix"].columns:
                res[Prefix._field_map.get(c.name, c.name)] = self.__getattribute__(c.name)
            return res
        for c in self.metadata.tables["prefix"].columns:
            v = self.__getattribute__(c.name)
            if isinstance(v, datetime.date):
                v = v.isoformat()
            res[c.name] = v
        return res

    def resolveUrl(self, identifier, force_ezid=False):
        if force_ezid and self.manager == "ezid":
            return f"https://ezid.cdlib.org/id/{identifier['normal']}"
        if self.redirect is None:
            raise ValueError(f"No redirect information for {self.id}")
        _id = urllib.parse.quote_plus(identifier["value"])
        return self.redirect.replace("$id", _id)

