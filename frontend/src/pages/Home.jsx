import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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

    useEffect(() => {
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
    }, []);

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
            {/* Background Effects */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[100px]" />
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-secondary/20 rounded-full blur-[100px]" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="z-10 w-full max-w-md md:max-w-3xl lg:max-w-4xl space-y-8 flex flex-col items-center"
            >
                <div className="text-center space-y-2">
                    <div className="flex justify-center mb-6">
                        <div className="p-4 rounded-full bg-surface border border-slate-700 shadow-2xl shadow-primary/20">
                            <Dna className="w-12 h-12 text-primary" />
                        </div>
                    </div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                        AI 亲子基因探测
                    </h1>
                    <p className="text-slate-400">
                        上传照片，探索孩子更像谁
                    </p>
                </div>

                {/* Demo Cards (Simplified for MVP) */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-surface/50 p-2 rounded-lg border border-slate-700/50 backdrop-blur-sm">
                        <div className="aspect-[3/4] bg-slate-800 rounded-md mb-2 overflow-hidden relative">
                            <img src="https://images.unsplash.com/photo-1511895426328-dc8714191300?w=300&q=80" alt="Father" className="object-cover w-full h-full opacity-70" />
                        </div>
                        <div className="text-[10px] text-center text-slate-400">父系特征分析</div>
                    </div>
                    <div className="bg-surface/50 p-2 rounded-lg border border-slate-700/50 backdrop-blur-sm">
                        <div className="aspect-[3/4] bg-slate-800 rounded-md mb-2 overflow-hidden relative">
                            <img src="https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=300&q=80" alt="Child" className="object-cover w-full h-full opacity-70" />
                            {/* Overlay lines simulation */}
                            <svg className="absolute inset-0 w-full h-full">
                                <circle cx="50%" cy="40%" r="3" fill="#3b82f6" />
                                <line x1="50%" y1="40%" x2="80%" y2="20%" stroke="#3b82f6" strokeWidth="1" />
                            </svg>
                        </div>
                        <div className="text-[10px] text-center text-slate-400">AI 智能匹配</div>
                    </div>
                </div>

                <div className="bg-surface/80 backdrop-blur-xl p-6 rounded-2xl border border-slate-700 shadow-xl w-full max-w-md">
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-300 ml-1">
                                兑换码
                            </label>
                            <Input
                                placeholder="请输入兑换码"
                                value={code}
                                onChange={(e) => setCode(e.target.value)}
                                className="text-center text-lg tracking-widest uppercase"
                            />
                        </div>

                        {error && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className="text-red-400 text-sm text-center bg-red-900/20 p-2 rounded"
                            >
                                {error}
                            </motion.div>
                        )}

                        <Button
                            type="submit"
                            className="w-full text-lg h-14"
                            disabled={loading || !code}
                        >
                            {loading ? (
                                <span className="flex items-center gap-2">
                                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    验证中...
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    开始 AI 探测 <ArrowRight className="w-5 h-5" />
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
            </motion.div>
        </div>
    );
}
