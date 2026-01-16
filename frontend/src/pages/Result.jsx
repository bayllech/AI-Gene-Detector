import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Download, RefreshCw, AlertCircle, Share2, Loader2 } from 'lucide-react';
import { getCachedResult } from '../services/api';

export default function Result() {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const navigate = useNavigate();
    const location = useLocation();
    const [resultData, setResultData] = useState(null);
    const [childImage, setChildImage] = useState(null);

    useEffect(() => {
        const fetchResult = async () => {
            const activeCode = localStorage.getItem('active_code');

            // 1. 尝试从 State 获取图片 (最高优先级，无网络延迟)
            let imagesObj = location.state?.images;

            // 2. 尝试本地兼容 (次优) - 注意我们稍后可能会废弃这个，因为 quota 问题
            if (!imagesObj) {
                const stored = localStorage.getItem('upload_images');
                if (stored) {
                    try { imagesObj = JSON.parse(stored); } catch (e) { }
                }
            }

            if (!activeCode) {
                navigate('/');
                return;
            }

            try {
                console.log('Fetching result for code:', activeCode);
                const result = await getCachedResult(activeCode);
                console.log('Result received:', result);

                if (result.success) {
                    setResultData(result);

                    // 3. 核心修复：如果本地没图，尝试用后端返回的图片 URL
                    if (!imagesObj && result.images && result.images.child) {
                        console.log('Using remote images from backend:', result.images);
                        imagesObj = result.images;
                    }

                    // 如果最终还是没图 (本地没了 + 后端也没存)，那就真的没办法了
                    if (!imagesObj) {
                        console.error('No images found (local or remote)');
                        localStorage.removeItem('active_code');
                        // 改为带错误信息跳转回首页，由首页显示友好提示
                        navigate('/', { state: { error: '图片数据已失效，请重新验证。' } });
                        return;
                    }

                    // 加载图片 (支持 Base64 和 URL)
                    const img = new Image();
                    img.src = imagesObj.child;
                    img.crossOrigin = "anonymous"; // 必须加，否则 canvas 跨域报错
                    img.onload = () => {
                        setChildImage(img);
                    };
                    img.onerror = (e) => {
                        console.error('Failed to load child image:', e);
                        alert('图片加载失败');
                    };
                } else {
                    // 后端说没有结果（可能被删了）
                    navigate('/upload');
                }
            } catch (error) {
                console.error('Failed to fetch result:', error);
                navigate('/');
            }
        };

        fetchResult();
    }, [navigate]);

    // Redraw canvas on window resize or data change
    // Redraw canvas on window resize or data change
    useEffect(() => {
        const handleDraw = () => {
            if (childImage && resultData) {
                const canvas = canvasRef.current;
                const container = containerRef.current;
                if (canvas && container) {
                    const dpr = window.devicePixelRatio || 1;
                    const containerWidth = container.clientWidth;
                    const scale = containerWidth / childImage.width;
                    const canvasHeight = childImage.height * scale;

                    canvas.width = containerWidth * dpr;
                    canvas.height = canvasHeight * dpr;
                    canvas.style.width = `${containerWidth}px`;
                    canvas.style.height = `${canvasHeight}px`;

                    const ctx = canvas.getContext('2d');
                    ctx.scale(dpr, dpr);
                    // The scaling and canvas dimensions are now managed within drawCanvas
                    drawCanvas(ctx, childImage, containerWidth, canvasHeight, resultData);
                }
            }
        };

        // Initial draw
        handleDraw();

        // Resize listener
        window.addEventListener('resize', handleDraw);
        return () => window.removeEventListener('resize', handleDraw);
    }, [childImage, resultData]);


    const drawCanvas = (ctx, img, containerWidth, initialHeight, analysisResult) => {
        const rawResults = analysisResult?.analysis_results || [];
        if (!rawResults.length) return;

        // -------------------------------------------------
        // 1. 数据排序与分组 (Fixed Slots Strategy)
        // -------------------------------------------------
        // 定义左右列和底部的固定顺序
        const LEFT_SLOTS = ['眉毛', '鼻子', '脸型'];
        const RIGHT_SLOTS = ['眼睛', '嘴巴', '头型'];
        const BOTTOM_SLOTS = ['总结'];

        const sortedResults = [];

        // 辅助函数：根据名称找数据
        const findPart = (keywords) => rawResults.find(r => keywords.some(k => r.part.includes(k)));

        LEFT_SLOTS.forEach(key => {
            const item = findPart([key]);
            if (item) sortedResults.push({ ...item, _layout: 'left' });
        });
        RIGHT_SLOTS.forEach(key => {
            const item = findPart([key]);
            if (item) sortedResults.push({ ...item, _layout: 'right' });
        });
        BOTTOM_SLOTS.forEach(key => {
            const item = findPart([key]);
            if (item) sortedResults.push({ ...item, _layout: 'bottom' });
        });

        const results = sortedResults;

        // -------------------------------------------------
        // 2. 颜色定义
        // -------------------------------------------------
        const palette = [
            '#38bdf8', '#a78bfa', '#f472b6', '#2dd4bf', '#fbbf24', '#f87171', '#a3e635'
        ];

        // -------------------------------------------------
        // 3. 布局计算
        // -------------------------------------------------
        const imgRatio = img.width / img.height;
        const drawWidth = containerWidth;
        const drawHeight = containerWidth / imgRatio;

        // 读取脸部中心点（鼻尖位置）和脸部宽度
        const center = analysisResult?.face_center || { x: 50, y: 40 };
        const faceWidthPct = analysisResult?.face_width || 40;

        // 将百分比转为像素
        const faceCenterX = (center.x / 100) * drawWidth;
        const faceCenterY = (center.y / 100) * drawHeight;
        const faceW = (faceWidthPct / 100) * drawWidth;

        // 解剖学比例表 (基于脸部中心点)
        const ANATOMY = {
            '头型': { yOffset: -0.70, xOffset: 0.25 },
            '眉毛': { yOffset: -0.35, xOffset: -0.20 },
            '眼睛': { yOffset: -0.22, xOffset: 0.25 },
            '鼻子': { yOffset: 0.00, xOffset: -0.08 },
            '嘴巴': { yOffset: 0.25, xOffset: 0.18 },
            '脸型': { yOffset: 0.45, xOffset: -0.25 },
        };

        const padding = 20;
        const channelWidth = 40;
        const cardGap = 12;
        const sectionGap = 50;

        const availableWidth = containerWidth - (padding * 2) - (channelWidth * 2);
        const colCardWidth = (availableWidth - cardGap) / 2;

        // --- 动态高度计算 ---
        // 辅助：计算卡片所需高度
        const calculateCardHeight = (item, w, isSummary) => {
            const indent = isSummary ? 20 : 15;
            const maxW = w - (indent * 2);

            // 1. 头部高度计算 (模拟 Header 绘制逻辑)
            let extraHeaderHeight = 0;
            if (!isSummary) {
                ctx.font = 'bold 15px Inter, system-ui';
                const partW = ctx.measureText(item.part).width;
                const tagX = w - 54 - indent; // Tag Width 54 (simplified)

                // 百分比碰撞检测
                const percentStartX = indent + partW + 5 + indent; // Relative X + indent
                // Note: logic in drawCard uses absolute X, here we simulate relative
                // tagLeftX relative to card = w - 54 - indent
                const tagLeftX = w - 54 - indent;
                const percentTextStartX = indent + partW + 5;
                const percentW = 35;

                if ((percentTextStartX + percentW) > (tagLeftX - 5)) {
                    extraHeaderHeight = 16;
                }
            }

            const topSectionHeight = (isSummary ? 32 : 26) + extraHeaderHeight;

            // 2. 描述文字高度计算
            ctx.font = isSummary ? '13px Inter, system-ui' : '11px Inter, system-ui';
            const lineHeight = isSummary ? 22 : 16;
            const text = item.description;
            let lineCount = 1;
            let line = '';

            for (const char of text) {
                if (ctx.measureText(line + char).width < maxW) {
                    line += char;
                } else {
                    line = char;
                    lineCount++;
                }
            }

            const textBlockHeight = lineCount * lineHeight;
            const bottomPadding = 15;
            const topPadding = 14;

            return topPadding + topSectionHeight + textBlockHeight + bottomPadding;
        };

        // 计算每一行的高度（取左右最大值）
        const rowHeights = [];
        const leftItems = results.filter(r => r._layout === 'left');
        const rightItems = results.filter(r => r._layout === 'right');
        const mainRows = Math.max(leftItems.length, rightItems.length);

        for (let i = 0; i < mainRows; i++) {
            const leftH = leftItems[i] ? calculateCardHeight(leftItems[i], colCardWidth, false) : 0;
            const rightH = rightItems[i] ? calculateCardHeight(rightItems[i], colCardWidth, false) : 0;
            rowHeights.push(Math.max(leftH, rightH, 80)); // 最小高度 80
        }

        // 计算总结卡片高度
        const summaryItem = results.find(r => r._layout === 'bottom');
        const summaryH = summaryItem
            ? calculateCardHeight(summaryItem, availableWidth, true)
            : 0;

        // 计算总高度
        const dataSectionHeight =
            rowHeights.reduce((a, b) => a + b + cardGap, 0) +
            (summaryH > 0 ? summaryH + cardGap : 0) +
            padding;

        const totalHeight = drawHeight + sectionGap + dataSectionHeight;

        // Canvas Resize
        const canvas = ctx.canvas;
        const dpr = window.devicePixelRatio || 1;
        if (canvas.height !== totalHeight * dpr) {
            canvas.width = containerWidth * dpr;
            canvas.height = totalHeight * dpr;
            canvas.style.height = `${totalHeight}px`;
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.scale(dpr, dpr);
        }

        // -------------------------------------------------
        // 4. 绘制背景与图片
        // -------------------------------------------------
        ctx.clearRect(0, 0, containerWidth, totalHeight);
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, containerWidth, totalHeight);
        ctx.drawImage(img, 0, 0, drawWidth, drawHeight);

        const gradient = ctx.createLinearGradient(0, drawHeight - 150, 0, drawHeight);
        gradient.addColorStop(0, 'rgba(15, 23, 42, 0)');
        gradient.addColorStop(0.5, 'rgba(15, 23, 42, 0.8)');
        gradient.addColorStop(1, '#0f172a');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, drawHeight - 150, drawWidth, 150);

        // [DEBUG] 绘制脸部中心点（鼻尖）
        // [DEBUG] 绘制脸部中心点（鼻尖）
        /*
        ctx.save();
        ctx.strokeStyle = '#fbbf24';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 20, faceCenterY);
        ctx.lineTo(faceCenterX + 20, faceCenterY);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(faceCenterX, faceCenterY - 20);
        ctx.lineTo(faceCenterX, faceCenterY + 20);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(faceCenterX, faceCenterY, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#fbbf24';
        ctx.fill();
        ctx.restore();
        */

        // -------------------------------------------------
        // 5. 绘制循环
        // -------------------------------------------------

        // 预计算每行的 Y 坐标起始点
        let currentRowY = drawHeight + sectionGap;

        // 绘制普通行
        for (let i = 0; i < mainRows; i++) {
            const h = rowHeights[i];

            // 左边卡片
            if (leftItems[i]) {
                const item = leftItems[i];
                const cardX = padding + channelWidth;
                drawConnectionAndCard(ctx, item, cardX, currentRowY, colCardWidth, h, faceCenterX, faceCenterY, faceW, true, i, containerWidth, drawHeight, sectionGap);
            }

            // 右边卡片
            if (rightItems[i]) {
                const item = rightItems[i];
                const cardX = padding + channelWidth + colCardWidth + cardGap;
                drawConnectionAndCard(ctx, item, cardX, currentRowY, colCardWidth, h, faceCenterX, faceCenterY, faceW, false, i, containerWidth, drawHeight, sectionGap);
            }

            currentRowY += h + cardGap;
        }

        // 绘制总结卡片
        if (summaryItem) {
            const cardX = padding + channelWidth;
            const color = palette[results.findIndex(r => r.part === '总结') % palette.length];
            drawCard(ctx, summaryItem, cardX, currentRowY, availableWidth, summaryH, color, true);
        }
    };

    // 辅助：绘制连线和卡片 (封装之前的逻辑)
    const drawConnectionAndCard = (ctx, item, cardX, cardY, w, h, faceCenterX, faceCenterY, faceW, isLeft, rowIndex, containerWidth, drawHeight, sectionGap) => {
        const palette = [
            '#38bdf8', '#a78bfa', '#f472b6', '#2dd4bf', '#fbbf24', '#f87171', '#a3e635'
        ];
        // 随便找个 index 算颜色，或者传入 index。这里简化，重新查找 index
        // 实际上 drawCanvas 上下文有 index，但这里重构了循环。
        // 简单哈希一下 part name 拿颜色
        const colorIdx = (item.part.charCodeAt(0) + item.part.length) % palette.length;
        const color = palette[colorIdx];

        // --- 坐标计算 (基于脸部中心点) ---
        const ANATOMY = {
            '头型': { yOffset: -0.70, xOffset: 0.25 },
            '眉毛': { yOffset: -0.35, xOffset: -0.20 },
            '眼睛': { yOffset: -0.22, xOffset: 0.25 },
            '鼻子': { yOffset: 0.00, xOffset: -0.08 },
            '嘴巴': { yOffset: 0.25, xOffset: 0.18 },
            '脸型': { yOffset: 0.45, xOffset: -0.25 },
        };
        const anatomy = ANATOMY[item.part] || { yOffset: 0, xOffset: 0 };

        // Y 坐标：脸部中心（鼻尖）+ 垂直偏移 * 脸宽
        const faceY = faceCenterY + faceW * anatomy.yOffset;
        let faceX = faceCenterX + faceW * anatomy.xOffset;

        // 微小随机抖动 (防止完全重叠)
        const seed = (rowIndex * 17) % 5 - 2;
        faceX += seed;

        // 绘制路径 (Edge Routing)
        ctx.beginPath();
        ctx.moveTo(faceX, faceY);

        // 通道计算
        const channelOffset = (rowIndex * 8) % 32;
        const padding = 20;
        const trackX = isLeft
            ? padding + 10 + channelOffset
            : containerWidth - padding - 10 - channelOffset;

        // 拐点
        const elbowY = drawHeight + (sectionGap * 0.2) + (rowIndex * 8);

        // 1. 飞出
        ctx.bezierCurveTo(
            isLeft ? faceX - 80 : faceX + 80, faceY,
            trackX, Math.min(faceY + 80, elbowY - 40),
            trackX, elbowY
        );
        // 2. 下落
        const cardEnterY = cardY + 28;
        ctx.lineTo(trackX, cardEnterY - 15);
        // 3. 切入
        const entryX = isLeft ? cardX : cardX + w;
        ctx.quadraticCurveTo(trackX, cardEnterY, entryX, cardEnterY);

        // 描边
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.lineCap = 'round';
        ctx.shadowColor = color;
        ctx.shadowBlur = 6;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // 端点 & 圆点...
        ctx.beginPath();
        ctx.arc(faceX, faceY, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#fff';
        ctx.fill();
        ctx.beginPath();
        ctx.arc(faceX, faceY, 5, 0, Math.PI * 2);
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(entryX, cardEnterY, 2, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        // 绘制卡片
        drawCard(ctx, item, cardX, cardY, w, h, color, false);
    };


    // 辅助：绘制卡片内容 (增加 isSummary 模式)
    const drawCard = (ctx, item, x, y, w, h, color, isSummary) => {
        ctx.save();

        // 背景
        ctx.fillStyle = 'rgba(30, 41, 59, 0.6)';
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(x, y, w, h, 12);
        else ctx.rect(x, y, w, h);
        ctx.fill();

        // 侧边条 (普通卡片才有)
        if (!isSummary) {
            ctx.fillStyle = color;
            ctx.fillRect(x, y + 16, 3, h - 32);
        }

        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';

        // --- 头部信息 ---
        const isDad = item.similar_to === 'Father';
        const indent = isSummary ? 20 : 15;
        const topY = y + 14;

        // 像谁标签 (先计算位置，防止遮挡)
        const whoText = isDad ? '像爸爸' : '像妈妈';
        const tagW = 54;
        const tagH = 20;
        const tagX = x + w - tagW - indent;

        // 绘制标签背景
        ctx.fillStyle = isDad ? 'rgba(59, 130, 246, 0.2)' : 'rgba(236, 72, 153, 0.2)';
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(tagX, topY - 1, tagW, tagH, 4);
        else ctx.fillRect(tagX, topY - 1, tagW, tagH);
        ctx.fill();

        // 绘制标签文字
        ctx.font = '11px Inter, system-ui';
        ctx.fillStyle = isDad ? '#60a5fa' : '#f472b6';
        ctx.textAlign = 'center';
        ctx.fillText(whoText, tagX + tagW / 2, topY + 4);

        // 绘制部位名称
        ctx.textAlign = 'left';
        ctx.font = 'bold 15px Inter, system-ui';
        ctx.fillStyle = '#fff';
        const partText = item.part;
        ctx.fillText(partText, x + indent, topY);

        const partW = ctx.measureText(partText).width;

        // 百分比 (智能避让逻辑)
        // 计算标签左侧的 x 坐标
        const tagLeftX = tagX;
        // 计算百分比数字原本应该开始的 x 坐标
        const percentStartX = x + indent + partW + 5;
        // 估算百分比文字的宽度 (假设大概 30px)
        const percentW = 35;

        // 检查是否会重叠 (保留 5px 缓冲)
        const isOverlap = (percentStartX + percentW) > (tagLeftX - 5);

        ctx.fillStyle = color;
        let extraHeaderHeight = 0;

        if (isOverlap) {
            // 空间不足，换行显示百分比
            ctx.font = 'bold 12px Inter, system-ui';
            ctx.fillText(`${item.similarity_score}%`, x + indent, topY + 16);
            extraHeaderHeight = 16;
        } else {
            // 空间充足，同一行显示
            if (tagLeftX - percentStartX < 40) {
                // 空间有些紧凑但没完全重叠，稍微缩小字体
                ctx.font = 'bold 13px Inter, system-ui';
            }
            ctx.fillText(` ${item.similarity_score}%`, x + indent + partW, topY);
        }

        // --- 描述文字 ---
        ctx.textAlign = 'left';
        ctx.fillStyle = isSummary ? '#e2e8f0' : '#cbd5e1';
        ctx.font = isSummary ? '13px Inter, system-ui' : '11px Inter, system-ui';

        // 动态调整描述文字的起始 Y 坐标
        const descY = topY + (isSummary ? 32 : 26) + extraHeaderHeight;
        const maxW = w - (indent * 2);
        const lineHeight = isSummary ? 22 : 16;

        const text = item.description;
        let line = '';
        let currentY = descY;

        // 多行换行逻辑
        for (const char of text) {
            if (ctx.measureText(line + char).width < maxW) {
                line += char;
            } else {
                ctx.fillText(line, x + indent, currentY);
                line = char;
                currentY += lineHeight;
                if (currentY > y + h - 15) break;
            }
        }
        ctx.fillText(line, x + indent, currentY);

        ctx.restore();
    };

    const handleSave = () => {
        if (canvasRef.current) {
            const link = document.createElement('a');
            link.download = `gene-analysis-${Date.now()}.png`;
            link.href = canvasRef.current.toDataURL();
            link.click();
        }
    };

    return (
        <div className="min-h-screen bg-background pb-20">
            <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-slate-800">
                <div className="w-full max-w-md md:max-w-3xl lg:max-w-4xl mx-auto p-4 flex justify-between items-center transition-all duration-300">
                    <h1 className="font-bold text-lg">分析报告</h1>
                    <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
                        <RefreshCw className="w-4 h-4 mr-1" /> 重测
                    </Button>
                </div>
            </div>

            <div className="w-full max-w-md md:max-w-3xl lg:max-w-4xl mx-auto p-4 transition-all duration-300">
                <div className="relative rounded-2xl overflow-hidden shadow-2xl shadow-primary/10 border border-slate-800 bg-slate-900 min-h-[400px]" ref={containerRef}>
                    <canvas ref={canvasRef} className="block w-full" />
                    {!childImage && (
                        <div className="absolute inset-0 flex items-center justify-center text-slate-500">
                            加载结果中...
                        </div>
                    )}
                </div>

                <div className="mt-4 p-4 bg-slate-900/50 rounded-xl border border-slate-800 text-xs text-slate-400 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-500" />
                    <p>
                        <span className="text-red-400 font-bold block mb-1">⚠️ 重要提示：请立即保存结果！</span>
                        为保护极度隐私，本结果为<span className="text-white font-bold">一次性阅后即焚</span>。
                        <br />
                        页面关闭或输入新兑换码后，当前结果将<span className="text-red-400">永久销毁且无法找回</span>。
                    </p>
                </div>
            </div>

            <div className="fixed bottom-0 left-0 right-0 bg-background/80 backdrop-blur-lg border-t border-slate-800">
                <div className="w-full max-w-md md:max-w-3xl lg:max-w-4xl mx-auto p-4 flex gap-3 transition-all duration-300">
                    <Button className="flex-1 text-base" onClick={handleSave}>
                        <Download className="w-4 h-4 mr-2" /> 保存相册
                    </Button>
                </div>
            </div>
        </div>
    );
}
