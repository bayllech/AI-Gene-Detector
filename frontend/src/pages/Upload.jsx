import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { motion } from 'framer-motion';
import { Upload as UploadIcon, Check, Plus, X } from 'lucide-react';
import { clsx } from 'clsx';

const ImageSlot = ({ label, required, value, onChange, onRemove }) => {
    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                onChange(reader.result);
            };
            reader.readAsDataURL(file);
        }
    };

    return (
        <div className="space-y-3">
            <div className="flex justify-between items-center px-1">
                <span className="text-white/90 font-semibold tracking-wide text-sm">{label}</span>
                {required ? (
                    <span className="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-2 py-1 rounded-md border border-blue-500/20">必填</span>
                ) : (
                    <span className="text-[10px] font-medium text-white/40">选填</span>
                )}
            </div>

            <div className={clsx(
                "relative aspect-[3/4] rounded-3xl border-2 border-dashed transition-all duration-300 overflow-hidden group",
                value
                    ? "border-blue-500/50 shadow-[0_0_20px_rgba(59,130,246,0.15)] bg-slate-900"
                    : "border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20 hover:scale-[1.02] active:scale-[0.98]"
            )}>
                {value ? (
                    <>
                        <img src={value} alt={label} className="w-full h-full object-cover" />
                        <button
                            onClick={onRemove}
                            className="absolute top-3 right-3 p-2 bg-black/40 rounded-full text-white backdrop-blur-md border border-white/10 hover:bg-red-500/80 transition-colors shadow-lg"
                        >
                            <X className="w-4 h-4" />
                        </button>
                        <div className="absolute bottom-3 right-3 p-1.5 bg-green-500 rounded-full shadow-lg shadow-green-500/30">
                            <Check className="w-3.5 h-3.5 text-white stroke-[3px]" />
                        </div>
                    </>
                ) : (
                    <label className="flex flex-col items-center justify-center w-full h-full cursor-pointer">
                        <input type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
                        <div className="p-4 rounded-full bg-white/5 border border-white/10 group-hover:bg-blue-500/10 group-hover:border-blue-500/30 transition-all duration-300 mb-3 shadow-inner">
                            <Plus className="w-6 h-6 text-white/50 group-hover:text-blue-400 transition-colors" />
                        </div>
                        <span className="text-xs font-medium text-white/40 text-center px-4 group-hover:text-white/70 transition-colors">点击上传</span>
                    </label>
                )}
            </div>
        </div>
    );
};

export default function Upload() {
    const navigate = useNavigate();
    const [images, setImages] = useState({
        father: null,
        mother: null,
        child: null
    });

    // 每次进入上传页，清理上一次可能残留的图片数据
    if (!images.child && localStorage.getItem('upload_images')) {
        localStorage.removeItem('upload_images');
    }

    const handleNext = () => {
        try {
            // 使用 Router State 传递图片数据，避免 LocalStorage 容量限制 (通常 5MB)
            console.log('[Upload] Navigating to /analyze with images...');
            navigate('/analyze', { state: { images } });
        } catch (e) {
            console.error('[Upload] Navigation failed:', e);
            alert('跳转失败，请重试');
        }
    };

    const isValid = (images.father || images.mother) && images.child;

    return (
        <div className="min-h-screen p-4 flex flex-col">
            <header className="py-4 text-center">
                <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                    上传照片
                </h2>
                <p className="text-sm text-slate-500 mt-1">请确保五官清晰，无遮挡</p>
            </header>

            <main className="flex-1 max-w-md md:max-w-3xl lg:max-w-4xl mx-auto w-full space-y-6 pb-24">
                <div className="grid grid-cols-2 gap-4 max-w-md mx-auto w-full">
                    <ImageSlot
                        label="父亲"
                        value={images.father}
                        onChange={(v) => setImages(p => ({ ...p, father: v }))}
                        onRemove={() => setImages(p => ({ ...p, father: null }))}
                    />
                    <ImageSlot
                        label="母亲"
                        value={images.mother}
                        onChange={(v) => setImages(p => ({ ...p, mother: v }))}
                        onRemove={() => setImages(p => ({ ...p, mother: null }))}
                    />
                </div>

                <div className="pt-2 max-w-md mx-auto w-full">
                    <ImageSlot
                        label="孩子 (关键)"
                        required
                        value={images.child}
                        onChange={(v) => setImages(p => ({ ...p, child: v }))}
                        onRemove={() => setImages(p => ({ ...p, child: null }))}
                    />
                    <p className="text-xs text-slate-500 mt-2 p-3 bg-slate-900/50 rounded-lg border border-slate-800">
                        💡 提示：孩子照片必须为正脸，尽量不戴眼镜，不要遮挡眉毛。
                    </p>
                </div>
            </main>

            <div className="fixed bottom-0 left-0 right-0 p-4 bg-background/80 backdrop-blur-lg border-t border-slate-800">
                <div className="max-w-md md:max-w-3xl lg:max-w-4xl mx-auto">
                    <Button
                        className="w-full text-lg shadow-lg shadow-primary/20"
                        size="lg"
                        disabled={!isValid}
                        onClick={handleNext}
                    >
                        开始分析
                    </Button>
                </div>
            </div>
        </div>
    );
}
