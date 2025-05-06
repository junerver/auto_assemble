# UniApp项目分发自动打包

## 术语说明

- 分发仓库，指请求打包时保存 UniApp 资源包的 [Git 仓库](http://192.168.187.232:28088/rdcenter/app-distribution)
- 基座工程，指用于 UniApp 离线打包的[基座工程项目](http://192.168.187.209:22999/summary/jkr%2Funi-base.git)
- 打包请求配置文件，指提交UniApp 资源包时需要一并提交的 `README.md` 文件，见根目录下的 `list.md` 文件

## 开发、使用环境要求

开发环境要求：

- python 3.10+
- pip 24.1+

打包构建依赖 Gradle 与 Android SDK，请确保已安装：
- Java 17+
- Android Studio 或 Android Command line tools

> 安装 Android Studio 会引导安装 SDK 管理工具，如果你只需要打包，可以仅安装 Command line
> tools，可以在 [Android Studio 官网](https://developer.android.com/studio)下载安装这两个工具

## python项目使用说明

### 工程安装

1. 克隆项目：
   ```bash
   git clone [项目地址]
   cd auto_assemble
   ```

2. 安装 uv

   ```bash
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. 同步项目

   ```bash
   uv sync
   ```

### 启动服务

开发环境启动服务：

```bash
uv run webhook
```

生产环境启动服务：

```bash
python -m waitress --port=5005 --host=0.0.0.0 webhook.__main__:app
```

### 配置 hook

在 Gitlab 中配置推送事件的 hook，地址为：

```bash
http://{host}:{port}/webhook
```

其中 host、port 填写项目真实部署的服务器的地址与端口。

### 模块说明

- `auto_assemble` 自动构建模块
- `cbr` 构建请求工具模块
- `webhook` 构建系统后台，提供hook钩子、管理后台的api等
- `manager_client` 构建通知客户端

### 环境变量说明

需要在 `webhook` 模块下创建 `.env` 文件，指向分发仓库、基座工程仓库

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
```

## Docker部署说明

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+

### 部署步骤

1. 备份本地数据库文件：
   ```bash
   # 备份现有数据库
   cp webhook/webhook_server.db webhook/webhook_server.db.bak
   ```

3. 构建和启动容器：
   ```bash
   docker-compose up -d
   ```

   注意，该服务依赖两个镜像：

   - `auto_assemble-repo:latest` 分发仓库镜像
   - `auto_assemble-webhook:latest` 运行环境镜像

   如果没有远程镜像仓库则需要先执行下面的命令自行构建：

   ```bash
   docker build -t auto_assemble-webhook:latest -f Dockerfile . && docker build -t auto_assemble-repo:latest -f Dockerfile.repo .
   ```

4. 查看服务状态：
   ```bash
   # 查看容器日志
   docker-compose logs -f
   
   # 查看容器状态
   docker-compose ps
   ```

### 维护操作

1. 停止服务：
   ```bash
   docker-compose down
   ```

2. 重启服务：
   ```bash
   docker-compose restart
   ```

3. 更新服务：
   ```bash
   # 拉取最新代码
   git pull
   
   # 重新构建并启动
   docker-compose up -d --build
   ```

4. 查看日志：
   ```bash
   docker-compose logs -f webhook
   ```

### 故障排除

1. 容器无法启动：
   - 检查端口是否被占用
   - 检查环境变量配置
   - 查看容器日志

2. 数据库问题：
   - 检查数据库文件权限
   - 验证数据库文件完整性
   - 必要时从备份恢复

3. 服务不可用：
   - 检查容器健康状态
   - 验证网络连接
   - 检查日志输出

## 错误码说明

错误码对应模块：

- 100：打包服务器
- 110：本地分发仓库
- 120：本机基座工程
- 200：基座工程构建

| 错误码 | 错误信息                                                     |
| ------ | ------------------------------------------------------------ |
| 10001  | 项目未在自动打包系统中创建、配置                             |
| 10002  | 打包服务器失败重试超时                                       |
| 10003  | 打包服务器主动停止任务                                       |
| 10004  | 打包服务器本地环境检查出错                                   |
| 10005  | 打包服务器缺少 rar、zip 依赖库                               |
| 11001  | 本地分发仓库不存在                                           |
| 11002  | 打包服务器本地分发仓库同步失败                               |
| 11003  | 本次打包任务所在文件夹已经存在产物                           |
| 11004  | 本次打包任务指向的目录中没有压缩文件                         |
| 11005  | 对UniApp资源包压缩文件内容检查失败                           |
| 11006  | 分发仓库没有任何更新                                         |
| 11007  | 分发仓库中需要提交的文件错误                                 |
| 11008  | 分发仓库中没有需要提交的apk                                  |
| 11009  | 分发仓库执行 git add 失败                                    |
| 11010  | 分发仓库中没有待提交文件                                     |
| 11011  | 分发仓库待提交文件校验失败                                   |
| 11012  | 分发仓库执行 git commit 失败                                 |
| 11013  | 用户取消push                                                 |
| 11014  | 分发仓库执行 git push 失败                                   |
| 11015  | 构建模式错误，不是通过构建工具发起的构建请求，不符合约定的提交信息格式 |
| 11016  | 解析readme文件失败                                           |
| 12001  | 基座工程分支检查失败                                         |
| 12002  | 基座工程资源目录结构检查失败                                 |
| 12003  | 基座工程清空资源目录失败                                     |
| 12004  | 解压资源文件到基座工程失败                                   |
| 12005  | 更新基座工程构建脚本失败                                     |
| 12006  | 更新基座工程 dcloud_control.xml 文件失败                     |
| 12007  | 更新 AndroidManifest.xml 文件失败                            |
| 12008  | 基座工程git执行add操作失败                                   |
| 12009  | 基座解析依赖失败，请检查依赖配置                             |
| 12010  | 基座工程项目校验失败，工程文件缺失                           |
| 12011  | 基座工程没有待提交的文件，资源文件未更新，终止执行           |
| 12012  | 基座工程git执行commit操作失败                                |
| 12013  | 基座工程git执行push操作失败                                  |
| 12014  | 基座工程git更新失败                                          |
| 20001  | 执行 Gradle 构建失败                                         |
| 20002  | 复制构建产物失败                                             |

## Changelog

- `v0.3.5` 增加手动标记过期任务的功能
- `v0.3.4` 首页的css、js资源本地存储
- `v0.3.3` 增加构建元数据的卡片展示
- `v0.3.2` 使用uv作为项目管理工具，合并层减少镜像体积
- `v0.3.1` cbr小工具从环境变量文件中读取服务地址
- `v0.3.0` 容器化部署，实现本地容器化方案
- `v0.2.4` 添加错误重播功能，后门鉴权，最近任务筛选
- `v0.2.3` bugfix
- `v0.2.2` 服务端分层拆分
- `v0.2.1` 完善错误提示
- `v0.2.0` 移除对.env文件依赖，项目模块化拆分
- `v0.1.3` 增加cbr工具，读取uni项目自动生成请求文件，增加wekhook服务，增加可视化界面，增加通知提醒
- `v0.1.2` 支持外部环境变量文件传入
- `v0.1.1` 增加资源更新是否有效，增加基座工程远端分支拉取、无分支时创建
- `v0.1.0` 工程化，完成基础的打包需求
