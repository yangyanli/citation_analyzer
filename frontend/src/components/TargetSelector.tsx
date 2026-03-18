"use client";

import { ChevronDown, Plus } from 'lucide-react';

interface TargetInfo {
    mode: "scholar" | "paper";
    name?: string;
    title?: string;
}

interface DerivedPaper {
    cited_title: string;
    source_target_id: string;
    citation_count: number;
}

interface TargetSelectorProps {
    targets: Record<string, TargetInfo>;
    targetIds: string[];
    selectedTargetId: string;
    isAdmin: boolean;
    onSelectTarget: (id: string) => void;
    onNewAnalysis: () => void;
    derivedPapers?: DerivedPaper[];
    selectedPaper?: string | null;
    onSelectPaper?: (citedTitle: string, sourceTargetId: string) => void;
}

export default function TargetSelector({
    targets,
    targetIds,
    selectedTargetId,
    isAdmin,
    onSelectTarget,
    onNewAnalysis,
    derivedPapers = [],
    selectedPaper = null,
    onSelectPaper,
}: TargetSelectorProps) {
    const explicitPaperIds = targetIds.filter(id => targets[id].mode === "paper");
    const hasPaperSelection = selectedPaper !== null || targets[selectedTargetId]?.mode === "paper";

    // Build a unique list of derived papers, excluding any that already exist as explicit paper targets
    const explicitPaperTitles = new Set(explicitPaperIds.map(id => targets[id].title));
    const uniqueDerivedPapers = derivedPapers.filter(dp => !explicitPaperTitles.has(dp.cited_title));

    // Truncate long paper titles for display
    const truncate = (s: string, max: number = 80) => s.length > max ? s.slice(0, max) + '…' : s;

    if (targetIds.length === 0) {
        return isAdmin ? (
            <button
                data-testid="add-analysis-btn"
                onClick={onNewAnalysis}
                className="flex items-center gap-3 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-lg shadow-indigo-500/20 hover:scale-105 active:scale-95"
            >
                <Plus className="h-5 w-5" />
                New Analysis
            </button>
        ) : null;
    }

    // Handle paper selector change
    const handlePaperChange = (value: string) => {
        if (!value) return;

        // Check if it's a derived paper (prefixed with "dp:")
        if (value.startsWith('dp:') && onSelectPaper) {
            const citedTitle = value.slice(3);
            const dp = uniqueDerivedPapers.find(d => d.cited_title === citedTitle);
            if (dp) {
                onSelectPaper(dp.cited_title, dp.source_target_id);
            }
        } else {
            // It's an explicit paper target
            onSelectTarget(value);
        }
    };

    return (
        <>
            {/* Author Selector */}
            <div className={`relative group flex-1 min-w-[240px] transition-all duration-300 ${targets[selectedTargetId]?.mode === "scholar" && !selectedPaper ? "ring-2 ring-indigo-500 rounded-xl" : "opacity-70 hover:opacity-100"}`}>
                <div className={`absolute inset-0 bg-indigo-500/20 rounded-xl blur-xl transition-opacity ${targets[selectedTargetId]?.mode === "scholar" && !selectedPaper ? "opacity-100" : "opacity-0"}`}></div>
                <select
                    value={targets[selectedTargetId]?.mode === "scholar" && !selectedPaper ? selectedTargetId : ""}
                    onChange={(e) => {
                        if (e.target.value) onSelectTarget(e.target.value);
                    }}
                    className="relative w-full appearance-none bg-white/40 dark:bg-slate-900/40 backdrop-blur-md border border-slate-200 dark:border-white/[0.1] text-slate-800 dark:text-white px-4 py-3 rounded-xl focus:outline-none focus:border-indigo-500 cursor-pointer text-sm font-medium shadow-xl transition-all"
                >
                    <option value="" disabled>{targets[selectedTargetId]?.mode === "scholar" && !selectedPaper ? "👤 View Researcher..." : "👤 Select Researcher..."}</option>
                    {targetIds.filter(id => targets[id].mode === "scholar").map(id => (
                        <option key={id} value={id}>{targets[id].name}</option>
                    ))}
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
                {targets[selectedTargetId]?.mode === "scholar" && !selectedPaper && (
                    <div className="absolute -top-6 left-2 text-[10px] font-bold text-indigo-400 uppercase tracking-widest animate-pulse">
                        Active Profile
                    </div>
                )}
            </div>

            <div className="text-slate-300 dark:text-slate-600 font-bold hidden md:block">/</div>

            {/* Paper Selector (explicit + derived papers) */}
            <div className={`relative group flex-1 min-w-[240px] transition-all duration-300 ${hasPaperSelection ? "ring-2 ring-emerald-500 rounded-xl" : "opacity-70 hover:opacity-100"}`}>
                <div className={`absolute inset-0 bg-emerald-500/20 rounded-xl blur-xl transition-opacity ${hasPaperSelection ? "opacity-100" : "opacity-0"}`}></div>
                <select
                    value={
                        selectedPaper ? `dp:${selectedPaper}` :
                        targets[selectedTargetId]?.mode === "paper" ? selectedTargetId : ""
                    }
                    onChange={(e) => handlePaperChange(e.target.value)}
                    className="relative w-full appearance-none bg-white/40 dark:bg-slate-900/40 backdrop-blur-md border border-slate-200 dark:border-white/[0.1] text-slate-800 dark:text-white px-4 py-3 rounded-xl focus:outline-none focus:border-emerald-500 cursor-pointer text-sm font-medium shadow-xl transition-all"
                >
                    <option value="" disabled>{hasPaperSelection ? "📄 View Publication..." : "📄 Select Publication..."}</option>
                    {explicitPaperIds.length > 0 && explicitPaperIds.map(id => (
                        <option key={id} value={id}>{truncate(targets[id].title || '')}</option>
                    ))}
                    {uniqueDerivedPapers.length > 0 && (
                        <option disabled>── From Author Analyses ──</option>
                    )}
                    {uniqueDerivedPapers.map((dp, i) => (
                        <option key={`dp-${i}`} value={`dp:${dp.cited_title}`}>
                            {truncate(dp.cited_title)} ({dp.citation_count})
                        </option>
                    ))}
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
                {hasPaperSelection && (
                    <div className="absolute -top-6 left-2 text-[10px] font-bold text-emerald-400 uppercase tracking-widest animate-pulse">
                        Active Paper
                    </div>
                )}
            </div>

            {isAdmin && (
                <button
                    data-testid="add-analysis-btn"
                    onClick={onNewAnalysis}
                    className="h-11 w-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center transition-all shadow-lg shadow-indigo-500/20 hover:scale-105 active:scale-95"
                    title="Add New Analysis"
                >
                    <Plus className="h-5 w-5" />
                </button>
            )}
        </>
    );
}

