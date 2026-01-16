import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { verifyCode } from '../services/api';
import FingerprintJS from '@fingerprintjs/fingerprintjs';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Dna, ArrowRight } from 'lucide-react';

export default function Home() {
    const [code, setCode] = useState('');
    const [loading, setLoading] = useState(false);
    const [agreed, setAgreed] = useState(false); // 新增状态


    const [error, setError] = useState('');
    const [fpHash, setFpHash] = useState('');
    const navigate = useNavigate();
    const location = useLocation(); // 新增 Hook

    useEffect(() => {
        // 1. 检查是否有跳转传过来的错误信息 (例如从 Result 页跳回)
        if (location.state?.error) {
            setError(location.state.error);
            // 清除 state，防止刷新页面时错误信息依然存在
            window.history.replaceState({}, document.title);
        }

        // Initialize fingerprint
        const setFp = async () => {
            const fp = await FingerprintJS.load();
            const result = await fp.get();
            setFpHash(result.visitorId);
        };
        setFp();

        // Check local history
        const savedCode = localStorage.getItem('active_code');

        // 清理旧的遗留数据（防止串号干扰）
        localStorage.removeItem('analysis_result');

        if (savedCode) {
            // Optional: Auto redirect or show message
        }
    }, [location]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!code) return;

        if (!agreed) {
            setError('请先阅读并勾选用户协议');
            return;
        }

        setLoading(true);
        setError('');

        try {
            if (!fpHash) {
                throw new Error('正在初始化安全组件，请稍后...');
            }
            const response = await verifyCode(code, fpHash);
            localStorage.setItem('active_code', code);

            // 如果已有结果，直接跳转到结果页
            if (response.has_result) {
                navigate('/result');
            } else {
                navigate('/upload');
            }
        } catch (err) {
            setError(err.message || '验证失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden">
            {/* 移除旧背景，使用全局流体背景 */}

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="z-10 w-full max-w-sm md:max-w-md space-y-8 flex flex-col items-center"
            >
                <div className="text-center space-y-3">
                    <div className="flex justify-center mb-8">
                        <div className="p-5 rounded-full glass-card">
                            <Dna className="w-14 h-14 text-white drop-shadow-[0_0_15px_rgba(41,151,255,0.5)]" />
                        </div>
                    </div>
                    <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight drop-shadow-md">
                        AI娱乐 - 宝宝像谁
                    </h1>
                    <p className="text-white/60 text-sm md:text-base font-medium tracking-wide">
                        上传全家福，一键揭秘面部特征密码
                    </p>
                </div>

                {/* Glass Card Container */}
                <div className="glass-card p-6 md:p-8 rounded-3xl w-full">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-white/80 ml-1">
                                兑换激活码
                            </label>
                            <Input
                                placeholder="输入您的专属CDK"
                                value={code}
                                onChange={(e) => setCode(e.target.value)}
                                className="text-center text-lg tracking-widest uppercase font-mono glass-input"
                            />
                        </div>

                        {error && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className="text-red-300 text-sm text-center bg-red-500/10 border border-red-500/20 p-3 rounded-xl backdrop-blur-md"
                            >
                                {error}
                            </motion.div>
                        )}

                        <Button
                            type="submit"
                            className="w-full text-lg h-14 font-semibold shadow-xl shadow-blue-500/20"
                            disabled={loading || !code}
                        >
                            {loading ? (
                                <span className="flex items-center gap-2">
                                    <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    <span>验证中...</span>
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    开始分析 <ArrowRight className="w-5 h-5" />
                                </span>
                            )}
                        </Button>

                        <div className="flex items-start gap-2 pt-2">
                            <input
                                type="checkbox"
                                id="terms"
                                className="mt-1 bg-transparent border-slate-600 rounded cursor-pointer accent-primary"
                                checked={agreed}
                                onChange={(e) => setAgreed(e.target.checked)}
                            />
                            <label htmlFor="terms" className="text-xs text-slate-500 leading-tight cursor-pointer select-none">
                                我已阅读并同意：本结果仅供娱乐，AI 分析受光线影响，无法退款。
                            </label>
                        </div>
                    </form>
                </div>

                <div className="pt-6 pb-2 text-center">
                    <p className="text-sm text-white/60 font-medium tracking-wide">
                        需要兑换码，请联系：<span className="text-white font-bold select-all">wxbeier669</span>
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
