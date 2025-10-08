# Product Requirements Document: Database Validation Integration

**Document Version:** 1.0
**Date:** 2025-10-07
**Status:** Draft for Review
**Owner:** Engineering Team
**Stakeholders:** QA, DevOps, Product Management

---

## 1. Context & Why Now

- **Quality Assurance Gap:** Currently, BLAST databases are created without automated post-creation validation, leading to potential deployment of non-functional databases to production
- **Manual Verification Overhead:** QA engineers manually test databases using sample sequences, a time-consuming and error-prone process that doesn't scale across 6 MODs and multiple environments
- **Production Reliability Risk:** Invalid databases reaching production (`/var/sequenceserver-data/`) can cause service disruptions and incorrect search results for research users
- **Existing Solution Available:** The `improved-error-reporting` branch contains a proven validation framework with 8 conserved sequences and MOD-specific test sequences, ready for integration
- **Deployment Velocity:** As AGR expands database coverage and update frequency increases, automated validation becomes critical to maintain deployment confidence

---

## 2. Users & Jobs to Be Done (JTBD)

### Primary Users

**DevOps Engineers**
- As a DevOps engineer, I need to verify database integrity before production deployment so that I can prevent service disruptions
- As a DevOps engineer, I need automated validation reports so that I can quickly diagnose database creation failures

**QA Engineers**
- As a QA engineer, I need automated database validation so that I can reduce manual testing time and increase coverage
- As a QA engineer, I need detailed hit rate reports so that I can identify potential data quality issues before production

**Pipeline Developers**
- As a developer, I need validation to run as an optional CLI step so that I can test databases during development
- As a developer, I need validation logs integrated with existing logging so that I can trace issues through the full pipeline

### Secondary Users

**Production Operators**
- As a production operator, I need confidence that deployed databases are functional so that I can maintain SLA commitments
- As a production operator, I need validation failure alerts in Slack so that I can respond quickly to issues

**Research Scientists (Indirect)**
- As a research scientist, I need reliable BLAST results so that I can trust the data for my publications

---

## 3. Business Goals & Success Metrics

### Business Goals

1. **Reduce Production Incidents:** Eliminate database-related BLAST search failures by catching issues before production deployment
2. **Accelerate QA Cycle:** Reduce manual database testing time by 80% through automation
3. **Improve Deployment Confidence:** Provide quantitative validation metrics for go/no-go deployment decisions
4. **Scale Database Coverage:** Enable validation of increasing database counts without proportional QA resource increase
5. **Enhance Observability:** Provide actionable validation metrics for continuous improvement

### Leading Indicators (Early Signals)

- Validation feature adoption rate: Target 80% of pipeline runs use `--validate` flag within 30 days
- Time to validate: Average validation time under 5 minutes for typical database sets
- Validation test coverage: 100% of deployed databases tested with both conserved and MOD-specific sequences
- Developer feedback: Positive developer survey responses on validation usefulness

### Lagging Indicators (Ultimate Success Measures)

- **Production database failures:** Reduce from current baseline to zero database-related incidents within 90 days
- **QA manual testing time:** Reduce from estimated 2 hours per MOD release to 15 minutes (validation review only)
- **Time to deployment:** Reduce database release cycle by 30% through faster validation
- **Database quality score:** Achieve >95% hit rate across all conserved sequence tests within 60 days

---

## 4. Functional Requirements

### FR1: CLI Validation Flag
**Description:** Add optional `--validate` flag to main CLI to trigger post-creation validation
**Acceptance Criteria:**
- `--validate` flag is mutually exclusive with `--check-parse-seqids` (validation requires actual databases)
- Flag is compatible with both `-g` (YAML) and `-j` (JSON) input modes
- Validation runs only after successful database creation
- Help text clearly explains validation purpose and timing

### FR2: Automated Sequence Discovery
**Description:** Automatically detect and validate all databases created in current pipeline run
**Acceptance Criteria:**
- System identifies all databases created in `../data/blast/{MOD}/{environment}/databases/`
- Both nucleotide and protein databases are discovered and tested appropriately
- Database type (blastn vs blastp) is auto-detected based on file extensions or content
- No manual configuration required for standard database structures

### FR3: Conserved Sequence Testing
**Description:** Test all databases against 8 highly conserved biological sequences
**Acceptance Criteria:**
- Tests include: 18S rRNA, 28S rRNA, COI mitochondrial, actin, GAPDH, U6 snRNA, histone H3, EF-1α
- Each sequence is tested against every discovered database
- E-value threshold is configurable with default of 10 (relaxed for validation)
- Word size is configurable with default of 7 for better sensitivity
- Hit counts and best identity percentages are tracked per sequence

### FR4: MOD-Specific Sequence Testing
**Description:** Test databases with organism-specific reference sequences
**Acceptance Criteria:**
- MOD-specific sequences for FB (white, rosy), WB (unc-22, dpy-10), SGD (GAL1, ACT1), ZFIN (pax2a, shh), RGD (Alb, Ins1), XB (sox2, bmp4)
- Sequences automatically matched to correct MOD based on database path
- Separate hit counts tracked for conserved vs MOD-specific sequences
- Handles cases where MOD-specific sequences are not available

### FR5: Validation Reporting
**Description:** Generate comprehensive validation report with hit rates and diagnostics
**Acceptance Criteria:**
- Terminal output shows: Total databases tested, databases with conserved hits, databases with MOD-specific hits, overall hit rate
- Per-MOD breakdown of validation results with percentages
- Top 3-5 best-performing databases listed with hit counts
- Databases with zero hits listed for investigation (limited to 5 for readability)
- Performance metrics: total validation time, average time per database

