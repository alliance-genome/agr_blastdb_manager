"""
sample_configurations.py

Sample configuration data for testing.
"""

SAMPLE_GLOBAL_CONFIG = {
    "providers": {
        "WB": {
            "dev": "conf/WB/databases.WB.WS285.json",
            "prod": "conf/WB/databases.WB.WS286.json"
        },
        "SGD": {
            "dev": "conf/SGD/databases.SGD.dev.json", 
            "prod": "conf/SGD/databases.SGD.prod.json"
        },
        "FB": {
            "dev": "conf/FB/databases.FB.dev.json",
            "prod": "conf/FB/databases.FB.prod.json"
        },
        "ZFIN": {
            "dev": "conf/ZFIN/databases.ZFIN.dev.json",
            "prod": "conf/ZFIN/databases.ZFIN.prod.json"
        },
        "RGD": {
            "dev": "conf/RGD/databases.RGD.dev.json",
            "prod": "conf/RGD/databases.RGD.prod.json"
        },
        "XB": {
            "dev": "conf/XB/databases.XB.dev.json",
            "prod": "conf/XB/databases.XB.prod.json"
        }
    }
}

SAMPLE_WB_CONFIG = {
    "databases": [
        {
            "name": "Caenorhabditis_elegans_genomic",
            "uri": "https://downloads.wormbase.org/releases/WS285/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.WS285.genomic.fa.gz",
            "md5": "1234567890abcdef1234567890abcdef",
            "blast_title": "C. elegans Genomic Sequences (WS285)",
            "taxonomy": "6239",
            "seqtype": "nucl",
            "gbrowse_moby": {
                "data_source": "wormbase",
                "organism": "C. elegans"
            }
        },
        {
            "name": "Caenorhabditis_elegans_protein",
            "uri": "https://downloads.wormbase.org/releases/WS285/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.WS285.protein.fa.gz",
            "md5": "abcdef1234567890abcdef1234567890",
            "blast_title": "C. elegans Protein Sequences (WS285)",
            "taxonomy": "6239",
            "seqtype": "prot"
        },
        {
            "name": "Caenorhabditis_briggsae_genomic",
            "uri": "https://downloads.wormbase.org/releases/WS285/species/c_briggsae/PRJNA10731/c_briggsae.PRJNA10731.WS285.genomic.fa.gz",
            "md5": "fedcba0987654321fedcba0987654321",
            "blast_title": "C. briggsae Genomic Sequences (WS285)",
            "taxonomy": "6238",
            "seqtype": "nucl"
        }
    ]
}

SAMPLE_SGD_CONFIG = {
    "databases": [
        {
            "name": "Saccharomyces_cerevisiae_genomic",
            "uri": "https://downloads.yeastgenome.org/sequence/S288C_reference/genome_releases/S288C_reference_genome_Current_Release.tgz",
            "md5": "abc123def456abc123def456abc123de",
            "blast_title": "S. cerevisiae Genomic DNA",
            "taxonomy": "4932",
            "seqtype": "nucl",
            "gbrowse_moby": {
                "data_source": "sgd",
                "organism": "S. cerevisiae"
            }
        },
        {
            "name": "Saccharomyces_cerevisiae_protein",
            "uri": "https://downloads.yeastgenome.org/sequence/S288C_reference/orf_protein/orf_trans_all.fasta.gz",
            "md5": "def456abc123def456abc123def456ab",
            "blast_title": "S. cerevisiae Protein Sequences",
            "taxonomy": "4932",
            "seqtype": "prot"
        }
    ]
}

SAMPLE_ZFIN_CONFIG = {
    "databases": [
        {
            "name": "Danio_rerio_genomic",
            "uri": "https://download.zfin.org/downloads/danio_rerio.fa.gz",
            "md5": "zfin123456789abcdef123456789abcdef",
            "blast_title": "D. rerio Genomic Sequences",
            "taxonomy": "7955",
            "seqtype": "nucl"
        },
        {
            "name": "Danio_rerio_protein",
            "uri": "https://download.zfin.org/downloads/danio_rerio_proteins.fa.gz", 
            "md5": "zfin987654321fedcba987654321fedcb",
            "blast_title": "D. rerio Protein Sequences",
            "taxonomy": "7955",
            "seqtype": "prot"
        }
    ]
}

