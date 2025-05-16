from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import JSONResponse

from webhook.extensions.db import get_db
from webhook.services.metadata_service import MetadataService
from webhook.types import MetaDataPostResp, MetaDataModel

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.post("/{task_id}", response_model=MetaDataPostResp)
async def create_metadata(
    task_id: Annotated[str, Path(..., description="提交元数据的任务id")],
    req: MetaDataModel,
    db=Depends(get_db),
):
    """创建构建任务产物元数据"""
    try:
        metadata = MetadataService.create_metadata(
            task_id=task_id,
            package_name=req.package_name,
            version_name=req.version_name,
            version_code=req.version_code,
            build_type=req.build_type,
            flavor=req.flavor,
            build_date=req.build_date,
            file_size=req.file_size,
            md5=req.md5,
            db=db,
        )
        return JSONResponse(status_code=201, content=metadata.to_dict())
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required field: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=MetaDataPostResp)
async def get_metadata(
    task_id: Annotated[str, Path(..., description="查询元数据的任务id")],
    db=Depends(get_db),
):
    """获取指定任务ID的构建任务产物元数据"""
    try:
        metadata = MetadataService.get_metadata_by_task_id(task_id, db=db)
        if metadata:
            return metadata.to_dict()
        raise HTTPException(status_code=404, detail="Metadata not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
