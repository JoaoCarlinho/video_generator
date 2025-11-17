"""
AWS Lambda handler for FastAPI backend API.
Uses Mangum to adapt FastAPI ASGI app for Lambda + API Gateway/Function URL.
"""

import logging
from mangum import Mangum
from app.main import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Lambda handler
# Mangum wraps the FastAPI app and adapts it for AWS Lambda
# - lifespan="on" enables startup/shutdown events (needed for DB initialization)
# - api_gateway_base_path is handled automatically by Mangum
handler = Mangum(app, lifespan="on")

# The handler function signature matches Lambda's requirements:
# def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]
#
# Mangum automatically:
# - Converts Lambda/API Gateway events to ASGI requests
# - Routes to FastAPI endpoints
# - Converts FastAPI responses back to Lambda/API Gateway format
# - Handles HTTP methods, headers, query params, body, etc.
#
# Example Lambda Function URL event structure:
# {
#   "version": "2.0",
#   "routeKey": "$default",
#   "rawPath": "/api/projects",
#   "headers": {...},
#   "requestContext": {...},
#   "body": "...",
#   "isBase64Encoded": false
# }
#
# Example Lambda response:
# {
#   "statusCode": 200,
#   "headers": {"content-type": "application/json"},
#   "body": "{\"status\": \"ok\"}"
# }

if __name__ == "__main__":
    # Local testing mode
    logger.info("Running API handler in local test mode")

    # Test event (simulates Lambda Function URL request)
    test_event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {
            "accept": "*/*",
            "content-type": "application/json",
        },
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/health",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "test"
            }
        },
        "isBase64Encoded": False
    }

    # Test Lambda context (minimal mock)
    class Context:
        function_name = "adgen-api"
        memory_limit_in_mb = 1024
        invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:adgen-api"
        aws_request_id = "test-request-id"

    # Call handler
    response = handler(test_event, Context())
    logger.info(f"Test response: {response}")
