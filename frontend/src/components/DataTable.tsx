"use client";

import { useState, useMemo, useEffect } from 'react';
import { Trophy, ArrowUpDown, Search, SlidersHorizontal } from 'lucide-react';
import CitationRow from './CitationRow';
import { CitationRecord } from '../types';
import 'katex/dist/katex.min.css';
import Latex from 'react-latex-next';

export default function DataTable({
    records,
    hideToggles = false,
    hideGroupToggle = false,
    defaultGrouped = false,
    onDeleteCitation,
    onUpdateCitation
}: {
    records: CitationRecord[],
    hideToggles?: boolean,
    hideGroupToggle?: boolean,
    defaultGrouped?: boolean,
    onDeleteCitation?: (id: string) => void,
    onUpdateCitation?: (id: string, updates: Partial<CitationRecord>) => void
}) {
    const [sortField, setSortField] = useState<string>('score');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

    // Grouping is on by default for Author mode, off for Paper mode
    const [isGrouped, setIsGrouped] = useState<boolean>(defaultGrouped);
    const [excludeSelfCitations, setExcludeSelfCitations] = useState<boolean>(true);
    const [showSignificantOnly, setShowSignificantOnly] = useState<boolean>(false);
    const [searchQuery, setSearchQuery] = useState<string>('');
    const [searchFields, setSearchFields] = useState<Record<string, boolean>>({
        title: true, authors: true, venue: true, domain: true, classification: true, comment: true
    });
    const [showFieldChips, setShowFieldChips] = useState(false);

    // Pagination state
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [pageSize, setPageSize] = useState<number>(10);

    const filteredRecords = useMemo(() => {
        return records.filter(r => {
            if (excludeSelfCitations && r.is_self_citation) return false;
            if (showSignificantOnly && !r.is_seminal && (!r.notable_authors || r.notable_authors.length === 0)) return false;
            if (searchQuery) {
                const q = searchQuery.toLowerCase();
                const matchesTitle = searchFields.title && (r.citing_title?.toLowerCase().includes(q) || r.cited_title?.toLowerCase().includes(q));
                const matchesVenue = searchFields.venue && r.venue?.toLowerCase().includes(q);
                const matchesClassification = searchFields.classification && r.usage_classification?.toLowerCase().includes(q);
                const matchesComment = searchFields.comment && r.positive_comment?.toLowerCase().includes(q);
                const matchesAuthor = searchFields.authors && r.notable_authors?.some(a => a.name.toLowerCase().includes(q));
                const matchesDomain = searchFields.domain && r.research_domain?.toLowerCase().includes(q);
                if (!matchesTitle && !matchesVenue && !matchesClassification && !matchesComment && !matchesAuthor && !matchesDomain) return false;
            }
            return true;
        });
    }, [records, excludeSelfCitations, showSignificantOnly, searchQuery, searchFields]);

    useEffect(() => {
        console.log("DataTable rendered. records.length:", records.length, "filteredRecords.length:", filteredRecords.length);
    }, [records, filteredRecords]);

    // Reset to page 1 when filters or sort change
    useEffect(() => {
        const timer = setTimeout(() => setCurrentPage(1), 0);
        return () => clearTimeout(timer);
    }, [excludeSelfCitations, showSignificantOnly, sortField, sortDirection, pageSize, searchQuery]);

    // Compute author stats across filtered records
    const authorStats = useMemo(() => {
        const stats: Record<string, { total: number; byPaper: Record<string, number> }> = {};
        filteredRecords.forEach(r => {
            r.notable_authors.forEach(a => {
                if (!stats[a.name]) stats[a.name] = { total: 0, byPaper: {} };
                stats[a.name].total += 1;
                stats[a.name].byPaper[r.cited_title] = (stats[a.name].byPaper[r.cited_title] || 0) + 1;
            });
        });
        return stats;
    }, [filteredRecords]);

    const handleSort = (field: string) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('desc');
        }
    };

    const sortedRecords = [...filteredRecords].sort((a, b) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        let valA: any = a[sortField as keyof CitationRecord];
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        let valB: any = b[sortField as keyof CitationRecord];

        // Special handling for some fields
        if (sortField === 'notable_authors_length') {
            valA = a.notable_authors?.length || 0;
            valB = b.notable_authors?.length || 0;
        } else if (sortField === 'score') {
            valA = a.score || 0;
            valB = b.score || 0;
        } else if (sortField === 'citing_citation_count') {
            valA = a.citing_citation_count || 0;
            valB = b.citing_citation_count || 0;
        } else if (sortField === 'year') {
            valA = a.year || 0;
            valB = b.year || 0;
        } else if (sortField === 'venue') {
            valA = a.venue || "";
            valB = b.venue || "";
        } else if (sortField === 'citing_title') {
            valA = a.citing_title || "";
            valB = b.citing_title || "";
        } else if (sortField === 'is_seminal') {
            valA = a.is_seminal ? 1 : 0;
            valB = b.is_seminal ? 1 : 0;
        }

        if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });

    // Group records if toggle is active
    const groupedRecords = useMemo(() => {
        const startIndex = (currentPage - 1) * pageSize;
        const paginatedRecords = sortedRecords.slice(startIndex, startIndex + pageSize);

        if (!isGrouped) return { "All Citations": paginatedRecords };

        const groups: Record<string, CitationRecord[]> = {};
        paginatedRecords.forEach(r => {
            if (!groups[r.cited_title]) groups[r.cited_title] = [];
            groups[r.cited_title].push(r);
        });
        return groups;
    }, [sortedRecords, isGrouped, currentPage, pageSize]);

    return (
        <div className="glass-panel overflow-hidden mb-8 bg-white dark:bg-slate-900/40">
            <div className="p-6 border-b border-slate-200 dark:border-white/[0.05] bg-slate-50 dark:bg-slate-900/30">
                {/* Top Row: Title */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div className="flex items-center gap-3">
                        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Citation Analysis Records</h2>
                        <div className="text-sm font-medium px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20">
                            {filteredRecords.length !== records.length ? (
                                <span className="inline-flex items-center gap-1">
                                    <span
                                        data-tooltip="Records visible after applying current filters"
                                        className="underline decoration-dotted decoration-indigo-300 dark:decoration-indigo-400/40 underline-offset-2"
                                    >{filteredRecords.length}</span>
                                    <span className="text-indigo-400 dark:text-indigo-400/60">/</span>
                                    <span
                                        data-tooltip="Total citation records analyzed by the pipeline"
                                        className="underline decoration-dotted decoration-indigo-300 dark:decoration-indigo-400/40 underline-offset-2"
                                    >{records.length}</span>
                                    {' '}Results
                                </span>
                            ) : (
                                <span>{records.length} Results</span>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <div className="print:hidden p-6 border-b border-slate-200 dark:border-white/[0.05] bg-slate-50 dark:bg-slate-900/30">
                {/* Bottom Row: Search & Filters */}
                <div className="flex flex-col md:flex-row lg:items-center justify-between gap-4">
                    {/* Search box + field chips */}
                    <div className="flex flex-col gap-2 w-full md:max-w-md lg:w-96 shrink-0">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                            <input
                                type="text"
                                placeholder={`Search ${Object.entries(searchFields).filter(([,v]) => v).map(([k]) => k).join(', ')}...`}
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-16 py-2.5 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/[0.08] text-slate-800 dark:text-white rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 placeholder:text-slate-400 dark:placeholder:text-slate-500 shadow-sm dark:shadow-inner transition-all"
                            />
                            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                                {searchQuery && (
                                    <button onClick={() => setSearchQuery('')} className="text-slate-500 hover:text-white transition-colors text-sm">
                                        ✕
                                    </button>
                                )}
                                <button
                                    onClick={() => setShowFieldChips(!showFieldChips)}
                                    className={`p-1 rounded transition-colors ${showFieldChips ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10' : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'}`}
                                    title="Toggle search field filters"
                                    id="search-fields-toggle"
                                >
                                    <SlidersHorizontal className="h-3.5 w-3.5" />
                                </button>
                            </div>
                        </div>
                        {showFieldChips && (
                            <div className="flex flex-wrap gap-1.5 animate-in fade-in slide-in-from-top-1" id="search-field-chips">
                                {Object.entries({ title: 'Title', authors: 'Authors', venue: 'Venue', domain: 'Domain', classification: 'Usage', comment: 'Comment' }).map(([key, label]) => (
                                    <button
                                        key={key}
                                        onClick={() => setSearchFields(prev => ({ ...prev, [key]: !prev[key] }))}
                                        className={`px-2 py-0.5 rounded-full text-[10px] font-medium border transition-all ${
                                            searchFields[key]
                                                ? 'bg-indigo-50 dark:bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 border-indigo-200 dark:border-indigo-500/25 hover:bg-indigo-100 dark:hover:bg-indigo-500/25'
                                                : 'bg-slate-50 dark:bg-slate-800/50 text-slate-400 dark:text-slate-500 border-slate-200 dark:border-white/[0.06] hover:text-slate-600 dark:hover:text-slate-400 hover:border-slate-300 dark:hover:border-white/10 line-through'
                                        }`}
                                        data-search-field={key}
                                    >
                                        {label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {!hideToggles && (
                        <div className="flex flex-row flex-wrap gap-4 sm:gap-6 items-center bg-slate-50 dark:bg-slate-900/40 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-white/[0.04]">
                            {/* Significant Only Toggle */}
                            <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                                <label className="flex items-center cursor-pointer gap-2 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">
                                    <input
                                        type="checkbox"
                                        className="w-4 h-4 rounded border-slate-600 bg-slate-900 focus:ring-indigo-500 checked:bg-indigo-500"
                                        checked={showSignificantOnly}
                                        onChange={(e) => setShowSignificantOnly(e.target.checked)}
                                    />
                                    <span>Representative Citations</span>
                                </label>
                            </div>

                            {/* Filter Self-Citations Toggle */}
                            <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                                <label className="flex items-center cursor-pointer gap-2 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">
                                    <input
                                        type="checkbox"
                                        className="w-4 h-4 rounded border-slate-600 bg-slate-900 focus:ring-indigo-500 checked:bg-indigo-500"
                                        checked={excludeSelfCitations}
                                        onChange={(e) => setExcludeSelfCitations(e.target.checked)}
                                    />
                                    <span>Exclude Self-Citations</span>
                                </label>
                            </div>

                            {/* Group Settings Toggle */}
                            {!hideGroupToggle && (
                                <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                                    <label className="flex items-center cursor-pointer gap-2 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">
                                        <input
                                            type="checkbox"
                                            className="w-4 h-4 rounded border-slate-600 bg-slate-900 focus:ring-indigo-500 checked:bg-indigo-500"
                                            checked={isGrouped}
                                            onChange={(e) => setIsGrouped(e.target.checked)}
                                        />
                                        <span>Group by Paper</span>
                                    </label>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Mobile sort control — visible only on small screens */}
                    <div className="flex md:hidden items-center gap-2 text-sm text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/40 px-3 py-2 rounded-xl border border-slate-200 dark:border-white/[0.04]">
                        <ArrowUpDown className="h-3.5 w-3.5 shrink-0 text-slate-400 dark:text-slate-500" />
                        <select
                            className="bg-transparent border-none text-slate-800 dark:text-white text-sm focus:outline-none focus:ring-0 flex-1 appearance-none cursor-pointer"
                            value={sortField}
                            onChange={(e) => { setSortField(e.target.value); setSortDirection('desc'); }}
                        >
                            <option value="score" className="bg-white dark:bg-slate-900">Sentiment</option>
                            <option value="citing_title" className="bg-white dark:bg-slate-900">Citing Paper</option>
                            <option value="notable_authors_length" className="bg-white dark:bg-slate-900">Rep. Citations</option>
                            <option value="year" className="bg-white dark:bg-slate-900">Year</option>
                            <option value="venue" className="bg-white dark:bg-slate-900">Venue</option>
                        </select>
                        <button
                            onClick={() => setSortDirection(d => d === 'asc' ? 'desc' : 'asc')}
                            className="text-xs px-2 py-1 rounded bg-white/[0.05] border border-white/[0.1] text-slate-300 hover:text-white hover:bg-white/[0.1] transition-colors whitespace-nowrap"
                        >
                            {sortDirection === 'desc' ? '↓ Desc' : '↑ Asc'}
                        </button>
                    </div>
                </div>
            </div>

            {filteredRecords.length === 0 ? (
                <div className="p-16 text-center text-slate-500">
                    <Trophy className="h-12 w-12 mx-auto mb-4 opacity-20" />
                    <p className="text-lg">No citations meeting 'Representative Citations' (seminal discoveries or notable authors) found.</p>
                    <p className="text-sm">Run the Python backend tool to populate the database.</p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                    {Object.entries(groupedRecords).map(([groupName, groupData]) => (
                        <div key={groupName} className={isGrouped ? "mb-8 last:mb-0" : ""}>
                            {isGrouped && (
                                <div className="px-6 py-4 bg-slate-50 dark:bg-white/[0.03] border-b border-slate-200 dark:border-white/[0.05]">
                                    <h3 className="text-lg font-medium text-indigo-600 dark:text-indigo-300">
                                        <span className="text-slate-500 dark:text-slate-400 font-normal mr-2">Cited Paper:</span>
                                        <Latex>{`"${groupName}"`}</Latex>
                                    </h3>
                                    <div className="text-sm text-slate-500 mt-1">{groupData.length} Notable Citations Found</div>
                                </div>
                            )}
                            <table className="citation-table w-full text-left border-collapse">
                                <thead>
                                    <tr className="border-b border-slate-200 dark:border-white/[0.05] text-slate-500 dark:text-slate-400 text-sm">
                                        <th className="p-6 font-medium cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors" onClick={() => handleSort('citing_title')}>
                                            <div className="flex items-center space-x-2"><span>Citing Paper</span><ArrowUpDown className="h-3 w-3 opacity-50" /></div>
                                        </th>
                                        <th className="p-6 font-medium cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors" onClick={() => handleSort('notable_authors_length')}>
                                            <div className="flex items-center space-x-2"><span>Representative Citations</span><ArrowUpDown className="h-3 w-3 opacity-50" /></div>
                                        </th>
                                        <th className="p-6 font-medium cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors" onClick={() => handleSort('year')}>
                                            <div className="flex items-center space-x-2"><span>Year</span><ArrowUpDown className="h-3 w-3 opacity-50" /></div>
                                        </th>
                                        <th className="p-6 font-medium cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors" onClick={() => handleSort('venue')}>
                                            <div className="flex items-center space-x-2"><span>Venue</span><ArrowUpDown className="h-3 w-3 opacity-50" /></div>
                                        </th>

                                        <th className="p-6 font-medium cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors" onClick={() => handleSort('score')}>
                                            <div className="flex items-center space-x-2"><span>Sentiment</span><ArrowUpDown className="h-3 w-3 opacity-50" /></div>
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-white/[0.05]">
                                    {groupData.map((record) => (
                                        <CitationRow
                                            key={record.citation_id}
                                            record={record}
                                            isGrouped={isGrouped}
                                            authorStats={authorStats}
                                            onDelete={onDeleteCitation}
                                            onUpdate={onUpdateCitation}
                                        />
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ))}

                    {/* Pagination Controls */}
                    {sortedRecords.length > 0 && (
                        <div className="print:hidden p-4 sm:px-6 border-t border-slate-200 dark:border-white/[0.05] flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50 dark:bg-slate-900/30">
                            <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
                                <span>Show</span>
                                <select
                                    className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white text-sm rounded focus:ring-indigo-500 focus:border-indigo-500 p-1"
                                    value={pageSize}
                                    onChange={(e) => setPageSize(Number(e.target.value))}
                                >
                                    <option value={10}>10</option>
                                    <option value={20}>20</option>
                                    <option value={50}>50</option>
                                    <option value={100}>100</option>
                                </select>
                                <span>per page</span>
                            </div>

                            <div className="flex items-center gap-4 text-sm">
                                <span className="text-slate-500 dark:text-slate-400">
                                    Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, sortedRecords.length)} of {sortedRecords.length} results
                                </span>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                        disabled={currentPage === 1}
                                        className="px-3 py-1 rounded bg-white dark:bg-white/[0.05] border border-slate-200 dark:border-white/[0.1] text-slate-700 dark:text-white hover:bg-slate-50 dark:hover:bg-white/[0.1] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        Previous
                                    </button>
                                    <button
                                        onClick={() => setCurrentPage(p => Math.min(Math.ceil(sortedRecords.length / pageSize), p + 1))}
                                        disabled={currentPage >= Math.ceil(sortedRecords.length / pageSize)}
                                        className="px-3 py-1 rounded bg-white dark:bg-white/[0.05] border border-slate-200 dark:border-white/[0.1] text-slate-700 dark:text-white hover:bg-slate-50 dark:hover:bg-white/[0.1] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        Next
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
