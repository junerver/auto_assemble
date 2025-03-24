# UniApp项目分发自动打包

## 开发环境设置

1. 克隆项目：
   ```bash
   git clone [项目地址]
   cd review_server
   ```

2. 创建虚拟环境：
   ```bash
   # Windows
   python -m venv venv
   
   # Linux/Mac
   python3 -m venv venv
   ```

3. 激活虚拟环境：
   ```bash
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

4. 安装依赖：

   有两种安装方式：

   a. 使用 requirements.txt（适用于开发环境）：
   ```bash
   pip install -r requirements.txt
   ```

   b. 使用 pip 安装（适用于生产环境）：
   ```bash
   pip install -e .
   ```

## 使用说明

### 生产环境使用


### 开发环境使用
1. 参考 `.env.template` 文件，创建 `.env` 环境变量文件，填写分发工程、基座工程的目录地址、需要指向的项目
2. 执行 `python .\assemble\copy_res.py`，拉取最新资源，拷贝到项目构建工程，填充必要信息，此后需要人工核对内容，确认是否存在模块更新；
3. 在确认完毕后执行 `python .\assemble\build.py` 进行项目构建，拷贝打包后的内容到分发仓库
4. 执行 `python .\assemble\push.py` 添加、提交、推送到分发仓库

工作流脚本：`python .\assemble\auto_flow.py`，直接一键执行上述全部步骤

## 脚本说明

`config.py` 中保存全局的常量配置

`copy_res.py` 用于从分发仓库拉取最新资源，并拷贝资源到构建工程中，同时解析 README.md 文件，读取需要修改的内容。
    - 读取 uniapp id 与 uniapp key，并更新 `build.gradle` 文件
    - 读取 versionName、versionCode，并更新 `build.gradle` 文件
    - 读取 hbx_version ，更新 `lib.version.toml` 文件
    - 读取第三方sdk配置（yml代码块），并更新 `build.gradle` 文件
    - 读取权限列表，更新应用权限清单 `AndroidManifest.xml` 文件

`build.py` 用于执行构建任务，并将最后的构建产物、产物元数据拷贝到分发仓库目录下

`push.py` 用于执行分发仓库的提交，负责将构建后的产物、元数据添加到 git 追踪，并按照要求使用时间标识提交

`parse_readme.py` 工具函数，用于读取分发仓库中的自述文件，从中提取版本信息

`parse_manifest.py` 工具函数，用于处理 README.md 中的权限列表，识别出默认权限、添加权限、删除权限


## Todo

- 修改 nodejs 脚本
- 增加对第三方模块的自动检查识别
