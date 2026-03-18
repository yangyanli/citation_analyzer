"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
    id: string;
    message: string;
    type: ToastType;
}

interface ToastContextType {
    showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
    const ctx = useContext(ToastContext);
    if (!ctx) throw new Error("useToast must be used within ToastProvider");
    return ctx;
}

const iconMap = {
    success: CheckCircle,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
};

const colorMap = {
    success: 'bg-emerald-50 dark:bg-emerald-500/15 border-emerald-200 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300',
    error: 'bg-red-50 dark:bg-red-500/15 border-red-200 dark:border-red-500/30 text-red-800 dark:text-red-300',
    warning: 'bg-amber-50 dark:bg-amber-500/15 border-amber-200 dark:border-amber-500/30 text-amber-800 dark:text-amber-300',
    info: 'bg-indigo-50 dark:bg-indigo-500/15 border-indigo-200 dark:border-indigo-500/30 text-indigo-800 dark:text-indigo-300',
};

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const showToast = useCallback((message: string, type: ToastType = 'info') => {
        const id = crypto.randomUUID();
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, 4000);
    }, []);

    const dismiss = (id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    return (
        <ToastContext.Provider value={{ showToast }}>
            {children}
            {/* Toast container */}
            <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
                {toasts.map((toast) => {
                    const Icon = iconMap[toast.type];
                    return (
                        <div
                            key={toast.id}
                            className={`flex items-start gap-2.5 px-4 py-3 rounded-lg border backdrop-blur-sm shadow-lg animate-slide-in ${colorMap[toast.type]}`}
                        >
                            <Icon className="h-4 w-4 mt-0.5 shrink-0" />
                            <span className="text-sm leading-snug flex-1">{toast.message}</span>
                            <button onClick={() => dismiss(toast.id)} className="opacity-50 hover:opacity-100 shrink-0 mt-0.5 transition-opacity">
                                <X className="h-3 w-3" />
                            </button>
                        </div>
                    );
                })}
            </div>
        </ToastContext.Provider>
    );
}
