# 前端设计

## 页面布局

```
┌──────────────────────────────────────────────────────────┐
│  🔧 离线软件包下载工具                      [任务历史] [设置] │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  1. 选择系统类型                                    │ │
│  │  ○ RPM  ○ DEB                                      │ │
│  │                                                    │ │
│  │  2. 选择发行版和架构                               │ │
│  │  [CentOS 8 ▼] [x86_64 ▼]                          │ │
│  │                                                    │ │
│  │  3. 输入包名                                       │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │ nginx, python3, redis                        │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  │  [🔍 搜索包]  [📋 批量导入]  [📦 预设模板]         │ │
│  │                                                    │ │
│  │  4. 高级选项                                       │ │
│  │  ☑ 递归下载所有依赖                                │ │
│  │  ☑ 包含推荐包                                      │ │
│  │                                                    │ │
│  │           [🚀 开始下载]                            │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  📥 下载进度                                        │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  75%           │ │
│  │  正在下载: openssl-libs-1.1.1k (3/12)              │ │
│  │  已下载: 45.2 MB / 120.5 MB                        │ │
│  │                                                    │ │
│  │  日志:                                             │ │
│  │  [15:30:22] 开始解析依赖...                         │ │
│  │  [15:30:25] 找到 12 个依赖包                        │ │
│  │  [15:30:26] 开始下载...                             │ │
│  │  [15:30:28] 下载完成: nginx-1.20.1                 │ │
│  │  [15:30:30] 下载完成: openssl-libs-1.1.1k          │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  最近任务                                           │ │
│  │  ✅ nginx (CentOS 8) - 2024-02-06 15:30 - [下载]    │ │
│  │  ✅ docker-ce (CentOS 8) - 2024-02-06 14:20 - [下载]│ │
│  │  ❌ mysql-server (Ubuntu 22) - 2024-02-06 13:10     │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## 核心功能模块

### 1. 包输入组件

```javascript
class PackageInput {
    constructor(container) {
        this.container = container;
        this.packages = [];
        this.init();
    }

    init() {
        // 标签输入框
        this.render();
        this.bindEvents();
    }

    addPackage(name) {
        if (!this.packages.includes(name)) {
            this.packages.push(name);
            this.render();
        }
    }

    removePackage(index) {
        this.packages.splice(index, 1);
        this.render();
    }

    render() {
        this.container.innerHTML = `
            <div class="package-tags">
                ${this.packages.map((pkg, i) => `
                    <span class="tag">
                        ${pkg}
                        <button onclick="removePackage(${i})">×</button>
                    </span>
                `).join('')}
            </div>
            <input type="text" placeholder="输入包名后回车..."
                   onkeypress="handleKeyPress(event)">
        `;
    }
}
```

### 2. 包搜索组件

```javascript
class PackageSearch {
    constructor(systemType, distribution) {
        this.systemType = systemType;
        this.distribution = distribution;
    }

    async search(query) {
        const response = await fetch(
            `/api/search?type=${this.systemType}&dist=${this.distribution}&q=${query}`
        );
        return await response.json();
    }

    renderSuggestions(packages) {
        return packages.map(pkg => `
            <div class="suggestion-item" onclick="selectPackage('${pkg.name}')">
                <strong>${pkg.name}</strong> - ${pkg.summary}
                <small>${pkg.version}</small>
            </div>
        `).join('');
    }
}
```

### 3. 进度显示组件

```javascript
class DownloadProgress {
    constructor(taskId) {
        this.taskId = taskId;
        this.eventSource = null;
    }

    start() {
        this.eventSource = new EventSource(`/api/events/${this.taskId}`);

        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.update(data);
        };

