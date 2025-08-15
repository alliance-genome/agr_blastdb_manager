#!/usr/bin/env python3
"""
Database Validator Module

Comprehensive BLAST database testing and validation system that runs
automatically after database creation to ensure quality and functionality.
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from . import terminal


class DatabaseValidator:
    """Comprehensive BLAST database validator with detailed logging"""
    
    def __init__(self, log_dir: str = "../logs", test_sequences_dir: str = "../tests/fixtures"):
        self.log_dir = Path(log_dir)
        self.test_sequences_dir = Path(test_sequences_dir)
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        # Setup comprehensive logging
        self.setup_logging()
        
        # Universal conserved sequences for testing
        self.universal_sequences = self.test_sequences_dir / "universal_conserved.fasta"
        
    def setup_logging(self):
        """Setup detailed logging for database validation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"database_validation_{timestamp}.log"
        
        # Create logger
        self.logger = logging.getLogger('database_validator')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler for progress updates
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Database validation logging initialized: {log_file}")
        
    def validate_database_files(self, db_path: str) -> Tuple[bool, str]:
        """Validate that all required BLAST database files exist and are readable"""
        required_extensions = ['.nin', '.nhr', '.nsq']  # nucleotide database files
        
        for ext in required_extensions:
            file_path = db_path + ext
            if not os.path.exists(file_path):
                self.logger.error(f"Missing required file: {file_path}")
                return False, f"Missing file: {file_path}"
            
            if not os.access(file_path, os.R_OK):
                self.logger.error(f"File not readable: {file_path}")
                return False, f"File not readable: {file_path}"
                
        self.logger.debug(f"All required files present for: {db_path}")
        return True, "All files present"
        
    def validate_database_integrity(self, db_path: str) -> Tuple[bool, str, Dict]:
        """Validate database integrity using blastdbcmd"""
        try:
            self.logger.debug(f"Checking database integrity: {db_path}")
            result = subprocess.run([
                'blastdbcmd', '-db', db_path, '-info'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                error_msg = f"blastdbcmd failed: {result.stderr[:200]}"
                self.logger.error(error_msg)
                return False, error_msg, {}
            
            # Parse database info
            info_output = result.stdout
            db_info = self.parse_database_info(info_output)
            
            # Check if database has sequences
            seq_count = db_info.get('sequences', 0)
            if seq_count == 0:
                self.logger.warning(f"Database contains 0 sequences: {db_path}")
                return False, "Database contains 0 sequences", db_info
                
            self.logger.info(f"Database valid: {db_path} ({seq_count:,} sequences)")
            return True, f"{seq_count:,} sequences", db_info
            
        except subprocess.TimeoutExpired:
            error_msg = "Database validation timeout"
            self.logger.error(f"{error_msg}: {db_path}")
            return False, error_msg, {}
        except Exception as e:
            error_msg = f"Validation error: {str(e)[:100]}"
            self.logger.error(f"{error_msg}: {db_path}")
            return False, error_msg, {}
    
    def parse_database_info(self, info_output: str) -> Dict:
        """Parse blastdbcmd -info output into structured data"""
        db_info = {}
        
        try:
            lines = info_output.strip().split('\n')
            for line in lines:
                if 'sequences;' in line:
                    # Extract sequence count
                    parts = line.split('sequences;')
                    if parts:
                        seq_count = int(parts[0].strip().split()[-1].replace(',', ''))
                        db_info['sequences'] = seq_count
                        
                if 'total letters' in line:
                    # Extract total base pairs
                    try:
                        bp_part = line.split('total letters')[0].strip().split()[-1]
                        db_info['total_bp'] = int(bp_part.replace(',', ''))
                    except:
                        pass
                        
                if 'Database:' in line:
                    db_info['title'] = line.replace('Database:', '').strip()
                    
        except Exception as e:
            self.logger.warning(f"Could not fully parse database info: {e}")
            
        return db_info
    
    def test_database_functionality(self, db_path: str) -> Tuple[bool, str, Dict]:
        """Test database functionality with universal conserved sequences"""
        if not self.universal_sequences.exists():
            self.logger.error(f"Universal test sequences not found: {self.universal_sequences}")
            return False, "Test sequences missing", {}
            
        try:
            self.logger.debug(f"Testing database functionality: {db_path}")
            result = subprocess.run([
                'blastn', '-query', str(self.universal_sequences), '-db', db_path,
                '-outfmt', '6 qseqid sseqid pident length evalue bitscore',
                '-evalue', '10',        # Very permissive
                '-word_size', '7',      # Sensitive
                '-max_target_seqs', '5' # Limited output
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                error_msg = f"BLAST search failed: {result.stderr[:200]}"
                self.logger.error(error_msg)
                return False, error_msg, {}
            
            # Analyze results
            output_lines = [line for line in result.stdout.strip().split('\n') 
                           if line and not line.startswith('Warning')]
            
            test_results = {
                'total_hits': len(output_lines),
                'queries_tested': self.count_sequences_in_fasta(str(self.universal_sequences)),
                'best_hits': []
            }
            
            # Process best hits
            for line in output_lines[:5]:  # Top 5 hits
                parts = line.split('\t')
                if len(parts) >= 6:
                    hit_info = {
                        'query': parts[0],
                        'subject': parts[1],
                        'identity': float(parts[2]),
                        'length': int(parts[3]),
                        'evalue': float(parts[4]),
                        'bitscore': float(parts[5])
                    }
                    test_results['best_hits'].append(hit_info)
            
            if test_results['total_hits'] > 0:
                self.logger.info(f"Database functional: {db_path} ({test_results['total_hits']} hits)")
                return True, f"{test_results['total_hits']} hits found", test_results
            else:
                self.logger.warning(f"Database functional but no hits: {db_path}")
                return True, "Functional but no hits", test_results
                
        except subprocess.TimeoutExpired:
            error_msg = "BLAST search timeout"
            self.logger.error(f"{error_msg}: {db_path}")
            return False, error_msg, {}
        except Exception as e:
            error_msg = f"BLAST search error: {str(e)[:100]}"
            self.logger.error(f"{error_msg}: {db_path}")
            return False, error_msg, {}
    
    def count_sequences_in_fasta(self, fasta_file: str) -> int:
        """Count number of sequences in FASTA file"""
        try:
            with open(fasta_file, 'r') as f:
                count = sum(1 for line in f if line.startswith('>'))
            return count
        except:
            return 0
    
    def validate_single_database(self, db_path: str) -> Dict:
        """Comprehensive validation of a single database"""
        start_time = time.time()
        self.logger.info(f"Validating database: {db_path}")
        
        validation_result = {
            'database_path': db_path,
            'timestamp': datetime.now().isoformat(),
            'validation_time_seconds': 0,
            'file_check': {'passed': False, 'message': ''},
            'integrity_check': {'passed': False, 'message': '', 'info': {}},
            'functionality_test': {'passed': False, 'message': '', 'results': {}},
            'overall_status': 'FAILED'
        }
        
        # Step 1: File validation
        files_ok, file_msg = self.validate_database_files(db_path)
        validation_result['file_check'] = {'passed': files_ok, 'message': file_msg}
        
        if not files_ok:
            validation_result['validation_time_seconds'] = time.time() - start_time
            self.logger.error(f"File validation failed for {db_path}: {file_msg}")
            return validation_result
        
        # Step 2: Integrity check
        integrity_ok, integrity_msg, db_info = self.validate_database_integrity(db_path)
        validation_result['integrity_check'] = {
            'passed': integrity_ok, 
            'message': integrity_msg, 
            'info': db_info
        }
        
        if not integrity_ok:
            validation_result['validation_time_seconds'] = time.time() - start_time
            self.logger.error(f"Integrity check failed for {db_path}: {integrity_msg}")
            return validation_result
        
        # Step 3: Functionality test
        func_ok, func_msg, test_results = self.test_database_functionality(db_path)
        validation_result['functionality_test'] = {
            'passed': func_ok,
            'message': func_msg,
            'results': test_results
        }
        
        # Overall status
        if files_ok and integrity_ok and func_ok:
            validation_result['overall_status'] = 'PASSED'
            self.logger.info(f"Database validation PASSED: {db_path}")
        else:
            self.logger.error(f"Database validation FAILED: {db_path}")
        
        validation_result['validation_time_seconds'] = time.time() - start_time
        return validation_result
    
    def validate_release(self, mod: str, release: str, base_path: str = "/var/sequenceserver-data/blast") -> Dict:
        """Validate all databases for a specific MOD release"""
        self.logger.info(f"Starting validation for {mod} {release}")
        terminal.print_header(f"Database Validation: {mod} {release}")
        
        release_path = Path(base_path) / mod / release
        if not release_path.exists():
            error_msg = f"Release directory not found: {release_path}"
            self.logger.error(error_msg)
            return {'error': error_msg, 'databases': []}
        
        # Find all databases
        nin_files = list(release_path.rglob("*.nin"))
        database_paths = [str(nin_file).replace('.nin', '') for nin_file in nin_files]
        
        self.logger.info(f"Found {len(database_paths)} databases to validate")
        
        validation_results = {
            'mod': mod,
            'release': release,
            'validation_start': datetime.now().isoformat(),
            'total_databases': len(database_paths),
            'databases': [],
            'summary': {
                'passed': 0,
                'failed': 0,
                'total_time_seconds': 0
            }
        }
        
        # Validate each database
        start_time = time.time()
        
        with terminal.create_progress() as progress:
            task = progress.add_task(f"Validating {mod} {release}", total=len(database_paths))
            
            for i, db_path in enumerate(database_paths):
                result = self.validate_single_database(db_path)
                validation_results['databases'].append(result)
                
                if result['overall_status'] == 'PASSED':
                    validation_results['summary']['passed'] += 1
                    terminal.print_status(f"✓ Database {i+1}/{len(database_paths)} validated", "success")
                else:
                    validation_results['summary']['failed'] += 1
                    terminal.print_status(f"✗ Database {i+1}/{len(database_paths)} failed validation", "error")
                
                progress.update(task, advance=1)
        
        validation_results['summary']['total_time_seconds'] = time.time() - start_time
        validation_results['validation_end'] = datetime.now().isoformat()
        
        # Save detailed results
        self.save_validation_report(validation_results)
        
        # Print summary
        self.print_validation_summary(validation_results)
        
        return validation_results
    
    def save_validation_report(self, results: Dict):
        """Save detailed validation report to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mod = results.get('mod', 'unknown')
        release = results.get('release', 'unknown')
        
        report_file = self.log_dir / f"validation_report_{mod}_{release}_{timestamp}.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Validation report saved: {report_file}")
        except Exception as e:
            self.logger.error(f"Failed to save validation report: {e}")
    
    def print_validation_summary(self, results: Dict):
        """Print comprehensive validation summary"""
        mod = results.get('mod', 'Unknown')
        release = results.get('release', 'Unknown')
        summary = results.get('summary', {})
        
        terminal.print_header(f"Validation Summary: {mod} {release}")
        
        print(f"Total databases tested: {summary.get('total_time_seconds', 0)}")
        print(f"Databases passed: {summary.get('passed', 0)}")
        print(f"Databases failed: {summary.get('failed', 0)}")
        print(f"Success rate: {(summary.get('passed', 0) / max(1, summary.get('passed', 0) + summary.get('failed', 0))) * 100:.1f}%")
        print(f"Total validation time: {summary.get('total_time_seconds', 0):.1f} seconds")
        
        # Show failed databases
        failed_dbs = [db for db in results.get('databases', []) if db['overall_status'] == 'FAILED']
        if failed_dbs:
            terminal.print_status(f"\nFailed Databases ({len(failed_dbs)}):", "warning")
            for db in failed_dbs[:5]:  # Show first 5
                print(f"  - {Path(db['database_path']).name}: {db.get('file_check', {}).get('message', 'Unknown error')}")
            if len(failed_dbs) > 5:
                print(f"  ... and {len(failed_dbs) - 5} more")
        
        terminal.print_status("Database validation completed", "success")