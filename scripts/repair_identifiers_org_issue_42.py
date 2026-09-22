#!/usr/bin/env python3
"""Apply the fixed identifiers.org data repair from roadmap issue 42."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any
from urllib.parse import unquote


MANIFEST_PATH = Path(__file__).parent / "fixtures" / "identifiers_org_issue_42.json"
SOURCE_SNAPSHOT_PATH = (
    Path(__file__).parent / "fixtures" / "identifiers_org_issue_42_source.json"
)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def choose_resource(namespace: dict[str, Any], overrides: dict[str, str]) -> dict[str, Any]:
    active = [resource for resource in namespace["resources"] if not resource["deprecated"]]
    selected_mir_id = overrides.get(namespace["prefix"])
    if selected_mir_id is not None:
        selected = [resource for resource in active if resource["mirId"] == selected_mir_id]
        if len(selected) != 1:
            prefix = namespace["prefix"]
            raise ValueError(
                f"{prefix}: resource override {selected_mir_id} is not uniquely active"
            )
        return selected[0]
    if len(active) != 1:
        raise ValueError(
            f"{namespace['prefix']}: expected one active resource, found {len(active)}"
        )
    return active[0]


def render_url(pattern: str, replacement: str) -> str:
    if pattern.count("{$id}") != 1:
        raise ValueError(f"expected one {{$id}} placeholder in {pattern!r}")
    return pattern.replace("{$id}", replacement)


def scheme_record(namespace: dict[str, Any], resource: dict[str, Any]) -> dict[str, Any]:
    redirect = render_url(resource["urlPattern"], "${content}")
    forward = render_url(resource["urlPattern"], "${ac}")
    sample_id = namespace["sampleId"]
    provider_code = resource["providerCode"] or None
    return {
        "id": namespace["prefix"],
        "target": {"DEFAULT": redirect},
        "type": "scheme",
        "name": resource["name"],
        "alias": None,
        "provider": provider_code,
        "provider_id": resource["mirId"],
        "primary": int(resource["official"]),
        "forward": forward,
        "redirect": redirect,
        "description": namespace["description"],
        "location": resource["location"]["countryName"],
        "institution": resource["institution"]["name"],
        "prefixed": int(namespace["namespaceEmbeddedInLui"]),
        "test": sample_id,
        "probe": render_url(resource["urlPattern"], unquote(sample_id)),
        "pattern": namespace["pattern"],
        "more": resource["resourceHomeUrl"],
        "revision": 0,
    }


def filename_for(prefix: str) -> str:
    filename = prefix.lower().strip().replace("/", "_")
    return "index_" if filename == "index" else filename


def encode_json(value: Any) -> bytes:
    return json.dumps(value, indent=2, ensure_ascii=False).encode()


def atomic_write(path: Path, content: bytes) -> None:
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(content)
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def is_placeholder(record: dict[str, Any], prefix: str) -> bool:
    target = record.get("target", {}).get("DEFAULT")
    redirect = record.get("redirect")
    return (
        record.get("id") == prefix
        and record.get("type") == "commonspfx"
        and not target
        and (not redirect or redirect == "N/A")
    )


def build_records(dataset: dict[str, Any], manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    missing = manifest["missing_prefixes"]
    placeholders = manifest["placeholder_prefixes"]
    if len(missing) != 167 or len(placeholders) != 11:
        raise ValueError("manifest must contain 167 missing and 11 placeholder prefixes")
    scope = missing + placeholders
    if len(scope) != len(set(scope)):
        raise ValueError("manifest prefix lists overlap or contain duplicates")

    namespaces: dict[str, dict[str, Any]] = {}
    for namespace in dataset["payload"]["namespaces"]:
        prefix = namespace["prefix"]
        if prefix in scope:
            if prefix in namespaces:
                raise ValueError(f"duplicate namespace {prefix!r} in resolver dataset")
            namespaces[prefix] = namespace
    absent = sorted(set(scope) - namespaces.keys())
    if absent:
        raise ValueError(f"resolver dataset is missing manifest prefixes: {', '.join(absent)}")

    overrides = manifest["resource_overrides"]
    if set(overrides) != {"clo", "col"}:
        raise ValueError("resource overrides must select only clo and col")
    return {
        prefix: scheme_record(namespaces[prefix], choose_resource(namespaces[prefix], overrides))
        for prefix in scope
    }


def verify_related_names(
    schemes_dir: Path,
    index: dict[str, str],
    related_names: dict[str, str],
) -> None:
    absent = [
        existing
        for existing in related_names.values()
        if index.get(existing) != filename_for(existing)
        or not (schemes_dir / f"{filename_for(existing)}.json").is_file()
    ]
    if absent:
        raise ValueError(f"related N2T names are missing or unindexed: {', '.join(absent)}")


def reconcile(
    schemes_dir: Path,
    records: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    check: bool,
) -> int:
    missing = set(manifest["missing_prefixes"])
    placeholders = set(manifest["placeholder_prefixes"])
    index_path = schemes_dir / "index.json"
    index = load_json(index_path)
    verify_related_names(schemes_dir, index, manifest["related_names"])
    differences: list[str] = []

    for prefix, expected in records.items():
        path = schemes_dir / f"{filename_for(prefix)}.json"
        if path.exists():
            actual = load_json(path)
            if actual == expected:
                continue
            if prefix in missing or not is_placeholder(actual, prefix):
                if check:
                    differences.append(str(path))
                    continue
                raise ValueError(f"refusing to overwrite non-placeholder record {path}")
        elif prefix in placeholders and not check:
            raise ValueError(f"expected placeholder record {path}")

        differences.append(str(path))
        if not check:
            atomic_write(path, encode_json(expected))

    expected_index = dict(index)
    for prefix in records:
        current = index.get(prefix)
        expected = filename_for(prefix)
        if current is not None and current != expected:
            if check:
                differences.append(str(index_path))
                continue
            raise ValueError(
                f"refusing to overwrite index mapping {prefix!r}: {current!r}"
            )
        expected_index[prefix] = expected
    if index != expected_index:
        differences.append(str(index_path))
        if not check:
            atomic_write(index_path, encode_json(expected_index))

    if check and differences:
        print("issue 42 repair differs:", file=sys.stderr)
        for path in differences:
            print(f"  {path}", file=sys.stderr)
        return 1
    action = "verified" if check else "reconciled"
    print(f"{action} {len(records)} issue 42 scheme records")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        type=Path,
        nargs="?",
        default=SOURCE_SNAPSHOT_PATH,
        help="downloaded resolver dataset, defaults to the fixed issue 42 snapshot",
    )
    parser.add_argument("--schemes-dir", type=Path, default=Path("schemes"))
    parser.add_argument("--check", action="store_true", help="report drift without writing files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_json(MANIFEST_PATH)
    actual_hash = file_sha256(args.dataset)
    expected_hashes = {
        manifest["source_snapshot"]["sha256"],
        manifest["resolver_dataset"]["sha256"],
    }
    if actual_hash not in expected_hashes:
        raise ValueError(
            "resolver data SHA-256 mismatch: expected a pinned issue 42 source, "
            f"found {actual_hash}"
        )
    dataset = load_json(args.dataset)
    records = build_records(dataset, manifest)
    return reconcile(args.schemes_dir, records, manifest, args.check)


if __name__ == "__main__":
    raise SystemExit(main())
