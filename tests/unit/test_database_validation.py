#!/usr/bin/env python3

"""
Database validation test with highly conserved sequences and relaxed e-value.
Uses universal sequences that should be found across all organisms.
"""

import subprocess
import glob
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple, Dict

def create_conserved_test_sequences() -> Dict[str, str]:
    """
    Create highly conserved sequences that should exist in all organisms.
    These are chosen for maximum conservation across species.
    """
    sequences = {
        # 18S ribosomal RNA - highly conserved across all eukaryotes
        "18S_rRNA": """>18S_ribosomal_RNA_conserved_region
GTCAGAGGTGAAATTCTTGGATCGCCGCAAGACGAACCAAAGCGAAAGCATTTGCCAAG
AATGTTTTCATTAATCAAGAACGAAAGTTAGAGGTTCGAAGGCGATCAGATACCGCCCT
AGTTCTAACCATAAACGATGCCGACCAGGGATCAGCGAATGTTACGCT""",
        
        # 28S ribosomal RNA - another highly conserved sequence
        "28S_rRNA": """>28S_ribosomal_RNA_conserved_region  
GCCGGATCCTTTGAAGACGGGTCGCTTGCGACCCGACGCCAAGGAACCAAGCTGACCGT
CGAGGCAACCCACTCGGACGGGGGCCCAAGTCCAACTACGAGCTTTTTAACTGCAGCAA
CCGAAGCGTACCGCATGGCCGTTGCGCTTCGGC""",
        
        # Cytochrome c oxidase subunit I (COI) - mitochondrial, highly conserved
        "COI_mt": """>COI_mitochondrial_conserved
CTGGATCAGGAACAGGTTGAACAGTTTACCCTCCTTTATCAGCAGGAATTGCTCATGCA
GGAGCATCAGTTGATTTAGCTATTTTTTCTTTACATTTAGCAGGAATTTCATCAATTTT
AGGAGCAGTAAATTTTATTACAACAGTAATTAATATACGATCAACA""",
        
        # Actin - highly conserved protein-coding gene
        "actin": """>actin_conserved_region
ATGTGTGACGACGAGGAGACCACCGCCCTCGTCACCAGAGTCCATCACGATGCCAGTCC
TCAAGAACCCCTAAGGCCAACCGTGAAAAGATGACCCAGATCATGTTTGAGACCTTCAA
CACCCCCGCCATGTACGTTGCCATCCAGGCCGTGCTGTCCCT""",
        
        # GAPDH - housekeeping gene, very conserved
        "gapdh": """>GAPDH_conserved_region
GTCGGAGTCAACGGATTTGGTCGTATTGGGCGCCTGGTCACCAGGGCTGCTTTTAACTC
TGGTAAAGTGGATATTGTTGCCATCAATGACCCCTTCATTGACCTCAACTACATGGTTT
ACATGTTCCAATATGATTCCACCCATGGCAAATTCCATGGCACCG""",
        
        # U6 snRNA - highly conserved small nuclear RNA
        "U6_snRNA": """>U6_snRNA_conserved
GTGCTCGCTTCGGCAGCACATATACTAAAATTGGAACGATACAGAGAAGATTAGCATGG
CCCCTGCGCAAGGATGACACGCAAATTCGTGAAGCGTTCCATATTT""",
        
        # Histone H3 - extremely conserved across eukaryotes
        "histone_H3": """>histone_H3_conserved
GCGACCAACTTGTTGGGGACAACATTCGAAGTCTGGTCGGTCTCCTAAGCAGACCGGTG
GAAAAAGCAAACGACGGAAGGGCAAGGGAAGAAGACCCGCAGAGCGTCATGACCACCAC
AAGCAGACTGCGAGGAAGCAGCTGGCTACCAAGGCCGCTCGCAAGAGTGCGCCACGTGC""",
        
        # EF-1 alpha - translation elongation factor, highly conserved
        "EF1a": """>EF1_alpha_conserved  
GGTATTGGACAAACTGAAGGCTGAGCGTGAACGTGGTATCACCATTGATATCACACTTC
TCGGGTGCATCTCAACAGACTTCACATCAACATCGTCGTAATCGGACACGTCGATCTTG
GAGATACCAGCCTCGGCCCACTTACAGCTGAGTTCGAAGGCTGGTCCATC"""
    }
    return sequences

