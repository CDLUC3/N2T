import sys
import os
import logging
import click
import json
import time
import urllib.parse
import requests
import htrace
import lib_n2t.prefixes
import jdcal


# Global for access by event hooks
_session = requests.Session()

W = "\033[0m"  # white (normal)
R = "\033[31m"  # red
G = "\033[32m"  # green
O = "\033[33m"  # orange
B = "\033[34m"  # blue
P = "\033[35m"  # purple

L = logging.getLogger("n2t")


def datetimeToJD(dt):
    mjd0, mjd = jdcal.gcal2jd(dt.year, dt.month, dt.day)
    jd = mjd0 + mjd + (dt.hour*3600 + dt.minute*60 + dt.second + dt.microsecond/1E6) / 86400.0
    return jd


def printSummary(s):
    L = logging.getLogger("SUMMARY:")
    L.info(f"Start URL: {s['responses'][0]['url']}")
    L.info(f"Final URL: {s['request']['url']}")
    L.info(f"Start: {s['tstart']}")
    L.info(f"Num requests: {len(s['responses'])}")
    L.info(f"Elapsed: {s['elapsed']:.3f} seconds")


def cbUrl(response, *args, **kwargs):
    OUT = logging.getLogger(">")
    IN = logging.getLogger("<")
    OUT.info(f"{G}{response.request.method}: {response.request.url}{W}")
    OUT.info(f"{G}Accept: {response.request.headers.get('Accept', '-')}{W}")
    IN.info(f"{P}{response.status_code}{B} {response.url}{W}")
    rh = response.headers
    for h in sorted(response.headers.keys()):
        IN.info(f"{B}{h}{W}: {response.headers[h]}")
    IN.info(f"{R}{htrace.dtdsecs(response.elapsed):.4f} sec{W}")


def cbUrlMinimum(response, *args, **kwargs):
    OUT = logging.getLogger(">")
    IN = logging.getLogger("<")
    OUT.info(f"{G}{response.request.method}: {response.request.url}{W}")
    meta = (
        response.headers.get("location", response.headers.get("content-type"))
            .encode("iso-8859-1")
            .decode()
    )
    IN.info(f"{P}{response.status_code}{B} {G}{meta}{W}")
    IN.info(f"{R}{htrace.dtdsecs(response.elapsed):.4f} sec{W}")


def cbLinkFollow(response, *args, **kwargs):
    global _session
    L = logging.getLogger("L")
    # First check to see if response matches requested properties
    if _session._extra["link_type"] is not None:
        if (
                response.headers.get("Content-Type", "").find(_session._extra["link_type"])
                >= 0
        ):
            if _session._extra["link_profile"] is None:
                L.info(f"Match linked type {R}{_session._extra['link_type']}{W}")
                return
            _profile = response.headers.get("Content-Profile", "")
            if _profile.find(_session._extra["link_profile"]) >= 0:
                L.info(
                    f"Match linked type {R}{_session._extra['link_type']}{W} and profile {R}{_session._extra['link_profile']}{W}"
                )
                return

    alllinks = htrace.parseLinkHeader(response.headers.get("Link", ""))
    lhs = alllinks.get(_session._extra["link_rel"], [])
    for lh in lhs:
        if lh["type"] == _session._extra["link_type"]:
            if (
                    _session._extra["link_profile"] is None
                    or lh.get("profile", "") == _session._extra["link_profile"]
            ):
                link_url = urllib.parse.urljoin(response.url, lh["target"])
                # Fake out requests with an injected redirect
                response.headers["Location"] = lh["target"]
                response.status_code = 302
                L.info(f"Follow Link: {R}{link_url}{W}")


@click.group()
@click.pass_context
@click.argument("source")
def main(ctx, source):
    lformat = "%(name)s: %(message)s"
    #if log_time:
    #    lformat = "%(asctime)s.%(msecs)03d:%(name)s %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=lformat,
        datefmt="%Y-%m-%d %H:%M:%S",
    )    
    # Setup context for operations
    ctx.ensure_object(dict)
    ctx.obj["source"] = source
    ctx.obj["pfx"] = None

    # if provided a sqlite source, then open connection   
    ctx.obj["pfx"] = lib_n2t.prefixes.PrefixList(fn_src=ctx.obj["source"])
    L.info("Prefixes loaded from: %s", ctx.obj["source"])


