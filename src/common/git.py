import logging
import os
import subprocess
from collections import namedtuple
from pathlib import Path

from common.config import config

GitCommitInfo = namedtuple("GitCommitInfo", ["commit_date", "author", "message", "commit_hash"])


def _get_git_info(repo_path: str) -> GitCommitInfo | None:
    """
    获取Git仓库信息，包含下面信息：
    1. 最后提交时间
    2. 最后提交人
    3. 最后提交信息
    4. 最后提交的MD5
    Args:
        repo_path: Git仓库路径
    Returns:
        GitCommitInfo: (最后提交时间, 最后提交人, 最后提交信息, 最后提交的MD5)
    """
    try:
        # 获取最后一次提交信息
        last_commit = subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%cd,%an,%s,%H",
                "--date=format:%Y-%m-%d %H:%M:%S",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",  # 指定编码为utf-8
            cwd=repo_path,
        )
        if last_commit.returncode == 0:
            commit_date, author, message, commit_hash = last_commit.stdout.strip().split(",", 3)
            return GitCommitInfo(
                commit_date=commit_date,
                author=author,
                message=message,
                commit_hash=commit_hash,
            )
        else:
            logging.error(f"{repo_path} 获取Git信息失败: {last_commit.stderr}")
    except Exception as e:
        logging.exception(f"{repo_path} 获取Git信息失败: {e}")
    return None