def create_mod_specific_sequences() -> Dict[str, Dict[str, str]]:
    """
    Create MOD-specific sequences that should definitely exist in each organism.
    These are actual sequences from reference genomes.
    """
    mod_sequences = {
        "FB": {
            # Drosophila-specific sequences
            "white_gene": """>Drosophila_white_gene_fragment
ATGGTCAATTACAAGGTGCGCAGCCTGGCCGAGGACTTCCTGGAGGAGGAGAAGAAGCC
GCTGATCTTCTCGGATCCGCCCAAATCCACCAAGCCCGAGTTCCAGTTCAGCGTGCTGG""",
            "rosy_gene": """>Drosophila_rosy_gene
ATGGCGGAAGAAGTGGCGATGTTGAAGGTGAAGGCCGGCAAGGGCAAGGTGGGCAAGCT
GGAGCGCTGGAACTACGCCAAGCACGTGGAGACCTACTCGCCCGAGATCGTGCACAAGG"""
        },
        "WB": {
            # C. elegans-specific sequences  
            "unc-22": """>C_elegans_unc22_fragment
ATGAACACCAAAATCGTTGATACGATTGCAGATGAAACAACGTCCATTCCAGAAGAGAT
TCAAATCATGAAGACTTTAGGACCGGTCGATGGCGATCGCGACGCTCTGGAGACTCTCC""",
            "dpy-10": """>C_elegans_dpy10
ATGTCGTCAAAAAGAAGACTGAAAAAGCTATTAGCACTTGTATTAGCCGTTCTTCAAGC
AGTGTTCGCAAAACTCGTTGCTTCAGCCGGTGGAGCTGTACCAGGAGCCGTTATTGGCG"""
        },
        "SGD": {
            # Yeast-specific sequences
            "GAL1": """>S_cerevisiae_GAL1_promoter
CGAGGCAAGCTAAACAGATCTCCAGAAGAAGGGTTGAATGATAGGAAACACATGAAATA
AAGCATTCTCAATATATTAAACTAAGTGAAAATCTTATAGGTGCCACTAAACCGTAACT""",
            "ACT1": """>S_cerevisiae_ACT1
ATGGATTCTGGTATGTTCTAGCGCTTGCACCATCCCATTTAACTGTAAGAAGAATTGCA
CGATGCATCATGGAAGATGCTGTTGTTCCCACATCCGTTTTCGCCGCAATAAGAAAAAC"""
        },
        "ZFIN": {
            # Zebrafish-specific sequences
            "pax2a": """>zebrafish_pax2a_fragment
ATGGATAGCCCGAGGTTGCAGACAGATCTGCACGGAAGCCCAGTCATGTTCGCCTCGGT
CATCAACGGGACCAAGCTGGAGAAGAAAATCCGCCACACGAAGAGGATCTGCGCCAATG""",
            "sonic_hedgehog": """>zebrafish_shh
ATGCGGCTTTTGACGAGAATAGCCGGGCCGATCTTGCCATCTCCGTGATGAACCAGTGG
CCGCCCGTCCACAACAAAGACTCGAGCTGGGTGGATGTCCGAGGCCAAGGCAATCCTCG"""
        },
        "RGD": {
            # Rat-specific sequences
            "Alb": """>rat_albumin_fragment
ATGAAGTGGGTAACCTTTATTTCCCTTCTTTTTCTCTTTAGCTCGGCTTATTCCAGGGC
TGTGTGACTAGACTCACCAAATGCCATTGTCAATGGAAGCTGCACGCTGCCGTCCTGCA""",
            "Ins1": """>rat_insulin1
ATGGCCCTGTGGATGCGCCTCCTGCCCCTGCTGGCGCTGCTGGCCCTCTGGGGACCTGA
CCCAGCCGCAGCCTTTGTGAACCAACACCTGTGCGGCTCACACCTGGTGGAAGCTCTCT"""
        },
        "XB": {
            # Xenopus-specific sequences
            "sox2": """>xenopus_sox2_fragment
ATGTATAAGATGGCCACGGCAGCGCCCGGATGCACCGCTACGACGTGAGCGCCCTGCAG
TATAACTCCAACAACAACAGCAGCTACAGCATGATGCAGGACCAGCTGGGCTACCCGCA""",
            "bmp4": """>xenopus_bmp4
ATGATTCTTTACCGGCTCCAGTCTCTGGGCCTCTGCTTCCCGCAGCTGCTCGCCTCGAT
GCCCTCCCTGCTGACGGACTCCTTTTCTGGAATTCAGCCCTAAGCAAGATGCCGAGCCG"""
        }
    }
    return mod_sequences

