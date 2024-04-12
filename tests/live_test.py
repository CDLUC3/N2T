"""
Given a feed from the legacy n2t access log, retrieve target and issue request against new n2t.

This script exercises the new n2t, arks.org, and ezid infrastructure by repeating requests being
made to legacy n2t to the new n2t service. It is used as a test mechanism for verifying that
requests made to the new n2t service provide the same result as issuing to the legacy n2t service.

legacy N2T logs are in /apps/n2t/sv/cv2/apache2/logs

Run me like:

  ssh n2t-prd 'tail -f /apps/n2t/sv/cv2/apache2/logs/transaction_log' | python live_test.py

Expects geoip city database in ../data

Download from https://www.maxmind.com/en/accounts/995868/geoip/downloads
"""

import asyncio
import json
import logging
import logging.config
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

LOGGING_CONFIG = {
    "version": 1,
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "http",
            "stream": "ext://sys.stderr"
        }
    },
    "formatters": {
        "http": {
            "format": "%(levelname)s [%(asctime)s] %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    'loggers': {
        'httpx': {
            'handlers': ['default'],
            'level': 'ERROR',
        },
        'httpcore': {
            'handlers': ['default'],
            'level': 'ERROR',
        },
        'test': {
            'handlers': ['default'],
            'level': 'INFO'
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)

L = logging.getLogger("test")


class IpAddressList:
    """
    Implements a cache of IP addresses and computes coordinates based on geoip2.

    Useful for basic metrics on the origin of requests.
    """
    def __init__(self, geo_database):
        self._L = logging.getLogger("IpAddressList")
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
                self._L.info(e)
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


async def parse_trace_log(inf)->dict:
    """
    Reads the trace log line by line and emits records.

    Each record is a dict that contains the request and result
    of resolution on the legacy n2t service.
    """
    buffer = {}
    while True:
        try:
            line = await inf.readuntil()
            line = line.decode("ISO-8859-1")
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
        except asyncio.IncompleteReadError as e:
            #L.info(e)
            await asyncio.sleep(0.5)

async def send_request(id, record: dict, client):
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
    visited = []
    try:
        visited.append(str(url))
        req = client.build_request("GET", url, headers=headers)
        last_response = None
        target_url = None
        while req is not None:
            try:
                L.debug("Send %s", req.url)
                response = await client.send(req)
            except Exception as e:
                L.error(f"client id %s url %s %s", id, req.url, e)
                break
            req = response.next_request
            if req is not None:
                _url = str(req.url)
                _is_local = False
                for prefix in local_prefixes:
                    if _url.startswith(prefix):
                        _is_local = True
                last_response = response
                target_url = _url
                if not _is_local:
                    break
                if _url in visited:
                    L.error("Cyclic redirect for %s", req.url)
                    raise ValueError("Redirect loop for %s", req.url)
                visited.append(_url)
                if not _is_local:
                    req = None
        L.debug("Finished last response %s", last_response.url)
        result = {
            "status": last_response.status_code,
            "target": target_url
        }
        return result
    except Exception as e:
        L.error("Client id %s : %s", id, e)
    return None


async def resolve_task(id, q: asyncio.Queue):
    """Worker that pulls tasks from queue and executes.
    """
    n = 0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            while True:
                record = await q.get()
                try:
                    result = await send_request(id, record, client)
                    n += 1
                    if result is not None:
                        print(f"{id} {n} {record['pid']} {record['target']} {result['target']} {result['status']}")
                except Exception as e:
                    L.error(e)
                q.task_done()
    finally:
        await client.aclose()
        L.warning("Client has bailed")


async def connect_stdin():
    """Create an async stdin reader
    """
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


async def main():
    n_workers = 10
    reader = await connect_stdin()
    task_queue = asyncio.Queue(maxsize=n_workers*10)
    pool = [asyncio.create_task(resolve_task(n, task_queue)) for n in range(0,n_workers)]
    total = 0
    t0 = time.time()
    try:
        async for record in parse_trace_log(reader):
            if record['outcome'] == "SUCCESS":
                total += 1
                L.debug(f"put {task_queue.qsize()}")
                await task_queue.put(record)
                if total % 100 == 0:
                    t1 = time.time()
                    print(f"Total: {total} over {(t1-t0):.1f} seconds, average = {total / (t1-t0):.2f} with {len(IP_DICT)} client locations")
                    with open("iplist.json", "w") as dst:
                        json.dump(IP_DICT.to_json(), dst, indent=2)
                await asyncio.sleep(0)
    except KeyboardInterrupt:
        for task in pool:
            task.cancel()
        sys.stdout.flush()



if __name__ == "__main__":
    asyncio.run(main())
