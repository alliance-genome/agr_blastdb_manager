#!/usr/bin/env python3

import os
import subprocess
import glob

def run_blast(query_file, db_path):
    """Run BLAST and return whether hits were found"""
    try:
        result = subprocess.run([
            'blastn', '-query', query_file, '-db', db_path,
            '-outfmt', '6', '-max_target_seqs', '1', '-word_size', '7'
        ], capture_output=True, text=True, timeout=30)
        
        # Check if there are hits (non-empty output excluding warnings)
        output_lines = [line for line in result.stdout.strip().split('\n') if line and not line.startswith('Warning')]
        return len(output_lines) > 0
    except:
        return False

# Test sequence
query_file = 'test_minimal_sequence.fasta'

# Find all genome assembly databases
base_path = '/var/sequenceserver-data/blast/FB/FB2025_03/databases'
genome_dbs = []

for genus_dir in glob.glob(f"{base_path}/*"):
    if os.path.isdir(genus_dir):
        genus = os.path.basename(genus_dir)
        for species_dir in glob.glob(f"{genus_dir}/*"):
            if os.path.isdir(species_dir):
                species = os.path.basename(species_dir)
                # Look for genome assembly databases (usually nucleotide, not RNA or protein)
                for db_dir in glob.glob(f"{species_dir}/*Genome*"):
                    if os.path.isdir(db_dir):
                        # Find the .nin file to get database name
                        nin_files = glob.glob(f"{db_dir}/*.nin")
                        if nin_files:
                            db_path = nin_files[0].replace('.nin', '')
                            genome_dbs.append((genus, species, db_path))

print(f"Testing {len(genome_dbs)} genome databases...")
hits = 0
total = 0

for genus, species, db_path in genome_dbs:  # Test all databases
    total += 1
    has_hit = run_blast(query_file, db_path)
    if has_hit:
        hits += 1
        print(f"✓ {genus} {species}")
    else:
        print(f"✗ {genus} {species}")

print(f"\nResults: {hits}/{total} species had hits ({hits/total*100:.1f}%)")