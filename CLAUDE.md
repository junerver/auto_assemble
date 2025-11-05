# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 UniApp 项目分发自动打包系统，用于自动化构建和打包 Android 应用。系统包含多个 Python 模块，支持从 GitLab webhook 触发到最终 APK 生成的完整流程。

## 开发环境

- Python 3.10+
- uv 作为包管理工具
- Java 17+
- Android SDK/Android Studio

## 常用命令

### 项目安装和同步
```bash
# 安装 uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 同步项目（仅服务端）
uv sync

# 同步项目（客户端+服务端）
uv sync --extra dev

# 打包客户端
uv run .\script\release_module.py -m cbr -e create_build_req
```

### 启动服务
```bash
# 启动 webhook 服务
uv run webhook

# 启动构建通知客户端
uv run manager-client

# 使用 cbr 工具
uv run cbr

# 使用派生任务工具
uv run fork-task
```

### 开发工具
```bash
# 代码格式化
uv run black src/
uv run isort src/

# 代码检查
uv run ruff check src/

# 运行测试
uv run pytest

# 测试覆盖率
uv run pytest --cov=src --cov-report=html
```

## 项目架构

### 模块结构
- **auto_assemble**: 核心自动构建工具模块
- **webhook**: FastAPI 后端服务，提供 webhook 接口和管理后台
- **cbr**: 构建请求客户端工具
- **manager_client**: 构建通知客户端，监听服务器构建事件
- **fork_task**: 派生任务工具模块
- **common**: 公共模块

### Webhook 模块架构
Webhook 模块使用 FastAPI 框架，结构如下：

**入口与启动**
- 主入口：`webhook/__main__.py`
- 应用创建：`webhook/app.py`
- 配置管理：`webhook/config.py`

**路由控制器**
- `webhook_controller.py`: Webhook 相关接口
- `project_controller.py`: 项目配置接口
- `task_controller.py`: 任务相关接口
- `third_party_controller.py`: 第三方配置接口
- `auth_controller.py`: 认证接口
- `events_controller.py`: 事件接口
- `metadata_controller.py`: 元数据接口

**数据模型**
- `models/task.py`: 任务模型
- `models/webhook_request.py`: Webhook 请求模型
- `models/metadata.py`: 元数据模型
- `models/project.py`: 项目模型
- `models/third_party.py`: 第三方配置模型

**服务层**
- 业务逻辑服务位于 `services/` 目录
- 扩展功能位于 `extensions/` 目录（SSE、数据库连接等）

### 构建流程
1. GitLab 推送事件触发 webhook
2. 解析 README.md 配置文件
3. 同步分发仓库资源
4. 检查基座工程状态
5. 解压资源到基座工程
6. 更新构建配置文件
7. 执行 Gradle 构建
8. 处理构建产物并推送

## 环境变量配置

### 服务端（webhook/.env）
```bash
# 分发仓库的本地目录
DISTRIBUTION_PATH=D:/dev/identify_field/app-distribution

# Android 基座工程所在目录
ANDROID_UNI_BASE_PATH=E:/dev/uni/uni-base

# 是否启用调试模式
FLASK_DEBUG=true
# 服务端口
PORT=5005
# 管理后台接口地址
SERVER_HOST_URL=http://localhost:5005

# 混淆程度
OBFUSCATOR_PRESET=low
# api测试模式
API_TEST=false
# 是否基于GitLab作为文件中转服务
BASE_ON_GITLAB=true
```

### 客户端（cbr）
```bash
# 服务器配置
SERVER_HOST_URL=http://192.168.189.243:5005
# cbr 工作模式，支持 repo、post 两种
CBR_MODE=post
```

## 数据库表结构

- **build_task_metadata**: 元数据表
- **project_config**: 项目配置表
- **tasks**: 构建任务表
- **third_party_config**: 第三方配置表
- **third_party_dict**: 第三方配置字典
- **webhook_requests**: 钩子请求表
- **fork_task**: 派生任务表

## 测试最佳实践

### Mock 策略
- 直接 mock 模块级别的依赖，而不是全局依赖
- 使用 `@patch("auto_assemble.module.Path")` 而不是 `@patch("pathlib.Path")`
- 对于只读的 @property 属性，直接 mock 整个 config 对象
- 保持 mock 设置简单直接，避免复杂的 side_effect 逻辑

### 测试规范
- 使用 `test_` 前缀命名测试方法
- 描述测试场景和预期结果
- 每个测试用例只测试一个功能点
- 使用固定的测试数据，避免测试之间的依赖

## Docker 部署

```bash
# 构建镜像
docker build -t auto_assemble-webhook:latest -f Dockerfile .
docker build -t auto_assemble-repo:latest -f Dockerfile.repo .

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 错误码规范

错误码对应模块：
- 100：打包服务器
- 110：本地分发仓库
- 120：本机基座工程
- 130：派生任务
- 200：基座工程构建

完整错误码列表见 README.md 中的错误码说明章节。

## 重要文件说明

### 脚本文件
- `script/release_module.py`: 模块打包脚本
- `script/build.py`: 构建脚本

### 配置文件
- `webhook/.env`: 服务端环境变量
- `webhook/.env.template`: 环境变量模板
- `pyproject.toml`: 项目配置和依赖管理

### 重要代码文件
- `src/auto_assemble/auto_flow.py`: 自动构建主流程
- `src/webhook/config.py`: Webhook 配置管理
- `src/common/err_code.py`: 错误码定义