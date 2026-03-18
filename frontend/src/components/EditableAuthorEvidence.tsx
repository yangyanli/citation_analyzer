"use client";

import { useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Edit2, ShieldCheck, Check, X, Loader2, ExternalLink } from 'lucide-react';
import 'katex/dist/katex.min.css';
import Latex from 'react-latex-next';

interface PopupPos { top: number; left: number; right?: number; anchorSide: 'left' | 'right' }

export default function EditableAuthorEvidence({ authorName, initialEvidence, initialHomepage, canEdit = true, citedCount = 0, citedByPaper = {} }: { authorName: string, initialEvidence: string, initialHomepage?: string, canEdit?: boolean, citedCount?: number, citedByPaper?: Record<string, number> }) {
    const [isEditing, setIsEditing] = useState(false);
    const [evidence, setEvidence] = useState(initialEvidence);
    const [homepage, setHomepage] = useState(initialHomepage || "");
    const [draft, setDraft] = useState(initialEvidence);
    const [draftHomepage, setDraftHomepage] = useState(initialHomepage || "");
    const [isSaving, setIsSaving] = useState(false);

    // Popup state — position: fixed to escape overflow clipping
    const [evidencePopup, setEvidencePopup] = useState<PopupPos | null>(null);
    const [statsPopup, setStatsPopup] = useState<PopupPos | null>(null);
    const nameRef = useRef<HTMLSpanElement>(null);
    const statsRef = useRef<HTMLSpanElement>(null);

    const isVerifiedWeb = evidence.includes('[AI Verified]');
    const isVerifiedUser = evidence.includes('[User Verified]');
    const isVerified = isVerifiedWeb || isVerifiedUser;

    const cleanText = evidence
        .replace(/\[AI Verified\]/gi, '')
        .replace(/\[User Verified\]/gi, '')
        .trim();

    const showEvidencePopup = useCallback(() => {
        if (!nameRef.current || !cleanText || isEditing) return;
        const rect = nameRef.current.getBoundingClientRect();
        setEvidencePopup({ top: rect.top, left: rect.left, anchorSide: 'left' });
    }, [cleanText, isEditing]);

    const showStatsPopup = useCallback(() => {
        if (!statsRef.current) return;
        const rect = statsRef.current.getBoundingClientRect();
        setStatsPopup({ top: rect.top, left: rect.left, right: rect.right, anchorSide: 'right' });
    }, []);

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const res = await fetch('/api/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    author_name: authorName,
                    new_evidence: draft || undefined,
                    new_homepage: draftHomepage !== homepage ? draftHomepage : undefined
                })
            });
            const data = await res.json();
            if (data.success) {
                if (data.evidence) setEvidence(data.evidence);
                if (draftHomepage !== homepage) setHomepage(draftHomepage);
                setIsEditing(false);
            } else {
                alert("Failed to save: " + data.error);
            }
        } catch (e) {
            console.error(e);
            alert("Network error.");
        } finally {
            setIsSaving(false);
        }
    };

    const hasPapers = Object.keys(citedByPaper).length > 0;

    return (
        <div className="relative">
            {/* Header / Author Name & Actions — single line */}
            <div className="flex items-center gap-1.5">
                <span className="text-[9px] uppercase tracking-wider font-bold text-indigo-600/60 dark:text-indigo-400/60 shrink-0">Notable</span>

                {/* Author name — hover for evidence popup */}
                <span
                    ref={nameRef}
                    className="text-xs font-semibold text-indigo-600 dark:text-indigo-300 truncate cursor-default"
                    onMouseEnter={showEvidencePopup}
                    onMouseLeave={() => setEvidencePopup(null)}
                >
                    <Latex>{authorName}</Latex>
                </span>

                {/* Cited Nx badge */}
                {citedCount > 0 && (
                    <span
                        ref={statsRef}
                        className="text-[9px] font-medium text-indigo-700 dark:text-indigo-300/80 bg-indigo-50 dark:bg-indigo-500/10 px-1.5 py-0.5 rounded cursor-default whitespace-nowrap shrink-0"
                        onMouseEnter={showStatsPopup}
                        onMouseLeave={() => setStatsPopup(null)}
                    >
                        {citedCount}x
                    </span>
                )}

                {/* Verified icon */}
                {isVerified && !isEditing && (
                    <span className="shrink-0 text-amber-500" title={isVerifiedUser ? "Verified manually by user" : "Verified automatically via Crossref/Homepage lookup"}>
                        <ShieldCheck className="h-3 w-3" />
                    </span>
                )}

                {/* Homepage & Edit — shown on card hover */}
                {homepage && homepage !== "false" && homepage !== "null" && (
                    <a href={homepage} target="_blank" rel="noopener noreferrer" className="opacity-0 group-hover/author:opacity-100 transition-opacity text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-white shrink-0" title="Visit Homepage">
                        <ExternalLink className="h-3 w-3" />
                    </a>
                )}

                {canEdit && !isEditing && (
                    <button onClick={() => { setDraft(cleanText); setDraftHomepage(homepage); setIsEditing(true); }} className="opacity-0 group-hover/author:opacity-100 transition-opacity text-slate-400 hover:text-indigo-500 dark:text-slate-500 dark:hover:text-indigo-400 p-0.5 shrink-0 ml-auto" title="Edit Evidence & Homepage">
                        <Edit2 className="h-3 w-3" />
                    </button>
                )}
            </div>

            {/* Editing form */}
            {isEditing && (
                <div className="mb-2 mt-1 space-y-2">
                    <div>
                        <label className="text-[9px] uppercase text-slate-500 font-bold mb-0.5 block">Evidence</label>
                        <textarea
                            value={draft}
                            onChange={(e) => setDraft(e.target.value)}
                            className="w-full text-[10px] text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950 p-2 rounded border border-slate-300 dark:border-indigo-500/30 focus:outline-none focus:border-indigo-500 dark:focus:border-indigo-400 min-h-[50px]"
                        />
                    </div>
                    <div>
                        <label className="text-[9px] uppercase text-slate-500 font-bold mb-0.5 block">Homepage URL</label>
                        <input
                            type="url"
                            value={draftHomepage}
                            onChange={(e) => setDraftHomepage(e.target.value)}
                            placeholder="https://..."
                            className="w-full text-[10px] text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-indigo-500/30 focus:outline-none focus:border-indigo-500 dark:focus:border-indigo-400"
                        />
                    </div>
                    <div className="flex items-center gap-2 justify-end">
                        <button onClick={() => setIsEditing(false)} disabled={isSaving} className="text-[10px] text-slate-500 hover:text-slate-700 dark:hover:text-white px-2 py-1 flex items-center gap-1">
                            <X className="h-3 w-3" /> Cancel
                        </button>
                        <button onClick={handleSave} disabled={isSaving} className="text-[10px] bg-indigo-500 hover:bg-indigo-400 text-white px-2 py-1 rounded flex items-center gap-1 transition-colors">
                            {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />} Save
                        </button>
                    </div>
                </div>
            )}

            {/* ── Portal-rendered popups (fixed position, escapes overflow) ── */}
            {typeof window !== 'undefined' && evidencePopup && cleanText && createPortal(
                <div
                    className="fixed z-[9999] w-64 pointer-events-none"
                    style={{ top: evidencePopup.top - 8, left: evidencePopup.left, transform: 'translateY(-100%)' }}
                >
                    <div className="bg-white/95 dark:bg-slate-800/95 backdrop-blur-md border border-slate-200 dark:border-slate-600/50 p-3 rounded-lg shadow-xl relative">
                        <div className="text-[9px] uppercase font-bold tracking-wider text-indigo-600 dark:text-indigo-300 mb-1.5">Evidence</div>
                        <p className="text-[10px] text-slate-700 dark:text-slate-300 leading-relaxed italic">{cleanText}</p>
                        <div className="absolute -bottom-2 left-6 w-4 h-4 bg-white/95 dark:bg-slate-800/95 border-b border-r border-slate-200 dark:border-slate-600/50 transform rotate-45"></div>
                    </div>
                </div>,
                document.body
            )}

            {typeof window !== 'undefined' && statsPopup && hasPapers && createPortal(
                <div
                    className="fixed z-[9999] w-64 pointer-events-none"
                    style={{ top: statsPopup.top - 8, right: typeof window !== 'undefined' ? window.innerWidth - (statsPopup.right || 0) : 0, transform: 'translateY(-100%)' }}
                >
                    <div className="bg-white/95 dark:bg-slate-800/95 backdrop-blur-md border border-slate-200 dark:border-slate-600/50 p-3 rounded-lg shadow-xl relative">
                        <div className="text-[9px] uppercase font-bold tracking-wider text-indigo-600 dark:text-indigo-300 mb-1.5">Citations by Paper</div>
                        <ul className="space-y-1">
                            {Object.entries(citedByPaper).map(([paper, count]) => (
                                <li key={paper} className="flex justify-between items-center text-[9px] text-slate-700 dark:text-slate-300 opacity-80 gap-2">
                                    <span className="truncate italic">"{paper}"</span>
                                    <span className="px-1 bg-slate-100 dark:bg-white/[0.05] rounded shrink-0">{count}x</span>
                                </li>
                            ))}
                        </ul>
                        <div className="absolute -bottom-2 right-4 w-4 h-4 bg-white/95 dark:bg-slate-800/95 border-b border-r border-slate-200 dark:border-slate-600/50 transform rotate-45"></div>
                    </div>
                </div>,
                document.body
            )}
        </div>
    );
}
