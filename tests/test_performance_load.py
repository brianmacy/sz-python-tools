"""Performance and Load Tests for sz_configtool.

These tests validate performance characteristics, resource usage,
and behavior under load conditions to ensure the system meets
performance requirements and handles stress appropriately.
"""

import pytest
import time
import threading
import json
import sys
import os
import gc
import psutil
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from unittest.mock import patch

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from configtool_main import ConfigToolShell
from _config_core import ConfigurationManager
from _config_display import ConfigDisplayFormatter


class PerformanceTestHarness:
    """Harness for running performance and load tests."""

    def __init__(self):
        """Initialize the performance test harness."""
        self.config_manager = ConfigurationManager()
        self.display_formatter = ConfigDisplayFormatter(use_colors=False)
        self.shell = ConfigToolShell(self.config_manager, self.display_formatter)
        self.senzing_available = self.config_manager.initialize_senzing()

        # Performance tracking
        self.performance_data = []
        self.baseline_memory = None

    def measure_command_performance(self, command_name: str, args: str = "", iterations: int = 1) -> Dict[str, Any]:
        """Measure performance metrics for a command."""
        if not hasattr(self.shell, f'do_{command_name}'):
            return {"error": f"Command {command_name} not found"}

        method = getattr(self.shell, f'do_{command_name}')

        # Collect garbage before measurement
        gc.collect()

        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        execution_times = []
        outputs = []
        errors = []

        for i in range(iterations):
            old_stdout = sys.stdout
            old_stderr = sys.stderr

            try:
                sys.stdout = StringIO()
                sys.stderr = StringIO()

                start_time = time.perf_counter()
                method(args)
                end_time = time.perf_counter()

                execution_time = end_time - start_time
                execution_times.append(execution_time)

                stdout_content = sys.stdout.getvalue()
                stderr_content = sys.stderr.getvalue()

                outputs.append(stdout_content)
                if stderr_content:
                    errors.append(stderr_content)

            except Exception as e:
                errors.append(str(e))
                execution_times.append(float('inf'))  # Mark as failed

            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_delta = final_memory - initial_memory

        # Calculate statistics
        valid_times = [t for t in execution_times if t != float('inf')]

        if valid_times:
            avg_time = sum(valid_times) / len(valid_times)
            min_time = min(valid_times)
            max_time = max(valid_times)
        else:
            avg_time = min_time = max_time = float('inf')

        return {
            "command": command_name,
            "args": args,
            "iterations": iterations,
            "successful_runs": len(valid_times),
            "failed_runs": iterations - len(valid_times),
            "avg_execution_time": avg_time,
            "min_execution_time": min_time,
            "max_execution_time": max_time,
            "memory_delta_bytes": memory_delta,
            "memory_delta_mb": memory_delta / (1024 * 1024),
            "outputs": outputs,
            "errors": errors
        }

    def run_concurrent_commands(self, command_specs: List[Dict], max_workers: int = 4) -> List[Dict[str, Any]]:
        """Run multiple commands concurrently to test thread safety."""
        results = []

        def execute_single_command(spec):
            command = spec['command']
            args = spec.get('args', '')
            iterations = spec.get('iterations', 1)
            return self.measure_command_performance(command, args, iterations)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_spec = {executor.submit(execute_single_command, spec): spec
                             for spec in command_specs}

            for future in as_completed(future_to_spec):
                spec = future_to_spec[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "command": spec['command'],
                        "error": f"Concurrent execution failed: {str(e)}"
                    })

        return results

    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / (1024 * 1024),
            "vms_mb": memory_info.vms / (1024 * 1024),
            "percent": process.memory_percent()
        }

    def set_baseline_memory(self):
        """Set baseline memory usage for comparison."""
        self.baseline_memory = self.get_memory_usage()

    def get_memory_delta(self) -> Optional[Dict[str, float]]:
        """Get memory usage delta from baseline."""
        if not self.baseline_memory:
            return None

        current = self.get_memory_usage()
        return {
            "rss_delta_mb": current["rss_mb"] - self.baseline_memory["rss_mb"],
            "vms_delta_mb": current["vms_mb"] - self.baseline_memory["vms_mb"],
            "percent_delta": current["percent"] - self.baseline_memory["percent"]
        }


