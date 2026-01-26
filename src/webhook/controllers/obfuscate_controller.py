import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from webhook.services.obfuscate_service import ObfuscateService

router = APIRouter(prefix="/api/obfuscate", tags=["obfuscate"])


@router.post("")
async def obfuscate_resource(
    res_zip: UploadFile = File(..., description="UniApp 资源包 (.zip)"),
    preset: str = Form(default="low", description="混淆等级: default/low/medium/high"),
):
    """混淆 UniApp 资源包

    接收用户上传的 zip 资源包，执行 javascript-obfuscator 混淆后返回下载 URL。

    Args:
        res_zip: 资源包文件 (.zip)
        preset: 混淆等级 (default/low/medium/high)

    Returns:
        包含 uuid 和 download_url 的响应
    """
    # 验证文件格式
    if not res_zip.filename or not res_zip.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="请上传 zip 格式的资源包")

    # 验证混淆等级
    if preset not in ["default", "low", "medium", "high"]:
        raise HTTPException(status_code=400, detail="无效的混淆等级，可选: default/low/medium/high")

    task_uuid = str(uuid.uuid4())
    work_dir = ObfuscateService.get_obfuscate_dir() / task_uuid
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 保存上传文件
        zip_path = work_dir / res_zip.filename
        with zip_path.open("wb") as f:
            shutil.copyfileobj(res_zip.file, f)
        logging.info(f"保存上传文件: {zip_path}")

        # 解压
        extract_dir = work_dir / "extracted"
        ObfuscateService.extract_zip(zip_path, extract_dir)
        logging.info(f"解压完成: {extract_dir}")

        # 执行混淆
        success, error = ObfuscateService.run_obfuscator(extract_dir, preset)  # type: ignore
        if not success:
            raise HTTPException(status_code=500, detail=f"混淆失败: {error}")

        # 打包结果
        output_zip = work_dir / f"{task_uuid}_obfuscated.zip"
        ObfuscateService.create_obfuscated_zip(extract_dir, output_zip)

        # 存储结果
        result = ObfuscateService.store_result(task_uuid, output_zip, res_zip.filename)

        return {
            "message": "混淆成功",
            "uuid": task_uuid,
            "download_url": f"/api/obfuscate/{task_uuid}/download",
            "expires_at": result["expires_at"].isoformat(),
        }

    except HTTPException:
        ObfuscateService.cleanup_work_dir(work_dir)
        raise
    except Exception as e:
        logging.exception(f"混淆处理失败: {e}")
        ObfuscateService.cleanup_work_dir(work_dir)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/{task_uuid}/download")
async def download_obfuscated(task_uuid: str):
    """下载混淆后的资源包

    Args:
        task_uuid: 混淆任务的 UUID

    Returns:
        混淆后的 zip 文件流
    """
    result = ObfuscateService.get_result(task_uuid)

    if not result:
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    if datetime.now() > result["expires_at"]:
        # 清理过期文件
        work_dir = result["path"].parent
        ObfuscateService.cleanup_work_dir(work_dir)
        ObfuscateService.remove_result(task_uuid)
        raise HTTPException(status_code=410, detail="文件已过期")

    file_path: Path = result["path"]
    if not file_path.exists():
        ObfuscateService.remove_result(task_uuid)
        raise HTTPException(status_code=404, detail="文件不存在")

    def file_iterator():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        content=file_iterator(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={result['filename']}",
        },
    )
