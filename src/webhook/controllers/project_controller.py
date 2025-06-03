from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from webhook.extensions.db import get_db
from webhook.types import (
    AllProjectsResp,
    ConfigureProjectResp,
    ProjectConfigDetailResp,
)
from webhook.models.third_party import ThirdPartyConfig
from webhook.services.project_service import ProjectService
from webhook.services.third_party_service import ThirdPartyService

router = APIRouter(prefix="/api/config", tags=["project"])


@router.post("/project", response_model=ConfigureProjectResp)
async def configure_project(request: Request, db=Depends(get_db)):
    """配置项目信息"""
    try:
        data = await request.json()
        if not data:
            raise HTTPException(status_code=400, detail="No JSON data received")

        project = ProjectService.configure_project(data, db=db)
        return {
            "message": "Project configured successfully",
            "project": project.to_dict(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project", response_model=ProjectConfigDetailResp)
async def get_project_config(
    url: str = Query(default=None, description="项目URL"),
    name: str = Query(default=None, description="项目名称"),
    db=Depends(get_db),
):
    """获取项目配置信息"""
    try:
        # 获取查询参数
        project_url = url
        prod_name = name

        if not project_url and not prod_name:
            raise HTTPException(status_code=400, detail="Must provide either url or name parameter")

        project = ProjectService.get_project(project_url=project_url, prod_name=prod_name, db=db)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 获取项目的第三方配置
        third_party_configs = ThirdPartyService.get_project_configs(project.id, db=db)

        return {
            "project_config": project.to_dict(),
            "third_party_configs": [config.to_dict() for config in third_party_configs],
            "message": "获取项目配置成功",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/project/{project_id}")
async def update_project_config(
    project_id: Annotated[str, Path(..., description="项目的uuid主键")],
    request: Request,
    db=Depends(get_db),
):
    """更新项目配置信息"""
    try:
        data = await request.json()
        if not data:
            raise HTTPException(status_code=400, detail="No JSON data received")

        # 分离基础配置和第三方配置
        base_config = {k: v for k, v in data.items() if k not in ["third_party_configs"]}
        third_party_configs = data.get("third_party_configs", [])

        # 更新基础配置
        project = ProjectService.update_project(project_id, db=db, **base_config)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 更新第三方配置
        if third_party_configs:
            # 获取当前项目的所有第三方配置
            current_configs = {
                config.dict_key: config.config_value
                for config in ThirdPartyService.get_project_configs(project_id, db=db)
            }

            for config in third_party_configs:
                dict_key = config.get("key")
                config_value = config.get("value")
                if not dict_key or not config_value:
                    continue

                # 检查字典项是否存在
                dict_item = ThirdPartyService.get_dict_item(dict_key, db=db)
                if not dict_item:
                    raise HTTPException(status_code=400, detail=f"Dictionary item {dict_key} not found")

                # 只有当配置值发生变化时才更新
                if dict_key not in current_configs or current_configs[dict_key] != config_value:
                    third_party_config = ThirdPartyConfig(
                        project_id=project_id,
                        dict_key=dict_key,
                        config_value=config_value,
                    )
                    if not third_party_config.save(db=db):
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to save third party config for {dict_key}",
                        )

        # 获取更新后的完整项目信息
        project_dict = project.to_dict()
        project_dict["third_party_configs"] = [
            config.to_dict() for config in ThirdPartyService.get_project_configs(project_id, db=db)
        ]

        return {
            "message": "Project configuration updated successfully",
            "project": project_dict,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=AllProjectsResp)
async def get_projects(db=Depends(get_db)):
    """获取所有项目配置列表"""
    try:
        projects = ProjectService.get_all_projects(db)
        return {"projects": [project.to_dict() for project in projects]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
