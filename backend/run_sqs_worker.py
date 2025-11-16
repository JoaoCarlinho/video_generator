#!/usr/bin/env python3
"""
SQS Worker startup script.

Run this to start the background job worker that polls AWS SQS:
  python run_sqs_worker.py

The worker will:
1. Poll SQS queue for messages
2. Process video generation jobs
3. Update project status in database
4. Delete messages after successful processing

Requirements:
- AWS credentials configured (via .env or environment)
- SQS_QUEUE_URL environment variable set
- All dependencies installed from requirements.txt

Note: For production, use AWS Lambda with SQS trigger instead of this script.
"""

import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Start the SQS worker."""
    try:
        from app.jobs.sqs_worker import create_sqs_worker
        from app.config import settings

        logger.info("🚀 Starting SQS Worker")
        logger.info(f"📌 SQS Queue URL: {settings.sqs_queue_url}")
        logger.info(f"📌 Environment: {settings.environment}")

        # Create and run worker
        worker_config = create_sqs_worker()
        worker_config.run_worker(verbose=True)

    except KeyboardInterrupt:
        logger.info("🛑 Worker shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Failed to start worker: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