def _git_fetch(repo_path: str, is_lfs: bool = False, branch: str = None) -> bool:
    """
    执行git fetch操作, 检查远程是否有更新, 如果本地代码已是最新, 则返回False, 否则返回True
    Args:
        repo_path: Git仓库路径
        is_lfs: 是否为LFS仓库，默认False
    Returns:
        bool: 是否需要拉取更新
    """
    try:
        # 检查远程是否有更新
        if not _git_fetch_branch(repo_path, branch):
            return False

        if is_lfs:
            # LFS文件fetch
            lfs_fetch = subprocess.run(
                ["git", "lfs", "fetch", "--all"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
            )
            if lfs_fetch.returncode != 0:
                logging.error(f"{repo_path} Git LFS fetch失败: {lfs_fetch.stderr}")
                return False
            logging.info(f"{repo_path} Git LFS fetch成功")

        # 检查是否需要更新
        status = subprocess.run(
            ["git", "status", "-uno"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=repo_path,
        )
        if "Your branch is up to date" in status.stdout:
            logging.info(f"{repo_path} 本地代码已是最新版本，无需更新")
            return False
        else:
            logging.info(f"{repo_path} 本地代码有更新，需要更新")
            return True
    except Exception as e:
        logging.exception(f"{repo_path} Git fetch执行失败: {e}")
        return False


def sync_repository(repo_path: str, is_lfs: bool = False, branch: str = None) -> bool:
    """
    同步Git仓库到最新状态
    Args:
        repo_path: Git仓库路径
        is_lfs: 是否为LFS仓库，默认False
        branch:
    Returns:
        bool: 同步是否成功
    """
    try:
        os.chdir(repo_path)

        # 获取更新前的提交信息
        before_commit_info = _get_git_info(repo_path)
        if before_commit_info:
            logging.info(
                f"当前版本 - 提交时间: {before_commit_info.commit_date}, 提交人: {before_commit_info.author}, 提交信息: {before_commit_info.message}"
            )
        # 检查远程是否有更新
        if not _git_fetch(repo_path, is_lfs, branch):
            # 不需要拉取更新说明本地已经是最新
            return True

        # 执行更新
        logging.info(f"{repo_path} 开始执行 git pull 拉取更新")
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            if is_lfs:
                # LFS文件更新
                lfs_pull = subprocess.run(
                    ["git", "lfs", "pull"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=repo_path,
                )
                if lfs_pull.returncode != 0:
                    logging.error(f"{repo_path} Git LFS pull失败: {lfs_pull.stderr}")
                    return False
                logging.info(f"{repo_path} Git LFS pull成功")

            # 获取更新后的提交信息
            after_commit_info = _get_git_info(repo_path)
            if after_commit_info:
                logging.info(f"{repo_path} 更新成功 - 新版本信息:")
                logging.info(f"提交时间: {after_commit_info.commit_date}")
                logging.info(f"提交人: {after_commit_info.author}")
                logging.info(f"提交信息: {after_commit_info.message}")
                logging.info(f"提交哈希: {after_commit_info.commit_hash}")

            return True
        else:
            logging.error(f"{repo_path} Git仓库同步失败: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        logging.error(f"{repo_path} Git命令执行失败: {e}")
        return False
    except Exception as e:
        logging.exception(f"{repo_path} 同步仓库时发生错误: {e}")
        return False


def _git_reset_hard_head(repo_path: str) -> bool:
    """
    执行git reset --hard HEAD操作，重置当前分支最后一次提交
    """
    try:
        result = subprocess.run(
            ["git", "reset", "--hard", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=repo_path,
        )
        if result.returncode != 0:
            logging.error(f"{repo_path} Git reset --hard HEAD执行失败: {result.stderr}")
            return False
        logging.info(f"{repo_path} Git reset --hard HEAD执行成功")
        return True
    except Exception as e:
        logging.exception(f"{repo_path} Git reset --hard HEAD执行失败: {e}")
        return False


def _git_clean_fd(repo_path: str) -> bool:
    """
    执行git clean操作，删除所有未跟踪的文件
    """
    try:
        result = subprocess.run(
            ["git", "clean", "-fd"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=repo_path,
        )
        if result.returncode != 0:
            logging.error(f"{repo_path} Git clean执行失败: {result.stderr}")
            return False
        logging.info(f"{repo_path} Git clean执行成功")
        return True
    except Exception as e:
        logging.exception(f"{repo_path} Git clean执行失败: {e}")
        return False


def git_reset_and_clean(repo_path: str, is_lfs: bool = False) -> bool:
    """
    执行git reset --hard HEAD和git clean -fd操作，重置当前分支最后一次提交并删除所有未跟踪的文件
    Args:
        repo_path: Git仓库路径
        is_lfs: 是否为LFS仓库，默认False
    """
    logging.info(f"开始清理仓库{repo_path} git 缓存")
    try:
        if is_lfs:
            # 清理LFS缓存
            lfs_clean = subprocess.run(
                ["git", "lfs", "clean"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
            )
            if lfs_clean.returncode != 0:
                logging.error(f"{repo_path} Git LFS clean失败: {lfs_clean.stderr}")
                return False
            logging.info(f"{repo_path} Git LFS clean成功")

        if not _git_reset_hard_head(repo_path):
            return False
        if not _git_clean_fd(repo_path):
            return False
        logging.info(f"{repo_path} Git reset --hard HEAD和git clean -fd执行成功")
        return True
    except Exception as e:
        logging.exception(f"{repo_path} Git reset --hard HEAD和git clean -fd执行失败: {e}")
        return False


def check_git_branch(repo_path: str, target_branch: str, is_lfs: bool = False, max_attempts: int = 2) -> bool:
    """
    检查Git项目分支状态并尝试切换到目标分支，需要对基座工程进行远程拉取，保证使用的分支是最新的

    返回True的条件：
    1. 当前已在目标分支
    2. 可以安全切换到目标分支且切换成功
    3. 目标分支不存在但在无未提交更改的情况下，
       切换到master分支后创建新分支 config.PROD_BRANCH 成功

    返回False的条件：
    1. 有未提交的更改
    2. Git命令执行失败
    3. 其他异常情况

    Args:
        repo_path: Git项目路径
        target_branch: 指定的工作分支，如果为空，则使用config.PROD_BRANCH
        is_lfs: 是否为LFS仓库，默认False
        max_attempts: 最大尝试次数，默认2次
    Returns:
        bool: 是否在目标分支或可以安全切换到目标分支
    """
    for attempt in range(max_attempts):
        try:
            logging.info(f"开始检查Git分支: {repo_path}/{target_branch} (尝试 {attempt + 1}/{max_attempts})")

            # 1. 获取远程更新
            if not _git_fetch_branch(repo_path):
                if attempt < max_attempts - 1:
                    logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                    import time

                    time.sleep(2**attempt)
                    continue
                return False

            if is_lfs:
                # LFS文件fetch
                lfs_fetch = subprocess.run(
                    ["git", "lfs", "fetch", "--all"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=repo_path,
                    timeout=120,  # 增加超时时间到120秒
                )
                if lfs_fetch.returncode != 0:
                    logging.error(f"{repo_path} Git LFS fetch失败: {lfs_fetch.stderr}")
                    if attempt < max_attempts - 1:
                        logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                        import time

                        time.sleep(2**attempt)
                        continue
                    return False
                logging.info(f"{repo_path} Git LFS fetch成功")

            # 2. 检查当前分支与远程分支的差异
            diff_proc = subprocess.run(
                ["git", "diff", "HEAD", "origin/HEAD"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=60,  # 增加超时时间
            )
            if diff_proc.returncode != 0:
                logging.error(f"{repo_path} 检查分支差异失败: {diff_proc.stderr}")
                if attempt < max_attempts - 1:
                    logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                    import time

                    time.sleep(2**attempt)
                    continue
                return False

            # 3. 如果有差异，尝试安全地拉取更新
            if diff_proc.stdout.strip():
                # 检查是否有未提交的更改
                status_proc = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=repo_path,
                    timeout=60,
                )
                if status_proc.returncode != 0:
                    logging.error(f"{repo_path} 检查工作区状态失败: {status_proc.stderr}")
                    if attempt < max_attempts - 1:
                        logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                        import time

                        time.sleep(2**attempt)
                        continue
                    return False

                if status_proc.stdout.strip():
                    logging.error(
                        f"{repo_path} 存在未提交的更改，无法安全拉取远程更新, `{status_proc.stdout}`，准备重置并清理"
                    )
                    # 重置并清理
                    if not git_reset_and_clean(repo_path):
                        if attempt < max_attempts - 1:
                            logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                            import time

                            time.sleep(2**attempt)
                            continue
                        return False

                # 尝试拉取更新
                pull_proc = subprocess.run(
                    ["git", "pull", "origin"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=repo_path,
                    timeout=90,
                )
                if pull_proc.returncode != 0:
                    logging.error(f"{repo_path} 拉取远程更新失败: {pull_proc.stderr}")
                    if attempt < max_attempts - 1:
                        logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                        import time

                        time.sleep(2**attempt)
                        continue
                    return False

                logging.info(f"{repo_path} 成功拉取远程更新")

            # 4. 获取当前分支
            current_branch_proc = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=60,  # 增加超时时间
            )
            if current_branch_proc.returncode != 0:
                logging.error(f"{repo_path} 获取当前分支失败: {current_branch_proc.stderr}")
                if attempt < max_attempts - 1:
                    logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                    import time

                    time.sleep(2**attempt)
                    continue
                return False

            current_branch = current_branch_proc.stdout.strip()
            original_branch = current_branch  # 保存原始分支状态
            logging.info(f"当前分支: {current_branch}")

            # 5. 如果已经在目标分支，直接返回True
            if current_branch == target_branch:
                logging.info(f"已在指定分支 {target_branch} 上")
                return True
            logging.info(f"开始准备切换到目标分支: {target_branch}")
            # 6. 检查是否有未提交的更改（安全切换必须确保工作区干净）
            status_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=60,
            )
            if status_proc.returncode != 0:
                logging.error(f"{repo_path} 检查工作区状态失败: {status_proc.stderr}")
                if attempt < max_attempts - 1:
                    logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                    import time

                    time.sleep(2**attempt)
                    continue
                return False

            if out := status_proc.stdout.strip():
                logging.warn(f"{repo_path} 存在未提交的更改，无法安全切换分支: {out}，丢弃")
                if not git_reset_and_clean(repo_path):
                    if attempt < max_attempts - 1:
                        logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                        import time

                        time.sleep(2**attempt)
                        continue
                    return False

            # 7. 检查分支是否存在（包括本地和远程）
            branches_proc = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=60,  # 增加超时时间
            )
            if branches_proc.returncode != 0:
                logging.error(f"{repo_path} 获取分支列表失败: {branches_proc.stderr}")
                if attempt < max_attempts - 1:
                    logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                    import time

                    time.sleep(2**attempt)
                    continue
                return False

            # 更精确的分支匹配
            branches = [branch.strip() for branch in branches_proc.stdout.split("\n") if branch.strip()]
            local_branch_exists = any(branch.replace("*", "").strip() == target_branch for branch in branches)
            remote_branch_exists = any(branch.strip() == f"remotes/origin/{target_branch}" for branch in branches)

            if local_branch_exists:
                # 8. 如果本地分支存在，直接切换
                if not _git_checkout_branch(repo_path, target_branch):
                    if attempt < max_attempts - 1:
                        logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                        import time

                        time.sleep(2**attempt)
                        continue
                    return False

                logging.info(f"{repo_path} 成功切换到目标分支: {target_branch}")
                return True
            elif remote_branch_exists:
                # 9. 如果远程分支存在，从远程分支创建本地分支
                logging.info(f"{repo_path} 从远程分支创建本地分支: {target_branch}")
                if not _git_checkout_branch(
                    repo_path,
                    target_branch,
                    original_branch=f"origin/{target_branch}",
                    create_new=True,
                ):
                    if attempt < max_attempts - 1:
                        logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                        import time

                        time.sleep(2**attempt)
                        continue
                    return False

                logging.info(f"{repo_path} 成功创建并切换到新分支: {target_branch}")
                return True
            else:
                # 10. 如果本地和远程都不存在，从master创建新分支
                logging.info(f"{repo_path} 目标分支不存在，准备从master创建新分支")

                # 从master创建新分支
                if not _git_checkout_branch(repo_path, target_branch, original_branch="master", create_new=True):
                    if attempt < max_attempts - 1:
                        logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                        import time

                        time.sleep(2**attempt)
                        continue
                    return False

                logging.info(f"{repo_path} 成功从master创建并切换到新分支: {target_branch}")
                return True

        except subprocess.TimeoutExpired as e:
            logging.error(f"{repo_path} Git命令执行超时 (尝试 {attempt + 1}/{max_attempts}): {e}")
            # 清理可能残留的锁文件
            clear_git_locks(repo_path)
            # 尝试切回原分支
            try:
                _git_checkout_branch(repo_path, original_branch if "original_branch" in locals() else "master")
            except Exception:
                pass
            if attempt < max_attempts - 1:
                logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                import time

                time.sleep(2**attempt)
                continue
            return False
        except Exception as e:
            logging.exception(f"{repo_path} 分支操作过程中发生错误 (尝试 {attempt + 1}/{max_attempts}): {e}")
            # 尝试切回原分支
            try:
                _git_checkout_branch(repo_path, original_branch if "original_branch" in locals() else "master")
            except Exception:
                pass
            if attempt < max_attempts - 1:
                logging.info(f"将在 {2**attempt} 秒后重试整个流程...")
                import time

                time.sleep(2**attempt)
                continue
            return False

    logging.error(f"{repo_path} 检查Git分支失败，已达到最大尝试次数 {max_attempts}")
    return False


def _git_checkout_branch(
    repo_path: str,
    target_branch: str,
    original_branch: str = None,
    create_new: bool = False,
    max_retries: int = 3,
    timeout: int = 120,
):
    """
    切换到目标分支，如果目标分支不存在，则创建新分支
    Args:
        repo_path: Git仓库路径
        target_branch: 目标分支
        original_branch: 原始分支
        create_new: 是否创建新分支，默认False
        max_retries: 最大重试次数，默认3次
        timeout: 超时时间（秒），默认120秒
    """
    for attempt in range(max_retries):
        try:
            logging.info(f"开始切换到目标分支: {repo_path}/{target_branch} (尝试 {attempt + 1}/{max_retries})")
            cmd = ["git", "checkout"]
            if create_new:
                cmd.append("-b")
            cmd.append(target_branch)
            if original_branch is not None:
                cmd.append(original_branch)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=timeout,
            )
            if result.returncode != 0:
                logging.error(f"{repo_path} 切换到目标分支失败: {result.stderr}")
                if attempt < max_retries - 1:
                    logging.info(f"将在 {2**attempt} 秒后重试...")
                    import time

                    time.sleep(2**attempt)  # 指数退避
                    continue
                return False

            logging.info(f"{repo_path} 成功切换到目标分支: {target_branch}")
            return True

        except subprocess.TimeoutExpired as e:
            logging.error(f"{repo_path} 切换分支超时 (超时时间: {timeout}秒): {e}")
            if attempt < max_retries - 1:
                logging.info(f"将在 {2**attempt} 秒后重试...")
                import time

                time.sleep(2**attempt)
                continue
            logging.error(f"{repo_path} 切换分支超时，已达到最大重试次数 {max_retries}")
            return False
        except Exception as e:
            logging.exception(f"{repo_path} 切换到目标分支失败: {e}")
            if attempt < max_retries - 1:
                logging.info(f"将在 {2**attempt} 秒后重试...")
                import time

                time.sleep(2**attempt)
                continue
            return False

    return False


def _git_fetch_branch(repo_path: str, branch: str = None, max_retries: int = 2, timeout: int = 90):
    """
    获取指定分支的最新提交
    Args:
        repo_path: Git仓库路径
        branch: 指定分支，如果为空，则获取所有分支
        max_retries: 最大重试次数，默认2次
        timeout: 超时时间（秒），默认90秒
    Returns:
        bool: 获取指定分支最新提交是否成功
    """
    for attempt in range(max_retries):
        try:
            cmd = ["git", "fetch", "origin"]
            if branch is not None:
                cmd.append(branch)

            logging.info(f"获取分支更新: {repo_path} (尝试 {attempt + 1}/{max_retries})")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=timeout,
            )
            if result.returncode != 0:
                logging.error(f"{repo_path} 获取指定分支最新提交失败: {result.stderr}")
                if attempt < max_retries - 1:
                    logging.info(f"将在 {2**attempt} 秒后重试...")
                    import time

                    time.sleep(2**attempt)
                    continue
                return False

            logging.info(f"{repo_path} 成功获取分支更新")
            return True

        except subprocess.TimeoutExpired as e:
            logging.error(f"{repo_path} fetch 分支超时 (超时时间: {timeout}秒): {e}")
            if attempt < max_retries - 1:
                logging.info(f"将在 {2**attempt} 秒后重试...")
                import time

                time.sleep(2**attempt)
                continue
            logging.error(f"{repo_path} fetch 分支超时，已达到最大重试次数 {max_retries}")
            return False
        except Exception as e:
            logging.exception(f"{repo_path} 获取指定分支最新提交失败: {e}")
            if attempt < max_retries - 1:
                logging.info(f"将在 {2**attempt} 秒后重试...")
                import time

                time.sleep(2**attempt)
                continue
            return False

    return False


def get_untracked_files(repo_path: str) -> list[str]:
    """获取未跟踪的文件列表

    Args:
        repo_path: 仓库路径
    Returns
        list[]: 未跟踪的文件列表
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        if result.returncode != 0:
            logging.error(f"{repo_path} 获取git状态失败")
            return []

        files = []
        for line in result.stdout.splitlines():
            if line.startswith("??"):  # 未跟踪的文件
                files.append(line[3:])
                logging.info(f"     -{line[3:]}")
        return files
    except Exception as e:
        logging.exception(f"{repo_path} 获取未跟踪文件时发生错误: {str(e)}")
        return []


def get_staged_files(repo_path: str) -> list[str]:
    """获取已暂存的文件列表"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        if result.returncode != 0:
            logging.error(f"{repo_path} 获取暂存文件列表失败")
            return []

        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception as e:
        logging.exception(f"{repo_path} 获取暂存文件列表时发生错误: {str(e)}")
        return []


def git_add(repo_path: str) -> bool:
    """执行git add操作"""
    try:
        result = subprocess.run(["git", "add", "."], capture_output=True, text=True, cwd=repo_path)
        if result.returncode != 0:
            # 如果是因为锁文件问题，先清理锁文件再重试
            if "Unable to create" in result.stderr and "index.lock" in result.stderr:
                logging.warning(f"{repo_path} 检测到锁文件问题，尝试清理锁文件...")
                clear_git_locks(repo_path)
                # 重试一次
                result = subprocess.run(["git", "add", "."], capture_output=True, text=True, cwd=repo_path)
                if result.returncode != 0:
                    logging.error(f"{repo_path} git add 清理锁文件后重试仍然失败: {result.stderr}")
                    return False
                else:
                    logging.info(f"{repo_path} git add 清理锁文件后重试成功")
            else:
                logging.error(f"{repo_path} git add 执行失败: {result.stderr}")
                return False
        logging.info(f"{repo_path} git add 执行成功")
        return True
    except Exception as e:
        logging.exception(f"{repo_path} git add 执行时发生错误: {str(e)}")
        return False


def git_commit(commit_message: str, repo_path: str, author: str = None) -> bool:
    """
    执行git commit操作，默认工作目录为config.DISTRIBUTION_PATH

    Args:
    - commit_message: 提交信息
    - repo_path: 当前工作目录
    - author: 提交作者，git要求的格式为 "名字 <邮箱>"，例如 "John Doe <john@example.com>"，
              这里固定使用 <assemble_bot@jkr.com> 作为邮箱
    Return:
    - True: 执行成功
    - False: 执行失败
    """
    try:
        cmd = ["git", "commit"]
        if author is not None:
            cmd.extend(["--author", f"{author} <assemble_bot@jkr.com>"])
        cmd.extend(["-m", commit_message])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=repo_path,
            encoding="utf-8",  # ✅ 修改为 utf-8
            errors="replace",  # ✅ 可选，避免报错，替换非法字符
        )
        if result.returncode != 0:
            # 如果是因为锁文件问题，先清理锁文件再重试
            if "Unable to create" in result.stderr and "index.lock" in result.stderr:
                logging.warning(f"{repo_path} git commit 检测到锁文件问题，尝试清理锁文件...")
                clear_git_locks(repo_path)
                # 重试一次
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=repo_path,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.returncode != 0:
                    logging.error(f"{repo_path} git commit 清理锁文件后重试仍然失败: {result.stderr}")
                    return False
                else:
                    logging.info(f"{repo_path} git commit 清理锁文件后重试成功")
            else:
                logging.error(f"{repo_path} git commit 执行失败: {result.stderr}")
                return False
        logging.info(f"{repo_path} git commit 执行成功，提交信息: {commit_message}")
        return True
    except Exception as e:
        logging.exception(f"{repo_path} git commit 执行时发生错误: {str(e)}")
        return False


def git_push(repo_path: str, is_lfs: bool = False) -> bool:
    """
    执行git push操作
    当远程分支领先于本地分支时,自动执行rebase操作
    Args:
        repo_path: Git仓库路径
        is_lfs: 是否为LFS仓库，默认False
    """
    try:
        if is_lfs:
            # 先推送LFS文件
            lfs_push = subprocess.run(
                ["git", "lfs", "push", "--all", "origin"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            if lfs_push.returncode != 0:
                logging.error(f"{repo_path} Git LFS push失败: {lfs_push.stderr}")
                return False
            logging.info(f"{repo_path} Git LFS push成功")

        # 首先尝试push
        result = subprocess.run(
            ["git", "push"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )

        if result.returncode == 0:
            logging.info(f"{repo_path} git push 执行成功")
            return True

        # 检查是否是因为远程分支领先导致的失败
        if "git pull" in result.stderr or "rejected" in result.stderr:
            logging.info(f"{repo_path} 检测到远程分支领先,尝试执行rebase操作")

            # 获取当前分支名
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            if branch_result.returncode != 0:
                logging.error(f"{repo_path} 获取当前分支名失败: {branch_result.stderr}")
                return False

            current_branch = branch_result.stdout.strip()

            # 执行fetch
            if not _git_fetch_branch(repo_path, current_branch):
                return False

            # 执行rebase
            rebase_result = subprocess.run(
                ["git", "rebase", f"origin/{current_branch}"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            if rebase_result.returncode != 0:
                logging.error(f"{repo_path} git rebase 失败,可能存在冲突: {rebase_result.stderr}")
                # 中止rebase
                subprocess.run(
                    ["git", "rebase", "--abort"],
                    capture_output=True,
                    text=True,
                    cwd=repo_path,
                )
                return False

            # rebase成功后重新push
            push_result = subprocess.run(
                ["git", "push"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            if push_result.returncode != 0:
                logging.error(f"{repo_path} rebase后push仍然失败: {push_result.stderr}")
                return False

            logging.info(f"{repo_path} rebase并push成功")
            return True
        else:
            logging.error(f"{repo_path} git push 执行失败: {result.stderr}")
            return False

    except Exception as e:
        logging.exception(f"{repo_path} git push 执行时发生错误: {str(e)}")
        return False


def confirm_push(staged_files, commit_message) -> bool:
    """确认是否推送"""
    logging.info("=" * 50)
    logging.info("推送确认")
    logging.info("=" * 50)
    logging.info("本次提交的文件:")
    for file in staged_files:
        logging.info(f"  - {file}")
    logging.info(f"提交信息: {commit_message}")
    logging.info(f"提交人: {config.current_author}")
    logging.info("=" * 50)

    if config.work_mode == "ui":
        user_input = input("\n是否推送本次提交？(Y/y 确认，直接回车取消): ").strip()
        return user_input.lower() == "y"
    else:
        return True


def has_changes(cwd=config.DISTRIBUTION_PATH) -> bool:
    """检查是否有任何修改（包括未跟踪和已修改的文件）"""
    try:
        # 检查未跟踪的文件
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if result.returncode != 0:
            logging.error("获取未跟踪文件列表失败")
            return False

        # 检查已修改的文件
        modified_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if modified_result.returncode != 0:
            logging.error("获取git状态失败")
            return False

        # 如果有未跟踪的文件或已修改的文件，返回True
        return bool(result.stdout.strip()) or bool(modified_result.stdout.strip())
    except Exception as e:
        logging.exception(f"检查git状态时发生错误: {str(e)}")
        return False


def get_git_config(repo_path: str) -> dict:
    """
    Args:
        repo_path: Git 项目所在目录
    Returns:
        包含用户名和邮箱的字典
    """
    original_dir = None
    if os.path.exists(os.path.join(repo_path, ".git")):
        # 保存当前工作目录
        original_dir = os.getcwd()
    try:
        if original_dir:
            os.chdir(repo_path)
        # 执行 git config 命令获取用户名和邮箱
        username = (
            subprocess.check_output(
                ["git", "config", "user.name"],
                text=False,
            )
            .decode("utf-8")
            .strip()
        )
        email = (
            subprocess.check_output(
                ["git", "config", "user.email"],
                text=False,
            )
            .decode("utf-8")
            .strip()
        )

        return {"username": username, "email": email}

    except subprocess.CalledProcessError:
        raise ValueError("无法获取 Git 配置，可能未设置用户名或邮箱")
    finally:
        if original_dir:
            os.chdir(original_dir)


def get_git_author_str(repo_path: str) -> str:
    """
    获取git标准格式的用户信息
    Args:
        repo_path:

    Returns:

    """
    user_config = get_git_config(repo_path)
    return f"{user_config['username']} <{user_config['email']}>"


def parse_git_author(author: str) -> tuple[str, str]:
    """
    解析标准git用户信息
    Args:
        author:

    Returns:
        tuple[str,str]: username,email

    """
    return author.split("<")[0].strip(), author.split("<")[1].split(">")[0].strip()


def clear_git_locks(repo_path: str) -> bool:
    """
    清理Git仓库中的锁文件，解决因进程中断导致的锁文件残留问题
    Args:
        repo_path: Git仓库路径
    Returns:
        bool: 清理是否成功
    """
    try:
        git_dir = Path(repo_path) / ".git"
        if not git_dir.exists():
            return True

        cleared_files = []

        # 清理常见的锁文件
        lock_files = [
            "index.lock",
            "HEAD.lock",
            "refs/heads/master.lock",
            "refs/heads/main.lock",
            "refs/stash.lock",
            "refs/remotes/origin/HEAD.lock",
        ]

        for lock_file in lock_files:
            lock_path = git_dir / lock_file
            if lock_path.exists():
                try:
                    lock_path.unlink()
                    cleared_files.append(str(lock_file))
                    logging.info(f"{repo_path} 清理锁文件: {lock_file}")
                except Exception as e:
                    logging.error(f"{repo_path} 清理锁文件失败 {lock_file}: {e}")

        # 查找并清理其他可能的锁文件
        for lock_file in git_dir.rglob("*.lock"):
            if lock_file.is_file():
                try:
                    lock_file.unlink()
                    cleared_files.append(str(lock_file.relative_to(git_dir)))
                    logging.info(f"{repo_path} 清理锁文件: {lock_file.relative_to(git_dir)}")
                except Exception as e:
                    logging.error(f"{repo_path} 清理锁文件失败 {lock_file}: {e}")

        if cleared_files:
            logging.info(f"{repo_path} 总共清理了 {len(cleared_files)} 个锁文件: {cleared_files}")
        else:
            logging.debug(f"{repo_path} 没有发现需要清理的锁文件")

        return True

    except Exception as e:
        logging.exception(f"{repo_path} 清理Git锁文件时发生错误: {e}")
        return False


def check_git_lfs_installed(repo_path: str) -> bool:
    """
    检查git lfs是否安装，检查.git/hooks目录下的pre-push文件是否存在git-lfs
    """
    hooks_path = Path(repo_path) / ".git" / "hooks"
    pre_push_hook = hooks_path / "pre-push"
    if pre_push_hook.exists():
        with open(pre_push_hook, "r") as f:
            content = f.read()
            if "git-lfs" in content:
                return True
    return False


__all__ = [
    "sync_repository",
    "git_reset_and_clean",
    "check_git_branch",
    "get_untracked_files",
    "get_staged_files",
    "git_add",
    "git_commit",
    "git_push",
    "confirm_push",
    "has_changes",
    "get_git_config",
    "get_git_author_str",
    "parse_git_author",
    "check_git_lfs_installed",
    "clear_git_locks",
]
