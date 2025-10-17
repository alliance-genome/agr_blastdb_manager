# Product Requirements Document: BLAST Database Validation System Integration

**Document Version:** 1.0
**Date:** October 8, 2025
**Project:** AGR BLAST Database Manager
**Initiative:** Unify Dual Validation Systems
**Status:** Draft - Awaiting Stakeholder Review

---

## Executive Summary

The AGR BLAST Database Manager currently has **two independent validation systems** with overlapping functionality but complementary strengths. This creates maintenance burden, user confusion, and missed opportunities for comprehensive validation. This PRD outlines a strategy to **merge these systems into a single, best-of-both-worlds validation framework** that provides comprehensive database testing with excellent user experience.

**Current State:**
- **System 1 (main branch):** Rich sequence testing (20 sequences), excellent terminal UI, Slack integration, opt-in behavior
- **System 2 (branch):** 3-tier validation (file/integrity/search), HTML reports, standalone CLI, opt-out behavior, fixture-based sequences

**Proposed State:**
- **Unified system** combining 3-tier validation, rich sequence library, HTML reports, Rich terminal UI, and flexible deployment options
- **Single source of truth** for validation logic with clear separation of concerns
- **Backward compatible** CLI flags with improved defaults for production use

**Business Impact:**
- **Reduce maintenance cost:** Single codebase instead of two parallel systems (estimated 50% reduction in maintenance effort)
- **Improve database quality:** Comprehensive validation catches more issues before production deployment
- **Better user experience:** Consistent interface, clear reporting, actionable insights
- **Enable automation:** Standalone CLI and JSON exports support CI/CD integration

**Success Metrics:**
- Zero regression in existing validation capabilities
- 100% of databases validated post-creation (currently ~inconsistent usage)
- <30 second validation time for typical databases
- >95% user satisfaction with validation output (measured via Slack feedback)

---

## 1. Context & Why Now

- **Parallel development:** Two validation systems evolved independently to solve overlapping problems, creating technical debt
- **Production needs:** AGR requires reliable database validation before serving to users via SequenceServer
- **CI/CD integration:** Need standalone validation for automated testing pipelines
- **Maintenance burden:** Dual systems require duplicate bug fixes, feature additions, and testing
- **Branch merge pending:** `comprehensive-database-testing` branch has 38 files changed, ready for integration but needs unified design

---

## 2. Users & Jobs to Be Done

### Primary Users

**1. Database Pipeline Operators**
- **JTBD:** "As a pipeline operator, I need automatic post-creation validation so that I catch database corruption before deployment"
- **JTBD:** "As a pipeline operator, I need clear pass/fail signals so that I can decide whether to deploy or rollback"

**2. DevOps/Release Engineers**
- **JTBD:** "As a release engineer, I need standalone validation scripts so that I can integrate database testing into CI/CD pipelines"
- **JTBD:** "As a release engineer, I need JSON-formatted results so that I can programmatically assess release quality"

**3. QA/Test Engineers**
- **JTBD:** "As a QA engineer, I need detailed HTML reports so that I can diagnose validation failures and document testing outcomes"
- **JTBD:** "As a QA engineer, I need reproducible test sequences so that I can verify fixes across environments"

### Secondary Users

**4. MOD Data Curators**
- **JTBD:** "As a data curator, I need MOD-specific sequence validation so that I can verify species-appropriate data quality"

**5. System Administrators**
- **JTBD:** "As a sysadmin, I need Slack notifications so that I'm alerted to validation failures without polling logs"

---

## 3. Business Goals & Success Metrics

### Business Goals

1. **Reduce technical debt** by consolidating validation logic into single system
2. **Improve database quality** through comprehensive multi-tier validation
3. **Enable automation** with standalone CLI and structured output formats
4. **Maintain velocity** by preserving all existing capabilities without regression
5. **Enhance observability** with rich reporting and logging

### Success Metrics

**Leading Indicators (Early signals):**
- Validation coverage: 100% of production databases validated post-creation
- Time to validation: <30 seconds per database (P95)
- Test fixture coverage: 100% of MODs have species-appropriate sequences
- CLI adoption: >80% of manual validation uses standalone script

**Lagging Indicators (Ultimate success):**
- Production incidents: Zero database corruption incidents in first 90 days
- Developer satisfaction: >4/5 rating for validation experience
- Maintenance effort: <2 hours/month spent on validation system updates (vs. ~5 hours currently)
- False positive rate: <5% of validation failures are false alarms

**Targets & Timeframes:**
- **Q4 2025:** Complete integration, achieve 100% validation coverage
- **Q1 2026:** HTML reporting in production use, <5% false positive rate
- **Q2 2026:** CI/CD integration complete for all MODs

---

## 4. Functional Requirements

### FR1: Three-Tier Validation Framework
**Description:** Unified validator performs file integrity, database functionality, and search capability tests in sequence