### FR6: Failure Diagnostics
**Description:** Provide actionable diagnostics for low hit rates or validation failures
**Acceptance Criteria:**
- Warning displayed if overall hit rate <50%
- Diagnostic suggestions include: specialized database types, indexing issues, alternative BLAST programs needed
- Individual database failures show: database name, sequences tested, BLAST command used, error messages if any
- Timeout handling with clear error messages (default 30s per BLAST query)

### FR7: Slack Integration
**Description:** Send validation summary to Slack channel when `--update-slack` flag is used
**Acceptance Criteria:**
- Validation results included in existing Slack batch messaging system
- Summary includes: total databases, hit rates, top performers, failures
- Color-coded: green for >80% hit rate, yellow for 50-80%, red for <50%
- Respects existing 20-message batch limit
- Only sent when both `--validate` and `--update-slack` flags are present

### FR8: Logging Integration
**Description:** Integrate validation logging with existing pipeline logging infrastructure
**Acceptance Criteria:**
- Validation events logged to run-specific log file: `blast_db_{MOD}_{environment}_{timestamp}.log`
- Log entries include: sequences tested, BLAST commands executed, hit counts, error details
- Log level follows existing conventions (INFO for normal operation, WARNING for low hits, ERROR for failures)
- Validation section clearly demarcated in log file with headers

### FR9: Configuration Options
**Description:** Allow configuration of validation parameters via CLI or config file
**Acceptance Criteria:**
- E-value threshold configurable via CLI flag (e.g., `--validation-evalue 10`)
- Word size configurable via CLI flag (e.g., `--validation-word-size 7`)
- Option to skip conserved sequence tests (`--skip-conserved-validation`)
- Option to skip MOD-specific tests (`--skip-mod-validation`)
- Timeout per BLAST query configurable (default 30s)

### FR10: Performance Optimization
**Description:** Ensure validation completes efficiently without blocking pipeline
**Acceptance Criteria:**
- Validation runs in parallel across multiple databases (configurable thread count)
- Temporary query files cleaned up after validation
- Maximum 2 threads per BLAST query to balance speed and resource usage
- Total validation time for typical MOD (10-20 databases) under 5 minutes
- Memory usage remains under 500MB for validation process

---

## 5. Non-Functional Requirements

### Performance
- **Validation Speed:** Complete validation of 50 databases in under 10 minutes
- **BLAST Query Time:** Individual BLAST queries timeout after 30 seconds (configurable)
- **Parallel Processing:** Support up to 4 concurrent database validations
- **Resource Efficiency:** Validation adds <10% to total pipeline runtime

### Scale
- **Database Count:** Support validation of 500+ databases per pipeline run
- **Sequence Count:** Support testing with 20+ test sequences (conserved + MOD-specific)
- **Concurrent Runs:** Multiple pipeline instances can validate simultaneously without conflicts

### SLOs/SLAs
- **Validation Availability:** 99.9% success rate for validation process itself (excluding database issues)
- **False Positive Rate:** <1% incorrect validation failures (flagging good databases as bad)
- **False Negative Rate:** <0.1% missed issues (passing bad databases)

### Privacy
- **Data Handling:** Test sequences contain only public reference sequence data
- **Log Sanitization:** No sensitive credentials or API keys in validation logs
- **Temporary Files:** All query FASTA files written to `/tmp` with automatic cleanup

### Security
- **File Permissions:** Temporary query files have restrictive permissions (600)
- **BLAST Command Injection:** All BLAST parameters properly escaped and validated
- **Path Traversal:** Database paths validated to prevent directory traversal attacks

### Observability
- **Logging:** All validation steps logged with INFO level detail
- **Metrics:** Hit rates, timing, and success rates exported to logs
- **Alerting:** Slack notifications include actionable failure information
- **Debugging:** Verbose mode (`--verbose`) provides enhanced diagnostic output including BLAST commands and raw output

---

## 6. Scope Definition

### In Scope

- Integration of validation test suite from `improved-error-reporting` branch into main CLI
- CLI flag (`--validate`) to trigger optional post-creation validation
- Automated discovery of all databases created in current pipeline run
- Testing with 8 conserved sequences across all organisms
- Testing with MOD-specific sequences (FB, WB, SGD, ZFIN, RGD, XB)
- Comprehensive terminal reporting with Rich library integration
- Slack notification integration for validation results
- Detailed logging of validation process and results
- Performance optimization for validation speed
- Configuration options for e-value, word size, timeouts
- Documentation: user guide, troubleshooting section, example usage

### Out of Scope (Explicitly)

- **Automatic remediation:** System will report issues but not automatically fix databases
- **Historical database validation:** Only validates databases created in current run, not existing production databases (can be addressed in future with separate tool)
- **Custom sequence upload:** Users cannot upload their own test sequences (uses predefined conserved and MOD-specific sequences only)
- **Web UI for validation:** Remains CLI-only feature (UI may be added in future phase)
- **Real-time validation:** Validation runs post-creation, not during database building
- **Integration with CI/CD:** Direct CI/CD integration deferred to Phase 2
- **Database performance benchmarking:** Validation tests correctness only, not query performance
- **Comparison with previous runs:** No historical trending of validation metrics (future enhancement)

### Future Considerations (Potential Phase 2+)

- **Historical validation tool:** Standalone script to validate all production databases on-demand
- **Validation trending dashboard:** Web UI showing validation metrics over time
- **Custom sequence management:** Allow users to define and manage their own test sequences
- **CI/CD integration:** Automatic validation on PR creation and merge
- **Performance benchmarking:** Add query performance testing to validation suite
- **Auto-remediation suggestions:** Provide specific fix recommendations for common failures
- **Cross-MOD validation:** Test MOD databases against other MOD sequences to verify isolation

---

## 7. Rollout Plan

### Phase 1: Core Integration (Weeks 1-2)

