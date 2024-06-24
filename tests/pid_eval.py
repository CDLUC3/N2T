"""
This script is for evaluating the scheme translation from legacy n2t.

For each scheme that has a representative test value, resolve the identifier past the
known hosts. The resulting URL and response status code should be the same for
all cases.

Output is stored to a json file "ab_results.json" in the same folder as
where the script is run. That json file contains a summary of results for each test.

The json file can be loaded into an environment like duckdb for further analysis. e.g.:

$ duckdb
D install json; load json;
D create table tests as from "ab_results.json";
D select * from tests where msg='ERR';
"""

import asyncio
import json
import os
import sys
import typing

import duckdb
import hopper
import pydantic_settings

ENV_PREFIX = "n2t_test_"
SETTINGS_FILE_KEY = f"{ENV_PREFIX.upper()}SETTINGS"


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_prefix=ENV_PREFIX, env_file=".env")
    host_a: str = "https://n2t.net/"
    #host_b: str = "https://uc3-ezid-n2t-prd.cdlib.org/"
    host_b: str = "https://uc3-ezid-n2t-stg.cdlib.org/"
    #host_b: str = "http://localhost:8000/"
    white_hosts: typing.Set[str] = set(["n2t.net","uc3-ezid-n2t-prd.cdlib.org", "arks.org", "ezid.cdlib.org", "doi.org", "legacy-n2t.n2t.net"])
    accept_header: str = "*/*"
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    schemes: str = "./schemes"
    timeout:float = 3.0
    os_host:str = "https://search-os-uc3-logging-stg-suwz42vownvyte6ivqazeifz44.us-west-2.es.amazonaws.com/"
    os_user:str = "vieglais"
    os_password:str = "<PASSWORD>"
    os_max_rows:int = 1000000

def get_settings(env_file=None):
    if env_file is None:
        env_file = os.environ.get(SETTINGS_FILE_KEY, ".env")
    return Settings(_env_file=env_file)

settings = get_settings()


def load_targets(source_file:str) -> list[dict[str, typing.Any]]:
    targets = []
    con = duckdb.connect(database = ":memory:")
    sql = f"create table tests as select * from read_parquet('{source_file}')"
    con.sql(sql)
    sql = "select distinct prefix from tests where scheme = 'ark' order by prefix"
    prefixes = con.execute(sql).fetchall()
    ignore_prefixes = [
        '99999',
        '12345-dev',
        '12345',
    ]
    for prefix in prefixes:
        p = prefix[0]
        if p in ignore_prefixes:
            continue
        #print(p)
        res = con.execute("select pid, status from (select pid, status from tests where scheme='ark' and prefix=?) using sample 6", prefix).fetchall()
        for item in res:
            targets.append({
                'test': item[0],
                'status': item[1]
            })

    return targets

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

async def resolve_target(url: str) -> hopper.Hops:
#def resolve_target(url: str) -> hopper.Hops:
    results = hopper.follow_redirects(
        url,
        accept=settings.accept_header,
        user_agent=settings.user_agent,
        timeout=settings.timeout,
        method="GET",
        white_hosts=list(settings.white_hosts)
    )
    return results

async def main():
    #scheme_records = json_to_records(settings.schemes)
    source_file = "./tests/pids_10m.parquet"
    scheme_records = load_targets(source_file)
    results = []
    n = 0
    #for k,v in scheme_records.items():
    #    test_value = v.get("test", None)
    for v in scheme_records:
        test_pid = v.get("test")
        #if test_value is None:
        #    continue
        #test_pid = f"{k}:{test_value}"
        url_a = f"{settings.host_a}{test_pid}"
        url_b = f"{settings.host_b}{test_pid}"
        ab = await asyncio.gather(
            resolve_target(url_a),
            resolve_target(url_b)
        )
        cmp = ["=", "="]
        msg = "OK "
        status_ok = True
        url_ok = True
        if ab[0].final_status != ab[1].final_status:
            cmp[1] = "!"
            msg = "ERR"
            status_ok = False
        if ab[0].final_url != ab[1].final_url:
            cmp[0] = "!"
            msg = "ERR"
            url_ok = False
        cmp = "".join(cmp)
        if msg == 'ERR':
            sys.stdout.write(
                f"\n{n}/{len(scheme_records)} {msg}: {test_pid} = {ab[0].final_status} {ab[0].final_url} {cmp} {ab[1].final_status} {ab[1].final_url} "
            )
        else:
            sys.stdout.write(".")
        sys.stdout.flush()
        res = {
            "msg":msg,
            "pid":test_pid,
            "status_ok": status_ok,
            "url_ok": url_ok,
            "a_status": ab[0].final_status,
            "a_url": ab[0].final_url,
            "b_status": ab[1].final_status,
            "b_url": ab[1].final_url,
        }
        results.append(res)
        n += 1
        ab = None
    with open("ab_ark_results.json", "w") as dest:
        for r in results:
            json.dump(r, dest)
            dest.write(",\n")

if __name__ == "__main__":
    asyncio.run(main())