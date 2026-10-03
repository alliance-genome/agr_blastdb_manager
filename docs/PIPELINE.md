# How the BLAST database build pipeline works

One run of `src/create_blast_db.py` turns one MOD release's JSON config into a
directory of `makeblastdb` output under `/var/sequenceserver-data/blast`, where
all three SequenceServer containers read it. There is no scheduler, no queue and
no job state: a release is built by a person running one command, and the command
publishes to the live service when it finishes. Understanding that last sentence
is most of understanding this pipeline.

Line references in this document are to `92fdc2a` (`origin/main`). The build
host's checkout is one commit ahead of that: `c4daac6` inserts at
`src/utils.py:657` and `:774`, so citations into that file below those points sit
8 and 19 lines lower there. Every other file cited is byte-identical.

## Where the inputs are

The configs are **not** in this repository. `.gitignore` lists `conf`, and
`git ls-tree origin/main` confirms no `conf/` is tracked; the `conf/` directory
that exists on the build host is untracked leftover from 2024 and still names
WS285/WS286. The real configs live in a sibling repo:

    /home/ec2-user/gitroot/agr_blast_service_configuration/conf/<MOD>/databases.<MOD>.<release>.json

36 files are tracked there: 35 database configs plus `conf/global.yaml`. Roughly
one config per MOD per release, but only roughly —
`databases.SGD_fungal.2024-04-11.json` and `databases.SGD_fungal.2024-04-15.json`
both declare `release: SGD:2024-04-11`, and several SGD releases have a `_test`
variant sitting alongside them. Each JSON has a `metadata` block (contact,
`dataProvider`, `release`, `dateProduced`) and a `data` array of entries. An
entry is the unit of work:

```json
{
  "blast_title": "D. melanogaster Transcripts 6.69",
  "description": "D. melanogaster Transcripts 6.69",
  "genus": "Drosophila",
  "species": "melanogaster",
  "md5sum": "34b1293e7c7651da88f9ef79d313531b",
  "taxon_id": "7227",
  "uri": "https://s3ftp.flybase.org/alliance/blast/dmel-transcript.fasta.gz",
  "version": "6.69",
  "seqtype": "nucl"
}
```

`blast_title`, `uri`, `md5sum`, `seqtype` and `taxon_id` are load-bearing.
`genus` and `species` decide where the database lands on disk unless the entry
carries `seqcol_type` (SGD) or `seqcol` (legacy), in which case those do
(`src/create_blast_db.py:87-102`). `taxon_id` is written as `NCBITaxon:7955` by
some MODs and bare as `7227` by others; the code strips the prefix
(`:308`). An optional `genome_browser` block is copied through to the deployed
config and drives the JBrowse links in SequenceServer — the pipeline only
mirrors it into `genome_browser_map.{json,rb}` (`src/utils.py:1280`).

## Running it

uv is the only supported package manager. The project has no `[tool.poetry]`
section any more, so `poetry install` does not work, whatever `README.md` said
before `ddcdd7d`.

```bash
uv sync --locked --extra dev        # dev extras: pytest, hypothesis, playwright, ruff
```

`--locked` fails rather than re-resolving, which is the point: the lockfile and
the environment cannot drift apart silently.

Every path inside the script is relative to `../data` and `../logs`, so it has
to be run from `src/`. Run it from the repository root and it will create
`/home/ec2-user/gitroot/data/` and work there instead.

```bash
cd src
uv run python create_blast_db.py --help
```

The flags, as `--help` prints them:

| flag | effect |
|---|---|
| `-j, --input_json` | one config file; the usual way to build a release |
| `-g, --config_yaml` | a `global.yaml` naming many MOD/release pairs |
| `-e, --environment` | the release directory to write under; default `dev` |
| `-m, --mod` | only used to pick the MOD for `--validate` |
| `-d, --db_names` | comma-separated `blast_title`s; everything else is skipped |
| `-l, --list` | print the `blast_title`s in a config and exit |
| `-c, --check-parse-seqids` | download and report policy, build nothing, publish nothing |
| `--limit-dbs N` | process only the first N entries |
| `--skip-md5-check` | skip checksum verification |
| `--store-files` | keep the downloaded archive in `../data/database_<YYYY_Mon_DD>/` |
| `-cl, --cleanup` | delete FASTA files at the end; **on by default** |
| `--validate` | BLAST conserved sequences against what was built |
| `--validation-path` | where `--validate` looks; default `/var/sequenceserver-data/blast` |
| `-u, --update-slack` | post a summary to `#blast-status` |
| `-s3, --sync-s3` | `aws s3 sync ../data` to `$S3`, then S3 to `$EFS` |
| `-s, --skip_efs_sync` | with `-s3`, stop after S3 |

