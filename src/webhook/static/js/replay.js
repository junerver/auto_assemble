/**
 * 添加重播功能
 */
document.addEventListener('click', function (e) {
    if (e.target.closest('.replay-btn')) {
        const taskId = e.target.closest('.replay-btn').getAttribute('data-task-id');
        if (!taskId) return;

        if (!confirm('确定要重播这个任务吗？')) {
            return;
        }

        fetch(`/task/${taskId}/replay`, {
            method: 'POST'
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    alert('任务重播成功');
                    updateQueueStatus(); // 刷新状态
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('重播任务失败');
            });
    }
});

/**
 * 添加停止按钮点击事件处理
 */
document.addEventListener('click', function (event) {
    if (event.target.closest('.stop-btn')) {
        const taskId = event.target.closest('.stop-btn').getAttribute('data-task-id');
        if (confirm('确定要停止当前任务吗？')) {
            fetch(`/task/${taskId}/stop`, {
                method: 'POST'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                    } else {
                        alert('任务已停止');
                        updateQueueStatus(); // 刷新状态
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('停止任务失败');
                });
        }
    }
});
