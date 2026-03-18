"use client";

import { useState, useMemo, useEffect, useRef } from 'react';

import { CitationRecord } from '../types';

interface DomainChartProps {
    records: CitationRecord[];
    selectedDomain: string | null;
    onSelectDomain: (domain: string | null) => void;
}

const DOMAIN_COLORS = [
    '#818cf8', '#34d399', '#f472b6', '#fbbf24', '#60a5fa',
    '#a78bfa', '#fb923c', '#2dd4bf', '#f87171', '#c084fc',
    '#4ade80', '#38bdf8', '#e879f9', '#facc15', '#fb7185',
    '#67e8f9', '#a3e635', '#f9a8d4', '#86efac', '#fca5a1',
];

// Sentiment score colors: 0 (worst) → 10 (best)
const SCORE_COLORS: Record<number, string> = {
    0: '#dc2626',  // red-600
    1: '#ef4444',  // red-500
    2: '#f97316',  // orange-500
    3: '#fb923c',  // orange-400
    4: '#f59e0b',  // amber-500
    5: '#eab308',  // yellow-500
    6: '#a3e635',  // lime-400
    7: '#22d3ee',  // cyan-400
    8: '#34d399',  // emerald-400
    9: '#10b981',  // emerald-500
    10: '#059669', // emerald-600
};

const SCORE_LABELS: Record<number, string> = {
    0: 'Strongly Negative',
    1: 'Very Negative',
    2: 'Negative',
    3: 'Somewhat Negative',
    4: 'Slightly Negative',
    5: 'Neutral',
    6: 'Slightly Positive',
    7: 'Positive',
    8: 'Very Positive',
    9: 'Highly Positive',
    10: 'Exceptionally Positive',
};

function DomainLegendItem({ d, selectedDomain, onSelectDomain, setLegendHoveredDomain }: {
    d: { domain: string, count: number, color: string },
    selectedDomain: string | null,
    onSelectDomain: (domain: string | null) => void,
    setLegendHoveredDomain: (domain: string | null) => void
}) {
    const textRef = useRef<HTMLSpanElement>(null);
    const [isTruncated, setIsTruncated] = useState(false);

    useEffect(() => {
        if (textRef.current) {
            setIsTruncated(textRef.current.scrollWidth > textRef.current.clientWidth);
        }
    }, [d.domain]);

    return (
        <button
            onClick={() => onSelectDomain(selectedDomain === d.domain ? null : d.domain)}
            onMouseEnter={() => { if (!selectedDomain) setLegendHoveredDomain(d.domain); }}
            onMouseLeave={() => setLegendHoveredDomain(null)}
            className={`group relative flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                selectedDomain === d.domain
                    ? 'bg-slate-800 border-slate-700 text-white dark:bg-white/10 dark:border-white/20 dark:text-white'
                    : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100 hover:border-slate-300 dark:bg-white/[0.02] dark:border-white/[0.06] dark:text-slate-300 dark:hover:bg-white/[0.06] dark:hover:border-white/10'
            } ${selectedDomain && selectedDomain !== d.domain ? 'opacity-40' : ''}`}
            data-domain={d.domain}
        >
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
            <span ref={textRef} className="truncate max-w-[160px] block" style={{ maxWidth: '160px' }}>{d.domain}</span>
            <span className="text-slate-500 ml-1 shrink-0">{d.count}</span>
            {isTruncated && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1 bg-slate-800 dark:bg-slate-700 text-white text-[11px] rounded shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-[100] pointer-events-none whitespace-nowrap">
                    {d.domain}
                    <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800 dark:border-t-slate-700" />
                </div>
            )}
        </button>
    );
}

