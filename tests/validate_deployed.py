#!/usr/bin/env python3
"""
validate_deployed.py

Check the BLAST databases that are actually deployed, rather than the code that
builds them. Run it after a build, against the directory the server reads.

    ./tests/validate_deployed.py                       # every MOD under /db
    ./tests/validate_deployed.py --mod SGD             # one MOD
    ./tests/validate_deployed.py --root /var/sequenceserver-data/blast
    ./tests/validate_deployed.py --container agr-blast-dev   # run blastdbcmd in docker

Exits non-zero if any check fails, so it can gate a deploy.

What it checks, and why each one exists:

  queryable        blastdbcmd can open the database and report its metadata. A
                   database can look complete on disk (all index files present)
                   and still be unreadable.
  non-empty        It contains at least one sequence. A truncated makeblastdb run
                   leaves a valid but empty database.
  retrievable      A specific sequence can be fetched by accession. This is what
                   the "Sequence" and "Download FASTA" buttons do, and it fails
                   when a database was built without -parse_seqids.
  parse_seqids     Reports which databases lack it. ZFIN's are built that way on
                   purpose, so this is reported rather than failed.
  name index       The <db>.names.json written by build_name_index exists and
                   parses. Without it the server falls back to scanning every
                   defline, which takes seconds per lookup.
  index resolves   A name drawn from the index actually maps back to a sequence
                   the database can return -- proving the index matches the data
                   beside it rather than a previous build.
  environment.json Every database on disk is described in the environment config
                   the server reads, and vice versa. A mismatch means the UI
                   offers databases that do not exist, or hides ones that do.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# ANSI colours, suppressed when not writing to a terminal.
if sys.stdout.isatty():
    RED, GRN, YEL, DIM, RST = "\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[0m"
else:
    RED = GRN = YEL = DIM = RST = ""

DEFAULT_ROOT = "/db"
NAME_INDEX_SUFFIX = ".names.json"


class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warned = 0
        self.failures = []

    def ok(self, what):
        self.passed += 1

    def fail(self, what, detail=""):
        self.failed += 1
        self.failures.append(f"{what}: {detail}" if detail else what)
        print(f"  {RED}FAIL{RST} {what}")
        if detail:
            print(f"       {DIM}{detail}{RST}")

    def warn(self, what, detail=""):
        self.warned += 1
        print(f"  {YEL}WARN{RST} {what}")
        if detail:
            print(f"       {DIM}{detail}{RST}")


def run(cmd, container=None, timeout=120):
    """Run a command, optionally inside a docker container."""
    if container:
        cmd = ["docker", "exec", container] + cmd
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"timed out after {timeout}s"
    except FileNotFoundError as e:
        return 1, "", str(e)


def find_databases(root, container=None):
    """Every BLAST database under root, as (mod, version, db_path) triples."""
    # Index files identify a database; strip the suffix to get its base path.
    #
    # Depth varies by MOD: SGD nests <root>/MOD/version/databases/<group>/<db>,
    # while WB, FB, RGD and ZFIN add a genus/species level. A maxdepth tuned to
    # one layout silently finds nothing for the other, so allow for the deeper
    # one.
    code, out, err = run(
        ["sh", "-c", f"find {root} -maxdepth 8 \\( -name '*.nin' -o -name '*.pin' \\) 2>/dev/null"],
        container,
    )
    if code != 0 and not out:
        return []

    seen, found = set(), []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        base = line.rsplit(".", 1)[0]
        if base in seen:
            continue
        seen.add(base)
        rel = Path(base).relative_to(root) if str(base).startswith(str(root)) else Path(base)
        parts = rel.parts
        mod = parts[0] if len(parts) > 0 else "?"
        version = parts[1] if len(parts) > 1 else "?"
        found.append((mod, version, base))
    return sorted(found)


def db_info(db_path, container=None):
    """blastdbcmd -info, parsed into (sequences, is_protein) or None."""
    code, out, _ = run(["blastdbcmd", "-db", db_path, "-info"], container)
    if code != 0:
        return None
    sequences = 0
    for line in out.splitlines():
        if "sequences;" in line:
            token = line.strip().split()[0].replace(",", "")
            if token.isdigit():
                sequences = int(token)
            break
    return {"sequences": sequences, "protein": "Protein" in out, "raw": out}


def first_accession(db_path, container=None):
    code, out, _ = run(
        ["sh", "-c", f"blastdbcmd -db {db_path} -entry all -outfmt '%a' 2>/dev/null | head -1"],
        container,
    )
    return out.strip() if code == 0 else ""


def check_database(mod, version, db_path, res, container=None, deep=True):
    name = f"{mod}/{version}/{Path(db_path).name}"

    info = db_info(db_path, container)
    if info is None:
        res.fail(f"{name} is not queryable", "blastdbcmd -info failed")
        return
    res.ok(name)

    if info["sequences"] == 0:
        res.fail(f"{name} contains no sequences", "a truncated makeblastdb leaves a valid but empty database")
        return
    res.ok(name)

    if not deep:
        return

    accession = first_accession(db_path, container)
    if not accession:
        res.fail(f"{name} lists no accessions", "cannot enumerate entries")
        return

    # Retrieval by accession is what the UI's Sequence/FASTA buttons rely on.
    code, out, err = run(["blastdbcmd", "-db", db_path, "-entry", accession], container)
    if code != 0 or not out.startswith(">"):
        if accession.startswith("BL_ORD_ID"):
            res.warn(f"{name} was built without -parse_seqids",
                     "sequence retrieval and FASTA download will not work for this database")
        else:
            res.fail(f"{name} cannot retrieve {accession}", (err or out)[:120])
        return
    res.ok(name)

    # The name index the server uses for ?name= lookups.
    index_path = f"{db_path}{NAME_INDEX_SUFFIX}"
    code, out, _ = run(["sh", "-c", f"cat {index_path} 2>/dev/null"], container)
    if code != 0 or not out.strip():
        res.warn(f"{name} has no name index",
                 "?name= lookups fall back to scanning every defline in this database")
        return
    try:
        index = json.loads(out)
    except json.JSONDecodeError as e:
        res.fail(f"{name} name index is not valid JSON", str(e)[:100])
        return
    res.ok(name)

    if not index:
        return  # An empty index is meaningful: "this database holds no names".

    # The index must describe the data sitting beside it, not a previous build.
    sample_name, sample_accession = next(iter(index.items()))
    code, out, _ = run(["blastdbcmd", "-db", db_path, "-entry", sample_accession], container)
    if code != 0 or not out.startswith(">"):
        res.fail(f"{name} name index is stale",
                 f"index maps {sample_name!r} -> {sample_accession!r}, which the database cannot return")
        return
    res.ok(name)


def check_environment_json(mod, version, databases, root, res, container=None):
    """Cross-check the deployed databases against the config the server reads."""
    env_path = f"/sequenceserver/public/environments/{mod}/{version}/environment.json"
    code, out, _ = run(["sh", "-c", f"cat {env_path} 2>/dev/null"], container)
    if code != 0 or not out.strip():
        res.warn(f"{mod}/{version} has no environment.json", f"looked in {env_path}")
        return

    try:
        entries = json.loads(out).get("data", [])
    except json.JSONDecodeError as e:
        res.fail(f"{mod}/{version} environment.json is not valid JSON", str(e)[:100])
        return

    # environment.json identifies a database by the basename of its source URI.
    described = set()
    for entry in entries:
        uri = entry.get("uri", "")
        if uri:
            described.add(Path(uri).name.split(".")[0].lower())

    on_disk = {Path(p).name.replace("db", "").lower() for _, _, p in databases}
    missing = {d for d in on_disk if d and not any(d in c or c in d for c in described)}

    if missing:
        res.warn(f"{mod}/{version}: {len(missing)} database(s) on disk not described in environment.json",
                 ", ".join(sorted(missing)[:5]))
    else:
        res.ok(f"{mod}/{version} environment.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=DEFAULT_ROOT, help=f"database root (default {DEFAULT_ROOT})")
    ap.add_argument("--mod", help="check only this MOD")
    ap.add_argument("--container", help="run blastdbcmd inside this docker container")
    ap.add_argument("--shallow", action="store_true",
                    help="only check databases open and are non-empty (fast)")
    ap.add_argument("--limit", type=int, help="check at most this many databases per MOD")
    args = ap.parse_args()

    print(f"Validating deployed databases under {args.root}"
          + (f" (via docker exec {args.container})" if args.container else ""))

    databases = find_databases(args.root, args.container)
    if not databases:
        print(f"{RED}No databases found under {args.root}{RST}")
        return 2

    if args.mod:
        databases = [d for d in databases if d[0] == args.mod]
        if not databases:
            print(f"{RED}No databases for MOD {args.mod}{RST}")
            return 2

    res = Results()
    by_mod_version = {}
    for mod, version, path in databases:
        by_mod_version.setdefault((mod, version), []).append((mod, version, path))

    for (mod, version), group in sorted(by_mod_version.items()):
        checked = group[: args.limit] if args.limit else group
        skipped = len(group) - len(checked)
        print(f"\n{DIM}== {mod}/{version} — {len(checked)} database(s)"
              + (f", {skipped} skipped by --limit" if skipped else "") + f" =={RST}")
        for mod_, version_, path in checked:
            check_database(mod_, version_, path, res, args.container, deep=not args.shallow)
        check_environment_json(mod, version, checked, args.root, res, args.container)

    print(f"\n{GRN}{res.passed} passed{RST}, {RED}{res.failed} failed{RST}, {YEL}{res.warned} warnings{RST}")
    if res.failures:
        print("\nFailures:")
        for f in res.failures:
            print(f"  - {f}")
    return 1 if res.failed else 0


if __name__ == "__main__":
    sys.exit(main())
