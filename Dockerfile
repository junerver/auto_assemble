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
COPY resource/commandlinetools-linux-13114758_latest.zip /tmp/
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
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    python3.11-venv \
    passwd \
    login \
    adduser \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip \
    && pip install --no-cache-dir --upgrade pip

# 创建并激活虚拟环境
ENV VIRTUAL_ENV=/app/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 安装Python依赖
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制 Android 环境
COPY --from=android-builder /opt/android-sdk /opt/android-sdk
COPY --from=android-builder /opt/java /opt/java

# 设置环境变量
ENV ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    JAVA_HOME=/opt/java \
    PATH="$PATH:/opt/java/bin:/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:$VIRTUAL_ENV/bin"

# 创建非 root 用户
RUN addgroup --system --gid 1000 appuser \
    && adduser --system --uid 1000 --gid 1000 appuser \
    && mkdir -p /home/appuser \
    && chown -R appuser:appuser /app /opt/android-sdk /opt/java /home/appuser

# 切换用户前复制 .netrc
COPY resource/.netrc /home/appuser/.netrc
RUN chmod 600 /home/appuser/.netrc && chown appuser:appuser /home/appuser/.netrc

# 切换为 appuser
USER appuser
WORKDIR /app

# 设置 HOME 环境变量
ENV HOME=/home/appuser

# 准备 Git 认证
RUN echo '#!/bin/sh' > /home/appuser/git-askpass.sh \
    && echo 'case "$1" in *Username*) echo "junerver@qq.com";; *Password*) echo "tKKBSQCRsvSd3Sh";; esac' >> /home/appuser/git-askpass.sh \
    && chmod +x /home/appuser/git-askpass.sh

# 配置 Git 和克隆仓库
ENV GIT_ASKPASS=/home/appuser/git-askpass.sh
RUN git config --global user.name "assemble_bot" \
    && git config --global user.email "assemble_bot@jkr.com" \
    && git clone "http://192.168.187.232:28088/rdcenter/app-distribution.git" /app/distribution \
    && rm /home/appuser/git-askpass.sh

# 复制项目文件（必须在 USER appuser 之后，否则权限出错）
COPY --chown=appuser:appuser auto_assemble ./auto_assemble
COPY --chown=appuser:appuser webhook ./webhook
COPY --chown=appuser:appuser cbr ./cbr
COPY --chown=appuser:appuser manager_client ./manager_client
COPY --chown=appuser:appuser docker-entrypoint.sh ./docker-entrypoint.sh
COPY --chown=appuser:appuser pyproject.toml ./pyproject.toml

# 安装 auto_assemble 模块
RUN pip install -e .

# 设置入口点权限
RUN chmod +x docker-entrypoint.sh

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=webhook/__main__.py \
    FLASK_ENV=production

EXPOSE 5005

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "webhook"]
