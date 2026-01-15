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
        <div className="space-y-2">
            <div className="flex justify-between items-center text-sm">
                <span className="text-slate-300 font-medium">{label}</span>
                {required ? (
                    <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded">必填</span>
                ) : (
                    <span className="text-xs text-slate-500">选填</span>
                )}
            </div>

            <div className={clsx(
                "relative aspect-[3/4] rounded-xl border-2 border-dashed transition-all overflow-hidden group",
                value ? "border-primary/50 bg-slate-900" : "border-slate-700 bg-slate-800/50 hover:border-slate-600"
            )}>
                {value ? (
                    <>
                        <img src={value} alt={label} className="w-full h-full object-cover" />
                        <button
                            onClick={onRemove}
                            className="absolute top-2 right-2 p-1.5 bg-black/50 rounded-full text-white backdrop-blur-sm hover:bg-red-500/80 transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                        <div className="absolute bottom-2 right-2 p-1 bg-green-500/80 rounded-full">
                            <Check className="w-3 h-3 text-white" />
                        </div>
                    </>
                ) : (
                    <label className="flex flex-col items-center justify-center w-full h-full cursor-pointer">
                        <input type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
                        <div className="p-3 rounded-full bg-slate-800 group-hover:bg-slate-700 transition-colors mb-2">
                            <Plus className="w-6 h-6 text-slate-400" />
                        </div>
                        <span className="text-xs text-slate-500 text-center px-4">点击上传</span>
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
        // Save to local storage to pass to analyze page (mocking upload)
        localStorage.setItem('upload_images', JSON.stringify(images));
        navigate('/analyze');
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
