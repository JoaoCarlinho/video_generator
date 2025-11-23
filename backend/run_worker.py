#!/usr/bin/env python3
"""
RQ Worker startup script.

IMPORTANT FOR macOS USERS:
  Use ./start_worker.sh instead of running this directly!
  The shell script sets OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES before Python starts,
  which is required to prevent fork crashes on macOS.

Run this to start the background job worker:
  ./start_worker.sh    (recommended - handles macOS fork fix)
  OR
  export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES && python run_worker.py

The worker will:
1. Connect to Redis
2. Listen on the 'generation' queue
3. Process video generation jobs
4. Update campaign status in database

Requirements:
- Redis running (local or via Railway)
- REDIS_URL environment variable set
- All dependencies installed from requirements.txt
"""

# CRITICAL: Set environment variable BEFORE any imports that might use networking
# This must be set before Python initializes the Network framework on macOS
import os
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

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
    """Start the RQ worker."""
    try:
        from app.jobs.worker import create_worker
        from app.config import settings
        
        logger.info("🚀 Starting RQ Worker")
        logger.info(f"📌 Redis URL: {settings.redis_url[:30]}...")
        logger.info(f"📌 Environment: {settings.environment}")
        
        # Create and run worker
        worker_config = create_worker()
        worker_config.run_worker(verbose=True)
        
    except KeyboardInterrupt:
        logger.info("🛑 Worker shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Failed to start worker: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

