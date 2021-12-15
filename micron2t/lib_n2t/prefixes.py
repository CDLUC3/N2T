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
    if v is None:
        return v
    v = v.strip()
    if len(v) < 1:
        return v
    vl = v.lower()
    if vl == "true":
        return True
    if vl == "false":
        return False
    try:
        return int(v)
    except ValueError:
        pass
    if DATE_MATCH.match(v):
        try:
            nv = datetime.datetime.strptime(v, DATE_PATTERN)
            return nv.date()
        except ValueError:
            pass
    return v


def _cleanEntry(e):
    res = {}
    for k, v in e.items():
        res[k] = _convertValue(v)
    return res


def fromYAML(fnsrc: str, fndest: str = None):
    #if fndest is None:
    #    _base, _ext = os.path.splitext(fnsrc)
    #    fndest = f"{_base}.sqlite"
    #    if os.path.exists(fndest):
    #        raise ValueError("Target %s exists. Can not overwrite.")
    if fndest is None:
        L.warning("Creating temporary in memory database.")
        fndest = ":memory:"
    _data = {}
    L.info("Loading YAML source...")
    with open(fnsrc, "rb") as stream:
        _data = yaml.safe_load(stream)
    engine = sqlmodel.create_engine(f"sqlite:///{fndest}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    _field_map = lib_n2t.models.Prefix.inverseFieldMap()
    L.info("Populating database %s", fndest)
    with sqlmodel.Session(engine) as session:
        for k, v in _data.items():
            values = _cleanEntry(v)
            _entry = {"id": k}
            for field in values.keys():
                _entry[_field_map.get(field, field)] = values[field]
            session.add(lib_n2t.models.Prefix(**_entry))
            session.commit()
    L.info("Database load complete.")
    return engine


class PrefixList:
    def __init__(self, cnstr=None, engine=None):
        self.cnstr = cnstr
        if engine is not None:
            self.db = engine
        else:
            self.db = self.getDBConnection()

    def getDBConnection(self):
        engine = sqlmodel.create_engine(self.cnstr)
        sqlmodel.SQLModel.metadata.create_all(engine)
        return engine

    def fields(self):
        res = {}
        columns = lib_n2t.models.Prefix.columns()
        with sqlmodel.Session(self.db) as session:
            for cname in columns:
                sql = f"SELECT COUNT(*) FROM prefix WHERE {cname} IS NOT NULL;"
                rs = session.execute(sql)
                res[cname] = rs.fetchone()[0]
        return res

    def fieldValues(self, field):
        res = {}
        with sqlmodel.Session(self.db) as session:
            sql = f"SELECT {field}, COUNT(*) AS CNT FROM prefix GROUP BY {field} ORDER BY cnt"
            rs = session.execute(sql)
            for row in rs:
                res[row[0]] = row[1]
        return res

    def prefixes(self):
        with sqlmodel.Session(self.db) as session:
            sql = "SELECT id FROM prefix ORDER BY id"
            rs = session.execute(sql)
            for row in rs:
                yield row[0]

    def length(self):
        with sqlmodel.Session(self.db) as session:
            sql = "SELECT COUNT(*) FROM prefix"
            rs = session.execute(sql)
            return rs.fetchone()[0]

    def getEntry(self, key):
        with sqlmodel.Session(self.db) as session:
            return session.query(lib_n2t.models.Prefix).get(key)

    def findResolver(self, identifier):
        res = []
        with sqlmodel.Session(self.db) as session:
            sql = (
                "SELECT id FROM prefix "
                "WHERE instr(:id, id) = 1 "
                "AND (ptype='naan' OR "
                "    (ptype='shoulder' AND redirect IS NOT NULL)) "
                "ORDER BY LENGTH(id) DESC "
            )
            rs = session.execute(
                sql,
                {
                    "id": identifier,
                },
            )
            for row in rs:
                res.append(row[0])
        return res

    def findEntries(self, identifier):
        """

        Args:
            identifier:

        Returns:

        """
        lnid = len(identifier)
        schemes = []
        shorts = []
        longs = []
        for k in self.data:
            if identifier.startswith(k):
                shorts.append(k)
            elif k.startswith(identifier):
                longs.append(k)
        short_candidates = sorted(shorts, key=len, reverse=True)
        long_candidates = sorted(longs, key=len, reverse=True)
        return short_candidates, long_candidates


    def toPython(self, version_info="dev"):        
        def _adjustRedirectProtocol(r):
            _protocols = ["http", "https", "ftp", "ftps", "sftp", ]
            try:
                a,b = r.split(":",1)
                a = a.lower()
                if not a in _protocols:
                    return f"http://{r.lstrip('/')}"
                return r
            except ValueError as e:
                pass
            return f"http://{r.lstrip('/')}"

        # TODO: Split into three dicts:
        #  1. PREFIXES = scheme, synonym, and commonspfx
        #  2. NAANS = naan
        #  3. SHOULDERS = shoulder
        # When resolving, try NAAN, then SHOULDER, then PREFIX
        _L = [
            '# !!Auto generated file. Any edits will be lost!!',
            f'# Generated {datetime.datetime.utcnow().isoformat()}+00',
            '',
            'import re',
            f'_VERSION_ = "{version_info}"',
            'PREFIXES = {'
        ]
        with sqlmodel.Session(self.db) as session:
            sql = "SELECT id FROM prefix"
            rs = session.execute(sql)
            _prefixes = []
            for row in rs:
                prefix = self.getEntry(row[0])
                _redirect = prefix.redirect
                if _redirect is not None:
                    _redirect = _redirect.replace("$id", "{id}")
                    _redirect = _redirect.replace("'", "%27")
                    _redirect = _redirect.replace('"', "%22")
                    _redirect = _adjustRedirectProtocol(_redirect)
                entry = {
                    "type": prefix.ptype,
                    "redirect": _redirect,
                    "pattern": prefix.pattern,
                    "description": prefix.description,
                    "name": prefix.name,
                    "subject": prefix.subject,
                    "location": prefix.location,
                    "for": prefix.pfor,
                }
                _prefixes.append(f"  '{row[0]}':{entry}")
                #_prefixes.append(f"  '{row[0]}':" + "{" + f"'r':'{_redirect}', 'm':r'{prefix.pattern}'" + "}")
            _L.append(",\n".join(_prefixes))
        _L.append("}\n\n")
        return '\n'.join(_L)
