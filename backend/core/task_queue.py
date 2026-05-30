from __future__ import annotations

import logging
from typing import Any

from celery import Task
from celery.exceptions import CeleryError
from kombu.exceptions import OperationalError


logger = logging.getLogger(__name__)


def enqueue_task(task: Task, *args: Any, **kwargs: Any) -> bool:
    try:
        task.delay(*args, **kwargs)
    except (OperationalError, CeleryError, OSError) as exc:
        logger.warning("Failed to enqueue Celery task %s: %s", task.name, exc)
        return False
    return True
