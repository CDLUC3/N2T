import os
import json
import re
import datetime
import logging
import typing
import lib_n2t

try:
    import yaml
except ImportError:
    pass
LMDB_AVAIALBLE = False
try:
    import lmdbm
    import orjson

    LMDB_AVAIALBLE = True

    class JsonLmdb(lmdbm.Lmdb):
        def _pre_key(self, value):
            return value.encode("utf-8")

        def _post_key(self, value):
            return value.decode("utf-8")

        def _pre_value(self, value):
            return orjson.dumps(value)

        def _post_value(self, value):
            return orjson.loads(value)

except ImportError:
    print("LMDB not available.")
    pass

DATE_MATCH = re.compile(r"\d{4}\.\d{2}\.\d{2}")
DATE_PATTERN = "%Y.%m.%d"

L = logging.getLogger("prefixes")


def _convert_value(v):
    """Return parsed representation of value loaded from YAML"""
    if v is None:
        return v
    v = v.strip()
    if len(v) < 1:
        return v
    vl = v.lower()
    # booleans are represented in the table
    # as optional ints, null = unset, 0 = False, 1 = True
    if vl == "true":
        return 1
    if vl == "false":
        return 0
    # try:
    #    return int(v)
    # except ValueError:
    #    pass
    if DATE_MATCH.match(v):
        try:
            nv = datetime.datetime.strptime(v, DATE_PATTERN)
            return nv.date().isoformat()
        except ValueError:
            pass
    return v


def _adjust_redirect_protocol(r, default_protocol="https"):
    """Make a redirect entry into a URL, if possible"""
    _protocols = [
        "http",
        "https",
        "ftp",
        "ftps",
        "sftp",
    ]
    try:
        a, b = r.split(":", 1)
        a = a.lower()
        if not a in _protocols:
            return f"{default_protocol}://{r.lstrip('/')}"
        return r
    except ValueError as e:
        pass
    return f"{default_protocol}://{r.lstrip('/')}"


def cleanPrefix(key, data, field_map=None):
    """Clean a prefix entry retrieved from YAML"""
    values = {}
    for k, v in data.items():
        values[k] = _convert_value(v)
    _entry = {"id": key, "target": {}}
    _type = values.get("type")
    for field in values.keys():
        if field_map is not None:
            _entry[field_map.get(field, field)] = values[field]
        else:
            _entry[field] = values[field]
    _redirect = _entry.get("redirect", None)
    if _redirect is not None:
        _redirect = _redirect.replace("$id", "{id}")
        _redirect = _redirect.replace("'", "%27")
        _redirect = _redirect.replace('"', "%22")
        _redirect = _adjust_redirect_protocol(_redirect)
        _entry["redirect"] = _redirect
        _entry["target"]["DEFAULT"] = _redirect
    return _entry

def _is_valid_target(pfx):
    target = pfx.get("target", None)
    if target is None:
        return True
    if pfx.get("type", "") in ["synonym", ]:
        return True
    if target == {}:
        return False
    _t = target.get("DEFAULT", "")
    if _t in ["http://N/A", "https://N/A", "", ]:
        return False
    return True

def jsonFromYAML(
    fnsrc: str,
    fndest: str = None,
    ignore_types: typing.Optional[typing.Iterable[str]] = None,
    ignore_bad_targets: bool = True,
):
    if ignore_types is None:
        ignore_types = []
    _data = {}
    with open(fnsrc, "rb") as stream:
        _data = yaml.load(stream, Loader=yaml.SafeLoader)
    data = {}
    # python 3.7+ preserves order in dicts
    for k, v in _data.items():
        if v.get("type", "") not in ignore_types:
            if ignore_bad_targets:
                _cleaned = cleanPrefix(k, v)
                if _is_valid_target(_cleaned):
                    data[k] = _cleaned
            else:
                data[k] = cleanPrefix(k, v)
    if fndest is not None:
        with open(fndest, "w") as dest:
            json.dump(data, dest)
    return data


