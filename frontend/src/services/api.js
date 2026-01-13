/**
 * API 服务模块
 * 连接后端 FastAPI 服务
 */

// API 基础地址（开发环境）
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * 通用请求封装
 */
async function request(url, options = {}) {
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
    return request('/api/analyze/result', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${code}`,
        },
    });
};
