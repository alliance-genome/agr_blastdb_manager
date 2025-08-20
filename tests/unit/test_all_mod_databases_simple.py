#!/usr/bin/env python3
"""
Simple BLAST Database Testing Script - Progress Focused

Quick version with minimal output and clear progress tracking.
"""

import subprocess
import os
import pathlib
import time
from typing import Dict, List, Tuple

# MOD-specific real gene sequences
MOD_SEQUENCES = {
    'FB': '../../tests/fixtures/fb_real_genes.fasta',      # white, rosy, eve, actin
    'SGD': '../../tests/fixtures/sgd_real_genes.fasta',    # GAL1, ACT1, URA3, HIS3
    'WB': '../../tests/fixtures/wb_real_genes.fasta',      # unc-22, dpy-10, act-1, lin-15
    'ZFIN': '../../tests/fixtures/zfin_real_genes.fasta',  # pax2a, shha, actb1, tbx16
    'RGD': '../../tests/fixtures/rgd_real_genes.fasta',    # albumin, insulin, actb, gapdh
    'XB': '../../tests/fixtures/xb_real_genes.fasta'       # sox2, bmp4, actb, nodal
}

def test_database_quick(query_file: str, db_path: str) -> bool:
    """Quick BLAST test with minimal output"""
    try:
        result = subprocess.run([
            'blastn', '-query', query_file, '-db', db_path,
            '-outfmt', '6', '-evalue', '1e-1', '-max_target_seqs', '1'
        ], capture_output=True, text=True, timeout=15)
        
        return bool(result.stdout.strip())
    except:
        return False

def discover_databases_by_mod(base_path: str = "/var/sequenceserver-data/blast") -> Dict[str, List[str]]:
    """Discover databases with minimal metadata"""
    databases = {}
    
    for mod in ['FB', 'SGD', 'WB', 'ZFIN', 'RGD', 'XB']:
        mod_path = pathlib.Path(base_path) / mod
        databases[mod] = []
        
        if mod_path.exists():
            nin_files = list(mod_path.rglob("*.nin"))
            databases[mod] = [str(nin_file).replace('.nin', '') for nin_file in nin_files]
    
    return databases

def test_mod_quick(mod: str, databases: List[str], query_file: str):
    """Test a single MOD with progress updates"""
    print(f"\n=== {mod} ({len(databases)} databases) ===")
    
    if not os.path.exists(query_file):
        print(f"❌ Query file missing: {query_file}")
        return 0, 0
    
    hits = 0
    total = len(databases)
    start_time = time.time()
    
    # Progress updates every 25 databases or 10%
    update_interval = min(25, max(1, total // 10))
    
    for i, db_path in enumerate(databases):
        if test_database_quick(query_file, db_path):
            hits += 1
        
        # Show progress
        if (i + 1) % update_interval == 0 or i == total - 1:
            elapsed = time.time() - start_time
            progress = ((i + 1) / total) * 100
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total - i - 1) / rate if rate > 0 else 0
            
            print(f"  Progress: {i+1:3d}/{total} ({progress:5.1f}%) | "
                  f"Hits: {hits:3d} | Rate: {rate:4.1f} db/s | ETA: {eta:4.0f}s")
    
    hit_rate = (hits / total * 100) if total > 0 else 0
    elapsed = time.time() - start_time
    
    print(f"  ✓ {mod}: {hits}/{total} ({hit_rate:.1f}%) in {elapsed:.1f}s")
    return hits, total

def main():
    """Run quick test across all MODs"""
    print("AGR BLAST Database Manager - Quick Progress Test")
    print("=" * 60)
    
    # Change to correct directory
    script_dir = pathlib.Path(__file__).parent
    os.chdir(script_dir)
    
    # Discover databases
    all_databases = discover_databases_by_mod()
    total_dbs = sum(len(dbs) for dbs in all_databases.values())
    
    print(f"Found {total_dbs} databases across {len(all_databases)} MODs")
    for mod, dbs in all_databases.items():
        print(f"  {mod}: {len(dbs)}")
    
    # Test each MOD
    overall_start = time.time()
    total_hits = 0
    total_tested = 0
    
    for mod, databases in all_databases.items():
        if not databases:
            continue
            
        query_file = MOD_SEQUENCES[mod]
        hits, tested = test_mod_quick(mod, databases, query_file)
        total_hits += hits
        total_tested += tested
    
    # Final summary
    overall_time = time.time() - overall_start
    overall_rate = (total_hits / total_tested * 100) if total_tested > 0 else 0
    
    print(f"\n{'='*20} FINAL RESULTS {'='*20}")
    print(f"Total databases tested: {total_tested}")
    print(f"Total hits found: {total_hits}")
    print(f"Overall hit rate: {overall_rate:.1f}%")
    print(f"Total time: {overall_time:.1f} seconds")
    print(f"Average: {total_tested/overall_time:.1f} databases/second")
    print("=" * 60)

if __name__ == "__main__":
    main()