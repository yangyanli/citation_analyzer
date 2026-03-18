"use client";

import { CheckCircle2 } from 'lucide-react';

interface ReRunModalProps {
    phase: number;
    criteria: string;
    onCriteriaChange: (value: string) => void;
    onConfirm: () => void;
    onClose: () => void;
}

export default function ReRunModal({
    phase,
    criteria,
    onCriteriaChange,
    onConfirm,
    onClose,
}: ReRunModalProps) {
    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
            <div className="absolute inset-0 bg-slate-900/50 dark:bg-slate-950/60 backdrop-blur-sm" onClick={onClose} />
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 relative w-full max-w-2xl rounded-2xl shadow-2xl p-6 z-10">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">
                    Re-run Phase {phase}
                </h2>
                <p className="text-slate-600 dark:text-slate-400 text-sm mb-6">
                    You can optionally update the {phase === 2 ? 'Notable Author' : 'Seminal Work'} criteria before re-running this phase.
                </p>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    Criteria
                </label>
                <textarea
                    className="w-full h-32 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl p-4 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:border-indigo-500 mb-6"
                    value={criteria}
                    onChange={(e) => onCriteriaChange(e.target.value)}
                />
                <div className="flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-sm font-semibold"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        className="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-lg hover:shadow-indigo-500/25 text-sm flex items-center gap-2"
                    >
                        <CheckCircle2 className="h-4 w-4" /> Start Re-Run
                    </button>
                </div>
            </div>
        </div>
    );
}