**Milestone 1.1: Foundation Setup**
- Integrate validation sequence library from `improved-error-reporting` branch
- Create validation module in `src/validation.py` with core testing logic
- Add CLI flag `--validate` to `create_blast_db.py`
- Success gate: Validation runs and reports results (even if formatting is basic)

**Milestone 1.2: Reporting & Logging**
- Integrate with Rich library for terminal output formatting
- Add validation events to existing logging infrastructure
- Implement per-MOD result aggregation and reporting
- Success gate: Clean, readable validation reports in terminal and logs

**Guardrails:**
- Validation must be optional (flag-based) to avoid breaking existing workflows
- If validation fails (bugs), pipeline continues without blocking database creation
- All temporary files cleaned up even if validation crashes

### Phase 2: Integration & Polish (Weeks 3-4)

**Milestone 2.1: Slack & Configuration**
- Integrate validation results into Slack notification system
- Add configuration flags for e-value, word size, timeouts
- Implement performance optimizations (parallel processing)
- Success gate: Full validation completes in <5 minutes for 20 databases

**Milestone 2.2: Testing & Documentation**
- Comprehensive unit tests for validation logic
- Integration tests with mock databases
- User documentation with examples
- Troubleshooting guide for common validation failures
- Success gate: >90% test coverage for validation module, documentation complete

**Guardrails:**
- Slack messages respect 20-attachment batch limit
- Configuration defaults match proven values from standalone test script
- Performance testing shows <10% pipeline overhead

### Phase 3: Production Rollout (Weeks 5-6)

**Milestone 3.1: Staged Deployment**
- Week 5: Deploy to dev environment, monitor all pipeline runs with `--validate`
- Week 6: Deploy to staging, require `--validate` for all staging deployments
- Success gate: Zero validation-related pipeline failures in dev/staging

**Milestone 3.2: Production Enablement**
- Production deployment with optional flag
- Team training on interpreting validation results
- Runbook for responding to validation failures
- Success gate: 80% of production pipelines use `--validate` within 2 weeks

**Guardrails:**
- Validation failures do not block production deployments (warnings only)
- Monitoring for validation false positives/negatives
- Rollback plan if validation causes pipeline instability

### Kill-Switch Criteria

Immediately disable validation feature if:
- **Pipeline Breakage:** Validation causes >5% of pipeline runs to fail
- **Performance Degradation:** Validation adds >20% to pipeline runtime
- **Resource Exhaustion:** Validation consumes >1GB memory or causes system instability
- **False Positive Rate:** >10% of databases incorrectly flagged as failures
- **Data Corruption:** Any evidence of validation process modifying databases

### Success Gates Between Phases

**Phase 1 → Phase 2:**
- Core validation runs successfully on all 6 MODs
- Terminal output is clear and actionable
- Zero pipeline disruptions in dev testing

**Phase 2 → Phase 3:**
- All configuration options working correctly
- Performance targets met (<5 min for 20 databases)
- Documentation approved by QA and DevOps teams
- Test coverage >90%

**Phase 3 Complete:**
- Production deployment stable for 2 weeks
- >80% adoption rate among pipeline runs
- Zero production incidents attributed to validation
- Positive feedback from QA and DevOps teams

---

## 8. Risks & Open Questions

### Technical Risks

**Risk T1: BLAST Performance Variability**
- **Impact:** High - Could cause timeouts or slow pipelines
- **Likelihood:** Medium
- **Mitigation:** Configurable timeouts, parallel processing, relaxed e-value defaults
- **Monitoring:** Track validation time per database, alert if >2 min per database

**Risk T2: Database Type Detection Failures**
- **Impact:** Medium - Could run blastn on protein databases or vice versa
- **Likelihood:** Low
- **Mitigation:** Robust detection logic based on file extensions and database structure, fallback to nucleotide default
- **Monitoring:** Log all type detection decisions, alert on detection failures

**Risk T3: Sequence Library Maintenance**
- **Impact:** Medium - Test sequences may become outdated or MOD-specific
- **Likelihood:** Low (sequences are highly conserved)
- **Mitigation:** Version test sequences, document sequence sources, periodic review process
- **Monitoring:** Track hit rate trends, investigate sudden drops

**Risk T4: Integration with Existing Logging**
- **Impact:** Low - Log files could become cluttered or validation events missed
- **Likelihood:** Low
- **Mitigation:** Clear log section demarcation, follow existing log format conventions
- **Monitoring:** Review log readability in QA, adjust formatting as needed

### Business/Operational Risks

**Risk B1: False Sense of Security**
- **Impact:** High - Teams may rely solely on validation, missing other database issues
- **Likelihood:** Medium
- **Mitigation:** Clear documentation that validation is one signal, not comprehensive QA; maintain some manual testing
- **Monitoring:** Track production incidents, ensure validation doesn't create blind spots

**Risk B2: Adoption Resistance**
- **Impact:** Medium - Teams may not use `--validate` flag, reducing value
- **Likelihood:** Medium
- **Mitigation:** Make validation easy to use, show clear value in reports, consider making default-on in future
- **Monitoring:** Track flag usage, gather user feedback, adjust UX as needed

**Risk B3: Alert Fatigue**
- **Impact:** Medium - Too many Slack validation notifications could desensitize team
- **Likelihood:** Medium
- **Mitigation:** Smart alerting (only on failures or low hit rates), batched messages, configurable notification levels
- **Monitoring:** Track Slack message volume, alert suppression if >10/day per channel

### Open Questions Requiring Further Investigation

**Q1: Should validation be enabled by default in production?**
- **Context:** Currently scoped as optional flag; could make default-on with opt-out flag
- **Consideration:** Balance deployment safety vs. pipeline complexity
- **Decision Needed By:** End of Phase 2 (before production rollout)
- **Owners:** Product Management + DevOps

