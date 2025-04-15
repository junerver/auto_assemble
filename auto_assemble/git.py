import logging
import os
import subprocess
import textwrap
from collections import namedtuple

from auto_assemble.config import config

GitCommitInfo = namedtuple("GitCommitInfo", ["commit_date", "author", "message", "commit_hash"])


def get_git_info(repo_path: str) -> GitCommitInfo | None:
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
                commit_date=commit_date, author=author, message=message, commit_hash=commit_hash
            )
        else:
            logging.error(f"获取Git信息失败: {last_commit.stderr}")
    except Exception as e:
        logging.error(f"获取Git信息失败: {e}")
    return None


def git_fetch(repo_path: str) -> bool:
    """
    执行git fetch操作, 检查远程是否有更新, 如果本地代码已是最新, 则返回False, 否则返回True
    Args:
        repo_path: Git仓库路径
    Returns:
        bool: 是否需要拉取更新
    """
    try:
        # 检查远程是否有更新
        fetch_result = subprocess.run(
            ["git", "fetch"], capture_output=True, text=True, encoding="utf-8", cwd=repo_path
        )
        if fetch_result.returncode != 0:
            logging.error(f"Git fetch失败: {fetch_result.stderr}")
            return False

        # 检查是否需要更新
        status = subprocess.run(
            ["git", "status", "-uno"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=repo_path,
        )
        if "Your branch is up to date" in status.stdout:
            logging.info("本地代码已是最新版本，无需更新")
            return False
        else:
            logging.info("本地代码有更新，需要更新")
            return True
    except Exception as e:
        logging.error(f"Git fetch执行失败: {e}")
        return False


def sync_repository(repo_path: str) -> bool:
    """
    同步Git仓库到最新状态
    Args:
        repo_path: Git仓库路径
    Returns:
        bool: 同步是否成功
    """
    try:
        os.chdir(repo_path)

        # 获取更新前的提交信息
        before_commit_info = get_git_info(repo_path)
        if before_commit_info:
            logging.info(
                f"当前版本 - 提交时间: {before_commit_info.commit_date}, 提交人: {before_commit_info.author}, 提交信息: {before_commit_info.message}"
            )
            config.last_commit_message = textwrap.dedent(
                f"""
                
                提交时间: {before_commit_info.commit_date}
                提交人: {before_commit_info.author}
                提交信息: {before_commit_info.message}
                提交哈希: {before_commit_info.commit_hash}
                """
            )

        # 检查远程是否有更新
        if not git_fetch(repo_path):
            # 不需要拉取更新说明本地已经是最新
            return True

        # 执行更新
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            # 获取更新后的提交信息
            after_commit_info = get_git_info(repo_path)
            if after_commit_info:
                logging.info(f"更新成功 - 新版本信息:")
                logging.info(f"提交时间: {after_commit_info.commit_date}")
                logging.info(f"提交人: {after_commit_info.author}")
                logging.info(f"提交信息: {after_commit_info.message}")
                logging.info(f"提交哈希: {after_commit_info.commit_hash}")

            config.last_commit_message = textwrap.dedent(
                f"""
                
                提交时间: {after_commit_info.commit_date}
                提交人: {after_commit_info.author}
                提交信息: {after_commit_info.message}
                提交哈希: {after_commit_info.commit_hash}
                """
            )
            return True
        else:
            logging.error(f"Git仓库同步失败: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Git命令执行失败: {e}")
        return False
    except Exception as e:
        logging.error(f"同步仓库时发生错误: {e}")
        return False


def check_git_branch(repo_path: str, target_branch: str = None) -> bool:
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
    Returns:
        bool: 是否在目标分支或可以安全切换到目标分支
    """
    try:
        logging.info(f"开始检查Git分支: {repo_path}/{target_branch}")

        # 1. 获取远程更新
        fetch_proc = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=repo_path,
            timeout=30,
        )
        if fetch_proc.returncode != 0:
            logging.error(f"获取远程更新失败: {fetch_proc.stderr}")
            return False

        # 2. 检查当前分支与远程分支的差异
        diff_proc = subprocess.run(
            ["git", "diff", "HEAD", "origin/HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=repo_path,
            timeout=30,
        )
        if diff_proc.returncode != 0:
            logging.error(f"检查分支差异失败: {diff_proc.stderr}")
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
                timeout=30,
            )
            if status_proc.returncode != 0:
                logging.error(f"检查工作区状态失败: {status_proc.stderr}")
                return False

            if status_proc.stdout.strip():
                logging.error(
                    f"{repo_path}存在未提交的更改，无法安全拉取远程更新\n{status_proc.stdout}"
                )
                return False

            # 尝试拉取更新
            pull_proc = subprocess.run(
                ["git", "pull", "origin"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=30,
            )
            if pull_proc.returncode != 0:
                logging.error(f"拉取远程更新失败: {pull_proc.stderr}")
                return False

            logging.info("成功拉取远程更新")

        # 4. 获取当前分支
        current_branch_proc = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=repo_path,
            timeout=30,
        )
        if current_branch_proc.returncode != 0:
            logging.error(f"获取当前分支失败: {current_branch_proc.stderr}")
            return False

        current_branch = current_branch_proc.stdout.strip()
        original_branch = current_branch  # 保存原始分支状态
        logging.info(f"当前分支: {current_branch}")

        # 5. 如果已经在目标分支，直接返回True
        if not target_branch:
            # 如果未指定目标分支，则使用config.PROD_BRANCH
            if current_branch == config.PROD_BRANCH:
                logging.info(f"已在目标分支 {config.PROD_BRANCH} 上")
                return True
            target_branch = config.PROD_BRANCH
        else:
            # 如果指定目标分支，则检查是否在目标分支上
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
            timeout=30,
        )
        if status_proc.returncode != 0:
            logging.error(f"检查工作区状态失败: {status_proc.stderr}")
            return False

        if status_proc.stdout.strip():
            logging.error("存在未提交的更改，无法安全切换分支")
            return False

        try:
            # 7. 检查分支是否存在（包括本地和远程）
            branches_proc = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=30,
            )
            if branches_proc.returncode != 0:
                logging.error(f"获取分支列表失败: {branches_proc.stderr}")
                return False

            # 更精确的分支匹配
            branches = [
                branch.strip() for branch in branches_proc.stdout.split("\n") if branch.strip()
            ]
            local_branch_exists = any(
                branch.replace("*", "").strip() == target_branch for branch in branches
            )
            remote_branch_exists = any(
                branch.strip() == f"remotes/origin/{target_branch}" for branch in branches
            )

            if local_branch_exists:
                # 8. 如果本地分支存在，直接切换
                switch_proc = subprocess.run(
                    ["git", "checkout", target_branch],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=repo_path,
                    timeout=30,
                )
                if switch_proc.returncode != 0:
                    logging.error(f"切换到目标分支失败: {switch_proc.stderr}")
                    return False

                logging.info(f"成功切换到目标分支: {target_branch}")
                return True
            elif remote_branch_exists:
                # 9. 如果远程分支存在，从远程分支创建本地分支
                logging.info(f"从远程分支创建本地分支: {target_branch}")
                create_branch_proc = subprocess.run(
                    ["git", "checkout", "-b", target_branch, f"origin/{target_branch}"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=repo_path,
                    timeout=30,
                )
                if create_branch_proc.returncode != 0:
                    logging.error(f"从远程分支创建本地分支失败: {create_branch_proc.stderr}")
                    return False

                logging.info(f"成功创建并切换到新分支: {target_branch}")
                return True
            else:
                # 10. 如果本地和远程都不存在，从master创建新分支
                logging.info(f"目标分支不存在，准备从master创建新分支")

                # 先切换到master分支
                switch_master_proc = subprocess.run(
                    ["git", "checkout", "master"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=repo_path,
                    timeout=30,
                )
                if switch_master_proc.returncode != 0:
                    logging.error(f"切换到master分支失败: {switch_master_proc.stderr}")
                    return False

                logging.info("成功切换到master分支")

                # 从master创建新分支
                create_branch_proc = subprocess.run(
                    ["git", "checkout", "-b", target_branch],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=repo_path,
                    timeout=30,
                )
                if create_branch_proc.returncode != 0:
                    logging.error(f"从master创建新分支失败: {create_branch_proc.stderr}")
                    return False

                logging.info(f"成功创建并切换到新分支: {target_branch}")
                return True

        except subprocess.TimeoutExpired as e:
            logging.error(f"Git命令执行超时: {e}")
            # 尝试切回原分支
            subprocess.run(
                ["git", "checkout", original_branch],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=30,
            )
            return False
        except Exception as e:
            logging.error(f"分支操作过程中发生错误: {e}")
            # 尝试切回原分支
            subprocess.run(
                ["git", "checkout", original_branch],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=repo_path,
                timeout=30,
            )
            return False

    except Exception as e:
        logging.error(f"检查Git分支时发生错误: {e}")
        return False


def get_untracked_files(repo_path: str):
    """获取未跟踪的文件列表"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        if result.returncode != 0:
            logging.error("获取git状态失败")
            return []

        files = []
        for line in result.stdout.splitlines():
            if line.startswith("??"):  # 未跟踪的文件
                files.append(line[3:])
                logging.info(f"     -{line[3:]}")
        return files
    except Exception as e:
        logging.error(f"获取未跟踪文件时发生错误: {str(e)}")
        return []


def get_staged_files(repo_path: str):
    """获取已暂存的文件列表"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        if result.returncode != 0:
            logging.error("获取暂存文件列表失败")
            return []

        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception as e:
        logging.error(f"获取暂存文件列表时发生错误: {str(e)}")
        return []


def git_add(repo_path: str):
    """执行git add操作"""
    try:
        result = subprocess.run(["git", "add", "."], capture_output=True, text=True, cwd=repo_path)
        if result.returncode != 0:
            logging.error(f"git add 执行失败: {result.stderr}")
            return False
        logging.info("git add 执行成功")
        return True
    except Exception as e:
        logging.error(f"git add 执行时发生错误: {str(e)}")
        return False


def git_commit(commit_message, repo_path):
    """
    执行git commit操作，默认工作目录为config.DISTRIBUTION_PATH

    parameters:
    - commit_message: 提交信息
    - cwd: 当前工作目录
    return:
    - True: 执行成功
    - False: 执行失败
    """
    try:
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        if result.returncode != 0:
            logging.error(f"git commit 执行失败: {result.stderr}")
            return False
        logging.info(f"git commit 执行成功，提交信息: {commit_message}")
        return True
    except Exception as e:
        logging.error(f"git commit 执行时发生错误: {str(e)}")
        return False


def git_push(repo_path: str):
    """
    执行git push操作
    当远程分支领先于本地分支时,自动执行rebase操作
    """
    try:
        # 首先尝试push
        result = subprocess.run(
            ["git", "push"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )

        if result.returncode == 0:
            logging.info("git push 执行成功")
            return True

        # 检查是否是因为远程分支领先导致的失败
        if "git pull" in result.stderr or "rejected" in result.stderr:
            logging.info("检测到远程分支领先,尝试执行rebase操作")

            # 获取当前分支名
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            if branch_result.returncode != 0:
                logging.error(f"获取当前分支名失败: {branch_result.stderr}")
                return False

            current_branch = branch_result.stdout.strip()

            # 执行fetch
            fetch_result = subprocess.run(
                ["git", "fetch", "origin", current_branch],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            if fetch_result.returncode != 0:
                logging.error(f"git fetch 失败: {fetch_result.stderr}")
                return False

            # 执行rebase
            rebase_result = subprocess.run(
                ["git", "rebase", f"origin/{current_branch}"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            if rebase_result.returncode != 0:
                logging.error(f"git rebase 失败,可能存在冲突: {rebase_result.stderr}")
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
                logging.error(f"rebase后push仍然失败: {push_result.stderr}")
                return False

            logging.info("rebase并push成功")
            return True
        else:
            logging.error(f"git push 执行失败: {result.stderr}")
            return False

    except Exception as e:
        logging.error(f"git push 执行时发生错误: {str(e)}")
        return False
