import json
import logging

from ..models.webhook_request import WebhookRequest


class WebhookRequestService:
    @staticmethod
    def save_webhook_request(task_id, request_data, headers=None):
        """保存webhook请求记录"""
        try:
            request_body = (
                json.dumps(request_data) if isinstance(request_data, dict) else request_data
            )
            # 向header中插入自定义标头，表示这是一个缓存的请求
            headers["X-Webhook-Request-Cache"] = "true"

            headers_str = json.dumps(headers) if headers else None

            webhook_request = WebhookRequest(task_id, request_body, headers_str)
            webhook_request.save()
            logging.info(f"成功保存webhook请求记录，task_id: {task_id}")
            return True
        except Exception as e:
            logging.error(f"保存webhook请求记录失败: {str(e)}")
            return False

    @staticmethod
    def get_webhook_request(task_id):
        """获取webhook请求记录"""
        try:
            request = WebhookRequest.get_by_task_id(task_id)
            if request:
                return request.to_dict()
            return None
        except Exception as e:
            logging.error(f"获取webhook请求记录失败: {str(e)}")
            return None

    @staticmethod
    def delete_webhook_request(task_id):
        """删除webhook请求记录"""
        try:
            WebhookRequest.delete_by_task_id(task_id)
            logging.info(f"成功删除webhook请求记录，task_id: {task_id}")
            return True
        except Exception as e:
            logging.error(f"删除webhook请求记录失败: {str(e)}")
            return False

    @staticmethod
    def replay_webhook_request(task_id):
        """重放webhook请求"""
        try:
            request = WebhookRequest.get_by_task_id(task_id)
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
    def update_replay_count(task_id):
        """更新webhook请求记录的replay_count"""
        try:
            WebhookRequest.update_replay_count(task_id)
        except Exception as e:
            logging.error(f"更新webhook请求记录的replay_count失败: {str(e)}")
            return False