There is **no flag that disables publishing to production.** The copy at
`src/create_blast_db.py:1106-1208` runs on any build that is not
`--check-parse-seqids` and in which at least one entry succeeded. See
*Publishing* below.

`-g` looks tempting and is almost always wrong, and there are two `global.yaml`
files to be wrong with. The one in the configuration repo names WS291, WS292,
FB2024_04, SGD 2024-06-13, XB 5.5.1 and `ALLIANCE/prod` — five stale releases and
the one that is already broken. The untracked `conf/global.yaml` on the build
host is worse: WS285 and WS286 only, with the FB, SGD and XB blocks commented out
and no ALLIANCE block at all. That second one is the file `make docker-run`
passes to `--config_yaml`, because `CONFIG_DIR` is `$(pwd)/conf` and the target
mounts it at `/conf`. A release is built with `-j` and an explicit `-e`.

`-e` is free text and does not have to match the config filename. The SGD
directories on the host prove it: `SGD/R64-5-1f` (312 databases) was built from
`databases.SGD_fungal_test.2025-10-11.json` and `SGD/R64-5-1m` (183) from
`databases.SGD.test.2025-10-07.json`. The MOD, by contrast, is derived from the
filename's second dot-separated field by prefix match against
`["FB","SGD","WB","XB","ZFIN","RGD"]` (`src/utils.py:403-432`), which is how
`SGD_fungal_test` becomes `SGD`. A name matching nothing is passed through
verbatim, which is the only reason `ALLIANCE` works at all.

## Building one database, start to finish

The real example is FlyBase's transcript set, which this pipeline lost in
September 2026 and recovered on 1 October. Curators reported it as "the option to
search annotated transcripts has disappeared" after seven releases of having it.

```bash
cd /home/ec2-user/gitroot/agr_blastdb_manager/src
uv run python create_blast_db.py \
  -j ../../agr_blast_service_configuration/conf/FB/databases.FB.FB2026_03.json \
  -e FB2026_03 \
  -d "D. melanogaster Transcripts 6.69"
```

That config holds 200 entries (`-l` prints 200 titles; the host serves 200
databases for `FB/FB2026_03`). `-d` narrows the run to one of them. Run as
written today it fails at step 4, because the pinned checksum is now stale — see
*FB2026_03's pin is stale right now* below. What happens:

1. `get_mod_from_json` reads `FB` out of the filename.
2. `process_entry` (`:505`) opens a per-entry log at
   `../logs/Drosophila_melanogaster_nucl_2026_Oct_02.log`. The filename is built
   from `genus`, `species` and `seqtype` run through `log_safe_filename`
   (`src/utils.py:337`) — not cosmetic: SGD's genus is literally
   `S288C Reference (DNA/RNA/Vector)`, and before `c76c585` those slashes made
   this a path into non-existent directories, so every S288C database failed on
   `FileNotFoundError` before it was even downloaded, while the run still
   reported success.
3. The URI is `https://`, so `get_files_http` (`src/utils.py:985`) shells out to
   `wget --timeout=30 --tries=3` into `../data/dmel-transcript.fasta.gz`
   (20,130,525 bytes).
4. The md5 is checked against the config. See *The checksum pin*.
5. `create_db_structure` makes
   `../data/blast/FB/FB2026_03/databases/Drosophila/melanogaster/D_melanogaster_Transcripts_6_69/`.
   The leaf is `blast_title` with `\W+` collapsed to `_`; SequenceServer uses
   exactly that string as the database title, and re-derives it from
   `blast_title` the same way when it needs the organism back.
6. `gunzip -v ../data/dmel-transcript.fasta.gz` (`:605`).
7. `deduplicate_fasta` rewrites the FASTA. This file needed it when the database
   was built on 1 October 2026 — 39,891 records down to 35,738. The file
   FlyBase publishes now does not, so on a rebuild this step would find nothing
   to do and return in one pass.
