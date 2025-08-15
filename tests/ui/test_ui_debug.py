#!/usr/bin/env python3

import os
import subprocess
import glob

def test_permissive_blast(query_file, db_path, species_name):
    """Test with extremely permissive BLAST parameters"""
    try:
        # Very permissive parameters
        result = subprocess.run([
            'blastn', '-query', query_file, '-db', db_path,
            '-outfmt', '6 qseqid sseqid pident length evalue',
            '-max_target_seqs', '1',
            '-evalue', '1000',      # Very high e-value
            '-word_size', '4',      # Very small word size  
            '-dust', 'no',          # No filtering
            '-penalty', '-1',       # Mismatch penalty
            '-reward', '1',         # Match reward
            '-gapopen', '2',        # Gap open penalty
            '-gapextend', '1'       # Gap extend penalty
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"  ERROR {species_name}: {result.stderr.strip()}")
            return False
            
        output_lines = [line for line in result.stdout.strip().split('\n') if line and not line.startswith('Warning')]
        has_hits = len(output_lines) > 0
        
        if has_hits:
            print(f"  ✓ {species_name}: {output_lines[0]}")
        else:
            print(f"  ✗ {species_name}: No hits")
            
        return has_hits
    except Exception as e:
        print(f"  ERROR {species_name}: {e}")
        return False

# Test different sequence lengths and types
test_sequences = [
    ("actin21", "ATGTGTGACGAAGAAGTTGCC"),
    ("actin18", "ATGTGTGACGAAGAAGTT"),
    ("actin15", "ATGTGTGACGAAGAA"),
    ("atg_start", "ATGGCCGCGCCG"),
    ("poly_at", "ATATATATATATAT"),
    ("ribosomal", "GTCGTAACAAGGTA")
]

# Test against a few FB2025 species
base_path = '/var/sequenceserver-data/blast/FB'
test_species = []

# Find available FB2025 databases
for version in ['FB2025_01', 'FB2025_03']:
    version_path = f"{base_path}/{version}/databases"
    if os.path.exists(version_path):
        print(f"Found {version}")
        # Get D. melanogaster first
        mel_path = f"{version_path}/Drosophila/melanogaster"
        if os.path.exists(mel_path):
            for db_dir in glob.glob(f"{mel_path}/*Genome*"):
                nin_files = glob.glob(f"{db_dir}/*.nin")
                if nin_files:
                    db_path = nin_files[0].replace('.nin', '')
                    test_species.append((f"D.mel_{version}", db_path))
                    break
        
        # Get one other species
        apis_path = f"{version_path}/Apis/mellifera"  
        if os.path.exists(apis_path):
            for db_dir in glob.glob(f"{apis_path}/*Genome*"):
                nin_files = glob.glob(f"{db_dir}/*.nin")
                if nin_files:
                    db_path = nin_files[0].replace('.nin', '')
                    test_species.append((f"A.mel_{version}", db_path))
                    break

print(f"\nTesting {len(test_species)} databases with {len(test_sequences)} sequences...")
print("=" * 80)

for seq_name, sequence in test_sequences:
    print(f"\n{seq_name.upper()}: {sequence}")
    print("-" * 40)
    
    # Write sequence to temp file
    with open('temp_seq.fasta', 'w') as f:
        f.write(f">{seq_name}\n{sequence}\n")
    
    for species_name, db_path in test_species:
        test_permissive_blast('temp_seq.fasta', db_path, species_name)

# Clean up
if os.path.exists('temp_seq.fasta'):
    os.remove('temp_seq.fasta')