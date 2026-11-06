#!/usr/bin/env python3
"""
Build a per-assembly gene interval index from the Alliance JBrowse 2 GFFs.

Why this exists rather than a tabix dependency. A BLAST hit gives coordinates;
reaching a gene page needs the genes overlapping those coordinates, and
reaching orthologues needs that gene's curie. The Alliance already publishes
what is needed, as the `<Assembly>_all_genes` tracks in its JBrowse 2 config,
each a Gff3TabixAdapter over an S3 `.gff.gz` with a `.tbi`.

docs/ALLIANCE_WIDE_PLAN.md Phase 4 assumed the query path was a range request
answered by `tabix`, which is installed nowhere and would be a new runtime
dependency plus a live call to S3 on every hit. It does not have to be. Only
`gene` rows matter, and they carry five useful fields out of a file that is
mostly exons and CDS: measured on the yeast GFF, 6,613 gene rows out of
33,867 lines. Extracting those once at deploy time gives a table small enough
to ship beside the databases and answer by binary search, with no new binary
and no runtime network.

Output, one file per assembly:

    {"assembly": ..., "release": ..., "source": <gff url>,
     "counts": {...},
     "refs": {"<refName>": [[start, end, "Name", "curie-or-null"], ...]}}

Intervals are 1-based inclusive, as GFF gives them, and sorted by start, which
is asserted rather than assumed even though the sources are named `.sorted`.

Two data facts the caller has to live with, measured 2026-10-30:

  * Danio rerio carries `curie=` on 22,542 of 49,257 gene rows, 45.8%.
  * Xenopus laevis carries one on all 42,645, but 15,760 are `modelID:`
    rather than `Xenbase:`, and `modelID:` returns HTTP 200 with total=0 from
    the orthologue API.

Both are recorded per assembly in `counts` so a caller can say "no orthologues
for this gene" rather than show an empty panel.
"""

import argparse
import gzip
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

JBROWSE_CONFIG = "https://www.alliancegenome.org/jbrowse2/config.json"

# A curie the Alliance orthologue API can answer for. `modelID:` is a
# placeholder the Xenopus laevis GFF uses where no Xenbase gene exists; the API
# accepts it with HTTP 200 and returns total=0, so it is stored as null to stop
# a caller treating the 200 as a result.
USABLE_CURIE = re.compile(r"^(HGNC|MGI|RGD|ZFIN|FB|WB|SGD|Xenbase):")

ATTR_NAME = re.compile(r"(?:^|;)Name=([^;]*)")
ATTR_CURIE = re.compile(r"(?:^|;)curie=([^;]*)")


def fetch(url, timeout=600):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def all_genes_tracks(config):
    """Assembly name to GFF url, for every `<Assembly>_all_genes` track."""
    out = {}
    for track in config.get("tracks", []):
        tid = track.get("trackId", "")
        if not tid.endswith("_all_genes"):
            continue
        adapter = track.get("adapter", {})
        location = adapter.get("gffGzLocation") or {}
        if location.get("uri"):
            out[tid[: -len("_all_genes")]] = location["uri"]
    return out


def parse_genes(stream):
    """Yield (refname, start, end, name, curie, dropped_curie) per gene row.

    `curie` is the one the orthologue API can answer, or None. `dropped_curie`
    is what was in the file when it had to be discarded, so the caller can
    count placeholders instead of reporting a flat zero.
    """
    for raw in stream:
        if raw.startswith(b"#"):
            continue
        parts = raw.rstrip(b"\n").split(b"\t")
        if len(parts) < 9 or parts[2] != b"gene":
            continue
        attrs = parts[8].decode("utf-8", "replace")
        name_match = ATTR_NAME.search(attrs)
        curie_match = ATTR_CURIE.search(attrs)
        found = curie_match.group(1) if curie_match else None
        curie = found if found and USABLE_CURIE.match(found) else None
        yield (
            parts[0].decode(),
            int(parts[3]),
            int(parts[4]),
            name_match.group(1) if name_match else None,
            curie,
            None if curie else found,
        )


def build(assembly, gff_url, release, out_dir):
    refs = {}
    counts = {"genes": 0, "with_curie": 0, "unusable_curie": 0, "no_name": 0}

    # Streamed through memory rather than to a temporary file: the largest GFF
    # is 90 MB and the whole set is 313 MB, so a file would buy nothing and
    # leave something to clean up.
    with gzip.GzipFile(fileobj=io.BytesIO(fetch(gff_url))) as handle:
        for refname, start, end, name, curie, dropped in parse_genes(handle):
            counts["genes"] += 1
            if curie:
                counts["with_curie"] += 1
            if dropped:
                counts["unusable_curie"] += 1
            if name is None:
                counts["no_name"] += 1
            refs.setdefault(refname, []).append([start, end, name, curie])

    # Asserted rather than assumed: the sources are named .sorted, and a table
    # that is not sorted by start cannot be binary-searched.
    unsorted = [r for r, rows in refs.items()
                if any(rows[i][0] > rows[i + 1][0] for i in range(len(rows) - 1))]
    for ref in unsorted:
        refs[ref].sort(key=lambda row: (row[0], row[1]))

    doc = {
        "assembly": assembly,
        "release": release,
        "source": gff_url,
        "counts": counts,
        "refs": refs,
    }
    path = Path(out_dir) / f"{assembly}.genes.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as out:
        json.dump(doc, out, separators=(",", ":"))

    return path, counts, len(refs), unsorted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out-dir", default="../data/gene_index")
    parser.add_argument("-c", "--config", default=JBROWSE_CONFIG,
                        help="JBrowse 2 config URL or local path")
    parser.add_argument("-r", "--release", default="unknown",
                        help="Alliance release these GFFs belong to")
    parser.add_argument("-a", "--assembly", action="append",
                        help="limit to these assemblies; repeatable")
    args = parser.parse_args()

    Path(args.out_dir).mkdir(parents=True, exist_ok=True)

    if args.config.startswith(("http://", "https://")):
        config = json.loads(fetch(args.config))
    else:
        config = json.loads(Path(args.config).read_text())

    tracks = all_genes_tracks(config)
    if args.assembly:
        tracks = {k: v for k, v in tracks.items() if k in set(args.assembly)}
    if not tracks:
        print("no all_genes tracks matched", file=sys.stderr)
        return 1

    print(f"{len(tracks)} assemblies, writing to {args.out_dir}\n")
    total_bytes = 0
    for assembly in sorted(tracks):
        path, counts, n_refs, unsorted = build(
            assembly, tracks[assembly], args.release, args.out_dir
        )
        size = path.stat().st_size
        total_bytes += size
        pct = 100.0 * counts["with_curie"] / counts["genes"] if counts["genes"] else 0
        print(
            f"{assembly:<26} genes={counts['genes']:>7} "
            f"curie={counts['with_curie']:>7} ({pct:4.1f}%) "
            f"refs={n_refs:>5} {size/1e6:6.2f} MB"
            + (f"  resorted={len(unsorted)}" if unsorted else "")
        )
    print(f"\ntotal {total_bytes/1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
