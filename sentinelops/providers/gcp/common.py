import asyncio
import importlib
import re
from collections.abc import Callable
from typing import Any


class CloudConfigurationError(RuntimeError):
    pass


def require_project(project: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,62}", project):
        raise CloudConfigurationError("Set GCP_PROJECT_ID, install the gcp extra, and use gcloud auth application-default login for development")


def client(module: str, class_name: str, **kwargs: Any) -> Any:
    try:
        factory = getattr(importlib.import_module(module), class_name)
        return factory(**kwargs)
    except Exception as error:
        raise CloudConfigurationError("GCP provider unavailable. Install `uv sync --extra gcp` and configure Application Default Credentials or a workload identity") from error


async def cloud_call[T](operation: Callable[[], T]) -> T:
    try:
        return await asyncio.to_thread(operation)
    except Exception as error:
        raise CloudConfigurationError("GCP operation failed; check resource configuration, workload identity and IAM permissions") from error
