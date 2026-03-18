"use client";

import { useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Link as LinkIcon, Edit2, Trash2, Check, X, Loader2, ShieldCheck, UserPlus, UserMinus, RotateCcw } from 'lucide-react';
import { CitationRecord } from '../types';
import 'katex/dist/katex.min.css';
import Latex from 'react-latex-next';
import EditableAuthorEvidence from './EditableAuthorEvidence';
import { useToast } from './Toast';
import { useAuth } from '@/app/context/AuthContext';

function CommentWithCitedPopup({ comment, citedTitle }: { comment: string; citedTitle: string }) {
    const ref = useRef<HTMLDivElement>(null);
    const [popup, setPopup] = useState<{ top: number; left: number } | null>(null);

    const show = useCallback(() => {
        if (!ref.current) return;
        const rect = ref.current.getBoundingClientRect();
        setPopup({ top: rect.top - 8, left: rect.left });
    }, []);

    return (
        <div
            ref={ref}
            className="relative mb-3 cursor-default"
            onMouseEnter={show}
            onMouseLeave={() => setPopup(null)}
        >
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-indigo-500 to-purple-500 rounded-full"></div>
            <p className="pl-4 text-xs text-slate-700 dark:text-slate-300 italic leading-relaxed">
                {comment}
            </p>
            {typeof window !== 'undefined' && popup && createPortal(
                <div
                    className="fixed z-[9999] max-w-sm pointer-events-none"
                    style={{ top: popup.top, left: popup.left, transform: 'translateY(-100%)' }}
                >
                    <div className="bg-white/95 dark:bg-slate-800/95 backdrop-blur-md border border-slate-200 dark:border-slate-600/50 p-3 rounded-lg shadow-xl">
                        <div className="text-[9px] uppercase font-bold tracking-wider text-indigo-600 dark:text-indigo-300 mb-1">Cited Paper</div>
                        <p className="text-[11px] text-slate-700 dark:text-slate-300 leading-relaxed italic"><Latex>{`"${citedTitle}"`}</Latex></p>
                        <div className="absolute -bottom-2 left-6 w-4 h-4 bg-white/95 dark:bg-slate-800/95 border-b border-r border-slate-200 dark:border-slate-600/50 transform rotate-45"></div>
                    </div>
                </div>,
                document.body
            )}
        </div>
    );
}