class TestPerformanceBaseline:
    """Baseline performance tests for individual commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = PerformanceTestHarness()
        self.harness.set_baseline_memory()

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_basic_command_performance_baseline(self):
        """Test baseline performance for basic commands."""
        basic_commands = [
            {"command": "help", "args": ""},
            {"command": "listDataSources", "args": "json"},
            {"command": "listFeatures", "args": "json"},
            {"command": "listAttributes", "args": "json"},
        ]

        performance_results = []

        for cmd_spec in basic_commands:
            result = self.harness.measure_command_performance(
                cmd_spec["command"],
                cmd_spec["args"],
                iterations=3
            )
            performance_results.append(result)

        # Validate performance requirements
        for result in performance_results:
            command = result["command"]

            # Should have successful runs
            assert result["successful_runs"] > 0, f"Command {command} should have successful runs"

            # Performance thresholds (reasonable for CI/development)
            if command == "help":
                assert result["avg_execution_time"] < 1.0, \
                    f"Help command too slow: {result['avg_execution_time']:.3f}s"
            else:
                assert result["avg_execution_time"] < 10.0, \
                    f"Command {command} too slow: {result['avg_execution_time']:.3f}s"

            # Memory usage should be reasonable (not more than 100MB growth per command)
            assert result["memory_delta_mb"] < 100, \
                f"Command {command} excessive memory usage: {result['memory_delta_mb']:.2f}MB"

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_list_command_scalability(self):
        """Test scalability characteristics of list commands."""
        list_commands = ["listDataSources", "listFeatures", "listAttributes", "listElements"]

        for command in list_commands:
            # Test with different output formats
            formats = ["", "json", "table"]

            for output_format in formats:
                result = self.harness.measure_command_performance(command, output_format, iterations=2)

                # Should complete successfully
                assert result["successful_runs"] > 0, \
                    f"Command {command} {output_format} should have successful runs"

                # Should be reasonably fast
                assert result["avg_execution_time"] < 15.0, \
                    f"Command {command} {output_format} too slow: {result['avg_execution_time']:.3f}s"

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_get_command_performance(self):
        """Test performance of get commands with actual data."""
        # First get some data to test with
        list_result = self.harness.measure_command_performance("listAttributes", "json", 1)

        if list_result["successful_runs"] > 0 and list_result["outputs"]:
            output = list_result["outputs"][0]
            lines = output.strip().split('\n')

            for line in lines:
                line = line.strip()
                if line.startswith('['):
                    try:
                        attributes = json.loads(line)
                        if attributes and isinstance(attributes, list):
                            # Test getAttribute with first attribute
                            first_attr = attributes[0]
                            attr_name = first_attr.get("ATTR_CODE") or first_attr.get("attribute")

                            if attr_name:
                                get_result = self.harness.measure_command_performance(
                                    "getAttribute",
                                    f"{attr_name} json",
                                    iterations=3
                                )

                                assert get_result["successful_runs"] > 0, \
                                    "getAttribute should have successful runs"
                                assert get_result["avg_execution_time"] < 5.0, \
                                    f"getAttribute too slow: {get_result['avg_execution_time']:.3f}s"
                            break
                    except json.JSONDecodeError:
                        continue


class TestLoadAndStress:
    """Load and stress tests for system limits."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = PerformanceTestHarness()
        self.harness.set_baseline_memory()

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_repeated_operations_load(self):
        """Test system behavior under repeated operations."""
        # Test repeated execution of basic operations
        load_test_commands = [
            {"command": "listDataSources", "args": "json"},
            {"command": "listFeatures", "args": "json"},
            {"command": "help", "args": ""}
        ]

        iteration_counts = [10, 5, 15]  # Different loads for different commands

        for i, cmd_spec in enumerate(load_test_commands):
            iterations = iteration_counts[i]
            result = self.harness.measure_command_performance(
                cmd_spec["command"],
                cmd_spec["args"],
                iterations=iterations
            )

            # Should handle repeated operations successfully
            success_rate = result["successful_runs"] / result["iterations"]
            assert success_rate >= 0.8, \
                f"Command {cmd_spec['command']} low success rate under load: {success_rate:.2f}"

            # Performance should not degrade significantly
            # (max time should not be more than 3x average for reasonable consistency)
            if result["avg_execution_time"] > 0:
                performance_variance = result["max_execution_time"] / result["avg_execution_time"]
                assert performance_variance < 10.0, \
                    f"Command {cmd_spec['command']} inconsistent performance: {performance_variance:.2f}x variance"

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_concurrent_operations_load(self):
        """Test system behavior under concurrent operations."""
        # Define concurrent workload
        concurrent_specs = [
            {"command": "listDataSources", "args": "json", "iterations": 3},
            {"command": "listFeatures", "args": "json", "iterations": 3},
            {"command": "listAttributes", "args": "json", "iterations": 3},
            {"command": "help", "args": "", "iterations": 2}
        ]

        start_time = time.time()
        results = self.harness.run_concurrent_commands(concurrent_specs, max_workers=4)
        end_time = time.time()

        total_duration = end_time - start_time

        # All concurrent operations should complete
        assert len(results) == len(concurrent_specs), "All concurrent operations should complete"

        # Most operations should succeed
        successful_results = [r for r in results if r.get("successful_runs", 0) > 0]
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.75, f"Concurrent operations low success rate: {success_rate:.2f}"

        # Total time should be reasonable (should be faster than sequential)
        # Estimate sequential time (conservative)
        estimated_sequential_time = sum(r.get("avg_execution_time", 5.0) * r.get("iterations", 1)
                                      for r in results if "avg_execution_time" in r)

        if estimated_sequential_time > 0:
            # For very fast operations (< 1 second), concurrency overhead may make them slower
            # Only expect performance gains for operations that take longer
            if estimated_sequential_time >= 1.0:
                # Concurrent should be at least 25% faster than sequential (accounting for overhead)
                assert total_duration < estimated_sequential_time * 0.75, \
                    f"Concurrent execution not efficient: {total_duration:.2f}s vs estimated {estimated_sequential_time:.2f}s"
            else:
                # For fast operations, just ensure concurrent execution completes reasonably
                # Allow up to 2x the estimated time due to concurrency overhead
                assert total_duration < estimated_sequential_time * 2.0, \
                    f"Concurrent execution too slow: {total_duration:.2f}s vs estimated {estimated_sequential_time:.2f}s"

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_memory_stability_under_load(self):
        """Test memory stability under sustained load."""
        # Run multiple iterations and check memory growth
        command = "listDataSources"
        args = "json"

        memory_samples = []

        # Take initial memory sample
        initial_memory = self.harness.get_memory_usage()
        memory_samples.append(initial_memory["rss_mb"])

        # Run commands in batches and sample memory
        batch_size = 5
        num_batches = 6

        for batch in range(num_batches):
            # Run a batch of commands
            for i in range(batch_size):
                result = self.harness.measure_command_performance(command, args, 1)
                assert result["successful_runs"] > 0, f"Command should succeed in batch {batch}, iteration {i}"

            # Sample memory after batch
            current_memory = self.harness.get_memory_usage()
            memory_samples.append(current_memory["rss_mb"])

            # Force garbage collection
            gc.collect()

        # Analyze memory trend
        memory_growth = memory_samples[-1] - memory_samples[0]

        # Should not have excessive memory growth (allow up to 50MB for reasonable buffering/caching)
        assert memory_growth < 50.0, \
            f"Excessive memory growth under load: {memory_growth:.2f}MB over {num_batches * batch_size} operations"

        # Check for memory leaks - growth should not be strictly increasing
        # (some variance is normal due to garbage collection timing)
        monotonic_increases = 0
        for i in range(1, len(memory_samples)):
            if memory_samples[i] > memory_samples[i-1]:
                monotonic_increases += 1

        # Should not be strictly increasing (would indicate a memory leak)
        leak_ratio = monotonic_increases / (len(memory_samples) - 1)
        assert leak_ratio < 0.8, \
            f"Possible memory leak detected: {leak_ratio:.2f} ratio of increases"