        this.eventSource.onerror = () => {
            this.showError('连接断开');
        };
    }

    update(data) {
        document.getElementById('progress-bar').style.width = `${data.progress}%`;
        document.getElementById('progress-text').textContent = `${data.progress}%`;
        document.getElementById('status-message').textContent = data.message;

        // 更新日志
        if (data.log) {
            this.addLog(data.log);
        }

        // 完成后自动下载
        if (data.status === 'completed') {
            this.autoDownload(data.download_url);
        }
    }

    autoDownload(url) {
        const a = document.createElement('a');
        a.href = url;
        a.download = '';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    stop() {
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}
```

### 4. 任务列表组件

```javascript
class TaskList {
    constructor() {
        this.tasks = [];
        this.load();
        this.startAutoRefresh();
    }

    async load() {
        const response = await fetch('/api/tasks');
        const data = await response.json();
        this.tasks = data.tasks;
        this.render();
    }

    render() {
        const container = document.getElementById('task-list');
        container.innerHTML = this.tasks.map(task => `
            <div class="task-item ${task.status}">
                <div class="task-header">
                    <span class="task-name">${task.packages.join(', ')}</span>
                    <span class="task-meta">
                        ${task.system_type} - ${task.distribution}
                    </span>
                </div>
                <div class="task-status">
                    ${this.getStatusIcon(task.status)}
                    ${task.message}
                </div>
                ${task.status === 'completed' ? `
                    <button onclick="downloadFile('${task.task_id}')">
                        下载压缩包
                    </button>
                ` : ''}
            </div>
        `).join('');
    }

    getStatusIcon(status) {
        const icons = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌'
        };
        return icons[status] || '❓';
    }

    startAutoRefresh() {
        setInterval(() => this.load(), 5000); // 5秒刷新
    }
}
```

## CSS 样式设计

```css
:root {
    --primary-color: #2563eb;
    --success-color: #10b981;
    --error-color: #ef4444;
    --bg-color: #f8fafc;
    --border-color: #e2e8f0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg-color);
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
}

.card {
    background: white;
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* 标签输入 */
.package-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
}

.tag {
    background: #dbeafe;
    padding: 4px 12px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.tag button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 18px;
    color: #6b7280;
}

/* 进度条 */
.progress-container {
    background: #e5e7eb;
    height: 24px;
    border-radius: 12px;
    overflow: hidden;
    margin: 16px 0;
}

.progress-bar {
    background: var(--primary-color);
    height: 100%;
    transition: width 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 12px;
}

/* 日志 */
.log-container {
    background: #1f2937;
    color: #f3f4f6;
    padding: 16px;
    border-radius: 8px;
    font-family: 'Courier New', monospace;
    font-size: 14px;
    max-height: 300px;
    overflow-y: auto;
}

.log-entry {
    margin: 4px 0;
    padding-left: 12px;
    border-left: 2px solid #6b7280;
}

/* 任务列表 */
.task-item {
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}

.task-item.completed {
    border-left: 4px solid var(--success-color);
}

.task-item.failed {
    border-left: 4px solid var(--error-color);
}

/* 响应式 */
@media (max-width: 768px) {
    .container {
        padding: 12px;
    }

    .card {
        padding: 16px;
    }
}
```

## API 交互封装

```javascript
class API {
    static async download(request) {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(request)
        });
        return await response.json();
    }

    static async getTasks() {
        const response = await fetch('/api/tasks');
        return await response.json();
    }

    static async getTask(taskId) {
        const response = await fetch(`/api/tasks/${taskId}`);
        return await response.json();
    }

    static async deleteTask(taskId) {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });
        return await response.json();
    }

    static async searchPackages(type, dist, query) {
        const response = await fetch(
            `/api/packages?type=${type}&dist=${dist}&q=${query}`
        );
        return await response.json();
    }
}
```

## 主应用逻辑

```javascript
class App {
    constructor() {
        this.packageInput = new PackageInput(document.getElementById('package-input'));
        this.taskList = new TaskList();
        this.currentProgress = null;
    }

    async startDownload() {
        const request = {
            packages: this.packageInput.packages,
            system_type: document.getElementById('system-type').value,
            distribution: document.getElementById('distribution').value,
            arch: document.getElementById('arch').value,
            deep_download: document.getElementById('deep-download').checked
        };

        try {
            const result = await API.download(request);

            // 显示进度
            this.currentProgress = new DownloadProgress(result.task_id);
            this.currentProgress.start();

            // 刷新任务列表
            this.taskList.load();

        } catch (error) {
            alert('下载失败: ' + error.message);
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
```

## 预设模板功能

```javascript
const TEMPLATES = {
    'web-server': {
        name: 'Web 服务器',
        packages: ['nginx', 'openssl'],
        description: '包含 Nginx 及其依赖'
    },
    'docker': {
        name: 'Docker 容器',
        packages: ['docker-ce', 'docker-ce-cli', 'containerd.io'],
        description: '完整的 Docker 容器环境'
    },
    'development': {
        name: '开发工具',
        packages: ['git', 'vim', 'python3', 'nodejs', 'gcc'],
        description: '常用的开发工具集'
    }
};

function applyTemplate(templateId) {
    const template = TEMPLATES[templateId];
    window.app.packageInput.packages = [...template.packages];
    window.app.packageInput.render();
}
```

这部分前端设计是否满足需求?
