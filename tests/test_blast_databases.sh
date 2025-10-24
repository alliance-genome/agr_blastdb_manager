#!/bin/bash
# Agnostic BLAST Database Testing Script
# Auto-discovers and tests all MOD databases in ../data/blast/
# Generates a comprehensive markdown report

set -e

BASE_DIR="../data/blast"
RESULTS_DIR="blast_test_results"
REPORT_FILE="$RESULTS_DIR/TEST_REPORT.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Create results directory
mkdir -p "$RESULTS_DIR"

# Create test sequences
cat > "$RESULTS_DIR/test_nucl.fasta" << 'EOF'
>test_nucleotide_query
ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC
EOF

cat > "$RESULTS_DIR/test_prot.fasta" << 'EOF'
>test_protein_query
MKLLIVDDSSGKVRAEIKQLLKQGVNPE
EOF

# Initialize report
cat > "$REPORT_FILE" << EOF
# BLAST Database Test Report

**Generated:** $TIMESTAMP

## Test Overview

This report contains automated test results for all BLAST databases created by the AGR BLAST Database Manager pipeline.

### Test Methodology

- **Test Sequences:** Generic nucleotide (60bp) and protein (28aa) sequences
- **BLAST Tools:** blastn for nucleotide, blastp for protein databases
- **Output Format:** Tabular format with detailed alignment metrics
- **Success Criteria:** Database is readable and queryable (hits not required)

---

## Test Results

EOF

# Track statistics
total_tests=0
successful_tests=0
failed_tests=0

# Test function
test_database() {
    local db_path=$1
    local db_type=$2
    local mod=$3
    local env=$4
    local db_name=$(basename "$db_path" | sed 's/db$//')

    total_tests=$((total_tests + 1))

    echo "Testing: $mod/$env - $db_name ($db_type)"

    # Get database info
    local db_info=$(blastdbcmd -db "$db_path" -info 2>&1 | head -5)

    if [ $? -ne 0 ]; then
        failed_tests=$((failed_tests + 1))
        echo "  ✗ Database not readable"

        cat >> "$REPORT_FILE" << EOF
### ✗ $mod / $env - $db_name ($db_type)

**Status:** FAILED - Database not readable

\`\`\`
$db_info
\`\`\`

EOF
        return 1
    fi

    # Extract database stats
    local seq_count=$(echo "$db_info" | grep -oP '\d+(?= sequences)' | head -1)
    local total_bases=$(echo "$db_info" | grep -oP '[\d,]+(?= total (bases|residues))' | head -1)

    # Run BLAST query
    local blast_output
    local blast_result=0

    if [ "$db_type" == "nucl" ]; then
        blast_output=$(blastn -query "$RESULTS_DIR/test_nucl.fasta" -db "$db_path" \
            -max_target_seqs 5 -outfmt "7" 2>&1)
        blast_result=$?
    else
        blast_output=$(blastp -query "$RESULTS_DIR/test_prot.fasta" -db "$db_path" \
            -max_target_seqs 5 -outfmt "7" 2>&1)
        blast_result=$?
    fi

    if [ $blast_result -ne 0 ]; then
        failed_tests=$((failed_tests + 1))
        echo "  ✗ BLAST query failed"

        cat >> "$REPORT_FILE" << EOF
### ✗ $mod / $env - $db_name ($db_type)

**Status:** FAILED - BLAST query error

**Database Info:**
- Sequences: $seq_count
- Total bases/residues: $total_bases

**Error:**
\`\`\`
$blast_output
\`\`\`

EOF
        return 1
    fi

    successful_tests=$((successful_tests + 1))

    # Count hits
    local hits=$(echo "$blast_output" | grep "# .* hits found" | grep -oP '\d+')

    echo "  ✓ Database readable and queryable"
    echo "  ✓ Sequences: $seq_count, Bases/Residues: $total_bases, Hits: $hits"

    cat >> "$REPORT_FILE" << EOF
### ✓ $mod / $env - $db_name ($db_type)

**Status:** PASSED

**Database Info:**
- Sequences: $seq_count
- Total bases/residues: $total_bases
- Test query hits: $hits

**Database Path:** \`$db_path\`

EOF
}

echo "========================================="
echo "BLAST Database Auto-Discovery Testing"
echo "========================================="
echo ""

# Auto-discover all MODs and environments
for mod_dir in "$BASE_DIR"/*; do
    if [ ! -d "$mod_dir" ]; then
        continue
    fi

    mod_name=$(basename "$mod_dir")

    echo ""
    echo "MOD: $mod_name"
    echo "---"

    cat >> "$REPORT_FILE" << EOF

## $mod_name

EOF

    for env_dir in "$mod_dir"/*; do
        if [ ! -d "$env_dir" ]; then
            continue
        fi

        env_name=$(basename "$env_dir")
        databases_dir="$env_dir/databases"

        if [ ! -d "$databases_dir" ]; then
            echo "  No databases directory in $env_name"
            continue
        fi

        echo "  Environment: $env_name"

        # Find and test nucleotide databases
        nucl_dbs=$(find "$databases_dir" -name "*.nhr" 2>/dev/null | sed 's/\.nhr$//' || true)
        for db in $nucl_dbs; do
            test_database "$db" "nucl" "$mod_name" "$env_name"
        done

        # Find and test protein databases
        prot_dbs=$(find "$databases_dir" -name "*.phr" 2>/dev/null | sed 's/\.phr$//' || true)
        for db in $prot_dbs; do
            test_database "$db" "prot" "$mod_name" "$env_name"
        done
    done
done

# Add summary to report
cat >> "$REPORT_FILE" << EOF

---

## Summary Statistics

- **Total Tests:** $total_tests
- **Successful:** $successful_tests ($(awk "BEGIN {printf \"%.1f\", ($successful_tests/$total_tests)*100}")%)
- **Failed:** $failed_tests ($(awk "BEGIN {printf \"%.1f\", ($failed_tests/$total_tests)*100}")%)

---

## System Information

- **BLAST Version:** $(blastn -version | head -1)
- **Test Date:** $TIMESTAMP
- **Test Script:** tests/test_blast_databases.sh

EOF

echo ""
echo "========================================="
echo "Testing Complete!"
echo "========================================="
echo ""
echo "Total Tests: $total_tests"
echo "Successful:  $successful_tests"
echo "Failed:      $failed_tests"
echo ""
echo "Report saved to: $REPORT_FILE"
