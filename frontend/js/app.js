/**
 * 包输入管理器
 */
class PackageInput {
    constructor(inputId, tagsId) {
        console.log('[PackageInput] 初始化, inputId:', inputId, 'tagsId:', tagsId);
        this.input = document.getElementById(inputId);
        this.tagsContainer = document.getElementById(tagsId);
        this.packages = new Set();

        if (!this.input) {
            console.error('[PackageInput] 找不到输入框元素:', inputId);
            return;
        }
        if (!this.tagsContainer) {
            console.error('[PackageInput] 找不到标签容器元素:', tagsId);
            return;
        }

        console.log('[PackageInput] 元素找到,开始初始化');
        this.init();
    }

    init() {
        console.log('[PackageInput] 绑定事件监听器');
        // 监听回车键
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                console.log('[PackageInput] 回车键被按下,值:', this.input.value);
                this.addPackage();
            }
        });

        // 监听输入,显示包名建议
        this.input.addEventListener('input', (e) => {
            const value = e.target.value;
            console.log('[PackageInput] 输入事件,值:', value, '长度:', value.length);
            this.onInput(value);
        });
    }

    onInput(value) {
        console.log('[PackageInput] onInput 被调用,值:', value);
        if (value.length >= 2) {
            console.log('[PackageInput] 触发建议显示');
            // 触发建议显示事件
            if (window.app && window.app.showPackageSuggestions) {
                window.app.showPackageSuggestions(value);
            } else {
                console.error('[PackageInput] window.app 不存在');
            }
        } else {
            console.log('[PackageInput] 隐藏建议');
            if (window.app && window.app.hidePackageSuggestions) {
                window.app.hidePackageSuggestions();
            }
        }
    }

    addPackage() {
        const packageName = this.input.value.trim();
        console.log('[PackageInput] 尝试添加包:', packageName);

        if (!packageName) {
            console.warn('[PackageInput] 包名为空,跳过');
            return;
        }

        if (this.packages.has(packageName)) {
            console.warn('[PackageInput] 包已存在:', packageName);
            this.input.value = '';
            return;
        }

        this.packages.add(packageName);
        console.log('[PackageInput] 包已添加到Set,当前包列表:', Array.from(this.packages));
        this.renderTag(packageName);
        this.input.value = '';
    }

    removePackage(packageName) {
        console.log('[PackageInput] 移除包:', packageName);
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
        console.log('[TaskList] 初始化, containerId:', containerId);
        this.container = document.getElementById(containerId);
        this.tasks = [];
        this.pollingInterval = null;

        if (!this.container) {
            console.error('[TaskList] 找不到容器元素:', containerId);
        }
    }

    async fetchTasks() {
        console.log('[TaskList] 获取任务列表');
        try {
            const response = await fetch('/api/tasks');
            const data = await response.json();
            this.tasks = data.tasks || [];
            console.log('[TaskList] 获取到任务:', this.tasks.length);
            this.render();
        } catch (error) {
            console.error('[TaskList] 获取任务列表失败:', error);
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

        this.container.innerHTML = this.tasks.map(task => {
            console.log('[TaskList] 渲染任务:', task);
            const statusClass = task.status || 'pending';
            const statusText = {
                'pending': '⏳ 等待中',
                'running': '🔄 进行中',
                'completed': '✅ 已完成',
                'failed': '❌ 失败'
            }[task.status] || task.status;

            let downloadButton = '';
            if (task.status === 'completed') {
                downloadButton = `
                    <button onclick="window.app.downloadFile('${task.task_id}')" class="btn-download">
                        📥 下载压缩包
                    </button>
                `;
            }

            return `
                <div class="task-item ${statusClass}">
                    <div class="task-header">
                        <div class="task-info">
                            <strong>包列表:</strong> ${task.packages ? task.packages.join(', ') : 'N/A'}
                            <br>
                            <span class="task-meta">
                                ${task.system_type} | ${task.distribution} | ${task.arch || 'auto'}
                            </span>
                        </div>
                        <div class="task-status">
                            ${statusText}
                            ${downloadButton}
                        </div>
                    </div>
                    <div class="task-message">
                        ${task.message || '无消息'}
                    </div>
                </div>
            `;
        }).join('');
    }

    startPolling(intervalMs = 2000) {
        console.log('[TaskList] 开始轮询,间隔:', intervalMs);
        if (this.pollingInterval) {
            return;
        }

        this.pollingInterval = setInterval(() => {
            this.fetchTasks();
        }, intervalMs);
    }

    stopPolling() {
        console.log('[TaskList] 停止轮询');
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
        console.log('[App] 初始化应用');
        this.packageInput = new PackageInput('package-input', 'package-tags');
        this.taskList = new TaskList('task-list');
        this.currentTaskId = null;
        this.progressPolling = null;

        this.init();
    }

    init() {
        console.log('[App] 开始初始化');
        // 获取元素
        this.systemTypeSelect = document.getElementById('system-type');
        this.distributionSelect = document.getElementById('distribution');
        this.archSelect = document.getElementById('arch');
        this.deepDownloadCheckbox = document.getElementById('deep-download');
        this.downloadButton = document.getElementById('btn-download');
        this.progressSection = document.getElementById('progress-section');
        this.progressBar = document.getElementById('progress-bar');
        this.progressMessage = document.getElementById('progress-message');

        // 验证元素
        if (!this.downloadButton) {
            console.error('[App] 找不到下载按钮!');
            return;
        }

        console.log('[App] 所有元素找到成功');

        // 系统类型改变时更新发行版选项
        this.systemTypeSelect.addEventListener('change', () => {
            console.log('[App] 系统类型改变:', this.systemTypeSelect.value);
            this.updateDistributions();
        });

        // 初始化发行版选项
        this.updateDistributions();

        // 初始化包名建议
        this.initPackageSuggestions();

        // 绑定下载按钮事件
        console.log('[App] 绑定下载按钮事件');
        this.downloadButton.addEventListener('click', () => {
            console.log('[App] 下载按钮被点击');
            this.handleDownload();
        });

        // 启动任务列表轮询
        this.taskList.startPolling(2000);
        this.taskList.fetchTasks();

        // 点击外部隐藏建议框
        document.addEventListener('click', (e) => {
            if (this.suggestionsElement &&
                this.suggestionsElement.style.display === 'block' &&
                !this.suggestionsElement.contains(e.target) &&
                e.target !== this.packageInput.input) {
                this.hidePackageSuggestions();
            }
        });

        console.log('[App] 初始化完成');
    }

    updateDistributions() {
        console.log('[App] 更新发行版选项,系统类型:', this.systemTypeSelect.value);
        const systemType = this.systemTypeSelect.value;
        const options = this.distributionSelect.querySelectorAll('option');

        options.forEach(option => {
            const optionType = option.getAttribute('data-type');
            if (optionType === systemType) {
                option.style.display = '';
            } else {
                option.style.display = 'none';
            }
        });

        // 选择第一个可见的选项
        const firstVisible = Array.from(options).find(
            opt => opt.style.display !== 'none'
        );
        if (firstVisible) {
            this.distributionSelect.value = firstVisible.value;
            console.log('[App] 选择默认发行版:', firstVisible.value);
        }
    }

    initPackageSuggestions() {
        console.log('[App] 初始化包名建议');
        // 常见包列表(按系统类型分类)
        this.commonPackages = {
            rpm: [
                'bash', 'coreutils', 'vim-minimal', 'nano', 'curl',
                'wget', 'git', 'nginx', 'docker-ce', 'podman',
                'python3', 'python3-pip', 'nodejs', 'golang', 'java-11-openjdk',
                'mysql', 'postgresql', 'redis', 'httpd', 'tomcat', 'openssh-server'
            ],
            deb: [
                'bash', 'coreutils', 'vim', 'nano', 'curl',
                'wget', 'git', 'nginx', 'docker.io', 'podman',
                'python3', 'python3-pip', 'nodejs', 'golang', 'openjdk-11-jre',
                'mysql-server', 'postgresql', 'redis-server', 'apache2', 'openssh-server'
            ]
        };

        this.suggestionsElement = document.getElementById('package-suggestions');
        if (!this.suggestionsElement) {
            console.error('[App] 找不到建议框元素!');
        } else {
            console.log('[App] 建议框元素找到');
        }
    }

    showPackageSuggestions(query) {
        console.log('[App] showPackageSuggestions 被调用, query:', query);
        const systemType = this.systemTypeSelect.value;
        const packages = this.commonPackages[systemType] || [];

        console.log('[App] 系统类型:', systemType, '可用包数量:', packages.length);

        // 过滤匹配的包
        const matches = packages.filter(pkg =>
            pkg.toLowerCase().startsWith(query.toLowerCase())
        );

        console.log('[App] 匹配的包:', matches);

        if (matches.length === 0) {
            this.hidePackageSuggestions();
            return;
        }

        // 显示建议列表
        this.suggestionsElement.innerHTML = `
            <div class="suggestions-list">
                ${matches.map(pkg => {
                    // 转义单引号以避免 JavaScript 语法错误
                    const escapedPkg = pkg.replace(/'/g, "\\'");
                    return `
                        <div class="suggestion-item" data-package="${escapedPkg}">
                            <strong>${pkg}</strong>
                        </div>
                    `;
                }).join('')}
            </div>
        `;

        // 使用事件委托而不是内联 onclick
        const suggestionItems = this.suggestionsElement.querySelectorAll('.suggestion-item');
        suggestionItems.forEach(item => {
            item.addEventListener('click', () => {
                const packageName = item.getAttribute('data-package');
                this.selectPackage(packageName);
            });
        });

        this.suggestionsElement.style.display = 'block';
        console.log('[App] 建议框已显示');
    }

    hidePackageSuggestions() {
        if (this.suggestionsElement) {
            this.suggestionsElement.style.display = 'none';
            console.log('[App] 建议框已隐藏');
        }
    }

    selectPackage(packageName) {
        console.log('[App] selectPackage 被调用:', packageName);
        this.packageInput.input.value = packageName;
        this.packageInput.addPackage();
        this.hidePackageSuggestions();
        this.packageInput.input.focus();
    }

    async handleDownload() {
        console.log('[App] handleDownload 开始');
        const packages = this.packageInput.getPackages();

        if (packages.length === 0) {
            alert('请至少输入一个包名');
            return;
        }

        console.log('[App] 要下载的包:', packages);

        // 禁用按钮
        this.downloadButton.disabled = true;
        this.downloadButton.textContent = '提交中...';

        try {
            const requestData = {
                system_type: this.systemTypeSelect.value,
                distribution: this.distributionSelect.value,
                arch: this.archSelect.value,
                packages: packages,
                deep_download: this.deepDownloadCheckbox.checked
            };

            console.log('[App] 发送请求:', requestData);

            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            console.log('[App] 响应状态:', response.status);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '提交失败');
            }

            const data = await response.json();
            console.log('[App] 任务创建成功:', data);
            this.currentTaskId = data.task_id;

            // 显示进度区域
            this.progressSection.style.display = 'block';
            this.updateProgress(0, '任务已创建,正在处理...');

            // 开始轮询进度
            this.startProgressPolling();

            // 清空输入
            this.packageInput.clear();

        } catch (error) {
            console.error('[App] 下载失败:', error);
            alert(`提交失败: ${error.message}`);
            this.downloadButton.disabled = false;
            this.downloadButton.textContent = '🚀 开始下载';
        }
    }

    startProgressPolling() {
        console.log('[App] 开始进度轮询, taskId:', this.currentTaskId);
        if (this.progressPolling) {
            return;
        }

        this.progressPolling = setInterval(async () => {
            try {
                const response = await fetch(`/api/tasks/${this.currentTaskId}`);
                const task = await response.json();

                console.log('[App] 任务状态:', task);

                if (task.progress !== undefined) {
                    this.updateProgress(task.progress, this.getProgressMessage(task));
                }

                // 任务完成或失败
                if (task.status === 'completed') {
                    console.log('[App] 任务完成');
                    this.stopProgressPolling();
                    this.updateProgress(100, '✅ 下载完成!');
                    this.triggerDownload(task.archive_path);
                    this.taskList.fetchTasks();
                    this.resetButton();
                } else if (task.status === 'failed') {
                    console.log('[App] 任务失败:', task.error);
                    this.stopProgressPolling();
                    this.updateProgress(0, `❌ 下载失败: ${task.error}`);
                    this.taskList.fetchTasks();
                    this.resetButton();
                }

            } catch (error) {
                console.error('[App] 获取进度失败:', error);
            }
        }, 2000);
    }

    stopProgressPolling() {
        console.log('[App] 停止进度轮询');
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
        return task.message || '处理中...';
    }

    triggerDownload(archivePath) {
        console.log('[App] 触发下载, archivePath:', archivePath);
        if (!archivePath) {
            console.log('[App] 无archivePath,从taskId下载');
            // 从 taskId 下载
            const link = document.createElement('a');
            link.href = `/api/download/${this.currentTaskId}`;
            link.download = `packages-${this.currentTaskId}.tar.gz`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            return;
        }

        // 创建隐藏的下载链接
        const link = document.createElement('a');
        link.href = `/api/download/${this.currentTaskId}`;
        link.download = archivePath.split('/').pop();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    downloadFile(taskId) {
        console.log('[App] downloadFile 被调用, taskId:', taskId);
        window.location.href = `/api/download/${taskId}`;
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
    console.log('[DOMContentLoaded] DOM加载完成,初始化应用');
    window.app = new App();
});
