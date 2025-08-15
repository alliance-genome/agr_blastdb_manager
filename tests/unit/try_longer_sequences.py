#!/usr/bin/env python3

import subprocess
import os

def test_with_ui_defaults(sequence, name):
    """Test sequence with SequenceServer UI default parameters"""
    with open('test_seq.fasta', 'w') as f:
        f.write(f">{name}\n{sequence}\n")
    
    # UI defaults: word_size=11, dust=yes, evalue=10
    try:
        result = subprocess.run([
            'blastn', '-query', 'test_seq.fasta', 
            '-db', '/var/sequenceserver-data/blast/FB/FB2025_03/databases/Drosophila/melanogaster/D_melanogaster_Genome_Assembly_6_64/dmel-assemblydb',
            '-outfmt', '6',
            '-word_size', '11',  # UI default
            '-dust', 'yes',      # UI default
            '-evalue', '10'      # UI default
        ], capture_output=True, text=True, timeout=30)
        
        output_lines = [line for line in result.stdout.strip().split('\n') if line and not line.startswith('Warning')]
        return len(output_lines) > 0, len(output_lines)
    except:
        return False, 0

# Try longer, more conserved sequences that match word_size=11
test_sequences = [
    # 28bp sequences (longer for word_size=11)
    ("actin_28bp", "ATGTGTGACGAAGAAGTTGCCGCCGAAG"),
    ("tubulin_28bp", "ATGCGTGAGATCGTGCACATCCGCAAGC"),
    ("histone_28bp", "ATGGCTCGCACCAAGCAGACGTCCTACC"),
    
    # Very common sequences
    ("ribosomal_30bp", "AAGAAACTCAAATGAATGACCCTATGAACT"),
    ("conserved_kozak", "GCCGCCACCATGGCCGCCGCCACCATG"),
    
    # Multiple start codons
    ("multi_start", "ATGATGATGATGATGATGATGATGATG"),
    
    # Poly sequences that should exist
    ("poly_gc", "GCGCGCGCGCGCGCGCGCGCGCGCGCGC"),
    ("cpg_islands", "CGCGCGCGCGCGCGCGCGCGCGCGCG")
]

print("Testing with UI default parameters (word_size=11, dust=yes, evalue=10)")
print("=" * 70)

for name, sequence in test_sequences:
    has_hits, count = test_with_ui_defaults(sequence, name)
    if has_hits:
        print(f"✓ {name} ({len(sequence)}bp): {count} hits - {sequence}")
    else:
        print(f"✗ {name} ({len(sequence)}bp): No hits - {sequence}")

# Clean up
if os.path.exists('test_seq.fasta'):
    os.remove('test_seq.fasta')