def test_database_comprehensive(query_file: str, db_path: str, db_name: str, 
                               blast_type: str = "blastn", evalue: str = "10") -> Tuple[bool, int, float, str]:
    """
    Test a database with relaxed e-value for validation purposes.
    Returns: (success, hit_count, best_identity, best_hit_name)
    """
    try:
        result = subprocess.run([
            blast_type, '-query', query_file, '-db', db_path,
            '-outfmt', '6 qseqid sseqid pident length evalue bitscore stitle',
            '-evalue', evalue,  # Much more relaxed for validation
            '-max_target_seqs', '10',
            '-word_size', '7',  # Smaller word size for better sensitivity
            '-num_threads', '2'
        ], capture_output=True, text=True, timeout=30)
        
        output_lines = [line for line in result.stdout.strip().split('\n') 
                       if line and not line.startswith('Warning')]
        
        if output_lines:
            # Parse best hit
            parts = output_lines[0].split('\t')
            hit_name = parts[1] if len(parts) > 1 else "unknown"
            identity = float(parts[2]) if len(parts) > 2 else 0.0
            return True, len(output_lines), identity, hit_name
        else:
            return False, 0, 0.0, ""
    except subprocess.TimeoutExpired:
        return False, 0, 0.0, "timeout"
    except Exception as e:
        return False, 0, 0.0, str(e)

def validate_mod_databases(mod: str, databases: List[Tuple[str, str]], 
                          conserved_seqs: Dict[str, str], 
                          mod_specific_seqs: Dict[str, Dict[str, str]]) -> Dict:
    """
    Validate databases for a specific MOD using both conserved and specific sequences.
    """
    print(f"\n{'=' * 20} Validating {mod} Databases {'=' * 20}")
    print(f"Testing {len(databases)} databases with conserved and MOD-specific sequences")
    
    results = {
        'total': len(databases),
        'with_conserved_hits': 0,
        'with_specific_hits': 0,
        'no_hits': [],
        'best_performers': []
    }
    
    # Test each database
    for i, (db_name, db_path) in enumerate(databases, 1):
        if i % 10 == 0 or len(databases) < 20:
            print(f"  Progress: {i}/{len(databases)} ({i/len(databases)*100:.0f}%)")
        
        # Determine blast type
        blast_type = "blastp" if db_path.endswith("_prot") or "protein" in db_path.lower() else "blastn"
        
        conserved_hits = 0
        specific_hits = 0
        
        # Test with conserved sequences
        for seq_name, seq_content in conserved_seqs.items():
            query_file = f"/tmp/test_{seq_name}.fasta"
            with open(query_file, 'w') as f:
                f.write(seq_content)
            
            success, hits, identity, _ = test_database_comprehensive(
                query_file, db_path, db_name, blast_type, evalue="10"
            )
            if success:
                conserved_hits += hits
        
        # Test with MOD-specific sequences if available
        if mod in mod_specific_seqs:
            for seq_name, seq_content in mod_specific_seqs[mod].items():
                query_file = f"/tmp/test_{mod}_{seq_name}.fasta"
                with open(query_file, 'w') as f:
                    f.write(seq_content)
                
                success, hits, identity, _ = test_database_comprehensive(
                    query_file, db_path, db_name, blast_type, evalue="10"
                )
                if success:
                    specific_hits += hits
        
        # Update results
        if conserved_hits > 0:
            results['with_conserved_hits'] += 1
        if specific_hits > 0:
            results['with_specific_hits'] += 1
        if conserved_hits == 0 and specific_hits == 0:
            results['no_hits'].append(db_name)
        
        if conserved_hits + specific_hits > 0:
            results['best_performers'].append({
                'name': db_name,
                'conserved_hits': conserved_hits,
                'specific_hits': specific_hits,
                'total_hits': conserved_hits + specific_hits
            })
    
    # Sort best performers
    results['best_performers'].sort(key=lambda x: x['total_hits'], reverse=True)
    results['best_performers'] = results['best_performers'][:5]  # Keep top 5
    
    return results