class PrefixList:
    def __init__(
        self, fn_src=None, ignore_types: typing.Optional[typing.List[str]] = None
    ):
        self.data = {}
        if fn_src is not None:
            self.load(fn_src, ignore_types=ignore_types)

    def load(
        self,
        fn_src: str,
        ignore_types: typing.Optional[typing.List[str]] = None,
        ignore_bad_targets = True,
    ) -> None:
        """
        Prepares PrefixList for accessing content.

        The source may be yaml (fn_src ends with .yaml or .yml),
        an lmdb instance (fnsrc ends with .db or .lmdb) or
        json (any other file name extension).

        Args:
            fn_src: Source for loading the prefix list.
            ignore_types: List of type names to ignore when loading.
            ignore_bad_targets: bool, don't load entries with bad targets

        Returns:
            Nothing.

        """
        fn, ext = os.path.splitext(fn_src)
        ext = ext.lower()
        if ext in [".yml", ".yaml"]:
            self.data = jsonFromYAML(fn_src, ignore_types=ignore_types, ignore_bad_targets=ignore_bad_targets)
        else:
            if LMDB_AVAIALBLE and ext in [".db", ".lmdb"]:
                self.data = JsonLmdb.open(fn_src, "r")
            else:
                with open(fn_src, "r") as src:
                    self.data = json.load(src)

    def store(self, fn_dst: str) -> None:
        """
        Store the prefix list to a JSON file or LMDB instance.

        Output to an LMDB instance if fn_dst ends with .db or .lmdb and LMDB is installed,
        otherwise output is to a JSON file.

        Args:
            fn_dst: file name of destination.

        Returns:
            Nothing
        """
        fn, ext = os.path.splitext(fn_dst)
        ext = ext.lower()
        if LMDB_AVAIALBLE and ext in [".db", ".lmdb"]:
            with JsonLmdb.open(fn_dst, "c") as dst:
                for k, v in self.data.items():
                    dst[k] = v
        else:
            with open(fn_dst, "w") as dst:
                json.dump(self.data, dst, indent=2)

    def fields(self) -> typing.Dict[str, int]:
        """Return dict of fields and their occurrence counts"""
        res = {}
        for k, v in self.data.items():
            for cname in v.keys():
                n = res.get(cname, 0)
                n = n + 1
                res[cname] = n
        return res

    def field_values(self, field: str) -> typing.Dict[str, int]:
        """Return list of distinct values and counts for field"""
        res = {}
        for prefix, entry in self.data.items():
            v = entry.get(field, None)
            if v is not None:
                n = res.get(v, 0)
                n = n + 1
                res[v] = n
        return res

    def prefixes(self) -> typing.Iterable[str]:
        """Iterator of prefix keys"""
        return self.data.keys()

    def length(self) -> int:
        """Number of prefixes"""
        return len(list(self.data.keys()))

    def get_entry(self, key) -> typing.Dict:
        """Get prefix entry at key"""
        return self.data.get(key)

    def get_resolver_by_scheme(
        self, key: str, entries: typing.List[typing.Dict] = None, counter: int = 0
    ) -> typing.List[typing.Dict]:
        """Returns the resolver for the provided key.

        If the key points to a synonym, the synonym is followed
        to the resolver instance.

        Raises KeyError if not found.

        Args:
            key: str, the scheme to lookup
            entries: accumulated resolvers in order of discovery
            counter: int, to keep track of cyclic synonyms

        Returns:
            None or a dict of resolver information.
        """
        if entries is None:
            entries = []
        res = self.get_entry(key)
        if res is None:
            raise KeyError(f"Resolver '{key}' not found.")
        entries.append(res)
        rtype = res.get("type", "")
        if rtype == "synonym":
            _for = res.get("for", None)
            if _for is None:
                raise KeyError(f"Resolver '{key}' is synonym with no target.")
            return self.get_resolver_by_scheme(
                _for, entries=entries, counter=counter + 1
            )
        if counter > 10:
            raise KeyError(f"Synonym loop for '{key}'!")
        return entries

    def get_resolver(self, pid: str) -> typing.List[typing.Dict]:
        scheme, value = lib_n2t.get_scheme(pid)
        return self.get_resolver_by_scheme(scheme)

    def get_redirect(self, key: str, scheme: str) -> typing.Optional[str]:
        """
        Get the redirect url for key.

        If necessary, this will populate the redirect by looking up
        "special" information about the resolver.
        """
        r = self.data.get(key)
        if r is None:
            return None
        redir = r.get("redirect")
        if redir is not None:
            return redir
        manager = r.get("manager")
        if manager == "ezid":
            # To be be replaced by https://ezid.cdlib.org/ark:{id}
            return "https://n2t.net/" + scheme + ":{id}"
        if manager == "n2t":
            return "ERROR: manager is set as n2t for {id}"
        return "ERROR: unknown handler for {id}"

    def get_longest_matching_prefix(self, test: str, scheme: str):
        """Find longest key pattern that matches test"""
        match = set()
        t3 = test[:3]
        if not t3 in ["ark", "doi"]:
            ab = test.split(":", 1)
            test = ab[0]
        etest = f"/{test}"
        L.debug("Testing: %s  %s", test, etest)
        for p, v in self.data.items():
            # if p.startswith(test) or p.endswith(etest):
            if test.startswith(p) or p.endswith(etest):
                L.debug("Hit key = %s", p)
                vt = v.get("type")
                if vt == "scheme":
                    match.add(p)
                    continue
                if vt == "naan":
                    match.add(p)
                    continue
                if vt == "shoulder":
                    match.add(p)
                    continue
                if vt == "datacenter":
                    match.add(p)
                    continue
                if vt == "synonym":
                    _for = v.get("for")
                    if _for is not None:
                        match.add(_for)
        return sorted(list(match), key=len, reverse=True)

    def resolve(self, identifier):
        """Given identifier, return normalized, resolver_key, resolver"""
        nid, resolver_key = lib_n2t.normalize_identifier(identifier)
        res_keys = self.get_longest_matching_prefix(resolver_key, nid.scheme)
        resolvers = []
        redirect_url = None
        nid.url = None
        for k in res_keys:
            resolver = self.get_entry(k)
            resolvers.append(resolver)
            redirect_url = self.get_redirect(k)  # resolver.get("redirect", None)
            if nid.url is None and redirect_url is not None:
                try:
                    nid.url = redirect_url.format(id=nid.value)
                except KeyError as e:
                    L.error(e)
        return nid, res_keys, resolvers

    def _to_identifier_resolver(
        self, key: str, scheme: str
    ) -> lib_n2t.IdentifierResolver:
        r = self.get_entry(key)
        idtype = r.get("type")
        redir = self.get_redirect(key, scheme)
        # redir = r.get('redirect')
        if redir is None and idtype == "shoulder":
            # Lookup the redirect url of the shoulder manager!!
            redir = "TEST"
        L.debug("r = %s", r)
        _t = lib_n2t.IdentifierResolver(
            id=r.get("id"),
            idtype=idtype,
            redirect=redir,
            name=r.get("name"),
            alias=r.get("alias"),
            provider=r.get("provider"),
            provider_id=r.get("provider_id"),
            description=r.get("description"),
            subject=r.get("subject"),
            location=r.get("location"),
            institution=r.get("institution"),
            more=r.get("more"),
            test=r.get("test"),
            identifier=None,
        )
        return _t

    def info(self, identifier: str) -> lib_n2t.IdentifierResolution:
        nid, rkey = lib_n2t.normalize_identifier(identifier)
        result = lib_n2t.IdentifierResolution(input=nid, resolution=[])
        L.debug("nid = %s", nid)
        res_keys = self.get_longest_matching_prefix(rkey, nid.scheme)
        redirect_url = None
        for k in res_keys:
            r = self._to_identifier_resolver(k, nid.scheme)
            target = lib_n2t.ResolverTarget(url=None, resolver=r)
            target.set_url(nid)
            L.debug("target = %s", target)
            result.resolution.append(target)
        return result
