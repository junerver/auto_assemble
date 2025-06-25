
/**
 * 显示第三方字典维护
 */
function showThirdPartyDict() {
    fetch('/api/config/third-party/dict')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            const tbody = document.getElementById('dictTableBody');
            tbody.innerHTML = data.items.map(item => `
            <tr>
                <td>${item.provider}</td>
                <td>${item.key}</td>
                <td>${item.value}</td>
                <td>${item.description}</td>
                <td>
                    <button type="button" class="btn btn-sm btn-primary me-1" onclick="editDictItem('${item.key}')">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-danger" onclick="deleteDictItem('${item.key}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');

            const modal = new bootstrap.Modal(document.getElementById('thirdPartyDictModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('获取字典列表失败');
        });
}

/**
 * 显示添加字典项
 */
function showAddDictItem() {
    document.getElementById('dictItemModalLabel').textContent = '添加字典项';
    document.getElementById('dictItemForm').reset();
    document.getElementById('saveDictItem').onclick = saveDictItem;
    const modal = new bootstrap.Modal(document.getElementById('dictItemModal'));
    modal.show();
}

/**
 * 显示编辑字典项
 * @param {*} key 
 */
function editDictItem(key) {
    fetch(`/api/config/third-party/dict/${key}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            document.getElementById('dictItemModalLabel').textContent = '编辑字典项';
            document.getElementById('dictProvider').value = data.provider;
            document.getElementById('dictKey').value = data.key;
            document.getElementById('dictValue').value = data.value;
            document.getElementById('dictDescription').value = data.description;
            document.getElementById('saveDictItem').onclick = () => updateDictItem(key);
            const modal = new bootstrap.Modal(document.getElementById('dictItemModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('获取字典项失败');
        });
}

/**
 * 保存字典项
 */
function saveDictItem() {
    const formData = {
        provider: document.getElementById('dictProvider').value,
        dict_key: document.getElementById('dictKey').value,
        dict_value: document.getElementById('dictValue').value,
        description: document.getElementById('dictDescription').value
    };

    fetch('/api/config/third-party/dict', {
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
                alert('字典项添加成功');
                bootstrap.Modal.getInstance(document.getElementById('dictItemModal')).hide();
                showThirdPartyDict();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('添加字典项失败');
        });
}

/**
 * 更新字典项
 * @param {*} key 
 */
function updateDictItem(key) {
    const formData = {
        provider: document.getElementById('dictProvider').value,
        dict_key: document.getElementById('dictKey').value,
        dict_value: document.getElementById('dictValue').value,
        description: document.getElementById('dictDescription').value
    };

    fetch(`/api/config/third-party/dict/${key}`, {
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
                alert('字典项更新成功');
                bootstrap.Modal.getInstance(document.getElementById('dictItemModal')).hide();
                showThirdPartyDict();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('更新字典项失败');
        });
}

/**
 * 删除字典项
 * @param {*} key 
 */
function deleteDictItem(key) {
    if (!confirm('确定要删除这个字典项吗？')) {
        return;
    }

    fetch(`/api/config/third-party/dict/${key}/delete`, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert('字典项删除成功');
                showThirdPartyDict();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('删除字典项失败');
        });
}

/**
 * 删除第三方配置项
 * @param {*} key 
 */
function deleteThirdPartyConfig(key) {
    if (!confirm('确定要删除这个配置项吗？')) {
        return;
    }

    const projectId = document.getElementById('projectConfigForm').dataset.projectId;
    if (!projectId) {
        alert('无法获取项目ID');
        return;
    }

    // 获取当前所有配置
    const currentConfigs = Array.from(document.querySelectorAll('input[name="third_party_configs"]'))
        .map(input => ({
            key: input.dataset.key,
            value: input.value
        }))
        .filter(config => config.key !== key); // 移除要删除的配置项

    // 更新项目配置
    const updateData = {
        project_url: document.getElementById('projectUrl').value,
        prod_name: document.getElementById('prodName').value,
        hbx_version: document.getElementById('hbxVersion').value,
        uniapp_id: document.getElementById('uniappId').value,
        uniapp_appkey: document.getElementById('uniappAppkey').value,
        uniapp_is_cli: document.getElementById('uniappIsCli').checked,
        third_party_configs: currentConfigs
    };

    fetch(`/api/config/project/${projectId}/update`, {
        method: 'POST',
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
                alert('配置项删除成功');
                // 重新加载项目配置
                const projectName = document.getElementById('prodName').value;
                if (projectName) {
                    showProjectConfig(projectName);
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('删除配置项失败');
        });
}
