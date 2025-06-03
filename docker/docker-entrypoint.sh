#!/bin/sh
set -e

# 等待数据库文件就绪
if [ ! -f "/app/webhook/webhook_server.db" ]; then
    echo "数据库文件不存在，等待初始化..."
    sleep 5
fi

# 执行清理脚本
./cleanup.sh

# 执行传入的命令
exec "$@"
