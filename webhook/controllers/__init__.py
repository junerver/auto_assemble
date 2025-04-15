from flask import Blueprint

# 创建蓝图
webhook_bp = Blueprint("webhook", __name__)
project_bp = Blueprint("project", __name__)
task_bp = Blueprint("task", __name__)
third_party_bp = Blueprint("third_party", __name__)

# 导入路由
from .webhook_controller import *
from .project_controller import *
from .task_controller import *
from .third_party_controller import *
