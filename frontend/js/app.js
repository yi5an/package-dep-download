/**
 * 包输入管理器
 */
class PackageInput {
    constructor(inputId, tagsId) {
        this.input = document.getElementById(inputId);
        this.tagsContainer = document.getElementById(tagsId);
        this.packages = new Set();

        this.init();
    }

    init() {
        // 监听回车键
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.addPackage();
            }
        });
    }

    addPackage() {
        const packageName = this.input.value.trim();

        if (!packageName) {
            return;
        }

        if (this.packages.has(packageName)) {
            this.input.value = '';
            return;
        }

        this.packages.add(packageName);
        this.renderTag(packageName);
        this.input.value = '';
    }

    removePackage(packageName) {
        this.packages.delete(packageName);
        this.render();
    }

    renderTag(packageName) {
        const tag = document.createElement('div');
        tag.className = 'package-tag';
        tag.innerHTML = `
            ${packageName}
            <span class="remove-tag" data-package="${packageName}">×</span>
        `;

        tag.querySelector('.remove-tag').addEventListener('click', () => {
            this.removePackage(packageName);
        });

        this.tagsContainer.appendChild(tag);
    }

    render() {
        this.tagsContainer.innerHTML = '';
        this.packages.forEach(pkg => this.renderTag(pkg));
    }

    getPackages() {
        return Array.from(this.packages);
    }

    clear() {
        this.packages.clear();
        this.render();
    }
}

/**
 * 任务列表管理器
 */
class TaskList {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.tasks = [];
        this.pollingInterval = null;
    }

    async fetchTasks() {
        try {
            const response = await fetch('/api/tasks');
            this.tasks = await response.json();
            this.render();
        } catch (error) {
            console.error('获取任务列表失败:', error);
        }
    }

    render() {
        if (this.tasks.length === 0) {
            this.container.innerHTML = `
                <div class="empty-state">
                    <p>暂无任务记录</p>
                </div>
            `;
            return;
        }

        this.container.innerHTML = this.tasks.map(task => this.renderTask(task)).join('');
    }

    renderTask(task) {
        const statusClass = task.status.toLowerCase();
        const statusText = {
            'pending': '等待中',
            'processing': '处理中',
            'completed': '已完成',
            'failed': '失败'
        }[task.status] || task.status;

        let detailsHtml = '';

        if (task.packages && task.packages.length > 0) {
            detailsHtml += `
                <div class="task-packages">
                    <strong>包列表:</strong>
                    ${task.packages.join(', ')}
                </div>
            `;
        }

        if (task.status === 'processing' && task.progress !== undefined) {
            detailsHtml += `
                <div class="task-progress">
                    进度: ${task.progress}%
                </div>
            `;
        }

        if (task.error) {
            detailsHtml += `
                <div class="task-error">
                    错误: ${task.error}
                </div>
            `;
        }

        return `
            <div class="task-item ${statusClass}">
                <div class="task-header">
                    <div class="task-id">任务 #${task.id}</div>
                    <div class="task-status ${statusClass}">${statusText}</div>
                </div>
                <div class="task-details">
                    系统: ${task.system_type} | 发行版: ${task.distribution}
                </div>
                ${detailsHtml}
            </div>
        `;
    }

    startPolling(intervalMs = 2000) {
        if (this.pollingInterval) {
            return;
        }

        this.pollingInterval = setInterval(() => {
            this.fetchTasks();
        }, intervalMs);
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
}

/**
 * 应用程序主类
 */
class App {
    constructor() {
        this.packageInput = new PackageInput('package-input', 'package-tags');
        this.taskList = new TaskList('task-list');
        this.currentTaskId = null;
        this.progressPolling = null;

        this.init();
    }

    init() {
        // 获取元素
        this.systemTypeSelect = document.getElementById('system-type');
        this.distributionSelect = document.getElementById('distribution');
        this.deepDownloadCheckbox = document.getElementById('deep-download');
        this.downloadButton = document.getElementById('btn-download');
        this.progressSection = document.getElementById('progress-section');
        this.progressBar = document.getElementById('progress-bar');
        this.progressMessage = document.getElementById('progress-message');

        // 绑定事件
        this.downloadButton.addEventListener('click', () => this.handleDownload());

        // 启动任务列表轮询
        this.taskList.startPolling(2000);
        this.taskList.fetchTasks();
    }

    async handleDownload() {
        const packages = this.packageInput.getPackages();

        if (packages.length === 0) {
            alert('请至少输入一个包名');
            return;
        }

        // 禁用按钮
        this.downloadButton.disabled = true;
        this.downloadButton.textContent = '提交中...';

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    system_type: this.systemTypeSelect.value,
                    distribution: this.distributionSelect.value,
                    packages: packages,
                    deep_download: this.deepDownloadCheckbox.checked
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '提交失败');
            }

            const data = await response.json();
            this.currentTaskId = data.task_id;

            // 显示进度区域
            this.progressSection.style.display = 'block';
            this.updateProgress(0, '任务已创建,正在处理...');

            // 开始轮询进度
            this.startProgressPolling();

            // 清空输入
            this.packageInput.clear();

        } catch (error) {
            alert(`提交失败: ${error.message}`);
            this.downloadButton.disabled = false;
            this.downloadButton.textContent = '🚀 开始下载';
        }
    }

    startProgressPolling() {
        if (this.progressPolling) {
            return;
        }

        this.progressPolling = setInterval(async () => {
            try {
                const response = await fetch(`/api/tasks/${this.currentTaskId}`);
                const task = await response.json();

                if (task.progress !== undefined) {
                    this.updateProgress(task.progress, this.getProgressMessage(task));
                }

                // 任务完成或失败
                if (task.status === 'completed') {
                    this.stopProgressPolling();
                    this.updateProgress(100, '✅ 下载完成!');
                    this.triggerDownload(task.archive_path);
                    this.taskList.fetchTasks();
                    this.resetButton();
                } else if (task.status === 'failed') {
                    this.stopProgressPolling();
                    this.updateProgress(0, `❌ 下载失败: ${task.error}`);
                    this.taskList.fetchTasks();
                    this.resetButton();
                }

            } catch (error) {
                console.error('获取进度失败:', error);
            }
        }, 2000);
    }

    stopProgressPolling() {
        if (this.progressPolling) {
            clearInterval(this.progressPolling);
            this.progressPolling = null;
        }
    }

    updateProgress(progress, message) {
        this.progressBar.style.width = `${progress}%`;
        this.progressBar.textContent = `${progress}%`;
        this.progressMessage.textContent = message;
    }

    getProgressMessage(task) {
        if (task.current_step) {
            return `正在执行: ${task.current_step}`;
        }
        return '处理中...';
    }

    triggerDownload(archivePath) {
        if (!archivePath) {
            return;
        }

        // 创建隐藏的下载链接
        const link = document.createElement('a');
        link.href = `/api/download/${this.currentTaskId}/archive`;
        link.download = archivePath.split('/').pop();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    resetButton() {
        setTimeout(() => {
            this.downloadButton.disabled = false;
            this.downloadButton.textContent = '🚀 开始下载';
        }, 2000);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new App();
});
