# Why ALLIANCE/prod serves one genome instead of nine

Written 2026-10-01, from evidence that lives only in a git-ignored log on one
host. The log is `src/blast_db_creation.log` (2.1 MB, ignored), so the relevant
lines are reproduced in full below rather than cited. If that host is rebuilt,
this file is the record.

## Summary

`/blast/ALLIANCE/prod/` is the Alliance-wide, cross-species BLAST deployment. It
declares nine reference genomes — one per member species, plus human and mouse —
and has served exactly one of them, zebrafish, since 2024.

The cause is not a design problem. One build ran, on 2024-10-09, for 65 seconds.
C. elegans failed on a stale MD5; seven more failed on a full disk; zebrafish
succeeded. **The run exited 0.** A year later the single database that had
succeeded was copied to production, and every check since has agreed that one
database is the correct number.

## Timeline

| When | What |
|---|---|
| 2024-03-21 | Adam Wright creates `conf/ALLIANCE/databases.ALLIANCE.prod.json` in `agr_blast_service_configuration` (PR #14, empty body) and adds `ALLIANCE` to the schema enum. Nine entries. This is the only statement of intent that exists. |
| 2024-10-09 03:17, 03:20 | Two aborted runs against that config. |
| 2024-10-09 03:42 | The run below. 1 of 9 built. Exit 0. |
| 2025-10-14 14:34 | `copy_to_production` copies the one database to `/var/sequenceserver-data/blast/ALLIANCE/prod/databases`, and the config to `config-dev`. |
| 2026-10-01 | Still 1 of 9. The config has never been content-edited since the day it was created. |

## The evidence

Extracted verbatim from `src/blast_db_creation.log`, the 2024-10-09 03:42 run:

```
2024-10-09 03:42:10,580 INFO Processing JSON file: ../../agr_blast_service_configuration/conf/ALLIANCE/databases.ALLIANCE.prod.json
2024-10-09 03:42:11,830 ERROR MD5sums do not match
2024-10-09 03:42:31,424 INFO Directory ../data/blast/ALLIANCE/prod/databases/Danio/rerio/ZFIN_GRCz11 created
2024-10-09 03:42:47,569 INFO Makeblastdb: done
2024-10-09 03:43:15,278 ERROR Error downloading .../GCF_015227675.2_mRatBN7.2_genomic.fna.gz: [Errno 28] No space left on device
2024-10-09 03:43:15,434 ERROR Error downloading .../GCF_000001635.27_GRCm39_genomic.fna.gz: [Errno 28] No space left on device
2024-10-09 03:43:15,572 ERROR Error downloading .../GCF_000001405.40_GRCh38.p14_genomic.fna.gz: [Errno 28] No space left on device
2024-10-09 03:43:15,702 ERROR Error downloading .../GCF_000001215.4_Release_6_plus_ISO1_MT_genomic.fna.gz: [Errno 28] No space left on device
2024-10-09 03:43:15,795 ERROR Error downloading .../GCF_000146045.2_R64_genomic.fna.gz: [Errno 28] No space left on device
2024-10-09 03:43:16,074 ERROR Error downloading .../XENLA_9.2_genome.fa.gz: [Errno 28] No space left on device
2024-10-09 03:43:16,357 ERROR Error downloading .../XENTR_9.1_genome.fa.gz: [Errno 28] No space left on device
2024-10-09 03:43:16,359 INFO create_dbs function completed in 65.78 seconds
```

Per entry, in config order:

| # | Genome | Outcome |
|---|---|---|
| 1 | *Caenorhabditis elegans* | `MD5sums do not match` — skipped |
| 2 | *Danio rerio* (GRCz11) | **built** |
| 3 | *Rattus norvegicus* | `ENOSPC` |
| 4 | *Mus musculus* | `ENOSPC` |
| 5 | *Homo sapiens* | `ENOSPC` |
| 6 | *Drosophila melanogaster* | `ENOSPC` |
| 7 | *Saccharomyces cerevisiae* | `ENOSPC` |
| 8 | *Xenopus laevis* | `ENOSPC` |
| 9 | *Xenopus tropicalis* | `ENOSPC` |

The disk filled while downloading entry 3. Everything after it failed in under
two seconds each, which is why a nine-genome build finished in 65 seconds.

## Why a bad night became two years

Four independent mechanisms had to agree for this to persist. Each is worth
fixing on its own.

**1. Partial failure is not failure.** `process_json_entries` returns
`successful > 0` (`src/create_blast_db.py:710`), `process_files` discards that
return value (`:331-335`), and `create_dbs` never inspects it. Eight of nine
entries died and the process exited 0. Nothing alerted.

**2. The build input is republished as the deployment's truth.**
`copy_config_file` (`src/utils.py:38-54`) writes the *input* config out as
`environment.json` whenever at least one entry succeeded. That is precisely how
the deployment came to **declare nine genomes while serving one** — the config
describing all nine was published alongside the single database that existed.

**3. Nothing checks free space before starting.** The run had no idea it was
about to need several GB it did not have, and no `ENOSPC` handler that stops
rather than continuing to the next entry.

**4. The tests assert the broken state is correct.** Two of them:

- `tests/blast_test_results/TEST_REPORT.md` in this repo records
  `| ALLIANCE | prod | 1 | 0 | ✓ PASS |` — one database, zero failures, green.
- `agr_sequenceserver/test/e2e/cross_mod.spec.js` sets `databaseFloor: 1` for
  ALLIANCE, so its cross-MOD suite passes on one database too.

Both were written after the failure, against the failed state, and so encoded it
as the expectation. This is the mechanism most worth remembering: the other
three let the failure happen, but this one is why nobody found it.

## Also wrong in the config, never noticed

Because the build never got past entry 3, these have never been exercised:

- `mus musculus` has `taxon_id: "NCBITaxon:"` — empty. `create_blast_db.py:146-155`
  interpolates that into `-taxid` and `makeblastdb` exits 1, so **mouse cannot
  build at all** even with disk available.
- `homo sapiens` has `taxon_id: "NCBITaxon:9506"`, which is *Ateles* (spider
  monkey), not 9606. This does not fail the build; it stamps the wrong organism
  into the database.
- Six of nine genera are lowercase, and both *Xenopus* entries are misspelled
  differently — `xenupus` and `xenupos`. Genus and species are interpolated
  verbatim into the on-disk path (`:92-99`), which becomes the database tree's
  grouping, so a complete build would render two misspelled *Xenopus* genera.
- Eight of nine entries have no `genome_browser` block, so their hits would get
  no browser link. The ninth points at WormBase's JBrowse 2 at WS292.

## Current state of the checksums

All nine URIs return HTTP 200 and were re-verified on 2026-09-30 by streaming
each object through `md5sum`. **Eight of nine still match** what the config
recorded in 2024. Only C. elegans is stale:

```
configured  4af7b125bde3c80617ad846cc2ff266e
actual      5c0d5cae0c4cd14a05fcf9e3092c4597
```

That entry also still claims `version: WS292`, so the object at that S3 key has
been replaced since Adam wrote the config, and the entry may want a fresh URI
rather than only a fresh checksum.

## A second instance, and the same mechanism

FlyBase's FB2026_03 lost its *D. melanogaster* Transcripts database to exactly
this pattern on 2026-09-15: `makeblastdb` rejected the FASTA, the entry failed,
the run exited 0, and the remaining four databases shipped. Curators reported it
as "the option to search annotated transcripts has disappeared". Seven previous
releases had the database.

Different proximate cause -- duplicate sequence ids in the export rather than a
full disk -- but the same three mechanisms let it reach users and stay there:
partial failure is not failure, the config is republished regardless, and
nothing afterwards checks that what is served matches what is declared.

`deduplicate_fasta` in `src/create_blast_db.py` now handles the duplicate ids.
It does not address any of the three mechanisms above.

## What to do about it

The repair plan lives in the SequenceServer repo at
`docs/ALLIANCE_WIDE_PLAN.md`. The short version: make the deploy reversible
first (there is no opt-out flag — see the warning in `CLAUDE.md`), then fix the
config, then build. The build itself is cheap: the 2024 log measures 35 seconds
end to end for the 442 MB zebrafish genome, so all nine is about an hour of
machine time.
