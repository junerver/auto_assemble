# 构建阶段：安装Android SDK和JDK
FROM ubuntu:22.04 AS android-builder

# 设置环境变量
ENV ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    JAVA_HOME=/opt/java \
    PATH=$PATH:/opt/java/bin:/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools

# 安装基础工具
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装JDK 17
RUN wget -q https://download.java.net/java/GA/jdk17.0.2/dfd4a8d0985749f896bed50d7138ee7f/8/GPL/openjdk-17.0.2_linux-x64_bin.tar.gz \
    && mkdir -p /opt/java \
    && tar -xzf openjdk-17.0.2_linux-x64_bin.tar.gz -C /opt/java --strip-components=1 \
    && rm openjdk-17.0.2_linux-x64_bin.tar.gz

# 安装Android SDK
COPY sdk/commandlinetools-linux-13114758_latest.zip /tmp/
RUN mkdir -p /opt/android-sdk/cmdline-tools \
    && unzip -q /tmp/commandlinetools-linux-13114758_latest.zip -d /opt/android-sdk/cmdline-tools \
    && mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest \
    && rm /tmp/commandlinetools-linux-13114758_latest.zip

# 安装Android SDK组件
RUN yes | sdkmanager --licenses \
    && sdkmanager "platform-tools" \
    && sdkmanager "platforms;android-35" \
    && sdkmanager "build-tools;35.0.0" \
    && sdkmanager "ndk;25.1.8937393"

# 最终阶段：构建应用镜像
FROM ubuntu:22.04

# 设置工作目录
WORKDIR /app

# 安装系统依赖和Python
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    passwd \
    login \
    adduser \
    gcc \
    libffi-dev \
    libssl-dev \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip \
    && pip install --no-cache-dir --upgrade pip

# 复制依赖文件
COPY requirements.txt ./requirements.txt

# 创建并激活虚拟环境
ENV VIRTUAL_ENV=/app/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 从android-builder阶段复制Android环境
COPY --from=android-builder /opt/android-sdk /opt/android-sdk
COPY --from=android-builder /opt/java /opt/java

# 设置环境变量
ENV ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    JAVA_HOME=/opt/java \
    PATH="$PATH:/opt/java/bin:/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:$VIRTUAL_ENV/bin"

# 复制项目文件
COPY auto_assemble ./auto_assemble
COPY webhook ./webhook
COPY cbr ./cbr
COPY docker-entrypoint.sh ./docker-entrypoint.sh
COPY pyproject.toml ./pyproject.toml

# 安装auto_assemble模块
RUN pip install -e .

# 创建非root用户
RUN addgroup --system --gid 1000 appuser \
    && adduser --system --uid 1000 --gid 1000 appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /opt/android-sdk \
    && chown -R appuser:appuser /opt/java

# 设置入口点脚本权限
RUN chmod +x docker-entrypoint.sh

# 切换到非root用户
USER appuser

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=webhook/__main__.py \
    FLASK_ENV=production

# 暴露端口
EXPOSE 5005

# 设置入口点
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 启动命令
CMD ["python", "-m", "webhook"] 