**Q2: What hit rate threshold indicates a database should not be deployed?**
- **Context:** Currently reporting only; should we enforce minimum hit rates?
- **Consideration:** Different database types (protein-only, ncRNA) may have legitimate low hit rates
- **Decision Needed By:** End of Phase 2
- **Owners:** QA + Science Team

**Q3: Should we validate databases copied to production location vs. source location?**
- **Context:** Currently validates source databases; could validate production copy to verify transfer integrity
- **Consideration:** Adds time but catches copy corruption issues
- **Decision Needed By:** Mid Phase 2 (design decision)
- **Owners:** DevOps + Engineering

**Q4: How do we handle specialized databases (protein-only, ncRNA-only)?**
- **Context:** These may legitimately fail conserved nucleotide sequence tests
- **Consideration:** May need database metadata to indicate expected sequence types
- **Decision Needed By:** Mid Phase 2 (impacts diagnostic logic)
- **Owners:** QA + Engineering

**Q5: Should validation results influence production copy confirmation prompt?**
- **Context:** Currently separate; could show validation summary before "copy to production" confirmation
- **Consideration:** Better UX but increases coupling between features
- **Decision Needed By:** Late Phase 2
- **Owners:** Product + Engineering

**Q6: Do we need validation result storage/history?**
- **Context:** Currently logs only; no structured storage for trending
- **Consideration:** Useful for quality trends but adds complexity
- **Decision Needed By:** Phase 3 planning (consider for future)
- **Owners:** Product Management

**Q7: Should timeout values vary by MOD or database size?**
- **Context:** Currently fixed 30s timeout; large databases may need more time
- **Consideration:** Could auto-adjust based on database file size
- **Decision Needed By:** Mid Phase 2 (performance optimization)
- **Owners:** Engineering

**Q8: How do we validate databases that use specialized BLAST variants (tblastx, etc.)?**
- **Context:** Currently supports blastn and blastp only
- **Consideration:** Some databases may require translated search
- **Decision Needed By:** Phase 3 (scope expansion)
- **Owners:** Science Team + Engineering

---

## 9. Dependencies

### Internal Dependencies

- **Rich Library Integration:** Validation reporting requires Rich for formatted terminal output (already in project)
- **Logging Infrastructure:** Uses existing `extendable_logger` and run-specific log files from `utils.py`
- **Slack SDK Integration:** Leverages existing Slack messaging infrastructure from `utils.py`
- **BLAST Tools:** Requires makeblastdb and BLAST+ suite already installed for pipeline
- **Database Creation Pipeline:** Validation runs only after successful database creation

### External Dependencies

- **NCBI BLAST+ Suite:** blastn, blastp commands must be in PATH
- **File System Access:** Read access to `../data/blast/{MOD}/{environment}/databases/`
- **Temporary Directory:** Write access to `/tmp` for query FASTA files
- **Network (Optional):** Only needed if Slack notifications enabled

### Team Dependencies

- **QA Team:** Define acceptable hit rate thresholds and validation criteria
- **Science Team:** Review and approve test sequence library for biological relevance
- **DevOps Team:** Define production validation requirements and deployment approval process
- **Documentation Team:** Create user guide and troubleshooting documentation

---

## 10. Technical Architecture

### Module Structure

```
src/
├── create_blast_db.py          # Main CLI - add --validate flag
├── validation.py               # NEW: Core validation logic
│   ├── ConservedSequences      # Sequence library management
│   ├── DatabaseValidator       # Validation orchestration
│   ├── ValidationReporter      # Result aggregation and reporting
│   └── BlastRunner             # BLAST execution wrapper
├── utils.py                    # Existing utilities (logging, Slack)
└── terminal.py                 # Existing terminal output (Rich)

tests/
└── unit/
    └── test_validation.py      # NEW: Validation unit tests
```

### Data Flow

1. **Database Creation:** Pipeline creates databases in `../data/blast/{MOD}/{environment}/databases/`
2. **Validation Trigger:** If `--validate` flag present, validation initiates after successful creation
3. **Database Discovery:** Scan created directories for `.nin` (nucleotide) and `.pin` (protein) files
4. **Sequence Testing:**
   - Load conserved sequences (8 universal)
   - Load MOD-specific sequences (2-3 per MOD)
   - For each database: determine type (blastn/blastp), execute BLAST queries, collect hits
5. **Result Aggregation:** Combine results per MOD, calculate hit rates, identify top/bottom performers
6. **Reporting:**
   - Terminal: Rich-formatted summary with tables
   - Logs: Detailed validation events in run-specific log
   - Slack: Summary message if `--update-slack` enabled
7. **Cleanup:** Remove temporary query files from `/tmp`

### Integration Points

**CLI Integration (`create_blast_db.py`):**
```python
@click.option('--validate', help='Validate databases after creation', is_flag=True, default=False)
def create_dbs(..., validate: bool):
    # ... existing database creation logic ...

    if validate and not check_parse_seqids:
        from validation import DatabaseValidator
        validator = DatabaseValidator(mod_code, environment, LOGGER)
        results = validator.validate_all()

        # Report results
        from terminal import show_validation_summary
        show_validation_summary(results)

        # Send to Slack if requested
        if update_slack:
            SLACK_MESSAGES.append(validator.format_slack_message(results))
```

**Validation Module (`validation.py`):**
```python
class DatabaseValidator:
    def __init__(self, mod: str, environment: str, logger):
        self.mod = mod
        self.environment = environment
        self.logger = logger
        self.conserved_seqs = ConservedSequences.load()
        self.mod_specific_seqs = ModSpecificSequences.load(mod)

    def discover_databases(self) -> List[DatabaseInfo]:
        """Find all databases in current run output"""

    def validate_database(self, db_info: DatabaseInfo) -> ValidationResult:
        """Run BLAST queries against single database"""

    def validate_all(self) -> ValidationSummary:
        """Validate all discovered databases, return aggregated results"""
```

