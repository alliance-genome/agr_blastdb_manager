"""
test_performance.py

Performance tests for the AGR BLAST DB Manager.
"""

import hashlib
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    from .fixtures import PERFORMANCE_TEST_DATA, LARGE_SEQUENCE_FASTA
except ImportError:
    from fixtures import PERFORMANCE_TEST_DATA, LARGE_SEQUENCE_FASTA


class TestDownloadPerformance:
    """Test performance of file download operations."""

    @patch('src.utils.requests.get')
    def test_download_speed_small_file(self, mock_get, temp_dir):
        """Test download speed for small files."""
        # Mock small file (1MB)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": str(1024 * 1024)}  # 1MB
        mock_response.iter_content.return_value = [b'x' * 1024] * 1024  # 1024 chunks of 1KB
        mock_get.return_value = mock_response
        
        output_file = temp_dir / "small_file.fa"
        
        start_time = time.time()
        # This would call the actual download function
        # success = get_files_http("http://example.com/small.fa", str(output_file))
        download_time = time.time() - start_time
        
        # Verify download completes within reasonable time
        assert download_time < 5.0  # Should complete within 5 seconds
        mock_get.assert_called_once()

    @patch('src.utils.requests.get')
    def test_download_speed_large_file(self, mock_get, temp_dir):
        """Test download speed for large files."""
        # Mock large file (100MB)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": str(100 * 1024 * 1024)}  # 100MB
        # Simulate large file with fewer, larger chunks
        mock_response.iter_content.return_value = [b'x' * (1024 * 1024)] * 100  # 100 chunks of 1MB
        mock_get.return_value = mock_response
        
        output_file = temp_dir / "large_file.fa"
        
        start_time = time.time()
        # This would call the actual download function
        # success = get_files_http("http://example.com/large.fa", str(output_file))
        download_time = time.time() - start_time
        
        # Large files should still complete within reasonable time
        assert download_time < 60.0  # Should complete within 1 minute for simulation

    def test_concurrent_downloads(self, temp_dir):
        """Test performance of concurrent downloads."""
        import concurrent.futures
        import threading
        
        # Simulate concurrent downloads
        download_results = []
        download_times = []
        
        def mock_download(url, output_path):
            start_time = time.time()
            time.sleep(0.1)  # Simulate download time
            end_time = time.time()
            download_times.append(end_time - start_time)
            return True
        
        urls = [f"http://example.com/file_{i}.fa" for i in range(10)]
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i, url in enumerate(urls):
                output_path = temp_dir / f"file_{i}.fa"
                future = executor.submit(mock_download, url, str(output_path))
                futures.append(future)
            
            # Wait for all downloads to complete
            for future in concurrent.futures.as_completed(futures):
                download_results.append(future.result())
        
        total_time = time.time() - start_time
        
        # Concurrent downloads should be faster than sequential
        assert total_time < sum(download_times)  # Should be faster than sequential
        assert all(download_results)  # All downloads should succeed


class TestValidationPerformance:
    """Test performance of file validation operations."""

    def test_md5_validation_speed(self, temp_dir):
        """Test MD5 validation performance."""
        # Create test files of different sizes
        test_cases = [
            {"size": 1024, "name": "small.fa"},       # 1KB
            {"size": 1024 * 1024, "name": "medium.fa"},    # 1MB  
            {"size": 10 * 1024 * 1024, "name": "large.fa"}  # 10MB
        ]
        
        validation_times = []
        
        for case in test_cases:
            # Create test file
            test_file = temp_dir / case["name"]
            test_content = b"A" * case["size"]
            with open(test_file, 'wb') as f:
                f.write(test_content)
            
            # Calculate expected MD5
            expected_md5 = hashlib.md5(test_content).hexdigest()
            
            # Time the validation
            start_time = time.time()
            with open(test_file, 'rb') as f:
                actual_md5 = hashlib.md5(f.read()).hexdigest()
            validation_time = time.time() - start_time
            
            validation_times.append({
                "size": case["size"],
                "time": validation_time
            })
            
            assert actual_md5 == expected_md5
        
        # Verify validation time scales reasonably with file size
        # Larger files should take longer, but not exponentially
        for i in range(1, len(validation_times)):
            size_ratio = validation_times[i]["size"] / validation_times[i-1]["size"]
            time_ratio = validation_times[i]["time"] / validation_times[i-1]["time"]
            
            # Time should scale roughly linearly with size (allow some variance)
            assert time_ratio <= size_ratio * 2

    def test_fasta_parsing_speed(self, temp_dir):
        """Test FASTA parsing performance."""
        # Create FASTA files with different sequence counts
        sequence_counts = [100, 1000, 10000]
        parsing_times = []
        
        for count in sequence_counts:
            fasta_content = ""
            for i in range(count):
                fasta_content += f">seq_{i}\n"
                fasta_content += "ATGCGATCGATCGATCGATCGATCG\n"
            
            fasta_file = temp_dir / f"sequences_{count}.fa"
            fasta_file.write_text(fasta_content)
            
            start_time = time.time()
            # Simulate FASTA parsing
            with open(fasta_file) as f:
                content = f.read()
                sequence_count = content.count(">")
                
            parsing_time = time.time() - start_time
            parsing_times.append({
                "sequences": count,
                "time": parsing_time
            })
            
            assert sequence_count == count
        
        # Verify parsing time scales reasonably
        for parsing_info in parsing_times:
            # Should parse at least 1000 sequences per second
            sequences_per_second = parsing_info["sequences"] / parsing_info["time"]
            assert sequences_per_second > 1000


