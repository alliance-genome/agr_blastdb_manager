# BLAST Database Test Report

**Generated:** 2025-10-24 01:20:55  
**BLAST Version:** blastn: 2.15.0+

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Databases** | 871 |
| **Passed** | 871 |
| **Failed** | 0 |
| **Success Rate** | 100.0% |

## MOD Breakdown

| MOD | Environments | Tested | Failed | Status |
|-----|-------------|--------|--------|--------|
| ALLIANCE | prod | 1 | 0 | ✓ PASS |
| RGD | rgdtest | 9 | 0 | ✓ PASS |
| SGD | R64-5-1f, R64-5-1m, sgdtest4, sgdtest5 | 861 | 0 | ✓ PASS |

---

## All Tests Passed ✓

All databases are readable and queryable.


---

## Expected Databases

Databases were found and tested for all MODs present in `../data/blast/`.


---

## How to Run

```bash

cd tests

python test_blast_databases.py

# or

uv run python test_blast_databases.py

```

*Test framework: AGR BLAST Database Manager*
