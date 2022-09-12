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

DATE_MATCH = re.compile(r"\d{4}\.\d{2}\.\d{2}")
DATE_PATTERN = "%Y.%m.%d"

L = logging.getLogger("prefixes")

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
    _data = {}
    with open(fnsrc, "rb") as stream:
        _data = yaml.load(stream, Loader=yaml.SafeLoader)
    data = {}
    # python 3.7+ preserves order in dicts
    for k,v in _data.items():
        data[k] = cleanPrefix(k, v)
    if fndest is not None:
        with open(fndest, "w") as dest:
            json.dump(data, dest)
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

    def store(self, fn_dst):
        with open(fn_dst, "w") as dst:
            json.dump(self.data, dst, indent=2)

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

    def getRedirect(self, key, scheme):
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


    def getLongestMatchingPrefix(self, test, scheme):
        '''Find longest key pattern that matches test
        '''
        match = set()
        t3 = test[:3]
        if not t3 in ['ark', 'doi']:
            ab = test.split(":",1)
            test = ab[0]
        etest = f'/{test}'
        L.debug("Testing: %s  %s", test, etest)
        for p,v in self.data.items():
            if p.startswith(test) or p.endswith(etest):
                L.debug("Hit key = %s",p)
                vt = v.get('type')
                if vt == 'scheme':
                    match.add(p)
                    continue
                if vt == 'naan':
                    match.add(p)
                    continue
                if vt == 'shoulder':
                    match.add(p)
                    continue
                if vt == 'datacenter':
                    match.add(p)
                    continue
                if vt == 'synonym':
                    _for = v.get('for')
                    if _for is not None:
                        match.add(_for)
                #sp = p
                #vt = v.get("type")
                #if vt == "synonym":
                #    sp = v.get("for", None)
                #    if sp is not None:
                #        v = self.data.get(sp)
                #        #match.append(sp)
                #else:
                #    match.append(sp)
                #if vt == "scheme":
                #    if sp == scheme:
                #        match.add(sp)
                #else:
                #    match.add(sp)
                ##if sp == scheme:
                ##    break
        return sorted(list(match), key=len, reverse=True)

    def resolve(self, identifier):
        """Given identifier, return normalized, resolver_key, resolver
        """
        nid = lib_n2t.normalizeIdentifier(identifier)
        res_keys = self.getLongestMatchingPrefix(nid['resolver_key'], nid['scheme'])
        resolvers = []
        redirect_url = None
        nid['url'] = None
        for k in res_keys:
            resolver = self.getEntry(k)            
            resolvers.append(resolver)
            redirect_url = self.getRedirect(k) #resolver.get("redirect", None)
            if nid['url'] is None and redirect_url is not None:
                nid["url"] = redirect_url.format(id=nid["value"])
        return nid, res_keys, resolvers

    def _toIdentifierResolver(self, key:str, scheme:str) -> lib_n2t.IdentifierResolver:
        r = self.getEntry(key)
        idtype = r.get('type')
        redir = self.getRedirect(key, scheme)
        #redir = r.get('redirect')
        if redir is None and idtype == 'shoulder':
            # Lookup the redirect url of the shoulder manager!!
            redir = "TEST"
        L.debug("r = %s", r)
        _t = lib_n2t.IdentifierResolver(
            id = r.get('id'),
            idtype = idtype,
            redirect = redir,
            name = r.get('name'),
            alias = r.get('alias'),
            provider = r.get('provider'),
            provider_id = r.get('provider_id'),
            description = r.get('description'),
            subject = r.get('subject'),
            location = r.get('location'),
            institution = r.get('institution'),
            more = r.get('more'),
            test = r.get('test'),
            identifier = None
        )
        return _t

    def info(self, identifier:str)->typing.List[lib_n2t.IdentifierResolver]:
        nid, rkey = lib_n2t.normalizeIdentifier(identifier)
        L.debug("nid = %s",nid)
        res_keys = self.getLongestMatchingPrefix(rkey, nid.scheme)
        resolvers = []
        redirect_url = None
        for k in res_keys:
            r = self._toIdentifierResolver(k, nid.scheme)
            L.debug("resolver = %s", r)
            r.set_identifier(nid)
            resolvers.append(r)
        return resolvers