**Acceptance Criteria:**
- Tier 1 (File Integrity): Validates presence and readability of .nin, .nhr, .nsq files
- Tier 2 (Database Functionality): Runs `blastdbcmd -info` and parses sequence counts, total base pairs
- Tier 3 (Search Capability): Executes BLAST searches with universal conserved sequences
- Each tier can fail independently with clear error messages
- Validation proceeds to next tier only if previous tier passes
- All three tiers complete in <30 seconds for typical databases (P95)

---

### FR2: Rich Sequence Testing Library
**Description:** Validator uses comprehensive sequence library with both universal and MOD-specific test cases

**Acceptance Criteria:**
- **Universal sequences (8):** 18S rRNA, 28S rRNA, COI, actin, GAPDH, U6 snRNA, histone H3, EF-1α
- **MOD-specific sequences (12):** FB (white, rosy), WB (unc-22, dpy-10), SGD (GAL1, ACT1), ZFIN (pax2a, shh), RGD (Alb, Ins1), XB (sox2, bmp4)
- Sequences stored as external fixture files in `tests/fixtures/` for maintainability
- Fallback to hardcoded sequences if fixture files unavailable
- Each sequence tested independently with configurable BLAST parameters (e-value, word size)
- Hit rate calculated: (sequences_with_hits / total_sequences_tested) × 100

---

### FR3: Rich Terminal User Interface
**Description:** Validation output uses Rich library for progress bars, status indicators, and formatted summaries

**Acceptance Criteria:**
- Real-time progress bar showing validation status across databases
- Color-coded status messages (green=pass, yellow=warning, red=fail)
- Hierarchical summary: overall stats → per-MOD stats → per-database details
- Duration tracking with human-readable time formatting
- Header/section formatting with clear visual separation
- Supports both interactive (TTY) and non-interactive (CI/CD) modes

---

### FR4: HTML Report Generation
**Description:** Generate comprehensive HTML reports with executive dashboard and detailed database results

**Acceptance Criteria:**
- **Executive Dashboard:** Pass/fail counts, success rate pie chart, validation duration, timestamp
- **Failed Databases Section:** Grid view of failures with error details, file check status, integrity check status
- **Successful Databases Table:** Name, sequence count, hit count, validation time, status
- **Visual Design:** Gradient headers, color-coded stat cards, responsive grid layout
- HTML includes embedded CSS (no external dependencies)
- Reports saved to `../reports/validation_report_{MOD}_{RELEASE}_{TIMESTAMP}.html`
- Report generation <2 seconds for typical validation run

---

### FR5: JSON Export for CI/CD Integration
**Description:** Export structured validation results in JSON format for programmatic consumption

**Acceptance Criteria:**
- JSON schema includes: `mod`, `release`, `timestamp`, `summary`, `databases[]`
- Each database entry includes: `name`, `path`, `overall_status`, `file_check`, `integrity_check`, `functionality_test`, `validation_time_seconds`
- Summary includes: `total`, `passed`, `failed`, `success_rate`, `total_time_seconds`
- JSON saved to `../logs/validation_summary_{MOD}_{RELEASE}.json`
- Valid JSON (parseable by `jq`, Python `json` module, etc.)
- Exit code reflects validation status: 0=success, 1=error, 2=validation failures

---

### FR6: Standalone Validation CLI
**Description:** Independent CLI tool for on-demand validation without running full database creation pipeline

**Acceptance Criteria:**
- Command structure: `validate_release.py validate -m <MOD> -r <RELEASE>`
- Supports all MODs: FB, SGD, WB, ZFIN, RGD, XB
- Configurable base path for database discovery
- `--json-report` flag for JSON export
- `list` subcommand to discover available releases
- Respects same validation parameters as main pipeline (e-value, word size, timeout)
- Can run independently without database creation workflow

---

### FR7: Integrated Pipeline Validation
**Description:** Validation runs automatically after successful database creation in main pipeline

**Acceptance Criteria:**
- Default behavior: validation runs post-creation (opt-out, not opt-in)
- CLI flags: `--validate` (explicit enable), `--skip-validation` (explicit disable)
- Validation only runs if database creation succeeds
- Validation results sent to Slack (if configured) with color-coded messages
- Validation failures logged as warnings but don't fail pipeline (databases still copied to SequenceServer)
- Log file includes validation section with clear headers

---

### FR8: Comprehensive Logging
**Description:** Detailed logging captures all validation steps, results, and timing information

**Acceptance Criteria:**
- Log file naming: `database_validation_{MOD}_{ENVIRONMENT}_{TIMESTAMP}.log`
- Log levels: DEBUG (all BLAST commands), INFO (progress updates), WARNING (low hit rates), ERROR (validation failures)
- Captures: configuration used, databases discovered, test sequences used, BLAST parameters, per-database results, summary statistics
- Log file rotation: maintains last 30 days of validation logs
- Logs written to `../logs/` directory
- File handler (detailed) and console handler (progress only)

