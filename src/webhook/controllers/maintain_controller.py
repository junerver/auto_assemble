from typing import Annotated

from fastapi import APIRouter, Depends, Path

from webhook.extensions.db import get_db
from webhook.services.webhook_request_service import WebhookRequestService
from webhook.types import BaseResp

router = APIRouter(prefix="/api/maintain", tags=["maintain"])


@router.get("/requests", response_model=BaseResp)
async def clear_invalid_webhook_requests(db=Depends(get_db)):
    """清除无效的webhook请求"""
    WebhookRequestService.clear_invalid_webhook_requests(db)
    return {"message": "Invalid webhook requests cleared"}


@router.delete("/requests/{task_id}", response_model=BaseResp)
async def delete_webhook_requests(
    task_id: Annotated[str, Path(..., description="任务id")],
    db=Depends(get_db),
):
    WebhookRequestService.delete_webhook_request(task_id, db=db)
    return {"message": "Webhook requests deleted successfully"}
