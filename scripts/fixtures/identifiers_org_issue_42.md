# Identifiers.org issue 42 data repair

This repair covers the first checklist item in
[roadmap issue 42](https://github.com/CDLUC3/arks-n2t-roadmap/issues/42). It adds
167 missing prefixes and repairs 11 placeholder records.

The fixed scope came from the comparison audit dated 2026-09-18. The audit was
downloaded from the attachment URL recorded in
`identifiers_org_issue_42.json`. The resolver dataset was downloaded on
2026-09-22 from the identifiers.org URL in the same manifest. SHA-256 hashes
pin both inputs. `identifiers_org_issue_42_source.json` contains the 178 source
namespaces and selected resources needed to reproduce the repair offline.

Run the repair or verify the checked-in data from a fresh clone.

```sh
python3 scripts/repair_identifiers_org_issue_42.py
python3 scripts/repair_identifiers_org_issue_42.py --check
```

An explicit resolver dataset path must match the full download hash in the
manifest.

The manifest selects the only active resource for 176 prefixes. `col` selects
the official ChecklistBank resource `MIR:00000970`. `clo` selects the official
OLS resource `MIR:00000982`.

The `primary` field follows the selected resource's identifiers.org `official`
value. The snapshot has 173 official and five unofficial selected resources.

The new `go_ref`, `mmmp.biomaps`, and `slm` records coexist with N2T's existing
`go.ref`, `biomaps`, and `swisslipid` names. The repaired `gro` and `mi` records
coexist with `gramene.growthstage` and `psimi`. The script checks that all five
existing names remain present and does not edit them.

Named provider routes remain part of the provider review checklist item. The
affected namespaces contain 176 active resources with provider codes. Of the
selected default resources, 174 have provider codes. Adding those routes here
would double the data change before the provider policy review.

The regression fixture in `tests/test_data/identifiers_org_repairs.json` was
extracted independently from the comparison audit. The repair script does not
read or generate that fixture.

The resolver decodes percent escapes in incoming identifiers. The upstream
`datanator.reaction` sample keeps `%3E` in `test` and the pattern. Its `probe`
uses the decoded `>` that the resolver inserts into the redirect location.
