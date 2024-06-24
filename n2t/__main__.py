"""
Management commands for N2T.

This script is used for initializing the scheme records from the original YAML
source and populating a resolver database with the records.
"""

import dataclasses
import datetime
import json
import logging
import os
import sys
import typing

import click
import sqlalchemy

import rslv.lib_rslv.piddefine

from n2t import __version__
from n2t import config as appconfig
from n2t import n2tutils

APP_NAME = "n2t"

class EnhancedJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles dataclasses and datetime instances."""

    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, datetime.datetime):
            return o.isoformat(timespec="seconds")
        return super().default(o)

def load_yaml_to_dict(
    source: str, ignore_types: typing.Optional[typing.List] = None
) -> dict:
    """
    Load YAML from source, clean values, and return a dict with keys being uniq
    value.

    Args:
        source: Filename of source YAML
        ignore_types: Ignore entries with these "type" values

    Returns:
        dict of prefixes
    """
    with open(source, "r") as inf:
        records = n2tutils.n2t_prefixes_from_yaml(
            inf, ignore_types=ignore_types, ignore_bad_targets=False
        )
    return records


def prefix_to_pathname(prefix: str) -> str:
    """
    Convert prefix to a file name byt replacing special characters.

    Args:
        prefix: string

    Returns:
        escaped prefix suitable for file name
    """
    res = prefix.lower().strip()
    res = res.replace("/", "_")
    if res == "index":
        res = "index_"
    return res


def records_to_json(
    records: typing.Dict[str, typing.Any], dest_folder: str
) -> typing.Tuple[int, int]:
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    total = 0
    updated = 0
    index = {}
    paths = set()
    for key, record in records.items():
        fkey = prefix_to_pathname(key)
        # ensure we don't overwrite an existing definition
        assert fkey not in paths
        paths.add(fkey)
        fname = os.path.join(dest_folder, f"{fkey}.json")
        do_write = True
        existing = None
        if os.path.exists(fname):
            with open(fname, "r") as fsrc:
                existing = json.load(fsrc)

        if existing is not None:
            new_revision = record.get("revision", 0)
            if existing["revision"] > new_revision:
                do_write = False
        if do_write:
            with open(fname, "w") as destf:
                json.dump(record, destf, indent=2)
                updated += 1
        total += 1
        index[key] = fkey
    with open(os.path.join(dest_folder, "index.json"), "w") as destf:
        json.dump(index, destf, indent=2)
    return (total, updated)


def json_to_records(src_folder: str) -> typing.Dict[str, typing.Any]:
    index = {}
    with open(os.path.join(src_folder, "index.json"), "r") as fsrc:
        index = json.load(fsrc)
    records = {}
    for key, fkey in index.items():
        fname = os.path.join(src_folder, f"{fkey}.json")
        with open(fname, "r") as fsrc:
            record = json.load(fsrc)
            records[key] = record
    return records

def _add_or_update_record(repository, key:str, value:dict[str, typing.Any]) -> typing.Tuple[int, int, int]:
    """Add or update the record identified by key with the properties of value.
    """
    L = logging.getLogger(APP_NAME)
    _parsed = rslv.lib_rslv.split_identifier_string(key)
    _scheme = _parsed.get("scheme", None)
    _total = 0
    _added = 0
    _updated = 0
    if _scheme is not None:  # and _scheme != "ark":
        _synonym_for = None
        _prefix = _parsed.get("prefix", None)
        _value = _parsed.get("value", None)
        _uniq = rslv.lib_rslv.piddefine.calculate_definition_uniq(
            _scheme, _prefix, _value
        )
        target = value.get("target", {}).get("DEFAULT", None)
        if target is None:
            target = value.get("redirect")
        if target is None:
            target = f"/.info/{_scheme}"
            if _prefix is not None:
                target = target + f"/{_prefix}"
                if _value is not None:
                    target = target + f"/{_value}"
        # TODO: alias in prefixes yaml means that the value is an alias for this record
        # _alias = value.get("alias", None)
        # if _alias is not None:
        #    _synonym_for = f"{_alias}:"
        if value.get("type", None) == "synonym":
            _s_parsed = rslv.lib_rslv.split_identifier_string(value.get("for", ""))
            _s_scheme = _s_parsed.get("scheme", None)
            _s_prefix = _s_parsed.get("prefix", None)
            _s_value = _s_parsed.get("value", None)
            _synonym_for = rslv.lib_rslv.piddefine.calculate_definition_uniq(
                _s_scheme, _s_prefix, _s_value
            )
        properties = value
        for prop in []:
            try:
                del properties[prop]
            except KeyError as e:
                pass
        entry = rslv.lib_rslv.piddefine.PidDefinition(
            scheme=_scheme,
            prefix=_prefix,
            value=_value,
            target=target,
            canonical=_parsed.get("pid", key),
            synonym_for=_synonym_for,
            properties=properties,
        )
        if value.get("type", None) == "synonym":
            L.info(entry.__dict__)
        _total += 1
        try:
            res = repository.add_or_update(entry)
            uniq = res.get("uniq", entry.uniq)
            n_changes = res.get("n_changes", -1)
            if n_changes < 0:
                _added += 1
                L.info("Added %s", uniq)
            elif n_changes == 0:
                L.info("No changes for %s", uniq)
            else:
                _updated += 1
                L.info("Updated %s with %s changes", uniq, n_changes)
        except sqlalchemy.exc.IntegrityError as e:
            repository._session.rollback()
            L.exception(e)
            L.error("Failed to add record for %s", key)
    else:
        L.warning("No record added for key: %s", key)
    return (_total, _added, _updated)


def records_to_db(
    records: typing.Dict[str, typing.Any], db_str: str, clear_existing: bool = False
) -> typing.Tuple[int, int, int, int]:
    """
    Load YAML configuration.

    example: https://n2t.net/e/n2t_full_prefixes.yaml

    Args:
        source: the N2T full prefixes yaml

    Returns:
        int: number of entries loaded.
    """
    L = logging.getLogger(APP_NAME)
    # initialize database
    engine = sqlalchemy.create_engine(db_str, pool_pre_ping=True)

    rslv.lib_rslv.piddefine.create_database(engine, description="n2t_full_prefixes")
    session = rslv.lib_rslv.piddefine.get_session(engine)
    repository = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    _total = 0
    _added = 0
    _updated = 0
    _nsynonyms = 0
    _synonyms = []
    for key, value in records.items():
        if value.get("type", "").lower() != "synonym":
            tau = _add_or_update_record(repository, key, value)
            _total += tau[0]
            _added += tau[1]
            _updated += tau[2]
    # Process synonyms last since they should reference existing records.
    for key, value in records.items():
        if value.get("type", "").lower() == "synonym":
            L.info("Adding synonym: %s", key)
            tau = _add_or_update_record(repository, key, value)
            _total += tau[0]
            _nsynonyms += tau[1]
            _updated += tau[2]

    return (_total, _added, _updated, _nsynonyms)


@click.group("cli")
@click.pass_context
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, readable=True),
    default=None,
)
def cli(ctx, config) -> int:
    """
    Management commands for N2T.

    This script is used for initializing the JSON representation of scheme
    records from the original YAML and creating or updating the sqlite store
    used by the resolver application.
    """
    logging.basicConfig(level=logging.INFO)
    L = logging.getLogger(APP_NAME)
    if config is not None:
        os.environ[appconfig.SETTINGS_FILE_KEY] = config
        L.info("Using configuration from --config option: %s", config)
    else:
        _efile = os.environ.get(appconfig.SETTINGS_FILE_KEY, None)
        if _efile is not None:
            L.info("Using configuration from %s: %s", appconfig.SETTINGS_FILE_KEY, _efile)
        else:
            if os.path.exists(".env"):
                L.info("Using configuration from file: .env")
            else:
                L.warning("Using default configuration.")
    ctx.obj = appconfig.get_settings(env_file=config)
    return 0

@cli.command("info")
@click.pass_obj
def get_info(config: appconfig.Settings) -> int:
    """
    Print application version and basic status.
    """
    L = logging.getLogger(APP_NAME)
    engine = sqlalchemy.create_engine(config.db_connection_string, pool_pre_ping=True)
    session = rslv.lib_rslv.piddefine.get_session(engine)
    repository = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    res = {
        "version": __version__,
        "environment": config.environment,
        "status": "not initialized",
        "description": None,
        "created": None,
        "schemes": {
            "total": 0,
            "valid": 0
        }
    }
    try:
        meta = repository.get_metadata()
        res["description"] = meta.get("description", "")
        res["created"] = meta.get("created", "")
        res["status"] = "initialized"
        schemes = repository.list_schemes(valid_targets_only=False)
        res["schemes"]["total"] = len(schemes.all())
        schemes = repository.list_schemes(valid_targets_only=True)
        res["schemes"]["valid"] = len(schemes.all())
    except Exception as e:
        L.warning(e)
        pass
    if res["schemes"]["total"] == 0:
        L.warning("No schemes have been loaded!")
    print(json.dumps(res, indent=2, cls=EnhancedJSONEncoder))
    return 0



@cli.command("yaml2json")
@click.pass_obj
@click.option(
    "-y",
    "--yamlsrc",
    type=click.Path(
        exists=False,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    default="n2t_full_prefixes.yaml",
)
def cli_yaml2json(config: appconfig.Settings, yamlsrc: str) -> int:
    """
    Generate or update JSON record from YAML source.
    """
    L = logging.getLogger(APP_NAME)
    ignore_types = ["datacenter", "naan", "shoulder"]
    records = load_yaml_to_dict(yamlsrc, ignore_types=ignore_types)
    res = records_to_json(records, config.json_dir)
    L.info(f"Processed {res[0]} records, updated {res[1]}.")
    print("Load to JSON complete.")
    return 0


@cli.command("loaddb")
@click.pass_obj
def cli_loaddb(config: appconfig.Settings) -> int:
    """
    Load or update the scheme database.
    """
    L = logging.getLogger(APP_NAME)
    records = json_to_records(config.json_dir)
    res = records_to_db(records, config.db_connection_string)
    L.info(f"Processed {res[0]} records, added {res[1]}, updated {res[2]}, synonyms {res[3]}.")
    print("Load to DB complete.")
    return 0


try:
    import uvicorn

    @cli.command("serve")
    @click.pass_obj
    @click.option(
        "-r",
        "--reload",
        is_flag=True,
        default=False,
        help="Enable service reload on source change.",
    )
    def cli_serve(config: appconfig.Settings, reload) -> int:
        uvicorn.run("n2t.app:app", host=config.host, port=config.port, log_level="info", reload=reload)
        return 0

except ImportError:
    print("Install uvicorn for development serve option to be available.")


def main() -> int:
    cli(prog_name="n2t")
    return 0


if __name__ == "__main__":
    sys.exit(main())