---

### FR9: Slack Integration
**Description:** Send validation results to Slack channel with formatted messages and color-coding

**Acceptance Criteria:**
- Success message (green): "All {N} databases passed validation"
- Warning message (yellow): "{N}/{TOTAL} databases failed validation"
- Error message (red): "Database validation failed - {ERROR}"
- Includes MOD, environment, timestamp, hit rates
- Handles Slack message batching (respects API limits)
- Graceful fallback if Slack webhook unavailable
- No PII/sensitive data in Slack messages

---

### FR10: Configurable Validation Parameters
**Description:** BLAST search parameters configurable via CLI flags and environment variables

**Acceptance Criteria:**
- `--evalue`: E-value threshold (default: 10)
- `--word-size`: BLAST word size (default: 7)
- `--timeout`: Timeout per BLAST search in seconds (default: 30)
- `--num-threads`: BLAST parallelization (default: 2)
- Parameters logged at validation start
- Invalid parameters rejected with clear error messages
- Documented default values optimized for sensitivity (permissive thresholds)

---

## 5. Non-Functional Requirements

### Performance
- Validation completes in <30 seconds per database (P95)
- Memory usage <500MB during validation of single database
- BLAST searches timeout after configurable duration (default: 30s)
- HTML report generation <2 seconds
- Parallel validation: supports validating multiple databases concurrently (future enhancement)

### Scale
- Supports validation of 1,000+ databases in single run (current: FB has 513 databases)
- Handles databases from 1KB to 50GB size
- Test sequence library scales to 50+ sequences without performance degradation

### SLOs/SLAs
- **Availability:** Validation runs 100% of times when invoked (no silent failures)
- **Reliability:** <5% false positive rate (incorrectly flagging valid databases as failed)
- **Latency:** P50 <15 seconds, P95 <30 seconds, P99 <60 seconds per database

### Privacy
- No personally identifiable information (PII) in validation logs or reports
- Sequence data limited to small test fragments (not full genome sequences)
- Slack notifications contain only summary statistics (no raw sequence data)

### Security
- Read-only operations: validation never modifies database files
- No external network calls except Slack webhook (optional)
- Validates file permissions before attempting reads
- Subprocess timeouts prevent runaway BLAST processes
- No shell injection vulnerabilities (uses subprocess with argument lists)

### Observability
- Structured logging with log levels (DEBUG, INFO, WARNING, ERROR)
- Validation metrics exportable as JSON for monitoring dashboards
- Real-time progress updates via Rich terminal UI
- Failed validations include diagnostic information (tier failed, error message, suggested fixes)
- Log aggregation friendly: one log file per validation run with unique timestamp

---

## 6. Scope Definition

### In Scope

- Merge `src/validation.py` (main) and `src/database_validator.py` (branch) into unified validator
- Integrate `src/validation_reporter.py` for HTML report generation
- Preserve `src/validate_release.py` as standalone CLI tool
- Update `src/create_blast_db.py` to use unified validation system
- Migrate test sequences to external fixture files in `tests/fixtures/`
- Update documentation: CLAUDE.md, README.md, DATABASE_VALIDATION.md
- Update test suite: `tests/unit/test_validation.py` covers unified system
- Default behavior: validation enabled post-creation (opt-out)

### Out of Scope

- Real-time dashboard: Web-based validation monitoring (future consideration)
- Database repair: Automatic fixing of failed databases (remain diagnostic-only)
- Protein database validation: Focus remains on nucleotide databases (blastn)
- Cross-version validation: Comparing databases across releases (future enhancement)
- Performance benchmarking: Detailed query performance testing (separate initiative)
- MOD-specific validation rules: Complex per-MOD validation logic (keep universal)

### Future Considerations

- **Phase 2:** Web dashboard for multi-MOD validation status across environments
- **Phase 3:** Protein database support (blastp) with appropriate test sequences
- **Phase 4:** Validation result time-series database for trend analysis
- **Phase 5:** Automated alerting based on hit rate thresholds (beyond Slack)
- **Phase 6:** Integration with GitHub status checks for PR validation

---

## 7. Rollout Plan

### Phase 1: Core Integration (Weeks 1-2)

**Milestone:** Unified validator functional with 3-tier validation + rich sequence library

**Tasks:**
- Create `src/validation_unified.py` merging logic from both systems
- Architecture: `DatabaseValidator` class (validation engine) + `ValidationReporter` class (reporting)
- Preserve all sequence tests from `validation.py` (8 conserved + 12 MOD-specific)
- Add 3-tier validation logic from `database_validator.py`
- Migrate sequences to fixture files while maintaining hardcoded fallback
- Update imports in `create_blast_db.py` to use unified validator

