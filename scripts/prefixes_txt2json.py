"""
Script to generate a JSON representation of public information contained in the
"main_naans" resource maintained at https://github.com/CDLUC3/naan_reg_priv/main_naans

This script is intended to run under python 3.9+ using standard libraries only.
"""

import argparse
import dataclasses
import datetime
import json
import logging
import os
import sys
import typing

COMMENT_CHAR = "#"

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        return super().default(o)

@dataclasses.dataclass
class Agent:
    name: typing.Optional[str] = None


@dataclasses.dataclass
class ArkNaan:
    naan: int = 0
    org_name: str = ""
    org_acronym: typing.Optional[str] = None
    date_registered: typing.Optional[datetime.date] = None
    nma_url: list[str] = ()
    tenure_start: typing.Optional[int] = None
    org_type: typing.Optional[str] = None
    policy: typing.Optional[str] = None
    policy_narrative: typing.Optional[str] = None
    tenure_end: typing.Optional[datetime.date] = None


class ArkNaanPrivate(ArkNaan):
    naa_why: typing.Optional[str] = None
    contact: Agent
    address: typing.Optional[str] = None
    naa_history: list[int] = []

    def public(self):
        return ArkNaan(
            self.naan,
            self.org_name,
            self.org_acronym,
            self.date_registered,
            self.nma_url,
            self.tenure_start,
            self.org_type,
            policy=self.policy,
            policy_narrative=self.policy_narrative,
            tenure_end=self.tenure_end,
        )


def naan_from_rows(rows)->typing.Optional[ArkNaanPrivate]:
    L = logging.getLogger("naan_from_rows")
    if len(rows) < 1:
        return None
    key = rows.pop(0).strip()
    if key == "naa:":
        naan = ArkNaanPrivate()
        while True:
            try:
                row = rows.pop(0)
            except IndexError as e:
                break
            L.debug(row)
            parts = row.strip().split(":", 1)
            k = parts[0].strip().lower()
            if k == "who":
                ab = parts[1].split("(=)")
                naan.org_name = ab[0].strip()
                naan.org_acronym = ab[1].strip()
            elif k == "what":
                naan.naan = int(parts[1].strip())
            elif k == "when":
                naan.date_registered = datetime.datetime.strptime(parts[1].strip(),"%Y.%m.%d")
            elif k == "where":
                if len(naan.nma_url) < 1:
                    naan.nma_url = [parts[1].strip()]
                else:
                    naan.nma_url.append(parts[1].strip())
            elif k == "how":
                ab = parts[1].split("|")
                naan.org_type = ab[0].strip()
                naan.policy = ab[1].strip()
                if naan.policy == "(:unkn) unknown":
                    naan.policy = None
                naan.tenure_start = int(ab[2].strip())
            elif k == "!why":
                naan.naa_why = parts[1].strip()
            elif k == "!contact":
                agent = Agent(name=parts[1].strip())
                naan.contact = agent
            elif k == "!what":
                ab = parts[1].strip().split(" ", 1)
                naan.naa_history.append(int(ab[0]))
            elif k == "!address":
                naan.address = parts[1].strip()
        return naan
    return None


def load_ark_prefixes(fn_source: str):
    naans = []
    with open(fn_source, "rt") as fsrc:
        _block = []
        for line in fsrc:
            line = line.strip()
            if line.startswith(COMMENT_CHAR):
                continue
            if line == "":
                record = naan_from_rows(_block)
                if record is not None:
                    naans.append(record)
                _block = []
            else:
                _block.append(line)
        record = naan_from_rows(_block)
        if record is not None:
            naans.append(record)
    return naans


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="prefixes_txt2json",
        description="Generate JSON representation of public content in main_naans",
    )
    parser.add_argument("source", help="main_naans source file")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Set log level to DEBUG"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    L = logging.getLogger("prefixes")
    if not os.path.exists(args.source):
        L.error(f"Specified source not found: {args.source}")
        return 1
    L.info("Loading %s", args.source)
    naans = load_ark_prefixes(args.source)
    print(json.dumps(naans, indent=2, cls=EnhancedJSONEncoder))
    return 0


if __name__ == "__main__":
    sys.exit(main())
