# 使用运行时镜像作为基础
FROM auto_assemble-runtime:latest

# 保存git凭证
RUN git config --global credential.helper store && \
    echo "http://junerver%40qq.com:tKKBSQCRsvSd3Sh@192.168.187.232:28088" >> ~/.git-credentials && \
    echo "http://houwenjun:%40Aa123456@192.168.187.209:22999" >> ~/.git-credentials && \
    git config --global user.name "assemble_bot" && \
    git config --global user.email "assemble_bot@jkr.com"

# 复制项目文件
COPY --chown=appuser:appuser auto_assemble ./auto_assemble
COPY --chown=appuser:appuser webhook ./webhook
COPY --chown=appuser:appuser cbr ./cbr
COPY --chown=appuser:appuser manager_client ./manager_client
COPY --chown=appuser:appuser docker-entrypoint.sh ./docker-entrypoint.sh
COPY --chown=appuser:appuser pyproject.toml ./pyproject.toml

# 安装项目依赖和模块
RUN pip install -e .

# 设置入口点权限
RUN chmod +x docker-entrypoint.sh

# 设置环境变量
ENV FLASK_APP=webhook/__main__.py \
    FLASK_ENV=production

EXPOSE 5005

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "webhook"]