**Success Gate:**
- All existing tests pass (`tests/unit/test_validation.py`)
- 3-tier validation executes successfully on test databases
- No regression in terminal UI quality

**Guardrails:**
- If validation runtime >2x current average, pause for performance optimization
- If false positive rate >10%, investigate sequence library issues

---

### Phase 2: Reporting & CLI (Weeks 3-4)

**Milestone:** HTML reports generated, standalone CLI functional

**Tasks:**
- Integrate `ValidationReporter` class for HTML/JSON export
- Update `validate_release.py` to use unified validator
- Add `--html-report` and `--json-report` flags to main CLI
- Implement report generation in post-validation hook
- Test report generation with sample validation runs

**Success Gate:**
- HTML reports render correctly in browsers (Chrome, Firefox, Safari)
- JSON exports parse successfully in CI/CD scripts
- Standalone CLI validates databases without running full pipeline

**Guardrails:**
- If report generation takes >5 seconds, optimize HTML templating
- If JSON schema breaks existing integrations, maintain backward compatibility

---

### Phase 3: Integration & Testing (Week 5)

**Milestone:** Full integration with `create_blast_db.py`, comprehensive test coverage

**Tasks:**
- Update CLI flags: `--validate` (default: true), `--skip-validation` (opt-out)
- Add validation section to per-run log files
- Implement Slack notification formatting for validation results
- Write integration tests: `tests/integration/test_validation_integration.py`
- Update fixture files with real conserved sequences (verify against NCBI)

**Success Gate:**
- Integration tests pass with 100% coverage of validation code paths
- Validation runs successfully on all MODs in test environment
- Slack notifications format correctly with color-coding

**Guardrails:**
- If validation causes pipeline failures >5%, make validation non-blocking
- If Slack message volume exceeds limits, implement batching

---

### Phase 4: Documentation & Rollout (Week 6)

**Milestone:** Production-ready system with complete documentation

**Tasks:**
- Update `DATABASE_VALIDATION.md` with unified system documentation
- Update `CLAUDE.md` with new CLI flags and behavior
- Update `README.md` with validation section
- Create runbook: "Troubleshooting Validation Failures"
- Deprecate `src/validation.py` and `src/database_validator.py` (mark as legacy)
- Deploy to staging environment for final testing

**Success Gate:**
- Documentation reviewed and approved by stakeholders
- Staging validation runs successfully for 3 consecutive database updates
- Runbook tested by QA team

**Guardrails:**
- If documentation is unclear (>3 questions per section), revise before production
- If staging validation fails, rollback and debug before production deployment

---

### Phase 5: Production Deployment (Week 7)

**Milestone:** Unified validation system running in production

**Tasks:**
- Deploy to production environment
- Monitor validation runs for first 7 days (daily check-in)
- Collect feedback from pipeline operators and data curators
- Address any performance or usability issues
- Remove legacy validation code after 30 days of stable operation

**Success Gate:**
- Zero production incidents caused by validation system
- Validation runs successfully on 100% of database creation runs
- User feedback >4/5 satisfaction rating

**Guardrails:**
- If validation false positive rate >5%, tune sequence library
- If validation runtime impacts pipeline SLA, implement parallelization

**Kill-Switch Criteria:**
- If validation causes pipeline downtime >1 hour, disable validation and rollback
- If validation corrupts database files (should be impossible due to read-only design), immediate rollback
- If Slack spam exceeds 10 messages/minute, disable Slack integration

---

## 8. Technical Architecture

### Unified Validator Design

**File Structure:**
```
src/
├── validation_unified.py        # New unified validator (merges both systems)
│   ├── DatabaseValidator        # Core validation engine
│   └── ValidationResult         # Result container
├── validation_reporter.py       # HTML/JSON report generation (preserved)
├── validate_release.py          # Standalone CLI (preserved, updated imports)
├── create_blast_db.py           # Updated to use validation_unified
├── validation.py                # Legacy (deprecated, remove after 30 days)
└── database_validator.py        # Legacy (deprecated, remove after 30 days)

tests/
├── fixtures/
│   ├── universal_conserved.fasta      # Universal sequences (preserved)
│   ├── fb_specific.fasta              # FB-specific sequences
│   ├── wb_specific.fasta              # WB-specific sequences
│   ├── sgd_specific.fasta             # SGD-specific sequences
│   ├── zfin_specific.fasta            # ZFIN-specific sequences
│   ├── rgd_specific.fasta             # RGD-specific sequences
│   └── xb_specific.fasta              # XB-specific sequences
└── unit/
    └── test_validation_unified.py     # New comprehensive test suite
```

**Class Architecture:**

