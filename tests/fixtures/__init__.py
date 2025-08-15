"""
fixtures package

Test fixtures and sample data for the AGR BLAST DB Manager.
"""

from .mock_data.sample_configurations import *
from .mock_data.sample_sequences import *

__all__ = [
    # Configuration fixtures
    'SAMPLE_GLOBAL_CONFIG',
    'SAMPLE_WB_CONFIG', 
    'SAMPLE_SGD_CONFIG',
    'SAMPLE_ZFIN_CONFIG',
    'SAMPLE_UI_TEST_CONFIG',
    'SAMPLE_LOAD_TEST_CONFIG',
    'ERROR_SCENARIOS',
    'PERFORMANCE_TEST_DATA',
    
    # Sequence fixtures
    'SIMPLE_NUCLEOTIDE_FASTA',
    'SIMPLE_PROTEIN_FASTA',
    'PARSE_SEQIDS_NUCLEOTIDE_FASTA',
    'PARSE_SEQIDS_PROTEIN_FASTA',
    'MIXED_HEADER_FASTA',
    'LARGE_SEQUENCE_FASTA',
    'INVALID_FASTA_NO_HEADER',
    'INVALID_FASTA_EMPTY_SEQUENCE',
    'INVALID_FASTA_SPECIAL_CHARS',
    'CELEGANS_SAMPLE_SEQUENCES',
    'SCEREVISIAE_SAMPLE_SEQUENCES',
    'MOD_SPECIFIC_SEQUENCES',
    'EDGE_CASE_SEQUENCES',
    'COMPRESSED_SEQUENCES'
]