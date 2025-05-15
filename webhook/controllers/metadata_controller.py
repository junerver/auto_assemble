from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from webhook.extensions.db import get_db
from webhook.services.metadata_service import MetadataService

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.post("/{task_id}")
async def create_metadata(task_id: str, request: Request, db=Depends(get_db)):
    """
    创建构建任务产物元数据

    通过接口提交的json格式如下：
    {
        "package_name": "com.jkr.identify_field",
        "version_name": "1.0.0",
        "version_code": 109,
        "build_type": "release",
        "flavor": "",
        "build_date": "2025-04-30 10:06:31",
        "file_size": 50140,
        "md5": "6c53fc10a93a0fee08a24e63957ad4f7"
    }
    """
    data = await request.json()
    try:
        metadata = MetadataService.create_metadata(
            task_id=task_id,
            package_name=data["package_name"],
            version_name=data["version_name"],
            version_code=data["version_code"],
            build_type=data["build_type"],
            flavor=data["flavor"],
            build_date=data["build_date"],
            file_size=data["file_size"],
            md5=data["md5"],
            db=db,
        )
        return JSONResponse(status_code=201, content=metadata.to_dict())
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required field: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}")
async def get_metadata(task_id: str, db=Depends(get_db)):
    """获取指定任务ID的构建任务产物元数据"""
    try:
        metadata = MetadataService.get_metadata_by_task_id(task_id, db=db)
        if metadata:
            return metadata.to_dict()
        raise HTTPException(status_code=404, detail="Metadata not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
