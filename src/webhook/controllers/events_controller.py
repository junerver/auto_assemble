import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from webhook.extensions.sse import sse  # 单例实例
from webhook.types import PublishSSEReq

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
def stream():
    """SSE 流端点"""
    logging.info("New SSE connection established")
    try:
        return sse.stream()
    except RuntimeError as e:
        logging.error(f"SSE extension not initialized: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/publish")
def publish_event(event: PublishSSEReq):
    """发布事件"""
    sse.publish(event.type, {"title": event.title, "message": event.message})
    return JSONResponse(status_code=200, content={"status": "success", "message": "Event published"})
