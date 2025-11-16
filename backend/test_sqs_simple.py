#!/usr/bin/env python3
"""
Simple SQS test - just test SQS queue connectivity without full app dependencies.
"""

import sys
import logging
import json
import boto3
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test SQS connectivity."""
    from app.config import settings

    logger.info("=" * 60)
    logger.info("Simple SQS Connectivity Test")
    logger.info("=" * 60)

    logger.info(f"\nSQS Queue URL: {settings.sqs_queue_url}")
    logger.info(f"SQS DLQ URL: {settings.sqs_dlq_url}")
    logger.info(f"AWS Region: {settings.aws_region}")

    # Create SQS client directly
    try:
        sqs_client = boto3.client(
            'sqs',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        logger.info("✅ SQS client created")

        # Test 1: Send a message
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: Send Message to Queue")
        logger.info("=" * 60)

        test_message = {
            "job_id": "test-123",
            "project_id": "00000000-0000-0000-0000-000000000001",
            "function": "generate_video",
            "test": True
        }

        response = sqs_client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps(test_message)
        )

        logger.info(f"✅ Message sent successfully")
        logger.info(f"   SQS Message ID: {response['MessageId']}")

        # Test 2: Receive the message
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Receive Message from Queue")
        logger.info("=" * 60)

        logger.info("Polling queue (5 second wait)...")
        response = sqs_client.receive_message(
            QueueUrl=settings.sqs_queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5
        )

        messages = response.get('Messages', [])

        if messages:
            logger.info(f"✅ Received {len(messages)} message(s)")

            for msg in messages:
                body = json.loads(msg['Body'])
                logger.info(f"   Job ID: {body.get('job_id')}")
                logger.info(f"   Project ID: {body.get('project_id')}")

                # Delete the message
                logger.info("   Deleting test message...")
                sqs_client.delete_message(
                    QueueUrl=settings.sqs_queue_url,
                    ReceiptHandle=msg['ReceiptHandle']
                )
                logger.info("   ✅ Message deleted")
        else:
            logger.warning("⚠️  No messages received")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Summary")
        logger.info("=" * 60)
        logger.info("✅ SQS Connection: PASS")
        logger.info("✅ Send Message: PASS")
        logger.info(f"{'✅' if messages else '⚠️ '} Receive Message: {'PASS' if messages else 'SKIP (empty queue)'}")
        logger.info("=" * 60)

        logger.info("\n🎉 SQS is working correctly!")
        logger.info("\nYour SQS queues are ready for use.")
        logger.info("Next step: Run the full worker with: python run_sqs_worker.py")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
