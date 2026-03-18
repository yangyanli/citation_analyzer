"use client";

import { useState, useRef, useEffect, useMemo } from 'react';
import { Download, FileJson, FileSpreadsheet, Globe, FileText, ChevronDown } from 'lucide-react';
import { CitationRecord } from '../types';
import { exportRawJSON, exportRawCSV, exportDomainDistribution, exportSingleHTML } from '../lib/export';

const DOMAIN_COLORS = [
    '#818cf8', '#34d399', '#f472b6', '#fbbf24', '#60a5fa',
    '#a78bfa', '#fb923c', '#2dd4bf', '#f87171', '#c084fc',
    '#4ade80', '#38bdf8', '#e879f9', '#facc15', '#fb7185',
    '#67e8f9', '#a3e635', '#f9a8d4', '#86efac', '#fca5a1',
];

interface ExportMenuProps {
    records: CitationRecord[];
    targetName: string;
    targetId: string;
}

export default function ExportMenu({ records, targetName, targetId }: ExportMenuProps) {
    const [isOpen, setIsOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    // Close on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    // Build domain data for HTML export
    const domainData = useMemo(() => {
        const counts: Record<string, number> = {};
        records.forEach(r => {
            const d = r.research_domain;
            if (d) counts[d] = (counts[d] || 0) + 1;
        });
        return Object.entries(counts)
            .sort(([, a], [, b]) => b - a)
            .map(([domain, count], i) => ({
                domain,
                count,
                color: DOMAIN_COLORS[i % DOMAIN_COLORS.length],
            }));
    }, [records]);

    if (records.length === 0) return null;

    const items = [
        {
            icon: <FileJson className="h-4 w-4" />,
            label: 'Raw Data (JSON)',
            desc: 'Full citation records',
            action: () => exportRawJSON(records, targetName),
        },
        {
            icon: <FileSpreadsheet className="h-4 w-4" />,
            label: 'Raw Data (CSV)',
            desc: 'Spreadsheet-compatible',
            action: () => exportRawCSV(records, targetName),
        },
        {
            icon: <Globe className="h-4 w-4" />,
            label: 'Domain Distribution (JSON)',
            desc: 'Embeddable chart data (domains.json)',
            action: () => exportDomainDistribution(records, targetName, targetId),
        },
        {
            icon: <FileText className="h-4 w-4" />,
            label: 'Standalone Report (HTML)',
            desc: 'Self-contained, print-ready',
            action: () => exportSingleHTML(records, targetName, domainData),
        },
    ];

    return (
        <div className="relative z-[100] print:hidden" ref={menuRef} id="export-menu">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-xl border border-indigo-500/30 text-indigo-600 dark:text-indigo-300 hover:bg-indigo-500/10 transition-all"
                id="export-menu-trigger"
            >
                <Download className="h-4 w-4" />
                Export
                <ChevronDown className={`h-3 w-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <>
                <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
                <div className="absolute right-0 top-full mt-2 w-56 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/80 rounded-xl shadow-lg dark:shadow-[0_10px_40px_-10px_rgba(0,0,0,0.8)] z-50 py-1.5 ring-1 ring-black/5">
                    
                    {/* Raw Data Section */}
                    <div className="px-4 py-1.5 text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mt-0.5">
                        Raw Data
                    </div>
                    <button
                        onClick={() => { items[0].action(); setIsOpen(false); }}
                        className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-slate-50 dark:hover:bg-white/[0.08] transition-colors text-[13px] text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-white"
                        id="export-option-0"
                    >
                        <span className="text-indigo-500 dark:text-indigo-400">{items[0].icon}</span>
                        Raw JSON
                    </button>
                    <button
                        onClick={() => { items[1].action(); setIsOpen(false); }}
                        className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-slate-50 dark:hover:bg-white/[0.08] transition-colors text-[13px] text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-white"
                        id="export-option-1"
                    >
                        <span className="text-indigo-500 dark:text-indigo-400">{items[1].icon}</span>
                        Raw CSV
                    </button>

                    <div className="h-px bg-slate-200 dark:bg-slate-700/50 my-1.5" />

                    {/* Reports Section */}
                    <div className="px-4 py-1.5 text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mt-0.5">
                        Reports
                    </div>
                    <button
                        onClick={() => { items[2].action(); setIsOpen(false); }}
                        className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-slate-50 dark:hover:bg-white/[0.08] transition-colors text-[13px] text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-white"
                        id="export-option-2"
                    >
                        <span className="text-indigo-500 dark:text-indigo-400">{items[2].icon}</span>
                        Domain Distribution
                    </button>
                    <button
                        onClick={() => { items[3].action(); setIsOpen(false); }}
                        className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-slate-50 dark:hover:bg-white/[0.08] transition-colors text-[13px] text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-white"
                        id="export-option-3"
                    >
                        <span className="text-indigo-500 dark:text-indigo-400">{items[3].icon}</span>
                        Standalone HTML
                    </button>
                </div>
                </>
            )}
        </div>
    );
}
