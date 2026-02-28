"""
Tests for Queue System
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.queue.worker import (
    get_queue,
    get_worker,
    enqueue_job,
    get_job_status,
    cancel_job,
    get_queue_stats,
    get_all_workers,
)
from app.queue.scheduler import (
    get_scheduler,
    schedule_daily_cleanup,
    schedule_weekly_report,
    list_scheduled_jobs,
    cancel_scheduled_job,
)
from app.queue.jobs import (
    process_etl_job,
    batch_prediction_job,
    generate_report_job,
    cleanup_old_data_job,
)


@pytest.fixture
def mock_redis():
    """Mock Redis connection"""
    redis = Mock()
    redis.ping.return_value = True
    return redis


@pytest.fixture
def mock_queue():
    """Mock RQ Queue"""
    queue = Mock()
    queue.name = "test_queue"
    queue.enqueue.return_value = Mock(id="job123")
    queue.__len__.return_value = 0
    queue.failed_job_count = 0
    queue.started_job_count = 0
    queue.finished_job_count = 0
    queue.worker_count = 1
    return queue


class TestQueueWorker:
    """Test queue worker functions"""
    
    @patch('app.queue.worker._redis_connection')
    @patch('app.queue.worker.Redis')
    def test_get_redis_connection(self, mock_redis_class, mock_redis_conn, mock_redis):
        """Test getting Redis connection"""
        mock_redis_class.return_value = mock_redis
        mock_redis_conn is None
        
        from app.queue.worker import get_redis_connection
        conn = get_redis_connection()
        
        assert conn is not None
        mock_redis_class.assert_called_once()
    
    @patch('app.queue.worker.get_redis_connection')
    @patch('app.queue.worker.Queue')
    def test_get_queue(self, mock_queue_class, mock_redis_conn, mock_queue):
        """Test getting queue"""
        mock_redis_conn.return_value = Mock()
        mock_queue_class.return_value = mock_queue
        
        from app.queue.worker import _queue
        _queue.value = None  # Reset
        
        queue = get_queue()
        
        assert queue is not None
        mock_queue_class.assert_called_once()
    
    @patch('app.queue.worker.get_redis_connection')
    @patch('app.queue.worker.Worker')
    def test_get_worker(self, mock_worker_class, mock_redis_conn):
        """Test getting worker"""
        mock_redis_conn.return_value = Mock()
        mock_worker = Mock()
        mock_worker.name = "test_worker"
        mock_worker_class.return_value = mock_worker
        
        worker = get_worker()
        
        assert worker is not None
        assert worker.name == "test_worker"
        mock_worker_class.assert_called_once()
    
    @patch('app.queue.worker.settings')
    @patch('app.queue.worker.get_queue')
    def test_enqueue_job_enabled(self, mock_get_queue, mock_settings, mock_queue):
        """Test enqueuing job when queue is enabled"""
        mock_settings.redis_queue_enabled = True
        mock_get_queue.return_value = mock_queue
        
        def test_job():
            return "result"
        
        job = enqueue_job(test_job)
        
        assert job is not None
        assert job.id == "job123"
        mock_queue.enqueue.assert_called_once()
    
    @patch('app.queue.worker.settings')
    @patch('app.queue.worker.get_queue')
    def test_enqueue_job_disabled(self, mock_get_queue, mock_settings):
        """Test enqueuing job when queue is disabled (synchronous execution)"""
        mock_settings.redis_queue_enabled = False
        
        call_result = []
        
        def test_job():
            call_result.append("called")
            return "result"
        
        job = enqueue_job(test_job)
        
        assert job is None  # No job returned when queue disabled
        assert call_result == ["called"]  # Function was called synchronously


class TestJobFunctions:
    """Test job functions"""
    
    def test_process_etl_job_success(self):
        """Test ETL job success"""
        with patch('app.queue.jobs.process_file') as mock_process:
            mock_process.return_value = {
                "records_processed": 100,
                "errors": []
            }
            
            result = process_etl_job("test.csv", batch_size=50)
            
            assert result["status"] == "success"
            assert result["records_processed"] == 100
    
    def test_process_etl_job_failure(self):
        """Test ETL job failure"""
        with patch('app.queue.jobs.process_file') as mock_process:
            mock_process.side_effect = Exception("File not found")
            
            result = process_etl_job("missing.csv")
            
            assert result["status"] == "error"
            assert "File not found" in result["error"]
    
    def test_batch_prediction_job(self):
        """Test batch prediction job"""
        with patch('app.queue.jobs.get_model') as mock_get_model, \
             patch('app.queue.jobs.SessionLocal') as mock_session:
            
            mock_model = Mock()
            mock_get_model.return_value = mock_model
            
            mock_db = Mock()
            mock_session.return_value = mock_db
            
            result = batch_prediction_job(["uuid1", "uuid2"])
            
            assert result["status"] == "success"
            assert "predictions" in result or "errors" in result
    
    def test_generate_report_job(self):
        """Test report generation job"""
        with patch('app.queue.jobs.SessionLocal') as mock_session, \
             patch('app.queue.jobs.pd.DataFrame') as mock_df, \
             patch('app.queue.jobs.os.makedirs') as mock_makedirs:
            
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_df_instance = Mock()
            mock_df.return_value = mock_df_instance
            
            result = generate_report_job(
                "predictions",
                "2024-01-01",
                "2024-01-31"
            )
            
            assert result["status"] in ["success", "error"]


class TestScheduler:
    """Test scheduler functions"""
    
    @patch('app.queue.scheduler.get_redis_connection')
    @patch('app.queue.scheduler.Scheduler')
    def test_get_scheduler(self, mock_scheduler_class, mock_redis_conn):
        """Test getting scheduler"""
        mock_redis_conn.return_value = Mock()
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        from app.queue.scheduler import _scheduler
        _scheduler.value = None  # Reset
        
        scheduler = get_scheduler()
        
        assert scheduler is not None
        mock_scheduler_class.assert_called_once()
    
    @patch('app.queue.scheduler.get_scheduler')
    def test_schedule_daily_cleanup(self, mock_get_scheduler):
        """Test scheduling daily cleanup"""
        mock_scheduler = Mock()
        mock_job = Mock()
        mock_job.id = "schedule123"
        mock_scheduler.schedule.return_value = mock_job
        mock_get_scheduler.return_value = mock_scheduler
        
        job_id = schedule_daily_cleanup(hour=2, minute=0, days_to_keep=90)
        
        assert job_id == "schedule123"
        mock_scheduler.schedule.assert_called_once()
    
    @patch('app.queue.scheduler.get_scheduler')
    def test_schedule_weekly_report(self, mock_get_scheduler):
        """Test scheduling weekly report"""
        mock_scheduler = Mock()
        mock_job = Mock()
        mock_job.id = "schedule456"
        mock_scheduler.schedule.return_value = mock_job
        mock_get_scheduler.return_value = mock_scheduler
        
        job_id = schedule_weekly_report(
            day_of_week=0,
            hour=8,
            report_type="predictions"
        )
        
        assert job_id == "schedule456"
        mock_scheduler.schedule.assert_called_once()
    
    @patch('app.queue.scheduler.get_scheduler')
    def test_list_scheduled_jobs(self, mock_get_scheduler):
        """Test listing scheduled jobs"""
        mock_scheduler = Mock()
        mock_job = Mock()
        mock_job.id = "job123"
        mock_job.func_name = "cleanup_old_data_job"
        mock_job.scheduled_time = datetime.now()
        mock_job.meta = {"interval": 86400}
        mock_job.timeout = 3600
        mock_scheduler.get_jobs.return_value = [mock_job]
        mock_get_scheduler.return_value = mock_scheduler
        
        jobs = list_scheduled_jobs()
        
        assert len(jobs) == 1
        assert jobs[0]["id"] == "job123"
        assert jobs[0]["func_name"] == "cleanup_old_data_job"
    
    @patch('app.queue.scheduler.get_scheduler')
    def test_cancel_scheduled_job(self, mock_get_scheduler):
        """Test cancelling scheduled job"""
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler
        
        result = cancel_scheduled_job("job123")
        
        assert result is True
        mock_scheduler.cancel.assert_called_once_with("job123")


class TestQueueStats:
    """Test queue statistics functions"""
    
    @patch('app.queue.worker.get_queue')
    def test_get_queue_stats(self, mock_get_queue, mock_queue):
        """Test getting queue statistics"""
        mock_get_queue.return_value = mock_queue
        
        stats = get_queue_stats()
        
        assert stats["name"] == "test_queue"
        assert stats["queued"] == 0
        assert stats["failed"] == 0
        assert stats["workers"] == 1
    
    @patch('app.queue.worker.Worker')
    @patch('app.queue.worker.get_redis_connection')
    @patch('app.queue.worker.get_queue')
    def test_get_all_workers(self, mock_get_queue, mock_redis_conn, mock_worker_class, mock_queue):
        """Test getting all workers"""
        mock_get_queue.return_value = mock_queue
        mock_redis_conn.return_value = Mock()
        
        mock_worker = Mock()
        mock_worker.name = "worker1"
        mock_worker.get_state.return_value = "busy"
        mock_worker.get_current_job_id.return_value = "job123"
        mock_worker.queues = [mock_queue]
        mock_worker_class.all.return_value = [mock_worker]
        
        workers = get_all_workers()
        
        assert len(workers) == 1
        assert workers[0]["name"] == "worker1"
        assert workers[0]["state"] == "busy"


class TestJobStatus:
    """Test job status functions"""
    
    @patch('app.queue.worker.get_redis_connection')
    @patch('app.queue.worker.Job')
    def test_get_job_status(self, mock_job_class, mock_redis_conn):
        """Test getting job status"""
        mock_redis_conn.return_value = Mock()
        
        mock_job = Mock()
        mock_job.id = "job123"
        mock_job.get_status.return_value = "finished"
        mock_job.created_at = datetime.now()
        mock_job.started_at = datetime.now()
        mock_job.ended_at = datetime.now()
        mock_job.exc_info = None
        mock_job.result = {"status": "success"}
        mock_job_class.fetch.return_value = mock_job
        
        status = get_job_status("job123")
        
        assert status is not None
        assert status["id"] == "job123"
        assert status["status"] == "finished"
    
    @patch('app.queue.worker.get_redis_connection')
    @patch('app.queue.worker.Job')
    def test_cancel_job(self, mock_job_class, mock_redis_conn):
        """Test cancelling job"""
        mock_redis_conn.return_value = Mock()
        
        mock_job = Mock()
        mock_job.get_status.return_value = "queued"
        mock_job_class.fetch.return_value = mock_job
        
        result = cancel_job("job123")
        
        assert result is True
        mock_job.cancel.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
