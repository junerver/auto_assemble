from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from webhook.models.task import TaskStatus


# ========================请求、响应模型============================
class BaseResp(BaseModel):
    """基础响应模型"""

    message: str = Field(..., description="消息说明")


class AuthResponse(BaseModel):
    """鉴权接口响应"""

    authorized: bool = Field(..., description="是否是允许访问其他功能")
    client_ip: str = Field(..., description="客户端访问ip")
    role: str = Field(..., description="访问者角色")
    permissions: list[str] = Field(..., description="允许使用的权限")


class ForkTaskReq(BaseModel):
    """请求创建派生任务的请求体"""

    source_task_id: str = Field(..., description="源任务的任务id")
    source_branch: str = Field(..., description="源任务所在分支")
    target_branch: str = Field(..., description="派生任务目标分支")
    target_version_name: str = Field(..., description="派生任务目标版本名")
    target_version_code: str = Field(..., description="派生任务目标版本号")
    commit_message: str = Field(..., description="派生任务的提交消息")
    operator: Optional[str] = Field("assemble_bot")


class ForkTaskModel(ForkTaskReq):
    """派生任务详情"""

    id: str = Field(..., description="派生任务的任务id")
    created_at: Optional[datetime] = Field(None, description="派生任务创建时间")


class ForkTaskResp(BaseModel):
    """创建派生任务后响应的内容"""

    message: str = Field(..., description="派生任务响应说明")
    fork_task: ForkTaskModel = Field(..., description="派生任务详情")


class ForkTaskDetailResp(BaseModel):
    """派生任务详情接口响应"""

    fork_task: ForkTaskModel = Field(..., description="派生任务详情")


class MetaDataModel(BaseModel):
    """任务元数据"""

    package_name: str = Field(..., description="包名")
    version_name: str = Field(..., description="版本名")
    version_code: int = Field(..., description="版本号")
    build_type: str = Field(..., description="构建类型")
    flavor: str = Field(..., description="风味维度")
    build_date: str = Field(..., description="构建日期")
    file_size: int = Field(..., description="文件大小（Kb）")
    md5: str = Field(..., description="MD5")
    is_normalized: Optional[bool] = Field(False, description="是否已经归一化")
    is_obfuscated: Optional[bool] = Field(False, description="是否已经混淆")


class MetaDataPostResp(MetaDataModel):
    """元数据响应值"""

    id: int = Field(..., description="主键id")
    task_id: str = Field(..., description="构建任务id")
    created_at: Optional[datetime] = Field(None, description="添加事件")


class ProjectModel(BaseModel):
    """项目配置模型"""

    id: str = Field(..., description="项目id [UUID]")
    project_url: str = Field(..., description="项目Git仓库地址")
    prod_name: str = Field(..., description="项目内部代号")
    hbx_version: str = Field(..., description="项目使用HBX编译版本")
    uniapp_id: str = Field(..., description="项目 UniApp 后台 appid")
    uniapp_appkey: str = Field(..., description="项目 UniApp 后台 appkey")
    uniapp_is_cli: bool = Field(..., description="项目是否为cli创建项目")
    created_at: Optional[datetime] = Field(None, description="项目配置创建时间")
    updated_at: Optional[datetime] = Field(None, description="项目配置更新时间")


class ConfigureProjectResp(BaseResp):
    """配置项目的响应"""

    project: ProjectModel = Field(..., description="项目配置信息")


class ProjectConfigDetailResp(BaseResp):
    """项目配置查询的详情"""

    project_config: ProjectModel = Field(..., description="项目配置信息")
    third_party_configs: list["ThirdPartyConfigModel"] = Field(..., description="第三方配置列表")


class AllProjectsResp(BaseModel):
    """全部项目列表接口响应体"""

    projects: list[ProjectModel]


class BaseTaskModel(BaseModel):
    """任务的基础字段，排除了前端重命名部分"""

    id: str = Field(..., description="任务id，由项目别名与申请时间戳拼接")
    author: str = Field(..., description="作者")
    commit_title: str = Field(..., description="提交标题")
    commit_message: str = Field(..., description="完整提交信息")
    commit_url: str = Field(..., description="提交链接")
    priority: int = Field(..., description="优先级，数值越大越优先")
    retries: int = Field(..., description="已重试次数")
    created_at: Optional[datetime] = Field(None, description="任务创建时间")
    started_at: Optional[datetime] = Field(None, description="任务开始时间")
    completed_at: Optional[datetime] = Field(None, description="任务完成时间")
    status: Optional["TaskStatus"] = Field(..., description="当前状态")
    error: Optional[str] = Field(None, description="错误信息（如果有）")
    commit_hash: Optional[str] = Field(None, description="提交哈希值")
    response_hash: Optional[str] = Field(None, description="响应哈希值")
    metadata: Optional[MetaDataModel] = Field(None, description="附加元数据")
    source_task_id: Optional[str] = Field(None, description="来源任务ID（如果是派生任务）")


