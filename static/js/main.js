// 云控助手 - 主要 JavaScript 功能

// 全局配置
const YunKong = {
    config: {
        apiBase: '/api',
        timeout: 30000,
        refreshInterval: 30000
    },
    
    // 工具函数
    utils: {
        // 显示加载状态
        showLoading: function(element, text = '加载中...') {
            if (typeof element === 'string') {
                element = document.querySelector(element);
            }
            
            if (element) {
                element.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>${text}`;
                element.disabled = true;
            }
        },
        
        // 隐藏加载状态
        hideLoading: function(element, originalText) {
            if (typeof element === 'string') {
                element = document.querySelector(element);
            }
            
            if (element) {
                element.innerHTML = originalText;
                element.disabled = false;
            }
        },
        
        // 格式化日期
        formatDate: function(dateString) {
            if (!dateString) return '从未';
            
            const date = new Date(dateString);
            const now = new Date();
            const diff = now - date;
            
            // 小于1分钟
            if (diff < 60000) {
                return '刚刚';
            }
            
            // 小于1小时
            if (diff < 3600000) {
                return Math.floor(diff / 60000) + '分钟前';
            }
            
            // 小于1天
            if (diff < 86400000) {
                return Math.floor(diff / 3600000) + '小时前';
            }
            
            // 大于1天
            return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });
        },
        
        // 数字格式化
        formatNumber: function(num) {
            if (num >= 1000000) {
                return (num / 1000000).toFixed(1) + 'M';
            }
            if (num >= 1000) {
                return (num / 1000).toFixed(1) + 'K';
            }
            return num.toString();
        },
        
        // 复制到剪贴板
        copyToClipboard: function(text) {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(() => {
                    this.showToast('已复制到剪贴板', 'success');
                });
            } else {
                // 兼容旧浏览器
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                this.showToast('已复制到剪贴板', 'success');
            }
        },
        
        // 显示 Toast 消息
        showToast: function(message, type = 'info') {
            // 如果已经有 toast 容器，使用现有的，否则创建新的
            let toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
                document.body.appendChild(toastContainer);
            }
            
            const toastId = 'toast_' + Date.now();
            const toast = document.createElement('div');
            toast.className = `toast align-items-center text-white bg-${type} border-0`;
            toast.id = toastId;
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;
            
            toastContainer.appendChild(toast);
            
            // 显示 toast
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
            
            // 自动清理
            toast.addEventListener('hidden.bs.toast', () => {
                toast.remove();
            });
        }
    },
    
    // API 请求
    api: {
        // 通用请求函数
        request: function(url, options = {}) {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                },
                timeout: YunKong.config.timeout
            };
            
            const finalOptions = { ...defaultOptions, ...options };
            
            return fetch(url, finalOptions)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .catch(error => {
                    console.error('API Request Error:', error);
                    throw error;
                });
        },
        
        // GET 请求
        get: function(url) {
            return this.request(url, { method: 'GET' });
        },
        
        // POST 请求
        post: function(url, data) {
            return this.request(url, {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },
        
        // PUT 请求
        put: function(url, data) {
            return this.request(url, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },
        
        // DELETE 请求
        delete: function(url) {
            return this.request(url, { method: 'DELETE' });
        }
    },
    
    // 页面特定功能
    pages: {
        // 仪表板功能
        dashboard: {
            init: function() {
                this.loadStatistics();
                this.startAutoRefresh();
            },
            
            loadStatistics: function() {
                // 加载统计数据的逻辑
                console.log('Loading dashboard statistics...');
            },
            
            startAutoRefresh: function() {
                setInterval(() => {
                    this.loadStatistics();
                }, YunKong.config.refreshInterval);
            }
        },
        
        // 账户管理功能
        accounts: {
            init: function() {
                this.bindEvents();
            },
            
            bindEvents: function() {
                // 绑定账户相关事件
                document.addEventListener('click', (e) => {
                    if (e.target.matches('[data-action="sync-groups"]')) {
                        e.preventDefault();
                        const accountId = e.target.dataset.accountId;
                        this.syncGroups(accountId);
                    }
                    
                    if (e.target.matches('[data-action="test-connection"]')) {
                        e.preventDefault();
                        const accountId = e.target.dataset.accountId;
                        this.testConnection(accountId);
                    }
                });
            },
            
            syncGroups: function(accountId) {
                if (!confirm('确定要同步此账户的群组信息吗？')) {
                    return;
                }
                
                YunKong.api.get(`/groups/sync/${accountId}`)
                    .then(data => {
                        if (data.success) {
                            YunKong.utils.showToast(data.message, 'success');
                        } else {
                            YunKong.utils.showToast('同步失败：' + data.message, 'danger');
                        }
                    })
                    .catch(error => {
                        YunKong.utils.showToast('网络错误，请重试', 'danger');
                    });
            },
            
            testConnection: function(accountId) {
                YunKong.utils.showToast('连接测试功能开发中...', 'info');
            }
        },
        
        // 活动管理功能
        campaigns: {
            init: function() {
                this.bindEvents();
            },
            
            bindEvents: function() {
                document.addEventListener('click', (e) => {
                    if (e.target.matches('[data-action="start-campaign"]')) {
                        e.preventDefault();
                        const campaignId = e.target.dataset.campaignId;
                        this.startCampaign(campaignId);
                    }
                });
            },
            
            startCampaign: function(campaignId) {
                if (!confirm('确定要启动这个营销活动吗？')) {
                    return;
                }
                
                YunKong.api.get(`/campaigns/start/${campaignId}`)
                    .then(data => {
                        if (data.success) {
                            YunKong.utils.showToast('活动启动成功！', 'success');
                            setTimeout(() => {
                                location.reload();
                            }, 1000);
                        } else {
                            YunKong.utils.showToast('启动失败：' + data.message, 'danger');
                        }
                    })
                    .catch(error => {
                        YunKong.utils.showToast('网络错误，请重试', 'danger');
                    });
            }
        }
    }
};

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化 tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 初始化 popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // 根据当前页面初始化相应功能
    const body = document.body;
    const pageName = body.dataset.page;
    
    switch (pageName) {
        case 'dashboard':
            YunKong.pages.dashboard.init();
            break;
        case 'accounts':
            YunKong.pages.accounts.init();
            break;
        case 'campaigns':
            YunKong.pages.campaigns.init();
            break;
    }
    
    // 添加淡入动画
    document.querySelectorAll('.card').forEach(card => {
        card.classList.add('fade-in');
    });
});

// 表单验证工具
const FormValidator = {
    // 验证手机号码
    validatePhone: function(phone) {
        const phonePattern = /^\+\d{10,15}$/;
        return phonePattern.test(phone);
    },
    
    // 验证邮箱
    validateEmail: function(email) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailPattern.test(email);
    },
    
    // 验证必填字段
    validateRequired: function(value) {
        return value && value.trim() !== '';
    },
    
    // 验证数字
    validateNumber: function(value, min = null, max = null) {
        const num = parseFloat(value);
        if (isNaN(num)) return false;
        if (min !== null && num < min) return false;
        if (max !== null && num > max) return false;
        return true;
    }
};

// 导出到全局作用域
window.YunKong = YunKong;
window.FormValidator = FormValidator;