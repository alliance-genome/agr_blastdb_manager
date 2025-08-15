#!/usr/bin/env python3

import subprocess
import glob
import os

def test_sequence_stringent(query_file, db_path, species_name):
    """Test with stringent e-value like user is using"""
    try:
        result = subprocess.run([
            'blastn', '-query', query_file, '-db', db_path,
            '-outfmt', '6 qseqid sseqid pident length evalue bitscore',
            '-evalue', '1e-3',  # Stringent like user's e 10-3
            '-max_target_seqs', '5'
        ], capture_output=True, text=True, timeout=60)
        
        output_lines = [line for line in result.stdout.strip().split('\n') if line and not line.startswith('Warning')]
        if output_lines:
            print(f"✓ {species_name}: {len(output_lines)} hits")
            # Show best hit
            parts = output_lines[0].split('\t')
            print(f"  Best: {parts[1]} - {parts[2]}% identity, e-value {parts[4]}")
            return True
        else:
            print(f"✗ {species_name}: No hits")
            return False
    except Exception as e:
        print(f"ERROR {species_name}: {e}")
        return False

# Get all FB genome databases
base_path = '/var/sequenceserver-data/blast/FB'
all_dbs = []

# Check all FB versions
for version in ['FB2025_01', 'FB2025_03']:
    version_path = f"{base_path}/{version}/databases"
    if os.path.exists(version_path):
        print(f"Found {version}")
        
        for genus_dir in glob.glob(f"{version_path}/*"):
            if os.path.isdir(genus_dir):
                genus = os.path.basename(genus_dir)
                for species_dir in glob.glob(f"{genus_dir}/*"):
                    if os.path.isdir(species_dir):
                        species = os.path.basename(species_dir)
                        # Look for genome assembly databases
                        for db_dir in glob.glob(f"{species_dir}/*Genome*"):
                            if os.path.isdir(db_dir):
                                nin_files = glob.glob(f"{db_dir}/*.nin")
                                if nin_files:
                                    db_path = nin_files[0].replace('.nin', '')
                                    all_dbs.append((f"{genus} {species}", db_path))
                                    break

print(f"\nTesting user sequence against {len(all_dbs)} FB genome databases")
print(f"Sequence length: {len(open('../../tests/fixtures/test_user_sequence.fasta').readlines()[1].strip())}bp")
print("Using stringent e-value: 1e-3")
print("=" * 80)

hits = 0
total = 0
hit_species = []

for species_name, db_path in sorted(all_dbs):
    total += 1
    if test_sequence_stringent('../../tests/fixtures/test_user_sequence.fasta', db_path, species_name):
        hits += 1
        hit_species.append(species_name)

print("\n" + "=" * 80)
print(f"FINAL RESULTS:")
print(f"Hits: {hits}/{total} species ({hits/total*100:.1f}%)")
print(f"\nSpecies with hits:")
for species in hit_species:
    print(f"  - {species}")

if hits < total:
    print(f"\nSpecies without hits: {total - hits}")