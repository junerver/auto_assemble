// 添加IP校验状态变量
let isAuthorizedIP = false;
// 权限列表
let permissions = [];
let role = "";

const isAdmin = () => {
    return role === "admin";
}

let permissionsConfig = {
    // 修改项目配置
    updateProjectConfigEnabled: false,
    // 删除项目配置
    deleteProjectConfigEnabled: false,
    // 重播任务
    replayTaskEnabled: false,
    showProjectDetailEnabled: false,
    stopTaskEnabled: false,
    forkTaskEnabled: false,
    deleteTaskEnabled: false,
}


// 分发仓库地址
const distributionUrl = "http://192.168.187.232:28088/rdcenter/app-distribution/"

// 初始化tooltip
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

// 检查IP授权状态
function checkIPAuthorization() {
    fetch('/check-ip')
        .then(response => response.json())
        .then(data => {
            isAuthorizedIP = data.authorized;
            permissions = data.permissions;
            role = data.role;
            permissionsConfig = {
                "showProjectDetailEnabled": data.permissions.includes("show_project_detail"),
                "updateProjectConfigEnabled": data.permissions.includes("update_project"),
                "deleteProjectConfigEnabled": data.permissions.includes("delete_project"),
                "replayTaskEnabled": data.permissions.includes("replay_task"),
                "stopTaskEnabled": data.permissions.includes("stop_task"),
                "forkTaskEnabled": data.permissions.includes("fork_task"),
                "deleteTaskEnabled": data.permissions.includes("delete_task"),
            }
            // 更新UI状态
            updateUIAuthorization();
        })
        .catch(error => {
            console.error('Error checking IP authorization:', error);
            isAuthorizedIP = false;
            updateUIAuthorization();
        });
}

// 更新UI授权状态
function updateUIAuthorization() {
    // 更新项目配置表单
    const formInputs = document.querySelectorAll('#projectConfigForm input, #projectConfigForm select');
    formInputs.forEach(input => {
        input.readOnly = !isAuthorizedIP;
        input.disabled = !isAuthorizedIP;
    });

    // 更新保存按钮
    const saveButton = document.getElementById('saveProjectConfig');
    if (saveButton) {
        saveButton.style.display = isAuthorizedIP ? 'block' : 'none';
    }

    // 更新添加第三方配置按钮
    const addConfigButton = document.querySelector('#projectConfigForm button[onclick="showAddThirdPartyConfig()"]');
    if (addConfigButton) {
        addConfigButton.style.display = isAuthorizedIP ? 'block' : 'none';
    }

    // 更新删除配置按钮
    const deleteButtons = document.querySelectorAll('#projectConfigForm button[onclick^="deleteThirdPartyConfig"]');
    deleteButtons.forEach(button => {
        button.style.display = isAuthorizedIP ? 'block' : 'none';
    });
}

// 在页面加载时检查IP授权
document.addEventListener('DOMContentLoaded', function () {
    checkIPAuthorization();
    // 应用保存的缩放设置
    applyZoom();
});

// 缩放控制相关函数，初始缩放 1.25
let currentZoom = parseFloat(localStorage.getItem('pageZoom')) || 1.25;

/**
 * 放大，极限为2
 */
function zoomIn() {
    if (currentZoom < 2.0) {
        currentZoom += 0.1;
        applyZoom();
    }
}

/**
 * 缩小，极限为0.5
 */
function zoomOut() {
    if (currentZoom > 0.5) {
        currentZoom -= 0.1;
        applyZoom();
    }
}

/**
 * 使用css中 style-zoom控制页面主体缩放
 */
function applyZoom() {
    document.body.style.zoom = currentZoom;
    document.getElementById('zoomLevel').textContent = `${Math.round(currentZoom * 100)}%`;
    localStorage.setItem('pageZoom', currentZoom);
}

/**
 * 格式化日期时间
 * @param {*} dateString 
 * @returns 
 */
function formatDateTime(dateString) {
    if (!dateString) return '未知';
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            return '未知';
        }
        // 使用 toLocaleString 时指定完整的配置，包括时区
        return date.toLocaleString('zh-CN', {
            timeZone: 'Asia/Shanghai',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    } catch (e) {
        return '未知';
    }
}

