"""
Script to generate a pid_config json from yaml
"""
import json
import logging
import os.path
import sys
import click
import lib_n2t.prefixes




@click.command()
@click.argument("source")
def main(source) -> int:
    logging.basicConfig(level=logging.INFO)
    L = logging.getLogger()
    if not os.path.exists(source):
        L.error("Source '%s' does not exist.", source)
        return 1
    ignored_types = []
    data = lib_n2t.prefixes.jsonFromYAML(source, None, ignore_types=ignored_types, ignore_bad_targets=True)
    config = {
        "target": "{pid}",
        "canonical": "{pid}",
        "parser": "pidparse.BasePidParser",
        "data": {}
    }
    default_parser = "pidparse.BasePidParser"
    scheme_parsers = {"ark": "pidparse.ArkParser", "doi": "pidparse.DoiParser", }
    for k, v in data.items():
        entry = {
            "id": v["id"],
            "target": None,
        }
        _parser = scheme_parsers.get(k, None)
        if _parser is not None:
            entry["parser"] = _parser
        _target = v.get("target", {}).get("DEFAULT", None)
        if _target is None:
            continue
        if "{id}" in _target:
            _target = _target.replace("{id}", "{group_value}")
        entry["target"] = _target
        config["data"][k] = entry
    print(json.dumps(config, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())