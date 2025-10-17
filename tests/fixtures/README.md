# Test Fixtures for Database Validation

This directory contains test sequence files used for validating BLAST databases.

## Files

### Universal Conserved Sequences
**`universal_conserved.fasta`** - Highly conserved sequences found across all eukaryotic organisms:
- 18S rRNA - Universal ribosomal RNA
- 28S rRNA - Large ribosomal subunit RNA
- COI mitochondrial - Cytochrome c oxidase subunit I
- Actin - Structural protein
- GAPDH - Glyceraldehyde-3-phosphate dehydrogenase
- U6 snRNA - Small nuclear RNA for splicing
- Histone H3 - DNA packaging protein
- EF-1α - Translation elongation factor

These sequences are used to test basic database functionality and searchability.

## Usage

The validation system automatically loads sequences from these fixture files. If files are missing, it falls back to hardcoded sequences in `src/validation.py`.

## Adding New Test Sequences

To add new test sequences:

1. Create a new FASTA file in this directory
2. Use descriptive headers (e.g., `>sequence_name_description`)
3. Keep sequences reasonably short (100-200 bp) for fast validation
4. Update the validation system to reference the new file

## Updating Sequences

You can update sequences in these files without modifying the validation code. The system will automatically use the latest versions from these files.

## MOD-Specific Sequences

MOD-specific test sequences are currently hardcoded in `src/validation.py`. Future enhancements may move these to separate fixture files per MOD.