8. `makeblastdb` runs, with `-parse_seqids`.
9. `build_name_index` writes `dmel-transcriptdb.names.json` and
   `dmel-transcriptdb.names.display.json` beside the database.
10. Both the `.gz` and the unzipped FASTA are deleted (`:373-389`), and
    `cleanup_fasta_files` sweeps `../data` again at the end of the run.
11. `copy_config_file` writes the input JSON out as
    `../data/config/FB/FB2026_03/environment.json`.
12. `copy_to_production` `rmtree`s and replaces
    `/var/sequenceserver-data/blast/FB/FB2026_03/databases`, and
    `copy_config_to_production` writes the config to
    `/var/sequenceserver-data/config-dev/FB/FB2026_03/`.

The command assembled at `:304-310` is:

```
makeblastdb -in ../data/dmel-transcript.fasta -dbtype nucl \
  -title 'D_melanogaster_Transcripts_6_69' \
  -out <output_dir>/dmel-transcriptdb \
  -taxid 7227 -parse_seqids
```

The `db` basename comes from `fasta_file.replace(extensions, 'db')` where
`extensions = "".join(Path(fasta_file).suffixes)`. Because `Path.suffixes`
splits on every dot, a filename with dots in its stem gets truncated:
`GCF_015227675.2_mRatBN7.2_genomic.fna.gz` yields `GCF_015227675db`, which is
what is on disk at
`/var/sequenceserver-data/blast/RGD/8.3.0/databases/Rattus/norvegicus/mRatBN7_2/`.
Harmless, because nothing user-facing reads that basename — the directory name
is what the tree shows — but it means you cannot identify an assembly from the
database files.

The result, verified from the deployed `.njs`:

```
dbname               dmel-transcriptdb
number-of-sequences  35738
number-of-letters    92863658
last-updated         2026-10-01T19:35:00
```

35,738 is the de-duplicated count, which is the whole story of the next two
sections.

### The three on-disk layouts

`create_db_structure` picks one of three shapes per entry, and the choice shows
up directly in SequenceServer's database tree, so it is a presentation decision
dressed as a path decision. Two of the three are in use:

| config field | path under `databases/` | example |
|---|---|---|
| `seqcol_type` | `<seqcol_type>/<blast_title>` | `SGD/R64-5-1m/databases/S288C_Reference_Strain_Genomic_DNA/Nuclear_chromosomes/` |
| `seqcol` | `<seqcol>/<blast_title>` | legacy; no current config uses it |
| neither | `<genus>/<species>/<blast_title>` | `FB/FB2026_03/databases/Drosophila/melanogaster/D_melanogaster_Transcripts_6_69/` |

Every component goes through `re.sub(r"\W+", "_", …).strip("_")` except `genus`
and `species` in the third form, which are interpolated **verbatim**. That is
why `docs/alliance_2024_build_failure.md` notes that a complete ALLIANCE build
would render two separately misspelled *Xenopus* genera (`xenupus` and
`xenupos`) as two sibling nodes in the tree: the config is the only validation
there is.

Nothing requires two entries to land in different directories, and two
legitimately do not. `databases.ZFIN.production.json` declares `ZFIN TALEN
Sequences` twice, once for `talen_fasta.fa.gz` and once for `zfin_mrph.fa.gz`;
`databases.WB.WS285.json` declares `C. elegans Genome Assembly` three times, once
per bioproject. They can share a directory because the database basename inside
it comes from the FASTA filename rather than from `blast_title`. That is fine
until one of them fails, because `run_makeblastdb` cleans up after a failure by
`rmtree`ing the whole output directory rather than the files it wrote — on a
non-zero `makeblastdb` exit (`src/create_blast_db.py:348`) and again on any
exception (`:396`). A later entry failing therefore deletes an earlier entry's
finished database, and the run reports only its own failure. The deployed
`ZFIN/prod/.../ZFIN_TALEN_Sequences/` holds `zfin_mrph.fa` and nothing else;
whether `talen_fasta` was lost this way or simply never downloaded is not
recoverable from what is on disk.

## The checksum pin