### Configuration Schema

```yaml
# Optional: Extended config in YAML for validation settings
validation:
  enabled: true
  evalue: 10
  word_size: 7
  timeout: 30
  max_threads: 4
  min_hit_rate_warning: 0.5
  sequences:
    conserved: auto  # Use built-in conserved sequences
    mod_specific: auto  # Use built-in MOD-specific sequences
```

---

## 11. User Experience & Interface Design

### CLI Usage Examples

**Basic Validation:**
```bash
# Validate databases after creation
uv run python src/create_blast_db.py -j conf/SGD/databases.SGD.dev.json -e dev --validate
```

**With Slack Notifications:**
```bash
# Validate and send results to Slack
uv run python src/create_blast_db.py -g conf/global.yaml --validate --update-slack
```

**Custom Validation Parameters:**
```bash
# Adjust e-value and timeout
uv run python src/create_blast_db.py -j conf/WB/databases.WB.prod.json -e prod \
  --validate --validation-evalue 1e-5 --validation-timeout 60
```

**Skip Specific Tests:**
```bash
# Only run MOD-specific validation
uv run python src/create_blast_db.py -j conf/FB/databases.FB.dev.json -e dev \
  --validate --skip-conserved-validation
```

### Terminal Output Design

**Validation Header:**
```
═══════════════════════════════════════════════════════════════════════
                   DATABASE VALIDATION REPORT
═══════════════════════════════════════════════════════════════════════

Testing 12 databases with:
  • 8 conserved sequences (18S rRNA, 28S rRNA, COI, actin, GAPDH, U6, H3, EF-1α)
  • 2 SGD-specific sequences (GAL1, ACT1)
  • E-value threshold: 10 (relaxed for validation)
  • Timeout per query: 30s
```

**Progress Display:**
```
→ Validating databases...
  ✓ [1/12] S_cerevisiae_genome_db (15 hits)
  ✓ [2/12] S_cerevisiae_CDS_db (23 hits)
  ! [3/12] S_cerevisiae_ncRNA_db (2 hits - low)
  ✓ [4/12] S_cerevisiae_protein_db (18 hits)
  ...
```

**Results Summary Table:**
```
╭─────────────────────── SGD Validation Results ────────────────────────╮
│ Metric                          │ Value                               │
├─────────────────────────────────┼─────────────────────────────────────┤
│ Total Databases                 │ 12                                  │
│ With Conserved Hits             │ 11/12 (91.7%)                       │
│ With MOD-Specific Hits          │ 10/12 (83.3%)                       │
│ Average Hit Rate                │ 87.5%                               │
│ Validation Time                 │ 3m 24s                              │
╰─────────────────────────────────┴─────────────────────────────────────╯

Top Performers:
  ✓ S_cerevisiae_CDS_db: 23 hits (conserved: 15, MOD-specific: 8)
  ✓ S_cerevisiae_genome_db: 21 hits (conserved: 14, MOD-specific: 7)
  ✓ S_cerevisiae_protein_db: 18 hits (conserved: 12, MOD-specific: 6)

Databases with Low Hits (Review Recommended):
  ! S_cerevisiae_ncRNA_db: 2 hits - May be specialized database (ncRNA-only)
  ! S_cerevisiae_tRNA_db: 1 hit - Consider specialized validation sequences
```

**Warning Messages:**
```
⚠️  WARNING: Overall hit rate (65.3%) below 80% threshold

    Possible reasons:
    • Databases may be specialized (protein-only, ncRNA-only, etc.)
    • Database indexing issues - verify makeblastdb completed successfully
    • Consider using translated BLAST (tblastx) for some databases
    • MOD-specific sequences may need updating for this organism

    Review individual database logs for details.
```

### Slack Message Format

**Success Message (>80% hit rate):**
```
🟢 Database Validation: SGD dev - PASSED

✅ Overall Results:
  • Total Databases: 12
  • Conserved Hit Rate: 91.7% (11/12)
  • MOD-Specific Hit Rate: 83.3% (10/12)
  • Validation Time: 3m 24s

📊 Top Performers:
  • S_cerevisiae_CDS_db: 23 hits
  • S_cerevisiae_genome_db: 21 hits
  • S_cerevisiae_protein_db: 18 hits

⚠️ Low Hit Databases:
  • S_cerevisiae_ncRNA_db: 2 hits (may be specialized)

Pipeline: Run #1847
Environment: dev
```

**Warning Message (50-80% hit rate):**
```
🟡 Database Validation: WB prod - WARNING

⚠️ Overall Results:
  • Total Databases: 18
  • Conserved Hit Rate: 66.7% (12/18)
  • MOD-Specific Hit Rate: 55.6% (10/18)
  • Validation Time: 5m 12s

❌ Databases with No Hits (6):
  • C_elegans_miRNA_db
  • C_elegans_piRNA_db
  • C_elegans_lncRNA_db
  • C_elegans_pseudogenes_db
  • C_elegans_repeats_db
  • C_elegans_transposons_db

💡 Recommendation: Review specialized databases before production deployment

Pipeline: Run #1848
Environment: prod
```

**Failure Message (<50% hit rate):**
```
🔴 Database Validation: FB stage - FAILED

❌ Overall Results:
  • Total Databases: 25
  • Conserved Hit Rate: 32.0% (8/25)
  • MOD-Specific Hit Rate: 28.0% (7/25)
  • Validation Time: 6m 47s

🚨 Critical Issues:
  • 17 databases with zero hits
  • Possible database corruption or indexing failure
  • Review pipeline logs immediately

📋 Action Required:
  1. Check makeblastdb logs for errors
  2. Verify FASTA file integrity
  3. Consider re-running pipeline
  4. DO NOT deploy to production

Pipeline: Run #1849
Environment: stage
```

---

