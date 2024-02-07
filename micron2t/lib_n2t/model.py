import dataclasses
import datetime
import json
import typing

# WIP - the scheme registry record definitions

@dataclasses.dataclass
class ParsedPid:
    """
    Represents an identifier parsed into components. The properties are
    available for rendering as a target URL or the canonical form.

    """
    pid: str
    scheme: typing.Optional[str] = None
    group_value_raw: typing.Optional[str] = None
    target_template: str = dataclasses.field(default="{pid}")
    canon_template: str = dataclasses.field(default="{pid}")
    url_template: str = dataclasses.field(default="https://n2t.net/{pid}")

    def _get_params(self):
        params = {
            "pid": self.pid,
            "scheme": self.scheme,
        }
        if self.group_value_raw is not None:
            params["group_value_raw"] = self.group_value_raw
            params["group_value"] = self.group_value
        return params

    def json_dict(self):
        return self._get_params()

    def __str__(self):
        return self.canonical

    def __repr__(self):
        return json.dumps(self._get_params(), indent=2)

    @property
    def group_value(self):
        return self.group_value_raw

    @group_value.setter
    def group_value(self, v:str):
        self.group_value_raw = v

    @property
    def canonical(self):
        params = self._get_params()
        try:
            return self.canon_template.format(**params)
        except KeyError:
            pass
        return None

    @property
    def target(self) -> typing.Optional[str]:
        params = self._get_params()
        try:
            return self.target_template.format(**params)
        except (KeyError, AttributeError, ):
            pass
        return None


@dataclasses.dataclass
class ParsedGroupPid(ParsedPid):
    group_raw: typing.Optional[str] = None
    value_raw: typing.Optional[str] = None

    @property
    def group_value(self):
        if self.group_value_raw is None:
            return None
        return f"{self.group}/{self.value if self.value_raw is not None else ''}"

    @property
    def group(self):
        return self.group_raw

    @group.setter
    def group(self, v: str):
        self.group_raw = v

    @property
    def value(self):
        return self.value_raw

    @value.setter
    def value(self, v:str):
        self.value_raw = v

    def _get_params(self):
        params = super()._get_params()
        if self.group_raw is not None:
            params["group_raw"] = self.group_raw
            params["group"] = self.group
            if self.value_raw is not None:
                params["value_raw"] = self.value_raw
                params["value"] = self.value
        return params


@dataclasses.dataclass
class ParsedArkPid(ParsedGroupPid):

    @property
    def group(self):
        if self.group_raw is None:
            return None
        return self.group_raw.strip("/ ")

    @group.setter
    def group(self, v: str):
        self.group_raw = v

    @property
    def value(self):
        # Remove hyphens
        if self.value_raw is None:
            return None
        return self.value_raw.replace("-", "")


@dataclasses.dataclass
class ParsedDoiPid(ParsedGroupPid):

    @property
    def group(self):
        if self.group_raw is None:
            return None
        return self.group_raw.strip("/ ")

    @property
    def value(self):
        # DOIs are case insensitive
        if self.value_raw is None:
            return None
        return self.value_raw.lower()


@dataclasses.dataclass
class IdentifierSchemeSynonym:
    scheme: str
    target: str

@dataclasses.dataclass
class IdentifierScheme:
    scheme: str
    target: str
    name: typing.Optional[str] = None
    description: typing.Optional[str] = None
    organization: typing.Optional[str] = None



