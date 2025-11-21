"""
AWS Lambda handler for SQS-triggered video generation.

This handler is invoked by AWS Lambda when messages arrive in the SQS queue.
Each message represents a video generation job to be processed.

Environment Variables Required:
- DATABASE_URL: Supabase PostgreSQL connection string
- SUPABASE_URL: Supabase project URL
- SUPABASE_SERVICE_ROLE_KEY: Supabase service role key (for admin operations)
- AWS_ACCESS_KEY_ID: AWS credentials (automatically provided by Lambda)
- AWS_SECRET_ACCESS_KEY: AWS credentials (automatically provided by Lambda)
- S3_BUCKET_NAME: S3 bucket for video storage
- REPLICATE_API_TOKEN: Replicate API key for AI generation
- OPENAI_API_KEY: OpenAI API key for GPT operations
"""

import json
import logging
import os
import traceback
from typing import Dict, Any

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Log Lambda context
logger.info(f"Lambda runtime: Python {os.sys.version}")
logger.info(f"Lambda task root: {os.environ.get('LAMBDA_TASK_ROOT', 'Not set')}")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for SQS-triggered video generation.

    Args:
        event: SQS event containing message records
        context: Lambda context object

    Returns:
        Dict with status code and processing results

    Raises:
        Exception: Re-raises exceptions to trigger SQS retry/DLQ mechanism
    """
    logger.info("=" * 60)
    logger.info("Lambda invocation started")
    logger.info("=" * 60)

    # Log Lambda context
    logger.info(f"Function name: {context.function_name}")
    logger.info(f"Function version: {context.function_version}")
    logger.info(f"Request ID: {context.aws_request_id}")
    logger.info(f"Memory limit: {context.memory_limit_in_mb} MB")
    logger.info(f"Time remaining: {context.get_remaining_time_in_millis()} ms")

    # Log SQS event details
    records = event.get('Records', [])
    logger.info(f"Processing {len(records)} SQS record(s)")

    # Import here to avoid cold start issues
    try:
        from app.jobs.generation_pipeline import generate_video
        from app.database.connection import init_db
        logger.info("✅ Successfully imported dependencies")
    except ImportError as e:
        logger.error(f"❌ Failed to import dependencies: {e}")
        logger.error(traceback.format_exc())
        raise

    # Initialize database connection
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization warning: {e}")
        # Continue - database might initialize lazily

    # Process results
    results = []
    failed_count = 0
    success_count = 0

    # Process each SQS record
    for i, record in enumerate(records, 1):
        record_id = record.get('messageId', 'unknown')
        logger.info("-" * 60)
        logger.info(f"Processing record {i}/{len(records)}")
        logger.info(f"Message ID: {record_id}")

        try:
            # Parse message body
            try:
                body = json.loads(record['body'])
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in message body: {e}")
                raise ValueError(f"Invalid JSON in message body: {e}")

            job_id = body.get('job_id')
            project_id = body.get('project_id')
            function = body.get('function', 'unknown')

            # Extract provider with backward-compatible default
            video_provider = body.get('video_provider', 'replicate')

            logger.info(f"Job ID: {job_id}")
            logger.info(f"Project ID: {project_id}")
            logger.info(f"Function: {function}")
            logger.info(f"Job {project_id}: Using provider {video_provider}")

            # Validate message
            if not project_id:
                raise ValueError("Missing project_id in message body")

            if function != 'generate_video':
                raise ValueError(f"Unknown function: {function}")

            # Process the video generation job
            logger.info(f"🎬 Starting video generation for project {project_id} with provider {video_provider}")

            # Call the generation pipeline with provider parameter
            generate_video(project_id, video_provider=video_provider)

            logger.info(f"✅ Job {project_id} completed with provider: {video_provider}")
            success_count += 1

            results.append({
                'messageId': record_id,
                'jobId': job_id,
                'projectId': project_id,
                'provider': video_provider,
                'status': 'success'
            })

        except Exception as e:
            failed_count += 1
            error_msg = str(e)
            error_trace = traceback.format_exc()

            # Include provider in error log if available
            provider_info = f" with provider {video_provider}" if 'video_provider' in locals() else ""
            logger.error(f"❌ Job {project_id} failed{provider_info}: {error_msg}")
            logger.error(f"Traceback:\n{error_trace}")

            results.append({
                'messageId': record_id,
                'jobId': job_id if 'job_id' in locals() else None,
                'projectId': project_id if 'project_id' in locals() else None,
                'provider': video_provider if 'video_provider' in locals() else None,
                'status': 'failed',
                'error': error_msg
            })

            # Re-raise to trigger SQS retry mechanism
            # After max retries (3), message will go to DLQ
            raise Exception(f"Job processing failed: {error_msg}") from e

    # Log summary
    logger.info("=" * 60)
    logger.info("Processing Summary")
    logger.info("=" * 60)
    logger.info(f"Total records: {len(records)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Time remaining: {context.get_remaining_time_in_millis()} ms")

    # Return response
    response = {
        'statusCode': 200 if failed_count == 0 else 500,
        'body': json.dumps({
            'processed': len(records),
            'successful': success_count,
            'failed': failed_count,
            'results': results
        })
    }

    logger.info("Lambda invocation completed")
    return response


# For local testing
if __name__ == "__main__":
    # Mock Lambda context
    class MockContext:
        function_name = "adgen-video-generation-worker"
        function_version = "$LATEST"
        request_id = "local-test-123"
        memory_limit_in_mb = 10240

        def get_remaining_time_in_millis(self):
            return 900000  # 15 minutes

    # Mock SQS event with ECS provider
    test_event_ecs = {
        'Records': [{
            'messageId': 'test-message-123',
            'receiptHandle': 'test-receipt-handle',
            'body': json.dumps({
                'job_id': 'test-job-456',
                'project_id': '00000000-0000-0000-0000-000000000001',
                'function': 'generate_video',
                'video_provider': 'ecs',
                'enqueued_at': 1234567890
            }),
            'attributes': {
                'ApproximateReceiveCount': '1',
                'SentTimestamp': '1234567890000'
            }
        }]
    }

    # Mock SQS event with Replicate provider
    test_event_replicate = {
        'Records': [{
            'messageId': 'test-message-124',
            'receiptHandle': 'test-receipt-handle',
            'body': json.dumps({
                'job_id': 'test-job-457',
                'project_id': '00000000-0000-0000-0000-000000000002',
                'function': 'generate_video',
                'video_provider': 'replicate',
                'enqueued_at': 1234567890
            }),
            'attributes': {
                'ApproximateReceiveCount': '1',
                'SentTimestamp': '1234567890000'
            }
        }]
    }

    # Mock SQS event without provider (backward compatibility test)
    test_event_no_provider = {
        'Records': [{
            'messageId': 'test-message-125',
            'receiptHandle': 'test-receipt-handle',
            'body': json.dumps({
                'job_id': 'test-job-458',
                'project_id': '00000000-0000-0000-0000-000000000003',
                'function': 'generate_video',
                'enqueued_at': 1234567890
            }),
            'attributes': {
                'ApproximateReceiveCount': '1',
                'SentTimestamp': '1234567890000'
            }
        }]
    }

    print("Testing Lambda handler locally...")
    print("=" * 60)

    # Test with ECS provider
    print("\nTest 1: With ECS provider")
    print("-" * 40)
    try:
        result = handler(test_event_ecs, MockContext())
        print("\nTest Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\nTest Failed: {e}")
        traceback.print_exc()

    # Test without provider (backward compatibility)
    print("\n\nTest 2: Without provider (should default to 'replicate')")
    print("-" * 40)
    try:
        result = handler(test_event_no_provider, MockContext())
        print("\nTest Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\nTest Failed: {e}")
        traceback.print_exc()