## 12. Testing & Quality Assurance

### Unit Testing Requirements

**Validation Logic Tests:**
- Test conserved sequence loading and validation
- Test MOD-specific sequence matching
- Test database type detection (blastn vs blastp)
- Test BLAST command construction and parameter handling
- Test timeout and error handling
- Test result aggregation and hit rate calculation

**Integration Tests:**
- Test full validation flow with mock databases
- Test CLI flag integration
- Test Slack message formatting and batching
- Test logging integration
- Test cleanup of temporary files

**Performance Tests:**
- Validate 50 databases completes in <10 minutes
- Memory usage stays under 500MB
- Parallel processing scales correctly
- Timeout handling works as expected

### Test Coverage Targets

- **Validation Module:** >95% line coverage
- **Integration Points:** 100% coverage of CLI flag handling
- **Error Paths:** 100% coverage of timeout and BLAST failure scenarios
- **Overall:** >90% coverage for validation-related code

### QA Test Cases

**TC1: Happy Path Validation**
- **Given:** 10 valid databases created successfully
- **When:** `--validate` flag used
- **Then:** All databases tested, >80% hit rate, clean report

**TC2: Mixed Results Validation**
- **Given:** 10 databases with 5 specialized (ncRNA, repeats)
- **When:** `--validate` flag used
- **Then:** General databases have high hit rate, specialized databases flagged with warnings

**TC3: Validation Failure**
- **Given:** Corrupted databases created
- **When:** `--validate` flag used
- **Then:** Low hit rate detected, detailed diagnostics provided, Slack alert sent

**TC4: Performance Under Load**
- **Given:** 100 databases to validate
- **When:** `--validate` flag used
- **Then:** Validation completes in <15 minutes, no resource exhaustion

**TC5: Configuration Override**
- **Given:** Custom e-value and timeout specified
- **When:** `--validate --validation-evalue 1e-10 --validation-timeout 60` used
- **Then:** Validation uses custom parameters, shown in logs

**TC6: Partial Validation**
- **Given:** Skip conserved tests requested
- **When:** `--validate --skip-conserved-validation` used
- **Then:** Only MOD-specific tests run, report reflects this

---

## 13. Documentation Requirements

### User Documentation

**1. User Guide Section: "Database Validation"**
- Purpose and benefits of validation
- When to use `--validate` flag
- Interpreting validation reports
- Understanding hit rates and what they mean
- Configuration options and when to adjust them

**2. CLI Reference Update**
- Add `--validate` flag documentation
- Add `--validation-evalue` parameter
- Add `--validation-word-size` parameter
- Add `--validation-timeout` parameter
- Add `--skip-conserved-validation` flag
- Add `--skip-mod-validation` flag

**3. Troubleshooting Guide**
- "Low hit rate warnings" - what they mean and how to address
- "Validation timeouts" - causes and solutions
- "Specialized database validation" - handling protein-only, ncRNA databases
- "BLAST command failures" - debugging BLAST issues
- "False positives/negatives" - when validation may be incorrect

**4. Sequence Library Documentation**
- List of all conserved sequences with sources
- List of MOD-specific sequences with sources
- Rationale for sequence selection
- Process for updating/adding sequences
- Version history of sequence library

### Developer Documentation

**1. Architecture Documentation**
- Validation module design and data flow
- Integration points with existing pipeline
- Sequence library management
- Extension points for new MODs or sequences

**2. API Documentation**
- `DatabaseValidator` class API
- `ConservedSequences` class API
- `ValidationReporter` class API
- Helper functions and utilities

**3. Testing Documentation**
- How to run validation tests
- How to add new test sequences
- Mock database creation for testing
- Performance testing procedures

### Operational Documentation

**1. Runbook: "Responding to Validation Failures"**
- Step-by-step troubleshooting process
- When to re-run pipeline
- When to deploy despite low hit rates
- Escalation procedures for persistent failures

**2. Monitoring & Alerting Guide**
- Key validation metrics to monitor
- Alert thresholds and meanings
- Dashboard setup (if applicable)
- Log analysis procedures

**3. Deployment Guide**
- Phase-by-phase rollout instructions
- Feature flag configuration
- Rollback procedures
- Success criteria verification

---

## 14. Success Criteria & Acceptance

### Feature Complete Criteria

The database validation integration is considered **feature complete** when:

1. ✅ `--validate` flag implemented and functional in main CLI
2. ✅ All 8 conserved sequences tested against discovered databases
3. ✅ All 6 MODs have MOD-specific sequences tested (FB, WB, SGD, ZFIN, RGD, XB)
4. ✅ Auto-detection of database type (blastn vs blastp) works correctly
5. ✅ Terminal reporting integrated with Rich library formatting
6. ✅ Logging integrated with existing pipeline logs
7. ✅ Slack notifications integrated and respecting batch limits
8. ✅ Configuration options (e-value, timeout, word size) working
9. ✅ Temporary file cleanup verified
10. ✅ Performance targets met (<5 min for 20 databases)
11. ✅ Test coverage >90% for validation module
12. ✅ Documentation complete (user guide, troubleshooting, API docs)

### Production Ready Criteria

The feature is considered **production ready** when:

1. ✅ All feature complete criteria met
2. ✅ Zero critical bugs in dev/staging testing
3. ✅ Performance validated with real production-scale database sets
4. ✅ False positive rate verified <1% through manual QA
5. ✅ False negative rate verified <0.1% through deliberate database corruption tests
6. ✅ Slack integration tested with real webhook
7. ✅ Runbook and troubleshooting docs validated by DevOps team
8. ✅ Training completed for QA and DevOps teams
9. ✅ Monitoring/alerting configured and tested
10. ✅ Rollback plan documented and tested

### User Acceptance Criteria

