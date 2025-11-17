"""Jobs module for background processing."""

# These imports require image processing libraries (OpenCV/NumPy)
# They're only needed in the worker Lambda, not the API Lambda
try:
    from app.jobs.generation_pipeline import GenerationPipeline, generate_video
    from app.jobs.sqs_worker import SQSWorkerConfig, create_sqs_worker
    _HAS_JOBS = True
except (ImportError, AttributeError) as e:
    # Missing dependencies for image processing
    GenerationPipeline = None
    generate_video = None
    SQSWorkerConfig = None
    create_sqs_worker = None
    _HAS_JOBS = False

__all__ = [
    "GenerationPipeline",
    "generate_video",
    "SQSWorkerConfig",
    "create_sqs_worker",
]

