import { useEffect, useState, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { analyzePhotos } from '../services/api';

const steps = [
    "正在连接 Google Gemini 大脑...",
    "正在提取面部 106 个特征点...",
    "正在比对遗传相似度...",
    "正在生成基因分析报告..."
];

export default function Analyze() {
    const navigate = useNavigate();
    const location = useLocation();
    const [currentStep, setCurrentStep] = useState(0); // 恢复定义
    const [error, setError] = useState(null);
    const analyzeCalled = useRef(false);
    const pollIntervalRef = useRef(null); // 新增 Ref 追踪轮询定时器

    useEffect(() => {
        // ... (keep existing useEffect logic but replace alert with setError) ...
        const code = localStorage.getItem('active_code');
        let images = location.state?.images;

        if (!images) {
            const stored = localStorage.getItem('upload_images');
            if (stored) {
                try { images = JSON.parse(stored); } catch (e) { }
            }
        }

        if (!code || !images) {
            navigate('/');
            return;
        }

        const doAnalyze = async () => {
            if (analyzeCalled.current) return;
            analyzeCalled.current = true;

            try {
                // 如果您想增加一点延迟效果，可以在这里加 await new Promise(r => setTimeout(r, 2000));
                await analyzePhotos(code, images);

                setTimeout(() => {
                    navigate('/result', { state: { images } });
                }, 1000);
            } catch (e) {
                console.error('分析失败:', e);

                // 1. 检测是否是"重复分析"（已完成）
                const isDuplicate = e.message.includes('禁止重复分析') || e.message.includes('已使用') || e.message.includes('已生成');

                // 2. 检测是否是"正在进行"（并发请求）
                const isProcessing = e.message.includes('409') || e.message.includes('正在进行') || e.message.includes('耐心等待');

                if (isDuplicate) {
                    navigate('/result', { state: { images } });
                } else if (isProcessing) {
                    // 如果正在分析中，进入轮询模式
                    console.log('检测到分析正在进行，开始轮询结果...');

                    // 使用 Ref 存储定时器 ID
                    pollIntervalRef.current = setInterval(async () => {
                        try {
                            const res = await getCachedResult(code);
                            if (res && res.success) {
                                clearInterval(pollIntervalRef.current);
                                navigate('/result', { state: { images } });
                            }
                        } catch (pollErr) {
                            // 忽略轮询错误
                        }


                    }, 3000);

                    // 设置一个 5 分钟的超时保护 (与 Nginx 保持一致)
                    setTimeout(() => {
                        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
                        if (location.pathname.includes('analyze')) {
                            setError('分析请求响应超时，请刷新重试。');
                        }
                    }, 300000);

                } else {
                    let userMsg = "AI 大脑正在开小差，请稍后再试。";
                    if (e.message && (e.message.includes('504') || e.message.includes('503') || e.message.includes('timeout'))) {
                        userMsg = "分析请求超时（算力拥堵），您的兑换码依然有效，请重试。";
                    } else if (e.message && e.message.includes('empty')) {
                        userMsg = "服务器繁忙（AI响应异常），请点击重试。";
                    } else {
                        userMsg = e.message || "未知错误";
                    }
                    setError(userMsg);
                }
            }
        };

        doAnalyze();

        const stepInterval = setInterval(() => {
            setCurrentStep(prev => {
                if (prev < steps.length - 1) return prev + 1;
                return prev;
            });
        }, 1200);

        // 关键修复：组件卸载时，同时清理 步骤动画定时器 和 轮询定时器
        return () => {
            clearInterval(stepInterval);
            if (pollIntervalRef.current) {
                console.log('Cleaning up poll interval');
                clearInterval(pollIntervalRef.current);
            }
        };
    }, [navigate, location.state, location.pathname]); // 依赖项可能需要微调，但通常 navigate 足够

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-6">
                <div className="w-full max-w-sm glass-card rounded-3xl p-8 text-center">
                    <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6 border border-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.2)]">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-red-500 w-8 h-8"><circle cx="12" cy="12" r="10" /><line x1="12" x2="12" y1="8" y2="12" /><line x1="12" x2="12.01" y1="16" y2="16" /></svg>
                    </div>
                    <h3 className="text-xl font-bold text-white mb-3 tracking-wide">分析中断</h3>
                    <p className="text-white/60 mb-8 text-sm leading-relaxed font-medium">
                        {error}
                    </p>
                    <button
                        onClick={() => navigate('/upload')}
                        className="w-full py-3.5 bg-white text-black font-semibold rounded-full hover:bg-gray-100 transition-all active:scale-95 shadow-lg"
                    >
                        重试 (兑换码有效)
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden p-6">
            {/* 移除背景div，使用全局 */}

            <div className="z-10 flex flex-col items-center w-full max-w-sm">
                {/* Radar/Scan Animation */}
                <div className="relative w-72 h-72 mb-16">
                    <div className="absolute inset-0 border border-white/10 rounded-full bg-white/5 backdrop-blur-sm" />
                    <div className="absolute inset-12 border border-white/5 rounded-full" />
                    <div className="absolute inset-1/2 w-3 h-3 bg-blue-500 rounded-full shadow-[0_0_20px_#3b82f6] z-20" />

                    {/* Scan line */}
                    <motion.div
                        className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-500/10 to-transparent w-full h-1/2 border-b border-blue-500/30"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }}
                        style={{ borderRadius: '50%', transformOrigin: 'bottom center' }}
                    />

                    {/* Particles */}
                    {[...Array(5)].map((_, i) => (
                        <motion.div
                            key={i}
                            className="absolute w-1.5 h-1.5 bg-white/50 rounded-full blur-[1px]"
                            initial={{ opacity: 0, scale: 0, x: 144, y: 144 }}
                            animate={{
                                opacity: [0, 0.8, 0],
                                scale: [0, 1.5],
                                x: 144 + Math.cos(i) * 120,
                                y: 144 + Math.sin(i) * 120
                            }}
                            transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.4 }}
                        />
                    ))}
                </div>

                <div className="h-20 flex flex-col items-center justify-center space-y-3">
                    <span className="w-8 h-8 border-2 border-white/10 border-t-blue-500 rounded-full animate-spin mb-4" />
                    <motion.p
                        key={currentStep}
                        initial={{ opacity: 0, y: 10, filter: 'blur(5px)' }}
                        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                        exit={{ opacity: 0, y: -10, filter: 'blur(5px)' }}
                        className="text-white/90 text-lg font-medium text-center tracking-wide drop-shadow-md"
                    >
                        {steps[currentStep]}
                    </motion.p>
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-slate-900 h-1.5 rounded-full mt-4 overflow-hidden border border-slate-800">
                    <motion.div
                        className="h-full bg-gradient-to-r from-primary to-accent"
                        initial={{ width: "0%" }}
                        animate={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
                        transition={{ duration: 0.5 }}
                    />
                </div>
            </div>
        </div>
    );
}