**QA Team Acceptance:**
- ✅ Validation detects all deliberately corrupted test databases
- ✅ Reports are clear and actionable without engineering support
- ✅ Reduces manual testing time by measured >80%
- ✅ Integration with existing workflow is seamless

**DevOps Team Acceptance:**
- ✅ Validation does not increase pipeline failure rate
- ✅ Performance overhead is acceptable (<10%)
- ✅ Logs and Slack messages provide sufficient debug information
- ✅ Runbook enables self-service troubleshooting

**Development Team Acceptance:**
- ✅ Validation helps catch database issues during development
- ✅ CLI flags are intuitive and well-documented
- ✅ Code is maintainable and well-tested
- ✅ Adding new test sequences is straightforward

### Business Success Criteria (90 Days Post-Launch)

**Primary Metrics:**
- ✅ Zero production database failures attributed to issues validation would have caught
- ✅ QA manual testing time reduced from 2 hours to <15 minutes per MOD release
- ✅ 80%+ of production pipeline runs use `--validate` flag

**Secondary Metrics:**
- ✅ Database release cycle time reduced by 30%
- ✅ >95% average hit rate across all MODs for conserved sequences
- ✅ <5 false positive validation alerts per month
- ✅ Positive NPS score from QA and DevOps teams (>8/10)

---

## Appendix A: Test Sequence Library

### Conserved Sequences (Universal)

1. **18S rRNA** - Highly conserved across all eukaryotes, ribosomal RNA
2. **28S rRNA** - Another highly conserved ribosomal RNA sequence
3. **COI mitochondrial** - Cytochrome c oxidase subunit I, mitochondrial barcode
4. **Actin** - Highly conserved protein-coding gene, cytoskeletal protein
5. **GAPDH** - Housekeeping gene, glycolytic enzyme
6. **U6 snRNA** - Highly conserved small nuclear RNA, splicing component
7. **Histone H3** - Extremely conserved across eukaryotes, chromatin protein
8. **EF-1α** - Translation elongation factor, highly conserved

### MOD-Specific Sequences

**FlyBase (FB) - Drosophila melanogaster:**
- white gene - Eye color gene, commonly mutated
- rosy gene - Xanthine dehydrogenase, eye color

**WormBase (WB) - C. elegans:**
- unc-22 - Twitching phenotype, muscle protein
- dpy-10 - Dumpy phenotype, cuticle collagen

**SGD - S. cerevisiae (Yeast):**
- GAL1 - Galactose metabolism, inducible promoter
- ACT1 - Actin, highly expressed housekeeping gene

**ZFIN - Danio rerio (Zebrafish):**
- pax2a - Paired box gene, development
- sonic hedgehog (shh) - Signaling molecule, development

**RGD - Rattus norvegicus (Rat):**
- Alb (albumin) - Serum protein, highly expressed
- Ins1 (insulin 1) - Metabolic hormone

**XenBase (XB) - Xenopus:**
- sox2 - Stem cell marker, development
- bmp4 - Bone morphogenetic protein, development

---

## Appendix B: Validation Report Examples

### Example 1: Successful Validation (High Hit Rate)

```
═══════════════════════════════════════════════════════════════════════
                   DATABASE VALIDATION REPORT
═══════════════════════════════════════════════════════════════════════

MOD: SGD | Environment: prod | Databases: 15 | Time: 4m 32s

Test Sequences:
  • 8 conserved sequences (18S rRNA, 28S rRNA, COI, actin, GAPDH, U6, H3, EF-1α)
  • 2 SGD-specific sequences (GAL1, ACT1)
  • E-value threshold: 10 | Timeout: 30s

╭─────────────────────── Validation Summary ─────────────────────────╮
│ Metric                          │ Value                            │
├─────────────────────────────────┼──────────────────────────────────┤
│ Total Databases                 │ 15                               │
│ With Conserved Hits             │ 14/15 (93.3%)                    │
│ With MOD-Specific Hits          │ 13/15 (86.7%)                    │
│ Overall Success Rate            │ 90.0%                            │
│ Total Hits                      │ 287                              │
│ Average Hits per Database       │ 19.1                             │
╰─────────────────────────────────┴──────────────────────────────────╯

✅ Top Performing Databases:
  1. S_cerevisiae_genome_R64-4-1.db
     - Conserved hits: 18 | MOD-specific hits: 7 | Total: 25
  2. S_cerevisiae_CDS_all.db
     - Conserved hits: 16 | MOD-specific hits: 6 | Total: 22
  3. S_cerevisiae_protein_all.db
     - Conserved hits: 15 | MOD-specific hits: 5 | Total: 20

⚠️  Low Hit Databases (Review):
  • S_cerevisiae_ncRNA_only.db - 2 hits (specialized: ncRNA-only)
  • S_cerevisiae_tRNA.db - 1 hit (specialized: tRNA-only)

✅ VALIDATION PASSED - Databases ready for production deployment
```

### Example 2: Warning Validation (Medium Hit Rate)