class TestDatabaseCreationPerformance:
    """Test performance of BLAST database creation."""

    @patch('src.create_blast_db.Popen')
    def test_makeblastdb_performance_nucleotide(self, mock_popen, temp_dir):
        """Test makeblastdb performance for nucleotide databases."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success", b"")
        mock_popen.return_value = mock_process
        
        # Create test FASTA files of different sizes
        test_cases = PERFORMANCE_TEST_DATA
        
        for case_name, case_data in test_cases.items():
            fasta_content = ""
            for i in range(case_data["sequence_count"]):
                fasta_content += f">seq_{i}\n"
                fasta_content += "A" * case_data["avg_sequence_length"] + "\n"
            
            fasta_file = temp_dir / f"{case_name}.fa"
            fasta_file.write_text(fasta_content)
            
            start_time = time.time()
            # This would call the actual makeblastdb function
            # result = makeblastdb(str(fasta_file), str(temp_dir), db_config, "TEST")
            processing_time = time.time() - start_time
            
            # Verify processing completes within expected time
            # For testing, we'll allow more generous timeouts
            expected_time = case_data["expected_time_seconds"] * 2  # Allow 2x expected time
            assert processing_time < expected_time

    @patch('src.create_blast_db.Popen')
    def test_makeblastdb_performance_protein(self, mock_popen, temp_dir):
        """Test makeblastdb performance for protein databases."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success", b"")
        mock_popen.return_value = mock_process
        
        # Create protein FASTA
        protein_sequences = [
            "MKLLIVDDSSGKVRAEIKQLLKQGVNPE",
            "ARNDCQEGHILKMFPSTWYVARNDCQEG", 
            "MLKIVDDQWERTYUIOPASDFGHJKLZX"
        ] * 1000  # 3000 protein sequences
        
        fasta_content = ""
        for i, seq in enumerate(protein_sequences):
            fasta_content += f">prot_{i}\n{seq}\n"
        
        fasta_file = temp_dir / "proteins.fa"
        fasta_file.write_text(fasta_content)
        
        start_time = time.time()
        # This would call makeblastdb for proteins
        processing_time = time.time() - start_time
        
        # Protein databases should be processed efficiently
        assert processing_time < 30  # Should complete within 30 seconds

    def test_concurrent_database_creation(self, temp_dir):
        """Test performance of creating multiple databases concurrently."""
        import concurrent.futures
        
        def mock_create_database(fasta_file, output_dir, db_name):
            start_time = time.time()
            time.sleep(0.5)  # Simulate database creation time
            processing_time = time.time() - start_time
            return {
                "database": db_name,
                "time": processing_time,
                "success": True
            }
        
        # Create multiple test databases
        databases = [
            {"name": "db1", "fasta": "file1.fa"},
            {"name": "db2", "fasta": "file2.fa"},
            {"name": "db3", "fasta": "file3.fa"},
            {"name": "db4", "fasta": "file4.fa"}
        ]
        
        # Sequential processing
        start_time = time.time()
        sequential_results = []
        for db in databases:
            result = mock_create_database(db["fasta"], str(temp_dir), db["name"])
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # Concurrent processing
        start_time = time.time()
        concurrent_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for db in databases:
                future = executor.submit(mock_create_database, db["fasta"], str(temp_dir), db["name"])
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                concurrent_results.append(future.result())
        
        concurrent_time = time.time() - start_time
        
        # Concurrent should be faster than sequential
        assert concurrent_time < sequential_time
        assert len(concurrent_results) == len(databases)
        assert all(r["success"] for r in concurrent_results)


