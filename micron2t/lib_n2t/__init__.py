
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

    # Ensure ark identifier values have the form "ark:/..."
    if scheme == "ark":
        if value is not None and len(value) > 0:
            if value[0] != "/":
                value = "/"+value
    
    res["value"] = value
    res["normal"] = f"{scheme}:{value}"
    return res