```python
class DatabaseValidator:
    """
    Unified validation engine combining 3-tier validation with rich sequence library.
    Responsibilities: File checks, integrity tests, BLAST searches, result aggregation.
    """

    def __init__(self, logger, evalue="10", word_size="7", timeout=30, num_threads=2):
        # Merge initialization from both systems
        self.logger = logger
        self.evalue = evalue
        self.word_size = word_size
        self.timeout = timeout
        self.num_threads = num_threads
        self.sequence_library = self._load_sequence_library()

    def _load_sequence_library(self) -> Dict[str, str]:
        """Load sequences from fixture files with hardcoded fallback"""
        # Try fixture files first, fallback to hardcoded sequences
        pass

    def validate_database(self, db_name: str, db_path: str, mod: str) -> ValidationResult:
        """
        Run 3-tier validation on single database.
        Returns: ValidationResult with detailed test outcomes
        """
        result = ValidationResult(db_name, db_path, mod)

        # Tier 1: File integrity
        if not self._validate_files(db_path, result):
            return result  # Stop if files missing/unreadable

        # Tier 2: Database functionality
        if not self._validate_integrity(db_path, result):
            return result  # Stop if database corrupted

        # Tier 3: Search capability
        self._validate_search(db_path, mod, result)

        return result

    def validate_all(self, base_path: str, mod_filter: Optional[str] = None) -> Dict:
        """Validate all databases with Rich UI and summary stats"""
        pass

class ValidationResult:
    """
    Container for validation results with hierarchical test outcomes.
    Includes: file_check, integrity_check, search_tests, timing, summary.
    """
    pass

class ValidationReporter:
    """
    Report generation engine (preserved from branch).
    Responsibilities: HTML reports, JSON exports, dashboard generation.
    """

    def generate_html_report(self, validation_results: Dict) -> str:
        """Generate HTML report from ValidationResult data"""
        pass

    def generate_json_export(self, validation_results: Dict) -> str:
        """Generate JSON export for CI/CD integration"""
        pass
```

**Data Flow:**

1. **Pipeline Trigger:** `create_blast_db.py` completes database creation successfully
2. **Validator Init:** Initialize `DatabaseValidator` with logger and parameters
3. **Database Discovery:** Scan output directory for .nin/.pin files by MOD/environment
4. **Per-Database Validation:**
   - Tier 1: Check file existence/permissions
   - Tier 2: Run `blastdbcmd -info`, parse sequence counts
   - Tier 3: Execute BLAST searches with test sequences
5. **Result Aggregation:** Collect `ValidationResult` objects into summary stats
6. **Reporting:**
   - Terminal: Rich UI with progress bars, color-coded summary
   - HTML: Generate comprehensive report via `ValidationReporter`
   - JSON: Export structured data for CI/CD
   - Slack: Send formatted notification with pass/fail counts
7. **Cleanup:** Write final log entry, return control to main pipeline

---

### Migration Strategy

**Backward Compatibility:**

- Preserve `--validate` flag (currently opt-in) but change default to `True`
- Add `--skip-validation` flag for explicit opt-out
- If user specifies `--validate` explicitly, log warning: "Note: Validation now runs by default. Use --skip-validation to disable."
- Maintain Slack message format (existing integrations depend on this)

**Deprecation Path:**

1. **Week 1-4:** Both systems coexist, new unified system under development
2. **Week 5-6:** Unified system deployed, legacy systems marked deprecated with log warnings
3. **Week 7-10:** Monitor unified system in production, collect feedback
4. **Week 11:** Remove `validation.py` and `database_validator.py` if no issues reported

**Code Migration:**

- Sequence library: Copy from `validation.py` (more comprehensive) to fixture files
- File checks: Copy from `database_validator.py` (more robust)
- Terminal UI: Preserve `validation.py` Rich integration (better UX)
- HTML reports: Preserve `validation_reporter.py` (comprehensive feature)
- Logging: Merge approaches (file handler from `database_validator.py`, Rich console from `validation.py`)

---

## 9. Testing Strategy

### Unit Tests

**Test Coverage Requirements: >90% line coverage**

- `test_validation_unified.py`: Core validator functionality
  - Test 3-tier validation logic
  - Test sequence library loading (fixture files + fallback)
  - Test BLAST parameter handling
  - Test timeout/error handling
  - Mock BLAST subprocess calls

- `test_validation_reporter.py`: Report generation
  - Test HTML generation with sample data
  - Test JSON schema compliance
  - Test report edge cases (0 databases, all failed, all passed)

- `test_validate_release_cli.py`: Standalone CLI
  - Test argument parsing
  - Test MOD/release discovery
  - Test exit codes (0, 1, 2)

### Integration Tests

**Test Coverage: All MODs × validation scenarios**

- `test_validation_integration.py`:
  - End-to-end validation after database creation
  - Test on real test databases (small samples)
  - Verify log file creation
  - Verify HTML report generation
  - Verify Slack notifications (with mock webhook)
  - Test validation with database creation failures (validation should skip)

### Regression Tests

