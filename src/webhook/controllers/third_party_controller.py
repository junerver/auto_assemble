from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse

from webhook.extensions.db import get_db
from webhook.types import BaseResp
from webhook.models.third_party import ThirdPartyDict
from webhook.services.third_party_service import ThirdPartyService

router = APIRouter(prefix="/api/config/third-party", tags=["third-party"])


@router.get("/dict")
async def get_third_party_dict(db=Depends(get_db)):
    """获取所有第三方配置字典"""
    try:
        dict_items = ThirdPartyService.get_all_dict_items(db=db)
        return {"items": [item.to_dict() for item in dict_items]}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.post("/dict")
async def add_third_party_dict(request: Request, db=Depends(get_db)):
    """添加新的第三方配置字典项"""
    try:
        try:
            dict_item = await parse_third_party_config_dict(request)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        if ThirdPartyService.add_dict_item(dict_item, db=db):
            return JSONResponse(
                content={"message": "Third party dictionary item added successfully"},
                status_code=201,
            )
        else:
            raise HTTPException(status_code=400, detail="Dictionary key already exists")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dict/{key}")
async def get_third_party_dict_item(
    key: Annotated[str, Path(..., description="第三方服务配置的键值")],
    db=Depends(get_db),
):
    """获取单个第三方配置字典项"""
    try:
        item = ThirdPartyService.get_dict_item(key, db=db)
        if not item:
            raise HTTPException(status_code=404, detail="Dictionary item not found")

        return item.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/dict/{key}", response_model=BaseResp)
async def update_third_party_dict_item(
    key: Annotated[str, Path(..., description="第三方服务配置的键值")],
    request: Request,
    db=Depends(get_db),
):
    """更新第三方配置字典项"""
    try:
        try:
            dict_item = await parse_third_party_config_dict(request)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        if ThirdPartyService.update_dict_item(key, dict_item, db=db):
            return {"message": "Third party dictionary item updated successfully"}
        else:
            raise HTTPException(
                status_code=404,
                detail="Dictionary item not found or key already exists",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dict/{key}", response_model=BaseResp)
async def delete_third_party_dict_item(
    key: Annotated[str, Path(..., description="第三方服务配置的键值")],
    db=Depends(get_db),
):
    """删除第三方配置字典项"""
    try:
        if ThirdPartyService.delete_dict_item(key, db=db):
            return {"message": "Third party dictionary item deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Dictionary item not found or is in use")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dict/unconfigured")
async def get_unconfigured_dict_items(project_id: str = Query(default=None, description="项目URL"), db=Depends(get_db)):
    """获取项目未配置的字典项"""
    try:
        if not project_id:
            raise HTTPException(status_code=400, detail="Project ID is required")

        unconfigured_items = ThirdPartyService.get_unconfigured_dict_items(project_id, db=db)
        return {"items": [item.to_dict() for item in unconfigured_items]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def parse_third_party_config_dict(api_request: Request) -> ThirdPartyDict:
    """解析第三方配置字典项"""
    data = await api_request.json()
    if not data:
        raise HTTPException(status_code=400, detail="No JSON data received")

    required_fields = ["provider", "dict_key", "dict_value", "description"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    dict_item = ThirdPartyDict(
        provider=data["provider"],
        dict_key=data["dict_key"],
        dict_value=data["dict_value"],
        description=data["description"],
    )
    return dict_item
