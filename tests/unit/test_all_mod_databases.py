#!/usr/bin/env python3
"""
Comprehensive BLAST Database Testing Script for All MODs

Tests BLAST databases across all Model Organism Databases (MODs):
- FB (FlyBase): 513 databases
- SGD (Saccharomyces Genome Database): 333 databases  
- WB (WormBase): 217 databases
- ZFIN (Zebrafish Information Network): 7 databases
- RGD (Rat Genome Database): 2 databases

Total: 1,072 BLAST databases
"""

import subprocess
import glob
import os
import pathlib
import time
from typing import Dict, List, Tuple

# Universal highly conserved sequences that should exist in all eukaryotes
UNIVERSAL_SEQUENCES = '../../tests/fixtures/universal_conserved.fasta'  # 18S/28S rRNA, COI, actin, GAPDH, histone H3, EF-1α, U6 snRNA

# Use universal sequences for all MODs for maximum compatibility
MOD_SEQUENCES = {
    'FB': UNIVERSAL_SEQUENCES,    # Universal sequences work better across species
    'SGD': UNIVERSAL_SEQUENCES,   # Universal sequences work better across strains
    'WB': UNIVERSAL_SEQUENCES,    # Universal sequences work better across species
    'ZFIN': UNIVERSAL_SEQUENCES,  # Universal sequences work better
    'RGD': UNIVERSAL_SEQUENCES    # Universal sequences work better
}

