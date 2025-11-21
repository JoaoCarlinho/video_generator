"""RQ Worker configuration and helpers."""

# Fix for macOS fork crash - must be set before any network operations
import os
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# Monkey-patch os.fork to ensure environment variable is set before fork
# This is a workaround for macOS Network framework crashes in forked processes
_original_fork = os.fork
def _patched_fork():
    """Fork wrapper that ensures environment variable is set."""
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    return _original_fork()
os.fork = _patched_fork

import logging
from redis import Redis
from rq import Queue, Worker
from rq.job import Job, JobStatus

from app.config import settings
from app.jobs.generation_pipeline import generate_video
from app.jobs.edit_pipeline import edit_scene_job

logger = logging.getLogger(__name__)


class WorkerConfig:
    """Configuration for RQ Worker."""

    def __init__(self):
        """Initialize worker configuration."""
        # Redis connection for RQ
        # Note: RQ will create new connections in forked child processes
        # This connection is only used by the parent worker process
        self.redis_conn = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30
        )
        self.queue = Queue("generation", connection=self.redis_conn)
        # Configure worker
        # Note: job_timeout is set per-job in enqueue_job(), not here
        self.worker = Worker(
            [self.queue], 
            connection=self.redis_conn
        )

    def get_queue(self) -> Queue:
        """Get the generation queue."""
        return self.queue

    def get_redis(self) -> Redis:
        """Get Redis connection."""
        return self.redis_conn

    def enqueue_job(self, campaign_id: str) -> Job:
        """
        Enqueue a generation job.
        
        Args:
            campaign_id: UUID string of campaign to generate
            
        Returns:
            RQ Job object
        """
        try:
            job = self.queue.enqueue(
                generate_video,
                args=(campaign_id,),
                job_timeout="1h",  # 1 hour timeout per job
                result_ttl=86400,  # Keep results for 24 hours
                failure_ttl=604800,  # Keep failures for 7 days
            )
            logger.info(f"✅ Enqueued job {job.id} for campaign {campaign_id}")
            return job
        except Exception as e:
            logger.error(f"❌ Failed to enqueue job: {e}")
            raise
    
    def enqueue_edit_job(self, campaign_id: str, scene_index: int, edit_instruction: str) -> Job:
        """
        Enqueue an edit scene job.
        
        Args:
            campaign_id: UUID string of campaign
            scene_index: Scene index to edit (0-based)
            edit_instruction: User's edit instruction/prompt
            
        Returns:
            RQ Job object
        """
        try:
            job = self.queue.enqueue(
                edit_scene_job,
                args=(campaign_id, scene_index, edit_instruction),
                job_timeout="15m",  # 15 minutes timeout for edit jobs
                result_ttl=86400,  # Keep results for 24 hours
                failure_ttl=604800,  # Keep failures for 7 days
            )
            logger.info(f"✅ Enqueued edit job {job.id} for campaign {campaign_id}, scene {scene_index}")
            return job
        except Exception as e:
            logger.error(f"❌ Failed to enqueue edit job: {e}")
            raise

    def get_job_status(self, job_id: str) -> dict:
        """
        Get status of a specific job.
        
        Args:
            job_id: RQ Job ID
            
        Returns:
            Dict with job status information
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            return {
                "job_id": job.id,
                "status": job.get_status(),
                "progress": job.meta.get("progress", 0),
                "result": job.result,
                "exc_info": job.exc_info,
            }
        except Exception as e:
            logger.error(f"❌ Failed to get job status: {e}")
            return {"error": str(e)}

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: RQ Job ID
            
        Returns:
            True if cancelled, False otherwise
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            if job.is_started:
                job.cancel()
                logger.info(f"✅ Cancelled job {job_id}")
                return True
            else:
                job.delete()
                logger.info(f"✅ Removed job {job_id} from queue")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to cancel job: {e}")
            return False

    def run_worker(self, verbose: bool = True):
        """
        Start the RQ worker (blocking).
        
        Args:
            verbose: Enable verbose logging (not used by RQ, but kept for API compatibility)
        """
        logger.info("🚀 Starting RQ Worker...")
        logger.info(f"📌 Listening on queue: {self.queue.name}")
        logger.info(f"📌 Job timeout: 1 hour")
        
        try:
            # RQ 2.x work() method signature
            self.worker.work(with_scheduler=True)
        except KeyboardInterrupt:
            logger.info("🛑 Worker interrupted")
        except Exception as e:
            logger.error(f"❌ Worker error: {e}", exc_info=True)


def create_worker() -> WorkerConfig:
    """Factory function to create worker configuration."""
    return WorkerConfig()

