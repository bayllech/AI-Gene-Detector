import React from 'react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

const Button = React.forwardRef(({ className, variant = 'primary', size = 'default', ...props }, ref) => {
    const variants = {
        primary: 'bg-gradient-to-r from-primary to-accent hover:from-blue-600 hover:to-cyan-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)]',
        outline: 'border border-primary/50 text-primary hover:bg-primary/10',
        ghost: 'hover:bg-slate-800 text-slate-300',
    };

    const sizes = {
        default: 'h-12 px-6 py-2',
        sm: 'h-9 px-3',
        lg: 'h-14 px-8 text-lg',
    };

    return (
        <motion.button
            whileTap={{ scale: 0.95 }}
            whileHover={{ scale: 1.02 }}
            ref={ref}
            className={cn(
                'inline-flex items-center justify-center rounded-xl font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
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