export default function CitationRow({
    record,
    isGrouped,
    authorStats,
    onDelete,
    onUpdate
}: {
    record: CitationRecord;
    isGrouped: boolean;
    authorStats: Record<string, { total: number; byPaper: Record<string, number> }>;
    onDelete?: (id: string) => void;
    onUpdate?: (id: string, updates: Partial<CitationRecord>) => void;
}) {
    const [isEditingPaper, setIsEditingPaper] = useState(false);
    const [isEditingYear, setIsEditingYear] = useState(false);
    const [isEditingVenue, setIsEditingVenue] = useState(false);
    const [isEditingSentiment, setIsEditingSentiment] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [isReverting, setIsReverting] = useState(false);
    const [confirmAction, setConfirmAction] = useState<'delete' | 'revert' | null>(null);
    const { showToast } = useToast();
    const { requireRole } = useAuth();

    const isAdmin = requireRole(['admin']);
    const canEdit = requireRole(['admin', 'editor']);

    // Edit state
    const [editForm, setEditForm] = useState({
        score: record.score,
        usage_classification: record.usage_classification || "",
        positive_comment: record.positive_comment || "",
        sentiment_evidence: record.sentiment_evidence || "",
        is_seminal: record.is_seminal || false,
        seminal_evidence: record.seminal_evidence || "",
        paper_homepage: record.paper_homepage || "",
        notable_authors: record.notable_authors || [],
        citing_title: record.citing_title || "",
        year: record.year,
        venue: record.venue || "",
        authors: record.authors ? record.authors.map(a => a.name).join('\n') : ""
    });

    // State for adding a new notable author
    const [newAuthorName, setNewAuthorName] = useState("");
    const [newAuthorEvidence, setNewAuthorEvidence] = useState("");

    const executeDelete = async (e?: React.MouseEvent) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setIsDeleting(true);
        try {
            const res = await fetch(`/api/citations/${record.citation_id}?target_id=${encodeURIComponent(record.target_id)}`, { method: 'DELETE' });
            if (res.ok && onDelete) {
                showToast("Citation deleted from database.", 'success');
                onDelete(record.citation_id);
            } else {
                showToast("Failed to delete citation.", 'error');
                setIsDeleting(false);
                setConfirmAction(null);
            }
        } catch (error) {
            console.error(error);
            showToast("Error deleting citation.", 'error');
            setIsDeleting(false);
            setConfirmAction(null);
        }
    };

    const handleSave = async (section: 'paper' | 'year' | 'venue' | 'sentiment', e?: React.MouseEvent) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setIsSaving(true);
        try {
            const parsedAuthors = editForm.authors.split('\n').map(n => n.trim()).filter(n => n).map(name => ({ name }));
            const payload = { ...editForm, authors: parsedAuthors };

            const res = await fetch(`/api/citations/${record.citation_id}?target_id=${encodeURIComponent(record.target_id)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok && onUpdate) {
                onUpdate(record.citation_id, {
                    ...payload,
                    is_human_verified: true
                });
                if (section === 'paper') setIsEditingPaper(false);
                if (section === 'year') setIsEditingYear(false);
                if (section === 'venue') setIsEditingVenue(false);
                if (section === 'sentiment') setIsEditingSentiment(false);
                showToast("Citation updated successfully.", 'success');
            } else {
                showToast("Failed to update citation.", 'error');
            }
        } catch (error) {
            console.error(error);
            showToast("Error updating citation.", 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const executeRevertToAI = async (e?: React.MouseEvent) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setIsReverting(true);
        try {
            const aiData = {
                score: record.ai_score ?? record.score,
                usage_classification: record.ai_usage_classification ?? record.usage_classification,
                positive_comment: record.ai_positive_comment ?? record.positive_comment,
                sentiment_evidence: record.ai_sentiment_evidence ?? record.sentiment_evidence,
                is_seminal: record.ai_is_seminal ?? record.is_seminal,
                seminal_evidence: record.ai_seminal_evidence ?? record.seminal_evidence,
            };
            const res = await fetch(`/api/citations/${record.citation_id}?target_id=${encodeURIComponent(record.target_id)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...aiData, revert_to_ai: true })
            });
            if (res.ok && onUpdate) {
                onUpdate(record.citation_id, {
                    ...aiData,
                    is_human_verified: false
                });
                showToast("Citation reverted to AI baseline.", 'success');
                setConfirmAction(null);
            } else {
                showToast("Failed to revert.", 'error');
            }
        } catch (error) {
            console.error(error);
            showToast("Error reverting citation.", 'error');
        } finally {
            setIsReverting(false);
        }
    };

    const startEditing = (section: 'paper' | 'year' | 'venue' | 'sentiment', e?: React.MouseEvent) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setEditForm({
            score: record.score,
            usage_classification: record.usage_classification || "",
            positive_comment: record.positive_comment || "",
            sentiment_evidence: record.sentiment_evidence || "",
            is_seminal: record.is_seminal || false,
            seminal_evidence: record.seminal_evidence || "",
            paper_homepage: record.paper_homepage || "",
            notable_authors: record.notable_authors ? [...record.notable_authors] : [],
            citing_title: record.citing_title || "",
            year: record.year,
            venue: record.venue || "",
            authors: record.authors ? record.authors.map(a => a.name).join('\n') : ""
        });
        if (section === 'paper') setIsEditingPaper(true);
        if (section === 'year') setIsEditingYear(true);
        if (section === 'venue') setIsEditingVenue(true);
        if (section === 'sentiment') setIsEditingSentiment(true);
    };

    const formatAuthors = (authors?: { name: string }[]) => {
        if (!authors || authors.length === 0) return null;
        if (authors.length <= 10) {
            return authors.map(a => a.name).join(', ');
        }
        const firstFive = authors.slice(0, 5).map(a => a.name);
        const lastTwo = authors.slice(-2).map(a => a.name);
        return `${firstFive.join(', ')} ... ${lastTwo.join(', ')}`;
    };

    return (
        <tr className="hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors group">
            {/* Column 1: Paper Title & Citation Count */}
            <td className="p-6 w-1/4 align-top group/paper relative" data-label="Citing Paper">
                {isEditingPaper ? (
                    <div className="flex flex-col gap-2 mb-4">
                        <div>
                            <label className="text-[9px] uppercase text-slate-500 font-bold mb-1 block">Citing Paper Title</label>
                            <textarea
                                className="w-full text-sm bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 min-h-[60px]"
                                value={editForm.citing_title}
                                onChange={(e) => setEditForm(prev => ({ ...prev, citing_title: e.target.value }))}
                            />
                        </div>
                        <div>
                            <label className="text-[9px] uppercase text-slate-500 font-bold mb-1 block">Authors (One per line)</label>
                            <textarea
                                className="w-full text-xs font-mono bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-white/10 text-slate-700 dark:text-slate-300 focus:outline-none focus:border-indigo-500 min-h-[80px]"
                                value={editForm.authors}
                                onChange={(e) => setEditForm(prev => ({ ...prev, authors: e.target.value }))}
                                placeholder="Author 1&#10;Author 2&#10;Author 3"
                            />
                        </div>
                        <div className="flex justify-end gap-2 mt-1">
                            <button onClick={(e) => { e.stopPropagation(); setIsEditingPaper(false); }} className="px-2 py-1 text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-white transition-colors">Cancel</button>
                            <button onClick={(e) => handleSave('paper', e)} className="px-2 py-1 text-xs bg-indigo-500 hover:bg-indigo-600 text-white rounded transition-colors flex items-center gap-1">
                                {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                                Save
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="font-medium text-slate-800 dark:text-slate-200 mb-2 leading-snug flex flex-col items-start gap-2 relative">
                        {canEdit && (
                            <button onClick={(e) => startEditing('paper', e)} className="absolute top-0 right-0 opacity-0 group-hover/paper:opacity-100 text-slate-400 hover:text-indigo-600 dark:text-slate-500 dark:hover:text-indigo-400 p-1 bg-slate-100/80 dark:bg-slate-950/80 rounded transition-opacity" title="Edit Paper Info">
                                <Edit2 className="h-3.5 w-3.5" />
                            </button>
                        )}
                        {(record.paper_homepage || record.url) ? (
                            <a href={record.paper_homepage || record.url} target="_blank" rel="noopener noreferrer" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex items-start gap-2 pr-6 group/link">
                                <Latex>{record.citing_title}</Latex>
                                <LinkIcon className="h-3 w-3 mt-1 opacity-0 group-hover/link:opacity-100 transition-opacity flex-shrink-0" />
                            </a>
                        ) : (
                            <span className="pr-6"><Latex>{record.citing_title}</Latex></span>
                        )}
                        {record.authors && record.authors.length > 0 && (
                            <div className="text-xs text-slate-500 dark:text-slate-400 font-serif italic mb-1">
                                {formatAuthors(record.authors)}
                            </div>
                        )}
                        <div className="flex items-center gap-2 flex-wrap">
                            {(record.citing_citation_count ?? 0) >= 100 ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-orange-500/20 text-orange-400 border border-orange-500/30 whitespace-nowrap">
                                    🔥 {(record.citing_citation_count ?? 0).toLocaleString()} Citations
                                </span>
                            ) : (
                                <span className="text-[10px] text-slate-500 font-medium">
                                    {(record.citing_citation_count ?? 0).toLocaleString()} Citations
                                </span>
                            )}
                            {record.research_domain && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-violet-500/15 text-violet-300 border border-violet-500/20 whitespace-nowrap" data-domain-badge={record.research_domain}>
                                    {record.research_domain}
                                </span>
                            )}
                        </div>
                    </div>
                )}

            </td>

            {/* Column 2: Representative Citations (Seminal Status + Notable Authors) */}
            <td className="p-6 w-1/5 align-top border-l border-slate-100 dark:border-white/[0.02]" data-label="Representative Citations">
                <div className="flex flex-col gap-3 max-h-[200px] overflow-y-auto custom-scrollbar">
                    {/* Seminal Discovery Card */}
                    {(record.is_seminal || isEditingSentiment) && (
                        <div className="flex flex-col bg-yellow-50 dark:bg-slate-900/50 rounded-lg border border-yellow-200 dark:border-yellow-500/15 p-3">
                            <div className="flex items-center gap-2 mb-1.5">
                                <span className="text-[9px] uppercase tracking-wider font-bold text-yellow-600/60 dark:text-yellow-400/60">Seminal</span>
                                <span className="text-xs font-semibold text-yellow-700 dark:text-yellow-300">🌟 Seminal Discovery</span>
                                {isEditingSentiment && (
                                    <label className="flex items-center gap-2 ml-auto text-xs text-slate-700 dark:text-white">
                                        <input
                                            type="checkbox"
                                            checked={editForm.is_seminal}
                                            onChange={(e) => setEditForm(prev => ({ ...prev, is_seminal: e.target.checked }))}
                                            className="w-3 h-3 rounded"
                                        />
                                        Enable
                                    </label>
                                )}
                            </div>
                            {isEditingSentiment && editForm.is_seminal ? (
                                <textarea
                                    className="w-full text-[10px] text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950 p-2 rounded border border-yellow-300 dark:border-yellow-500/30 focus:outline-none min-h-[40px] mt-1"
                                    value={editForm.seminal_evidence}
                                    onChange={(e) => setEditForm(prev => ({ ...prev, seminal_evidence: e.target.value }))}
                                    placeholder="Evidence..."
                                />
                            ) : (
                                record.seminal_evidence && (
                                    <span className="text-[10px] text-slate-600 dark:text-slate-400 italic">
                                        {record.seminal_evidence}
                                    </span>
                                )
                            )}
                        </div>
                    )}

                    {/* Notable Author Cards */}
                    {record.notable_authors.map((author, idx) => {
                        const stats = authorStats[author.name] || { total: 0, byPaper: {} };
                        return (
                            <div key={idx} className="bg-indigo-50/50 dark:bg-slate-900/50 rounded-lg border border-indigo-200 dark:border-indigo-500/10 p-3 relative group/author">
                                <EditableAuthorEvidence authorName={author.name} initialEvidence={author.evidence || ""} initialHomepage={author.homepage} canEdit={canEdit} citedCount={stats.total} citedByPaper={stats.byPaper} />
                            </div>
                        );
                    })}
                </div>
            </td>

            {/* Column 3: Date */}
            <td className="p-6 w-[8%] align-top border-l border-slate-100 dark:border-white/[0.02] relative group/year" data-label="Year">
                {isEditingYear ? (
                    <div className="flex flex-col gap-2">
                        <input
                            type="number"
                            className="w-full text-sm bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                            value={editForm.year || ""}
                            onChange={(e) => setEditForm(prev => ({ ...prev, year: parseInt(e.target.value) || undefined }))}
                            placeholder="Year"
                        />
                        <div className="flex justify-end gap-1">
                            <button onClick={(e) => { e.stopPropagation(); setIsEditingYear(false); }} className="p-1 hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500 dark:text-slate-400 rounded"><X className="h-3 w-3" /></button>
                            <button onClick={(e) => handleSave('year', e)} className="p-1 hover:bg-indigo-500/20 text-indigo-400 rounded">
                                {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="flex items-start justify-between">
                        {record.year ? (
                            <div className="font-semibold text-slate-700 dark:text-slate-300">{record.year}</div>
                        ) : (
                            <div className="text-slate-500 text-sm">N/A</div>
                        )}
                        {canEdit && (
                            <button onClick={(e) => startEditing('year', e)} className="opacity-0 group-hover/year:opacity-100 text-slate-400 hover:text-indigo-600 dark:text-slate-500 dark:hover:text-indigo-400 p-1 -mt-1 -mr-2 rounded" title="Edit Year">
                                <Edit2 className="h-3.5 w-3.5" />
                            </button>
                        )}
                    </div>
                )}
            </td>

            {/* Column 4: Venue */}
            <td className="p-6 w-[10%] align-top border-l border-slate-100 dark:border-white/[0.02] relative group/venue" data-label="Venue">
                {isEditingVenue ? (
                    <div className="flex flex-col gap-2">
                        <textarea
                            className="w-full text-xs bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 min-h-[60px]"
                            value={editForm.venue}
                            onChange={(e) => setEditForm(prev => ({ ...prev, venue: e.target.value }))}
                            placeholder="Venue"
                        />
                        <div className="flex justify-end gap-1">
                            <button onClick={(e) => { e.stopPropagation(); setIsEditingVenue(false); }} className="p-1 hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500 dark:text-slate-400 rounded"><X className="h-3 w-3" /></button>
                            <button onClick={(e) => handleSave('venue', e)} className="p-1 hover:bg-indigo-500/20 text-indigo-400 rounded">
                                {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="flex items-start justify-between">
                        {record.venue ? (
                            <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">{record.venue}</div>
                        ) : (
                            <div className="text-slate-400 dark:text-slate-600 text-sm italic">None</div>
                        )}
                        {canEdit && (
                            <button onClick={(e) => startEditing('venue', e)} className="opacity-0 group-hover/venue:opacity-100 text-slate-400 hover:text-indigo-600 dark:text-slate-500 dark:hover:text-indigo-400 p-1 -mt-1 -mr-2 rounded" title="Edit Venue">
                                <Edit2 className="h-3.5 w-3.5" />
                            </button>
                        )}
                    </div>
                )}
            </td>

            {/* Column 5/6: Sentiment & Comment */}
            <td className="p-6 w-1/4 align-top border-l border-slate-100 dark:border-white/[0.02] relative hover:bg-slate-50 dark:hover:bg-slate-900/10 group/sentiment" data-label="Sentiment">
                {isEditingSentiment ? (
                    <div className="flex flex-col gap-3">
                        <div className="flex gap-2 mb-1">
                            <div className="flex-1">
                                <label className="text-[9px] uppercase text-slate-500 font-bold mb-1 block">Score (1-10)</label>
                                <input
                                    type="number"
                                    min="1" max="10"
                                    className="w-full text-sm bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                                    value={editForm.score}
                                    onChange={(e) => setEditForm(prev => ({ ...prev, score: parseInt(e.target.value) || 0 }))}
                                />
                            </div>
                            <div className="flex-[2]">
                                <label className="text-[9px] uppercase text-slate-500 font-bold mb-1 block">Classification</label>
                                <input
                                    type="text"
                                    className="w-full text-sm bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                                    value={editForm.usage_classification}
                                    onChange={(e) => setEditForm(prev => ({ ...prev, usage_classification: e.target.value }))}
                                />
                            </div>
                        </div>

                        <div>
                            <label className="text-[9px] uppercase text-slate-500 font-bold mb-1 block">Paper Homepage URL</label>
                            <input
                                type="url"
                                className="w-full text-xs text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-white/10 focus:outline-none focus:border-indigo-500"
                                value={editForm.paper_homepage}
                                onChange={(e) => setEditForm(prev => ({ ...prev, paper_homepage: e.target.value }))}
                                placeholder="https://..."
                            />
                        </div>

                        <div>
                            <label className="text-[9px] uppercase text-slate-500 font-bold mb-1 block">Comment</label>
                            <textarea
                                className="w-full text-xs text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950 p-2 rounded border border-slate-300 dark:border-white/10 focus:outline-none focus:border-indigo-500 min-h-[60px]"
                                value={editForm.positive_comment}
                                onChange={(e) => setEditForm(prev => ({ ...prev, positive_comment: e.target.value }))}
                            />
                        </div>

                        <div>
                            <label className="text-[9px] uppercase text-slate-500 font-bold mb-1 block">Sentiment Evidence</label>
                            <textarea
                                className="w-full text-xs text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950 p-2 rounded border border-slate-300 dark:border-white/10 focus:outline-none focus:border-indigo-500 min-h-[60px]"
                                value={editForm.sentiment_evidence}
                                onChange={(e) => setEditForm(prev => ({ ...prev, sentiment_evidence: e.target.value }))}
                            />
                        </div>

                        {/* Notable Authors Management */}
                        <div className="border-t border-slate-200 dark:border-white/5 pt-3">
                            <label className="text-[9px] uppercase text-slate-500 font-bold mb-2 block">Notable Authors</label>
                            {editForm.notable_authors.length > 0 && (
                                <div className="space-y-2 mb-2">
                                    {editForm.notable_authors.map((author, idx) => (
                                        <div key={idx} className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-2.5 border border-indigo-200 dark:border-indigo-500/10 space-y-1.5">
                                            <div className="flex items-center gap-1.5">
                                                <input
                                                    type="text"
                                                    value={author.name}
                                                    onChange={(e) => setEditForm(prev => ({
                                                        ...prev,
                                                        notable_authors: prev.notable_authors.map((a, i) => i === idx ? { ...a, name: e.target.value } : a)
                                                    }))}
                                                    className="flex-1 text-[10px] text-indigo-600 dark:text-indigo-300 font-medium bg-white dark:bg-slate-950 p-1 rounded border border-slate-300 dark:border-white/10 focus:outline-none focus:border-indigo-500"
                                                    placeholder="Author name"
                                                />
                                                <button
                                                    onClick={() => setEditForm(prev => ({
                                                        ...prev,
                                                        notable_authors: prev.notable_authors.filter((_, i) => i !== idx)
                                                    }))}
                                                    className="text-red-500 dark:text-red-400 hover:text-red-600 dark:hover:text-red-300 p-0.5 shrink-0 transition-colors"
                                                    title="Remove author"
                                                >
                                                    <UserMinus className="h-3 w-3" />
                                                </button>
                                            </div>
                                            <input
                                                type="text"
                                                value={author.evidence?.replace(/\[(AI|User) Verified.*?\]/g, '').trim() || ''}
                                                onChange={(e) => setEditForm(prev => ({
                                                    ...prev,
                                                    notable_authors: prev.notable_authors.map((a, i) => i === idx ? { ...a, evidence: e.target.value } : a)
                                                }))}
                                                className="w-full text-[10px] text-slate-700 dark:text-slate-400 bg-white dark:bg-slate-950 p-1 rounded border border-slate-300 dark:border-white/10 focus:outline-none focus:border-indigo-500"
                                                placeholder="Evidence / reason"
                                            />
                                            <input
                                                type="url"
                                                value={author.homepage || ''}
                                                onChange={(e) => setEditForm(prev => ({
                                                    ...prev,
                                                    notable_authors: prev.notable_authors.map((a, i) => i === idx ? { ...a, homepage: e.target.value } : a)
                                                }))}
                                                className="w-full text-[10px] text-slate-700 dark:text-slate-400 bg-white dark:bg-slate-950 p-1 rounded border border-slate-300 dark:border-white/10 focus:outline-none focus:border-indigo-500"
                                                placeholder="Homepage URL (optional)"
                                            />
                                        </div>
                                    ))}
                                </div>
                            )}
                            <div className="flex gap-1.5 items-end">
                                <div className="flex-1">
                                    <input
                                        type="text"
                                        placeholder="Author name"
                                        className="w-full text-[10px] text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-white/10 focus:outline-none focus:border-indigo-500"
                                        value={newAuthorName}
                                        onChange={(e) => setNewAuthorName(e.target.value)}
                                    />
                                </div>
                                <div className="flex-[2]">
                                    <input
                                        type="text"
                                        placeholder="Evidence / reason"
                                        className="w-full text-[10px] text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950 p-1.5 rounded border border-slate-300 dark:border-white/10 focus:outline-none focus:border-indigo-500"
                                        value={newAuthorEvidence}
                                        onChange={(e) => setNewAuthorEvidence(e.target.value)}
                                    />
                                </div>
                                <button
                                    onClick={() => {
                                        if (!newAuthorName.trim()) return;
                                        setEditForm(prev => ({
                                            ...prev,
                                            notable_authors: [...prev.notable_authors, { name: newAuthorName.trim(), evidence: newAuthorEvidence.trim() || 'Added by user [User Verified]', homepage: '' }]
                                        }));
                                        setNewAuthorName("");
                                        setNewAuthorEvidence("");
                                    }}
                                    className="text-[10px] bg-indigo-50 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-500/30 p-1.5 rounded transition-colors shrink-0 border border-indigo-200 dark:border-transparent"
                                    title="Add notable author"
                                >
                                    <UserPlus className="h-3 w-3" />
                                </button>
                            </div>
                        </div>

                        <div className="flex justify-end gap-2 mt-2 pt-2 border-t border-slate-200 dark:border-white/5">
                            <button onClick={() => setIsEditingSentiment(false)} disabled={isSaving} className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-white px-3 py-1.5 flex items-center gap-1 rounded">
                                <X className="h-3 w-3" /> Cancel
                            </button>
                            <button onClick={(e) => handleSave('sentiment', e)} disabled={isSaving} className="text-xs bg-indigo-500 hover:bg-indigo-400 text-white px-3 py-1.5 rounded flex items-center gap-1 transition-colors">
                                {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />} Save
                            </button>
                        </div>
                    </div>
                ) : (
                    <>
                        {/* Header Row for Score, Classification, Badges, and Actions */}
                        <div className="flex items-center gap-2 mb-3 flex-wrap relative z-10 w-full min-h-[28px]">
                            <div className={`flex items-center justify-center h-6 w-6 rounded-full font-bold text-[10px] shrink-0
                                ${record.score >= 8 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                                    record.score >= 5 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                                        'bg-rose-500/20 text-rose-400 border border-rose-500/30'}`}>
                                {record.score}
                            </div>

                            {record.usage_classification && (
                                <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] uppercase font-bold border max-w-[120px] truncate block shrink-0
                                    ${(record.usage_classification === 'Experimental Comparison' || record.usage_classification === 'Comparison') ? 'bg-purple-500/20 text-purple-400 border-purple-500/30' :
                                        record.usage_classification === 'Extending / Using' ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' :
                                            'bg-slate-500/20 text-slate-400 border-slate-500/30'}`} title={record.usage_classification}>
                                    {record.usage_classification === 'Experimental Comparison' ? 'Comparison' : record.usage_classification}
                                </span>
                            )}

                            {record.is_human_verified ? (
                                <span className="inline-flex items-center gap-0.5 text-[8px] uppercase tracking-wider font-bold text-amber-500 bg-amber-500/10 px-1 py-0.5 rounded shrink-0 shadow-sm shadow-amber-500/10" title="Verified manually by user">
                                    <ShieldCheck className="h-2.5 w-2.5" />
                                    User Verified
                                </span>
                            ) : (
                                <span className="inline-flex items-center gap-0.5 text-[8px] uppercase tracking-wider font-bold text-indigo-400 bg-indigo-500/10 px-1 py-0.5 rounded shrink-0" title="Extracted by AI">
                                    AI Extracted
                                </span>
                            )}

                            <div className={`flex items-center gap-1 ml-auto shrink-0 transition-opacity ${confirmAction ? 'opacity-100' : 'opacity-0 group-hover/sentiment:opacity-100'}`}>
                                {canEdit && (
                                    <button type="button" onClick={(e) => startEditing('sentiment', e)} className="text-slate-500 hover:text-indigo-400 p-0.5 transition-colors" title="Edit">
                                        <Edit2 className="h-3.5 w-3.5" />
                                    </button>
                                )}

                                {record.is_human_verified && canEdit && (
                                    <div className="relative flex items-center ml-1">
                                        {confirmAction === 'revert' && (
                                            <div className="absolute right-[100%] mr-2 flex items-center gap-1 bg-white dark:bg-slate-950/80 px-1.5 py-0.5 rounded border border-amber-300 dark:border-amber-500/20 shadow-md dark:shadow-none animate-in fade-in slide-in-from-right-2 whitespace-nowrap z-20">
                                                <span className="text-[9px] text-amber-600 dark:text-amber-400 font-bold uppercase tracking-wider mx-0.5">Revert?</span>
                                                <button type="button" onClick={executeRevertToAI} disabled={isReverting} className="p-0.5 hover:bg-amber-100 dark:hover:bg-amber-500/20 text-amber-500 dark:text-amber-400 rounded transition-all" title="Confirm Revert">
                                                    {isReverting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                                                </button>
                                                <button type="button" onClick={(e) => { e.stopPropagation(); setConfirmAction(null); }} className="p-0.5 hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500 dark:text-slate-400 rounded transition-all" title="Cancel">
                                                    <X className="h-3 w-3" />
                                                </button>
                                            </div>
                                        )}
                                        <button type="button" onClick={(e) => { e.stopPropagation(); setConfirmAction('revert'); }} className={`p-0.5 transition-colors ${confirmAction === 'revert' ? 'text-amber-500 dark:text-amber-400' : 'text-slate-500 hover:text-amber-500 dark:hover:text-amber-400'}`} title="Revert to AI data">
                                            <RotateCcw className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                )}

                                {isAdmin && (
                                    <div className="relative flex items-center ml-1">
                                        {confirmAction === 'delete' && (
                                            <div className="absolute right-[100%] mr-2 flex items-center gap-1 bg-white dark:bg-slate-950/80 px-1.5 py-0.5 rounded border border-red-300 dark:border-red-500/20 shadow-md dark:shadow-none animate-in fade-in slide-in-from-right-2 whitespace-nowrap z-20">
                                                <span className="text-[9px] text-red-600 dark:text-red-400 font-bold uppercase tracking-wider mx-0.5">Delete?</span>
                                                <button type="button" onClick={executeDelete} disabled={isDeleting} className="p-0.5 hover:bg-red-50 dark:hover:bg-red-500/20 text-red-500 dark:text-red-400 rounded transition-all" title="Confirm Delete">
                                                    {isDeleting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                                                </button>
                                                <button type="button" onClick={(e) => { e.stopPropagation(); setConfirmAction(null); }} className="p-0.5 hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500 dark:text-slate-400 rounded transition-all" title="Cancel">
                                                    <X className="h-3 w-3" />
                                                </button>
                                            </div>
                                        )}
                                        <button type="button" onClick={(e) => { e.stopPropagation(); setConfirmAction('delete'); }} className={`p-0.5 transition-colors ${confirmAction === 'delete' ? 'text-red-500 dark:text-red-400' : 'text-slate-500 hover:text-red-500 dark:hover:text-red-400'}`} title="Delete">
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>

                        {record.positive_comment && (
                            !isGrouped ? (
                                <CommentWithCitedPopup comment={record.positive_comment} citedTitle={record.cited_title} />
                            ) : (
                                <div className="relative mb-3">
                                    <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-indigo-500 to-purple-500 rounded-full"></div>
                                    <p className="pl-4 text-xs text-slate-700 dark:text-slate-300 italic leading-relaxed">
                                        {record.positive_comment}
                                    </p>
                                </div>
                            )
                        )}

                        {record.sentiment_evidence && (
                            <div className="mb-4 bg-slate-50 dark:bg-slate-900/40 p-3 rounded-lg border border-slate-200 dark:border-slate-700/50 relative group/quote">
                                <div className="text-[9px] uppercase font-bold tracking-wider text-slate-500 mb-1.5 flex items-center justify-between">
                                    <div className="flex items-center gap-1.5">
                                        <div className="h-3 w-3 rounded-sm bg-slate-200 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400">”</div>
                                        Evidence Quote
                                    </div>
                                    {record.contexts && record.contexts.length > 0 && (
                                        <span className="text-[8px] bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 px-1.5 py-0.5 rounded opacity-0 group-hover/quote:opacity-100 transition-opacity">Hovering reveals context</span>
                                    )}
                                </div>
                                <p className="text-xs text-slate-700 dark:text-slate-400 leading-relaxed font-serif">
                                    "{record.sentiment_evidence}"
                                </p>

                                {/* Hover Citation Context Floating Overlay */}
                                {record.contexts && record.contexts.length > 0 && (
                                    <div className="absolute left-0 top-full pt-2 w-full z-50 opacity-0 invisible group-hover/quote:opacity-100 group-hover/quote:visible transition-all duration-200 drop-shadow-2xl">
                                        <div className="bg-white/95 dark:bg-slate-800/95 backdrop-blur-md border border-slate-200 dark:border-slate-600/50 p-3 rounded-lg shadow-xl relative">
                                            {/* Top triangle pointer */}
                                            <div className="absolute -top-2 left-6 w-4 h-4 bg-white/95 dark:bg-slate-800/95 border-t border-l border-slate-200 dark:border-slate-600/50 transform rotate-45"></div>
                                            <div className="text-[10px] uppercase font-bold tracking-wider text-indigo-600 dark:text-indigo-300 mb-2 relative z-10">Citation Contexts</div>
                                            <div className="max-h-[250px] overflow-y-auto pr-1 custom-scrollbar relative z-10">
                                                {record.contexts.map((ctx, idx) => (
                                                    <p key={idx} className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed mb-2 pb-2 border-b border-slate-100 dark:border-white/5 last:border-0 last:mb-0 font-mono bg-slate-50 dark:bg-slate-900/50 p-2 rounded">
                                                        {ctx}
                                                    </p>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </>
                )}
            </td>
        </tr>
    );
}