`md5sum` in the config is a pin, not a hint. `check_md5sum` (`src/utils.py:364`)
reads the whole downloaded file into memory, hashes it, and on a mismatch returns
`False`, which makes `get_files_http`/`get_files_ftp` return `False`, which makes
`process_entry` return `False` and record the failure under stage `download`.
Note that the message it logs is `File download failed from <uri>` — the download
succeeded; only the hash disagreed. Read the per-entry log for `MD5 checksums do
not match` to tell the two apart.

ZFIN is exempt (`src/utils.py:1057-1058`, `:1191-1192`). The code does not say
why, and `databases.ZFIN.production.json` does carry an `md5sum` on all thirteen
of its entries, so the exemption is a policy decision recorded nowhere — treat
it as load-bearing until someone establishes otherwise. `--skip-md5-check`
exempts everything, and logs a warning four times on the way for the benefit of
whoever reads the log later — once per run (`src/create_blast_db.py:1044`), once
per config file (`:737`), and twice per entry inside the download helper
(`src/utils.py:997` and `:1055`, or `:1086` and `:1187` on the FTP path).

**This pin is how ALLIANCE lost *C. elegans*.** `docs/alliance_2024_build_failure.md`
is the record and should be read rather than summarised; the short version is that
`/blast/ALLIANCE/prod/` declares nine reference genomes and has served exactly one
since 2024. One build ran, on 2024-10-09 at 03:42, for 65 seconds. Entry 1,
*C. elegans*, failed on a stale md5. Entry 2, zebrafish, built. Entry 3 then
spent 28 seconds downloading until the disk filled, and entries 4 through 9
failed inside a single second between them, each with `[Errno 28] No space left
on device`. **The run exited 0.** A year later the one database that existed was
copied to production alongside the config describing all nine, and every check
since has agreed that one database is the correct number —
including this repo's own `tests/blast_test_results/TEST_REPORT.md`, which records
`| ALLIANCE | prod | 1 | 0 | ✓ PASS |`. Of the nine checksums, eight still matched
when re-verified in 2026; only *C. elegans* was stale.

The deployed zebrafish database still carries `"last-updated":
"2024-10-09T03:42:00"` in its `.njs`, and has no `.nog`/`.nos` files, so it was
built without `-parse_seqids` — which is why its accessions come back as
`BL_ORD_ID:0`.

Nothing in the pipeline checks free space before starting, and there is still no
`ENOSPC` handler that stops the run rather than continuing to the next entry. The
host is at 170 GB of 250 GB used.

### FB2026_03's pin is stale right now

Checked 2026-10-02 by streaming the object through `md5sum`:

```
configured (databases.FB.FB2026_03.json)  34b1293e7c7651da88f9ef79d313531b
actual                                    015f3efbffdc7dc8cc362e5a21ed3cb8
last-modified (HTTP HEAD)                 Thu, 01 Oct 2026 20:56:27 GMT
```

A rebuild of FB2026_03 today fails on that entry, in exactly the way ALLIANCE
failed. The reason the object changed is good news: FlyBase have fixed their
assembly script. The new file holds 35,738 records under 35,738 distinct ids —
zero duplicates, zero records with invalid residues — and `FBtr0077872` is now
just its 71 bp tRNA. Update the `md5sum` in the config before rebuilding;
`/home/ec2-user/fb-transcript-6.69-check/compare.sh` watches both this object and
FlyBase's canonical export and prints the new value.

## `deduplicate_fasta`

`makeblastdb -parse_seqids` refuses a file containing two records with the same
id, and `-parse_seqids` is mandatory for every MOD except ZFIN
(`src/create_blast_db.py:274-280`). Without it, accessions come back as
`BL_ORD_ID:n` and nothing downstream can link a hit to a gene. So a duplicate id
is not untidiness, it is a build failure — and in September 2026 it was a silent
one: `makeblastdb` exited non-zero, the entry failed, the run exited 0, and the
other four FlyBase melanogaster databases shipped without it.

`deduplicate_fasta` (`:131-252`) exists to get past that, and is called only on
the `-parse_seqids` path (`:284`), because that is the only place a duplicate id
matters. One streaming pass establishes whether any id repeats at all, and if
none does it returns `None` — so the normal case costs a single read and rewrites
nothing. Only a file that needs changing is read a second time and replaced.

The design point is **what it refuses to do.** Two different things produce a
duplicate id and they get different treatment:

