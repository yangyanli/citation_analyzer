"use client";

import { ExternalLink, FileText, Loader2, Trash2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { EvaluationCriteria } from '../types';

interface TargetInfo {
    mode: "scholar" | "paper";
    name?: string;
    title?: string;
    url?: string;
    s2_url?: string;
    status: string;
    total_citations: number;
    s2_total_citations: number;
    progress: number;
    error?: string;
    interests?: string[];
    p2_est_batches?: number;
    p2_est_cost?: number;
    p3_est_batches?: number;
    p3_est_cost?: number;
    p4_est_batches?: number;
    p4_est_cost?: number;
    p5_est_batches?: number;
    p5_est_cost?: number;
    group_id?: string | number;
    evaluation_criteria?: EvaluationCriteria;
}

interface TargetDetailBarProps {
    target: TargetInfo;
    totalCitations: number;
    isAdmin: boolean;
    isViewer: boolean;
    isDeleting: boolean;
    isResolvingVenues: boolean;
    selectedPaper?: string | null;
    onDelete: () => void;
    onTargetAction: (action: 'pause' | 'resume' | 'cancel') => void;
    onPhaseAction: (action: 'wipe' | 'run', phase: number) => void;
    onResolveArxiv: () => void;
}

export default function TargetDetailBar({
    target,
    totalCitations,
    isAdmin,
    isViewer,
    isDeleting,
    isResolvingVenues,
    selectedPaper,
    onDelete,
    onTargetAction,
    onPhaseAction,
    onResolveArxiv,
}: TargetDetailBarProps) {
    // When a derived paper is selected within a scholar target, show paper info instead of scholar profile
    const showPaperView = target.mode === 'scholar' && !!selectedPaper;
    return (
        <div className="glass-panel flex flex-col gap-0 p-0 animate-slide-in relative z-20 overflow-hidden bg-white dark:bg-slate-900/40">
            {/* TOP ROW: Main Info & Progress */}
            <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 p-5">
                {/* Profile Info */}
                <div className="flex items-start xl:items-center gap-3 flex-1 min-w-0">
                    <div className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 ${showPaperView ? 'bg-gradient-to-br from-emerald-500/20 to-teal-500/20' : target.mode === 'scholar' ? 'bg-gradient-to-br from-indigo-500/20 to-purple-500/20 text-lg font-bold text-indigo-300' : 'bg-gradient-to-br from-emerald-500/20 to-teal-500/20'}`}>
                        {showPaperView ? <FileText className="h-5 w-5 text-emerald-300" /> : target.mode === "scholar" ? (target.name?.charAt(0) || '?') : <FileText className="h-5 w-5 text-emerald-300" />}
                    </div>
                    <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                            <span className="text-slate-900 dark:text-white font-semibold truncate max-w-2xl block" title={showPaperView ? selectedPaper! : (target.name || target.title)}>
                                {showPaperView ? selectedPaper : (target.name || target.title)}
                            </span>
                            {!showPaperView && (
                                <a href={target.url || target.s2_url} target="_blank" rel="noopener noreferrer" className="text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors shrink-0">
                                    <ExternalLink className="h-4 w-4" />
                                </a>
                            )}
                        </div>
                        <div className="text-xs text-slate-500 mt-1 truncate">
                            {showPaperView ? (
                                <>Viewing paper citations from <span className="text-slate-700 dark:text-slate-400">{target.name}</span>&apos;s analysis</>
                            ) : target.mode === "scholar" ? (
                                <>Researcher profile via Google Scholar
                                    {!target.evaluation_criteria?.inferred_domain && (target.interests?.length ?? 0) > 0 && (
                                        <span className="ml-2 inline-flex gap-1">
                                            • {target.interests?.slice(0, 3).join(", ")}
                                            {(target.interests?.length ?? 0) > 3 && ` +${(target.interests?.length ?? 0) - 3}`}
                                        </span>
                                    )}
                                </>
                            ) : "Single paper analysis via Semantic Scholar"}
                        </div>
                        {!showPaperView && target.evaluation_criteria?.inferred_domain && (
                            <div className="flex flex-wrap gap-1.5 mt-1.5">
                                {(() => {
                                    const renderText = (val: unknown): string => {
                                        if (!val) return "";
                                        if (typeof val === 'string') return val;
                                        if (Array.isArray(val)) return val.map(renderText).join(', ');
                                        if (typeof val === 'object') return Object.values(val).map(renderText).join(' ');
                                        return String(val);
                                    };
                                    const fullText = renderText(target.evaluation_criteria.inferred_domain) || 'Research Domain Derived';
                                    return fullText.split(/,\s*/).map((domain, i) => (
                                        <span key={i} className="text-xs font-medium text-indigo-400/90 bg-indigo-500/10 px-2 py-0.5 rounded-md border border-indigo-500/20 whitespace-nowrap">
                                            {domain.trim()}
                                        </span>
                                    ));
                                })()}
                            </div>
                        )}
                    </div>
                </div>

                {/* Status & Primary Controls */}
                <div className="flex flex-wrap items-center gap-4 shrink-0 mt-4 xl:mt-0">
                    {target.status !== 'completed' && (
                        <div className="flex flex-col items-end gap-1 px-4 py-2 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-white/5 w-full sm:w-auto min-w-[240px]">
                            <div className="flex items-center gap-2 text-xs font-semibold text-indigo-500 dark:text-indigo-400 w-full">
                                {target.status === 'failed' ? (
                                    <><AlertCircle className="h-3 w-3 text-red-500 dark:text-red-400" /> <span className="text-red-500 dark:text-red-400">Analysis Failed</span></>
                                ) : target.status === 'collecting' ? (
                                    <><Loader2 className="h-3 w-3 animate-spin" /> <span>Collecting ({totalCitations}{target.total_citations > 0 ? `/${target.total_citations}` : ''})...</span></>
                                ) : target.status === 'scoring' ? (
                                    <><Loader2 className="h-3 w-3 animate-spin" /> <span>Analyzing ({totalCitations} citations)...</span></>
                                ) : target.status === 'resolving_venues' ? (
                                    <><Loader2 className="h-3 w-3 animate-spin" /> <span>Resolving Venues...</span></>
                                ) : (
                                    <><Loader2 className="h-3 w-3 animate-spin" /> <span>Pending ({target.total_citations || totalCitations})...</span></>
                                )}
                                <span className="ml-auto text-slate-500 dark:text-slate-300">
                                    {target.progress}%
                                </span>
                            </div>
                            <div className="w-full h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden mt-1">
                                <div
                                    className={`h-full transition-all duration-500 ${target.status === 'failed' ? 'bg-red-500' : 'bg-indigo-500'}`}
                                    style={{ width: `${target.progress}%` }}
                                ></div>
                            </div>
                            {target.error && (
                                <div className="text-[10px] text-red-400 mt-1 truncate max-w-[220px]" title={target.error}>
                                    {target.error}
                                </div>
                            )}
                            {/* Phase Estimates */}
                            {target.status !== 'failed' && target.status !== 'completed' && target.status !== 'cancelled' && (
                                <div className="mt-2 grid grid-cols-1 gap-1 text-[10px] text-slate-500 dark:text-slate-400 w-full border-t border-slate-200 dark:border-white/5 pt-2">
                                    {target.p2_est_batches !== undefined && target.p2_est_batches > 0 && (
                                        <div className="flex justify-between items-center">
                                            <span>Phase 2 (Authors): {target.p2_est_batches} batches</span>
                                            <span>est. ${target.p2_est_cost?.toFixed(4)}</span>
                                        </div>
                                    )}
                                    {target.p3_est_batches !== undefined && target.p3_est_batches > 0 && (
                                        <div className="flex justify-between items-center">
                                            <span>Phase 3 (Seminal): {target.p3_est_batches} batches</span>
                                            <span>est. ${target.p3_est_cost?.toFixed(4)}</span>
                                        </div>
                                    )}
                                    {target.p4_est_batches !== undefined && target.p4_est_batches > 0 && (
                                        <div className="flex justify-between items-center">
                                            <span>Phase 4 (Sentiment): {target.p4_est_batches} batches</span>
                                            {target.p4_est_cost !== undefined && target.p4_est_cost > 0 && (
                                                <span>est. ${target.p4_est_cost.toFixed(4)}</span>
                                            )}
                                        </div>
                                    )}
                                    {target.p5_est_batches !== undefined && target.p5_est_batches > 0 && (
                                        <div className="flex justify-between items-center">
                                            <span>Phase 5 (Domain): {target.p5_est_batches} batches</span>
                                            <span>est. ${target.p5_est_cost?.toFixed(4)}</span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {target.status === 'completed' && !isViewer && (
                        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 bg-emerald-500/5 px-3 py-1.5 rounded-lg border border-emerald-500/10 h-10">
                            <CheckCircle2 className="h-3 w-3" />
                            <span>Analysis Complete</span>
                            {target.s2_total_citations > 0 ? (
                                <span className="inline-flex items-center gap-0.5">
                                    (<span
                                        data-tooltip="Citations successfully analyzed by the pipeline"
                                        className="underline decoration-dotted decoration-emerald-500/40 underline-offset-2"
                                    >{totalCitations}</span>
                                    /
                                    <span
                                        data-tooltip="Total citations discovered on Google Scholar / Semantic Scholar"
                                        className="underline decoration-dotted decoration-emerald-500/40 underline-offset-2"
                                    >{target.s2_total_citations}</span> citations)
                                </span>
                            ) : (
                                <span>({totalCitations} citations)</span>
                            )}
                        </div>
                    )}

                    {isAdmin && (
                        <div className="flex items-center gap-2">
                            {/* Target Action Controls (Pause/Resume/Cancel) */}
                            {target.status !== 'completed' && target.status !== 'failed' && target.status !== 'cancelled' ? (
                                target.status === 'paused' ? (
                                    <button
                                        onClick={() => onTargetAction('resume')}
                                        className="px-3 py-2 text-sm font-medium rounded-xl border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                                        title="Resume Analysis"
                                    >
                                        Resume
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => onTargetAction('pause')}
                                        className="px-3 py-2 text-sm font-medium rounded-xl border border-amber-500/30 text-amber-400 hover:bg-amber-500/10 transition-colors"
                                        title="Pause Analysis"
                                    >
                                        Pause
                                    </button>
                                )
                            ) : null}

                            {target.status !== 'completed' && target.status !== 'cancelled' && (
                                <button
                                    onClick={() => onTargetAction('cancel')}
                                    className="px-3 py-2 text-sm font-medium rounded-xl border border-slate-300 dark:border-slate-500/30 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-500/10 transition-colors"
                                    title="Cancel Analysis"
                                >
                                    Cancel
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* BOTTOM ROW: Admin Controls */}
            {isAdmin && (
                <div className="flex items-center justify-between gap-4 px-5 py-3 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-white/5">
                    <div className="flex items-center gap-3 w-full overflow-x-auto pb-1 pb-xl-0 snap-x">
                        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider shrink-0 snap-start">Admin Controls</span>
                        <div className="h-4 w-px bg-slate-300 dark:bg-white/10 shrink-0"></div>
                        
                        {/* Phase Isolation Controls */}
                        <div className="flex items-center gap-2 shrink-0">
                            {[
                                { num: 2, label: "Authors" },
                                { num: 3, label: "Seminal" },
                                { num: 4, label: "Sentiment" },
                                { num: 5, label: "Update DB" }
                            ].map(phase => (
                                <div key={phase.num} className="flex bg-white dark:bg-slate-800/80 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-500/20 max-h-8 shrink-0 snap-start">
                                    <div className="px-3 py-0.5 text-[10px] font-semibold text-slate-500 dark:text-slate-300 bg-slate-100 dark:bg-slate-900/80 border-r border-slate-200 dark:border-slate-500/20 flex flex-col justify-center items-center text-center uppercase leading-none whitespace-nowrap min-w-[110px]">
                                        <span>Phase {phase.num}: {phase.label}</span>
                                    </div>
                                    <button 
                                        onClick={() => onPhaseAction('wipe', phase.num)} 
                                        className="px-3 py-1 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-700/80 text-slate-500 dark:text-slate-400 hover:text-red-500 dark:hover:text-red-400 transition-colors border-r border-slate-200 dark:border-slate-500/20 flex items-center justify-center gap-1.5" 
                                        title={`Wipe Phase ${phase.num} data`}
                                    >
                                        <Trash2 className="h-3 w-3" />
                                        <span>Wipe</span>
                                    </button>
                                    <button 
                                        onClick={() => onPhaseAction('run', phase.num)} 
                                        disabled={target.status === 'scoring' || target.status === 'collecting'} 
                                        className="px-3 py-1 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-700/80 text-indigo-600 dark:text-indigo-400 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5" 
                                        title={`Re-run Phase ${phase.num} only`}
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                                        <span>Run</span>
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Secondary Actions */}
                    <div className="flex items-center gap-2">
                        <button
                            onClick={onResolveArxiv}
                            disabled={isResolvingVenues}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors disabled:opacity-50 border border-indigo-500/20"
                            title="Scan and resolve arXiv venues to peer-reviewed venues"
                        >
                            {isResolvingVenues ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileText className="h-3 w-3" />}
                            Resolve arXiv
                        </button>
                        <button
                            onClick={onDelete}
                            disabled={isDeleting}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-500 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50 border border-red-500/20"
                            title="Delete this analysis and all its citations"
                        >
                            {isDeleting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                            Delete Target
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
