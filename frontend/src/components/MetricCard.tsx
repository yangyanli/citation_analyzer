import React from 'react';

export default function MetricCard({ title, value, subtitle, icon }: { title: string, value: string, subtitle: string, icon: React.ReactNode }) {
    return (
        <div className="glass-card relative group overflow-hidden bg-white dark:bg-transparent">
            <div className="absolute inset-0 bg-gradient-to-br from-slate-50 to-white dark:from-white/[0.03] dark:to-white/[0.01] rounded-2xl transition-opacity opacity-100 group-hover:opacity-0" />
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-50/50 to-purple-50/50 dark:from-indigo-500/5 dark:to-purple-500/5 rounded-2xl transition-opacity opacity-0 group-hover:opacity-100" />
            <div className="relative p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-slate-500 dark:text-slate-400 font-medium text-sm tracking-wide uppercase">{title}</h3>
                    <div className="p-2 bg-slate-50 dark:bg-white/[0.03] rounded-lg border border-slate-100 dark:border-white/[0.05]">
                        <div className="text-indigo-500 dark:text-indigo-400">
                            {icon}
                        </div>
                    </div>
                </div>
                <div className="text-3xl font-bold text-slate-900 dark:text-white mb-2">{value}</div>
                <div className="text-sm text-slate-500">{subtitle}</div>
            </div>
        </div>
    );
}
