/**
 * API 服务模块
 * 连接后端 FastAPI 服务
 */

// API 基础地址
// 生产环境(PROD)下默认为空（使用相对路径，走Nginx反代）
// 开发环境(DEV)下默认为 http://localhost:8000
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000');

/**
 * 通用请求封装
 */
async function request(url, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${url}`, {
            ...options,
            headers: {
                ...options.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: '请求失败' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    } catch (error) {
        // 捕获 verify 429 错误（detail 已在上一步抛出，这里主要是捕获 fetch 本身的网络错误）
        // "Failed to fetch" 是 fetch 在网络不通时的标准报错（TypeError）
        if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
            throw new Error('无法连接到服务器，请检查网络或稍后重试');
        }
        throw error;
    }
}

/**
 * 验证兑换码
 * @param {string} code - 兑换码
 * @param {string} deviceId - 设备指纹
 */
export const verifyCode = async (code, deviceId) => {
    return request('/api/code/verify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code, device_id: deviceId }),
    });
};

/**
 * 上传照片并分析
 * @param {string} code - 兑换码
 * @param {Object} images - 图片对象 { child, father?, mother? }
 */
export const analyzePhotos = async (code, images) => {
    const formData = new FormData();

    // 将 Base64 转换为 Blob
    const base64ToBlob = (base64) => {
        const parts = base64.split(',');
        const mime = parts[0].match(/:(.*?);/)[1];
        const bstr = atob(parts[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        return new Blob([u8arr], { type: mime });
    };

    // 添加孩子照片（必填）
    if (images.child) {
        formData.append('child', base64ToBlob(images.child), 'child.jpg');
    }

    // 添加父亲照片（选填）
    if (images.father) {
        formData.append('father', base64ToBlob(images.father), 'father.jpg');
    }

    // 添加母亲照片（选填）
    if (images.mother) {
        formData.append('mother', base64ToBlob(images.mother), 'mother.jpg');
    }

    return request('/api/analyze', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${code}`,
        },
        body: formData,
    });
};

/**
 * 获取缓存的分析结果
 * @param {string} code - 兑换码
 */
export const getCachedResult = async (code) => {
    // 增加时间戳防止浏览器缓存 GET 请求
    return request(`/api/analyze/result?_t=${Date.now()}`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${code}`,
        },
    });
};
/**
 * 检查兑换码状态
 * @param {string} code - 兑换码
 */
export const checkCodeStatus = async (code) => {
    return request('/api/code/check-status', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${code}`,
        },
    });
};
