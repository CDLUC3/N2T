
def parseIdentifier(identifier):
    identifier = identifier.strip()
    parts = identifier.split(":", 1)
    scheme = parts[0].strip().lower()
    value = None
    try:
        value = parts[1].strip()
    except IndexError:
        pass
    return scheme, value


def normalizeIdentifier(identifier):
    res = {
        "original": identifier,
    }
    scheme, value = parseIdentifier(identifier)
    res["scheme"] = scheme
    res["value"] = value
    res["normal"] = f"{scheme}:{value}"
    return res