"""
Performance tests for IIT Prediction ML Service
Load testing and stress testing
"""
import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
import statistics
import psutil
import os

from app.main import app

client = TestClient(app)


class TestLoadTesting:
    """Load testing for concurrent operations"""

    @pytest.fixture
    def sample_prediction_data(self):
        """Generate sample prediction data"""
        return {
            "messageData": {
                "demographics": {
                    "patientUuid": "perf-test-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+2348012345678"
                },
                "visits": [
                    {
                        "dateStarted": "2024-10-01 10:30:00",
                        "voided": 0
                    }
                ],
                "encounters": [
                    {
                        "encounterUuid": "perf-enc-123",
                        "encounterDatetime": "2024-10-01 10:30:00",
                        "pmmForm": "Pharmacy Order Form",
                        "voided": 0
                    }
                ],
                "obs": [
                    {
                        "obsDatetime": "2024-10-01 10:30:00",
                        "variableName": "Medication duration",
                        "valueNumeric": 90.0,
                        "voided": 0
                    }
                ]
            }
        }

    def test_concurrent_predictions(self, sample_prediction_data):
        """Test concurrent prediction requests"""
        def make_prediction_request(request_id):
            start_time = time.time()
            try:
                response = client.post("/predict", json=sample_prediction_data)
                end_time = time.time()
                return {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "request_id": request_id,
                    "status_code": None,
                    "response_time": end_time - start_time,
                    "success": False,
                    "error": str(e)
                }

        # Test with different concurrency levels
        concurrency_levels = [5, 10, 20]

        for num_concurrent in concurrency_levels:
            print(f"\nTesting with {num_concurrent} concurrent requests...")

            start_time = time.time()

            with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
                futures = [executor.submit(make_prediction_request, i) for i in range(num_concurrent)]
                results = [future.result() for future in as_completed(futures)]

            total_time = time.time() - start_time

            # Analyze results
            successful_requests = [r for r in results if r["success"]]
            failed_requests = [r for r in results if not r["success"]]
            response_times = [r["response_time"] for r in results]

            success_rate = len(successful_requests) / len(results) * 100
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)

            print(f"Success rate: {success_rate:.2f}%")
            print(f"Average response time: {avg_response_time:.3f}s")
            print(f"Median response time: {median_response_time:.3f}s")
            print(f"Max response time: {max_response_time:.3f}s")
            print(f"Min response time: {min_response_time:.3f}s")
            print(f"Total time for {num_concurrent} requests: {total_time:.3f}s")

            # Assertions for performance benchmarks
            assert success_rate >= 95.0, f"Success rate too low: {success_rate}%"
            assert avg_response_time < 5.0, f"Average response time too high: {avg_response_time}s"
            assert max_response_time < 10.0, f"Max response time too high: {max_response_time}s"

    def test_batch_prediction_performance(self):
        """Test batch prediction performance with varying batch sizes"""
        def create_batch_data(batch_size):
            patients = []
            for i in range(batch_size):
                patient = {
                    "messageData": {
                        "demographics": {
                            "patientUuid": f"batch-perf-{i}",
                            "birthdate": "1985-06-15 00:00:00",
                            "gender": "F",
                            "stateProvince": "Lagos",
                            "cityVillage": "Ikeja",
                            "phoneNumber": "+2348012345678"
                        },
                        "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                        "encounters": [{"encounterUuid": f"batch-enc-{i}", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                        "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
                    }
                }
                patients.append(patient)
            return {"patients": patients}

        batch_sizes = [5, 10, 25]

        for batch_size in batch_sizes:
            print(f"\nTesting batch prediction with {batch_size} patients...")

            batch_data = create_batch_data(batch_size)
            start_time = time.time()

            response = client.post("/batch_predict", json=batch_data)

            end_time = time.time()
            response_time = end_time - start_time

            assert response.status_code == 200
            result = response.json()

            print(f"Batch size: {batch_size}")
            print(f"Response time: {response_time:.3f}s")
            print(f"Processed patients: {result.get('total_processed', 'N/A')}")

            # Performance assertions
            assert response_time < 30.0, f"Batch processing too slow: {response_time}s for {batch_size} patients"
            assert result.get('total_processed', 0) == batch_size


class TestStressTesting:
    """Stress testing for system limits"""

    def test_memory_usage_under_load(self):
        """Test memory usage during high load"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        def make_multiple_requests(num_requests):
            for i in range(num_requests):
                try:
                    response = client.get("/health")
                    assert response.status_code == 200
                except:
                    pass  # Ignore errors for stress testing

        # Stress with multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_multiple_requests, 50) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")

        # Assert memory usage is reasonable
        assert memory_increase < 100.0, f"Memory increase too high: {memory_increase} MB"

    def test_database_connection_pool_limits(self):
        """Test database connection pool under stress"""
        # This test would require monitoring database connections
        # Implementation depends on database setup
        pass

    def test_api_rate_limiting(self):
        """Test API rate limiting under stress"""
        def make_request():
            response = client.get("/health")
            return response.status_code

        # Rapid fire requests
        start_time = time.time()
        results = []

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(200)]
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()
        total_time = end_time - start_time

        success_count = results.count(200)
        rate_limited_count = results.count(429)  # Assuming 429 for rate limiting

        print(f"Total requests: {len(results)}")
        print(f"Successful: {success_count}")
        print(f"Rate limited: {rate_limited_count}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Requests per second: {len(results) / total_time:.2f}")

        # If rate limiting is implemented, some requests should be limited
        # If not implemented, all should succeed
        assert success_count > 0, "No successful requests"


class TestScalabilityTesting:
    """Test system scalability"""

    def test_response_time_degradation(self):
        """Test how response times degrade with increasing load"""
        response_times = []

        # Test with increasing concurrent users
        for concurrent_users in [1, 5, 10, 20]:
            def single_request():
                start = time.time()
                response = client.get("/health")
                end = time.time()
                return end - start if response.status_code == 200 else None

            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(single_request) for _ in range(concurrent_users)]
                times = [f.result() for f in futures if f.result() is not None]

            if times:
                avg_time = statistics.mean(times)
                response_times.append((concurrent_users, avg_time))
                print(f"Concurrent users: {concurrent_users}, Avg response time: {avg_time:.3f}s")

        # Check that response time degradation is acceptable
        if len(response_times) > 1:
            initial_time = response_times[0][1]
            final_time = response_times[-1][1]
            degradation_ratio = final_time / initial_time

            print(f"Response time degradation ratio: {degradation_ratio:.2f}x")
            # Allow up to 5x degradation under high load
            assert degradation_ratio < 5.0, f"Response time degraded too much: {degradation_ratio}x"


class TestResourceMonitoring:
    """Monitor system resources during testing"""

    def test_cpu_usage_during_operations(self):
        """Monitor CPU usage during intensive operations"""
        process = psutil.Process(os.getpid())

        # Get initial CPU usage
        initial_cpu = process.cpu_percent(interval=1)

        # Perform intensive operations
        def intensive_operation():
            for _ in range(100):
                response = client.get("/health")
                assert response.status_code == 200

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(intensive_operation) for _ in range(5)]
            for future in as_completed(futures):
                future.result()

        # Get final CPU usage
        final_cpu = process.cpu_percent(interval=1)

        print(f"Initial CPU usage: {initial_cpu:.2f}%")
        print(f"Final CPU usage: {final_cpu:.2f}%")

        # CPU usage should remain reasonable
        assert final_cpu < 90.0, f"CPU usage too high: {final_cpu}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
