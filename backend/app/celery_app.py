import os
from celery import Celery

broker_url = os.getenv("REDIS_BROKER_URL", "redis://redis:6379/0")
result_backend = os.getenv("REDIS_RESULT_BACKEND", "redis://redis:6379/1")

celery = Celery(
    "rasid",
    broker=broker_url,
    backend=result_backend,
)

celery.conf.update(
    task_track_started=True,
)

import app.tasks  # noqa