*The same record twice.* FlyBase's `alliance/blast/dmel-transcript.fasta.gz` was
assembled by concatenating six of their own export files with four of them
included twice each: 39,891 records under 35,738 distinct ids, 4,153 duplicates,
all but one a byte-identical twin. Dropping the copy loses nothing, so copies that
compare equal collapse and the first occurrence is kept, preserving file order so
the result stays diffable against its source.

*One copy corrupt.* `FBtr0077872` appeared twice in that file: once as the 71 bp
tRNA its own `loc=` describes, and once as that sequence with a line of `ls -l`
output concatenated onto the end —

    ...CGGCCGATGCA-rw-r--r-- 1 argosadm fbadmin 61946 Sep  9 12:50
    /bio/ftp/genomes/Drosophila_melanogaster/current/fasta/dmel-all-miRNA-r6.69.fasta.gz

a directory listing that leaked into the export between two concatenated parts,
and the long-standing source of the `FASTA-Reader: Ignoring invalid residues ...
On line 54667` warning in the build log. That copy is identifiable without
guessing, because it is not sequence data: `VALID_RESIDUES` (`:125-127`) lists the
IUPAC codes, gaps and stops a FASTA of each declared `seqtype` may contain, and
the corrupt copy fails that test while the good one passes. Where exactly one of
several copies is valid, the invalid ones are discarded and a warning names the id
and the count.

*Anything else is refused.* If an id still names more than one distinct,
individually valid record, `deduplicate_fasta` logs an error, rewrites nothing,
and returns `{"unresolved": n, "removed": 0}` so `makeblastdb` rejects the file
(`:211-218`). Silently picking one of two plausible records is how a deployment
ends up serving data nobody has checked, and the right answer at that point is a
conversation with whoever produced the file. The alphabet check follows the
declared `seqtype`, so protein records are not judged by nucleotide rules — and
with an unrecognised `seqtype` there is no alphabet, so differing copies are
unresolved rather than ranked by a rule that does not apply.

The function is a workaround and says so in its own log line: "This is a
workaround; the source export should be fixed." It was the right call — the
de-duplicated 35,738-record set is *more* complete than FlyBase's canonical
`dmel-all-transcript-r6.69`, which has only the 30,838 mRNAs and none of the
ncRNAs, miRNAs or tRNAs a curator wants. And it has now been vindicated: the
upstream file FlyBase publishes today contains those same 35,738 records with the
duplicates and the corruption gone.

`src/create_blast_db.py:187` computes a `repeated` dict that nothing reads. Dead.

## Indexing gene names

After a successful `makeblastdb` and before the FASTA is deleted,
`build_name_index` (`src/utils.py:730`) writes `<db>.names.json` and
`<db>.names.display.json` beside the database, so SequenceServer can answer
`?name=` and the gene search box without reading every defline in the deployment.
On FlyBase the alias table from
`fb_synonym_fb_<release>.tsv.gz` is fetched once per run (`gene_aliases`,
`src/utils.py:564`) and joined to records by `parent=FBgn…`, which is what makes
"white" findable when the defline only ever says `name=w-RA`. The transcript
database's index holds 131,148 names for 35,738 records.

The file formats, the grammar of each MOD's deflines, the display-spelling
companion file and `bin/backfill_name_indexes.py` are all documented in
`docs/NAME_INDEX.md`; they are not repeated here. Two facts belong in a pipeline
document, though. The index is written from the unzipped FASTA, so it can only be
produced during a build — a database whose FASTA is gone needs the backfill tool.
And an index is written even when a FASTA carries no gene names at all: an empty
object tells the server the database holds none, which is a different thing from
having no index, and lets it skip the database instead of scanning it. Across the
host that is 2,387 `.names.json` files totalling 1.36 GB, and 2,383
`.names.display.json` totalling 1.33 GB.

## Publishing

This is the part to be careful about.

`copy_to_production` (`src/utils.py:57-134`) copies
`../data/blast/<MOD>/<env>/databases` to
`/var/sequenceserver-data/blast/<MOD>/<env>/databases`. It does so by
`shutil.rmtree`ing the destination (`:123-124`) and then `shutil.copytree`ing
into it (`:128`). Operationally that means:

