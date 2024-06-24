"""
Query OpenSearch for legacy n2t and get 30* urls

Some examples of output handling:

install json; load json;
create table pids as select * from read_json('pids_1m.json', auto_detect=true,format='newline_delimited');

List of schemes:
select scheme, count(*) as n from pids group by pids.scheme order by n;

List of ark prefixes:
select prefix, count(*) as n from pids where scheme='ark' group by prefix order by n;

Sample of 5 identifiers per prefix:
select data.rn as rn, data.prefix as prefix, data.pid as pid from (
    select a.*, row_number() over (partition by a.prefix) as rn
      from (
          select distinct pids.prefix, pids.pid from pids
          where pids.scheme = 'ark' and length(pids.value) > 0
          order by pids.prefix, length(pids.pid)
      ) a
  ) data
where data.rn <= 1
order by prefix asc, rn asc;

Load the naan registry:

create table naans
  as select *
  from '/Users/vieglais/Documents/Projects/CDLUC3/naan_reg_priv_clone/naan_records/naans_public.json';

What arks have a prefix that isn't in the naans:

select count(*) as n, prefix from pids where prefix not in (select what from naans) and scheme='ark' group by prefix order by prefix;

Get some example pids for naans not in the registry:

select data.rn as rn, data.prefix as prefix, data.pid as pid from (
    select a.*, row_number() over (partition by a.prefix) as rn
      from (
          select distinct pids.prefix, pids.pid from pids
          where pids.scheme = 'ark' and length(pids.value) > 0
          and prefix not in (select what from naans)
          order by pids.prefix, length(pids.pid)
      ) a
  ) data
where data.rn <= 3
order by prefix asc, rn asc;

"""

import json
import typing
import urllib.parse
import httpx
import pid_eval
import rslv.lib_rslv

def get_os_records(host:str, user:str, passwd:str, body:object, max_rows=1000) -> typing.Dict[str,str]:
    auth = httpx.BasicAuth(user, passwd)
    client = httpx.Client(auth=auth)
    url = f"{host}filebeat-uc3-ezid-legacyn2t*/_search"
    headers = {"Content-Type": "application/json"}
    params = {
        "size":10000,   # page size
        "scroll":"5m"  # 5 minutes
    }
    more_work = True
    scroll_id = None
    total_rows = 0
    while more_work:
        response = client.request(
            method="GET",
            url=url,
            headers=headers,
            params=params,
            content=json.dumps(body).encode("utf-8")
        ).json()
        scroll_id = response.get("_scroll_id",scroll_id)
        n_rows = 0
        for record in response.get("hits", {}).get("hits",[]):
            row = {
                "t":record["fields"]["@timestamp"][0],
                "status":record["fields"]["http.response.status_code"][0],
                "pid":urllib.parse.unquote(record["fields"]["url.original"][0].lstrip("/ ")),
                "source": record["fields"]["source.address"][0],
                "scheme":"",
                "prefix": "",
                "value":"",
                "content":"",
            }
            parts = rslv.lib_rslv.split_identifier_string(row['pid'])
            row["scheme"] = parts.get("scheme", "")
            row["prefix"] = parts.get("prefix", "")
            row["value"] = parts.get("value", "")
            row["content"] = parts.get("content", "")
            n_rows += 1
            total_rows += 1
            yield row
            if total_rows >= max_rows:
                more_work = False
                break
        if n_rows < 1:
            more_work = False
        if scroll_id is not None:
            body = {"scroll_id":scroll_id, "scroll":"5m"}
            url = f"{host}_search/scroll"
            params = {}

def main():
    os_host = pid_eval.settings.os_host
    os_user = pid_eval.settings.os_user
    os_passwd = pid_eval.settings.os_password
    max_rows = pid_eval.settings.os_max_rows
    max_rows = max_rows*100
    body = {
        "query": {
            "terms": {
                "http.response.status_code": [
                    302,
                    303
                ]
            }
        },
        "fields":[
            "@timestamp",
            "http.response.status_code",
            "url.original",
            "source.address"
        ],
        "_source":False
    }
    for row in get_os_records(os_host, os_user, os_passwd, body, max_rows=max_rows):
        print(json.dumps(row))


if __name__ == "__main__":
    main()