/**
 * 格式化构建耗时
 * @param {*} startTime 
 * @param {*} endTime 
 * @returns 
 */
function formatDuration(startTime, endTime) {
    if (!startTime || !endTime) return '未知';
    try {
        const start = new Date(startTime);
        const end = new Date(endTime);
        if (isNaN(start.getTime()) || isNaN(end.getTime())) {
            return '未知';
        }
        // 确保时间差计算正确，不受时区影响
        const duration = Math.floor((end.getTime() - start.getTime()) / 1000);
        const minutes = Math.floor(duration / 60);
        const seconds = duration % 60;
        return `${minutes}分${seconds}秒`;
    } catch (e) {
        return '未知';
    }
}

/**
 * 获取请求类型徽标
 * @param {*} commitTitle 
 * @returns 
 */
function getReqTypeBadge(commitTitle) {
    if (!commitTitle) return '';
    if (commitTitle.startsWith('#dev_req#')) {
        return '<span class="badge req-badge dev-req">dev</span>';
    } else if (commitTitle.startsWith('#test_req#')) {
        return '<span class="badge req-badge test-req">test</span>';
    } else if (commitTitle.startsWith('#release_req#')) {
        return '<span class="badge req-badge release-req">release</span>';
    }
    return '';
}

/**
 * 获取分支名称
 * @param {*} commitTitle 
 * @returns 
 */
function getBranchName(commitTitle) {
    if (!commitTitle) return 'master';
    if (commitTitle.startsWith('#dev_req#')) {
        return 'master';
    } else if (commitTitle.startsWith('#test_req#')) {
        return 'test';
    } else if (commitTitle.startsWith('#release_req#')) {
        return 'release';
    }
    return 'master';
}

/**
 * 格式化提交标题
 * @param {*} commitTitle 
 * @returns 
 */
