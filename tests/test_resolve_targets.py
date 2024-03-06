"""
Implements tests for comparing legacy N2T resolution versus new N2T resolution
"""

import logging
import typing
import hopper

L = logging.getLogger()

def resolve(pid: str, resolver:str) -> hopper.Hops:
    url = resolver.format(pid=pid)
    return hopper.follow_redirects(url)


def resolve_pid(pid: str)-> typing.Tuple[hopper.Hops, hopper.Hops]:
    resolver_legacy = "https://n2t.net/{pid}"
    resolver_new = "http://127.0.0.1:8000/{pid}"
    legacy = resolve(pid, resolver_legacy)
    revised = resolve(pid, resolver_new)
    return legacy, revised


def compare_resolvers(pid):
    legacy, revised = resolve_pid(pid)
    L.info(f"{pid} -> {legacy.start_url} | {revised.start_url}")
    L.info(f"{pid} -> {legacy.final_url} | {revised.final_url}")
    print(f"{pid} match={legacy.final_url == revised.final_url} status => {legacy.hops[-1].status} | {revised.hops[-1].status}")


def main():
    pids = [
        "ark:/12345/foo",
        "ark:/13030/m5165j5h",
        "ark:/13030/c8dz0cbx",
        "ark:/88122/sgmy0083",
        "ark:/87278/s68eq8xm",
        "ark:/81423/m3js44",
        "ark:/65665/3f9782515-ef3b-40b0-97b3-0f30c5b0db03",
        "RRID:MMRRC_032054-JAX",
    ]
    for pid in pids:
        compare_resolvers(pid)

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    main()