def validate_database(db_path: str) -> tuple[bool, str]:
    """Check if database is valid and functional"""
    try:
        # Check if all required database files exist
        required_extensions = ['.nin', '.nhr', '.nsq']  # nucleotide database files
        for ext in required_extensions:
            if not os.path.exists(db_path + ext):
                return False, f"Missing file: {db_path}{ext}"
        
        # Try to get database info
        result = subprocess.run([
            'blastdbcmd', '-db', db_path, '-info'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return False, f"blastdbcmd failed: {result.stderr[:100]}"
        
        # Check if database has sequences
        info_output = result.stdout
        if "sequences;" in info_output:
            # Extract sequence count
            try:
                seq_count = int(info_output.split("sequences;")[0].split()[-1].replace(',', ''))
                if seq_count == 0:
                    return False, "Database contains 0 sequences"
                return True, f"{seq_count} sequences"
            except:
                return True, "Database appears valid"
        
        return False, "Could not determine sequence count"
        
    except subprocess.TimeoutExpired:
        return False, "Database validation timeout"
    except Exception as e:
        return False, f"Validation error: {str(e)[:50]}"

def test_sequence_relaxed(query_file: str, db_path: str, db_name: str) -> tuple[bool, str]:
    """Test sequence with very relaxed parameters for maximum sensitivity"""
    try:
        result = subprocess.run([
            'blastn', '-query', query_file, '-db', db_path,
            '-outfmt', '6 qseqid sseqid pident length evalue bitscore',
            '-evalue', '10',        # Very permissive e-value
            '-word_size', '7',      # More sensitive word size
            '-max_target_seqs', '10' # More targets to check
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return False, f"BLAST failed: {result.stderr[:50]}"
        
        output_lines = [line for line in result.stdout.strip().split('\n') 
                       if line and not line.startswith('Warning')]
        
        if output_lines:
            best_hit = output_lines[0].split('\t')
            if len(best_hit) >= 6:
                identity = float(best_hit[2])
                evalue = float(best_hit[4])
                # Very relaxed threshold - any reasonable hit counts
                if identity >= 50.0 or evalue <= 1.0:  # Much more permissive
                    return True, f"{identity:.1f}% identity, E={evalue:.2e}"
        
        return False, "No significant hits found"
            
    except subprocess.TimeoutExpired:
        return False, "BLAST timeout"
    except Exception as e:
        return False, f"BLAST error: {str(e)[:50]}"

def count_sequences_in_fasta(fasta_file: str) -> int:
    """Count number of sequences in FASTA file"""
    try:
        with open(fasta_file, 'r') as f:
            count = sum(1 for line in f if line.startswith('>'))
        return count
    except:
        return 0

def discover_latest_databases_by_mod(base_path: str = "/var/sequenceserver-data/blast") -> Dict[str, List[Tuple[str, str]]]:
    """Discover BLAST databases from most recent release only for each MOD"""
    databases = {}
    
    # Define most recent releases for each MOD
    latest_releases = {
        'FB': ['FB2025_03'],           # Most recent FlyBase
        'SGD': ['main', 'fungal'],     # SGD has both main and fungal
        'WB': ['WS297'],               # Most recent WormBase
        'ZFIN': ['prod'],              # ZFIN production
        'RGD': ['production']          # RGD production
    }
    
    for mod, releases in latest_releases.items():
        databases[mod] = []
        
        for release in releases:
            mod_release_path = pathlib.Path(base_path) / mod / release
            
            if not mod_release_path.exists():
                print(f"Warning: {mod} {release} directory not found at {mod_release_path}")
                continue
                
            # Find all .nin files (nucleotide databases) in this release
            nin_files = list(mod_release_path.rglob("*.nin"))
            
            for nin_file in nin_files:
                # Extract database path (remove .nin extension)
                db_path = str(nin_file).replace('.nin', '')
                
                # Create readable database name from path
                rel_path = nin_file.relative_to(mod_release_path)
                db_name = f"{mod} {release}: {'/'.join(rel_path.parts[:-1])}/{rel_path.stem}"
                
                databases[mod].append((db_name, db_path))
    
    return databases

def test_all_mod_databases():
    """Test latest release databases for all MODs"""
    print("AGR BLAST Database Manager - Latest Release Testing")
    print("=" * 60)
    
    # Discover latest release databases only
    all_databases = discover_latest_databases_by_mod()
    
    # Print summary
    total_dbs = sum(len(dbs) for dbs in all_databases.values())
    print(f"Testing latest releases only:")
    releases_info = {
        'FB': 'FB2025_03', 
        'SGD': 'main + fungal', 
        'WB': 'WS297', 
        'ZFIN': 'prod', 
        'RGD': 'production'
    }
    for mod, dbs in all_databases.items():
        print(f"  {mod} ({releases_info[mod]}): {len(dbs)} databases")
    print(f"  Total latest: {total_dbs} databases")
    print()
    
    # Test each MOD
    overall_stats = {}
    
    for mod, databases in all_databases.items():
        if not databases:
            continue
            
        print(f"\n{'='*20} Testing {mod} Databases {'='*20}")
        query_file = MOD_SEQUENCES[mod]
        
        # Verify query file exists
        if not os.path.exists(query_file):
            print(f"❌ Query file not found: {query_file}")
            continue
            
        # Get sequence info
        seq_count = count_sequences_in_fasta(query_file)
        try:
            with open(query_file, 'r') as f:
                lines = f.readlines()
                # Find first sequence line
                seq_line = next((line for line in lines if not line.startswith('>') and not line.startswith('#') and line.strip()), "")
                seq_length = len(seq_line.strip()) if seq_line else 0
                print(f"Query sequences: {seq_count} sequences, avg ~{seq_length}bp")
        except Exception as e:
            print(f"❌ Error reading query file: {e}")
            continue
            
        # Test databases with progress tracking
        hits = 0
        total = len(databases)
        hit_databases = []
        start_time = time.time()
        
        print(f"Testing {total} databases...")
        print("Progress: [", end="", flush=True)
        
        invalid_dbs = []
        valid_no_hits = []
        
        for i, (db_name, db_path) in enumerate(sorted(databases)):
            # Show progress every 10% or every 50 databases (whichever is smaller)
            progress_interval = min(50, max(1, total // 10))
            if i % progress_interval == 0:
                progress_pct = (i / total) * 100
                print(f"{progress_pct:.0f}%", end="", flush=True)
                if i < total - progress_interval:
                    print("...", end="", flush=True)
            
            # First validate the database
            is_valid, validation_msg = validate_database(db_path)
            if not is_valid:
                print(f"⚠ {db_name}: INVALID - {validation_msg}")
                invalid_dbs.append((db_name, validation_msg))
                continue
            
            # Test sequences on valid database
            has_hit, hit_msg = test_sequence_relaxed(query_file, db_path, db_name)
            if has_hit:
                hits += 1
                hit_databases.append(db_name)
                print(f"✓ {db_name}: {hit_msg}")
            else:
                valid_no_hits.append((db_name, hit_msg))
                if len(valid_no_hits) <= 5:  # Show first few no-hit cases
                    print(f"✗ {db_name}: {hit_msg} ({validation_msg})")
        
        print("] Complete!")
        elapsed = time.time() - start_time
        print(f"Testing completed in {elapsed:.1f} seconds")
        
        # MOD summary
        valid_dbs = total - len(invalid_dbs)
        hit_rate = (hits / valid_dbs * 100) if valid_dbs > 0 else 0
        print(f"\n{mod} Results:")
        print(f"  Total databases: {total}")
        print(f"  Invalid databases: {len(invalid_dbs)}")
        print(f"  Valid databases: {valid_dbs}")
        print(f"  Databases with hits: {hits}")
        print(f"  Hit rate (valid only): {hit_rate:.1f}%")
        
        if invalid_dbs:
            print(f"  Invalid database examples:")
            for db_name, reason in invalid_dbs[:3]:  # Show first 3
                print(f"    - {db_name}: {reason}")
            if len(invalid_dbs) > 3:
                print(f"    ... and {len(invalid_dbs) - 3} more")
        
        overall_stats[mod] = {
            'total': total,
            'invalid': len(invalid_dbs),
            'valid': valid_dbs,
            'hits': hits,
            'hit_rate': hit_rate,
            'hit_databases': hit_databases,
            'invalid_dbs': invalid_dbs,
            'valid_no_hits': valid_no_hits
        }
    
    # Overall summary
    print(f"\n{'='*25} OVERALL RESULTS {'='*25}")
    total_dbs = sum(stats['total'] for stats in overall_stats.values())
    total_invalid = sum(stats['invalid'] for stats in overall_stats.values())
    total_valid = sum(stats['valid'] for stats in overall_stats.values())
    total_hits = sum(stats['hits'] for stats in overall_stats.values())
    overall_hit_rate = (total_hits / total_valid * 100) if total_valid > 0 else 0
    
    print(f"Total databases found: {total_dbs}")
    print(f"Invalid databases: {total_invalid} ({total_invalid/total_dbs*100:.1f}%)")
    print(f"Valid databases: {total_valid}")
    print(f"Databases with hits: {total_hits}")  
    print(f"Hit rate (valid only): {overall_hit_rate:.1f}%")
    print()
    
    # Per-MOD breakdown
    print("Breakdown by MOD:")
    for mod, stats in overall_stats.items():
        print(f"{mod:4s}: {stats['hits']:3d}/{stats['valid']:3d} valid ({stats['hit_rate']:5.1f}%) | "
              f"{stats['invalid']} invalid | {stats['total']} total")
    
    print("\n" + "=" * 80)
    print("Testing completed!")
    
    return overall_stats

if __name__ == "__main__":
    # Change to the correct working directory for relative paths
    script_dir = pathlib.Path(__file__).parent
    os.chdir(script_dir)
    
    test_all_mod_databases()