export default function DomainChart({ records, selectedDomain, onSelectDomain }: DomainChartProps) {
    const [hoveredDomain, setHoveredDomain] = useState<string | null>(null);
    const [legendHoveredDomain, setLegendHoveredDomain] = useState<string | null>(null);
    const [hoveredScore, setHoveredScore] = useState<number | null>(null);

    // ── Domain-level data ──
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

    const domainTotal = useMemo(() => domainData.reduce((s, d) => s + d.count, 0), [domainData]);

    // ── Sentiment breakdown for the active domain (selected or legend-hovered) ──
    const activeDomain = selectedDomain || legendHoveredDomain;

    // Clear stale sentiment hover when switching domains
    useEffect(() => { setHoveredScore(null); }, [activeDomain]);
    const sentimentData = useMemo(() => {
        if (!activeDomain) return [];
        const counts: Record<number, number> = {};
        records.forEach(r => {
            if (r.research_domain !== activeDomain) return;
            const s = Math.round(Math.max(0, Math.min(10, r.score ?? 0)));
            counts[s] = (counts[s] || 0) + 1;
        });
        return Object.entries(counts)
            .map(([score, count]) => ({ score: Number(score), count }))
            .sort((a, b) => b.score - a.score); // 10 → 0 for counter-clockwise pie
    }, [records, activeDomain]);

    const sentimentTotal = useMemo(() => sentimentData.reduce((s, d) => s + d.count, 0), [sentimentData]);

    // ── Pie chart segments (generic helper) ──
    const buildSegments = <T extends { count: number }>(data: T[], total: number) => {
        const segments: (T & { startAngle: number; endAngle: number; percentage: number })[] = [];
        let currentAngle = -90;
        data.forEach(d => {
            const percentage = total > 0 ? (d.count / total) * 100 : 0;
            const angle = total > 0 ? (d.count / total) * 360 : 0;
            segments.push({
                ...d,
                startAngle: currentAngle,
                endAngle: currentAngle + angle,
                percentage,
            });
            currentAngle += angle;
        });
        return segments;
    };

    const domainSegments = useMemo(() => buildSegments(domainData, domainTotal), [domainData, domainTotal]);

    // Counter-clockwise segments for sentiment pie (angles go negative)
    const sentimentSegments = useMemo(() => {
        const segments: (typeof sentimentData[number] & { startAngle: number; endAngle: number; percentage: number })[] = [];
        let currentAngle = -90; // start from top
        sentimentData.forEach(d => {
            const percentage = sentimentTotal > 0 ? (d.count / sentimentTotal) * 100 : 0;
            const angle = sentimentTotal > 0 ? (d.count / sentimentTotal) * 360 : 0;
            segments.push({
                ...d,
                startAngle: currentAngle - angle, // go counter-clockwise
                endAngle: currentAngle,
                percentage,
            });
            currentAngle -= angle;
        });
        return segments;
    }, [sentimentData, sentimentTotal]);

    if (domainData.length === 0) return null;

    // ── SVG helpers ──
    const polarToCartesian = (cx: number, cy: number, r: number, angleDeg: number) => {
        const rad = (angleDeg * Math.PI) / 180;
        return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
    };

    const describeArc = (cx: number, cy: number, r: number, startAngle: number, endAngle: number) => {
        // Handle full circle (single segment covering 100%) — SVG arc can't draw 360°
        const sweep = Math.abs(endAngle - startAngle);
        if (sweep >= 359.99) {
            return `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy} A ${r} ${r} 0 1 1 ${cx - r} ${cy} Z`;
        }
        const start = polarToCartesian(cx, cy, r, endAngle);
        const end = polarToCartesian(cx, cy, r, startAngle);
        const largeArcFlag = sweep > 180 ? 1 : 0;
        return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y} Z`;
    };

    // Which view to show
    const showSentiment = !!activeDomain && sentimentData.length > 0;

    return (
        <div className="glass-panel p-6 mb-8 animate-slide-in" id="domain-chart-container">
            <div className="flex items-center gap-3 mb-6">
                <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Research Domain Distribution of Citations</h2>
                <span className="text-sm font-medium px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20">
                    {domainData.length} domains
                </span>
            </div>

            <div className="flex flex-col lg:flex-row items-center gap-8">
                {/* Pie Chart + color bar column */}
                <div className="w-56 shrink-0 flex flex-col items-center">
                    <div className={`text-xs text-slate-500 dark:text-slate-400 mb-2 text-center transition-opacity duration-300 ${showSentiment ? 'opacity-100' : 'opacity-0'}`}>
                        How They Cite
                    </div>
                    <div className="relative w-56 h-56">
                    <svg viewBox="0 0 200 200" className="w-full h-full" style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.3))' }}>
                        {showSentiment ? (
                            /* ── Sentiment pie ── */
                            sentimentSegments.map((seg, i) => {
                                const isHovered = hoveredScore === seg.score;
                                const scale = isHovered ? 'scale(1.04)' : 'scale(1)';
                                return (
                                    <path
                                        key={seg.score}
                                        d={describeArc(100, 100, 85, seg.startAngle, seg.endAngle)}
                                        fill={SCORE_COLORS[seg.score] || '#64748b'}
                                        stroke="none"
                                        opacity={isHovered ? 1 : 0.85}
                                        style={{
                                            transition: 'all 0.2s ease',
                                            transform: scale,
                                            transformOrigin: '100px 100px',
                                            cursor: 'default',
                                            animation: `sentimentFadeIn 0.35s ease-out ${i * 0.07}s both`,
                                        }}
                                        onMouseEnter={() => setHoveredScore(seg.score)}
                                        onMouseLeave={() => setHoveredScore(null)}
                                        data-score={seg.score}
                                    />
                                );
                            })
                        ) : (
                            /* ── Domain pie ── */
                            domainSegments.map((seg) => {
                                const isHovered = hoveredDomain === seg.domain;
                                const isSelected = selectedDomain === seg.domain;
                                const scale = (isHovered || isSelected) ? 'scale(1.04)' : 'scale(1)';
                                return (
                                    <path
                                        key={seg.domain}
                                        d={describeArc(100, 100, 85, seg.startAngle, seg.endAngle)}
                                        fill={seg.color}
                                        stroke="none"
                                        opacity={selectedDomain && selectedDomain !== seg.domain ? 0.3 : (isHovered ? 1 : 0.85)}
                                        style={{ transition: 'all 0.2s ease', transform: scale, transformOrigin: '100px 100px', cursor: 'pointer' }}
                                        onMouseEnter={() => setHoveredDomain(seg.domain)}
                                        onMouseLeave={() => setHoveredDomain(null)}
                                        onClick={() => onSelectDomain(selectedDomain === seg.domain ? null : seg.domain)}
                                        data-domain={seg.domain}
                                    />
                                );
                            })
                        )}

                    </svg>

                    {/* Hover tooltip — domain view */}
                    {!showSentiment && hoveredDomain && (() => {
                        const seg = domainSegments.find(s => s.domain === hoveredDomain);
                        if (!seg) return null;
                        return (
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-full mt-[-8px] bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl pointer-events-none z-50 whitespace-nowrap">
                                <span className="font-semibold text-slate-900 dark:text-white">{seg.domain}</span>
                                <span className="text-slate-500 dark:text-slate-400 ml-2">{seg.count} ({seg.percentage.toFixed(1)}%)</span>
                            </div>
                        );
                    })()}

                    {/* Hover tooltip — sentiment view */}
                    {showSentiment && hoveredScore !== null && (() => {
                        const seg = sentimentSegments.find(s => s.score === hoveredScore);
                        if (!seg) return null;
                        return (
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-full mt-[-8px] bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl pointer-events-none z-50 whitespace-nowrap">
                                <span className="font-semibold text-slate-900 dark:text-white">{seg.score}/10</span>
                                <span className="text-slate-600 dark:text-slate-500 ml-1.5">{SCORE_LABELS[seg.score]}</span>
                                <span className="text-slate-500 dark:text-slate-400 ml-2">{seg.count} ({seg.percentage.toFixed(1)}%)</span>
                            </div>
                        );
                    })()}
                    </div>
                    {/* Sentiment color scale — below pie, same width */}
                    <div className={`mt-3 w-full ${showSentiment ? 'opacity-100' : 'opacity-0'}`} id="sentiment-color-bar">
                        <div className="flex items-end rounded-full overflow-hidden border border-slate-200 dark:border-white/[0.06]">
                            {Array.from({ length: 11 }, (_, idx) => {
                                const score = 10 - idx;
                                const hasData = showSentiment && sentimentData.some(d => d.score === score);
                                const isHovered = hoveredScore === score;
                                return (
                                    <div
                                        key={score}
                                        className="transition-all duration-300"
                                        style={{
                                            flex: '1 1 0',
                                            height: '12px',
                                            backgroundColor: SCORE_COLORS[score],
                                            opacity: hoveredScore !== null
                                                ? (isHovered ? 1 : 0.3)
                                                : (hasData ? 0.9 : 0.25),
                                            transformOrigin: 'bottom',
                                            ...(showSentiment ? { animation: `segmentReveal 0.35s ease-out ${idx * (sentimentData.length * 0.07 / 11)}s both` } : {}),
                                        }}
                                        onMouseEnter={() => showSentiment && hasData && setHoveredScore(score)}
                                        onMouseLeave={() => setHoveredScore(null)}
                                        title={`${score}/10 ${SCORE_LABELS[score]}`}
                                    />
                                );
                            })}
                        </div>
                        <div className="flex justify-between mt-1 px-0.5">
                            <span className="text-[9px] text-slate-500">Praise</span>
                            <span className="text-[9px] text-slate-500">Critical</span>
                        </div>
                    </div>
                </div>

                {/* Legend — always shows domains */}
                <div className="flex flex-wrap gap-2 max-h-56 overflow-y-auto flex-1" id="domain-legend">
                    {domainData.map(d => (
                        <DomainLegendItem
                            key={d.domain}
                            d={d}
                            selectedDomain={selectedDomain}
                            onSelectDomain={onSelectDomain}
                            setLegendHoveredDomain={setLegendHoveredDomain}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
