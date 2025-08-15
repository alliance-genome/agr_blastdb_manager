#!/usr/bin/env python3

import os
import subprocess
import glob

def run_blast_ui_params(query_file, db_path, sequence_name):
    """Run BLAST with UI-like parameters"""
    try:
        # Test with UI-like default parameters
        result = subprocess.run([
            'blastn', '-query', query_file, '-db', db_path,
            '-outfmt', '6 qseqid sseqid pident length evalue bitscore',
            '-max_target_seqs', '50',  # UI default
            '-evalue', '10',           # UI default
            '-word_size', '11',        # UI default for blastn
            '-dust', 'yes'             # UI default filtering
        ], capture_output=True, text=True, timeout=30)
        
        # Check if there are hits (non-empty output excluding warnings)
        output_lines = [line for line in result.stdout.strip().split('\n') if line and not line.startswith('Warning')]
        return len(output_lines) > 0, len(output_lines)
    except Exception as e:
        return False, 0

# Test multiple sequences
test_sequences = [
    ("actin_current", "ATGTGTGACGAAGAAGTTGCC"),
    ("actin_shorter", "ATGTGTGACGAAGAAGTT"),
    ("histone_h3", "ATGGCTCGCACCAAGCAGAC"),
    ("tubulin_alpha", "ATGCGTGAGATCGTGCACATCC"),
    ("ribosomal_l32", "ATGACCGTCCGCAAGTACGC"),
    ("universal_start", "ATGGCCGCGCCGTAC")
]

base_path = '/var/sequenceserver-data/blast/FB/FB2025_03/databases'
genome_dbs = []

# Get a representative sample of diverse species
diverse_species = [
    "Drosophila/melanogaster",     # Diptera (most common)
    "Apis/mellifera",              # Hymenoptera 
    "Tribolium/castaneum",         # Coleoptera
    "Bombyx/mori",                 # Lepidoptera
    "Acyrthosiphon/pisum",         # Hemiptera
    "Ixodes/scapularis"            # Acari (tick)
]

for species_path in diverse_species:
    full_path = f"{base_path}/{species_path}"
    if os.path.exists(full_path):
        for db_dir in glob.glob(f"{full_path}/*Genome*"):
            nin_files = glob.glob(f"{db_dir}/*.nin")
            if nin_files:
                db_path = nin_files[0].replace('.nin', '')
                genome_dbs.append((species_path.replace('/', ' '), db_path))

print("Testing sequences with UI-compatible parameters...")
print("=" * 60)

for seq_name, sequence in test_sequences:
    print(f"\nTesting: {seq_name} - {sequence}")
    
    # Write sequence to temp file
    with open('temp_test.fasta', 'w') as f:
        f.write(f">{seq_name}\n{sequence}\n")
    
    hits = 0
    total = 0
    
    for species_name, db_path in genome_dbs:
        total += 1
        has_hit, hit_count = run_blast_ui_params('temp_test.fasta', db_path, seq_name)
        if has_hit:
            hits += 1
            print(f"  ✓ {species_name} ({hit_count} hits)")
        else:
            print(f"  ✗ {species_name}")
    
    print(f"  Result: {hits}/{total} species ({hits/total*100:.1f}%)")
    print("-" * 40)

# Clean up
if os.path.exists('temp_test.fasta'):
    os.remove('temp_test.fasta')