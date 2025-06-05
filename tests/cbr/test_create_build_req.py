import unittest
from unittest.mock import MagicMock, patch, mock_open

from cbr.create_build_req import create_build_req, rolling_req_build_status, check_git_lfs_installed
from common.types import TaskInfo


class TestCreateBuildReq(unittest.TestCase):
    """测试 create_build_req 函数"""

    @patch("cbr.create_build_req.setup_logging")
    @patch("cbr.create_build_req.argparse.ArgumentParser")
    @patch("cbr.create_build_req.load_dotenv")
    @patch("cbr.create_build_req.config")
    @patch("cbr.create_build_req.scan_uni_project")
    @patch("cbr.create_build_req.check_uni_project")
    @patch("cbr.create_build_req.Path")
    def test_create_build_req_missing_env_file(
        self,
        mock_path_class,
        mock_check_uni,
        mock_scan_uni,
        mock_config,
        mock_load_dotenv,
        mock_parser_class,
        mock_setup_logging,
    ):
        """测试缺少 .env 文件的情况"""
        # 设置 mock
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.uni = "/test/uni/project"
        mock_args.message = None
        mock_args.dev = True
        mock_args.test = False
        mock_args.release = False
        mock_parser.parse_args.return_value = mock_args

        # 设置 .env 文件不存在
        mock_env_path = MagicMock()
        mock_path_class.return_value = mock_env_path
        mock_env_path.exists.return_value = False

        # 执行测试
        result = create_build_req()

        # 验证结果
        self.assertEqual(result, 1)

    @patch("cbr.create_build_req.setup_logging")
    @patch("cbr.create_build_req.argparse.ArgumentParser")
    def test_create_build_req_missing_uni_arg(self, mock_parser_class, mock_setup_logging):
        """测试缺少 --uni 参数的情况"""
        # 设置 mock
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.uni = None  # 缺少 uni 参数
        mock_parser.parse_args.return_value = mock_args

        # 执行测试
        result = create_build_req()

        # 验证结果
        self.assertEqual(result, 1)


class TestRollingReqBuildStatus(unittest.TestCase):
    """测试 rolling_req_build_status 函数"""

    @patch("cbr.create_build_req.config")
    @patch("cbr.create_build_req.time.sleep")
    @patch("cbr.create_build_req.fetch_task_info")
    @patch("cbr.create_build_req.sync_repository")
    @patch("cbr.create_build_req.toast")
    def test_rolling_req_build_status_completed(
        self, mock_toast, mock_sync_repo, mock_fetch_task, mock_sleep, mock_config
    ):
        """测试构建完成的情况"""
        # 设置 config mock
        mock_config.cur_task_id = "test_task_id"
        mock_config.DISTRIBUTION_PATH = "/test/distribution"
        mock_config.cur_task_dir = "/test/task/dir"

        # 设置任务信息
        completed_task = TaskInfo(
            id="test_id",
            author="test_author",
            commit_title="test_commit_title",
            commit_message="test_commit_message",
            commit_url="test_commit_url",
            priority=0,
            retries=0,
            created_at="2023-01-01T00:00:00",
            started_at=None,
            completed_at=None,
            status="completed",
            error=None,
            commit_hash=None,
            response_hash=None,
            metadata=None,
            source_task_id=None,
            project="test_project",
            task="test_task",
        )

        # 配置 fetch_task_info 的行为
        def fetch_side_effect(task_id, on_success, on_error):
            self.assertEqual(task_id, "test_task_id")  # 验证传入的 task_id 是否正确
            on_success(completed_task)

        mock_fetch_task.side_effect = fetch_side_effect

        # 执行测试
        rolling_req_build_status()

        # 验证调用
        mock_sync_repo.assert_called_once_with("/test/distribution")
        mock_toast.assert_called_once()

    @patch("cbr.create_build_req.config")
    @patch("cbr.create_build_req.time.sleep")
    @patch("cbr.create_build_req.fetch_task_info")
    @patch("cbr.create_build_req.toast")
    def test_rolling_req_build_status_failed(self, mock_toast, mock_fetch_task, mock_sleep, mock_config):
        """测试构建失败的情况"""
        # 设置 config mock
        mock_config.cur_task_id = "test_task_id"
        mock_config.DISTRIBUTION_PATH = "/test/distribution"
        mock_config.cur_task_dir = "/test/task/dir"

        # 设置任务信息
        failed_task = TaskInfo(
            id="test_id",
            author="test_author",
            commit_title="test_commit_title",
            commit_message="test_commit_message",
            commit_url="test_commit_url",
            priority=0,
            retries=0,
            created_at="2023-01-01T00:00:00",
            started_at=None,
            completed_at=None,
            status="failed",
            error=None,
            commit_hash=None,
            response_hash=None,
            metadata=None,
            source_task_id=None,
            project="test_project",
            task="test_task",
        )

        # 配置 fetch_task_info 的行为
        def fetch_side_effect(task_id, on_success, on_error):
            self.assertEqual(task_id, "test_task_id")  # 验证传入的 task_id 是否正确
            on_success(failed_task)

        mock_fetch_task.side_effect = fetch_side_effect

        # 执行测试
        rolling_req_build_status()

        # 验证调用
        mock_toast.assert_called_once()

    @patch("cbr.create_build_req.config")
    @patch("cbr.create_build_req.time.sleep")
    @patch("cbr.create_build_req.fetch_task_info")
    @patch("cbr.create_build_req.sync_repository")
    @patch("cbr.create_build_req.toast")
    def test_rolling_req_build_status_running_then_completed(
        self, mock_toast, mock_sync_repo, mock_fetch_task, mock_sleep, mock_config
    ):
        """测试先运行后完成的情况"""
        # 设置 config mock
        mock_config.cur_task_id = "test_task_id"
        mock_config.DISTRIBUTION_PATH = "/test/distribution"
        mock_config.cur_task_dir = "/test/task/dir"

        # 设置任务信息
        running_task = TaskInfo(
            id="test_id",
            author="test_author",
            commit_title="test_commit_title",
            commit_message="test_commit_message",
            commit_url="test_commit_url",
            priority=0,
            retries=0,
            created_at="2023-01-01T00:00:00",
            started_at=None,
            completed_at=None,
            status="running",
            error=None,
            commit_hash=None,
            response_hash=None,
            metadata=None,
            source_task_id=None,
            project="test_project",
            task="test_task",
        )
        completed_task = TaskInfo(
            id="test_id",
            author="test_author",
            commit_title="test_commit_title",
            commit_message="test_commit_message",
            commit_url="test_commit_url",
            priority=0,
            retries=0,
            created_at="2023-01-01T00:00:00",
            started_at=None,
            completed_at=None,
            status="completed",
            error=None,
            commit_hash=None,
            response_hash=None,
            metadata=None,
            source_task_id=None,
            project="test_project",
            task="test_task",
        )

        call_count = 0

        def fetch_side_effect(task_id, on_success, on_error):
            nonlocal call_count
            call_count += 1
            self.assertEqual(task_id, "test_task_id")  # 验证传入的 task_id 是否正确
            if call_count == 1:
                on_success(running_task)
            else:
                on_success(completed_task)

        mock_fetch_task.side_effect = fetch_side_effect

        # 执行测试
        rolling_req_build_status()

        # 验证调用次数
        self.assertEqual(mock_fetch_task.call_count, 2)
        mock_sleep.assert_called_once()
        mock_sync_repo.assert_called_once_with("/test/distribution")
        mock_toast.assert_called_once()


