"""
Management commands for N2T
"""

import argparse
import json
import sys

import sqlalchemy

import rslv.lib_rslv.n2tutils
import rslv.lib_rslv.piddefine

def loadyml(source: str, db_str) -> int:
    """
    Load YAML configuration.

    example: https://n2t.net/e/n2t_full_prefixes.yaml

    Args:
        source: the N2T full prefixes yaml

    Returns:
        int: number of entries loaded.
    """
    # initialize database
    engine = sqlalchemy.create_engine(
        db_str, pool_pre_ping=True
    )
    rslv.lib_rslv.piddefine.create_database(engine, description="n2t_full_prefixes")
    # load yaml
    records = {}
    with open(source, "r") as inf:
        records = rslv.lib_rslv.n2tutils.n2t_prefixes_from_yaml(inf)
    session = rslv.lib_rslv.piddefine.get_session(engine)
    repository = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    n = 0
    entry = rslv.lib_rslv.piddefine.PidDefinition(
        scheme="ark",
        target="https://arks.org/{pid}",
        canonical = "ark:/{prefix}/{value}",
        synonym_for=None,
        properties={
            "what": "ark",
            "name": "Archival Resource Key",
        },
    )
    repository.add(entry)
    for key, value in records.items():
        _parsed = rslv.lib_rslv.split_identifier_string(key)
        print(f"{key}")
        print(json.dumps(value, indent=2))
        _scheme = _parsed.get("scheme", None)
        if _scheme is not None and _scheme != "ark":
            _prefix = _parsed.get("prefix", None)
            _value = _parsed.get("value", None)
            target = value.get("target", {}).get("DEFAULT", None)
            if target is None:
                target = value.get("redirect")
            if target is None:
                target = f"/.info/{_scheme}"
                if _prefix is not None:
                    target = target + f"/{_prefix}"
                    if _value is not None:
                        target = target + f"/{_value}"
            properties = value
            for prop in [ ]:
                try:
                    del properties[prop]
                except KeyError as e:
                    pass

            entry = rslv.lib_rslv.piddefine.PidDefinition(
                scheme = _scheme,
                prefix = _prefix,
                value = _value,
                target = target,
                canonical = _parsed.get("pid", key),
                synonym_for = None,
                properties = properties
            )
            print("ENTRY = ")
            print(entry)
            try:
                res = repository.add(entry)
                print(f"Added entry {res}")
                n += 1
            except sqlalchemy.exc.IntegrityError as e:
                session.rollback()
                print(f"Failed to add duplicate for {key}")
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "operation",
        help="Operation to perform",
        choices=[
            "loadyml",
        ],
        default="loadyml",
        type=str,
    )
    parser.add_argument(
        "-s", "--source", help="Source YAML file", default="n2t_full_prefixes.yaml"
    )
    parser.add_argument(
        "-d",
        "--database",
        default="sqlite:///data/n2t.db",
        type=str,
        help="Connection string for database.",
    )
    args = parser.parse_args()
    if args.operation == "loadyml":
        nrecs = loadyml(args.source, args.database)
        print(f"Loaded {nrecs} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
