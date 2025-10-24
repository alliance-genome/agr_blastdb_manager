#!/bin/bash
# CLI BLAST Database Testing Script
# Tests SGD (R64-5-1f, R64-5-1m) and RGD (rgdtest) databases

set -e

BASE_DIR="../data/blast"
TEST_DIR="/tmp/blast_tests"
mkdir -p $TEST_DIR

echo "========================================="
echo "BLAST Database CLI Testing"
echo "========================================="

# Create test sequences
cat > $TEST_DIR/test_nucl.fasta << 'EOF'
>test_nucleotide_query
ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC
EOF

cat > $TEST_DIR/test_prot.fasta << 'EOF'
>test_protein_query
MKLLIVDDSSGKVRAEIKQLLKQGVNPE
EOF

# Test function
test_database() {
    local db_path=$1
    local db_type=$2
    local mod=$3
    local env=$4

    echo ""
    echo "Testing: $mod/$env"
    echo "Database: $(basename $db_path)"
    echo "Type: $db_type"
    echo "---"

    # Get database info
    if blastdbcmd -db "$db_path" -info 2>&1 | head -5; then
        echo "✓ Database is readable"

        # Run a simple BLAST query
        if [ "$db_type" == "nucl" ]; then
            if blastn -query $TEST_DIR/test_nucl.fasta -db "$db_path" -max_target_seqs 1 -outfmt 6 > /dev/null 2>&1; then
                echo "✓ blastn query successful"
            else
                echo "✗ blastn query failed"
            fi
        else
            if blastp -query $TEST_DIR/test_prot.fasta -db "$db_path" -max_target_seqs 1 -outfmt 6 > /dev/null 2>&1; then
                echo "✓ blastp query successful"
            else
                echo "✗ blastp query failed"
            fi
        fi
    else
        echo "✗ Database is not readable"
        return 1
    fi
}

# Test SGD R64-5-1f
echo ""
echo "========================================="
echo "SGD R64-5-1f Databases"
echo "========================================="

# Test nucleotide database
test_database \
    "$BASE_DIR/SGD/R64-5-1f/databases/Hypocreales_Entomopathogens/A_muscarius_Genome_Assembly/akanthomyces_muscarius_genomicdb" \
    "nucl" \
    "SGD" \
    "R64-5-1f"

# Test protein database
test_database \
    "$BASE_DIR/SGD/R64-5-1f/databases/Hypocreales_Entomopathogens/A_muscarius_Protein_Sequences/akanthomyces_muscarius_proteindb" \
    "prot" \
    "SGD" \
    "R64-5-1f"

# Test SGD R64-5-1m
echo ""
echo "========================================="
echo "SGD R64-5-1m Databases"
echo "========================================="

# Find first nucleotide database in R64-5-1m
SGD_M_NUCL=$(find $BASE_DIR/SGD/R64-5-1m/databases -name "*.nhr" | head -1 | sed 's/\.nhr$//')
if [ -n "$SGD_M_NUCL" ]; then
    test_database "$SGD_M_NUCL" "nucl" "SGD" "R64-5-1m"
else
    echo "No nucleotide databases found in R64-5-1m"
fi

# Find first protein database in R64-5-1m
SGD_M_PROT=$(find $BASE_DIR/SGD/R64-5-1m/databases -name "*.phr" | head -1 | sed 's/\.phr$//')
if [ -n "$SGD_M_PROT" ]; then
    test_database "$SGD_M_PROT" "prot" "SGD" "R64-5-1m"
else
    echo "No protein databases found in R64-5-1m"
fi

# Test RGD rgdtest
echo ""
echo "========================================="
echo "RGD rgdtest Databases"
echo "========================================="

test_database \
    "$BASE_DIR/RGD/rgdtest/databases/Rattus/norvegicus/GRCr8/GCF_036323735db" \
    "nucl" \
    "RGD" \
    "rgdtest"

echo ""
echo "========================================="
echo "Testing Complete!"
echo "========================================="

# Cleanup
rm -rf $TEST_DIR
