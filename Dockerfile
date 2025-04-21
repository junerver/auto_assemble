# 使用Python 3.11 Alpine作为基础镜像
FROM python:3.13.3-alpine

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    wget \
    && pip install --no-cache-dir --upgrade pip

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建非root用户
RUN adduser -D -g '' appuser \
    && chown -R appuser:appuser /app

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