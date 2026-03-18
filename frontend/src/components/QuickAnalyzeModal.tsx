"use client";

import { useState, useEffect } from 'react';
import { X, Search, User, FileText, Loader2, ArrowRight } from 'lucide-react';

interface QuickAnalyzeModalProps {
    isOpen: boolean;
    onClose: () => void;
    onStarted: (targetId: string) => void;
}

export default function QuickAnalyzeModal({ isOpen, onClose, onStarted }: QuickAnalyzeModalProps) {
    const [step, setStep] = useState<1 | 2>(1);
    const [mode, setMode] = useState<'scholar' | 'paper'>('scholar');
    const [inputValue, setInputValue] = useState('');
    const [citationLimit, setCitationLimit] = useState<number | string>('all');
    // Step 2 Criteria State
    const [criteria, setCriteria] = useState({ domain: '', notable_criteria: '', seminal_criteria: '' });

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');

    // Group Assignment State
    const [userGroups, setUserGroups] = useState<{ id: number, name: string }[]>([]);
    const [selectedGroupId, setSelectedGroupId] = useState<number | ''>('');

    // Fetch user groups to populate the destination dropdown
    useEffect(() => {
        if (isOpen) {
            fetch('/api/auth/me')
                .then(res => res.json())
                .then(data => {
                    if (data.user && data.user.groups) {
                        setUserGroups(data.user.groups);
                        if (data.user.groups.length > 0) {
                            setSelectedGroupId(data.user.groups[0].id);
                        }
                    }
                })
                .catch(err => console.error("Failed to load user groups", err));
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const handleGenerateCriteria = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsSubmitting(true);

        try {
            const body = mode === 'scholar'
                ? { user_id: inputValue }
                : { paper: inputValue };

            const res = await fetch('/api/criteria', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            const data = await res.json();
            if (data.success && data.criteria) {
                setCriteria({
                    domain: data.criteria.inferred_domain || data.criteria.domain || '',
                    notable_criteria: data.criteria.notable_criteria || '',
                    seminal_criteria: data.criteria.seminal_criteria || ''
                });
                setStep(2);
            } else {
                setError(data.error || 'Failed to generate criteria');
            }
        } catch {
            setError('Connection error. Is the backend running?');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleStartAnalysis = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsSubmitting(true);

        try {
            const body = mode === 'scholar'
                ? { user_id: inputValue, total_citations_to_add: citationLimit, group_id: selectedGroupId, ...criteria }
                : { paper: inputValue, total_citations_to_add: citationLimit, group_id: selectedGroupId, ...criteria };

            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            const data = await res.json();
            if (data.success) {
                onStarted(data.target_id || inputValue);
                onClose();
            } else {
                setError(data.error || 'Failed to start analysis');
            }
        } catch {
            setError('Connection error. Is the backend running?');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
            <div className="absolute inset-0 bg-slate-900/50 dark:bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />

            <div className={`relative w-full ${step === 2 ? 'max-w-3xl' : 'max-w-lg'} bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300 my-8`}>
                <div className="p-6 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50 dark:bg-white/[0.02]">
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <Search className="h-5 w-5 text-indigo-500 dark:text-indigo-400" />
                        {step === 1 ? 'New Analysis' : 'Review Criteria'}
                    </h2>
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 dark:hover:bg-white/5 rounded-full text-slate-500 dark:text-slate-400 transition-colors">
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {step === 1 ? (
                    <form onSubmit={handleGenerateCriteria} className="p-8 space-y-8">
                        {/* Mode Toggle */}
                        <div className="flex p-1 bg-slate-100 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-white/5">
                            <button
                                type="button"
                                onClick={() => setMode('scholar')}
                                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${mode === 'scholar' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
                            >
                                <User className="h-4 w-4" />
                                Researcher
                            </button>
                            <button
                                type="button"
                                onClick={() => setMode('paper')}
                                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${mode === 'paper' ? 'bg-emerald-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
                            >
                                <FileText className="h-4 w-4" />
                                Publication
                            </button>
                        </div>

                        <div className="space-y-4">
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                                {mode === 'scholar' ? 'Google Scholar User ID' : 'Publication Title'}
                            </label>
                            <div className="relative group">
                                <input
                                    required
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    placeholder={mode === 'scholar' ? 'e.g., 9RxI7UAAAAAJ' : 'e.g., Attention Is All You Need'}
                                    className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-2xl px-5 py-4 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all placeholder:text-slate-400 dark:placeholder:text-slate-600"
                                />
                            </div>
                            <p className="text-[11px] text-slate-500 dark:text-slate-500 px-1">
                                {mode === 'scholar'
                                    ? 'Find the ID in your Google Scholar profile URL (example: user=9RxI7UAAAAAJ).'
                                    : 'Exact title works best. We will match it via Semantic Scholar.'}
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 ml-1">Citation Limit</label>
                                <select
                                    value={citationLimit.toString()}
                                    onChange={(e) => setCitationLimit(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                                    className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 text-sm"
                                >
                                    <option value="20">20 Citations</option>
                                    <option value="50">50 Citations</option>
                                    <option value="100">100 Citations (Debug)</option>
                                    <option value="500">500 Citations</option>
                                    <option value="all">All Citations</option>
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 ml-1">Destination Group</label>
                                <select
                                    required
                                    value={selectedGroupId}
                                    onChange={(e) => setSelectedGroupId(Number(e.target.value))}
                                    className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 text-sm"
                                >
                                    <option value="" disabled>Select a group...</option>
                                    {userGroups.map(g => (
                                        <option key={g.id} value={g.id}>{g.name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {error && (
                            <div className="p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-2xl text-red-600 dark:text-red-400 text-sm flex gap-3 animate-in slide-in-from-top-2">
                                <X className="h-5 w-5 shrink-0" />
                                {error}
                            </div>
                        )}

                        <button
                            disabled={isSubmitting}
                            className={`w-full py-4 rounded-2xl font-bold text-white transition-all flex items-center justify-center gap-3 shadow-xl ${isSubmitting ? 'bg-slate-400 dark:bg-slate-800' : mode === 'scholar' ? 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-500/20' : 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-500/20'}`}
                        >
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="h-5 w-5 animate-spin" />
                                    Analyzing Domain...
                                </>
                            ) : (
                                <>
                                    Generate AI Criteria
                                    <ArrowRight className="h-5 w-5" />
                                </>
                            )}
                        </button>
                    </form>
                ) : (
                    <form onSubmit={handleStartAnalysis} className="p-8 space-y-6">
                        <div className="space-y-2">
                            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">Domain / Field</label>
                            <input
                                required
                                value={criteria.domain}
                                onChange={(e) => setCriteria({ ...criteria, domain: e.target.value })}
                                className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">Notable Author Criteria</label>
                            <textarea
                                required
                                rows={4}
                                value={criteria.notable_criteria}
                                onChange={(e) => setCriteria({ ...criteria, notable_criteria: e.target.value })}
                                className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm resize-none"
                            />
                            <p className="text-xs text-slate-500">Defines what awards or fellowships qualify an author as &quot;notable&quot; in this field.</p>
                        </div>

                        <div className="space-y-2">
                            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">Seminal Discovery Criteria</label>
                            <textarea
                                required
                                rows={4}
                                value={criteria.seminal_criteria}
                                onChange={(e) => setCriteria({ ...criteria, seminal_criteria: e.target.value })}
                                className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm resize-none"
                            />
                            <p className="text-xs text-slate-500">Guidelines for determining if a citation context indicates a fundamental breakthrough.</p>
                        </div>

                        {error && (
                            <div className="p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-2xl text-red-600 dark:text-red-400 text-sm flex gap-3 animate-in slide-in-from-top-2">
                                <X className="h-5 w-5 shrink-0" />
                                {error}
                            </div>
                        )}

                        <div className="flex gap-4 pt-4">
                            <button
                                type="button"
                                onClick={() => setStep(1)}
                                disabled={isSubmitting}
                                className="px-6 py-4 rounded-2xl font-bold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all flex items-center justify-center disabled:opacity-50"
                            >
                                Back
                            </button>
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className={`flex-1 py-4 rounded-2xl font-bold text-white transition-all flex items-center justify-center gap-3 shadow-xl ${isSubmitting ? 'bg-slate-400 dark:bg-slate-800' : mode === 'scholar' ? 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-500/20' : 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-500/20'}`}
                            >
                                {isSubmitting ? (
                                    <>
                                        <Loader2 className="h-5 w-5 animate-spin" />
                                        Launching Engine...
                                    </>
                                ) : (
                                    <>
                                        Start Semantic Analysis
                                        <ArrowRight className="h-5 w-5" />
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}

