# UniApp项目分发自动打包

## 术语说明

- 分发仓库，指请求打包时保存 UniApp 资源包的 [Git 仓库](http://192.168.187.232:28088/rdcenter/app-distribution)
- 基座工程，指用于 UniApp 离线打包的[基座工程项目](http://192.168.187.209:22999/summary/jkr%2Funi-base.git)
- 打包请求配置文件，指提交UniApp 资源包时需要一并提交的 `README.md` 文件，见根目录下的 `list.md` 文件

## 开发环境设置

- python 3.8+
- Java 17+

## 使用说明

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
        - 读取第三方sdk配置（yml代码块），并更新 `build.gradle` 文件
        - 读取权限列表，更新应用权限清单 `AndroidManifest.xml` 文件

`build.py` 用于执行构建任务，并将最后的构建产物、产物元数据拷贝到**分发仓库**目录下

`push.py` 用于执行**分发仓库**的提交，负责将构建后的产物、元数据添加到 git 追踪，并按照要求使用时间标识提交

`parse_readme.py` 工具函数，用于解析**分发仓库**中的自述文件，从中提取版本信息

`parse_manifest.py` 工具函数，用于处理打包请求配置文件 `README.md` 中的权限列表，识别出默认权限、添加权限、删除权限


## Todo

- 修改 nodejs 脚本
- 增加对第三方模块的自动检查识别
