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
        <div className="space-y-4">
            <div className="flex justify-between items-center px-2">
                <span className="text-white font-bold text-lg tracking-wide">{label}</span>
                {required ? (
                    <span className="text-xs font-bold text-white bg-blue-600 px-3 py-1 rounded-full shadow-lg shadow-blue-500/30">必填</span>
                ) : (
                    <span className="text-xs font-medium text-white/50 bg-white/10 px-2 py-1 rounded-md">选填</span>
                )}
            </div>

            <div className={clsx(
                "relative aspect-[3/4] rounded-[2rem] border-2 border-dashed transition-all duration-300 overflow-hidden group",
                value
                    ? "border-blue-500/50 shadow-[0_0_30px_rgba(59,130,246,0.2)] bg-slate-900"
                    : "border-white/15 bg-white/5 hover:bg-white/10 hover:border-white/30 hover:scale-[1.02] active:scale-[0.98]"
            )}>
                {value ? (
                    <>
                        <img src={value} alt={label} className="w-full h-full object-cover" />
                        <button
                            onClick={onRemove}
                            className="absolute top-4 right-4 p-2.5 bg-black/60 rounded-full text-white backdrop-blur-md border border-white/20 hover:bg-red-500 hover:border-red-500 transition-all shadow-xl"
                        >
                            <X className="w-5 h-5" />
                        </button>
                        <div className="absolute bottom-4 right-4 p-2 bg-green-500 rounded-full shadow-lg shadow-green-500/40 animate-in zoom-in duration-300">
                            <Check className="w-4 h-4 text-white stroke-[3px]" />
                        </div>
                    </>
                ) : (
                    <label className="flex flex-col items-center justify-center w-full h-full cursor-pointer">
                        <input type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
                        <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center group-hover:bg-blue-500/20 group-hover:border-blue-500/50 transition-all duration-300 mb-4 shadow-inner">
                            <Plus className="w-8 h-8 text-white/40 group-hover:text-blue-400 transition-colors" />
                        </div>
                        <span className="text-sm font-bold text-white/60 text-center px-6 group-hover:text-white transition-colors">点击上传照片</span>
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
        <div className="min-h-screen p-6 flex flex-col pb-32">
            <header className="py-6 text-center space-y-2">
                <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
                    上传家庭成员照片
                </h2>
                <p className="text-white/60 font-medium">请确保五官清晰，无遮挡</p>
            </header>

            <main className="flex-1 max-w-md md:max-w-3xl lg:max-w-4xl mx-auto w-full space-y-8">
                <div className="grid grid-cols-2 gap-5 max-w-md mx-auto w-full">
                    <ImageSlot
                        label="爸爸"
                        value={images.father}
                        onChange={(v) => setImages(p => ({ ...p, father: v }))}
                        onRemove={() => setImages(p => ({ ...p, father: null }))}
                    />
                    <ImageSlot
                        label="妈妈"
                        value={images.mother}
                        onChange={(v) => setImages(p => ({ ...p, mother: v }))}
                        onRemove={() => setImages(p => ({ ...p, mother: null }))}
                    />
                </div>

                <div className="pt-2 max-w-md mx-auto w-full">
                    <ImageSlot
                        label="宝宝 (关键)"
                        required
                        value={images.child}
                        onChange={(v) => setImages(p => ({ ...p, child: v }))}
                        onRemove={() => setImages(p => ({ ...p, child: null }))}
                    />
                    <div className="mt-6 p-4 bg-blue-500/10 rounded-2xl border border-blue-500/20 flex gap-3 items-start">
                        <span className="text-xl">💡</span>
                        <p className="text-sm text-blue-100/90 leading-relaxed font-medium">
                            为获得最准确的分析结果，请上传<span className="text-white font-bold">正脸清晰照片</span>。尽量避免佩戴眼镜或帽子遮挡面部特征。
                        </p>
                    </div>
                </div>
            </main>

            <div className="fixed bottom-0 left-0 right-0 p-6 bg-background/80 backdrop-blur-xl border-t-0 z-20">
                <div className="max-w-md md:max-w-3xl lg:max-w-4xl mx-auto">
                    <Button
                        className="w-full text-lg h-14 rounded-full font-bold shadow-2xl shadow-blue-500/30 border border-white/10"
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
