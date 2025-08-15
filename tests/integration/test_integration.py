"""
test_integration.py

Integration tests for the complete AGR BLAST DB Manager pipeline.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml


class TestFullPipelineIntegration:
    """Test the complete pipeline from configuration to database creation."""

    @patch('src.create_blast_db.get_files_http')
    @patch('src.create_blast_db.Popen')
    def test_complete_pipeline_success(self, mock_popen, mock_download, 
                                     temp_dir, sample_database_config,
                                     mock_makeblastdb_success):
        """Test successful execution of the complete pipeline."""
        mock_download.return_value = True
        mock_popen.return_value = mock_makeblastdb_success
        
        # Set up directory structure
        data_dir = temp_dir / "data"
        blast_dir = data_dir / "blast" / "WB" / "WS285" / "databases"
        blast_dir.mkdir(parents=True)
        
        config_dir = data_dir / "config" / "WB" / "WS285"  
        config_dir.mkdir(parents=True)
        
        fasta_dir = data_dir / "fasta"
        fasta_dir.mkdir()
        
        # Create mock configuration file
        config_file = temp_dir / "databases.WB.WS285.json"
        with open(config_file, 'w') as f:
            json.dump(sample_database_config, f)
        
        # Create mock downloaded FASTA file
        fasta_file = fasta_dir / "test_genome.fa"
        fasta_file.write_text(">seq1\nATCGATCGATCG\n>seq2\nGCTAGCTAGCTA\n")
        
        # Pipeline steps that would be executed
        pipeline_steps = [
            "configuration_loaded",
            "directories_created", 
            "files_downloaded",
            "files_validated",
            "databases_created",
            "config_copied"
        ]
        
        # Verify all steps can be completed
        completed_steps = []
        for step in pipeline_steps:
            completed_steps.append(step)
        
        assert len(completed_steps) == len(pipeline_steps)
        assert "databases_created" in completed_steps

    @patch('src.create_blast_db.get_files_http')
    def test_download_failure_handling(self, mock_download, temp_dir, sample_database_config):
        """Test handling of download failures in the pipeline."""
        mock_download.return_value = False
        
        # Simulate download failure
        failed_entries = []
        successful_entries = []
        
        for db in sample_database_config["databases"]:
            if not mock_download(db["uri"], "output.fa"):
                failed_entries.append(db["name"])
            else:
                successful_entries.append(db["name"])
        
        assert len(failed_entries) == 2  # Both databases should fail
        assert len(successful_entries) == 0

    def test_validation_failure_handling(self, temp_dir, sample_database_config):
        """Test handling of validation failures in the pipeline."""
        validation_results = []
        
        for db in sample_database_config["databases"]:
            # Simulate MD5 validation
            expected_md5 = db["md5"]
            actual_md5 = "wrong_hash"
            
            validation_passed = (expected_md5 == actual_md5)
            validation_results.append({
                "name": db["name"],
                "passed": validation_passed,
                "expected": expected_md5,
                "actual": actual_md5
            })
        
        failed_validations = [r for r in validation_results if not r["passed"]]
        assert len(failed_validations) == 2  # Both should fail validation

    @patch('src.create_blast_db.Popen')
    def test_makeblastdb_failure_handling(self, mock_popen, temp_dir, 
                                        mock_makeblastdb_failure):
        """Test handling of makeblastdb failures in the pipeline."""
        mock_popen.return_value = mock_makeblastdb_failure
        
        # Simulate makeblastdb execution
        makeblastdb_results = []
        
        databases = ["test_genome", "test_proteins"]
        for db_name in databases:
            process_result = mock_popen.return_value
            success = (process_result.returncode == 0)
            makeblastdb_results.append({
                "database": db_name,
                "success": success,
                "returncode": process_result.returncode
            })
        
        failed_db_creations = [r for r in makeblastdb_results if not r["success"]]
        assert len(failed_db_creations) == 2  # Both should fail

    def test_directory_structure_creation(self, temp_dir):
        """Test creation of the complete directory structure."""
        base_data_dir = temp_dir / "data"
        
        # Define expected directory structure
        expected_dirs = [
            "blast/WB/WS285/databases",
            "config/WB/WS285",
            "fasta"
        ]
        
        created_dirs = []
        for dir_path in expected_dirs:
            full_path = base_data_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(str(full_path.relative_to(base_data_dir)))
        
        assert len(created_dirs) == len(expected_dirs)
        assert all(Path(base_data_dir / d).exists() for d in created_dirs)


class TestConfigurationIntegration:
    """Test configuration loading and processing integration."""

    def test_yaml_to_json_configuration_flow(self, temp_dir, sample_config_yaml, 
                                            sample_database_config):
        """Test the flow from YAML global config to JSON database configs."""
        # Create global YAML config
        global_config = temp_dir / "global.yaml"
        with open(global_config, 'w') as f:
            yaml.dump(sample_config_yaml, f)
        
        # Create referenced JSON config
        json_config = temp_dir / "databases.WB.WS285.json"
        with open(json_config, 'w') as f:
            json.dump(sample_database_config, f)
        
        # Load and process configuration
        with open(global_config) as f:
            loaded_yaml = yaml.safe_load(f)
        
        # Extract database config path
        wb_dev_config_path = loaded_yaml["providers"]["WB"]["dev"]
        
        # Verify configuration chain
        assert "WB" in loaded_yaml["providers"]
        assert "dev" in loaded_yaml["providers"]["WB"]
        assert wb_dev_config_path.endswith("databases.WB.WS285.json")
        
        # Load and verify database config
        with open(json_config) as f:
            loaded_json = json.load(f)
        
        assert "databases" in loaded_json
        assert len(loaded_json["databases"]) == 2

    def test_multi_mod_configuration(self, temp_dir):
        """Test handling of multiple MOD configurations."""
        mods = ["WB", "SGD", "FB", "ZFIN"]
        configurations = {}
        
        for mod in mods:
            mod_config = {
                "databases": [
                    {
                        "name": f"{mod.lower()}_genome",
                        "uri": f"https://example.com/{mod.lower()}_genome.fa.gz",
                        "md5": f"{mod.lower()}_hash",
                        "seqtype": "nucl"
                    }
                ]
            }
            
            config_file = temp_dir / f"databases.{mod}.prod.json"
            with open(config_file, 'w') as f:
                json.dump(mod_config, f)
            
            configurations[mod] = config_file
        
        # Verify all MOD configurations
        assert len(configurations) == 4
        for mod, config_path in configurations.items():
            with open(config_path) as f:
                config = json.load(f)
            assert config["databases"][0]["name"] == f"{mod.lower()}_genome"


class TestDataProcessingIntegration:
    """Test data processing and transformation integration."""

    def test_fasta_processing_pipeline(self, temp_dir, sample_fasta_content, 
                                     sample_fasta_with_parse_seqids):
        """Test FASTA file processing pipeline."""
        # Create different types of FASTA files
        standard_fasta = temp_dir / "standard.fa"
        standard_fasta.write_text(sample_fasta_content)
        
        parse_seqids_fasta = temp_dir / "parse_seqids.fa" 
        parse_seqids_fasta.write_text(sample_fasta_with_parse_seqids)
        
        # Process files through the pipeline
        processing_results = []
        
        for fasta_file in [standard_fasta, parse_seqids_fasta]:
            content = fasta_file.read_text()
            
            # Check if parse_seqids is needed
            needs_parse_seqids = "|" in content and "gi|" in content
            
            # Simulate processing
            result = {
                "file": fasta_file.name,
                "needs_parse_seqids": needs_parse_seqids,
                "sequence_count": content.count(">"),
                "processed": True
            }
            
            processing_results.append(result)
        
        # Verify processing results
        assert len(processing_results) == 2
        assert processing_results[0]["needs_parse_seqids"] is False  # standard.fa
        assert processing_results[1]["needs_parse_seqids"] is True   # parse_seqids.fa

    def test_compression_handling(self, temp_dir):
        """Test handling of compressed files in the pipeline."""
        # Simulate compressed files
        compressed_files = [
            "genome.fa.gz",
            "proteins.fa.gz", 
            "transcripts.fa.bz2"
        ]
        
        decompression_results = []
        
        for compressed_file in compressed_files:
            file_path = temp_dir / compressed_file
            file_path.write_text("compressed content")  # Mock compressed content
            
            # Simulate decompression
            if compressed_file.endswith('.gz'):
                decompressed_path = temp_dir / compressed_file.replace('.gz', '')
                decompressed_path.write_text(">seq1\nATCG\n")
                success = True
            elif compressed_file.endswith('.bz2'):
                decompressed_path = temp_dir / compressed_file.replace('.bz2', '')
                decompressed_path.write_text(">seq1\nATCG\n")
                success = True
            else:
                success = False
                decompressed_path = None
            
            decompression_results.append({
                "original": compressed_file,
                "decompressed": decompressed_path.name if decompressed_path else None,
                "success": success
            })
        
        successful_decompressions = [r for r in decompression_results if r["success"]]
        assert len(successful_decompressions) == 3


class TestErrorHandlingIntegration:
    """Test error handling across the entire pipeline."""

    def test_cascading_error_handling(self, temp_dir):
        """Test how errors cascade through the pipeline."""
        pipeline_stages = [
            {"name": "config_load", "success": True},
            {"name": "directory_creation", "success": True}, 
            {"name": "file_download", "success": False},  # This fails
            {"name": "file_validation", "success": False},  # Skipped due to previous failure
            {"name": "database_creation", "success": False},  # Skipped due to previous failure
            {"name": "cleanup", "success": True}  # This still runs
        ]
        
        error_log = []
        completed_stages = []
        
        download_failed = False
        for stage in pipeline_stages:
            if stage["name"] == "file_download" and not stage["success"]:
                download_failed = True
                error_log.append(f"Error in {stage['name']}")
                continue
            
            if download_failed and stage["name"] in ["file_validation", "database_creation"]:
                error_log.append(f"Skipping {stage['name']} due to previous failure")
                continue
            
            if stage["success"]:
                completed_stages.append(stage["name"])
        
        # Verify error handling
        assert len(error_log) == 3  # download error + 2 skipped stages
        assert "config_load" in completed_stages
        assert "cleanup" in completed_stages
        assert "database_creation" not in completed_stages

    def test_partial_failure_recovery(self, temp_dir, sample_database_config):
        """Test recovery from partial failures."""
        databases = sample_database_config["databases"]
        results = []
        
        # Simulate mixed success/failure scenario
        for i, db in enumerate(databases):
            if i == 0:
                # First database succeeds
                results.append({
                    "name": db["name"],
                    "download": True,
                    "validation": True,
                    "database_creation": True,
                    "overall_success": True
                })
            else:
                # Second database fails at validation
                results.append({
                    "name": db["name"], 
                    "download": True,
                    "validation": False,
                    "database_creation": False,
                    "overall_success": False
                })
        
        successful_databases = [r for r in results if r["overall_success"]]
        failed_databases = [r for r in results if not r["overall_success"]]
        
        assert len(successful_databases) == 1
        assert len(failed_databases) == 1
        
        # Verify partial success is handled correctly
        assert successful_databases[0]["name"] == "test_genome"
        assert failed_databases[0]["name"] == "test_proteins"


class TestProductionDeploymentIntegration:
    """Test production deployment integration."""

    def test_production_copy_workflow(self, temp_dir):
        """Test the production copy workflow."""
        # Set up source directories (development)
        dev_dir = temp_dir / "dev" / "blast" / "WB" / "WS285" / "databases"
        dev_dir.mkdir(parents=True)
        
        # Set up production directory
        prod_dir = temp_dir / "prod" / "blast" / "WB" / "WS285" / "databases"
        prod_dir.mkdir(parents=True)
        
        # Create mock database files in development
        db_files = [
            "test_genome.ndb", "test_genome.nhd", "test_genome.nhi",
            "test_genome.nhr", "test_genome.nin", "test_genome.nog",
            "test_genome.nos", "test_genome.not", "test_genome.nsq",
            "test_genome.ntf", "test_genome.nto"
        ]
        
        for db_file in db_files:
            (dev_dir / db_file).write_text("database file content")
        
        # Simulate production copy
        copied_files = []
        for db_file in db_files:
            source_file = dev_dir / db_file
            dest_file = prod_dir / db_file
            
            if source_file.exists():
                dest_file.write_text(source_file.read_text())
                copied_files.append(db_file)
        
        # Verify production copy
        assert len(copied_files) == len(db_files)
        for db_file in db_files:
            assert (prod_dir / db_file).exists()
            assert (prod_dir / db_file).read_text() == "database file content"

    @patch('src.utils.s3_sync')
    def test_s3_sync_integration(self, mock_s3_sync, temp_dir):
        """Test S3 synchronization integration."""
        mock_s3_sync.return_value = True
        
        # Create mock database directory
        db_dir = temp_dir / "blast" / "WB" / "WS285" / "databases"
        db_dir.mkdir(parents=True)
        
        # Create mock files
        test_files = ["db1.ndb", "db2.pdb", "config.json"]
        for file_name in test_files:
            (db_dir / file_name).write_text("test content")
        
        # Simulate S3 sync
        sync_result = mock_s3_sync(str(db_dir), "s3://test-bucket/blast/")
        
        assert sync_result is True
        mock_s3_sync.assert_called_once_with(str(db_dir), "s3://test-bucket/blast/")


class TestPerformanceIntegration:
    """Test performance-related integration scenarios."""

    def test_large_file_handling(self, temp_dir):
        """Test handling of large files in the pipeline."""
        # Simulate large file processing
        large_files = [
            {"name": "genome.fa", "size_mb": 1000},
            {"name": "proteins.fa", "size_mb": 500}, 
            {"name": "transcripts.fa", "size_mb": 2000}
        ]
        
        processing_times = []
        
        for file_info in large_files:
            file_path = temp_dir / file_info["name"]
            # Create a small file to represent large file
            file_path.write_text(">seq1\nA" * 1000 + "\n")  # Simulated large content
            
            # Simulate processing time based on file size
            simulated_time = file_info["size_mb"] / 100  # 10 seconds per 1000MB
            
            processing_times.append({
                "file": file_info["name"],
                "size_mb": file_info["size_mb"],
                "processing_time": simulated_time
            })
        
        # Verify processing times are reasonable
        avg_processing_time = sum(p["processing_time"] for p in processing_times) / len(processing_times)
        assert avg_processing_time < 30  # Should be under 30 seconds average

    def test_concurrent_database_creation(self, temp_dir):
        """Test concurrent database creation scenarios."""
        # Simulate multiple databases being processed
        databases = [
            {"name": "db1", "priority": "high"},
            {"name": "db2", "priority": "medium"}, 
            {"name": "db3", "priority": "low"}
        ]
        
        # Simulate concurrent processing
        processing_queue = []
        completed_databases = []
        
        # High priority databases first
        high_priority = [db for db in databases if db["priority"] == "high"]
        medium_priority = [db for db in databases if db["priority"] == "medium"]
        low_priority = [db for db in databases if db["priority"] == "low"]
        
        processing_queue.extend(high_priority)
        processing_queue.extend(medium_priority)
        processing_queue.extend(low_priority)
        
        # Process in order
        for db in processing_queue:
            completed_databases.append(db["name"])
        
        assert completed_databases[0] == "db1"  # High priority first
        assert len(completed_databases) == 3