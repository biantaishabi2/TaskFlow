// 通用工具函数
function formatDate(timestamp) {
    if (!timestamp) return '-';
    return new Date(timestamp * 1000).toLocaleString();
}

function formatDuration(seconds) {
    if (!seconds) return '-';
    
    if (seconds < 60) {
        return seconds.toFixed(2) + ' 秒';
    } else if (seconds < 3600) {
        return (seconds / 60).toFixed(2) + ' 分钟';
    } else {
        return (seconds / 3600).toFixed(2) + ' 小时';
    }
}

function formatTaskStatus(status, success) {
    if (status === 'completed') {
        return success ? 
            '<span class="status-completed">成功</span>' : 
            '<span class="status-error">失败</span>';
    } else if (status === 'running' || status === 'executing') {
        return '<span class="status-running">执行中</span>';
    } else if (status === 'planning') {
        return '<span class="status-planning">规划中</span>';
    } else if (status === 'error') {
        return '<span class="status-error">错误</span>';
    } else {
        return status || '未知';
    }
}

// 错误处理
function handleApiError(error, elementId) {
    console.error('API错误:', error);
    $(`#${elementId}`).html(`
        <div class="alert alert-danger">
            <h5>加载失败</h5>
            <p>${error.message || '无法连接到API服务器'}</p>
        </div>
    `);
}

// 数据刷新处理
let refreshTimers = {};

function startRefreshTimer(functionName, interval, ...args) {
    // 清除现有定时器
    if (refreshTimers[functionName]) {
        clearInterval(refreshTimers[functionName]);
    }
    
    // 创建新定时器
    refreshTimers[functionName] = setInterval(() => {
        window[functionName](...args);
    }, interval);
    
    // 立即执行一次
    window[functionName](...args);
}

function stopAllRefreshTimers() {
    Object.values(refreshTimers).forEach(timer => clearInterval(timer));
    refreshTimers = {};
}

// 页面离开时停止所有定时器
$(window).on('beforeunload', stopAllRefreshTimers);