- Between the `rmtree` and the end of the `copytree`, that release serves
  nothing. All three containers mount the same `/var/sequenceserver-data/blast`
  read-write, so the gap is visible to users immediately — there is no staging
  directory and no atomic swap.
- If the copy fails partway, the release is left incomplete, and the previous
  contents are already gone. There is no rollback, because there is no copy of
  what was there.
- Databases the new build did not produce are deleted, whether or not they were
  working. A run with `-d` narrowing to one entry replaces the whole release
  directory with just that one database.

A safer shape, given the same filesystem: `copytree` into
`…/databases.incoming`, then rename the live directory aside and the new one into
place, then `rmtree` the old — two renames, during which the destination is never
empty. `rsync -a --delete` into the live directory has the same property and is a
one-line change. Neither is implemented.

The copy is **not optional**. It runs at `src/create_blast_db.py:1106-1208`
whenever `--check-parse-seqids` was not passed and something was built (with
nothing built it prints "No data to copy to production" and stops). It prints a
dry-run preview of every directory it is about to replace, then prints
`Proceeding with production copy...` (`:1173`) and does it. Despite what the
preview looks like, **it does not prompt**. Earlier revisions of `CLAUDE.md`
documented a `--no-copy-to-sequenceserver` flag in three places; it was never
implemented, and passing it fails with `Error: No such option`. To build without
publishing you must edit `copy_to_production` or point the pipeline at a scratch
`/var/sequenceserver-data`.

It also runs on partial success. `process_json_entries` returns `successful > 0`
(`:875`), `process_files` discards that return value, and `create_dbs` never
inspects it; a `(mod, environment)` pair is queued for the production copy if at
least one of its entries built (`:792`). So a run in which most entries fail
still publishes the partial set — and republishes `environment.json`, which is
the *input* config, describing databases that were never built. That mismatch
between what a deployment declares and what it serves is the ALLIANCE failure,
and nothing in the pipeline checks for it.

Config is the one thing that does not go straight to production.
`CONFIG_DEPLOY_ROOT` (`src/utils.py:151`) defaults to
`/var/sequenceserver-data/config-dev`, which the test and dev containers mount;
production mounts `/var/sequenceserver-data/config`. Before `5bd3075` both
mounted the same directory, so a config change took effect on production the
moment it was written, with no deploy and no review — which is how production
came to serve genome browser links for code that only existed on dev. Promotion
is now a deliberate step:

```bash
cp -a /var/sequenceserver-data/config-dev/. /var/sequenceserver-data/config/
```

Set `AGR_CONFIG_ROOT` to override, including back to the production directory.
The asymmetry is worth stating plainly: **a build publishes its databases to
production and its config to dev.**

`-s3` is separate and genuinely optional. `s3_sync` (`src/utils.py:830`) runs
`aws s3 sync ../data $S3 --exclude '*.tmp'` and then, unless `-s` was passed,
`sync_to_efs` runs `aws s3 sync $S3 $EFS`. Both read `$S3` and `$EFS` from a
`.env` in the current working directory — i.e. `src/.env`, since that is where
the script must be run from. `src/.env.example` lists the keys.

## Validation

`--validate` runs after the production copy, against `--validation-path`
(default `/var/sequenceserver-data/blast`), which means it validates what was
published rather than what is about to be. `DatabaseValidator`
(`src/validation.py:150`) discovers databases by globbing `*.nin` and `*.pin`,
then picks `blastp` only when the word "protein" appears in the database path,
and BLASTs eight conserved sequences (18S, 28S, COI, actin, GAPDH, U6, histone
H3, EF-1α) plus two MOD-specific ones at `-evalue 10 -word_size 7`. A database
passes if any query produces any hit.

The selector reads `blastp if ".pin" in db_path or "protein" in db_path.lower()`
(`src/validation.py:325`), and the first half of that test is dead: `:210` and
`:217` strip the extension off before the path reaches it, so `".pin"` can never
be in it. A protein database whose path does not say "protein" would be searched
with `blastn` and fail every query. None currently deployed is in that position —
all 828 `.pin` paths on the host contain "protein" — which is why the dead branch
has never cost anything.

Validation is advisory only: `create_dbs` catches every exception from it and logs
"Continuing despite validation failure" (`src/create_blast_db.py:1211-1272`).
It does not compare what is served against what the config declares, which is
the check that would have caught ALLIANCE.