class TestCheckGitLfsInstalled(unittest.TestCase):
    """测试 check_git_lfs_installed 函数"""

    @patch("builtins.open", new_callable=mock_open)
    @patch("cbr.create_build_req.Path")
    def test_check_git_lfs_installed_true(self, mock_path_class, mock_file):
        """测试 Git LFS 已安装的情况"""
        # 设置 mock
        mock_pre_push_hook = MagicMock()
        mock_hooks_path = MagicMock()
        mock_repo_path = MagicMock()

        mock_path_class.side_effect = lambda path: {
            "/test/repo": mock_repo_path,
            "/test/repo/.git/hooks": mock_hooks_path,
            "/test/repo/.git/hooks/pre-push": mock_pre_push_hook,
        }.get(str(path), MagicMock())

        mock_pre_push_hook.exists.return_value = True
        mock_file.return_value.read.return_value = "#!/bin/sh\ngit-lfs pre-push\n"

        # 执行测试
        result = check_git_lfs_installed("/test/repo")

        # 验证结果
        self.assertTrue(result)

    @patch("builtins.open", new_callable=mock_open)
    @patch("cbr.create_build_req.Path")
    def test_check_git_lfs_installed_false_no_hook(self, mock_path_class, mock_file):
        """测试 Git LFS 未安装且 pre-push hook 不存在的情况"""
        # 创建模拟对象
        mock_repo_path = MagicMock()
        mock_git_path = MagicMock()
        mock_hooks_path = MagicMock()
        mock_pre_push_hook = MagicMock()

        # 设置 Path 构造函数
        mock_path_class.return_value = mock_repo_path

        # 设置路径操作的返回值
        def truediv_side_effect(path):
            if path == ".git":
                return mock_git_path
            elif path == "hooks":
                return mock_hooks_path
            elif path == "pre-push":
                return mock_pre_push_hook
            return MagicMock()

        mock_repo_path.__truediv__.side_effect = truediv_side_effect
        mock_git_path.__truediv__.side_effect = truediv_side_effect
        mock_hooks_path.__truediv__.side_effect = truediv_side_effect

        # 关键：确保 pre-push hook 不存在
        mock_pre_push_hook.exists.return_value = False

        # 执行测试
        result = check_git_lfs_installed("/test/repo")

        # 验证结果
        self.assertFalse(result)
        mock_file.assert_not_called()

    @patch("builtins.open", new_callable=mock_open)
    @patch("cbr.create_build_req.Path")
    def test_check_git_lfs_installed_false_no_lfs_content(self, mock_path_class, mock_file):
        """测试 hook 存在但不包含 git-lfs 的情况"""
        # 设置 mock
        mock_pre_push_hook = MagicMock()
        mock_hooks_path = MagicMock()
        mock_repo_path = MagicMock()

        mock_path_class.side_effect = lambda path: {
            "/test/repo": mock_repo_path,
            "/test/repo/.git/hooks": mock_hooks_path,
            "/test/repo/.git/hooks/pre-push": mock_pre_push_hook,
        }.get(str(path), MagicMock())

        mock_pre_push_hook.exists.return_value = True
        mock_file.return_value.read.return_value = "#!/bin/sh\necho 'no lfs here'\n"

        # 执行测试
        result = check_git_lfs_installed("/test/repo")

        # 验证结果
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
