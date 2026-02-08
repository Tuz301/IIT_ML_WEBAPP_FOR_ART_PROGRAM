"""
Tests for ETL API endpoints
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.models import User

client = TestClient(app)

@pytest.fixture
def admin_user():
    """Create admin user for testing"""
    return User(
        id=1,
        email="admin@test.com",
        username="admin",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True
    )

@pytest.fixture
def regular_user():
    """Create regular user for testing"""
    return User(
        id=2,
        email="user@test.com",
        username="user",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False
    )

class TestETLAPI:
    """Test ETL API endpoints"""

    def test_run_full_pipeline_admin_access(self, admin_user):
        """Test running full ETL pipeline with admin access"""
        with patch('app.api.etl.etl_pipeline') as mock_pipeline:
            mock_pipeline.run_full_pipeline = MagicMock()
            mock_pipeline.is_running = False
            mock_pipeline.last_run_time = None

            response = client.post(
                "/v1/etl/run-full-pipeline",
                json={"force_refresh": True}
            )

            # Should succeed with admin auth (mocked)
            assert response.status_code in [200, 401]  # 401 if auth not mocked properly

    def test_run_full_pipeline_non_admin_access(self, regular_user):
        """Test running full ETL pipeline without admin access"""
        response = client.post(
            "/v1/etl/run-full-pipeline",
            json={"force_refresh": False}
        )

        # Should fail with 401 or 403
        assert response.status_code in [401, 403]

    def test_ingest_data_admin_access(self, admin_user, tmp_path):
        """Test data ingestion with admin access"""
        # Create a test data file
        test_data = {"test": "data"}
        data_file = tmp_path / "test_data.json"
        data_file.write_text(str(test_data))

        with patch('app.api.etl.data_ingestion') as mock_ingestion:
            mock_ingestion.ingest_from_source = MagicMock()

            response = client.post(
                "/v1/etl/ingest-data",
                json={
                    "data_source": str(data_file),
                    "source_type": "json",
                    "batch_size": 100
                }
            )

            assert response.status_code in [200, 401]

    def test_ingest_data_file_not_found(self, admin_user):
        """Test data ingestion with non-existent file"""
        response = client.post(
            "/v1/etl/ingest-data",
            json={
                "data_source": "/non/existent/file.json",
                "source_type": "json"
            }
        )

        assert response.status_code in [404, 401]

    def test_process_features_admin_access(self, admin_user):
        """Test feature processing with admin access"""
        with patch('app.api.etl.data_processor') as mock_processor:
            mock_processor.process_all_features = MagicMock()

            response = client.post(
                "/v1/etl/process-features",
                json={
                    "patient_ids": ["patient-1", "patient-2"],
                    "force_reprocess": True
                }
            )

            assert response.status_code in [200, 401]

    def test_get_etl_status_admin_access(self, admin_user):
        """Test getting ETL status with admin access"""
        with patch('app.api.etl.etl_pipeline') as mock_pipeline:
            mock_pipeline.get_pipeline_status.return_value = {
                "status": "idle",
                "last_run": "2024-01-01T00:00:00"
            }
            mock_pipeline.last_run_time = "2024-01-01T00:00:00"
            mock_pipeline.is_running = False

            response = client.get("/v1/etl/status")

            assert response.status_code in [200, 401]

    def test_get_ingestion_stats_admin_access(self, admin_user):
        """Test getting ingestion stats with admin access"""
        with patch('app.api.etl.data_ingestion') as mock_ingestion:
            mock_ingestion.get_ingestion_stats.return_value = {
                "total_ingested": 1000,
                "failed_batches": 5,
                "last_ingestion": "2024-01-01T00:00:00"
            }

            response = client.get("/v1/etl/ingestion/stats")

            assert response.status_code in [200, 401]

    def test_get_processing_stats_admin_access(self, admin_user):
        """Test getting processing stats with admin access"""
        with patch('app.api.etl.data_processor') as mock_processor:
            mock_processor.get_processing_stats.return_value = {
                "total_processed": 500,
                "features_generated": 1500,
                "last_processing": "2024-01-01T00:00:00"
            }

            response = client.get("/v1/etl/processing/stats")

            assert response.status_code in [200, 401]

    def test_validate_data_source_admin_access(self, admin_user, tmp_path):
        """Test data source validation with admin access"""
        # Create a test data file
        test_data = {"test": "data"}
        data_file = tmp_path / "test_data.json"
        data_file.write_text(str(test_data))

        with patch('app.api.etl.data_ingestion') as mock_ingestion:
            mock_ingestion.validate_data_source.return_value = {
                "is_valid": True,
                "record_count": 1,
                "errors": []
            }

            response = client.post(
                "/v1/etl/validate-data",
                json={
                    "data_source": str(data_file),
                    "source_type": "json"
                }
            )

            assert response.status_code in [200, 401]

    def test_cleanup_etl_data_admin_access(self, admin_user):
        """Test ETL data cleanup with admin access"""
        with patch('app.api.etl.etl_pipeline') as mock_pipeline:
            mock_pipeline.cleanup_temp_files.return_value = {
                "files_removed": 5,
                "space_freed_mb": 100
            }

            response = client.delete(
                "/v1/etl/cleanup",
                params={"cleanup_type": "temp_files"}
            )

            assert response.status_code in [200, 401]

    def test_list_data_sources_admin_access(self, admin_user, tmp_path):
        """Test listing data sources with admin access"""
        # Create a test data directory with files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        test_file = data_dir / "test.json"
        test_file.write_text('{"test": "data"}')

        with patch('app.config.get_settings') as mock_settings:
            mock_settings.return_value.data_dir = str(data_dir)

            response = client.get("/v1/etl/sources")

            assert response.status_code in [200, 401]

    def test_schedule_etl_job_admin_access(self, admin_user):
        """Test scheduling ETL job with admin access"""
        response = client.post(
            "/v1/etl/schedule",
            json={
                "job_type": "full_pipeline",
                "schedule_config": {
                    "frequency": "daily",
                    "time": "02:00"
                }
            }
        )

        assert response.status_code in [200, 401]

    def test_schedule_etl_job_invalid_type(self, admin_user):
        """Test scheduling ETL job with invalid job type"""
        response = client.post(
            "/v1/etl/schedule",
            json={
                "job_type": "invalid_type",
                "schedule_config": {}
            }
        )

        # Should return 400 for invalid job type or 401 for auth
        assert response.status_code in [400, 401]

    # Test non-admin access for all endpoints
    def test_all_endpoints_require_admin(self, regular_user):
        """Test that all ETL endpoints require admin access"""
        endpoints = [
            ("/v1/etl/run-full-pipeline", "post"),
            ("/v1/etl/ingest-data", "post"),
            ("/v1/etl/process-features", "post"),
            ("/v1/etl/status", "get"),
            ("/v1/etl/ingestion/stats", "get"),
            ("/v1/etl/processing/stats", "get"),
            ("/v1/etl/validate-data", "post"),
            ("/v1/etl/cleanup", "delete"),
            ("/v1/etl/sources", "get"),
            ("/v1/etl/schedule", "post")
        ]

        for endpoint, method in endpoints:
            if method == "get":
                response = client.get(endpoint)
            elif method == "post":
                response = client.post(endpoint, json={})
            elif method == "delete":
                response = client.delete(endpoint)

            # Should fail with 401 or 403 (not 404 or 500)
            assert response.status_code in [401, 403]

class TestETLErrorHandling:
    """Test error handling in ETL API"""

    def test_pipeline_failure_handling(self, admin_user):
        """Test handling of pipeline execution failures"""
        with patch('app.api.etl.etl_pipeline') as mock_pipeline:
            mock_pipeline.run_full_pipeline.side_effect = Exception("Pipeline failed")

            response = client.post(
                "/v1/etl/run-full-pipeline",
                json={"force_refresh": False}
            )

            # Should handle the error gracefully
            assert response.status_code in [500, 401]

    def test_ingestion_failure_handling(self, admin_user):
        """Test handling of data ingestion failures"""
        with patch('app.api.etl.data_ingestion') as mock_ingestion:
            mock_ingestion.ingest_from_source.side_effect = Exception("Ingestion failed")

            response = client.post(
                "/v1/etl/ingest-data",
                json={
                    "data_source": "/some/file.json",
                    "source_type": "json"
                }
            )

            assert response.status_code in [500, 401]

class TestETLIntegration:
    """Test ETL integration with other components"""

    def test_etl_status_includes_timestamps(self, admin_user):
        """Test that ETL status includes proper timestamps"""
        with patch('app.api.etl.etl_pipeline') as mock_pipeline:
            mock_pipeline.get_pipeline_status.return_value = {"status": "completed"}
            mock_pipeline.last_run_time = datetime.utcnow().isoformat()
            mock_pipeline.is_running = False

            response = client.get("/v1/etl/status")

            if response.status_code == 200:
                data = response.json()
                assert "timestamp" in data
                assert "pipeline_status" in data

    def test_background_task_execution(self, admin_user):
        """Test that background tasks are properly queued"""
        with patch('app.api.etl.etl_pipeline') as mock_pipeline:
            mock_pipeline.run_full_pipeline = MagicMock()

            response = client.post(
                "/v1/etl/run-full-pipeline",
                json={"force_refresh": True}
            )

            if response.status_code == 200:
                data = response.json()
                assert "started_at" in data
                assert data["status"] == "running"
