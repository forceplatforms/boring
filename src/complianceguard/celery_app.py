"""
Celery application configuration for background task processing.

This module configures Celery to use Redis as a message broker and result backend
for asynchronous document ingestion and indexing tasks.
"""

import os
from celery import Celery
from celery.signals import task_failure, task_success
from kombu import Exchange, Queue

# Get configuration from environment variables
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
app = Celery("complianceguard")

# Configuration
app.conf.update(
    # Broker settings
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    broker_connection_retry_on_startup=True,

    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # Fetch one task at a time for fair distribution

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_persistent=True,
    result_extended=True,  # Store additional metadata

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Queue configuration
    task_default_queue="default",
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("indexing", Exchange("indexing"), routing_key="indexing.#"),
        Queue("compliance", Exchange("compliance"), routing_key="compliance.#"),
    ),
    task_routes={
        "complianceguard.tasks.ingest.*": {"queue": "indexing"},
        "process_compliance_scan": {"queue": "compliance"},
    },

    # Worker settings
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
    worker_disable_rate_limits=False,

    # Logging
    worker_redirect_stdouts=True,
    worker_redirect_stdouts_level="INFO",
)

# Auto-discover tasks from the tasks module
app.autodiscover_tasks(["complianceguard.tasks"])


# Task lifecycle hooks for logging and monitoring
@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Log successful task completion."""
    task_id = kwargs.get("task_id")
    task_name = sender.name if sender else "Unknown"
    print(f"✓ Task {task_name} [{task_id}] completed successfully")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """Log task failures for monitoring."""
    task_name = sender.name if sender else "Unknown"
    print(f"✗ Task {task_name} [{task_id}] failed: {exception}")


if __name__ == "__main__":
    app.start()
