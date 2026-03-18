"use client";

import { Loader2, FileText, AlertCircle, CheckCircle2, Shield } from 'lucide-react';

interface PendingFallback {
    runFolder: string;
    responseFile: string;
    promptFile: string;
    promptContent: string;
}

interface FallbackModalProps {
    pendingFallback: PendingFallback;
    fallbackResponse: string;
    isSubmittingFallback: boolean;
    onResponseChange: (value: string) => void;
    onSubmit: () => void;
    onHide: () => void;
}

export default function FallbackModal({
    pendingFallback,
    fallbackResponse,
    isSubmittingFallback,
    onResponseChange,
    onSubmit,
    onHide,
}: FallbackModalProps) {
    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
            <div className="absolute inset-0 bg-slate-900/50 dark:bg-slate-950/60 backdrop-blur-sm" />
            <div className="glass-panel relative w-full max-w-4xl overflow-hidden animate-slide-in my-8 flex flex-col h-[80vh] bg-white dark:bg-transparent">
                <div className="p-6 border-b border-slate-200 dark:border-white/10 flex items-center justify-between bg-indigo-50 dark:bg-indigo-500/5">
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <Shield className="h-6 w-6 text-indigo-500 dark:text-indigo-400" />
                        Fallback Intervention Required
                    </h2>
                    <div className="flex items-center">
                        <span className="text-sm font-medium px-3 py-1 bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 rounded-full border border-indigo-200 dark:border-indigo-500/30 animate-pulse">
                            Awaiting Your Response...
                        </span>
                        <button onClick={onHide} className="ml-4 p-1 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors text-xl font-bold" title="Hide Modal">
                            ✕
                        </button>
                    </div>
                </div>

                <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
                    {/* Prompt Side */}
                    <div className="flex-1 border-r border-slate-200 dark:border-white/10 flex flex-col bg-slate-50 dark:bg-slate-950/50 p-6 overflow-y-auto w-[50%]">
                        <h3 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            System Prompt ({pendingFallback.promptFile})
                        </h3>
                        <pre className="text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap font-mono leading-relaxed bg-white dark:bg-slate-950 p-4 rounded-xl border border-slate-200 dark:border-white/5 overflow-auto">
                            {pendingFallback.promptContent}
                        </pre>
                    </div>

                    {/* Response Side */}
                    <div className="flex-1 flex flex-col p-6 bg-white dark:bg-slate-900/50 w-[50%]">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-2">
                                <AlertCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                                Provide Response
                            </h3>
                            <span className="text-[10px] font-mono bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 px-2 py-1 rounded-md border border-emerald-200 dark:border-emerald-500/20">
                                Expected Format: {pendingFallback.responseFile.split('.').pop()?.toUpperCase() || 'UNKNOWN'}
                            </span>
                        </div>
                        <textarea
                            className="flex-1 w-full bg-slate-50 dark:bg-slate-950 border border-emerald-300 dark:border-emerald-500/30 rounded-xl px-5 py-4 text-emerald-600 dark:text-emerald-300 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all resize-none shadow-inner"
                            placeholder={`Paste or type the structured ${pendingFallback.responseFile.split('.').pop()?.toUpperCase()} response here...`}
                            value={fallbackResponse}
                            onChange={(e) => onResponseChange(e.target.value)}
                        />
                        <div className="mt-6 flex gap-4">
                            <button
                                onClick={onSubmit}
                                disabled={!fallbackResponse.trim() || isSubmittingFallback}
                                className="flex-1 py-4 rounded-xl font-bold text-white bg-emerald-600 hover:bg-emerald-500 transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isSubmittingFallback ? <Loader2 className="h-5 w-5 animate-spin" /> : <CheckCircle2 className="h-5 w-5" />}
                                Submit Response & Resume Engine
                            </button>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-4 text-center">
                            File context: {pendingFallback.responseFile}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
