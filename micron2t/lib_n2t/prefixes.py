import logging
import os
import yaml
import json
import re
import datetime
import sqlmodel
import lib_n2t.models


L = logging.getLogger("lib_n2t.prefixes")

DATE_MATCH = re.compile(r"\d{4}\.\d{2}\.\d{2}")
DATE_PATTERN = "%Y.%m.%d"


def _convertValue(v):
    '''Return parsed representation of value loaded from YAML
    '''
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
    #try:
    #    return int(v)
    #except ValueError:
    #    pass
    if DATE_MATCH.match(v):
        try:
            nv = datetime.datetime.strptime(v, DATE_PATTERN)
            return nv.date().isoformat()
        except ValueError:
            pass
    return v


def _adjustRedirectProtocol(r, default_protocol="https"):
    '''Make a redirect entry into a URL, if possible
    '''
    _protocols = ["http", "https", "ftp", "ftps", "sftp", ]
    try:
        a,b = r.split(":",1)
        a = a.lower()
        if not a in _protocols:
            return f"{default_protocol}://{r.lstrip('/')}"
        return r
    except ValueError as e:
        pass
    return f"{default_protocol}://{r.lstrip('/')}"


def cleanPrefix(key, data, field_map=None):
    '''Clean a prefix entry retrieved from YAML    
    '''
    values = {}
    for k,v in data.items():
        values[k] = _convertValue(v)
    _entry = {"id": key}
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
        _redirect = _adjustRedirectProtocol(_redirect)
        _entry["redirect"] = _redirect
    return _entry


def jsonFromYAML(fnsrc: str, fndest:str = None):
    if fndest is None:
        L.warning("Not persisting JSON store.")
    _data = {}
    L.info("Loading YAML source...")
    with open(fnsrc, "rb") as stream:
        _data = yaml.load(stream, Loader=yaml.SafeLoader)
    data = {}
    # python 3.7+ preserves order in dicts
    for k,v in _data.items():
        data[k] = cleanPrefix(k, v)
    if fndest is not None:
        with open(fndest, "w") as dest:
            json.dump(data, dest)
        L.info("Wrote %s", fndest)
    return data


class PrefixList:
    def __init__(self, fn_src=None):
        self.data = {}
        if fn_src is not None:
            self.load(fn_src)

    def load(self, fn_src):
        fn, ext = os.path.splitext(fn_src)
        ext = ext.lower()
        if ext in [".yml", ".yaml"]:
            self.data = jsonFromYAML(fn_src)            
        else:
            with open(fn_src, "r") as src:
                self.data = json.load(src)
        L.info("Loaded from: %s", fn_src)

    def store(self, fn_dst):
        with open(fn_dst, "w") as dst:
            json.dump(self.data, dst)
        L.info("stored to: %s", fn_dst)

    def fields(self):
        """Return dict of fields and their occurrence
        """
        res = {}
        for k,v in self.data.items():
            for cname in v.keys():
                n = res.get(cname, 0)
                n = n + 1
                res[cname] = n
        return res

    def fieldValues(self, field):
        """Return list of distinct values and counts for field
        """
        res = {}
        for prefix, entry in self.data.items():
            v = entry.get(field, None)
            if v is not None:
                n = res.get(v, 0)
                n = n + 1
                res[v] = n
        return res

    def prefixes(self):
        """Iterator of prefix keys
        """
        return self.data.keys()

    def length(self):
        """Number of prefixes
        """
        return len(list(self.data.keys()))

    def getEntry(self, key):
        """Get prefix entry at key
        """
        return self.data.get(key)

    def getLongestMatchingPrefix(self, test):
        '''Find longest key pattern that matches test
        '''
        match = None
        match_len = 0
        for p in self.prefixes():
            if test.startswith(p):
                plen = len(p)
                if plen > match_len:
                    match = p
                    match_len = plen
        return match        

    def resolve(self, identifier):
        """Given identifier, return it's resolver
        """
        nid = lib_n2t.normalizeIdentifier(identifier)
        res_key = self.getLongestMatchingPrefix(nid['resolver_key'])
        resolver = self.getEntry(res_key)
        if resolver.get("type") == "synonym":
            res_key = resolver.get("for")
            resolver = self.getEntry(res_key)
        target = resolver.get("redirect")
        nid['url'] = None
        if target is not None:
            nid['url'] = target.format(id=nid['value'])
        return nid, res_key, resolver
