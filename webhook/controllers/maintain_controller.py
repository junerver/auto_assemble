from fastapi import APIRouter, Depends

from webhook.extensions.db import get_db
from webhook.services.webhook_request_service import WebhookRequestService
from webhook.types import BaseRespModel

router = APIRouter(prefix="/api/maintain", tags=["maintain"])


@router.get("/requests", response_model=BaseRespModel)
async def clear_invalid_webhook_requests(db=Depends(get_db)):
    """清除无效的webhook请求"""
    WebhookRequestService.clear_invalid_webhook_requests(db)
    return {"message": "Invalid webhook requests cleared"}