```
═══════════════════════════════════════════════════════════════════════
                   DATABASE VALIDATION REPORT
═══════════════════════════════════════════════════════════════════════

MOD: WB | Environment: stage | Databases: 22 | Time: 6m 18s

Test Sequences:
  • 8 conserved sequences (18S rRNA, 28S rRNA, COI, actin, GAPDH, U6, H3, EF-1α)
  • 2 WB-specific sequences (unc-22, dpy-10)
  • E-value threshold: 10 | Timeout: 30s

╭─────────────────────── Validation Summary ─────────────────────────╮
│ Metric                          │ Value                            │
├─────────────────────────────────┼──────────────────────────────────┤
│ Total Databases                 │ 22                               │
│ With Conserved Hits             │ 15/22 (68.2%)                    │
│ With MOD-Specific Hits          │ 14/22 (63.6%)                    │
│ Overall Success Rate            │ 65.9%                            │
│ Total Hits                      │ 198                              │
│ Average Hits per Database       │ 9.0                              │
╰─────────────────────────────────┴──────────────────────────────────╯

⚠️  WARNING: Hit rate (65.9%) below 80% threshold

✅ Top Performing Databases:
  1. C_elegans_genome_WS289.db - 24 hits
  2. C_elegans_CDS_all.db - 21 hits
  3. C_elegans_protein_all.db - 18 hits

❌ Databases with No Hits (7):
  • C_elegans_miRNA.db
  • C_elegans_piRNA.db
  • C_elegans_lncRNA.db
  • C_elegans_pseudogenes.db
  • C_elegans_repeats.db
  • C_elegans_transposons.db
  • C_elegans_operons.db

💡 Diagnostic Suggestions:
  ✓ Specialized databases detected (ncRNA, repeats) - expected low hit rate
  ✓ General databases (genome, CDS, protein) have good hit rates
  ✓ Consider specialized validation sequences for ncRNA databases
  ✓ Review database indexing if general databases show low hits

⚠️  VALIDATION WARNING - Review specialized databases before deployment
```

### Example 3: Failed Validation (Low Hit Rate)

```
═══════════════════════════════════════════════════════════════════════
                   DATABASE VALIDATION REPORT
═══════════════════════════════════════════════════════════════════════

MOD: FB | Environment: prod | Databases: 18 | Time: 5m 44s

Test Sequences:
  • 8 conserved sequences (18S rRNA, 28S rRNA, COI, actin, GAPDH, U6, H3, EF-1α)
  • 2 FB-specific sequences (white, rosy)
  • E-value threshold: 10 | Timeout: 30s

╭─────────────────────── Validation Summary ─────────────────────────╮
│ Metric                          │ Value                            │
├─────────────────────────────────┼──────────────────────────────────┤
│ Total Databases                 │ 18                               │
│ With Conserved Hits             │ 6/18 (33.3%)                     │
│ With MOD-Specific Hits          │ 5/18 (27.8%)                     │
│ Overall Success Rate            │ 30.6%                            │
│ Total Hits                      │ 47                               │
│ Average Hits per Database       │ 2.6                              │
╰─────────────────────────────────┴──────────────────────────────────╯

🚨 CRITICAL: Hit rate (30.6%) critically low - likely pipeline failure

✅ Databases with Hits (6):
  • D_melanogaster_genome_r6.52.db - 12 hits
  • D_melanogaster_CDS_all.db - 9 hits
  • D_melanogaster_protein_all.db - 8 hits
  • D_melanogaster_ncRNA.db - 7 hits
  • D_melanogaster_transcripts.db - 6 hits
  • D_melanogaster_UTRs.db - 5 hits

❌ Databases with No Hits (12):
  • D_melanogaster_chr2L.db - 0 hits
  • D_melanogaster_chr2R.db - 0 hits
  • D_melanogaster_chr3L.db - 0 hits
  • D_melanogaster_chr3R.db - 0 hits
  • D_melanogaster_chrX.db - 0 hits
  • D_melanogaster_chrY.db - 0 hits
  • D_melanogaster_chr4.db - 0 hits
  • D_melanogaster_mitochondria.db - 0 hits
  • D_melanogaster_intergenic.db - 0 hits
  • D_melanogaster_introns.db - 0 hits
  • D_melanogaster_regulatory.db - 0 hits
  • D_melanogaster_repeats.db - 0 hits

💡 Diagnostic Analysis:
  ❌ Chromosome-specific databases have zero hits (expected some hits)
  ❌ Mitochondrial database has zero hits (COI should hit)
  ❌ General databases have hits but lower than expected

  Likely Issues:
  1. Database indexing failure during makeblastdb
  2. Incomplete FASTA files (truncated downloads)
  3. Wrong database type (nucleotide vs protein mismatch)

🚨 VALIDATION FAILED - DO NOT DEPLOY TO PRODUCTION

📋 Recommended Actions:
  1. Review makeblastdb logs for errors
  2. Verify MD5 checksums of downloaded FASTA files
  3. Check for disk space issues during database creation
  4. Re-run pipeline with --verbose flag for detailed diagnostics
  5. Contact DevOps if issue persists after retry
```

---

## Appendix C: Glossary

**BLAST (Basic Local Alignment Search Tool):** Sequence comparison algorithm used to find regions of similarity between biological sequences

**blastn:** BLAST program for nucleotide-nucleotide sequence comparison

**blastp:** BLAST program for protein-protein sequence comparison

**Conserved Sequence:** Biological sequence that remains similar across different species due to evolutionary pressure

**E-value (Expectation Value):** Statistical measure of the number of expected hits by chance; lower values indicate more significant matches

**False Negative:** Validation incorrectly passes a bad database (most critical type of error)

**False Positive:** Validation incorrectly fails a good database (causes unnecessary investigation)

**FASTA:** Standard text-based format for representing nucleotide or protein sequences

**Hit:** A successful match between query sequence and database sequence above threshold

**Hit Rate:** Percentage of databases that return at least one hit for test sequences

**makeblastdb:** NCBI tool that formats FASTA files into searchable BLAST databases

**MOD (Model Organism Database):** Curated database for a specific model organism (e.g., FlyBase for Drosophila)

**MOD-Specific Sequence:** Test sequence unique to a particular organism, expected to be found only in that MOD's databases

**Word Size:** BLAST parameter controlling sensitivity; smaller values are more sensitive but slower

---

*This PRD is a living document and will be updated as requirements evolve and open questions are resolved. Version history will be maintained in git.*

**Next Steps:**
1. Review and approval by stakeholders (Product, Engineering, QA, DevOps)
2. Technical design document creation by Engineering
3. Sprint planning and story breakdown
4. Implementation Phase 1 kickoff
