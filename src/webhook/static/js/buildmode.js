
/**
 * 存储当前选中的构建模式
 */
let currentBuildMode = localStorage.getItem('currentBuildMode') || 'all';

/**
 * 初始化时设置选中的 tag
 */
document.addEventListener('DOMContentLoaded', function () {
    updateSelectedTag();
});

/**
 * 更新选中的 tag 样式
 */
function updateSelectedTag() {
    document.querySelectorAll('.task-filter-tags .badge').forEach(tag => {
        const mode = tag.getAttribute('data-build-mode');
        // 先移除所有可能的颜色类
        tag.classList.remove('bg-primary', 'bg-info', 'bg-warning', 'bg-success', 'bg-light', 'text-white', 'text-dark', 'text-muted', 'active');

        if (mode === currentBuildMode) {
            tag.classList.add('active');
            // 设置选中状态的样式
            if (mode === 'all') {
                tag.classList.add('bg-primary', 'text-white');
            } else if (mode === 'dev') {
                tag.classList.add('bg-info', 'text-white'); // 匹配 .dev-req
            } else if (mode === 'test') {
                tag.classList.add('bg-warning', 'text-dark'); // 匹配 .test-req
            } else if (mode === 'release') {
                tag.classList.add('bg-success', 'text-white'); // 匹配 .release-req
            }
        } else {
            // 设置未选中状态的样式 (使用浅灰色背景和深色文字以确保可见性)
            tag.classList.add('bg-light', 'text-dark');
        }
    });
}

/**
 * 添加 tag 点击事件
 */
document.querySelectorAll('.task-filter-tags .badge').forEach(tag => {
    tag.addEventListener('click', function () {
        currentBuildMode = this.getAttribute('data-build-mode');
        localStorage.setItem('currentBuildMode', currentBuildMode);
        updateSelectedTag();
        updateQueueStatus(); // 重新获取队列状态
    });
});