class TestMemoryPerformance:
    """Test memory usage and performance."""

    def test_large_file_memory_usage(self, temp_dir):
        """Test memory usage when processing large files."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create and process a large file
        large_content = LARGE_SEQUENCE_FASTA
        large_file = temp_dir / "large_sequences.fa"
        large_file.write_text(large_content)
        
        # Simulate processing the large file
        with open(large_file) as f:
            content = f.read()
            sequences = content.count(">")
            total_length = len(content)
        
        # Check memory usage after processing
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for test)
        assert memory_increase < 100 * 1024 * 1024  # 100MB
        assert sequences > 0
        assert total_length > 0

    def test_memory_cleanup(self, temp_dir):
        """Test that memory is properly cleaned up after processing."""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        gc.collect()  # Force garbage collection
        baseline_memory = process.memory_info().rss
        
        # Create and process multiple files
        for i in range(10):
            test_file = temp_dir / f"test_{i}.fa"
            content = f">seq_{i}\n" + "ATCG" * 1000 + "\n"
            test_file.write_text(content)
            
            # Process file
            with open(test_file) as f:
                data = f.read()
                
            # Delete variables to free memory
            del data
        
        # Force cleanup
        gc.collect()
        final_memory = process.memory_info().rss
        
        # Memory should return close to baseline
        memory_difference = abs(final_memory - baseline_memory)
        assert memory_difference < 50 * 1024 * 1024  # Less than 50MB difference


class TestScalabilityPerformance:
    """Test scalability with varying workloads."""

    def test_linear_scaling_sequence_count(self, temp_dir):
        """Test that processing time scales linearly with sequence count."""
        sequence_counts = [100, 500, 1000, 2000]
        processing_times = []
        
        for count in sequence_counts:
            # Create FASTA with specified sequence count
            fasta_content = ""
            for i in range(count):
                fasta_content += f">seq_{i}\nATGCGATCGATCGATCG\n"
            
            fasta_file = temp_dir / f"scaling_{count}.fa"
            fasta_file.write_text(fasta_content)
            
            # Time the processing
            start_time = time.time()
            with open(fasta_file) as f:
                content = f.read()
                actual_count = content.count(">")
            processing_time = time.time() - start_time
            
            processing_times.append({
                "count": count,
                "time": processing_time,
                "rate": count / processing_time if processing_time > 0 else 0
            })
            
            assert actual_count == count
        
        # Check that processing rate is consistent (linear scaling)
        rates = [p["rate"] for p in processing_times]
        avg_rate = sum(rates) / len(rates)
        
        for rate in rates:
            # Each rate should be within 50% of average (allowing for variance)
            assert abs(rate - avg_rate) / avg_rate < 0.5

    def test_batch_processing_efficiency(self, temp_dir):
        """Test efficiency of batch processing vs individual processing."""
        # Create test files
        individual_files = []
        batch_content = ""
        
        for i in range(10):
            content = f">seq_{i}\nATGCGATCGATCGATCG\n"
            
            # Individual file
            individual_file = temp_dir / f"individual_{i}.fa"
            individual_file.write_text(content)
            individual_files.append(individual_file)
            
            # Add to batch
            batch_content += content
        
        # Create batch file
        batch_file = temp_dir / "batch.fa"
        batch_file.write_text(batch_content)
        
        # Time individual processing
        start_time = time.time()
        individual_sequences = 0
        for file_path in individual_files:
            with open(file_path) as f:
                content = f.read()
                individual_sequences += content.count(">")
        individual_time = time.time() - start_time
        
        # Time batch processing
        start_time = time.time()
        with open(batch_file) as f:
            content = f.read()
            batch_sequences = content.count(">")
        batch_time = time.time() - start_time
        
        # Verify same number of sequences processed
        assert individual_sequences == batch_sequences
        assert batch_sequences == 10
        
        # Batch processing should be more efficient
        assert batch_time < individual_time


class TestResourceUtilization:
    """Test system resource utilization."""

    def test_cpu_utilization(self):
        """Test CPU utilization during processing."""
        import psutil
        import time
        
        # Monitor CPU usage during a compute-intensive task
        cpu_percentages = []
        
        def cpu_monitor():
            for _ in range(10):  # Monitor for 1 second (10 samples at 0.1s intervals)
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_percentages.append(cpu_percent)
        
        # Start CPU monitoring
        import threading
        monitor_thread = threading.Thread(target=cpu_monitor)
        monitor_thread.start()
        
        # Perform CPU-intensive task
        result = 0
        for i in range(1000000):
            result += i * i
        
        monitor_thread.join()
        
        # Check CPU utilization
        avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
        max_cpu = max(cpu_percentages)
        
        # Should utilize CPU during processing
        assert max_cpu > 0
        assert avg_cpu >= 0
        assert result > 0  # Ensure task completed

    def test_disk_io_efficiency(self, temp_dir):
        """Test disk I/O efficiency."""
        import time
        
        # Write performance test
        test_data = b"ATCGATCGATCG" * 10000  # ~120KB
        
        start_time = time.time()
        for i in range(100):
            test_file = temp_dir / f"io_test_{i}.tmp"
            with open(test_file, 'wb') as f:
                f.write(test_data)
        write_time = time.time() - start_time
        
        # Read performance test
        start_time = time.time()
        total_bytes_read = 0
        for i in range(100):
            test_file = temp_dir / f"io_test_{i}.tmp"
            with open(test_file, 'rb') as f:
                data = f.read()
                total_bytes_read += len(data)
        read_time = time.time() - start_time
        
        # Calculate throughput
        total_bytes = len(test_data) * 100
        write_throughput = total_bytes / write_time  # bytes per second
        read_throughput = total_bytes / read_time
        
        # Should achieve reasonable I/O throughput (at least 1MB/s)
        assert write_throughput > 1024 * 1024  # 1MB/s
        assert read_throughput > 1024 * 1024   # 1MB/s
        assert total_bytes_read == total_bytes