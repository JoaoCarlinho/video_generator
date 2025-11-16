"""AWS SQS Worker configuration - replaces RQ/Redis."""

import json
import logging
import time
from typing import Optional, Dict, Any
from uuid import uuid4
import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class SQSWorkerConfig:
    """Configuration for AWS SQS Worker (replaces RQ)."""

    def __init__(self):
        """Initialize SQS worker configuration."""
        # Create SQS client
        self.sqs_client = boto3.client(
            'sqs',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )

        # Queue URLs from settings
        self.queue_url = settings.sqs_queue_url
        self.dlq_url = settings.sqs_dlq_url

        logger.info(f"✅ SQS Worker initialized")
        logger.info(f"📌 Queue URL: {self.queue_url}")
        logger.info(f"📌 DLQ URL: {self.dlq_url}")

    def enqueue_job(self, project_id: str) -> Dict[str, Any]:
        """
        Enqueue a generation job to SQS.

        Args:
            project_id: UUID string of project to generate

        Returns:
            Dict with job_id and metadata
        """
        try:
            # Generate unique job ID
            job_id = str(uuid4())

            # Create message body
            message_body = {
                "job_id": job_id,
                "project_id": project_id,
                "function": "generate_video",
                "enqueued_at": time.time()
            }

            # Send message to SQS
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
                MessageAttributes={
                    'JobId': {
                        'StringValue': job_id,
                        'DataType': 'String'
                    },
                    'ProjectId': {
                        'StringValue': project_id,
                        'DataType': 'String'
                    }
                }
            )

            logger.info(f"✅ Enqueued job {job_id} for project {project_id}")
            logger.info(f"📌 SQS Message ID: {response['MessageId']}")

            return {
                "id": job_id,
                "message_id": response['MessageId'],
                "project_id": project_id
            }

        except ClientError as e:
            logger.error(f"❌ Failed to enqueue job: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to enqueue job: {e}")
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a specific job.

        Note: SQS doesn't track job status like RQ does.
        Status must be tracked in the database (projects table).
        This method is kept for API compatibility but returns limited info.

        Args:
            job_id: Job ID

        Returns:
            Dict with job status information
        """
        # SQS doesn't have built-in job status tracking
        # Status should be tracked in database via project.status
        return {
            "job_id": job_id,
            "status": "unknown",
            "message": "Job status tracked in database. Check project.status instead."
        }

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job (not supported in SQS).

        Note: SQS doesn't support canceling specific messages once sent.
        The worker will need to check project.status and skip cancelled jobs.

        Args:
            job_id: Job ID

        Returns:
            False (cancellation not supported)
        """
        logger.warning(f"⚠️ Job cancellation not supported in SQS")
        logger.warning(f"⚠️ To cancel job {job_id}, update project.status to 'CANCELLED' in database")
        return False

    def receive_messages(self, max_messages: int = 1, wait_time: int = 20) -> list:
        """
        Receive messages from SQS queue (for worker polling).

        Args:
            max_messages: Maximum number of messages to receive (1-10)
            wait_time: Long polling wait time in seconds (0-20)

        Returns:
            List of SQS messages
        """
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time,
                MessageAttributeNames=['All'],
                AttributeNames=['All']
            )

            messages = response.get('Messages', [])

            if messages:
                logger.info(f"📨 Received {len(messages)} message(s) from queue")

            return messages

        except ClientError as e:
            logger.error(f"❌ Failed to receive messages: {e}")
            return []

    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a message from the queue (after successful processing).

        Args:
            receipt_handle: Receipt handle from received message

        Returns:
            True if deleted successfully
        """
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info(f"✅ Deleted message from queue")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to delete message: {e}")
            return False

    def change_message_visibility(self, receipt_handle: str, visibility_timeout: int) -> bool:
        """
        Change visibility timeout of a message (extend processing time).

        Args:
            receipt_handle: Receipt handle from received message
            visibility_timeout: New visibility timeout in seconds

        Returns:
            True if changed successfully
        """
        try:
            self.sqs_client.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout
            )
            logger.info(f"✅ Extended message visibility to {visibility_timeout}s")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to change visibility: {e}")
            return False

    def run_worker(self, verbose: bool = True):
        """
        Start the SQS worker (blocking).

        This polls SQS for messages and processes them.
        For production, use AWS Lambda with SQS trigger instead.

        Args:
            verbose: Enable verbose logging
        """
        from app.jobs.generation_pipeline import generate_video

        logger.info("🚀 Starting SQS Worker...")
        logger.info(f"📌 Polling queue: {self.queue_url}")
        logger.info(f"📌 Press Ctrl+C to stop")

        try:
            while True:
                # Long poll for messages (20 second wait)
                messages = self.receive_messages(max_messages=1, wait_time=20)

                for message in messages:
                    try:
                        # Parse message body
                        body = json.loads(message['Body'])
                        job_id = body['job_id']
                        project_id = body['project_id']

                        logger.info(f"🎬 Processing job {job_id} for project {project_id}")

                        # Process the job
                        generate_video(project_id)

                        # Delete message from queue (job completed)
                        self.delete_message(message['ReceiptHandle'])

                        logger.info(f"✅ Completed job {job_id}")

                    except Exception as e:
                        logger.error(f"❌ Job failed: {e}", exc_info=True)
                        # Don't delete message - it will go to DLQ after max retries

        except KeyboardInterrupt:
            logger.info("🛑 Worker interrupted")
        except Exception as e:
            logger.error(f"❌ Worker error: {e}", exc_info=True)


def create_sqs_worker() -> SQSWorkerConfig:
    """Factory function to create SQS worker configuration."""
    return SQSWorkerConfig()
