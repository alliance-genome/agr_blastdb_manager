#!/usr/bin/env python3

import os
import subprocess
import glob

def run_blast_ui_params(query_file, db_path):
    """Run BLAST with UI-like parameters"""
    try:
        result = subprocess.run([
            'blastn', '-query', query_file, '-db', db_path,
            '-outfmt', '6',
            '-max_target_seqs', '50',
            '-evalue', '10',
            '-word_size', '11',
            '-dust', 'yes'
        ], capture_output=True, text=True, timeout=30)
        
        output_lines = [line for line in result.stdout.strip().split('\n') if line and not line.startswith('Warning')]
        return len(output_lines) > 0
    except:
        return False

# Test the two best sequences
test_sequences = [
    ("actin", "ATGTGTGACGAAGAAGTTGCC"),
    ("tubulin", "ATGCGTGAGATCGTGCACATCC"),
]

# Get all genome databases
base_path = '/var/sequenceserver-data/blast/FB/FB2025_03/databases'
genome_dbs = []

for genus_dir in glob.glob(f"{base_path}/*"):
    if os.path.isdir(genus_dir):
        genus = os.path.basename(genus_dir)
        for species_dir in glob.glob(f"{genus_dir}/*"):
            if os.path.isdir(species_dir):
                species = os.path.basename(species_dir)
                for db_dir in glob.glob(f"{species_dir}/*Genome*"):
                    if os.path.isdir(db_dir):
                        nin_files = glob.glob(f"{db_dir}/*.nin")
                        if nin_files:
                            db_path = nin_files[0].replace('.nin', '')
                            genome_dbs.append((genus, species, db_path))

print(f"Testing {len(genome_dbs)} FB genome databases with UI parameters...")
print("=" * 70)

for seq_name, sequence in test_sequences:
    print(f"\n{seq_name.upper()}: {sequence}")
    print("-" * 50)
    
    # Write sequence to temp file
    with open('temp_test.fasta', 'w') as f:
        f.write(f">{seq_name}\n{sequence}\n")
    
    hits = 0
    total = 0
    failed_species = []
    
    for genus, species, db_path in sorted(genome_dbs):
        total += 1
        has_hit = run_blast_ui_params('temp_test.fasta', db_path)
        if has_hit:
            hits += 1
            print(f"✓ {genus} {species}")
        else:
            failed_species.append(f"{genus} {species}")
            print(f"✗ {genus} {species}")
    
    print(f"\nSUMMARY for {seq_name}:")
    print(f"  Success: {hits}/{total} species ({hits/total*100:.1f}%)")
    if failed_species:
        print(f"  Failed: {', '.join(failed_species)}")
    print("\n" + "=" * 70)

# Clean up
if os.path.exists('temp_test.fasta'):
    os.remove('temp_test.fasta')