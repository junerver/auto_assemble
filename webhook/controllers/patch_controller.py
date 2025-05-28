from typing import Annotated

from fastapi import APIRouter, Depends, Path

from webhook.extensions.db import get_db
from webhook.services.task_service import TaskService

router = APIRouter(prefix="/api/patch", tags=["patch"])


@router.get("/{task_id}")
async def get_other_normalized_tasks(task_id: Annotated[str, Path(..., description="任务id")], db=Depends(get_db)):
    return TaskService.get_other_normalized_tasks(task_id, db)