SAMPLE_UI_TEST_CONFIG = {
    "WB": {
        "nematode": {
            "items": [
                "Caenorhabditis_elegans_genomic",
                "Caenorhabditis_elegans_protein", 
                "Caenorhabditis_briggsae_genomic",
                "Caenorhabditis_briggsae_protein",
                "Brugia_malayi_genomic",
                "Brugia_malayi_protein"
            ],
            "nucl": "ATGCGATCGATCGATCGATCGATCGATCG",
            "prot": "MKLLIVDDSSGKVRAEIKQLLKQGVNPE"
        }
    },
    "SGD": {
        "fungal": {
            "items": [
                "Saccharomyces_cerevisiae_genomic",
                "Saccharomyces_cerevisiae_protein",
                "Candida_albicans_genomic",
                "Candida_albicans_protein"
            ],
            "nucl": "ATGAAAAAACTTATTTACCGCCCCCTGGAAA",
            "prot": "MKKLTYPPLEWDNKYKDWIRKLVV"
        }
    },
    "FB": {
        "insect": {
            "items": [
                "Drosophila_melanogaster_genomic",
                "Drosophila_melanogaster_protein",
                "Drosophila_simulans_genomic",
                "Drosophila_simulans_protein"
            ],
            "nucl": "CATATGAAGCTGCTGATTGTGGATGAC",
            "prot": "HMKLLIDDFGVKLKKEGDYVRK"
        }
    }
}

SAMPLE_LOAD_TEST_CONFIG = {
    "sequences": {
        "short_nucl": "ATGCGATCGATCG",
        "medium_nucl": "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "long_nucl": "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG" * 10,
        "short_prot": "MKLLIVDD",
        "medium_prot": "MKLLIVDDSSGKVRAEIKQLLKQGVNPE",
        "long_prot": "MKLLIVDDSSGKVRAEIKQLLKQGVNPEMKLLIVDDSSGKVRAEIKQLLKQGVNPE" * 5
    },
    "databases": {
        "WB": ["Caenorhabditis_elegans_genomic", "Caenorhabditis_elegans_protein"],
        "SGD": ["Saccharomyces_cerevisiae_genomic", "Saccharomyces_cerevisiae_protein"],
        "FB": ["Drosophila_melanogaster_genomic", "Drosophila_melanogaster_protein"]
    }
}

ERROR_SCENARIOS = {
    "invalid_config": {
        "missing_databases_key": {
            "invalid": "config without databases key"
        },
        "empty_databases": {
            "databases": []
        },
        "missing_required_fields": {
            "databases": [
                {
                    "name": "incomplete_db"
                    # Missing uri, md5, seqtype, etc.
                }
            ]
        }
    },
    "network_errors": {
        "connection_timeout": "Connection timeout during download",
        "dns_failure": "DNS resolution failed",
        "server_error": "HTTP 500 Internal Server Error",
        "not_found": "HTTP 404 File Not Found"
    },
    "validation_errors": {
        "md5_mismatch": "MD5 hash verification failed",
        "invalid_fasta": "File is not valid FASTA format",
        "empty_file": "Downloaded file is empty",
        "corrupted_archive": "Archive file is corrupted"
    },
    "makeblastdb_errors": {
        "invalid_sequence_type": "Invalid sequence type specified",
        "insufficient_disk_space": "Insufficient disk space",
        "permission_denied": "Permission denied creating database files",
        "invalid_fasta_headers": "FASTA headers contain invalid characters"
    }
}

PERFORMANCE_TEST_DATA = {
    "small_dataset": {
        "sequence_count": 100,
        "avg_sequence_length": 500,
        "expected_time_seconds": 5
    },
    "medium_dataset": {
        "sequence_count": 10000,
        "avg_sequence_length": 1000,
        "expected_time_seconds": 30
    },
    "large_dataset": {
        "sequence_count": 100000,
        "avg_sequence_length": 2000,
        "expected_time_seconds": 300
    },
    "genome_dataset": {
        "sequence_count": 1000000,
        "avg_sequence_length": 5000,
        "expected_time_seconds": 1800
    }
}