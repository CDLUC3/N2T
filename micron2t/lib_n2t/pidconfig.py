import json
import os.path
import typing

class PidConfig:

    def __init__(self, entries: typing.Union[str, typing.Dict] = None, base_path: str = "."):
        self._fn_source = None
        self._base_path = base_path
        self._config = {}
        if isinstance(entries, str):
            self._fn_source = entries
            self.load(os.path.join(self._base_path, self._fn_source))
        elif isinstance(entries, dict):
            self._config = entries

    def load(self, fn_source: str) -> 'PidConfig':
        """
        Load configuration from a file.

        Can be chained like:

          config = PidConfig().load("config.json")

        Args:
            fn_source: str, name of the JSON file to load.

        Returns: self
        """
        with open(fn_source, "r") as src:
            self._config = json.load(src)
        return self

    @property
    def meta(self) -> typing.Dict:
        return self._config.get("meta", {})

    @property
    def target(self) -> typing.Optional[str]:
        return self._config.get("target", None)

    @property
    def canonical(self) -> typing.Optional[str]:
        return self._config.get("canonical", None)

    @property
    def parser(self) -> typing.Optional[str]:
        return self._config.get("parser", None)

    @property
    def keys(self):
        return (self._config.get("data", {}), )

    def get_entry(self, key: str, exact: bool = True) -> (typing.Optional['PidConfig'], typing.Optional[str]):
        """
        Get entry with longest key matching start of key.

        Exact matches are fast. Prefix matches require a scan.

        Args:
            key: entry to look up
            exact: Only return an exact match or None.

        Returns: dict
        """
        _data = self._config.get("data", {})
        try:
            _entry = _data[key]
            _synonym_for = _entry.get("synonym_for", None)
            if _synonym_for is not None:
                cfg, _syn = self.get_entry(_synonym_for, exact=exact)
                return cfg, _synonym_for
            return PidConfig(_entry, base_path=self._base_path), None
        except KeyError:
            if exact:
                return None, None
        candidate = ""
        len_candidate = len(candidate)
        for k in _data:
            if key.startswith(k):
                if len(k) > len_candidate:
                    candidate = k
                    len_candidate = len(candidate)
        if candidate == '':
            return None, None
        return PidConfig(_data[candidate], base_path=self._base_path), None
