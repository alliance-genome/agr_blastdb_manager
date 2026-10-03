# The gene-name index, from the writer's side

Every BLAST database this pipeline builds gets two JSON files written beside it,
and SequenceServer's `?name=` deep links and its "Find a gene" box are answered
out of those files and nothing else. This document covers how the names get into
them: the defline grammars, the FlyBase synonym join, the display-spelling
companion file, and `bin/backfill_name_indexes.py`. The reader side — the two
HTTP endpoints, the prefix search, the result ordering — is
`agr_sequenceserver/docs/GENE_SEARCH.md`, and the build step this sits inside is
`docs/PIPELINE.md`.

Line numbers into `src/utils.py` and `bin/backfill_name_indexes.py` refer to
`c4daac6` ("Strip the '>' before deriving names, so both index paths agree"),
one commit past `92fdc2a` (#72); against `92fdc2a` everything inside and after
`index_entries` sits eight lines higher. Cites into `routes.rb` refer to
`agr_sequenceserver` at `d36800bb` ("Stop trusting request input that becomes a
filesystem path"), which moved most of that file, so they do not land on `main`
at `73e4a38a`. Figures were measured on the live host against
`/var/sequenceserver-data/blast`, which is the volume all three containers mount.

## Why there is an index at all

`?name=YFL039C` has to turn a gene name into one FASTA record. With nothing to
look it up in, SequenceServer streams deflines out of `blastdbcmd` for one
database after another until something matches, and a *miss* has to read all of
them. On SGD's fungal release that is 104 coding databases
(`SGD/R64-5-1f/databases/*/*Coding*`) holding 914,646 records between them, and
1,831,337 records across all 312 databases if the scan is not confined to the
coding sets. The original commit (`a72ada5`) measured a hit at 5.3s and a miss at
11s on an unauthenticated endpoint, and the code comments put the scan at "~100
coding databases and ~1.3M entries" — the 104 reproduces exactly; the 1.3M does
not, and sits between the coding-only and the whole-release record counts
measured today. On FlyBase the same scan took 10-13 seconds and then found
nothing, for a reason that had nothing to do with speed and is the subject of two
sections below.

Building the index during the build is nearly free, because the FASTA is on disk
and its deflines are being read anyway. `build_name_index` (`src/utils.py:738`)
is called from `run_makeblastdb` at `src/create_blast_db.py:364`, after
`makeblastdb` has succeeded and before the unzipped FASTA is deleted a few lines
later. That ordering is the whole constraint on this subsystem: the index can
only be produced while the FASTA still exists, which is why a tool that can
recover names from a finished database had to exist as well.

The measured win was a hit going 5.3s to 0.5s and a miss 11s to 0.5s. The scan
path still exists on the server (`routes.rb:837`) behind a 15-second budget
(`NAME_LOOKUP_BUDGET_SECONDS`, `routes.rb:612`), and is dead code in practice:
all 2,387 database stems on the host have an index.

## The two files

`<db>.names.json` (`NAME_INDEX_SUFFIX`, `src/utils.py:491`) maps a **lower-cased**
name to the accession to retrieve. One key per thing anyone might type —
accession, locus tag, gene symbol, and on FlyBase every synonym and full name too.
Written with `sort_keys=True` and `separators=(",", ":")`, so it is deterministic
for a given input and carries no whitespace. Real bytes from the head of
`FB/FB2026_03/.../dmel-transcriptdb.names.json`:

```json
{"#19/1":"FBtr0078143","&agr-ps3":"FBtr0087369","&ggr;-tubulin":"FBtr0081228",
 "'48' transcript":"FBtr0085065","(6-4) photolyase":"FBtr0081404", …}
```

`<db>.names.display.json` (`NAME_DISPLAY_SUFFIX`, `src/utils.py:495`) maps the
same lower-cased key to the spelling the source actually uses, and holds **only**
the keys where those differ:

```json
{"&agr-ps3":"&agr-PS3","(a+t)-stretch binding protein":"(A+T)-stretch binding protein",
 "(acp)76a":"(Acp)76A","(de)-cadherin":"(DE)-cadherin", …}
```

They are two files rather than one file with richer values, and that is a
deliberate trade stated at `src/utils.py:640-643` and again on the reader side at
`routes.rb:624-630`. The index is the hot path: a gene search reads the raw text
of *every* index in the deployment looking for the needle, so anything added to
an index is paid on every keystroke. The companion file is read only for the
handful of databases a search actually matches, and only once one of them has a
hit to label (`routes.rb:769`). The second reason is compatibility: leaving the
index's shape untouched means a deployment running older code goes on resolving
`?name=` against it unchanged, which is not hypothetical — production is
`agr-blast:fda1db1f`, eight PRs behind (#23; `main` is #31), and mounts this
same volume.

What is on the host:

| | index files | names | spelling files | spellings |
|---|---|---|---|---|
| FB | 1,560 | 28,534,406 | 1,560 | 28,326,496 |
| SGD | 495 | 3,567,859 | 493 | 3,555,736 |
| WB | 306 | 4,799,368 | 304 | 4,734,524 |
| ZFIN | 16 | 3,679,129 | 16 | 3,679,129 |
| RGD | 9 | 9,151 | 9 | 9,151 |
| ALLIANCE | 1 | 26 | 1 | 26 |
| total | 2,387 — 1.36 GB | 40,589,939 | 2,383 — 1.33 GB | 40,305,062 |

The WB row counts the whole volume, which is why it is 306 files for two served
releases: 182 of them sit under `WB/.retired-WS295`, `.retired-WS296` and
`.retired-WS297`, hidden from the server but still indexed, and carry 2,833,236
of those names. `WS298` and `dev` alone are 124 index files and 1,966,132 names.

The spelling files are nearly as large as the indexes (1.33 GB against 1.36 GB)
because most accessions are mixed-case, so almost every accession key earns a
display entry: `fbtr0070490` → `FBtr0070490`. That is not waste — the reader
labels an accession hit with it too — but it does mean the "only the difference"
economy saves much less than the name says. The separation still earns its keep
on *when* each file is read, not on size.

Four databases have an index and no spelling file:
`SGD/R64-5-1m/.../BY4741_Toronto_2012db` and `BY4742_Toronto_2012db`,
`WB/WS298/.../c_latensdb`, and `WB/dev/.../c_latens.PRJNA248912.WS291.genomic.db`.
All four hold nothing but already-lower-case keys — `2-micron` and
`chr01`…`chr17` on the Toronto strains, 1,858 `scaffold_<n>` names on the
C. latens assemblies — so `write_display_names` (`src/utils.py:713`) deleted
rather than wrote. Deleting rather than skipping matters on a rebuild: a stale
file left behind would go on labelling names the new index no longer holds.

No index on the host is empty. `index_entries` always does
`put(accession, accession)` first (`src/utils.py:668`), so a database can only
produce `{}` if every accession is blank — which no real FASTA and no
`blastdbcmd` output produces. The smallest index on disk is 25 bytes, the
2-micron plasmid with its single accession. That makes the empty-index
distinction the server leans on at `routes.rb:614-617` ("an empty object means the
database holds no names, which is different from having no index at all")
correct but unexercised.

## Four defline grammars, because there are four

Until `542da50` the index understood exactly one grammar:

```python
GENE_NAME_TAG_RE = re.compile(r"\[(locus_tag|gene)=([^\]]+)\]")
```

NCBI's bracket tags (`src/utils.py:463`). That is why `?name=ACT1` worked on SGD
and silently failed everywhere else: SGD's fungal set is NCBI-derived and uses
them, and nobody else does. A FlyBase index backfilled before this change held
30,837 keys, every one an `FBpp` accession and not a single symbol.

`MOD_SYMBOL_RES` (`src/utils.py:484`) adds the other three. They are ported from
the patterns `agr_sequenceserver`'s `lib/sequenceserver/links.rb` already used to
label a gene linkout, so that the index and the link cannot disagree about what a
symbol is; until then Ruby knew all four and Python knew one.

All four patterns are tried against every defline, because the indexer does not
know which MOD produced the file it is reading. That is only safe because each is
anchored on something specific to the MOD that wrote it. Deflines below are real,
pulled back out of the deployed databases with `blastdbcmd -outfmt '%a %t'`.

**WormBase** — `WB/WS298/.../C_elegans_Protein_Sequences`, pattern
`\blocus=([^\s;]+)`:

```
F11C3.3 wormpep=CE09349 gene=WBGene00006789 locus=unc-54 status=Confirmed uniprot=P02566 …
```

yields `f11c3.3` (the accession) and `unc-54`. Note what is *not* yielded:
`gene=` here holds an identifier, not a symbol, and indexing it would fill the
index with WBGene ids nobody searches for. It is skipped because
`GENE_NAME_TAG_RE` requires the bracket form and WormBase writes the bare one.
Confirmed on disk: `c_elegansdb.names.json` has `unc-54` → `F11C3.3` and
`rga-9` → `2RSSE.1a`, and no key `wbgene00006789`.

**FlyBase** — `FB/FB2026_03/.../D_melanogaster_Proteins_6_69`, pattern
`\bname=([^\s;]+?)-[A-Z]{2}\b`:

```
FBpp0070468 type=polypeptide; loc=X:complement(join(…)); ID=FBpp0070468;
name=w-PA; parent=FBgn0003996,FBtr0070490; dbxref=…; release=r6.69; species=Dmel;
```

yields `fbpp0070468` and `w`. `name=` names the *isoform*; the symbol is the part
before the two-letter suffix, and a `name=` without that suffix is deliberately
not indexed as a symbol — it is not an isoform. The transcript set spells the
same gene `name=w-RA`.

**ZFIN** — pattern `\A([a-z][^|\s]*)\|`, anchored on a lower-case first letter so
that clone names sitting in the same position (`CH211-107M8.1-002|…`) are left
alone. This pattern is the one that does not pay off, for two reasons given in
"What this does not cover" below.

**SGD** has two shapes and needs both. Its own FASTAs carry no bracket tags —
`SGD/R64-5-1m/.../ORF_coding`:

```
YFL039C ACT1 SGDID:S000001855, Chr VI from 54377-53260,54696-54687, Genome Release 64-3-1, …
```

so `sgd_symbol` (`src/utils.py:691`) takes the token immediately before the
`SGDID:` marker, which yields `act1` here and the systematic name again for a
gene with no symbol (`>YAL069W YAL069W SGDID:…`). Keying on the marker rather
than on token position is what stops it firing on other MODs' prose. Its fungal
set is NCBI-derived and does use the bracket tags —
`SGD/R64-5-1f/databases/Candida/C_albicans_Coding_Sequences`:

```
NC_032089.1_cds_XP_019330727.1_1268 [gene=ACT1] [locus_tag=CAALFM_C113700WA]
[db_xref=CGD:CAL0000191211,GeneID:3636195] [protein=actin] …
```

yielding the accession, `act1` and `caalfm_c113700wa`. The accession is an opaque
RefSeq CDS id, which is the case `GENE_NAME_TAG_RE` was written for in the first
place: without the tags there would be nothing searchable in that file at all.

### The ZFIN pattern could not fire from the build path

Up to `92fdc2a` the two writers disagreed about the same database, which is the
one thing sharing `index_entries` was meant to make impossible.
`build_name_index`'s inner `deflines()` generator yielded `parts[0], line` where
`line` was the raw FASTA header *including the leading `>`*. `MOD_SYMBOL_RES[2]`
is anchored with `\A` on `[a-z]` precisely because a ZFIN defline leads with its
symbol, so against `>itsn1|OTTDARP00000003617 …` it saw the `>` and never
matched. The backfill reads deflines back out of a finished database through
`blastdbcmd` and so never has a `>`, and derived ZFIN's symbols correctly.

The consequence was latent rather than live. Every deployed ZFIN index was
produced by the backfill and is correct; it is a ZFIN *rebuild* that would have
written an accession-only index over a correct one, with nothing in its output
to say the symbols had gone.

`c4daac6` normalises the `>` away inside `index_entries` itself
(`src/utils.py:667`) — the one point both paths share, rather than in the caller
that got it wrong, so a future caller handing over a raw FASTA line cannot
reintroduce it — and `deflines()` now yields `parts[0], line[1:]`
(`src/utils.py:788`). Re-measured against the current tree, the two shapes give
the same index:

```
build-path text  '>itsn1|OTT… BUSM1-173A8.1-002 pep\n'  ->  {'itsn1|ottdarp00000003617': …, 'itsn1': …}
backfill text    'itsn1|OTT… BUSM1-173A8.1-002 pep\n'   ->  {'itsn1|ottdarp00000003617': …, 'itsn1': …}
```

Two tests came with the fix and state both halves:
`test_build_and_backfill_derive_the_same_names`, that the two paths agree on a
ZFIN database, and `test_the_leading_angle_bracket_does_not_change_the_index`,
that a leading `>` changes no MOD's index.

The same anchoring also has a false positive the test suite lets through.
`test_a_genome_assembly_defline_yields_no_symbol` asserts only that
`aa605703.1` is absent from the index built from
`gb|AA605703.1|AA605703 fa17f11.s1 Ekker early gastrulation zebrafish embryo`.
What it actually produces is:

```
{'bl_ord_id:0': 'BL_ORD_ID:0', 'gb': 'BL_ORD_ID:0'}
```

The GenBank database tag `gb` becomes a gene name. That key exists only in the
unit test's shape today: no deployed ZFIN index holds it, because all 3,679,129
keys across the 16 ZFIN indexes are `bl_ord_id:<n>` — the backfill's `%a` put
`BL_ORD_ID:0` at the head of the text and the `\A` anchor could not reach the
`gb|` behind it. `gb` *is* a key in 16 indexes on the host, but as a real
FlyBase symbol: `FBgn0039487`, `current_fullname` "genderblind". Typing it
returns genuine hits, not one useless candidate.

`c4daac6` moves this defect from unreachable to reachable. With the `>`
stripped, a ZFIN rebuild from FASTA puts `gb|AA605703.1|…` at the head of the
text where the anchor does match, so the bogus key would be written. It is the
failure mode the anchoring was supposed to prevent, and the test that should
catch it asserts only the absence of `aa605703.1`.

## The FlyBase alias join

A curator searched the box for `white` and was told no such gene existed. As far
as the databases are concerned that was correct: FlyBase deflines carry
`name=w-RA` and nothing more, and the string "white" appears **zero** times in
all 1,560 FlyBase databases. Checked on the melanogaster transcript set —
`blastdbcmd -entry all -outfmt '%a %t' | grep -ic white` over all 35,738 records
returns 0. Only the symbol was ever indexable, and a curator types the name far
more often than the symbol.

FlyBase publish the other half themselves. `GENE_ALIAS_SOURCES`
(`src/utils.py:509`) points at
`releases/current/precomputed_files/synonyms/fb_synonym_{release}.tsv.gz`, which
today is 11,943,023 bytes gzipped and 1,020,534 lines. `flybase_aliases`
(`src/utils.py:522`) reads columns 2 through 5 — `current_symbol`,
`current_fullname`, `fullname_synonym(s)`, `symbol_synonym(s)` — splitting every
one of them on `|`, which only matters for the last two: the comment at
`src/utils.py:557` notes that the symbol and fullname columns carry no pipes. It
yields 1,020,528 gene ids carrying 2,108,729 names between them. For the gene in
question:

```
FBgn0003996  Dmel  w  white  White|enhancer of garnet|mini-white|modifier of garnet|white[+]|white[+]
                                BACN33B1.1|CG2759|DMWHITE|DmWhite|EG:BACN33B1.1|W|c23|e(g)|m(g)|mini-white|mw|…
```

The join is `PARENT_GENE_RE` (`src/utils.py:500`), `\bparent=([^;\s,]+)`, against
the `parent=FBgn0003996` the deflines already carry. The pattern stops at the
first comma, which is what makes the protein set's
`parent=FBgn0003996,FBtr0070490` resolve to the gene rather than to the
gene-plus-transcript pair.

Two consequences of joining by gene id rather than by name. First, the whole
table is safe to hand to every database: a name can only ever reach its own
gene's records, which is what
`test_a_name_cannot_reach_another_genes_records` pins. Second, rows for other
species can be kept without harm — the table carries 622 distinct organism
abbreviations and only 758,076 of its 1,020,528 rows are `Dmel` — and a FlyBase
deployment does carry more than *D. melanogaster*, 200 databases of it in
`FB2026_03`.

The effect, verified against the deployed index for the transcript set: `white`,
`w`, `mini-white` and `cg2759` all resolve to `FBtr0070490`, and the index holds
131,148 names for 35,738 records. The protein set holds 109,574 for its own
records. Before the join, a backfilled FlyBase index held 30,837 keys and no
symbols at all.

### Why the release is derived rather than passed in

`gene_aliases` (`src/utils.py:564`) takes the MOD code and the *environment* —
which in this pipeline is the release name, `FB2026_03`, not a deployment tier,
whatever `src/create_blast_db.py:69`'s docstring says; the config files are
literally `conf/FB/databases.FB.FB2026_03.json`. The regex at
`src/utils.py:588`, `([A-Za-z]+)(\d{4}_\d+)`, turns `FB2026_03` into
`fb_2026_03`, hence `fb_synonym_fb_2026_03.tsv.gz`.

It could have taken a path to a downloaded table instead, and that is exactly the
failure mode being avoided: `build_name_index` is what the pipeline calls, so a
rebuild that did not pass aliases would silently drop every full gene name and
return FlyBase to symbols only — the state that was reported as broken. Deriving
the filename means a rebuild picks the names up on its own.
`test_build_name_index_carries_aliases_through` exists for precisely that regression.

The table is fetched once per run and cached in `_GENE_ALIAS_CACHE`
(`src/utils.py:519`) keyed by `(mod, environment)`, which in this pipeline means
per release: it is a million rows and a FlyBase release build writes 200 indexes
— 1,560 across the eight releases on the host — so parsing it per database would
dominate the build. The code comment at `src/utils.py:517` quotes the 1,560, and
is wrong in the same way. The download is cached on disk at `Path("../data") / <filename>`
(`src/utils.py:598`), relative because the pipeline is run from `src/` and every
other path it writes is `../data/blast/...` and `../data/config/...` in the same
style.

Nothing here may fail a build. A MOD with no entry in `GENE_ALIAS_SOURCES`
returns `{}` before the regex is even reached; an environment name the regex
cannot parse warns and returns `{}`; a failed download, a bad gzip stream or a
CSV error is caught at `src/utils.py:614` and warns. All of them leave the build
with symbols only, which is worse than it could be and far better than a failed
release.

**One gap, verified.** The URL is pinned to `releases/current/`, so only recent
releases are fetchable. Measured today:

```
fb_2026_03 -> 200     fb_2026_01 -> 200     fb_2024_02 -> 404
```

Rebuilding `FB2024_02` therefore warns and produces a symbols-only index, with
nothing in the result to say the names are missing. The pipeline keeps eight
FlyBase releases on the host (`FB2024_02` through `FB2026_03`), so this is
reachable, not theoretical.

## Display spellings

Keys are lower-cased so that `?name=ACT1` and `?name=act1` reach the same record
without normalising anything at read time. The reader then printed the key, and
the cost showed up the moment the search box listed results: FlyBase's `Dll` came
back as `dll`, `CG2759` as `cg2759`, and every one of SGD's all-caps symbols in
lower case — someone typing `ACT1` was answered with `act1`.

`index_entries` takes an optional third argument, a dict it fills with the
spelling each name was written with (`src/utils.py:647-655`). Passing nothing
leaves the index byte-identical and costs nothing, which
`test_display_is_optional_and_changes_nothing` pins.

The rule that keeps the two files consistent is that the display entry is written
inside `put`, under the same first-name-wins guard as the index itself. A symbol
can occur in many records and in many synonym columns; the index maps it to the
first accession seen, so the spelling recorded has to be the one that won, not
whichever came last. FlyBase makes that concrete: `FBgn0003996`'s alias list
reaches `index_entries` as `['w', 'white', 'White', 'enhancer of garnet', …]`, so
`white` is inserted from the `current_fullname` column and the `White` synonym
that follows is dropped. There is consequently no display entry for `white` at
all, and the reader falls back to the key (`routes.rb:775`), which is the same
spelling. Confirmed on the deployed transcript index: `white` has no entry,
`cg2759` → `CG2759`, `dll` → `Dll`. The box shows the current name, not a
title-cased synonym.

The entire writer path is reproducible against what is on disk. Re-deriving the
FlyBase protein index from `blastdbcmd` output plus
`fb_synonym_fb_2026_03.tsv.gz` gives 109,574 index keys and 97,582 spellings,
and both dicts compare equal to the deployed files.

## The backfill tool

`build_name_index` only ever ran for databases built after it existed, which at
`542da50` meant SGD and nobody else: 1,892 databases across FB, WB, RGD, ZFIN and
ALLIANCE had no index. Rebuilding them to get one would have meant re-downloading
roughly 76 GB of FASTA — for scale, the data volume is 82 GB today, 64 GB of it
FlyBase — and would have risked every other failure mode a rebuild carries.

It is also unnecessary, because the deflines are *already inside the BLAST
databases*. `bin/backfill_name_indexes.py` streams them back out with
`blastdbcmd -entry all -outfmt '%a %t'` (`deflines`, line 86) and derives names
through the same `index_entries` the build path uses, so a backfilled index and a
freshly built one cannot disagree. `--mod RGD --dry-run --force` reproduces the
deployed index exactly: 9 databases, 9,151 names, against 9,151 on disk.

`databases()` (line 63) enumerates database stems by globbing `*.nin`, `*.pin`,
`*.nal` and `*.pal` and de-duplicating on the stem, so a large database split
into numbered volumes (`<name>.00`, `<name>.01`, … alongside an `.nal` alias) is
visited once. `--mod` filters on the first path segment and is case-sensitive:
`--mod FB`, not `--mod fb`.

Two flags matter for a live deployment.

`--aliases <fb_synonym_*.tsv.gz>` loads FlyBase's table through the same
`flybase_aliases` the build path uses and joins it in, which is how the 1,560
FlyBase indexes got their full gene names before the build path could produce
them. It needs `--force` as well, since those databases already had an index.

`--display-only` writes *only* the companion spelling file and leaves
`.names.json` untouched. This is the safe way to add capitalisation to a running
deployment, and it inverts the usual skip: a database with no index is skipped
rather than given one (line 161-166), because a database with no index has no
names to label and this mode must not create any.

### Runbook

Measured from file mtimes on `/var/sequenceserver-data/blast`, plus the figures
the three commits report:

| run | command | result |
|---|---|---|
| initial backfill, `a72ada5`..`542da50` | `bin/backfill_name_indexes.py /var/sequenceserver-data/blast` | 2,387 indexes, 39.4M names, 1.36 GB, about five minutes (827 of those files survive untouched, written 23:10-23:12 on 1 Oct) |
| FlyBase names, `481bb90` | `… --mod FB --aliases fb_synonym_fb_2026_03.tsv.gz --force` | 1,560 indexes, 28,534,406 names, 0 failed; 16:21-16:26 on 2 Oct |
| spellings, `92fdc2a` | `… --aliases fb_synonym_fb_2026_03.tsv.gz --display-only` | 2,383 spelling files, 40.3M spellings, no index rewritten; 17:27-17:33 on 2 Oct |

Always dry-run first — but a dry run that is meant to rewrite indexes needs
`--force` as well, or `bin/backfill_name_indexes.py:167` skips every database
that already has one *before* it is counted. On this host
`--mod RGD --dry-run` reports "would write 0 index(es), 0 names; 9 skipped" and
prints nothing per database; adding `--force` prints the nine lines and the
9,151 total. `--display-only` is unaffected, since its skip is the inverse one.

All three reported figures reproduce. The host holds 40,589,939 names across the
2,387 index files and 40,305,062 spellings across the 2,383 spelling files, so
the spelling run's 40.3M is simply the current number. The FlyBase count is
exact (28,534,406). The initial run's 39.4M predates the FlyBase rewrite in
`481bb90`, which replaced every FB index with one carrying full gene names, and
the gap is in that direction. The spellings do not exceed the names they came
from: they are 284,877 fewer, which is the keys whose spelling already matched
the lower-cased key and so earned no display entry.

Fetch the alias table the same way the build path does, so the two agree:

```
curl -O https://s3ftp.flybase.org/releases/current/precomputed_files/synonyms/fb_synonym_fb_2026_03.tsv.gz
```

### Two rough edges in the tool

Index writes go through a temporary file and `Path.replace` (line 202-206), so a
reader never sees a half-written index. The spelling file does not:
`write_display_names` opens the final path with `"w"` (`src/utils.py:726`), and
the backfill calls it directly. On a live volume a concurrent gene search can in
principle read a truncated spelling file. The consequence is bounded — the reader
catches `JSON::ParserError`, logs, and falls back to the keys
(`routes.rb:806-815`) — but the asymmetry is unintentional.

A `blastdbcmd` that cannot read a database is indistinguishable from a database
with no names. `deflines()` sends stderr to `DEVNULL` and discards the return
code, so the generator simply yields nothing; `index_entries` then returns `{}`
and the loop counts it under "had no names to index" (line 179-185) and the
script exits 0. Demonstrated by pointing `deflines()` at a path with no database
at all: it returns `[]` and raises nothing.

The empty-index branch there is also the direct opposite of the build path's
reasoning. `build_name_index` writes an empty index deliberately, so the server
can skip the database instead of scanning it; the backfill refuses to write one,
on the grounds that the server would treat it as authoritative. Both readings of
the server are right — `if index` at `routes.rb:652` is true for `{}` in Ruby —
they just disagree about whether that is desirable. Nothing turns on it today,
because `index_entries` always indexes the accession and so never returns `{}`
from real input, and no index on the host is empty.

## What this does not cover

**ZFIN and RGD have no gene symbols to index.** This is not a missing grammar; it
is the deflines. All 16 ZFIN indexes — `prod` and `zfintest` together — hold
3,679,129 keys and every single one is of the form `bl_ord_id:<n>`, because those
databases were built without `-parse_seqids` and `blastdbcmd` has no accession to
give back:

```
BL_ORD_ID:0 gb|AW422923.1|AW422923 fi49h02.y1 Sugano Kawakami zebrafish DRA Danio rerio cDNA clone IMAGE:2641011 5', mRNA sequence
BL_ORD_ID:0 tpe|ENSDART00000189431.1|gene_biotype:TR_D_gene|ENSDARG00000116509.1 transcript_biotype:TR_D_gene  cdna chromosome:GRCz11:2:36087769:36087779:1
```

Those keys resolve to nothing a lookup can retrieve, and `d36800bb` on
`agr_sequenceserver` now skips any candidate whose accession starts with
`BL_ORD_ID:` (`BL_ORD_ID_PREFIX`, `routes.rb:677`), so they no longer reach the
search box at all rather than offering rows that fail when clicked.

RGD's nine indexes hold 9,151 keys, all GenBank or RefSeq sequence accessions
(`nc_086019.1`, `cm038647.1`, `jakeku010000023.1`) taken from deflines that are
chromosome descriptions. No pattern can extract what is not in the file. Fixing
this needs the deflines standardised upstream, or names looked up from something
that knows them; it does not need more regular expressions here. Note that the
ZFIN databases would also need rebuilding with `-parse_seqids` before any symbol
could be attached to a retrievable accession.

**Roughly a quarter of the FlyBase keys cannot be typed.** The reader validates
against `/\A[a-zA-Z0-9_\-.]+\z/` before touching a database
(`routes.rb:636`), and the alias table is full of names with spaces, brackets and
parentheses. On the FlyBase protein index, 26,230 of 109,574 keys (23.9%) are
unreachable through that validator — `white rabbit`, `white[+]`,
`(A+T)-stretch binding protein`. They are reachable only as a prefix of their
first word, where that word is itself a key. Whether to normalise them at write
time, loosen the validator, or leave them is undecided.

**FlyBase's SGML entities are passed through as published.** The index holds
`14-3-3&epsilon`, `&ggr;-tubulin`, `plc&aggr;` and the rest. That is 15 of the
transcript set's 131,148 keys, two of which lead with `&` and so cannot be
prefix-matched at all. `src/utils.py:538-541` puts the leading-`&` count at
three; what is in `FB2026_03` is two, `&agr-ps3` and `&ggr;-tubulin`. Either way
the quantity is negligible and decoding them has not been attempted.

## Tests

`tests/unit/test_name_index.py` (30 tests, two of them added by `c4daac6`) and
`tests/test_index_entries.py` (15 tests) both pass — 45 in 0.2s on this host;
`tests/unit/test_utils_properties.py` adds Hypothesis properties over
`index_entries`, `sgd_symbol` and
`build_name_index`, including that the on-disk index is exactly `index_entries`
over the file's deflines.

The useful half of `test_index_entries.py` is not that each pattern matches its
own MOD, which is easy, but that none of them claims another MOD's text — see the
`gb` false positive above for the case it does not quite catch.
`test_name_index.py` is where the alias join and the display spellings are
pinned, each test named after the report behind it. One wart:
`test_gene_aliases_derives_the_published_filename` does
`monkeypatch.chdir(tmp_path)` then `Path("../data").mkdir(...)`, which writes
outside its own tmp directory and leaves
`/tmp/pytest-of-*/pytest-*/data/fb_synonym_fb_2026_03.tsv.gz` behind. Harmless,
but it is the reason stray copies of that file turn up under `/tmp`.