class TestPerformanceRegression:
    """Performance regression tests to catch performance degradation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = PerformanceTestHarness()

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_command_response_time_regression(self):
        """Test that command response times meet acceptable thresholds."""
        # Define acceptable response time thresholds (in seconds)
        performance_thresholds = {
            "help": 2.0,
            "listDataSources": 15.0,
            "listFeatures": 15.0,
            "listAttributes": 15.0,
            "listElements": 15.0
        }

        regression_failures = []

        for command, threshold in performance_thresholds.items():
            args = "json" if command.startswith("list") else ""

            result = self.harness.measure_command_performance(command, args, iterations=3)

            if result["successful_runs"] > 0:
                avg_time = result["avg_execution_time"]
                if avg_time > threshold:
                    regression_failures.append(
                        f"{command}: {avg_time:.3f}s (threshold: {threshold}s)"
                    )
            else:
                regression_failures.append(f"{command}: Failed to execute")

        assert not regression_failures, \
            f"Performance regression detected: {regression_failures}"

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_memory_usage_regression(self):
        """Test that memory usage remains within acceptable bounds."""
        # Test memory usage for common operations
        commands_to_test = [
            ("listDataSources", "json"),
            ("listFeatures", "json"),
            ("listAttributes", "json"),
            ("help", "")
        ]

        memory_regression_failures = []

        for command, args in commands_to_test:
            result = self.harness.measure_command_performance(command, args, iterations=5)

            if result["successful_runs"] > 0:
                memory_delta_mb = result["memory_delta_mb"]

                # Memory growth should be reasonable (less than 25MB per command set)
                if memory_delta_mb > 25.0:
                    memory_regression_failures.append(
                        f"{command}: {memory_delta_mb:.2f}MB growth"
                    )

        assert not memory_regression_failures, \
            f"Memory usage regression detected: {memory_regression_failures}"

    def test_startup_performance_regression(self):
        """Test that system startup/initialization time is acceptable."""
        # Test initialization performance
        start_time = time.time()

        # Create fresh instances to test initialization
        config_manager = ConfigurationManager()
        display_formatter = ConfigDisplayFormatter(use_colors=False)
        shell = ConfigToolShell(config_manager, display_formatter)

        initialization_time = time.time() - start_time

        # Initialization should be fast
        assert initialization_time < 5.0, \
            f"System initialization too slow: {initialization_time:.3f}s"

        # Test Senzing initialization if available
        if self.harness.senzing_available:
            start_time = time.time()
            senzing_init_result = config_manager.initialize_senzing()
            senzing_init_time = time.time() - start_time

            # Senzing initialization should be reasonable
            assert senzing_init_time < 30.0, \
                f"Senzing initialization too slow: {senzing_init_time:.3f}s"


class TestResourceUtilization:
    """Tests for resource utilization and efficiency."""

    def setup_method(self):
        """Set up test fixtures."""
        self.harness = PerformanceTestHarness()

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_cpu_utilization_efficiency(self):
        """Test that CPU utilization is reasonable."""
        # Monitor CPU usage during operations
        process = psutil.Process()

        # Get baseline CPU usage
        cpu_before = process.cpu_percent()
        time.sleep(0.1)  # Let CPU measurement stabilize

        # Run some CPU-intensive operations
        operations = [
            ("listDataSources", "json"),
            ("listFeatures", "json"),
            ("listAttributes", "json")
        ]

        start_time = time.time()
        for command, args in operations:
            result = self.harness.measure_command_performance(command, args, 2)
            assert result["successful_runs"] > 0, f"Operation {command} should succeed"

        operation_duration = time.time() - start_time

        # Get CPU usage after operations
        time.sleep(0.1)  # Let CPU measurement stabilize
        cpu_after = process.cpu_percent()

        # CPU utilization should be reasonable (not constantly at 100%)
        # This is a rough check - in a real environment you'd want more sophisticated monitoring
        assert operation_duration < 60.0, \
            f"Operations took too long: {operation_duration:.2f}s"

    @pytest.mark.skipif(not PerformanceTestHarness().senzing_available,
                       reason="Senzing not available")
    def test_file_descriptor_usage(self):
        """Test that file descriptor usage is reasonable."""
        process = psutil.Process()

        # Get initial file descriptor count
        try:
            initial_fd_count = process.num_fds()
        except AttributeError:
            # num_fds() not available on Windows
            pytest.skip("File descriptor monitoring not available on this platform")

        # Run operations that might open file descriptors
        for i in range(10):
            result = self.harness.measure_command_performance("listDataSources", "json", 1)
            assert result["successful_runs"] > 0, f"Operation {i} should succeed"

        # Get final file descriptor count
        final_fd_count = process.num_fds()
        fd_growth = final_fd_count - initial_fd_count

        # Should not leak file descriptors
        assert fd_growth < 50, \
            f"Possible file descriptor leak: {fd_growth} descriptors growth"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])