function formatCommitTitle(commitTitle) {
    if (!commitTitle) return '无标题';
    return commitTitle.replace(/^#(dev|test|release)_req#\s*/, '');
}

/**
 * 格式化文件体积
 * @param {*} fileSize 
 * @returns 
 */
function formatFileSize(fileSize) {
    if (!fileSize) return '未知';
    const units = ['KB', 'MB', 'GB', 'TB'];
    let index = 0;
    while (fileSize >= 1024 && index < units.length - 1) {
        fileSize /= 1024;
        index++;
    }
    return `${fileSize.toFixed(2)} ${units[index]}`;
}

/**
 * 创建任务项
 * @param {*} task
 * @param {*} isRunning 是否创建的是运行中任务
 * @returns 
 */
function createTaskItem(task, isRunning = false) {
    // 运行时长
    const duration = isRunning ?
        formatDuration(task.started_at, new Date()) :
        formatDuration(task.started_at, task.completed_at);
    // 运行状态
    const statusBadge = isRunning ?
        '<span class="badge bg-info status-badge"><i class="bi bi-play-circle"></i> 运行中</span>' :
        `<span class="badge ${task.status === 'completed' ? 'bg-success' : 'bg-danger'} status-badge">
            <i class="bi ${task.status === 'completed' ? 'bi-check-circle' : 'bi-x-circle'}"></i> ${task.status === 'completed' ? '成功' : '失败'}
        </span>`;
    // 构建产物元数据状态，显示版本名、版本号、文件体积
    const releaseMetaDataStatus = task.metadata ?
        `<span class="badge text-bg-secondary">${task.metadata.version_name}</span>
        <span class="badge text-bg-secondary">${task.metadata.version_code}</span>
        <span class="badge text-bg-secondary">${formatFileSize(task.metadata.file_size)}</span>
        ` :
        ``;
    // 源任务id
    const source_task_id = task.source_task_id;
    // 是否完成
    const isCompleted = task.status === 'completed';
    // 目标url，如果有响应hash，则指向响应hash，否则指向分支
    const targetUrl = task.response_hash ? task.response_hash : getBranchName(task.commit_title);
    // 是否归一化
    const isNormalized = task.metadata.is_normalized;

    // 构建完成时间显示（仅对已完成的任务显示）
    const completedTimeInfo = isCompleted && task.completed_at ?
        `<p class="mb-1 time-info"><i class="bi bi-calendar-check"></i> 完成时间: ${formatDateTime(task.completed_at)}</p>` : '';

    // 为已完成的任务标题添加点击事件
    const taskClickHandler = !isRunning && task.status !== 'pending' ?
        `onclick="window.open('${distributionUrl}-/tree/${targetUrl}/${task.project}/${task.task}', '_blank')" style="cursor: pointer;"` : '';

    // 项目名称点击事件
    const projectClickHandler = permissionsConfig.showProjectDetailEnabled ? `onclick="showProjectConfig('${task.project}')" style="cursor: pointer;"` : '';

    //获取资源文件地址
    const rawUrl = (file) => `${distributionUrl}-/raw/${targetUrl}/${task.project}/${task.task}/${file}`
    // 打包请求说明
    const reqReadme = rawUrl("README.md")
    // 构建产物元数据
    const releaseMetaData = rawUrl("release-metadata.md")
    // 构建产物apk文件
    const apkFile = rawUrl(getBranchName(task.commit_title) == "master" ? `${task.task}_debug.apk` : `${task.task}.apk`)

    // 资源链接部分（仅对已完成的任务显示）
    const resourceLinks = isCompleted ? `
            <div class="resource-links">
                <a href="${reqReadme}" class="resource-link" target="_blank">
                    <i class="bi bi-file-text"></i>打包请求说明
                </a>
                <a href="${releaseMetaData}" class="resource-link" target="_blank">
                    <i class="bi bi-file-earmark-code"></i>产物元数据
                </a>
                <a href="${apkFile}" class="resource-link" target="_blank">
                    <i class="bi bi-download"></i>产物APK
                </a>
            </div>
        ` : '';

    return `
        <div class="task-item ${task.error ? 'warning' : ''}">
            <h6 class="task-title" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span ${projectClickHandler}>${task.project}</span> - <span ${taskClickHandler}>${task.task}</span>
                    ${source_task_id && isAuthorizedIP ? `<i class="bi bi-link-45deg" 
                    style="font-size: 1rem; color: DarkGray; cursor: pointer;" onclick="openSourceTask('${source_task_id}')" 
                    data-bs-toggle="tooltip" data-bs-custom-class="custom-tooltip" data-bs-title="${source_task_id}"></i>` : ''}
                    ${isNormalized && isAuthorizedIP ? `<i class="bi bi-wrench-adjustable-circle" style="font-size: 0.9rem; color: mediumaquamarine;"></i>` : ''}
                    ${isRunning && isAuthorizedIP && permissionsConfig.stopTaskEnabled ? `<button class="btn btn-sm btn-outline-danger ms-2 stop-btn" data-task-id="${task.id}">
                        <i class="bi bi-stop-circle"></i> 停止
                    </button>` : ''}
                    ${task.error && isAuthorizedIP && permissionsConfig.replayTaskEnabled ? `<button class="btn btn-sm btn-outline-danger ms-2 replay-btn" data-task-id="${task.id}">
                        <i class="bi bi-arrow-repeat"></i> 重播
                    </button>` : ''}
                </div>
                <div>
                    ${!isRunning && isAuthorizedIP && permissionsConfig.forkTaskEnabled ? `<i class="bi bi-arrow-repeat" style="font-size: 1.1rem; color: DarkGreen; cursor: pointer;" onclick="forkTask('${task.id}')"></i>` : ''}
                    ${!isRunning && isAuthorizedIP && permissionsConfig.deleteTaskEnabled ? `<i id="outdated-task" class="bi bi-trash3-fill" style="font-size: 1rem; color: IndianRed; cursor: pointer;" onclick="outdatedTask('${task.id}')"></i>` : ''}
                </div>
            </h6>
            <p class="mb-1"><i class="bi bi-person"></i> 提交人: ${task.author || '未知'}</p>
            <p class="mb-1"><i class="bi bi-chat-text"></i> 提交信息: ${getReqTypeBadge(task.commit_title)}${formatCommitTitle(task.commit_title)}</p>
            <p class="mb-1 time-info" id="time-info-${task.id}">
                <i class="bi bi-hourglass-split"></i> ${isRunning ? '已运行' : '构建耗时'}: ${duration}
            </p>
            ${completedTimeInfo}
            <p class="mb-1">状态: ${statusBadge} ${releaseMetaDataStatus}</p>
            ${task.error ? `<p class="mb-1 text-danger"><i class="bi bi-exclamation-triangle"></i> 错误: ${task.error}</p>` : ''}
            ${resourceLinks}
        </div>
    `;
}

/**
 * 派生任务
 * @param {*} taskId
 */
function forkTask(taskId) {
    console.log(taskId);
    fetch(`/task/${taskId}`)
        .then(response => response.json())
        .then(data => {
            const sourceTask = data.task;
            console.log(sourceTask);
            // 填充模态窗口
            document.getElementById('sourceTaskId').value = sourceTask.id;
            document.getElementById('sourceBranch').value = getBranchName(sourceTask.commit_title);
            document.getElementById('targetBranchSelect').value = getBranchName(sourceTask.commit_title);
            document.getElementById('versionName').value = sourceTask.metadata?.version_name || '';
            document.getElementById('versionCode').value = sourceTask.metadata?.version_code || '';
            document.getElementById('commitMessage').value = formatCommitTitle(sourceTask.commit_message).substring(0) || '';
            // 操作人，原始作者为sourceTask.author
            document.getElementById('operator').value = sourceTask.author || 'assemble_bot';
            document.getElementById('createForkTask').onclick = () => createForkTask();
            // 弹出模态窗口
            const modal = new bootstrap.Modal(document.getElementById('forkTaskModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error showing fork task:', error);
        });
}

/**
 * 根据模态窗口数据创建派生任务
 */
function createForkTask() {
    console.log('createForkTask');
    const sourceTaskId = document.getElementById('sourceTaskId').value;
    const sourceBranch = document.getElementById('sourceBranch').value;
    const targetBranch = document.getElementById('targetBranchSelect').value;
    const versionName = document.getElementById('versionName').value;
    const versionCode = document.getElementById('versionCode').value;
    const commitMessage = document.getElementById('commitMessage').value;
    const operator = document.getElementById('operator').value;
    console.log(sourceTaskId, sourceBranch, targetBranch, versionName, versionCode, commitMessage);
    fetch(`/api/fork_task`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            source_task_id: sourceTaskId,
            source_branch: sourceBranch,
            target_branch: targetBranch,
            target_version_name: versionName,
            target_version_code: versionCode,
            commit_message: commitMessage,
            operator: operator,
        }),
    })
        .then(response => response.json())
        .then(data => {
            const forkTask = data.fork_task;
            if (forkTask) {
                alert('派生任务创建成功，请稍等...');
                // 关闭模态窗口
                const modal = bootstrap.Modal.getInstance(document.getElementById('forkTaskModal'));
                modal.hide();
                // 刷新任务列表
                updateQueueStatus();
            }
        })
}

/**
 * 显示派生任务
 * @param {*} sourceTaskId
 */
function openSourceTask(sourceTaskId) {

    fetch(`/task/${sourceTaskId}`)
        .then(response => response.json())
        .then(data => {
            const sourceTask = data.task;
            const targetUrl = sourceTask.response_hash ? sourceTask.response_hash : getBranchName(sourceTask.commit_title);
            window.open(`${distributionUrl}-/tree/${targetUrl}/${sourceTask.project}/${sourceTask.task}`, '_blank');
        })
        .catch(error => {
            console.error('Error showing fork task:', error);
        });
}

/**
 * 标记任务为过期
 * @param {*} taskId
 */
function outdatedTask(taskId) {
    fetch(`/task/${taskId}`, {
        method: 'DELETE'
    })
        .then(updateQueueStatus)
}