class TaskModel(BaseTaskModel):
    """前端使用的响应实体，对两个字段名称进行了重命名"""

    project: str = Field(..., description="项目名称")
    task: str = Field(..., description="任务名称")


class TaskDetailResp(BaseModel):
    """构建任务详情"""

    task: TaskModel = Field(..., description="构建任务详情")


class TaskStatisticsModel(BaseModel):
    """任务构建统计"""

    prod_name: str = Field(..., description="项目名称")
    count: int = Field(..., description="构建次数")


class UsageStatisticsModel(BaseModel):
    """使用者统计"""

    author: str = Field(..., description="使用人")
    count: int = Field(..., description="构建次数")


class StatisticsResp(BaseModel):
    """统计接口响应"""

    tasks: list[TaskStatisticsModel]
    packer_usage: list[UsageStatisticsModel]


class QueueDetailResp(BaseModel):
    """队列接口响应"""

    running_task: Optional[TaskModel] = Field(None, description="当前运行的构建任务")
    pending_tasks: list[TaskModel] = Field(..., description="排队中的构建任务")
    queue_size: int = Field(..., description="当前队列深度")
    recent_tasks: list[TaskModel] = Field(..., description="最近完成的构建任务")


class StopTaskResp(BaseResp):
    """停止任务响应"""

    task: TaskModel = Field(..., description="构建任务详情")


class ThirdPartyConfigModel(BaseModel):
    """第三方配置模型"""

    provider: str = Field(..., description="第三方服务提供商")
    description: str = Field(..., description="第三方服务描述")
    dict_key: str = Field(..., description="第三方服务字典键")
    dict_value: str = Field(..., description="第三方服务字典值")
    config_value: str = Field(..., description="第三方服务配置值")


class AuthorModel(BaseModel):
    """作者信息"""

    name: str = Field(..., description="作者名称")
    email: str = Field(..., description="作者邮箱")


class CommitModel(BaseModel):
    """提交信息"""

    id: str = Field(..., description="当前提交的hash值")
    message: str = Field(..., description="提交消息")
    title: str = Field(..., description="提交标题")
    timestamp: str = Field(..., description="提交时间戳")
    url: str = Field(..., description="当前提交对应仓库快照的url")
    author: AuthorModel = Field(..., description="提交人")
    added: list[str] = Field(..., description="添加的文件列表")
    modified: list[str] = Field(..., description="修改的文件列表")
    removed: list[str] = Field(..., description="移除的文件列表")


class ProjectInfoModel(BaseModel):
    """项目信息"""

    id: int = Field(..., description="gitlab项目id")
    name: str = Field(..., description="项目名称")
    description: str = Field(..., description="项目描述")
    web_url: str = Field(..., description="项目url")
    avatar_url: Optional[str] = Field(..., description="项目头像地址")
    git_ssh_url: str = Field(..., description="仓库ssh地址")
    git_http_url: str = Field(..., description="仓库http地址")
    namespace: str = Field(..., description="仓库命名空间")
    visibility_level: int = Field(..., description="仓库可见级别")
    path_with_namespace: str
    default_branch: str = Field(..., description="默认分支")
    ci_config_path: Optional[str] = Field(..., description="ci配置路径")
    homepage: str = Field(..., description="主页")
    url: str
    ssh_url: str
    http_url: str


class RepositoryInfoModel(BaseModel):
    """git仓库信息"""

    name: str
    url: str
    description: str
    homepage: str
    git_http_url: str
    git_ssh_url: str
    visibility_level: int


class GitLabPushEventReq(BaseModel):
    """webhook 推送事件请求实体类"""

    object_kind: str = Field(..., description="事件类型")
    event_name: str = Field(..., description="事件名称")
    before: str = Field(..., description="推送前的 commit hash")
    after: str = Field(..., description="推送后的 commit hash")
    ref: str = Field(..., description="分支引用（如 refs/heads/master）")
    ref_protected: bool = Field(..., description="是否是受保护的分支")
    checkout_sha: str = Field(..., description="当前检出的 commit hash")
    message: Optional[str] = Field(None, description="推送信息（可为空）")
    user_id: int = Field(..., description="用户 ID")
    user_name: str = Field(..., description="用户名字")
    user_username: str = Field(..., description="用户登录名")
    user_email: Optional[str] = Field(None, description="用户邮箱（可为空）")
    user_avatar: Optional[str] = Field(None, description="用户头像 URL（可为空）")
    project_id: int = Field(..., description="项目 ID")
    project: ProjectInfoModel = Field(..., description="项目信息")
    commits: list[CommitModel] = Field(..., description="提交记录列表")
    total_commits_count: int = Field(..., description="总提交数量")
    push_options: dict = Field(..., description="推送选项")
    repository: RepositoryInfoModel = Field(..., description="仓库基本信息")


class PublishSSEReq(BaseModel):
    """SSE 推送事件请求实体类"""

    type: Optional[str] = Field("toast", description="事件类型")
    title: str = Field(..., description="事件标题")
    message: str = Field(..., description="事件消息")
