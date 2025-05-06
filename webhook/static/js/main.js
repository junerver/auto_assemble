// 添加IP校验状态变量
let isAuthorizedIP = false;

// 检查IP授权状态
function checkIPAuthorization() {
    fetch('/check-ip')
        .then(response => response.json())
        .then(data => {
            isAuthorizedIP = data.authorized;
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
    startPolling();
});

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
 * @param {*} isRunning 
 * @returns 
 */
function createTaskItem(task, isRunning = false) {
    // 分发仓库地址
    const distributionUrl = "http://192.168.187.232:28088/rdcenter/app-distribution/"
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


    // 构建完成时间显示（仅对已完成的任务显示）
    const completedTimeInfo = !isRunning && task.status !== 'pending' && task.completed_at ?
        `<p class="mb-1 time-info"><i class="bi bi-calendar-check"></i> 完成时间: ${formatDateTime(task.completed_at)}</p>` : '';

    // 为已完成的任务标题添加点击事件
    const taskClickHandler = !isRunning && task.status !== 'pending' ?
        `onclick="window.open('${distributionUrl}-/tree/${getBranchName(task.commit_title)}/${task.project}/${task.task}', '_blank')" style="cursor: pointer;"` : '';

    // 项目名称点击事件
    const projectClickHandler = `onclick="showProjectConfig('${task.project}')" style="cursor: pointer;"`;

    //获取资源文件地址
    const rawUrl = (file) => `${distributionUrl}-/raw/${getBranchName(task.commit_title)}/${task.project}/${task.task}/${file}`
    // 打包请求说明
    const reqReadme = rawUrl("README.md")
    // 构建产物元数据
    const releaseMetaData = rawUrl("release-metadata.md")
    // 构建产物apk文件
    const apkFile = rawUrl(getBranchName(task.commit_title) == "master" ? `${task.task}_debug.apk` : `${task.task}.apk`)

    // 资源链接部分（仅对已完成的任务显示）
    const resourceLinks = !isRunning && task.status === 'completed' ? `
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
                    ${isRunning ? `<button class="btn btn-sm btn-outline-danger ms-2 stop-btn" data-task-id="${task.id}">
                        <i class="bi bi-stop-circle"></i> 停止
                    </button>` : ''}
                    ${task.error ? `<button class="btn btn-sm btn-outline-danger ms-2 replay-btn" data-task-id="${task.id}">
                        <i class="bi bi-arrow-repeat"></i> 重播
                    </button>` : ''}
                </div>
                ${isAuthorizedIP ? `<i id="outdated-task" class="bi bi-trash3-fill" style="font-size: 1rem; color: IndianRed; cursor: pointer;" onclick="outdatedTask('${task.id}')"></i>` : ''}
            </h6>
            <p class="mb-1"><i class="bi bi-person"></i> 提交人: ${task.author || '未知'}</p>
            <p class="mb-1"><i class="bi bi-chat-text"></i> 提交信息: ${getReqTypeBadge(task.commit_title)}${formatCommitTitle(task.commit_title)}</p>
            <p class="mb-1 time-info"><i class="bi bi-clock"></i> ${isRunning ? '开始时间' : '提交时间'}: ${formatDateTime(isRunning ? task.started_at : task.created_at)}</p>
            <p class="mb-1 time-info"><i class="bi bi-hourglass-split"></i> ${isRunning ? '已运行' : '构建耗时'}: ${duration}</p>
            ${completedTimeInfo}
            <p class="mb-1">状态: ${statusBadge} ${releaseMetaDataStatus}</p>
            ${task.error ? `<p class="mb-1 text-danger"><i class="bi bi-exclamation-triangle"></i> 错误: ${task.error}</p>` : ''}
            ${resourceLinks}
        </div>
    `;
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

/**
 * 更新状态
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

/**
 * 显示项目配置
 * @param {*} projectName 
 */
function showProjectConfig(projectName) {
    // 获取项目配置
    fetch(`/api/config/project?name=${encodeURIComponent(projectName)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            // 填充表单数据
            const form = document.getElementById('projectConfigForm');
            form.querySelectorAll('input, select').forEach(input => {
                input.readOnly = !isAuthorizedIP;
                input.disabled = !isAuthorizedIP;
            });

            document.getElementById('projectUrl').value = data.project_config.project_url;
            document.getElementById('prodName').value = data.project_config.prod_name;
            document.getElementById('hbxVersion').value = data.project_config.hbx_version;
            document.getElementById('uniappId').value = data.project_config.uniapp_id;
            document.getElementById('uniappAppkey').value = data.project_config.uniapp_appkey;
            document.getElementById('uniappIsCli').checked = data.project_config.uniapp_is_cli;
            form.dataset.projectId = data.project_config.id;

            // 填充第三方配置
            const thirdPartyConfigsDiv = document.getElementById('thirdPartyConfigs');
            thirdPartyConfigsDiv.innerHTML = data.third_party_configs.map(config => `
                <div class="mb-2">
                    <div class="d-flex align-items-center">
                        <div class="flex-grow-1">
                            <label class="form-label">${config.provider} - ${config.description}</label>
                            <input type="text" class="form-control" name="third_party_configs" 
                                   data-key="${config.dict_key}" value="${config.config_value}"
                                   ${!isAuthorizedIP ? 'readonly disabled' : ''}>
                        </div>
                        <button type="button" class="btn btn-sm btn-danger ms-2" 
                                style="height: fit-content; margin-top: 28px; ${!isAuthorizedIP ? 'display: none;' : ''}"
                                onclick="deleteThirdPartyConfig('${config.dict_key}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');

            // 显示模态窗口
            const modal = new bootstrap.Modal(document.getElementById('projectConfigModal'));
            modal.show();

            // 更新保存按钮显示状态
            const saveButton = document.getElementById('saveProjectConfig');
            if (saveButton) {
                saveButton.style.display = isAuthorizedIP ? 'block' : 'none';
                saveButton.onclick = function () {
                    saveProjectConfig(data.project_config.id);
                };
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('获取项目配置失败' + error);
        });
}

/**
 * 保存项目配置
 * @param {*} projectId 
 */
function saveProjectConfig(projectId) {
    const formData = {
        project_url: document.getElementById('projectUrl').value,
        prod_name: document.getElementById('prodName').value,
        hbx_version: document.getElementById('hbxVersion').value,
        uniapp_id: document.getElementById('uniappId').value,
        uniapp_appkey: document.getElementById('uniappAppkey').value,
        uniapp_is_cli: document.getElementById('uniappIsCli').checked,
        third_party_configs: Array.from(document.querySelectorAll('input[name="third_party_configs"]')).map(input => ({
            key: input.dataset.key,
            value: input.value
        }))
    };

    fetch(`/api/config/project/${projectId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert('配置保存成功');
                bootstrap.Modal.getInstance(document.getElementById('projectConfigModal')).hide();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('保存配置失败');
        });
}

/**
 * 显示添加第三方配置模态窗口
 */
function showAddThirdPartyConfig() {
    const projectId = document.getElementById('projectConfigForm').dataset.projectId;
    if (!projectId) {
        alert('无法获取项目ID');
        return;
    }

    fetch(`/api/config/third-party/dict/unconfigured?project_id=${projectId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            if (data.items.length === 0) {
                alert('没有可添加的配置项');
                return;
            }

            const modal = new bootstrap.Modal(document.getElementById('addThirdPartyConfigModal'));
            const form = document.getElementById('addThirdPartyConfigForm');
            form.innerHTML = '';

            // 创建选择框
            const selectDiv = document.createElement('div');
            selectDiv.className = 'mb-3';
            selectDiv.innerHTML = `
                <label class="form-label">选择配置项</label>
                <select class="form-select" id="dictItemSelect">
                    ${data.items.map(item => `
                        <option value="${item.key}" data-provider="${item.provider}" 
                                data-description="${item.description}">
                            ${item.provider} - ${item.description}
                        </option>
                    `).join('')}
                </select>
            `;
            form.appendChild(selectDiv);

            // 创建配置值输入框
            const valueDiv = document.createElement('div');
            valueDiv.className = 'mb-3';
            valueDiv.innerHTML = `
                <label class="form-label">配置值</label>
                <input type="text" class="form-control" id="configValue" required>
            `;
            form.appendChild(valueDiv);

            // 更新保存按钮事件
            document.getElementById('saveThirdPartyConfig').onclick = function () {
                const select = document.getElementById('dictItemSelect');
                const selectedOption = select.options[select.selectedIndex];
                const configValue = document.getElementById('configValue').value;

                if (!configValue) {
                    alert('请输入配置值');
                    return;
                }

                const newConfig = {
                    key: selectedOption.value,
                    value: configValue
                };

                // 获取当前所有配置
                const currentConfigs = Array.from(document.querySelectorAll('input[name="third_party_configs"]')).map(input => ({
                    key: input.dataset.key,
                    value: input.value
                }));

                // 添加新配置
                currentConfigs.push(newConfig);

                // 更新表单数据
                const projectConfigForm = document.getElementById('projectConfigForm');
                const projectId = projectConfigForm.dataset.projectId;
                const updateData = {
                    project_url: document.getElementById('projectUrl').value,
                    prod_name: document.getElementById('prodName').value,
                    hbx_version: document.getElementById('hbxVersion').value,
                    uniapp_id: document.getElementById('uniappId').value,
                    uniapp_appkey: document.getElementById('uniappAppkey').value,
                    uniapp_is_cli: document.getElementById('uniappIsCli').checked,
                    third_party_configs: currentConfigs
                };

                fetch(`/api/config/project/${projectId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData)
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            alert(data.error);
                        } else {
                            alert('配置添加成功');
                            bootstrap.Modal.getInstance(document.getElementById('addThirdPartyConfigModal')).hide();
                            // 重新加载项目配置
                            const projectName = document.getElementById('prodName').value;
                            if (projectName) {
                                showProjectConfig(projectName);
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('添加配置失败');
                    });
            };

            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('获取未配置项失败');
        });
}

/**
 * 添加标题点击计数器
 */
let titleClickCount = 0;

/**
 * 监听页面标题点击事件，如果点击次数达到3次，则显示项目列表
 */
document.getElementById('pageTitle').addEventListener('click', function () {
    if (isAuthorizedIP) {
        titleClickCount++;
        if (titleClickCount >= 3) {
            showProjects();
            titleClickCount = 0;
        }
    }
});

/**
 * 显示项目列表
 */
function showProjects() {
    fetch('/api/config/projects')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            const tbody = document.getElementById('projectsTableBody');
            tbody.innerHTML = data.projects.map(project => `
                <tr>
                    <td class="col-prod-name">${project.prod_name}</td>
                    <td class="col-url">
                        <div class="truncate-url" data-tooltip="${project.project_url}">
                            <span class="copy-content" data-clipboard-text="${project.project_url}">${project.project_url}</span>
                            <i class="bi bi-clipboard copy-icon" data-clipboard-text="${project.project_url}"></i>
                        </div>
                    </td>
                    <td class="col-hbx">${project.hbx_version || ''}</td>
                    <td class="col-uniapp-id">
                        <div class="truncate-url" data-tooltip="${project.uniapp_id || ''}">
                            <span class="copy-content" data-clipboard-text="${project.uniapp_id || ''}">${project.uniapp_id || ''}</span>
                            <i class="bi bi-clipboard copy-icon" data-clipboard-text="${project.uniapp_id || ''}"></i>
                        </div>
                    </td>
                    <td class="col-uniapp-key">
                        <div class="truncate-url" data-tooltip="${project.uniapp_appkey || ''}">
                            <span class="copy-content" data-clipboard-text="${project.uniapp_appkey || ''}">${project.uniapp_appkey || ''}</span>
                            <i class="bi bi-clipboard copy-icon" data-clipboard-text="${project.uniapp_appkey || ''}"></i>
                        </div>
                    </td>
                    <td class="col-cli text-center">${project.uniapp_is_cli ? '是' : '否'}</td>
                    <td class="col-actions text-center">
                        <button type="button" class="btn btn-sm btn-primary" onclick="showProjectConfig('${project.prod_name}')">
                            <i class="bi bi-pencil"></i>
                        </button>
                    </td>
                </tr>
            `).join('');

            const modal = new bootstrap.Modal(document.getElementById('projectsModal'));
            modal.show();

            // 初始化工具提示
            initTooltips();
            // 初始化剪贴板
            initClipboard();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('获取项目列表失败');
        });
}

/**
 * 工具提示初始化函数
 */
function initTooltips() {
    let tooltipTimeout;
    let activeTooltip = null;

    document.querySelectorAll('[data-tooltip]').forEach(element => {
        element.addEventListener('mouseenter', e => {
            // 清除之前的定时器
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }

            // 移除之前的工具提示
            if (activeTooltip) {
                activeTooltip.remove();
            }

            tooltipTimeout = setTimeout(() => {
                const tooltip = document.createElement('div');
                tooltip.className = 'tooltip';
                tooltip.textContent = e.target.getAttribute('data-tooltip');
                document.body.appendChild(tooltip);
                activeTooltip = tooltip;

                // 计算位置
                const rect = e.target.getBoundingClientRect();
                const tooltipRect = tooltip.getBoundingClientRect();

                // 计算最佳位置
                let top = rect.bottom + 5;
                let left = rect.left;

                // 检查是否会超出右边界
                if (left + tooltipRect.width > window.innerWidth) {
                    left = window.innerWidth - tooltipRect.width - 10;
                }

                // 检查是否会超出底部边界
                if (top + tooltipRect.height > window.innerHeight) {
                    // 如果超出底部，就显示在元素上方
                    top = rect.top - tooltipRect.height - 5;
                }

                // 确保不会超出左边界
                left = Math.max(10, left);

                tooltip.style.left = left + 'px';
                tooltip.style.top = top + 'px';

                // 显示工具提示
                requestAnimationFrame(() => {
                    tooltip.classList.add('show');
                });
            }, 500); // 500ms延迟显示
        });

        element.addEventListener('mouseleave', () => {
            // 清除显示定时器
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }

            // 移除工具提示
            if (activeTooltip) {
                activeTooltip.classList.remove('show');
                setTimeout(() => {
                    if (activeTooltip) {
                        activeTooltip.remove();
                        activeTooltip = null;
                    }
                }, 300);
            }
        });
    });
}

/**
 * 初始化剪贴板功能
 */
function initClipboard() {
    // 销毁之前的实例（如果存在）
    if (window.clipboard) {
        window.clipboard.destroy();
    }

    // 初始化新的剪贴板实例
    window.clipboard = new ClipboardJS('.copy-content, .copy-icon');

    // 复制成功事件
    window.clipboard.on('success', function (e) {
        console.log("实际复制的文本:", e.text);  // 确认这里是否有值
        e.clearSelection();
        showCopySuccess();
    });

    // 复制失败事件
    window.clipboard.on('error', function (e) {
        console.error('复制失败:', e);
        // 使用备用复制方法
        fallbackCopy(e.trigger.getAttribute('data-clipboard-text'));
    });

    // 为所有可复制元素添加点击事件
    document.querySelectorAll('.copy-content, .copy-icon').forEach(element => {
        element.addEventListener('click', function (e) {
            console.log("手动添加的点击事件");

            // e.stopPropagation();
            // e.preventDefault();
        });
    });
}

/**
 * 备用复制方法
 * @param {*} text 
 */
function fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    textarea.style.top = '0';
    document.body.appendChild(textarea);

    try {
        textarea.select();
        document.execCommand('copy');
        showCopySuccess();
    } catch (err) {
        console.error('复制失败:', err);
        alert('复制失败，请手动复制');
    } finally {
        document.body.removeChild(textarea);
    }
}

/**
 * 显示复制成功提示
 */
function showCopySuccess() {
    const notification = document.createElement('div');
    notification.className = 'copy-success';
    notification.textContent = '复制成功！';
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 2000);
}

/**
 * 显示新增项目模态窗口
 */
function showAddProject() {
    const modal = new bootstrap.Modal(document.getElementById('addProjectModal'));
    modal.show();
}

/**
 * 保存新项目
 */
function saveNewProject() {
    const formData = {
        project_url: document.getElementById('newProjectUrl').value,
        prod_name: document.getElementById('newProdName').value,
        hbx_version: document.getElementById('newHbxVersion').value,
        uniapp_id: document.getElementById('newUniappId').value,
        uniapp_appkey: document.getElementById('newUniappAppkey').value,
        uniapp_is_cli: document.getElementById('newUniappIsCli').checked,
        third_party_configs: []
    };

    fetch('/api/config/project', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert('项目添加成功');
                bootstrap.Modal.getInstance(document.getElementById('addProjectModal')).hide();
                // 重新加载项目列表
                showProjects();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('添加项目失败');
        });
}

/**
 * 添加保存新项目按钮的点击事件
 */
document.getElementById('saveNewProject').onclick = saveNewProject;


