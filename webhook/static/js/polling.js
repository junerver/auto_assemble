/**
 * 更新前端UI状态
 * @param {*} data
 */
function updateStatus(data) {
    try {
        // 更新当前运行任务
        const runningTaskDiv = document.getElementById('running-task');
        if (!runningTaskDiv) {
            console.error('找不到running-task元素');
            return;
        }

        if (data.running_task) {
            // 如果no-running-task元素不存在，我们需要创建它
            let noRunningTaskElement = document.getElementById('no-running-task');
            if (!noRunningTaskElement) {
                noRunningTaskElement = document.createElement('div');
                noRunningTaskElement.id = 'no-running-task';
                noRunningTaskElement.className = 'empty-state';
                noRunningTaskElement.innerHTML = '<i class="bi bi-check-circle"></i><p>暂无运行中的任务</p>';
                runningTaskDiv.appendChild(noRunningTaskElement);
            }

            noRunningTaskElement.style.display = 'none';
            // 创建任务元素
            const taskElement = document.createElement('div');
            taskElement.className = 'task-content';
            taskElement.innerHTML = createTaskItem(data.running_task, true);

            // 移除之前的任务内容（如果存在）
            const oldTaskContent = runningTaskDiv.querySelector('.task-content');
            if (oldTaskContent) {
                oldTaskContent.remove();
            }

            runningTaskDiv.appendChild(taskElement);
        } else {
            // 如果no-running-task元素不存在，我们需要创建它
            let noRunningTaskElement = document.getElementById('no-running-task');
            if (!noRunningTaskElement) {
                noRunningTaskElement = document.createElement('div');
                noRunningTaskElement.id = 'no-running-task';
                noRunningTaskElement.className = 'empty-state';
                noRunningTaskElement.innerHTML = '<i class="bi bi-check-circle"></i><p>暂无运行中的任务</p>';
                runningTaskDiv.appendChild(noRunningTaskElement);
            }

            noRunningTaskElement.style.display = 'block';
            // 移除任务内容（如果存在）
            const taskContent = runningTaskDiv.querySelector('.task-content');
            if (taskContent) {
                taskContent.remove();
            }
        }

        // 更新队列大小和等待中的任务
        const queueListDiv = document.getElementById('queue-list');
        if (!queueListDiv) {
            console.error('找不到queue-list元素');
            return;
        }

        // 更新队列大小
        const queueSizeElement = document.getElementById('queue-size');
        if (queueSizeElement) {
            queueSizeElement.textContent = data.queue_size || '0';
        }

        // 确保empty-queue元素存在
        let emptyQueueElement = document.getElementById('empty-queue');
        if (!emptyQueueElement) {
            emptyQueueElement = document.createElement('div');
            emptyQueueElement.id = 'empty-queue';
            emptyQueueElement.className = 'empty-state';
            emptyQueueElement.innerHTML = '<i class="bi bi-check-circle"></i><p>队列为空</p>';
            queueListDiv.appendChild(emptyQueueElement);
        }

        if (data.pending_tasks && data.pending_tasks.length > 0) {
            emptyQueueElement.style.display = 'none';
            // 创建任务列表元素
            const tasksElement = document.createElement('div');
            tasksElement.className = 'queue-tasks';
            // 确保等待中的任务按创建时间正序排列
            const sortedPendingTasks = [...data.pending_tasks].sort((a, b) => {
                return new Date(a.created_at) - new Date(b.created_at);
            });
            tasksElement.innerHTML = sortedPendingTasks.map(task => createTaskItem(task)).join('');

            // 移除之前的任务列表（如果存在）
            const oldTasksList = queueListDiv.querySelector('.queue-tasks');
            if (oldTasksList) {
                oldTasksList.remove();
            }

            queueListDiv.appendChild(tasksElement);
        } else {
            emptyQueueElement.style.display = 'block';
            // 移除任务列表（如果存在）
            const tasksList = queueListDiv.querySelector('.queue-tasks');
            if (tasksList) {
                tasksList.remove();
            }
        }

        // 更新最近任务
        const recentTasksDiv = document.getElementById('recent-tasks');
        if (!recentTasksDiv) {
            console.error('找不到recent-tasks元素');
            return;
        }

        // 确保no-recent-tasks元素存在
        let noRecentTasksElement = document.getElementById('no-recent-tasks');
        if (!noRecentTasksElement) {
            noRecentTasksElement = document.createElement('div');
            noRecentTasksElement.id = 'no-recent-tasks';
            noRecentTasksElement.className = 'empty-state';
            noRecentTasksElement.innerHTML = '<i class="bi bi-check-circle"></i><p>暂无最近任务</p>';
            recentTasksDiv.appendChild(noRecentTasksElement);
        }

        if (data.recent_tasks && data.recent_tasks.length > 0) {
            noRecentTasksElement.style.display = 'none';
            // 创建任务列表元素
            const tasksElement = document.createElement('div');
            tasksElement.className = 'recent-tasks-list';
            // 确保按completed_at倒序排列
            const sortedTasks = [...data.recent_tasks].sort((a, b) => {
                const dateA = new Date(a.completed_at || 0);
                const dateB = new Date(b.completed_at || 0);
                return dateB - dateA;
            });
            tasksElement.innerHTML = sortedTasks.map(task => createTaskItem(task)).join('');

            // 移除之前的任务列表（如果存在）
            const oldTasksList = recentTasksDiv.querySelector('.recent-tasks-list');
            if (oldTasksList) {
                oldTasksList.remove();
            }

            recentTasksDiv.appendChild(tasksElement);
        } else {
            noRecentTasksElement.style.display = 'block';
            // 移除任务列表（如果存在）
            const tasksList = recentTasksDiv.querySelector('.recent-tasks-list');
            if (tasksList) {
                tasksList.remove();
            }
        }
    } catch (error) {
        console.error('更新状态时发生错误:', error);
    }
}

/**
 * 更新队列状态
 */
function updateQueueStatus() {
    fetch('/queue?build_mode=' + currentBuildMode)
        .then(response => response.json())
        .then(data => updateStatus(data))
        .catch(error => console.error('Error:', error));
}

/**
 * 添加轮询间隔
 */
const POLL_INTERVAL = 5000; // 5秒
let pollTimer = null;

/**
 * 开始轮询
 */
function startPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
    }
    updateQueueStatus(); // 立即执行一次
    pollTimer = setInterval(updateQueueStatus, POLL_INTERVAL);
}

/**
 * 停止轮询
 */
function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

/**
 * 页面加载完成后开始轮询
 */
document.addEventListener('DOMContentLoaded', startPolling);

/**
 * 页面隐藏时停止轮询，显示时重新开始
 */
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopPolling();
    } else {
        startPolling();
    }
});