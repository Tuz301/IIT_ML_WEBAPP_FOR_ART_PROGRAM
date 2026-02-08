"""
Performance Validation Testing for IIT ML Service
Real-world load testing and performance validation
"""
import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import csv


@dataclass
class PerformanceMetric:
    """Represents a performance testing metric"""
    endpoint: str
    method: str
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    response_times: List[float]
    error_rate: float
    throughput_rps: float
    timestamp: datetime

    @property
    def avg_response_time(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0

    @property
    def p95_response_time(self) -> float:
        return statistics.quantiles(self.response_times, n=20)[18] if self.response_times else 0

    @property
    def p99_response_time(self) -> float:
        return statistics.quantiles(self.response_times, n=100)[98] if self.response_times else 0

    @property
    def min_response_time(self) -> float:
        return min(self.response_times) if self.response_times else 0

    @property
    def max_response_time(self) -> float:
        return max(self.response_times) if self.response_times else 0


class LoadTester:
    """Real-world load testing framework"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.logger = logging.getLogger(__name__)

    async def setup_session(self):
        """Initialize aiohttp session"""
        self.session = aiohttp.ClientSession()

    async def teardown_session(self):
        """Clean up aiohttp session"""
        if self.session:
            await self.session.close()

    async def make_request(self, endpoint: str, method: str = "GET",
                          data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Tuple[float, bool, int]:
        """Make a single HTTP request and measure response time"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            async with self.session.request(method, url, json=data, headers=headers) as response:
                await response.text()  # Consume response
                response_time = time.time() - start_time
                success = response.status < 400
                return response_time, success, response.status

        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            response_time = time.time() - start_time
            return response_time, False, 0

    async def run_load_test(self, endpoint: str, method: str = "GET",
                           concurrent_users: int = 10, duration_seconds: int = 60,
                           data: Optional[Dict] = None, headers: Optional[Dict] = None) -> PerformanceMetric:
        """Run load test for specific endpoint"""
        self.logger.info(f"Starting load test: {method} {endpoint} with {concurrent_users} concurrent users for {duration_seconds}s")

        response_times = []
        successful_requests = 0
        failed_requests = 0
        total_requests = 0

        async def worker():
            nonlocal successful_requests, failed_requests, total_requests
            end_time = time.time() + duration_seconds

            while time.time() < end_time:
                response_time, success, status_code = await self.make_request(endpoint, method, data, headers)
                response_times.append(response_time)
                total_requests += 1

                if success:
                    successful_requests += 1
                else:
                    failed_requests += 1

                # Small delay to prevent overwhelming the server
                await asyncio.sleep(0.01)

        # Run concurrent workers
        tasks = [worker() for _ in range(concurrent_users)]
        await asyncio.gather(*tasks)

        # Calculate metrics
        error_rate = (failed_requests / total_requests) * 100 if total_requests > 0 else 0
        throughput_rps = total_requests / duration_seconds

        return PerformanceMetric(
            endpoint=endpoint,
            method=method,
            concurrent_users=concurrent_users,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            response_times=response_times,
            error_rate=error_rate,
            throughput_rps=throughput_rps,
            timestamp=datetime.now()
        )

    async def test_health_endpoint(self) -> PerformanceMetric:
        """Test health endpoint performance"""
        return await self.run_load_test("/health", "GET", 50, 30)

    async def test_prediction_endpoint(self) -> PerformanceMetric:
        """Test prediction endpoint performance"""
        # Sample prediction data
        prediction_data = {
            "age": 45,
            "sex": "M",
            "chest_pain_type": 2,
            "resting_bp": 130,
            "cholesterol": 250,
            "fasting_bs": 0,
            "resting_ecg": 1,
            "max_hr": 150,
            "exercise_angina": 0,
            "oldpeak": 1.2,
            "st_slope": 2
        }

        return await self.run_load_test("/api/v1/predict", "POST", 20, 60, prediction_data)

    async def test_patient_list_endpoint(self) -> PerformanceMetric:
        """Test patient list endpoint performance"""
        return await self.run_load_test("/api/v1/patients", "GET", 30, 45)

    async def test_batch_prediction_endpoint(self) -> PerformanceMetric:
        """Test batch prediction endpoint performance"""
        # Sample batch data
        batch_data = {
            "predictions": [
                {
                    "age": 45, "sex": "M", "chest_pain_type": 2, "resting_bp": 130,
                    "cholesterol": 250, "fasting_bs": 0, "resting_ecg": 1,
                    "max_hr": 150, "exercise_angina": 0, "oldpeak": 1.2, "st_slope": 2
                }
                for _ in range(10)  # 10 predictions per batch
            ]
        }

        return await self.run_load_test("/api/v1/predict/batch", "POST", 10, 60, batch_data)

    async def run_comprehensive_load_test(self) -> Dict[str, PerformanceMetric]:
        """Run comprehensive load testing suite"""
        await self.setup_session()

        try:
            tests = [
                ("health_endpoint", self.test_health_endpoint),
                ("prediction_endpoint", self.test_prediction_endpoint),
                ("patient_list_endpoint", self.test_patient_list_endpoint),
                ("batch_prediction_endpoint", self.test_batch_prediction_endpoint)
            ]

            results = {}
            for test_name, test_func in tests:
                self.logger.info(f"Running {test_name}...")
                results[test_name] = await test_func()

            return results

        finally:
            await self.teardown_session()

    def generate_performance_report(self, results: Dict[str, PerformanceMetric]) -> str:
        """Generate comprehensive performance testing report"""
        report = f"""
# Performance Testing Report
Generated: {datetime.now()}

## Executive Summary
"""

        # Overall metrics
        total_requests = sum(metric.total_requests for metric in results.values())
        total_successful = sum(metric.successful_requests for metric in results.values())
        avg_error_rate = statistics.mean([metric.error_rate for metric in results.values()])
        avg_throughput = statistics.mean([metric.throughput_rps for metric in results.values()])

        report += f"""
- **Total Requests**: {total_requests:,}
- **Successful Requests**: {total_successful:,} ({total_successful/total_requests*100:.1f}%)
- **Average Error Rate**: {avg_error_rate:.2f}%
- **Average Throughput**: {avg_throughput:.1f} req/s

## Detailed Results by Endpoint
"""

        for test_name, metric in results.items():
            report += f"""
### {test_name.replace('_', ' ').title()}
- **Endpoint**: {metric.method} {metric.endpoint}
- **Concurrent Users**: {metric.concurrent_users}
- **Duration**: 60 seconds
- **Total Requests**: {metric.total_requests:,}
- **Successful Requests**: {metric.successful_requests:,}
- **Failed Requests**: {metric.failed_requests:,}
- **Error Rate**: {metric.error_rate:.2f}%
- **Throughput**: {metric.throughput_rps:.1f} req/s

#### Response Time Statistics:
- **Average**: {metric.avg_response_time:.3f}s
- **95th Percentile**: {metric.p95_response_time:.3f}s
- **99th Percentile**: {metric.p99_response_time:.3f}s
- **Min**: {metric.min_response_time:.3f}s
- **Max**: {metric.max_response_time:.3f}s

#### Performance Targets:
- **Response Time (P95)**: {'✅' if metric.p95_response_time < 1.0 else '❌'} < 1.0s (Target: {1.0:.3f}s)
- **Error Rate**: {'✅' if metric.error_rate < 5.0 else '❌'} < 5% (Target: {5.0:.1f}%)
- **Throughput**: {'✅' if metric.throughput_rps >= 10 else '❌'} ≥ 10 req/s (Target: {10:.1f} req/s)
"""

        # Recommendations
        report += """
## Recommendations

### Performance Issues Identified:
"""

        issues = []
        for test_name, metric in results.items():
            if metric.p95_response_time >= 1.0:
                issues.append(f"- {test_name}: High P95 response time ({metric.p95_response_time:.3f}s)")
            if metric.error_rate >= 5.0:
                issues.append(f"- {test_name}: High error rate ({metric.error_rate:.2f}%)")
            if metric.throughput_rps < 10:
                issues.append(f"- {test_name}: Low throughput ({metric.throughput_rps:.1f} req/s)")

        if not issues:
            report += "- ✅ No performance issues detected\n"
        else:
            report += "\n".join(issues) + "\n"

        report += """
### Optimization Recommendations:
1. **Caching**: Implement Redis caching for frequently accessed data
2. **Database**: Optimize database queries and add proper indexing
3. **Async Processing**: Use async/await for I/O operations
4. **Load Balancing**: Implement horizontal scaling with load balancer
5. **CDN**: Use CDN for static assets and API responses
6. **Monitoring**: Set up real-time performance monitoring

### Scaling Recommendations:
- **Current Load**: Handles {total_requests} requests across all endpoints
- **Recommended Capacity**: Scale to handle 2-3x current load
- **Auto-scaling**: Implement based on CPU/memory usage (>70%)
- **Database**: Consider read replicas for reporting endpoints

## Testing Environment
- **Tool**: Custom async load tester
- **Protocol**: HTTP/1.1 with connection pooling
- **Duration**: 60 seconds per endpoint
- **Concurrent Users**: 10-50 per endpoint
- **Server**: Local development environment
"""

        return report

    def export_results_to_csv(self, results: Dict[str, PerformanceMetric], filename: str = "performance_results.csv"):
        """Export performance results to CSV"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'endpoint', 'method', 'concurrent_users', 'total_requests',
                'successful_requests', 'failed_requests', 'error_rate',
                'throughput_rps', 'avg_response_time', 'p95_response_time',
                'p99_response_time', 'min_response_time', 'max_response_time',
                'timestamp'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for metric in results.values():
                writer.writerow({
                    'endpoint': metric.endpoint,
                    'method': metric.method,
                    'concurrent_users': metric.concurrent_users,
                    'total_requests': metric.total_requests,
                    'successful_requests': metric.successful_requests,
                    'failed_requests': metric.failed_requests,
                    'error_rate': metric.error_rate,
                    'throughput_rps': metric.throughput_rps,
                    'avg_response_time': metric.avg_response_time,
                    'p95_response_time': metric.p95_response_time,
                    'p99_response_time': metric.p99_response_time,
                    'min_response_time': metric.min_response_time,
                    'max_response_time': metric.max_response_time,
                    'timestamp': metric.timestamp.isoformat()
                })


# Synchronous wrapper for pytest
def run_async_load_test(endpoint: str, method: str = "GET", concurrent_users: int = 10,
                       duration_seconds: int = 60, data: Optional[Dict] = None) -> PerformanceMetric:
    """Synchronous wrapper for async load testing"""
    tester = LoadTester()

    async def run_test():
        await tester.setup_session()
        try:
            return await tester.run_load_test(endpoint, method, concurrent_users, duration_seconds, data)
        finally:
            await tester.teardown_session()

    # Run in new event loop
    import nest_asyncio
    nest_asyncio.apply()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(run_test())
    finally:
        loop.close()


# Pytest test cases
import pytest


@pytest.mark.performance
@pytest.mark.asyncio
async def test_health_endpoint_performance():
    """Test health endpoint can handle high load"""
    tester = LoadTester()
    await tester.setup_session()

    try:
        metric = await tester.test_health_endpoint()

        # Performance targets
        assert metric.error_rate < 1.0, f"Health endpoint error rate too high: {metric.error_rate}%"
        assert metric.p95_response_time < 0.5, f"Health endpoint P95 too slow: {metric.p95_response_time}s"
        assert metric.throughput_rps >= 50, f"Health endpoint throughput too low: {metric.throughput_rps} req/s"

    finally:
        await tester.teardown_session()


@pytest.mark.performance
@pytest.mark.asyncio
async def test_prediction_endpoint_performance():
    """Test prediction endpoint performance under load"""
    tester = LoadTester()
    await tester.setup_session()

    try:
        metric = await tester.test_prediction_endpoint()

        # Healthcare critical targets - must be fast and reliable
        assert metric.error_rate < 5.0, f"Prediction endpoint error rate too high: {metric.error_rate}%"
        assert metric.p95_response_time < 1.0, f"Prediction endpoint P95 too slow: {metric.p95_response_time}s"
        assert metric.throughput_rps >= 10, f"Prediction endpoint throughput too low: {metric.throughput_rps} req/s"

    finally:
        await tester.teardown_session()


@pytest.mark.performance
@pytest.mark.asyncio
async def test_batch_prediction_performance():
    """Test batch prediction performance"""
    tester = LoadTester()
    await tester.setup_session()

    try:
        metric = await tester.test_batch_prediction_endpoint()

        # Batch processing targets
        assert metric.error_rate < 10.0, f"Batch prediction error rate too high: {metric.error_rate}%"
        assert metric.p95_response_time < 5.0, f"Batch prediction P95 too slow: {metric.p95_response_time}s"
        assert metric.throughput_rps >= 5, f"Batch prediction throughput too low: {metric.throughput_rps} req/s"

    finally:
        await tester.teardown_session()


@pytest.mark.performance
def test_comprehensive_performance():
    """Run comprehensive performance test suite"""
    tester = LoadTester()

    async def run_all_tests():
        await tester.setup_session()
        try:
            results = await tester.run_comprehensive_load_test()
            report = tester.generate_performance_report(results)

            # Save report
            with open("performance_test_report.md", "w") as f:
                f.write(report)

            # Export CSV
            tester.export_results_to_csv(results)

            return results
        finally:
            await tester.teardown_session()

    # Run tests
    import nest_asyncio
    nest_asyncio.apply()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        results = loop.run_until_complete(run_all_tests())

        # Basic assertions on results
        for test_name, metric in results.items():
            assert metric.error_rate < 15.0, f"{test_name} error rate too high: {metric.error_rate}%"
            assert metric.total_requests > 0, f"{test_name} made no requests"

    finally:
        loop.close()


if __name__ == "__main__":
    # Run performance tests manually
    print("Running comprehensive performance tests...")

    tester = LoadTester()

    async def main():
        await tester.setup_session()
        try:
            results = await tester.run_comprehensive_load_test()
            report = tester.generate_performance_report(results)

            print("Performance testing completed!")
            print(f"Average error rate: {statistics.mean([r.error_rate for r in results.values()]):.2f}%")
            print(f"Average throughput: {statistics.mean([r.throughput_rps for r in results.values()]):.1f} req/s")

            # Save detailed report
            with open("performance_test_report.md", "w") as f:
                f.write(report)

            # Export CSV results
            tester.export_results_to_csv(results)

            print("Reports saved: performance_test_report.md, performance_results.csv")

        finally:
            await tester.teardown_session()

    # Run async tests
    import nest_asyncio
    nest_asyncio.apply()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    loop.close()
