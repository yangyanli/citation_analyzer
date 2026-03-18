"use client";

import { useState, useMemo, useEffect } from 'react';
import DataTable from './DataTable';
import MetricCard from './MetricCard';
import AdaptiveCriteriaBox from './AdaptiveCriteriaBox';
import QuickAnalyzeModal from './QuickAnalyzeModal';
import TargetSelector from './TargetSelector';
import TargetDetailBar from './TargetDetailBar';
import FallbackModal from './FallbackModal';
import ReRunModal from './ReRunModal';
import DomainChart from './DomainChart';
import ExportMenu from './ExportMenu';
import { ToastProvider } from './Toast';
import { Star, Trophy, LogOut, LogIn, Settings, Users, Shield, Terminal, Moon, Sun, Laptop } from 'lucide-react';
import { CitationRecord, EvaluationCriteria } from '../types';
import { useAuth } from '@/app/context/AuthContext';
import { useTheme } from '@/app/context/ThemeContext';
import Link from 'next/link';

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

interface DerivedPaper {
    cited_title: string;
    source_target_id: string;
    citation_count: number;
}

interface PendingFallback {
    runFolder: string;
    responseFile: string;
    promptFile: string;
    promptContent: string;
}

export default function DashboardClient() {
    const { user, logout, requireRole } = useAuth();
    const { theme, setTheme, resolvedTheme } = useTheme();
    const isAdmin = requireRole(['admin', 'super_admin']);

    const [targets, setTargets] = useState<Record<string, TargetInfo>>({});
    const [selectedTargetId, setSelectedTargetId] = useState<string>("");
    const [selectedPaper, setSelectedPaper] = useState<string | null>(null);
    const [derivedPapers, setDerivedPapers] = useState<DerivedPaper[]>([]);
    const [db, setDb] = useState<{ records: CitationRecord[], evaluation_criteria?: EvaluationCriteria }>({ records: [] });
    const [isDeleting, setIsDeleting] = useState(false);
    const [isResolvingVenues, setIsResolvingVenues] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Fallback Mode State
    const [pendingFallback, setPendingFallback] = useState<PendingFallback | null>(null);
    const [fallbackResponse, setFallbackResponse] = useState("");
    const [isSubmittingFallback, setIsSubmittingFallback] = useState(false);
    const [isFallbackModalHidden, setIsFallbackModalHidden] = useState(false);

    // Re-Run UI State
    const [reRunConfig, setReRunConfig] = useState<{isOpen: boolean, phase: number | null, criteria: string}>({ isOpen: false, phase: null, criteria: "" });

    // Domain filter state
    const [selectedDomain, setSelectedDomain] = useState<string | null>(null);

    // Hidden sign-in: revealed by double-clicking the title
    const [showSignIn, setShowSignIn] = useState(false);

    // Use window location for robust logout
        // Fetch targets on mount
    const fetchTargets = () => {
        fetch('/api/targets', { cache: 'no-store', headers: { 'Cache-Control': 'no-cache' } })
            .then(res => res.json())
            .then(data => {
                if (data.targets) {
                    setTargets(data.targets);
                    const ids = Object.keys(data.targets);
                    console.log("fetchTargets running. Current targets:", ids.length);
                    setSelectedTargetId(prev => {
                        console.log("setSelectedTargetId updater called in fetchTargets. prev:", prev);
                        if (!prev && ids.length > 0) {
                            console.log("setting to last target:", ids[ids.length - 1]);
                            return ids[ids.length - 1];
                        }
                        return prev;
                    });
                }
                if (data.derived_papers) {
                    setDerivedPapers(data.derived_papers);
                }
            })
            .catch(err => {
                console.error("Failed to fetch targets", err);
                
            });
    };

    useEffect(() => {
        fetchTargets();
        const intervalId = setInterval(fetchTargets, 5000);
        return () => clearInterval(intervalId);
    }, []);

    // Fallback Mode Polling (Global Fallback)
    useEffect(() => {
        const checkPendingFallback = async () => {
            try {
                const res = await fetch('/api/fallback-runs/pending', { cache: 'no-store', headers: { 'Cache-Control': 'no-cache' } });
                const data = await res.json();
                if (data.pendingRun) {
                    setPendingFallback(data.pendingRun);
                } else {
                    setPendingFallback(null);
                }
            } catch (err) {
                console.error("Failed to check fallback runs", err);
            }
        };

        checkPendingFallback();
        const intervalId = setInterval(checkPendingFallback, 3000);
        return () => clearInterval(intervalId);
    }, [isSubmittingFallback]);

    const handleFallbackSubmit = async () => {
        if (!pendingFallback || !fallbackResponse) return;
        setIsSubmittingFallback(true);
        try {
            const res = await fetch('/api/fallback-runs/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    runFolder: pendingFallback.runFolder,
                    responseFile: pendingFallback.responseFile,
                    responseContent: fallbackResponse
                })
            });
            if (res.ok) {
                setPendingFallback(null);
                setFallbackResponse("");
                fetchTargets(); // refresh status
            } else {
                alert("Failed to submit fallback response");
            }
        } catch (err) {
            console.error(err);
            alert("Error submitting fallback response");
        } finally {
            setIsSubmittingFallback(false);
        }
    };

    // Reset paper filter, domain filter, and stale records when target changes
    useEffect(() => {
        setSelectedPaper(null);
        setSelectedDomain(null);
        setDb({ records: [] }); // Clear stale records immediately to prevent data mismatch
    }, [selectedTargetId]);

    // Fetch citations when target changes, and poll for real-time updates
    useEffect(() => {
        if (!selectedTargetId) return;

        const fetchCitations = () => {
            fetch(`/api/citations?target_id=${encodeURIComponent(selectedTargetId)}`)
                .then(res => res.json())
                .then(data => {
                    console.log("RECEIVED CITATIONS DATA:", data);
                    setDb({
                        records: data.records || [],
                        evaluation_criteria: data.evaluation_criteria
                    });
                    
                })
                .catch(err => {
                    console.error("Failed to fetch citations", err);
                    
                });
        };

        // Initial fetch
        
        fetchCitations();

        // 5 second polling interval
        const intervalId = setInterval(fetchCitations, 5000);

        // Cleanup interval on unmount or target change
        return () => clearInterval(intervalId);
    }, [selectedTargetId]);

    const records = db.records || [];
    const criteria = db.evaluation_criteria || null;

    const targetIds = Object.keys(targets);
    const activeTarget = targets[selectedTargetId] || null;

    // Filter records based on Active Target 
    const activeRecords = useMemo(() => {
        if (!activeTarget) return [];

        // 1. In latest version, the API already filters correctly for the target_id.
        let filtered = [...records];

        // 2. Apply per-paper filter if active
        if (selectedPaper) {
            filtered = filtered.filter(r => r.cited_title === selectedPaper);
        }

        // 3. Apply domain filter if active
        if (selectedDomain) {
            filtered = filtered.filter(r => r.research_domain === selectedDomain);
        }

        return filtered;
    }, [records, activeTarget, selectedTargetId, selectedPaper, selectedDomain]);

    // Records for DomainChart: apply paper filter but NOT domain filter,
    // so DomainChart can show all domains and handle sentiment drill-down internally.
    const recordsForDomainChart = useMemo(() => {
        if (!activeTarget) return [];
        let filtered = [...records];
        if (selectedPaper) {
            filtered = filtered.filter(r => r.cited_title === selectedPaper);
        }
        return filtered;
    }, [records, activeTarget, selectedPaper]);

    const handleDelete = async () => {
        if (!selectedTargetId || !confirm(`Are you sure you want to delete "${activeTarget.name || activeTarget.title}"? This cannot be undone.`)) return;

        setIsDeleting(true);
        try {
            const res = await fetch(`/api/targets/${encodeURIComponent(selectedTargetId)}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                const newTargets = { ...targets };
                delete newTargets[selectedTargetId];
                setTargets(newTargets);
                const remainingIds = Object.keys(newTargets);
                setSelectedTargetId(remainingIds.length > 0 ? remainingIds[remainingIds.length - 1] : "");
            } else {
                const data = await res.json();
                alert(`Failed to delete target: ${data.error || "Unknown error"}`);
            }
        } catch (err: unknown) {
            console.error(err);
            alert(`Error deleting target: ${(err as Error).message || String(err)}`);
        } finally {
            setIsDeleting(false);
        }
    };

    const handleTargetAction = async (action: 'pause' | 'resume' | 'cancel') => {
        if (!selectedTargetId) return;
        if (action === 'cancel' && !confirm(`Are you sure you want to cancel analysis for "${activeTarget.name || activeTarget.title}"?`)) return;

        try {
            const endpoint = `/api/targets/${action}`;
            // Resume target from paused or fallback state
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_id: selectedTargetId })
            });

            if (res.ok) {
                fetchTargets();
            } else {
                const data = await res.json();
                alert(`Failed to ${action} target: ` + (data.error || "Unknown error"));
            }
        } catch (err: unknown) {
            console.error(err);
            alert(`Error trying to ${action} target: ` + ((err as Error).message || String(err)));
        }
    };

    const handlePhaseAction = async (action: 'wipe' | 'run', phase: number) => {
        if (!selectedTargetId) return;

        if (action === 'run' && (phase === 2 || phase === 3)) {
            const currentCriteria = phase === 2 ? 
                (activeTarget.evaluation_criteria?.notable_criteria || "") :
                (activeTarget.evaluation_criteria?.seminal_criteria || "");
            
            setReRunConfig({
                isOpen: true,
                phase: phase,
                criteria: currentCriteria
            });
            return;
        }

        if (!confirm(`Are you sure you want to ${action === 'wipe' ? 'wipe and reset' : 're-run'} Phase ${phase} for this Target?`)) return;

        executePhaseAction(action, phase);
    };

    const executePhaseAction = async (action: 'wipe' | 'run', phase: number, updatedCriteria?: string) => {
        try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const body: any = {
                group_id: activeTarget?.group_id
            };
            if (activeTarget?.mode === 'scholar') {
                body.user_id = selectedTargetId;
            } else {
                body.paper = selectedTargetId;
            }
            if (action === 'wipe') {
                body.wipe_phase = phase;
            } else {
                body.run_only_phase = phase;
                body.wipe_phase = phase; // Automatically wipe before re-running
            }

            if (updatedCriteria && phase === 2) {
                body.notable_criteria = updatedCriteria;
            } else if (updatedCriteria && phase === 3) {
                body.seminal_criteria = updatedCriteria;
            }

            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (res.ok) {
                setReRunConfig({ isOpen: false, phase: null, criteria: "" });
                fetchTargets();
            } else {
                const data = await res.json();
                alert(`Failed to ${action} phase: ` + (data.error || "Unknown error"));
            }
        } catch (err: unknown) {
            console.error(err);
            alert(`Error trying to ${action} phase: ` + ((err as Error).message || String(err)));
        }
    };

    const handleResolveArxiv = async () => {
        if (!selectedTargetId) return;
        setIsResolvingVenues(true);
        try {
            const res = await fetch('/api/citations/resolve-arxiv', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_id: selectedTargetId })
            });
            if (res.ok) {
                // Background job started. The polling will pick up updates naturally,
                // but we can optimisticially show a toast.
                console.log("Arxiv resolution started");
                // We leave the spinner spinning for 10 seconds to indicate background work
                setTimeout(() => setIsResolvingVenues(false), 10000);
            } else {
                const data = await res.json();
                alert(`Failed to start arXiv resolution: ${data.error || "Unknown error"}`);
                setIsResolvingVenues(false);
            }
        } catch (err: unknown) {
            console.error(err);
            alert(`Error starting arXiv resolution: ${(err as Error).message || String(err)}`);
            setIsResolvingVenues(false);
        }
    };

    // Calculate Metrics based on activeRecords
    const totalCitations = activeRecords.length;
    const notableCitations = activeRecords.filter(r => r.notable_authors.length > 0).length;
    const seminalCount = activeRecords.filter(r => r.is_seminal).length;

    const uniqueAuthors = new Set<string>();
    activeRecords.forEach(r => {
        r.notable_authors.forEach(a => uniqueAuthors.add(a.name));
    });

    const handleCitationDelete = (citationId: string) => {
        setDb(prev => ({
            ...prev,
            records: prev.records.filter(r => r.citation_id !== citationId)
        }));
    };

    const handleCitationUpdate = (citationId: string, updates: Partial<CitationRecord>) => {
        setDb(prev => ({
            ...prev,
            records: prev.records.map(r => r.citation_id === citationId ? { ...r, ...updates } : r)
        }));
    };

    return (
        <ToastProvider>
            <div className="min-h-screen bg-transparent text-slate-900 dark:text-slate-100 p-8 font-sans selection:bg-indigo-500/30 relative z-10 transition-colors duration-200">

                {/* Header */}
                <header className="mb-10 flex flex-col gap-6 relative z-20">
                    {/* Top Row: Title & Selectors */}
                    <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-6">
                        <div className="xl:max-w-2xl w-full">
                            <div className="flex items-center space-x-4 mb-2">
                                <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                                    <Trophy className="text-white h-5 w-5" />
                                </div>
                                <h1
                                    className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-slate-900 to-slate-500 dark:from-white block dark:to-slate-400 bg-clip-text text-transparent"
                                    onDoubleClick={() => setShowSignIn(v => !v)}
                                    style={{ cursor: 'default' }}
                                >
                                    Citation Analyzer
                                </h1>
                            </div>
                            <p className="text-slate-500 dark:text-slate-400 text-lg mt-3 leading-relaxed">
                                Beyond the count: AI-driven insights into who is citing, how they're citing, and in which research domains.
                            </p>

                        </div>

                        {/* Right-Side Controls */}
                        <div className="flex flex-col items-end gap-6 relative z-[100] w-full xl:w-auto mt-2 xl:mt-0">
                            {/* Auth & Theme Status */}
                            <div className="flex flex-wrap justify-end items-center gap-4 relative z-[110]">
                                {/* Theme Toggle */}
                                <div className="flex items-center p-1 bg-white/50 dark:bg-slate-800/50 backdrop-blur-md rounded-xl border border-slate-200/50 dark:border-white/10 shadow-sm">
                                    <button 
                                        onClick={() => setTheme('light')}
                                        className={`p-1.5 rounded-lg transition-colors ${theme === 'light' ? 'bg-white text-indigo-500 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'}`}
                                        title="Light Mode"
                                    >
                                        <Sun className="h-4 w-4" />
                                    </button>
                                    <button 
                                        onClick={() => setTheme('system')}
                                        className={`p-1.5 rounded-lg transition-colors ${theme === 'system' ? 'bg-white dark:bg-slate-700 text-indigo-500 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'}`}
                                        title="System Preference"
                                    >
                                        <Laptop className="h-4 w-4" />
                                    </button>
                                    <button 
                                        onClick={() => setTheme('dark')}
                                        className={`p-1.5 rounded-lg transition-colors ${theme === 'dark' ? 'bg-slate-700 text-indigo-400 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'}`}
                                        title="Dark Mode"
                                    >
                                        <Moon className="h-4 w-4" />
                                    </button>
                                </div>
                                {user ? (
                                    <div className="flex items-center gap-3">
                                        <div className="flex flex-col items-end">
                                            <span className="text-sm font-semibold text-slate-800 dark:text-white">{user.username}</span>
                                            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{user.role}</span>
                                        </div>
                                        <div className="flex items-center gap-1 border-l border-slate-300 dark:border-white/10 pl-3">
                                            {isAdmin && (
                                                <>
                                                    <Link href="/admin/llm-logs" className="p-2 text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors" title="LLM Logs">
                                                        <Terminal className="h-4 w-4" />
                                                    </Link>
                                                    <Link href="/admin/users" className="p-2 text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors" title="Manage Users">
                                                        <Users className="h-4 w-4" />
                                                    </Link>
                                                </>
                                            )}
                                            {user.role === 'super_admin' && (
                                                <Link href="/admin/groups" className="p-2 text-slate-500 hover:text-fuchsia-600 dark:text-slate-400 dark:hover:text-fuchsia-400 hover:bg-fuchsia-500/10 rounded-lg transition-colors" title="Manage Groups">
                                                    <Shield className="h-4 w-4" />
                                                </Link>
                                            )}
                                            <Link href="/settings" className="p-2 text-slate-500 hover:text-emerald-600 dark:text-slate-400 dark:hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors" title="Account Settings">
                                                <Settings className="h-4 w-4" />
                                            </Link>
                                            <button onClick={logout} className="p-2 text-slate-500 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors" title="Sign out">
                                                <LogOut className="h-4 w-4" />
                                            </button>
                                        </div>
                                    </div>
                                ) : showSignIn ? (
                                    <Link href="/login" className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl border border-indigo-500/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/10 transition-colors">
                                        <LogIn className="h-4 w-4" />
                                        Sign In
                                    </Link>
                                ) : null}
                                {pendingFallback && isFallbackModalHidden && (
                                    <button onClick={() => setIsFallbackModalHidden(false)} className="px-4 py-2 bg-amber-500/20 text-amber-500 rounded-xl font-bold animate-pulse hover:bg-amber-500/30 transition-colors border border-amber-500/40">
                                        ⚠️ Fallback Active
                                    </button>
                                )}
                                {activeTarget && activeRecords.length > 0 && user && user.role !== 'viewer' && (
                                    <ExportMenu
                                        records={activeRecords}
                                        targetName={activeTarget.name || activeTarget.title || selectedTargetId}
                                        targetId={selectedTargetId}
                                    />
                                )}
                            </div>

                            {/* Dual Target Selectors + New Analysis Button */}
                            <div className="print:hidden flex flex-row flex-wrap gap-4 items-center z-20 mt-6 xl:mt-0 w-full xl:w-auto">
                                <TargetSelector
                                    targets={targets as any}
                                    targetIds={targetIds}
                                    selectedTargetId={selectedTargetId}
                                    isAdmin={isAdmin}
                                    onSelectTarget={(id) => { setSelectedTargetId(id); setSelectedPaper(null); }}
                                    onNewAnalysis={() => setIsModalOpen(true)}
                                    derivedPapers={derivedPapers}
                                    selectedPaper={selectedPaper}
                                    onSelectPaper={(citedTitle, sourceTargetId) => {
                                        // Switch to the source author target and filter by paper
                                        if (selectedTargetId !== sourceTargetId) {
                                            setSelectedTargetId(sourceTargetId);
                                        }
                                        setSelectedPaper(citedTitle);
                                    }}
                                />
                            </div>
                        </div> {/* End Right-Side Controls */}
                    </div> {/* End Top Row */}

                    <>
                        {/* Expose modal trigger for testing to bypass flaky React hydration clicks */}
                        <span className="hidden" ref={() => { if (typeof window !== 'undefined') { (window as unknown as Record<string, unknown>).__OPEN_ANALYSIS_MODAL = () => setIsModalOpen(true); } }} />

                        <QuickAnalyzeModal
                            isOpen={isModalOpen}
                            onClose={() => setIsModalOpen(false)}
                            onStarted={(id) => {
                                setSelectedTargetId(id);
                                fetchTargets();
                            }}
                        />
                    </>

                    {/* Bottom Row: Selected Target Details */}
                    {activeTarget && (
                        <TargetDetailBar
                            target={activeTarget as any}
                            totalCitations={totalCitations}
                            isAdmin={isAdmin}
                            isViewer={!user || user.role === 'viewer'}
                            isDeleting={isDeleting}
                            isResolvingVenues={isResolvingVenues}
                            selectedPaper={selectedPaper}
                            onDelete={handleDelete}
                            onTargetAction={handleTargetAction}
                            onPhaseAction={handlePhaseAction}
                            onResolveArxiv={handleResolveArxiv}
                        />
                    )}
                </header>

                <AdaptiveCriteriaBox criteria={criteria} />

                {/* Metrics Row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                    <MetricCard
                        title="Seminal Works"
                        value={seminalCount.toString()}
                        subtitle="Breakthrough citing papers"
                        icon={<Star className="h-6 w-6 text-emerald-400" />}
                    />
                    <MetricCard
                        title="By Notable Authors"
                        value={notableCitations.toString()}
                        subtitle="Citations with notable authors"
                        icon={<Trophy className="h-6 w-6 text-amber-400" />}
                    />
                    <MetricCard
                        title="Notable Authors"
                        value={uniqueAuthors.size.toString()}
                        subtitle="Unique recognized researchers"
                        icon={<Trophy className="h-6 w-6 text-purple-400" />}
                    />
                </div>

                {/* Domain Distribution Chart */}
                <DomainChart
                    records={recordsForDomainChart}
                    selectedDomain={selectedDomain}
                    onSelectDomain={setSelectedDomain}
                />

                <DataTable
                    records={activeRecords}
                    hideToggles={activeTarget?.mode === "paper"}
                    hideGroupToggle={!!selectedPaper}
                    defaultGrouped={activeTarget?.mode === "scholar" && !selectedPaper}
                    onDeleteCitation={handleCitationDelete}
                    onUpdateCitation={handleCitationUpdate}
                />

                {/* Footnote Disclaimer */}
                <footer className="mt-16 pt-6 border-t border-slate-200 dark:border-white/[0.06] space-y-4">
                    <p className="text-slate-500 text-xs leading-relaxed">
                        <strong className="text-slate-700 dark:text-slate-400">Disclaimer:</strong> All metrics, including seminal discovery identification, notable author recognition,
                        sentiment analysis, and domain classifications, are estimated by an AI language model reading limited citation contexts. The classifications represent
                        a lower bound — if a paper's contribution or importance is not explicitly clear in the citation context, the AI might miss it.
                        Exhaustive classification would require full PDF analysis.
                    </p>
                    <p className="text-slate-500 text-xs leading-relaxed">
                        <strong className="text-slate-700 dark:text-slate-400">Data Source:</strong> This tool utilizes <a href="https://www.semanticscholar.org/" target="_blank" rel="noopener noreferrer" className="text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 underline">Semantic Scholar</a> and the <a href="https://arxiv.org/" target="_blank" rel="noopener noreferrer" className="text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 underline">arXiv API</a> as its primary data providers.
                        Unlike Google Scholar, Semantic Scholar provides structured <strong>citation contexts</strong> (the specific sentences where a paper is mentioned),
                        which allows our AI to accurately analyze the context, sentiment, and domain. Note that total citation counts may differ from Google Scholar as Semantic Scholar
                        utilizes a more curated index of peer-reviewed publications.
                    </p>
                </footer>

                {/* Fallback Mode Modal */}
                {pendingFallback && !isFallbackModalHidden && (
                    <FallbackModal
                        pendingFallback={pendingFallback}
                        fallbackResponse={fallbackResponse}
                        isSubmittingFallback={isSubmittingFallback}
                        onResponseChange={setFallbackResponse}
                        onSubmit={handleFallbackSubmit}
                        onHide={() => setIsFallbackModalHidden(true)}
                    />
                )}
                
                {/* Re-Run Modal */}
                {reRunConfig.isOpen && (
                    <ReRunModal
                        phase={reRunConfig.phase as number}
                        criteria={reRunConfig.criteria}
                        onCriteriaChange={(v) => setReRunConfig({ ...reRunConfig, criteria: v })}
                        onConfirm={() => executePhaseAction('run', reRunConfig.phase as number, reRunConfig.criteria)}
                        onClose={() => setReRunConfig({ isOpen: false, phase: null, criteria: "" })}
                    />
                )}
            </div>
        </ToastProvider>
    );
}
