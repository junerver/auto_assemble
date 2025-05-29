import json
import logging
import sqlite3
from typing import Any

from webhook.models.webhook_request import WebhookRequest
from webhook.types import GitLabPushEventModel


class WebhookRequestService:
    @staticmethod
    def save_webhook_request(task_id, request_data: dict[str, Any], headers=None, db: sqlite3.Connection = None):
        """
        保存webhook请求记录
        Args:
            task_id: 任务id
            request_data: 请求体
            headers: 请求头
            db:
        """
        try:
            request_body = json.dumps(request_data) if isinstance(request_data, dict) else request_data
            # 向header中插入自定义标头，表示这是一个缓存的请求
            headers["X-Webhook-Request-Cache"] = "true"

            headers_str = json.dumps(headers) if headers else None

            webhook_request = WebhookRequest(task_id, request_body, headers_str)
            webhook_request.save(db)
            logging.info(f"成功保存webhook请求记录，task_id: {task_id}")
            return True
        except Exception as e:
            logging.error(f"保存webhook请求记录失败: {str(e)}")
            return False

    @staticmethod
    def save_webhook_requests(tasks, event: GitLabPushEventModel, headers=None, db: sqlite3.Connection = None):
        """
        保存多个webhook请求记录，多条任务需要清洗request_data，确保commits中只包含当前任务的commit，通过task.commit_hash对比字典中的 commits.id，
        即保存的request_data中只包含当前任务的commit，这样才能实现多任务处理的同时，还能针对单任务进行重播
        """
        for task in tasks:
            logging.info(f"保存\清洗webhook请求记录，task_id: {task.id}")

            # 多条任务需要清洗request_data，确保commits中只包含当前任务的commit，通过task.commit_hash对比字典中的 commits.id
            filtered_commits = [commit for commit in event.commits if commit.id == task.commit_hash]
            request_data = event.model_dump(exclude={"commits"})
            request_data["commits"] = [c.model_dump() for c in filtered_commits]
            WebhookRequestService.save_webhook_request(task.id, request_data, headers, db)

    @staticmethod
    def get_webhook_request(task_id, db: sqlite3.Connection = None):
        """获取webhook请求记录"""
        try:
            request = WebhookRequest.get_by_task_id(task_id, db)
            if request:
                return request.to_dict()
            return None
        except Exception as e:
            logging.error(f"获取webhook请求记录失败: {str(e)}")
            return None

    @staticmethod
    def delete_webhook_request(task_id, db: sqlite3.Connection = None):
        """删除webhook请求记录"""
        try:
            WebhookRequest.delete_by_task_id(task_id, db)
            logging.info(f"成功删除webhook请求记录，task_id: {task_id}")
            return True
        except Exception as e:
            logging.error(f"删除webhook请求记录失败: {str(e)}")
            return False

    @staticmethod
    def replay_webhook_request(task_id, db: sqlite3.Connection = None):
        """重放webhook请求"""
        try:
            request = WebhookRequest.get_by_task_id(task_id, db)
            if not request:
                return None, "未找到对应的webhook请求记录", 404

            # 解析请求体和请求头
            request_data = json.loads(request.request_body)
            headers = json.loads(request.headers) if request.headers else {}

            return request_data, headers, 200
        except Exception as e:
            logging.error(f"重放webhook请求失败: {str(e)}")
            return None, str(e), 500

    @staticmethod
    def update_replay_count(task_id, db: sqlite3.Connection = None):
        """更新webhook请求记录的replay_count"""
        try:
            WebhookRequest.update_replay_count(task_id, db)
            return True
        except Exception as e:
            logging.error(f"更新webhook请求记录的replay_count失败: {str(e)}")
            return False
