import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
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
    const [currentStep, setCurrentStep] = useState(0);

    const analyzeCalled = useRef(false);

    useEffect(() => {
        // Start analysis
        const code = localStorage.getItem('active_code');
        const storedImages = localStorage.getItem('upload_images');

        if (!code || !storedImages) {
            navigate('/');
            return;
        }

        const images = JSON.parse(storedImages);

        const doAnalyze = async () => {
            if (analyzeCalled.current) return;
            analyzeCalled.current = true;

            try {
                const result = await analyzePhotos(code, images);
                // 结果直接存入后端，不再前端 localStorage 缓存，防止多账号串号问题
                // localStorage.setItem('analysis_result', JSON.stringify(result));

                // Wait for steps to finish visually
                setTimeout(() => {
                    navigate('/result');
                }, 1000);
            } catch (e) {
                console.error('分析失败:', e);

                // 【修复逻辑】如果错误提示包含"禁止重复分析"，说明结果已生成
                // 此时不应该踢回首页，而应该直接跳转结果页
                const isDuplicate = e.message.includes('禁止重复分析') || e.message.includes('已使用');

                if (isDuplicate) {
                    // alert('检测到结果已生成，正在跳转结果页...');
                    navigate('/result');
                } else {
                    alert(`分析失败: ${e.message || '请重试'}`);
                    navigate('/');
                }
            }
        };

        doAnalyze();

        // Step animation logic
        const interval = setInterval(() => {
            setCurrentStep(prev => {
                if (prev < steps.length - 1) return prev + 1;
                return prev;
            });
        }, 1200);

        return () => clearInterval(interval);
    }, [navigate]);

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-black relative overflow-hidden p-6">
            <div className="absolute inset-0 z-0">
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[80vw] max-w-[800px] h-[80vw] max-h-[800px] bg-primary/10 rounded-full blur-[100px] animate-pulse-slow" />
            </div>

            <div className="z-10 flex flex-col items-center w-full max-w-sm">
                {/* Radar/Scan Animation */}
                <div className="relative w-64 h-64 mb-12">
                    <div className="absolute inset-0 border-2 border-slate-800 rounded-full" />
                    <div className="absolute inset-4 border border-slate-700/50 rounded-full" />
                    <div className="absolute inset-1/2 w-2 h-2 bg-primary rounded-full shadow-[0_0_20px_#3b82f6]" />

                    {/* Scan line */}
                    <motion.div
                        className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/20 to-transparent w-full h-1/2 border-b-2 border-primary/50"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                        style={{ borderRadius: '50%', transformOrigin: 'bottom center' }}
                    />

                    {/* Particles */}
                    {[...Array(5)].map((_, i) => (
                        <motion.div
                            key={i}
                            className="absolute w-1 h-1 bg-accent rounded-full"
                            initial={{ opacity: 0, scale: 0, x: 128, y: 128 }}
                            animate={{
                                opacity: [0, 1, 0],
                                scale: [0, 1.5],
                                x: 128 + Math.cos(i) * 100,
                                y: 128 + Math.sin(i) * 100
                            }}
                            transition={{ duration: 2, repeat: Infinity, delay: i * 0.4 }}
                        />
                    ))}
                </div>

                <div className="h-16 flex items-center justify-center">
                    <motion.p
                        key={currentStep}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-primary font-mono text-center tracking-wide"
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
