"""
Provides utility methods for interacting with the legacy N2T service.

This content is not required for operation of rslv and may be removed in the future.

Dependencies for this are specified under the n2t group in poetry.
"""

import datetime
import logging
import re
import typing
import yaml

COMMENT_CHAR = "#"
DATE_MATCH = re.compile(r"\d{4}\.\d{2}\.\d{2}")
DATE_PATTERN = "%Y.%m.%d"


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


def _is_valid_target(target:typing.Optional[str]) -> bool:
    if target is None:
        return False
    _t = target.strip()
    _t = target.lower()
    if len(_t) < 6:
        return False
    if _t in [
        "",
        "http://n/a",
        "https://n/a",
        "https://unavailable",
        "http://unavailable",
        "https://no search",
        "http://no search",
        "https://need login",
        "http://need login",
        "https://need a Login",
        "http://need a Login",
        "https://login needed",
        "http://login needed",
        "https://login required",
        "http://login required",
    ]:
        return False
    return True


def _is_valid_prefix_target(pfx):
    target = pfx.get("target", None)
    if target is None:
        return True
    if pfx.get("type", "") in [
        "synonym",
    ]:
        return True
    if target == {}:
        return False
    _t = target.get("DEFAULT", "")
    return _is_valid_target(_t)


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
        _redirect = _redirect.replace("$id", "${content}")
        _redirect = _redirect.replace("'", "%27")
        _redirect = _redirect.replace('"', "%22")
        _redirect = _adjust_redirect_protocol(_redirect)
        if _is_valid_target(_redirect):
            _entry["redirect"] = _redirect
            _entry["target"]["DEFAULT"] = _redirect
    return _entry


def n2t_prefixes_from_yaml(
    yamlsrc:typing.IO,
    ignore_types: typing.Optional[typing.Iterable[str]] = None,
    ignore_bad_targets: bool = True,
) -> dict:
    """
    Loads content from N2T full prefixes YAML source.

    Available from URL: https://n2t.net/e/n2t_full_prefixes.yaml

    The full prefixes yaml file is a source of truth for the
    legacy N2T resolver service. This method reads the YAML and
    returns the parsed and somewhat cleaned content as a python
    dictionary.

    Args:
        yamlsrc: Open stream or YAML text
        ignore_types: List of "type" values to ignore (e.g. "naan")
        ignore_bad_targets: Ignore entries with malformed target URLs

    Returns:
        dict with keys being the prefix.
    """
    if ignore_types is None:
        ignore_types = []
    _data = {}
    _data = yaml.load(yamlsrc, Loader=yaml.SafeLoader)
    data = {}
    # python 3.7+ preserves order in dicts
    for k, v in _data.items():
        if v.get("type", "") not in ignore_types:
            _cleaned = cleanPrefix(k, v)
            if _cleaned.get("revision", None) is None:
                _cleaned["revision"] = 0
            if ignore_bad_targets and _is_valid_prefix_target(_cleaned):
                data[k] = _cleaned
            else:
                data[k] = _cleaned
    return data


def naa_record_from_rows(rows: typing.List[str])->typing.Optional[dict[str, typing.Any]]:
    L = logging.getLogger("naan_from_rows")
    if len(rows) < 1:
        return None
    key = rows.pop(0).strip()
    if key == "naa:":
        record = {}
        while True:
            try:
                row = rows.pop(0)
            except IndexError as e:
                break
            L.debug(row)
            parts = row.strip().split(":", 1)
            k = parts[0].strip().lower()
            if k == "who":
                ab = parts[1].split("(=)")
                record["org_name"] = ab[0].strip()
                record["org_acronym"] = ab[1].strip()
            elif k == "what":
                record["id"] = parts[1].strip()
            elif k == "when":
                record["date_registered"] = datetime.datetime.strptime(parts[1].strip(),"%Y.%m.%d").isoformat()
            elif k == "where":
                nma_url = record.get("nma_url", [])
                nma_url.append(parts[1].strip())
                record["nma_url"] = nma_url
            elif k == "how":
                ab = parts[1].split("|")
                record["org_type"] = ab[0].strip()
                record["policy"] = ab[1].strip()
                if record["policy"] == "(:unkn) unknown":
                    record["policy"] = None
                record["tenure_start"] = int(ab[2].strip())
            elif k == "!why":
                record["naa_why"] = parts[1].strip()
            elif k == "!contact":
                record["contact"] = parts[1].strip()
            elif k == "!what":
                ab = parts[1].strip().split(" ", 1)
                naa_history = record.get("naa_history", [])
                naa_history.append(ab[0])
                record["naa_history"] = naa_history
            elif k == "!address":
                record["address"] = parts[1].strip()
        return record
    return None


def naa_records_from_anvl_text(src_text):
    _block = []
    lines = src_text.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith(COMMENT_CHAR):
            continue
        if line == "":
            record = naa_record_from_rows(_block)
            if record is not None:
                yield record
            _block = []
        else:
            _block.append(line)
    record = naa_record_from_rows(_block)
    if record is not None:
        yield record

