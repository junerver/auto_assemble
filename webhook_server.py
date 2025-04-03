import logging
import os
import subprocess
import sys

from flask import Flask, jsonify

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


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        logging.info("收到GitLab推送事件，开始执行自动构建")
        # 执行自动构建命令，不阻塞
        subprocess.Popen(
            ["auto-assemble", "--fn", "1"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            encoding="utf-8",
        )

        return jsonify({"message": "Build successful"}), 200

    except Exception as e:
        logging.error(f"处理webhook请求时发生错误: {str(e)}")
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
    # 从环境变量获取端口，默认为5000
    port = int(os.getenv("PORT", 5005))
    app.run(host="0.0.0.0", port=port, ssl_context=None)