def main():
    """Main validation runner"""
    print("=" * 80)
    print("AGR BLAST Database Validation Test")
    print("Using highly conserved sequences and relaxed e-value (10)")
    print("=" * 80)
    
    # Find all databases
    base_path = "/var/sequenceserver-data/blast"
    mods = ["FB", "SGD", "WB", "ZFIN", "RGD", "XB"]
    all_databases = {}
    
    for mod in mods:
        mod_path = os.path.join(base_path, mod)
        databases = []
        
        if os.path.exists(mod_path):
            # Find all .nin files (nucleotide databases)
            for nin_file in Path(mod_path).rglob("*.nin"):
                db_path = str(nin_file).replace('.nin', '')
                db_name = nin_file.parent.name
                databases.append((db_name, db_path))
        
        if databases:
            all_databases[mod] = databases
    
    if not all_databases:
        print("ERROR: No databases found. Check path:", base_path)
        sys.exit(1)
    
    # Display summary
    print("\nFound databases:")
    total_dbs = 0
    for mod, databases in sorted(all_databases.items()):
        count = len(databases)
        total_dbs += count
        print(f"  {mod}: {count} databases")
    print(f"  Total: {total_dbs} databases\n")
    
    # Create test sequences
    conserved_seqs = create_conserved_test_sequences()
    mod_specific_seqs = create_mod_specific_sequences()
    
    print(f"Test sequences:")
    print(f"  - {len(conserved_seqs)} highly conserved sequences (rRNA, COI, actin, etc.)")
    print(f"  - MOD-specific sequences for each organism")
    print(f"  - Using relaxed e-value: 10 (for validation purposes)")
    print(f"  - Using smaller word size: 7 (for better sensitivity)\n")
    
    # Validate each MOD
    start_time = time.time()
    all_results = {}
    
    for mod in sorted(all_databases.keys()):
        databases = all_databases[mod]
        results = validate_mod_databases(mod, databases, conserved_seqs, mod_specific_seqs)
        all_results[mod] = results
        
        # Print MOD summary
        print(f"\n{mod} Results:")
        print(f"  Databases with conserved hits: {results['with_conserved_hits']}/{results['total']} ({results['with_conserved_hits']/results['total']*100:.1f}%)")
        print(f"  Databases with MOD-specific hits: {results['with_specific_hits']}/{results['total']} ({results['with_specific_hits']/results['total']*100:.1f}%)")
        
        if results['best_performers']:
            print(f"  Top performers:")
            for perf in results['best_performers'][:3]:
                print(f"    - {perf['name']}: {perf['total_hits']} total hits")
        
        if results['no_hits'] and len(results['no_hits']) <= 5:
            print(f"  Databases with no hits: {', '.join(results['no_hits'][:5])}")
    
    # Overall summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 25 + " OVERALL RESULTS " + "=" * 25)
    print(f"Total databases tested: {total_dbs}")
    
    total_with_hits = sum(r['with_conserved_hits'] for r in all_results.values())
    print(f"Total databases with conserved hits: {total_with_hits} ({total_with_hits/total_dbs*100:.1f}%)")
    
    total_with_specific = sum(r['with_specific_hits'] for r in all_results.values())
    print(f"Total databases with MOD-specific hits: {total_with_specific} ({total_with_specific/total_dbs*100:.1f}%)")
    
    print(f"\nPer-MOD hit rates (conserved sequences):")
    for mod in sorted(all_results.keys()):
        r = all_results[mod]
        rate = r['with_conserved_hits']/r['total']*100 if r['total'] > 0 else 0
        print(f"  {mod:4}: {r['with_conserved_hits']:3}/{r['total']:3} ({rate:5.1f}%)")
    
    print(f"\nCompleted in {elapsed:.1f} seconds")
    
    # Warnings for low hit rates
    if total_with_hits / total_dbs < 0.5:
        print("\n⚠️  WARNING: Low overall hit rate detected!")
        print("   This might indicate:")
        print("   - Databases are specialized (protein-only, non-coding RNA, etc.)")
        print("   - Database indexing issues")
        print("   - Need for different BLAST programs (tblastx, blastx)")

if __name__ == "__main__":
    main()