@main.command()
@click.option("-d", "--destfn", default=None, required=True, help="File name for target JSON document")
@click.option("-l","--lines", is_flag=True, default=False, help="Output as JSON-lines")
@click.pass_context
def tojson(ctx, destfn, lines):
    """
    """
    if lines:
        ctx.obj['pfx'].store_jsonl(destfn)
    else:
        ctx.obj['pfx'].store(destfn)
    L.info("Prefixes stored to: %s", destfn)


@main.command()
@click.option("-f", "--field", default=None, help="Show distinct values for specified field")
@click.pass_context
def summary(ctx, field):
    pfx = ctx.obj["pfx"]
    print(f"Source: {ctx.obj['source']}")
    print(f"Total prefixes: {pfx.length()}")
    print(f"Row  Count Key")
    props = pfx.fields()
    i = 0
    for k in sorted(list(props.keys())):
        print(f"{i:3} {props[k]:6} {k}")
        i += 1
    if field is not None:
        fvalues = pfx.fieldValues(field)
        print("")
        print(f"Distinct values for field: {field}")
        print(" Count Value")
        for k, v in fvalues.items():
            print(f"{v:6} {k}")


@main.command()
@click.pass_context
def prefixes(ctx):
    pfx = ctx.obj["pfx"]
    for prefix in pfx.prefixes():
        print(prefix)


@main.command()
@click.argument("prefix")
@click.pass_context
def prefix(ctx, prefix):
    pfx = ctx.obj["pfx"]
    entry = pfx.getEntry(prefix)
    if entry is not None:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return
    L.error("No entry found for %s", prefix)


@main.command()
@click.pass_context
@click.argument("identifier")
def resolver(ctx, identifier):
    pfx = ctx.obj["pfx"]
    normalized, resolver_key, resolver = pfx.resolve(identifier)
    print(f"Normalized id: {normalized['normal']}")
    print(f"Resolved URL: {normalized['url']}")
    print(f"Resolver: {resolver_key}")
    print(json.dumps(resolver, indent=2, ensure_ascii=False))


@main.command()
@click.pass_context
@click.argument("identifier")
@click.option("-a", "--accept", default="*/*", help="Accept header value")
@click.option("-t", "--test", is_flag=True, help="Try resolving URL")
@click.option("-T", "--timeout", default=10, help="Request timeout in seconds")
@click.option(
    "-k", "--insecure", default=False, is_flag=True, help="Don't verify certificates"
)
@click.option("-L", "--link-type", default=None, help="Follow link header with type")
@click.option(
    "-P", "--link-profile", default=None, help="Follow link header with profile"
)
@click.option(
    "-R", "--link-rel", default="alternate", help="Follow link header with rel"
)
@click.option("-U", "--user-agent", default=None, help="User agent header value")
def resolve(ctx, identifier, accept, test, timeout, insecure, link_type, link_profile, link_rel, user_agent):
    pfx = ctx.obj["pfx"]
    normalized, resolver_key, resolver = pfx.resolve(identifier)
    L.info("Normalized id: %s", normalized['normal'])
    L.info("Using resolver: %s", resolver_key)
    L.debug(json.dumps(resolver, indent=2, ensure_ascii=False))
    url = normalized['url']
    L.info("URL: %s", url)
    if test:
        global _session
        accept = htrace.ACCEPT_VALUES.get(accept, accept)
        headers = {
            "Accept": accept,
            "User-Agent": htrace.USER_AGENT,
        }
        if not user_agent is None:
            headers["User-Agent"] = user_agent
        url_cb = cbUrl
        hooks = {"response": [url_cb, cbLinkFollow]}
        tstart = time.time()
        _session._extra = {
            "link_type": link_type,
            "link_rel": link_rel,
            "link_profile": link_profile,
        }
        response = _session.get(
            url,
            timeout=timeout,
            headers=headers,
            hooks=hooks,
            allow_redirects=True,
            verify=not insecure,
        )
        tend = time.time()
        summary = htrace.responseSummary(response, tstart, tend)
        printSummary(summary)


if __name__ == "__main__":
    sys.exit(main())
