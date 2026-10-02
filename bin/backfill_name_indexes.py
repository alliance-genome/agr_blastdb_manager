#!/usr/bin/env python3
"""
Write a .names.json index beside every BLAST database that lacks one.

`?name=<gene symbol>` in SequenceServer resolves a symbol to a sequence by
reading an index next to each database. The index is written at build time by
build_name_index(), so only databases built since that existed have one --
today that is SGD and nobody else. Without it the lookup falls back to scanning
deflines, which on FlyBase takes 10-13 seconds and then finds nothing.

Rebuilding every database to get an index would mean re-downloading ~76 GB. It
is not necessary: the deflines are already inside the BLAST database, and
blastdbcmd will stream them back out. This reads them from there and derives
names with the same index_entries() the build path uses, so a backfilled index
and a freshly built one cannot disagree.

Usage:
    bin/backfill_name_indexes.py /var/sequenceserver-data/blast
    bin/backfill_name_indexes.py /var/sequenceserver-data/blast --dry-run
    bin/backfill_name_indexes.py /var/sequenceserver-data/blast --mod FB

Deflines carry a gene's symbol and nothing else, so a curator searching
FlyBase for "white" finds nothing -- only "w" is in the file. Pass FlyBase's
synonym table to index the full names too:

    curl -O https://s3ftp.flybase.org/releases/current/precomputed_files/\
synonyms/fb_synonym_fb_2026_03.tsv.gz
    bin/backfill_name_indexes.py /var/sequenceserver-data/blast --mod FB \
        --aliases fb_synonym_fb_2026_03.tsv.gz --force

The build path does this on its own now (see gene_aliases() in utils.py), so
this flag is for indexes built before that, which is all of them today.

Index keys are lower-cased so a lookup can be case-insensitive, which left the
search box showing "dll" for Dll and "cg2759" for CG2759. The spellings go in a
companion file; --display-only writes just that and leaves .names.json alone,
which is what to use on a live deployment:

    bin/backfill_name_indexes.py /var/sequenceserver-data/blast --mod FB \
        --aliases fb_synonym_fb_2026_03.tsv.gz --display-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils import (  # noqa: E402
    NAME_DISPLAY_SUFFIX,
    NAME_INDEX_SUFFIX,
    flybase_aliases,
    index_entries,
    write_display_names,
)


def databases(root: Path, mod: str | None):
    """
    Every BLAST database under root, as the path stem blastdbcmd expects.

    A database is several files sharing a stem (.nin/.nhr/.nsq, or .pin/...),
    and a large one is split into numbered volumes with an .nal/.pal alias. Key
    on the index file and de-duplicate by stem so a volume set is visited once.
    """
    seen = set()
    for suffix in ("*.nin", "*.pin", "*.nal", "*.pal"):
        for path in root.rglob(suffix):
            if mod and mod not in path.relative_to(root).parts[:1]:
                continue
            stem = path.with_suffix("")
            # Volumes are "<name>.00", "<name>.01", ... alongside the alias.
            if stem.suffix[1:].isdigit():
                stem = stem.with_suffix("")
            if stem in seen:
                continue
            seen.add(stem)
            yield stem


def deflines(db: Path, blastdbcmd: str):
    """
    Stream (accession, defline) out of a database.

    -outfmt '%a %t' gives accession and title, which is what the FASTA path
    yields too: there, the accession is the first whitespace-delimited token of
    the defline and the rest is the title.
    """
    argv = [blastdbcmd, "-db", str(db), "-entry", "all", "-outfmt", "%a %t"]
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        for line in proc.stdout:
            accession, _, title = line.partition(" ")
            if accession:
                yield accession, line
    finally:
        proc.stdout.close()
        proc.wait()


class Printer:
    """
    Minimal logger so write_display_names can report a failed write.

    Without one it swallows the error and returns 0, which is indistinguishable
    from "this database had no spellings to record" -- and that is exactly the
    answer a missing file gives, so the failure would be invisible.
    """

    def warning(self, message):
        print(f"  WARNING {message}", file=sys.stderr)

    def info(self, message):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path, help="e.g. /var/sequenceserver-data/blast")
    ap.add_argument("--mod", help="restrict to one MOD directory (FB, WB, ...)")
    ap.add_argument("--blastdbcmd", default="blastdbcmd")
    ap.add_argument("--dry-run", action="store_true", help="report what would be written")
    ap.add_argument("--force", action="store_true", help="rewrite indexes that already exist")
    ap.add_argument(
        "--aliases",
        type=Path,
        help="FlyBase fb_synonym_*.tsv.gz, to make full gene names searchable "
        "alongside the symbols the deflines carry",
    )
    ap.add_argument(
        "--display-only",
        action="store_true",
        help="write only the companion spelling file, leaving .names.json "
        "untouched -- the safe way to add capitalisation to a live deployment",
    )
    args = ap.parse_args()

    if not args.root.is_dir():
        print(f"not a directory: {args.root}", file=sys.stderr)
        return 2

    aliases = None
    if args.aliases:
        if not args.aliases.exists():
            print(f"no such alias file: {args.aliases}", file=sys.stderr)
            return 2
        aliases = flybase_aliases(args.aliases)
        print(f"  loaded names for {len(aliases):,} genes from {args.aliases.name}")

    written = skipped = empty = failed = 0
    names_total = 0
    started = time.monotonic()

    for db in sorted(databases(args.root, args.mod)):
        index_path = Path(f"{db}{NAME_INDEX_SUFFIX}")
        if args.display_only:
            # The inverse of the usual skip: a database with no index has no
            # names to label, and this mode must not create one.
            if not index_path.exists():
                skipped += 1
                continue
        elif index_path.exists() and not args.force:
            skipped += 1
            continue

        display: dict = {}
        try:
            index = index_entries(deflines(db, args.blastdbcmd), aliases, display)
        except OSError as e:
            print(f"  FAILED {db}: {e}", file=sys.stderr)
            failed += 1
            continue

        if not index:
            # A database whose deflines name nothing -- a genome assembly of bare
            # chromosome ids, say. Writing an empty index would be worse than
            # writing none: the lookup treats an index as authoritative for its
            # database and would stop scanning.
            empty += 1
            continue

        if args.display_only:
            names_total += len(display)
            if args.dry_run:
                print(f"  would write {len(display):>7} spellings  {db}{NAME_DISPLAY_SUFFIX}")
            else:
                write_display_names(display, str(db), Printer())
            written += 1
            continue

        names_total += len(index)
        if args.dry_run:
            print(f"  would write {len(index):>7} names  {index_path}")
            written += 1
            continue

        tmp = index_path.with_suffix(".json.tmp")
        try:
            with open(tmp, "w") as fh:
                json.dump(index, fh, separators=(",", ":"), sort_keys=True)
            tmp.replace(index_path)
        except OSError as e:
            print(f"  FAILED writing {index_path}: {e}", file=sys.stderr)
            failed += 1
            continue
        write_display_names(display, str(db), Printer())
        written += 1

    elapsed = time.monotonic() - started
    verb = "would write" if args.dry_run else "wrote"
    what = "spelling file(s)" if args.display_only else "index(es)"
    unit = "spellings" if args.display_only else "names"
    print(
        f"\n{verb} {written} {what}, {names_total:,} {unit}; "
        f"{skipped} skipped, {empty} had no names to index, {failed} failed "
        f"({elapsed:.1f}s)"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
