import React from 'react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

const Button = React.forwardRef(({ className, variant = 'primary', size = 'default', ...props }, ref) => {
    const variants = {
        primary: 'bg-[#007AFF] hover:bg-[#0071e3] text-white shadow-lg shadow-blue-500/20 border border-blue-400/20 active:shadow-none',
        outline: 'bg-white/5 border border-white/20 text-white hover:bg-white/10 backdrop-blur-md',
        ghost: 'hover:bg-white/5 text-white/70 hover:text-white',
        destructive: 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/20',
    };

    const sizes = {
        default: 'h-12 px-6 text-base',
        sm: 'h-8 px-4 text-xs',
        lg: 'h-14 px-8 text-lg font-semibold tracking-wide',
        icon: 'h-10 w-10 p-0',
    };

    return (
        <motion.button
            whileTap={{ scale: 0.96 }}
            whileHover={{ scale: 1.02 }}
            ref={ref}
            className={cn(
                'inline-flex items-center justify-center rounded-full transition-all duration-300 disabled:opacity-50 disabled:pointer-events-none',
                variants[variant],
                sizes[size],
                className
            )}
            {...props}
        />
    );
});
Button.displayName = 'Button';

export { Button };
