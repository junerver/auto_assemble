import logging
import pathlib
import shutil
import sqlite3
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from common.config import config
from webhook.extensions.db import get_db
from webhook.models.project import Project
from webhook.types import (
    AllProjectsResp,
    ConfigureProjectResp,
    ProjectConfigDetailResp,
    ProjectSignConfigReq,
)
from webhook.models.third_party import ThirdPartyConfig
from webhook.services.project_service import ProjectService
from webhook.services.third_party_service import ThirdPartyService

router = APIRouter(prefix="/api/config/project", tags=["project"])


@router.post("", response_model=ConfigureProjectResp)
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


@router.get("", response_model=ProjectConfigDetailResp)
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

        project: Optional[Project] = ProjectService.get_project(project_url=project_url, prod_name=prod_name, db=db)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 获取项目的第三方配置
        third_party_configs = ThirdPartyService.get_project_configs(project.id, db=db)
        logging.info(f"获取项目配置成功 {project.to_dict()}")
        return {
            "project_config": project.to_dict(),
            "third_party_configs": [config.to_dict() for config in third_party_configs],
            "message": "获取项目配置成功",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
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
        project: Optional[Project] = ProjectService.update_project(project_id, db=db, **base_config)
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


@router.get("/list", response_model=AllProjectsResp)
async def get_projects(db=Depends(get_db)):
    """获取所有项目配置列表"""
    try:
        projects = ProjectService.get_all_projects(db)
        return {"projects": [project.to_dict() for project in projects]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}/sign")
async def update_project_sign_config(
    project_id: Annotated[str, Path(..., description="项目的uuid主键")],
    sign_config: ProjectSignConfigReq = Depends(ProjectSignConfigReq.as_form),
    db: sqlite3.Connection = Depends(get_db),
):
    """更新项目签名配置信息"""
    # 获取项目
    project = ProjectService.get_project(project_id=project_id, db=db)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 删除旧签名文件
    if project.key_store and (key_store_path := pathlib.Path(project.key_store)).exists():
        key_store_path.unlink()

    # 定义签名文件存储目录
    sign_path = config.SIGN_PATH
    sign_path.mkdir(parents=True, exist_ok=True)  # 确保目录存在

    # 生成带项目前缀的文件名
    original_filename = sign_config.key_store.filename
    prefixed_filename = f"{project.prod_name}_{original_filename}"
    new_sign_file_path = sign_path / prefixed_filename

    # 保存上传的文件
    try:
        with new_sign_file_path.open("wb") as buffer:
            shutil.copyfileobj(sign_config.key_store.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")

    # 存储签名配置，传递生成的文件路径
    try:
        ProjectService.configure_project_sign_config(
            project=project,
            sign_config=sign_config,
            file_path=str(new_sign_file_path),  # configure_project_sign_config 接受 file_path 参数
            db=db,
        )
    except Exception as e:
        # 如果配置存储失败，删除已保存的文件
        new_sign_file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"配置签名失败: {str(e)}")

    return {"message": "项目签名配置更新成功", "file_path": str(new_sign_file_path)}


@router.get("/{project_id}/sign")
async def get_project_sign_config(
    project_id: Annotated[str, Path(..., description="项目的uuid主键")],
    db: sqlite3.Connection = Depends(get_db),
):
    """获取项目签名配置信息"""
    project: Project = ProjectService.get_project(project_id=project_id, db=db)
    return {"signConfig": project.get_sign_config()}
