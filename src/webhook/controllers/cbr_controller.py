"""
未来计划通过该控制器，客户端直接发起网络请求，提交文件、提交信息等内容，由后端处理cbr请求，
解析后执行cbr中的 git 提交过程。

cbr 控制其应该有的功能:
- cbr 客户端管理：版本、行为
- 接口处理cbr请求：接收提交 zip、readme、用户信息（git信息）、提交信息
- 分发仓库操作：分支切换、文件放置、提交（提交人、提交信息）

cbr 客户端渐进式升级：
第一步：
1. 不由本地发起提交，而是通过后台提交
2. 接收到成功通知后，客户端切换分支

第二步：
前端脱离分发仓库，使用看板，文件交接通过看板任务卡片（需要提供任务检索功能，日期、任务、提交人）
"""

import logging
import shutil
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse

from common import git
from common.commit_label import parse_build_req_message, parse_build_branch
from common.task_util import local_task_dir
from common.validate import validate_timestamp_format, validate_git_author
from webhook.config import DISTRIBUTION_PATH, API_TEST, BASE_ON_GITLAB
from webhook.extensions.db import get_db
from webhook.services.project_service import ProjectService
from webhook.services.task_service import TaskService
from webhook.utils.mock_request import send_mock_request, mock_request_body, mock_request_headers

router = APIRouter(prefix="/api/cbr", tags=["cbr"])


def cbr_worker(
    prod_name: str,
    build_mode: str,
    temp_task_dir: str,
    task_id: str,
    author: str,
    commit_message: str,
):
    """
    服务端尝试创建CBR任务
    Args:
        prod_name: 项目名称
        build_mode: 构建模式
        temp_task_dir: cbr接口缓存的请求资源目录
        task_id:
        author:
        commit_message:

    Returns:

    """

    logging.info(f"开始切换{DISTRIBUTION_PATH}到分支：{parse_build_branch(build_mode)}")
    git.check_git_branch(DISTRIBUTION_PATH, parse_build_branch(build_mode))
    target_dir: Path = Path(DISTRIBUTION_PATH) / prod_name / Path(temp_task_dir).name
    shutil.copytree(temp_task_dir, target_dir, dirs_exist_ok=True)
    logging.info(f"拷贝临时目录中的 zip 文件和 readme.md 文件到cbr任务目录: {target_dir}")
    # git add ,commit,push
    if not API_TEST:
        if not git.git_add(repo_path=DISTRIBUTION_PATH):
            logging.error("git add 失败")
        if not git.git_commit(commit_message, repo_path=DISTRIBUTION_PATH, author=author):
            logging.error("git commit 失败")
        if not git.git_push(repo_path=DISTRIBUTION_PATH):
            logging.error("git push 失败")
        logging.info(f"cbr任务 {task_id} 请求创建成功")
        shutil.rmtree(temp_task_dir)
    else:
        logging.info("测试环境，不进行git操作")


@router.post(
    "",
    responses={
        200: {"description": "CBR请求接收成功，文件校验无误，准备创建请求"},
        400: {"description": "CBR请求提内容校验不成功"},
        423: {"description": "CBR任务已存在"},
        404: {"description": "指向的项目不存在"},
    },
)
async def create_build_request(
    prod_name: str = Form(..., description="产品名称"),
    author: str = Form(..., description="作者"),
    commit_message: str = Form(..., description="提交信息"),
    readme: UploadFile = File(..., description="README.md"),
    res_zip: UploadFile = File(..., description="Uni资源包文件"),
    db=Depends(get_db),
):
    """
    cbr 提交接口，接口接收 Uni 资源的 zip 包、README.md、提交信息、作者
    """
    project = ProjectService.get_project(prod_name=prod_name, db=db)
    #  项目不存在
    if not project:
        return JSONResponse(content={"message": f"项目【{prod_name}】不存在"}, status_code=404)
    build_mode, _ = parse_build_req_message(commit_message)
    task = res_zip.filename.replace(".zip", "")
    task_id = f"{prod_name},{task}"
    #  任务已存在
    if TaskService.get_task(task_id=task_id, db=db):
        return JSONResponse(content={"message": f"任务【{task_id}】已存在"}, status_code=423)

    if not validate_git_author(author):
        return JSONResponse(content={"message": "请填写正确的 git 作者信息"}, status_code=400)
    if build_mode not in ["dev", "test", "release"]:
        return JSONResponse(content={"message": "请填写正确的 git 提交信息"}, status_code=400)
    if readme.filename != "README.md":
        return JSONResponse(content={"message": "请上传正确的 README.md 文件"}, status_code=400)
    if not res_zip.filename.endswith(".zip") or not validate_timestamp_format(task):
        return JSONResponse(content={"message": "请上传正确的资源包文件"}, status_code=400)

    temp_task_dir = local_task_dir(task_id, build_mode)
    temp_task_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"cbr 临时目录：{str(temp_task_dir)}")

    # 保存上传的文件
    try:
        for upload_file in [readme, res_zip]:
            local_file_path = temp_task_dir / upload_file.filename
            with local_file_path.open("wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            logging.info(f"cbr 提交信息: {commit_message} 提交人: {author} 提交文件: {str(local_file_path)} ")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
    if BASE_ON_GITLAB:
        Thread(
            target=cbr_worker, args=(prod_name, build_mode, str(temp_task_dir), task_id, author, commit_message)
        ).start()
    else:
        # 本地模式，文件存储到本地，直接模拟请求
        await send_mock_request(
            request_body=mock_request_body(
                author,
                prod_name,
                task,
                commit_message,
            ),
            headers=mock_request_headers(),
            db=db,
        )
    return {"message": f"cbr 任务【{prod_name},{task}】提交成功，请等待任务创建"}
