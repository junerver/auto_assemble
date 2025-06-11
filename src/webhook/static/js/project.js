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
                input.readOnly = !isAuthorizedIP || !permissionsConfig.updateProjectConfigEnabled;
                input.disabled = !isAuthorizedIP || !permissionsConfig.updateProjectConfigEnabled;
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
                                   ${isAuthorizedIP && permissionsConfig.updateProjectConfigEnabled ? '' : 'readonly disabled'}>
                        </div>
                        <button type="button" class="btn btn-sm btn-danger ms-2" 
                                style="height: fit-content; margin-top: 28px; ${isAuthorizedIP && permissionsConfig.updateProjectConfigEnabled ? 'display: block;' : 'display: none;'}"
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
                saveButton.style.display = (isAuthorizedIP && permissionsConfig.updateProjectConfigEnabled) ? 'block' : 'none';
                saveButton.onclick = function () {
                    saveProjectConfig(data.project_config.id);
                };
            }
            const addThirdPartyConfigBtn = document.getElementById('addThirdPartyConfigBtn');
            if (addThirdPartyConfigBtn) {
                addThirdPartyConfigBtn.style.display = (isAuthorizedIP && permissionsConfig.updateProjectConfigEnabled) ? 'block' : 'none';
                addThirdPartyConfigBtn.onclick = function () {
                    showAddThirdPartyConfig();
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
    // 管理员可以随时查看项目列表
    if (isAuthorizedIP && isAdmin()) {
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
    fetch('/api/config/project/list')
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


function showProjectSignConfig() {
    // 从form中获取项目ID（该数据在form显示时被灌入）
    const projectId = document.getElementById('projectConfigForm').dataset.projectId;
    fetch(`/api/config/project/${projectId}/sign`)
        .then(response => response.json())
        .then(data => {
            const modal = new bootstrap.Modal(document.getElementById('signatureModal'));
            const form = document.getElementById('signatureForm');
            const signFile = document.getElementById('signFile');
            const keyStoreDiv = document.getElementById('keyStoreDiv');
            const keyStorePath = document.getElementById('keyStorePath');
            const ksPass = document.getElementById('ksPass');
            const keyAlias = document.getElementById('keyAlias');
            const keyPass = document.getElementById('keyPass');
            document.getElementById('saveSignature').onclick = function () {
                updateProjectSignConfig(projectId, {
                    ks_pass: ksPass.value,
                    key_alias: keyAlias.value,
                    key_pass: keyPass.value
                }, signFile.files[0]).then(data => {
                    alert('签名配置保存成功');
                    bootstrap.Modal.getInstance(document.getElementById('signatureModal')).hide();
                })
            }
            if (data.signConfig) {
                ksPass.value = data.signConfig.ks_pass;
                keyAlias.value = data.signConfig.key_alias;
                keyPass.value = data.signConfig.key_pass;
                // 显示签名配置的路径
                keyStoreDiv.style.display = 'block';
                keyStorePath.value = data.signConfig.key_store;
            } else {
                keyStoreDiv.style.display = 'none';
            }
            modal.show();
        });
}

async function updateProjectSignConfig(projectId, signConfig, file) {
    try {
        // 创建 FormData 对象
        const formData = new FormData();
        // 单独添加 sign_config 的字段
        formData.append('key_store', file);
        formData.append('ks_pass', signConfig.ks_pass);
        formData.append('key_alias', signConfig.key_alias);
        formData.append('key_pass', signConfig.key_pass);

        // 发送 PUT 请求
        const response = await fetch(`/api/config/project/${projectId}/sign`, {
            method: 'PUT',
            body: formData,
        });

        // 检查响应
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '请求失败');
        }

        // 处理成功响应
        const data = await response.json();
        console.log('成功:', data.message, data.file_path);
        return data;
    } catch (error) {
        console.error('错误:', error.message);
        throw error;
    }
}