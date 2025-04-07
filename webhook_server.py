import logging
import os
import subprocess
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("webhook.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

app = Flask(__name__)

# 锁文件路径
LOCK_FILE = Path(__file__).parent / "build.lock"
# 最大等待时间（秒）
MAX_WAIT_TIME = 300  # 5分钟
# 检查间隔（秒）
CHECK_INTERVAL = 10


def is_build_in_progress():
    """检查是否正在构建"""
    return LOCK_FILE.exists()


def wait_for_build_completion():
    """等待正在进行的构建完成"""
    start_time = time.time()
    while is_build_in_progress():
        if time.time() - start_time > MAX_WAIT_TIME:
            logging.warning("等待构建完成超时")
            return False
        time.sleep(CHECK_INTERVAL)
    return True


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # 获取请求数据
        data = request.get_json()
        # 打印请求数据
        # 转换为 JSON 字符串
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        print(json_str)
        if not data:
            logging.warning("收到空的webhook请求")
            return jsonify({"error": "No JSON data received"}), 400

        # 记录webhook事件信息
        event_type = request.headers.get("X-Gitlab-Event")
        project_name = data.get("project", {}).get("name")
        branch = data.get("ref", "").split("/")[-1] if data.get("ref") else None
        commit_id = data.get("after")
        commit_message = (
            data.get("commits", [{}])[0].get("message") if data.get("commits") else None
        )
        commit_author = (
            data.get("commits", [{}])[0].get("author", {}).get("name")
            if data.get("commits")
            else None
        )

        logging.info(f"收到GitLab webhook事件: {event_type}")
        logging.info(f"项目: {project_name}")
        logging.info(f"分支: {branch}")
        logging.info(f"提交ID: {commit_id}")
        logging.info(f"提交信息: {commit_message}")

        # 检查是否是push事件
        if event_type != "Push Hook":
            logging.info(f"忽略非push事件: {event_type}")
            return jsonify({"message": f"Ignored non-push event: {event_type}"}), 200

        # 检查是否正在构建
        if is_build_in_progress():
            logging.info("检测到正在进行的构建，等待完成...")
            if not wait_for_build_completion():
                return jsonify({"message": "Build skipped - previous build timed out"}), 429

        # 创建锁文件
        LOCK_FILE.touch()

        logging.info("开始执行自动构建")
        # 执行自动构建命令，不阻塞
        process = subprocess.Popen(
            ["auto-assemble", "--fn", "1"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            encoding="utf-8",
        )

        # 等待进程完成并删除锁文件
        def cleanup():
            process.wait()
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()

        # 在后台线程中等待进程完成
        import threading

        threading.Thread(target=cleanup, daemon=True).start()

        return (
            jsonify(
                {
                    "message": "Build started successfully",
                    "project": project_name,
                    "branch": branch,
                    "commit_id": commit_id,
                }
            ),
            200,
        )

    except Exception as e:
        logging.error(f"处理webhook请求时发生错误: {str(e)}")
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
        return jsonify({"error": str(e)}), 500


@app.errorhandler(400)
def bad_request(error):
    """处理400错误"""
    return jsonify({"error": "Bad request"}), 400


@app.errorhandler(404)
def not_found(error):
    """处理404错误"""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """处理500错误"""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # 加载环境变量
    load_dotenv()
    # 从环境变量获取端口，默认为5000
    port = int(os.getenv("PORT", 5005))

    # 从环境变量获取是否启用调试模式
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print(f"debug: {debug}")

    # 配置热更新
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    app.run(
        host="0.0.0.0", port=port, ssl_context=None, debug=debug, use_reloader=debug  # 启用代码重载
    )