**Preserve existing behavior:**

- Compare validation results between legacy `validation.py` and unified system on same databases
- Verify no change in Slack message format (backward compatibility)
- Verify terminal UI quality matches or exceeds legacy system

### Performance Tests

**Load testing:**

- Validate 100 databases sequentially (measure total time)
- Validate databases with 1KB, 1MB, 100MB, 1GB sizes
- Test BLAST timeout enforcement (deliberately slow searches)
- Test parallel validation (future enhancement)

### User Acceptance Testing

**Scenarios:**

1. **Pipeline Operator:** Run full pipeline, verify validation runs automatically, check Slack notification
2. **Release Engineer:** Run standalone CLI, export JSON, parse in CI/CD script
3. **QA Engineer:** Generate HTML report, verify all sections render, download and archive

---

## 10. Documentation Updates

### Update `DATABASE_VALIDATION.md`

- Section 1: Overview of unified validation system
- Section 2: Quick start (automatic + manual validation)
- Section 3: Three-tier validation explanation
- Section 4: Sequence library documentation
- Section 5: Report formats (HTML, JSON)
- Section 6: Troubleshooting guide
- Section 7: CLI reference

### Update `CLAUDE.md`

- Update CLI flags: `--validate` (default: true), `--skip-validation`
- Update file structure: `validation_unified.py`, deprecate legacy files
- Update testing commands: new test file names
- Add validation section to "Architecture Overview"

### Update `README.md`

- Add "Database Validation" section
- Link to `DATABASE_VALIDATION.md` for details
- Include example CLI usage
- Mention automatic post-creation validation

### Create Runbook

- **Title:** "Troubleshooting BLAST Database Validation Failures"
- **Sections:**
  - Tier 1 failures: File integrity issues (permissions, missing files, corrupt files)
  - Tier 2 failures: Database integrity issues (blastdbcmd errors, empty databases)
  - Tier 3 failures: Search issues (no hits, timeouts, BLAST errors)
  - Common solutions: Rebuilding databases, adjusting BLAST parameters, MOD-specific considerations
  - Escalation path: When to contact MOD curators vs. AGR team

---

## 11. Risks & Mitigations

### Technical Risks

**Risk 1: Validation runtime regression**
- **Likelihood:** Medium
- **Impact:** High (slows pipeline, reduces developer velocity)
- **Mitigation:** Benchmark validation times before/after integration, optimize BLAST parameters, implement parallelization if needed
- **Contingency:** Add `--skip-validation` flag to unblock urgent deployments

**Risk 2: False positives in sequence testing**
- **Likelihood:** Medium
- **Impact:** Medium (wastes time investigating non-issues)
- **Mitigation:** Use permissive BLAST thresholds (e-value=10, word_size=7), validate fixture sequences against NCBI, tune thresholds based on real-world data
- **Contingency:** Provide flag to adjust e-value threshold per-MOD

**Risk 3: Breaking changes in CLI interface**
- **Likelihood:** Low
- **Impact:** High (breaks existing scripts, automation)
- **Mitigation:** Maintain backward compatibility for `--validate` flag, add new flags alongside old ones, deprecation warnings for 30 days
- **Contingency:** Provide compatibility shim for legacy flag names

**Risk 4: HTML report generation failures**
- **Likelihood:** Low
- **Impact:** Low (reports nice-to-have, not critical)
- **Mitigation:** HTML generation in try-catch block, fallback to JSON export only, validation continues even if report fails
- **Contingency:** Disable HTML reports if repeated failures

### Business/Market Risks

**Risk 5: User confusion from changed defaults**
- **Likelihood:** Medium
- **Impact:** Low (questions to support, minor workflow disruption)
- **Mitigation:** Clear documentation, deprecation warnings, changelog announcement, Slack notification about new behavior
- **Contingency:** Provide quick reference guide, add FAQ section

**Risk 6: Maintenance burden during transition**
- **Likelihood:** High
- **Impact:** Medium (dual systems require more effort)
- **Mitigation:** Time-box transition to 6 weeks, remove legacy code aggressively after 30 days, clear ownership assignment
- **Contingency:** If transition drags on, prioritize unified system and deprecate legacy immediately

### Dependencies

**Dependency 1: NCBI BLAST+ tools**
- **Risk:** BLAST tool version changes break validation
- **Mitigation:** Pin BLAST+ version in Docker container, test with multiple versions (2.13, 2.14, 2.15), document version compatibility
- **Contingency:** Maintain compatibility layer for BLAST output parsing

**Dependency 2: Slack webhook availability**
- **Risk:** Slack API changes or webhook becomes unavailable
- **Mitigation:** Graceful fallback (log warning but continue), webhook URL as optional configuration, test Slack integration in CI
- **Contingency:** Disable Slack notifications if API unavailable for >24 hours