## Docker

The image (`Dockerfile`) is `python:3.10` plus NCBI BLAST+ 2.13.0 unpacked into
`/blast`, with the project installed by a pinned uv:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /bin/uv
RUN uv sync --locked --no-dev
ENV PATH=/workflow/.venv/bin:${PATH}
```

`--locked` fails rather than re-resolving, so the image and `uv.lock` cannot
drift apart. `--no-dev`, despite the comment above it in the Dockerfile, does
nothing here: the test tooling — black, pillow, locust, playwright and the rest —
is declared as a PEP 621 extra (`[project.optional-dependencies] dev` in
`pyproject.toml`), and `uv sync --no-dev` suppresses dependency *groups*, of
which this project declares none. What keeps that tooling out of the image is
that `uv sync` installs no extras unless asked, so `uv sync --locked` on its own
would build the identical environment. Worth saying plainly, because the flag
looks like the guard and is not one.

The uv switch itself was `ddcdd7d`: the project
moved to uv in August 2025 but the Dockerfile kept driving poetry, which
by then had no `[tool.poetry]` section to read, so the image was resolving
dependencies by a different route than `uv.lock` described. `.dockerignore`
excludes `.venv/` for the same reason — copying a local virtualenv in would
shadow the one `uv sync` builds.

`make docker-build` tags `agr_blastdb_manager:<pyproject version>` and `:latest`;
`make docker-run` mounts `./data`, `./logs` and `./conf` and runs
`--config_yaml=/conf/global.yaml`. Note that `make docker-run` mounts data at
`/data` and `/logs` while the Dockerfile declares volumes at `/workflow/data` and
`/workflow/logs`, so that target does not do what it looks like it does.

## Tests

```bash
uv run pytest tests/ --ignore=tests/performance --ignore=tests/ui
```

At `92fdc2a`, in a clean `uv sync --locked --extra dev` tree, that is
**202 passed, 1 failed** in 9.4 seconds. Both exclusions are necessary and
neither is optional housekeeping:

- `tests/performance/test_performance.py` fails at *collection* — it does
  `from .fixtures import …`, and there is no `tests/performance/fixtures`
  (the fixtures are in `tests/fixtures/mock_data/`). A collection error aborts
  the whole run, so a plain `pytest tests/` reports nothing at all.
- `tests/ui/` drives Playwright and needs a browser
  (`uv run playwright install chromium`) and a reachable deployment.

The one real failure is `tests/integration/test_infrastructure.py::test_fixtures_import`,
which has the same broken import with a fallback that is equally broken.
`tests/cli/test_cli.py` collects nothing: it is a standalone click script that
shells out to `blastn`, not a test module.

What the tree actually contains:

| path | what it is |
|---|---|
| `tests/unit/` | 142 passing tests: `test_utils.py`, `test_create_blast_db.py`, `test_terminal.py`, `test_validation.py`, `test_name_index.py`, plus `test_utils_properties.py` (Hypothesis) |
| `tests/test_deduplicate_fasta.py` | 15 tests, and the best-documented file in the repo — read it to understand the de-duplication rules |
| `tests/test_index_entries.py` | 15 tests over the per-MOD defline grammars, checking chiefly that no pattern claims another MOD's text |
| `tests/integration/` | 30 passing, 1 failing; mostly mocked pipeline flows |
| `tests/performance/` | does not import, see above; `locustfile.py` for Locust load testing lives under it |
| `tests/ui/` | Playwright (was Selenium until `633d435`); needs `uv run playwright install chromium` |
| `tests/validate_deployed.py` | standalone script that checks deployed databases and their name indexes |
| `tests/test_blast_databases.py` | standalone BLAST smoke tests against deployed databases |
| `tests/fixtures/mock_data/` | sample configs and sequences for all MODs |
| `tests/blast_test_results/TEST_REPORT.md` | a generated report, and the file that recorded ALLIANCE's one database as a pass |

`tests/run_tests.py` and `run_tests.py` are two different wrappers around the
above; `pytest` directly is clearer. `TESTING_SUMMARY.md` and
`tests/QUICK_REFERENCE.md` both describe the suite in more flattering terms than
it currently earns — `QUICK_REFERENCE.md` still claims "SGD: main (1 database)".
