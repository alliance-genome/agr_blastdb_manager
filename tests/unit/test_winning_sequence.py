#!/usr/bin/env python3

import subprocess
import glob
import os

def test_ui_defaults(sequence, db_path):
    """Test with UI default parameters"""
    with open('winner.fasta', 'w') as f:
        f.write(f">winner\n{sequence}\n")
    
    try:
        result = subprocess.run([
            'blastn', '-query', 'winner.fasta', '-db', db_path,
            '-outfmt', '6', '-word_size', '11', '-dust', 'yes', '-evalue', '10'
        ], capture_output=True, text=True, timeout=30)
        
        output_lines = [line for line in result.stdout.strip().split('\n') if line and not line.startswith('Warning')]
        return len(output_lines) > 0
    except:
        return False

# The winning sequence
winner_sequence = "ATGTGTGACGAAGAAGTTGCCGCCGAAG"

# Test against diverse FB species
base_path = '/var/sequenceserver-data/blast/FB/FB2025_03/databases'
test_species = []

# Get genome databases for diverse species
diverse_genera = ['Drosophila', 'Apis', 'Tribolium', 'Bombyx', 'Musca', 'Anopheles', 'Nasonia', 'Ixodes']
for genus in diverse_genera:
    genus_path = f"{base_path}/{genus}"
    if os.path.exists(genus_path):
        for species_dir in os.listdir(genus_path):
            species_path = f"{genus_path}/{species_dir}"
            if os.path.isdir(species_path):
                for db_dir in glob.glob(f"{species_path}/*Genome*"):
                    nin_files = glob.glob(f"{db_dir}/*.nin")
                    if nin_files:
                        db_path = nin_files[0].replace('.nin', '')
                        test_species.append((f"{genus} {species_dir}", db_path))
                        break
                break

print(f"Testing winner sequence with UI defaults: {winner_sequence}")
print("=" * 80)

hits = 0
total = 0
for species_name, db_path in test_species:
    total += 1
    has_hit = test_ui_defaults(winner_sequence, db_path)
    if has_hit:
        hits += 1
        print(f"✓ {species_name}")
    else:
        print(f"✗ {species_name}")

print(f"\nRESULT: {hits}/{total} species ({hits/total*100:.1f}%)")

# Clean up
if os.path.exists('winner.fasta'):
    os.remove('winner.fasta')