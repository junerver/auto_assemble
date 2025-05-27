# 使用运行时镜像作为基础
FROM auto_assemble-runtime:uv

# 保存git凭证
RUN git config --global credential.helper store && \
    echo "http://junerver%40qq.com:tKKBSQCRsvSd3Sh@192.168.187.232:28088" >> ~/.git-credentials && \
    git config --global user.name "assemble_bot" && \
    git config --global user.email "assemble_bot@jkr.com"

# 复制项目文件
COPY --chown=appuser:appuser auto_assemble ./auto_assemble
COPY --chown=appuser:appuser webhook ./webhook
COPY --chown=appuser:appuser common ./common
COPY --chown=appuser:appuser fork_task ./fork_task
COPY --chown=appuser:appuser docker-entrypoint.sh ./docker-entrypoint.sh
COPY --chown=appuser:appuser pyproject.docker.toml ./pyproject.toml
COPY --chown=appuser:appuser cleanup.sh ./cleanup.sh
COPY --chown=appuser:appuser resource/ApkDiffPatch_v1.8.0 ./ApkDiffPatch

# ADP 可执行
RUN chmod +x /app/ApkDiffPatch/*

ENV PATH="/app/ApkDiffPatch:${PATH}"

# 设置环境变量
ENV FLASK_APP=webhook/__main__.py \
    FLASK_ENV=production \
    GRADLE_USER_HOME=/home/appuser/.gradle

# 删除文件中的回车符并设置权限
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && \
    sed -i 's/\r$//' /app/cleanup.sh && \
    chmod +x /app/docker-entrypoint.sh && \
    chmod +x /app/cleanup.sh && \
    # 创建 gradle 目录并设置权限
    mkdir -p $GRADLE_USER_HOME && \
    chown -R appuser:appuser $GRADLE_USER_HOME && \
    # 安装项目依赖和模块
    uv python install 3.13 && \
    uv sync && \
    uv pip install -e .

EXPOSE 5005

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uv", "run", "webhook"]
