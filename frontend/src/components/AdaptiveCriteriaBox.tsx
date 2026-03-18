import React, { useState } from 'react';
import { Star, ChevronDown, ChevronUp } from 'lucide-react';
import { EvaluationCriteria } from '../types';

export default function AdaptiveCriteriaBox({ criteria }: { criteria: EvaluationCriteria | null }) {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!criteria) return null;

    const renderText = (val: unknown): string => {
        if (!val) return "";
        if (typeof val === 'string') return val;
        if (Array.isArray(val)) return val.map(renderText).join(', ');
        if (typeof val === 'object') return Object.values(val).map(renderText).join(' ');
        return String(val);
    };

    return (
        <div className="glass-panel mb-10 p-6 animate-slide-in">
            <div 
                className={`flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity ${isExpanded ? 'mb-4' : ''}`}
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="p-2 bg-indigo-50 dark:bg-indigo-500/10 rounded-lg">
                    <Star className="h-5 w-5 text-indigo-500 dark:text-indigo-400" />
                </div>
                <div className="flex-1">
                    <div className="flex justify-between items-center">
                        <h2 className="text-slate-900 dark:text-white font-semibold text-lg">Domain-Adaptive Criteria</h2>
                        {isExpanded ? <ChevronUp className="h-5 w-5 text-slate-500 dark:text-slate-400" /> : <ChevronDown className="h-5 w-5 text-slate-500 dark:text-slate-400" />}
                    </div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm">AI-inferred criteria tailored to the detected research domain.</p>
                </div>
            </div>
            
            {isExpanded && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-slide-in">
                    <div className="glass-card p-4">
                        <div className="text-emerald-600 dark:text-emerald-400 text-xs uppercase tracking-wider font-semibold mb-2">Seminal Work Criteria</div>
                        <div className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">{renderText(criteria.seminal_criteria)}</div>
                    </div>
                    <div className="glass-card p-4">
                        <div className="text-amber-600 dark:text-amber-400 text-xs uppercase tracking-wider font-semibold mb-2">Notable Author Criteria</div>
                        <div className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">{renderText(criteria.notable_criteria)}</div>
                    </div>
                </div>
            )}
            {/* Always-rendered copy for print (hidden on screen when collapsed) */}
            {!isExpanded && (
                <div className="print-only-criteria grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="glass-card p-4">
                        <div className="text-emerald-600 dark:text-emerald-400 text-xs uppercase tracking-wider font-semibold mb-2">Seminal Work Criteria</div>
                        <div className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">{renderText(criteria.seminal_criteria)}</div>
                    </div>
                    <div className="glass-card p-4">
                        <div className="text-amber-600 dark:text-amber-400 text-xs uppercase tracking-wider font-semibold mb-2">Notable Author Criteria</div>
                        <div className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">{renderText(criteria.notable_criteria)}</div>
                    </div>
                </div>
            )}
        </div>
    );
}
