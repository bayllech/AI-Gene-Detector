import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { checkCodeStatus } from '../services/api';
import { Loader2 } from 'lucide-react';

export default function ProtectedRoute({ children }) {
    const navigate = useNavigate();
    const location = useLocation();
    const [verifying, setVerifying] = useState(true);

    useEffect(() => {
        const verifyStatus = async () => {
            const code = localStorage.getItem('active_code');

            // 1. 本地无码，直接踢回首页
            if (!code) {
                navigate('/', { replace: true });
                return;
            }

            try {
                // 2. 服务端实时状态检查
                const status = await checkCodeStatus(code);

                if (!status.valid) {
                    // 无效或过期
                    localStorage.removeItem('active_code');
                    alert(status.message || '会话已过期，请重新验证');
                    navigate('/', { replace: true });
                    return;
                }

                // 3. 结果页路由守卫
                // 试图访问 /upload 或 /analyze 但已经有结果了 -> 强转 /result
                if (status.has_result && (location.pathname === '/upload' || location.pathname === '/analyze')) {
                    navigate('/result', { replace: true });
                    return;
                }

                // 试图访问 /result 但还没有结果 -> 强转 /upload
                if (!status.has_result && location.pathname === '/result') {
                    navigate('/upload', { replace: true });
                    return;
                }

                // 一切正常
                setVerifying(false);

            } catch (error) {
                // 网络错误或其他异常，视为未授权
                console.error('Auth check failed:', error);
                navigate('/', { replace: true });
            }
        };

        verifyStatus();
    }, [navigate, location.pathname]);

    if (verifying) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background text-slate-400">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    <p className="text-sm">正在验证权限...</p>
                </div>
            </div>
        );
    }

    return children;
}
