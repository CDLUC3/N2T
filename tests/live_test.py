"""
Given a feed from the legacy n2t access log, retrieve target and issue request against new n2t.

This script exercises the new n2t, arks.org, and ezid infrastructure by repeating requests being
made to legacy n2t to the new n2t service. It is uses as a test mechanism for verifying requests
made to the new n2t service provide the same result as issuing to the legacy n2t service.

legacy N2T logs are in /apps/n2t/sv/cv2/apache2/logs

Run me like:

ssh n2t-prod 'tail -f /apps/n2t/sv/cv2/apache2/logs/transaction_log' | python live_test.py

Expects geoip city database in ../data

Download from https://www.maxmind.com/en/accounts/995868/geoip/downloads
"""

import asyncio
import json
import re
import sys
import time

import geoip2.database
import geoip2.errors
import httpx

# RE for the n2t apache access file
ACCESS_LINE_RE = re.compile(r'([(\d\.)]+) - - \[(.*?)\] "(?P<METHOD>[A-Z]*) (?P<URI>.*?) (.*)" (?P<STATUS>\d+) [-\d]* "(?P<TARGET>.*?)" "(?P<UA>.*?)"')
# 47.76.209.138 - - [03/Apr/2024:10:39:51 -0700] "HEAD /ark:/65665/3470dd4de-8b69-4883-a8d2-061855e434ff HTTP/1.1" 302 - "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3508.37 Safari/537.36"

# RE for matching start and end of the legacy n2t trace log
TRACE_LINE_BEGIN_RE = re.compile(r'(?P<client>\S*) (?P<host>\S*) (?P<date>\S*) (?P<KEY>\S*) (?P<STATE>BEGIN) (?P<action>\S*) (?P<PID>\S*).*ra=(?P<IP>[0-9\.]+).*ua=(?P<UA>.*)\!{3}')
TRACE_LINE_END_RE = re.compile(r'(?P<client>\S*) (?P<host>\S*) (?P<date>\S*) (?P<KEY>\S*) (?P<STATE>END) (?P<outcome>\S*) (?P<PID>\S*).*-> (?P<status>\S*) (?P<target>\S*)')

class IpAddressList:
    """
    Implements a cache of IP addresses and computes coordinates based on geoip2.

    Useful for basic metrics on the origin of requests.
    """
    def __init__(self, geo_database):
        self.data = {}
        self.ipdb = geoip2.database.Reader(geo_database)

    def add_ip(self, ip:str) -> None:
        """
        Adds an ip or increments count if existing.
        """
        if ip not in self.data:
            try:
                geoip = self.ipdb.city(ip)
                self.data[ip] = {
                    "n": 1,
                    "iso": geoip.country.iso_code,
                    "x": geoip.location.longitude,
                    "y": geoip.location.latitude,
                }
            except geoip2.errors.AddressNotFoundError as e:
                print(e)
                self.data[ip] = {
                    "n": 1,
                    "iso": "",
                    "x": None,
                    "y": None,
                }
        else:
            self.data[ip]["n"] = self.data[ip]["n"] + 1

    def __str__(self):
        return json.dumps(self.data)

    def __len__(self):
        return len(self.data)

    def to_json(self):
        """
        Returns a list of dict with the entries flattened.
        """
        res = []
        for k,v in self.data.items():
            res.append({
                "ip":k,
                "n":v["n"],
                "iso":v["iso"],
                "x":v["x"],
                "y":v["y"]
            })
        return res


# Global cache of entries
IP_DICT = IpAddressList("../data/GeoLite2-City.mmdb")


def parse_access_log_line(txt: str) -> dict:
    params = {
        "method": "",
        "target": "",
        "status": 0
    }
    match = re.match(ACCESS_LINE_RE, txt)
    if match is None:
        return params
    params["method"] = match.group("METHOD")
    params["target"] = match.group("URI")
    params["status"] = match.group("STATUS")
    return params


def parse_trace_log(inf)->dict:
    """
    Reads the trace log line by line and emits records.

    Each record is a dict that contains the request and result
    of resolution on the legacy n2t service.
    """
    buffer = {}
    while True:
        line = inf.readline()
        match = re.match(TRACE_LINE_BEGIN_RE, line)
        if match is not None:
            record = {
                "client": match.group("client"),
                "host": match.group("host"),
                "action": match.group("action"),
                "pid": match.group("PID"),
                "ip": match.group("IP"),
                "ua": match.group("UA"),
            }
            key = match.group("KEY")
            buffer[key] = record
            IP_DICT.add_ip(record["ip"])
            continue
        match = re.match(TRACE_LINE_END_RE, line)
        if match is not None:
            key = match.group("KEY")
            if key not in buffer:
                continue
            record = buffer[key]
            record["outcome"] = match.group("outcome")
            record["status"] = match.group("status")
            record["target"] = match.group("target")
            yield record
            del buffer[key]


async def send_request(record: dict, client):
    """
    Given a record of a resolve request from legacy n2t,
    replay the request on the new n2t and trace the redirects
    through known hosts. The final target address should match the
    target resolved by the legacy n2t service.
    """
    local_prefixes = [
        "https://uc3-ezid-n2t-prd.cdlib.org/",
        "https://arks.org/",
        "https://ezid.cdlib.org/",
    ]
    url = f"https://uc3-ezid-n2t-prd.cdlib.org/{record['pid']}"
    headers = {"User-Agent": record['ua']}
    try:
        req = client.build_request("GET", url, headers=headers)
        last_response = None
        while req is not None:
            response = await client.send(req)
            _url = str(response.url)
            _is_local = False
            for prefix in local_prefixes:
                if _url.startswith(prefix):
                    _is_local = True
            if not _is_local:
                last_response = response
                req = None
            else:
                req = response.next_request
                last_response = response
        result = {
            "status": last_response.status_code,
            "target": str(last_response.url)
        }
        return result
    except Exception as e:
        print(e)
    return None


async def resolve_task(id, q: asyncio.Queue):

    async with httpx.AsyncClient() as client:
        while True:
            record = await q.get()
            result = await send_request(record, client)
            if result is not None:
                if record['target'] == result['target']:
                    print(f"{id} {record['ip']:>18} {record['pid']:50} {result['status']}")
                else:
                    print(f"{id} {record['ip']:>18} {record['pid']:50} {record['target']:60} <> {result['target']:60} {result['status']}")
            q.task_done()


async def main():
    sys.stdin.reconfigure(encoding="ISO-8859-1")
    task_queue = asyncio.Queue(maxsize=10)
    pool = [asyncio.create_task(resolve_task(n, task_queue)) for n in range(0,10)]
    total = 0
    t0 = time.time()
    try:
        for record in parse_trace_log(sys.stdin):
            if record['outcome'] == "SUCCESS":
                total += 1
                #print(f"put {task_queue.qsize()}")
                await task_queue.put(record)
                if total % 100 == 0:
                    t1 = time.time()
                    print(f"Total: {total} over {(t1-t0):.1f} seconds, average = {total / (t1-t0):.2f} with {len(IP_DICT)} client locations")
                    with open("iplist.json", "w") as dst:
                        json.dump(IP_DICT.to_json(), dst, indent=2)
    except KeyboardInterrupt:
        for task in pool:
            task.cancel()
        sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