**Dependency 3: Test fixture files**
- **Risk:** Fixture files accidentally deleted or corrupted
- **Mitigation:** Maintain hardcoded sequence fallback, add fixtures to version control, test fixture loading in unit tests
- **Contingency:** Validator warns and falls back to hardcoded sequences

---

## 12. Open Questions Requiring Stakeholder Input

### Question 1: Default Behavior
**Decision:** Should validation be opt-in (like current `main` branch) or opt-out (like `comprehensive-database-testing` branch)?

**Recommendation:** **Opt-out** (default: enabled)
- **Rationale:** Production databases should be validated by default for quality assurance
- **User impact:** Adds ~30 seconds to pipeline runtime but catches critical issues before deployment
- **Escape hatch:** `--skip-validation` flag available for urgent deployments

**Stakeholder approval needed:** Database pipeline operators, Release engineering team

---

### Question 2: Sequence Library Storage
**Decision:** Should sequences be stored in external fixture files or hardcoded in Python?

**Recommendation:** **Fixture files with hardcoded fallback**
- **Rationale:** Fixture files easier to maintain, test, and update; fallback ensures reliability
- **Trade-off:** Slight complexity in loading logic, but better maintainability long-term
- **Implementation:** Load from `tests/fixtures/`, fallback to `CONSERVED_SEQUENCES` dict if unavailable

**Stakeholder approval needed:** Development team, QA team

---

### Question 3: HTML Reports Priority
**Decision:** Are HTML reports must-have for Phase 1 or can they be deferred to Phase 2?

**Recommendation:** **Include in Phase 2** (weeks 3-4)
- **Rationale:** Core validation functionality more critical than reporting polish
- **Trade-off:** QA team waits 2 weeks for HTML reports but gets stable validation sooner
- **Alternative:** JSON exports available in Phase 1 for programmatic analysis

**Stakeholder approval needed:** QA team, Product management

---

### Question 4: Validation Failure Behavior
**Decision:** Should validation failures block database deployment (hard fail) or just warn (soft fail)?

**Recommendation:** **Soft fail (warn but continue)**
- **Rationale:** Some MOD databases are specialized (e.g., structural RNA) and may legitimately fail universal sequence tests
- **User impact:** Databases copied to SequenceServer even if validation fails, but operators alerted via Slack/logs
- **Future enhancement:** Per-MOD validation rules with hard fail option

**Stakeholder approval needed:** Database pipeline operators, MOD data curators

---

### Question 5: Standalone CLI Tool Name
**Decision:** Keep `validate_release.py` name or rename to `blast_db_validate.py` for clarity?

**Recommendation:** **Keep `validate_release.py`**
- **Rationale:** Name accurately describes purpose (validate a specific release), established in branch
- **Alternative:** Add symlink `blast_db_validate.py → validate_release.py` for discoverability
- **Documentation:** Clearly document tool in README and CLAUDE.md

**Stakeholder approval needed:** Development team

---

### Question 6: Deprecation Timeline
**Decision:** How long should legacy validation systems (`validation.py`, `database_validator.py`) remain before removal?

**Recommendation:** **30 days after unified system deployed to production**
- **Rationale:** Gives time to identify regressions and roll back if needed
- **User impact:** Deprecation warnings logged but no functional impact
- **Cleanup:** Remove deprecated files in single commit with clear changelog entry

**Stakeholder approval needed:** Development team, Release engineering

---

### Question 7: Performance Budget
**Decision:** What is acceptable validation runtime? Current: ~15s/database, Target: ?

**Recommendation:** **<30 seconds per database (P95)**
- **Rationale:** Balances thoroughness with pipeline velocity (513 FB databases = ~4 hours at 30s each)
- **Optimization levers:** Parallel validation (future), reduced sequence library, higher e-value threshold
- **Monitoring:** Track P50/P95/P99 latency in logs, alert if P95 >45 seconds

**Stakeholder approval needed:** Database pipeline operators, Performance team

---

## 13. Success Criteria & Launch Checklist

### Pre-Launch Checklist

- [ ] All functional requirements implemented (FR1-FR10)
- [ ] Unit test coverage >90%
- [ ] Integration tests pass on staging environment
- [ ] Documentation updated (DATABASE_VALIDATION.md, CLAUDE.md, README.md)
- [ ] Runbook created and reviewed by QA team
- [ ] Stakeholder approval on open questions (Q1-Q7)
- [ ] Performance benchmarks meet targets (<30s P95)
- [ ] Slack integration tested with test webhook
- [ ] HTML reports render correctly in 3 browsers
- [ ] JSON exports validate against schema
- [ ] Backward compatibility verified (legacy `--validate` flag works)

### Launch Day Checklist

- [ ] Deploy unified validator to production
- [ ] Enable validation on next scheduled database update
- [ ] Monitor logs for validation errors
- [ ] Check Slack notifications format correctly
- [ ] Verify HTML reports generated and accessible
- [ ] Confirm no pipeline failures due to validation

