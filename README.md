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

## 可执行程序使用说明

可以下载项目中 `release` 目录下的可执行文件直接使用，初次使用会引导下创建一个 `.env` 文件，按照引导说明正确填写，即可使用。

可执行文件支持两种使用方式：

1. UI 模式，即双击打开后，按照引导输入使用功能
2. CLI 模式，你可以通过 `.\auto_assemble.exe --env 'E:\.env' --fn '1'` 这种方式在命令行中快捷使用

参数说明：

```bash
--env #指定环境遍历文件，你可以创建多个项目的环境变量文件，通过指定不同的文件，来实现多项目打包构建
--fn #所需要使用的功能序号
```

### 环境变量说明

```bash
# 分发仓库的本地目录
DISTRIBUTION_PATH=D:\dev\identify_field\app-distribution

# Android 基座工程所在目录
ANDROID_UNI_BASE_PATH=E:\dev\uni\uni-base

# 要构建的项目标识（即分发仓库中项目目录名）
PROD_NAME=identify_field

# UniApp SDK 版本
HBX_VERSION=4.45

# 该项目的 UniApp APPID
UNIAPP_ID=__UNI__882CCF1

# 该项目的 UniApp AppKey
UNIAPP_APPKEY=2b78b3e878310b084550b0efd28ab762

# 本地UniApp项目所在目录
UNIAPP_WORKSPACE=E:\dev\uni\identify-field-mall-uniapp

# 该 UniApp 项目是否为CLI创建（y/n）
UNIAPP_IS_CLI=y

# 最终 APK 产物输出目录
APK_OUTPUT_DIR=E:\dev\uni\identify-field-mall-uniapp

# 指定基座工程的构建分支，不指定使用f"prod_{PROD_NAME}"
TARGET_BRANCH=
```

### 支持的功能

当前打包工具支持如下三种功能：

1. 分发打包

   从分发仓库拉取 UniApp 资源包，在**基座工程**中进行本地构建，并上传产物到分发仓库，该功能适用于跨组合作时使用。

   通过统一约定的打包请求文件格式，修改**基座工程**中的相关配置，构建release包，并上传回**分发仓库**。

2. 本地打release包

   直接指定一个 UniApp 工程目录，在基座工程中进行本地构建，将产物输出到指定的目录下。

3. 本地构建离线基座`android_debug.apk`

   直接指定一个 UniApp 工程目录，在其下创建离线基座文件。

## python项目使用说明

### 工程安装

1. 克隆项目：
   ```bash
   git clone [项目地址]
   cd auto_assemble
   ```

2. 创建虚拟环境：
   ```bash
   python -m venv venv
   ```

3. 激活虚拟环境：
   ```bash
   .\venv\Scripts\activate
   ```

4. 安装依赖：
   ```bash
   pip install -e .
   ```

5. 配置 `.env`：

   参考 `.env.template` 文件，创建 `.env` 环境变量文件，填写分发工程、基座工程的目录地址和需要打包的项目

### 分步执行

1. 执行 `python -m auto_assemble.copy_res`，拉取最新资源，解析*打包请求配置文件* `README.md`，解压并拷贝资源到**基座工程**指定目录，根据解析结果修改基座工程的相关配置；
2. 在**基座工程**中确认修改无误后执行 `python -m auto_assemble.build` 进行项目构建，构建完毕后会拷贝产物、产物元数据到**分发仓库**
3. 执行 `python -m auto_assemble.push` ，会在分发仓库目录下执行git add、commit、push，将产物、元数据推送到**分发仓库**

### 一键执行全部步骤

在项目目录下直接执行：`auto-assemble`，改指令会依次执行上述分步流程，建议在基座配置基本稳定后使用，前期迭代时最好分步执行，确认修改内容是否正确。

### 通过bat执行

项目根目录下提供了四个 bat 批处理脚本，只需要双击即可执行相应指令：

- `run.bat` 执行 `auto-assemble`
- `run_copy_res.bat` 执行 `python -m auto_assemble.copy_res`
- `run_build.bat` 执行 `python -m auto_assemble.build` 
- `run_push.bat` 执行 `python -m auto_assemble.push`

**注意**：使用前需要先在 `config.bat` 脚本中配置 auto_assemble 项目所在目录地址：

```bash
@echo off
set MODULE_DIR=E:\dev\auto_assemble
```

## 脚本说明

`config.py` 中保存全局的常量配置

`copy_res.py` 用于从**分发仓库**拉取最新资源，解压、拷贝 UniApp 资源包到**基座工程**中，同时解析 `README.md` 文件，读取需要修改的内容。

- 读取 uniapp id 与 uniapp key，并更新 `build.gradle` 文件
- 读取 versionName、versionCode，并更新 `build.gradle` 文件
- 读取 hbx_version ，更新 `lib.version.toml` 文件
- 第三方sdk配置（yml代码块），并更新 `build.gradle` 文件
- 读取权限列表，更新应用权限清单 `AndroidManifest.xml` 文件

`build.py` 用于执行构建任务，并将最后的构建产物、产物元数据拷贝到**分发仓库**目录下

`push.py` 用于执行**分发仓库**的提交，负责将构建后的产物、元数据添加到 git 追踪，并按照要求使用时间标识提交

`parse_readme.py` 工具函数，用于解析**分发仓库**中的自述文件，从中提取版本信息

`parse_manifest.py` 工具函数，用于处理打包请求配置文件 `README.md` 中的权限列表，识别出默认权限、添加权限、删除权限


## Todo

- 修改 nodejs 脚本
- 增加对第三方模块的自动检查识别

## Changelog

- `v0.1.1` 增加资源更新是否有效，增加基座工程远端分支拉取、无分支时创建
- `v0.1.0` 工程化，完成基础的打包需求
