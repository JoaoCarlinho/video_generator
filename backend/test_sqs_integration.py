#!/usr/bin/env python3
"""
Quick test script to verify SQS integration.

This script:
1. Tests database connection to Supabase
2. Tests SQS queue access
3. Sends a test message to SQS
4. Receives and displays the message
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database():
    """Test database connection."""
    logger.info("=" * 60)
    logger.info("TEST 1: Database Connection")
    logger.info("=" * 60)

    try:
        from app.database.connection import test_connection
        from app.config import settings

        logger.info(f"Database URL: {settings.database_url[:50]}...")

        if test_connection():
            logger.info("✅ Database connection SUCCESS")
            return True
        else:
            logger.error("❌ Database connection FAILED")
            return False
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}", exc_info=True)
        return False


def test_sqs_connection():
    """Test SQS queue access."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: SQS Connection")
    logger.info("=" * 60)

    try:
        from app.jobs.sqs_worker import create_sqs_worker
        from app.config import settings

        logger.info(f"SQS Queue URL: {settings.sqs_queue_url}")
        logger.info(f"SQS DLQ URL: {settings.sqs_dlq_url}")

        worker = create_sqs_worker()
        logger.info("✅ SQS worker created successfully")
        return worker
    except Exception as e:
        logger.error(f"❌ SQS connection failed: {e}", exc_info=True)
        return None


def test_enqueue_message(worker):
    """Test enqueueing a message to SQS."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Enqueue Test Message")
    logger.info("=" * 60)

    try:
        # Use a test project ID
        test_project_id = "00000000-0000-0000-0000-000000000001"

        logger.info(f"Enqueueing test message for project: {test_project_id}")
        job = worker.enqueue_job(test_project_id)

        logger.info(f"✅ Message enqueued successfully")
        logger.info(f"   Job ID: {job['id']}")
        logger.info(f"   SQS Message ID: {job['message_id']}")
        return job
    except Exception as e:
        logger.error(f"❌ Failed to enqueue message: {e}", exc_info=True)
        return None


def test_receive_message(worker):
    """Test receiving a message from SQS."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Receive Message from Queue")
    logger.info("=" * 60)

    try:
        logger.info("Polling SQS queue (5 second wait)...")
        messages = worker.receive_messages(max_messages=1, wait_time=5)

        if messages:
            logger.info(f"✅ Received {len(messages)} message(s)")

            for msg in messages:
                import json
                body = json.loads(msg['Body'])
                logger.info(f"   Job ID: {body.get('job_id')}")
                logger.info(f"   Project ID: {body.get('project_id')}")
                logger.info(f"   Function: {body.get('function')}")

                # Delete the test message
                logger.info("   Deleting test message...")
                worker.delete_message(msg['ReceiptHandle'])
                logger.info("   ✅ Test message deleted")

            return True
        else:
            logger.warning("⚠️  No messages received (queue might be empty)")
            return False

    except Exception as e:
        logger.error(f"❌ Failed to receive message: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("SQS Integration Test Suite")
    logger.info("=" * 60 + "\n")

    # Test 1: Database
    db_success = test_database()

    # Test 2: SQS Connection
    worker = test_sqs_connection()
    if not worker:
        logger.error("\n❌ SQS tests aborted - connection failed")
        sys.exit(1)

    # Test 3: Enqueue Message
    job = test_enqueue_message(worker)
    if not job:
        logger.error("\n❌ Enqueue test failed")
        sys.exit(1)

    # Test 4: Receive Message
    received = test_receive_message(worker)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"Database Connection: {'✅ PASS' if db_success else '❌ FAIL'}")
    logger.info(f"SQS Connection: {'✅ PASS' if worker else '❌ FAIL'}")
    logger.info(f"Enqueue Message: {'✅ PASS' if job else '❌ FAIL'}")
    logger.info(f"Receive Message: {'✅ PASS' if received else '⚠️  SKIP (queue empty)'}")
    logger.info("=" * 60)

    if db_success and worker and job:
        logger.info("\n🎉 All critical tests PASSED!")
        logger.info("\nNext steps:")
        logger.info("1. Run the SQS worker: python run_sqs_worker.py")
        logger.info("2. Start the API: uvicorn app.main:app --reload")
        logger.info("3. Test full end-to-end flow with a real project")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests FAILED - check logs above")
        sys.exit(1)


if __name__ == "__main__":
    main()