### Post-Launch Checklist (7 days)

- [ ] Collect user feedback (>4/5 satisfaction rating)
- [ ] Analyze validation performance metrics (P95 <30s)
- [ ] Review false positive rate (<5%)
- [ ] Address any reported issues
- [ ] Update documentation based on feedback
- [ ] Schedule deprecation of legacy validation code (30 days)

---

## 14. Appendix

### Appendix A: Comparison Matrix

| Feature | validation.py (main) | database_validator.py (branch) | Unified System (proposed) |
|---------|----------------------|-------------------------------|---------------------------|
| **File integrity checks** | ❌ | ✅ | ✅ |
| **blastdbcmd -info** | ❌ | ✅ | ✅ |
| **BLAST searches** | ✅ | ✅ | ✅ |
| **Sequence library** | 20 sequences (hardcoded) | Universal only (fixtures) | 20 sequences (fixtures + fallback) |
| **Terminal UI** | ✅ Rich-based | ⚠️ Basic | ✅ Rich-based (enhanced) |
| **HTML reports** | ❌ | ✅ | ✅ |
| **JSON exports** | ❌ | ✅ | ✅ |
| **Standalone CLI** | ❌ | ✅ | ✅ |
| **Slack integration** | ✅ Color-coded | ✅ Basic | ✅ Color-coded (enhanced) |
| **Default behavior** | Opt-in (off) | Opt-out (on) | Opt-out (on) |
| **Test fixtures** | ❌ | ✅ | ✅ |
| **Logging** | ✅ | ✅ | ✅ (enhanced) |
| **Lines of code** | 524 | 829 (3 files) | ~650 (2 files) |

### Appendix B: Sequence Library

**Universal Conserved Sequences (8):**
1. **18S rRNA** - Small ribosomal subunit RNA, universal in eukaryotes
2. **28S rRNA** - Large ribosomal subunit RNA, universal in eukaryotes
3. **COI (Cytochrome c oxidase I)** - Mitochondrial gene, DNA barcoding standard
4. **Actin** - Cytoskeletal protein, highly conserved
5. **GAPDH** - Glycolysis enzyme, housekeeping gene
6. **U6 snRNA** - Splicing machinery RNA, universal in eukaryotes
7. **Histone H3** - DNA packaging protein, extreme conservation
8. **EF-1α (Elongation Factor 1-alpha)** - Translation machinery, highly conserved

**MOD-Specific Sequences (12):**
- **FB (FlyBase):** white gene, rosy gene
- **WB (WormBase):** unc-22, dpy-10
- **SGD (Yeast):** GAL1 promoter, ACT1
- **ZFIN (Zebrafish):** pax2a, sonic hedgehog
- **RGD (Rat):** Albumin, Insulin1
- **XB (Xenopus):** sox2, bmp4

### Appendix C: CLI Reference

```bash
# Main pipeline with validation (default)
uv run python src/create_blast_db.py --conf conf/global.yaml --mod FB --env FB2025_03

# Skip validation (opt-out)
uv run python src/create_blast_db.py --conf conf/global.yaml --mod WB --env WS297 --skip-validation

# Custom BLAST parameters
uv run python src/create_blast_db.py --conf conf/global.yaml --mod SGD --env main --evalue 1e-5 --word-size 11

# Standalone validation
uv run python src/validate_release.py validate -m FB -r FB2025_03

# Standalone validation with JSON report
uv run python src/validate_release.py validate -m SGD -r main --json-report

# List available releases
uv run python src/validate_release.py list
```

### Appendix D: References

- **Branch:** `origin/comprehensive-database-testing`
- **Files changed:** 46 files, +2336 insertions, -3860 deletions
- **Key commits:**
  - Main branch: `b94273c` - Add post-creation BLAST database validation feature
  - Branch: Multiple commits adding 3-tier validation, HTML reports, standalone CLI
- **Documentation:**
  - `DATABASE_VALIDATION.md` (328 lines)
  - `tests/ui/README_locust.md`
  - `tests/ui/Readme_ui.md`

---

## Approval & Sign-Off

**Document Prepared By:** Claude Code (AI Product Manager)
**Date:** October 8, 2025

**Approval Required From:**
- [ ] Technical Lead: Architecture and implementation approach
- [ ] Database Pipeline Operators: Default behavior and CLI flags
- [ ] Release Engineering: CI/CD integration and JSON schema
- [ ] QA Team: Testing strategy and validation criteria
- [ ] Product Management: Scope and timeline approval

**Next Steps:**
1. Review PRD with stakeholders (1 week)
2. Address open questions and collect decisions
3. Finalize technical design and create implementation tickets
4. Begin Phase 1 development (estimated start: Week of October 15, 2025)

---

**End of Document**
