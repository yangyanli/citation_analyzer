import { CitationRecord } from '../types';

/* ─── helpers ──────────────────────────────────────────── */

function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
}

function sanitize(name: string) {
    return name.replace(/[^a-zA-Z0-9_-]/g, '_').replace(/_+/g, '_').slice(0, 60);
}

function today() {
    return new Date().toISOString().slice(0, 10);
}

/* ─── 1. Raw JSON ──────────────────────────────────────── */

export function exportRawJSON(records: CitationRecord[], targetName: string) {
    const data = {
        exported: new Date().toISOString(),
        target: targetName,
        total: records.length,
        records: records.map(r => ({
            citing_title: r.citing_title,
            cited_title: r.cited_title,
            year: r.year ?? null,
            venue: r.venue ?? null,
            score: r.score,
            usage_classification: r.usage_classification ?? null,
            research_domain: r.research_domain ?? null,
            is_seminal: !!r.is_seminal,
            positive_comment: r.positive_comment ?? null,
            sentiment_evidence: r.sentiment_evidence ?? null,
            citing_citation_count: r.citing_citation_count ?? null,
            notable_authors: r.notable_authors.map(a => ({ name: a.name, evidence: a.evidence })),
            url: r.url ?? null,
        })),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    downloadBlob(blob, `citations_${sanitize(targetName)}_${today()}.json`);
}

/* ─── 2. Raw CSV ───────────────────────────────────────── */

function csvEscape(val: unknown): string {
    if (val == null) return '';
    const s = String(val);
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
}

export function exportRawCSV(records: CitationRecord[], targetName: string) {
    const headers = [
        'citing_title', 'cited_title', 'year', 'venue', 'score',
        'usage_classification', 'research_domain', 'is_seminal',
        'positive_comment', 'notable_authors', 'citing_citation_count',
    ];
    const rows = records.map(r => [
        csvEscape(r.citing_title),
        csvEscape(r.cited_title),
        csvEscape(r.year),
        csvEscape(r.venue),
        csvEscape(r.score),
        csvEscape(r.usage_classification),
        csvEscape(r.research_domain),
        csvEscape(r.is_seminal ? 'Yes' : 'No'),
        csvEscape(r.positive_comment),
        csvEscape(r.notable_authors.map(a => a.name).join('; ')),
        csvEscape(r.citing_citation_count),
    ].join(','));
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    downloadBlob(blob, `citations_${sanitize(targetName)}_${today()}.csv`);
}

/* ─── 3. Domain Distribution (domains.json) ────────────── */

export function exportDomainDistribution(records: CitationRecord[], targetName: string, targetId: string) {
    // Build domain distribution with sentiment breakdown — mirrors export_domains.py
    const domainCounts: Record<string, CitationRecord[]> = {};
    records.forEach(r => {
        const d = r.research_domain;
        if (d) {
            if (!domainCounts[d]) domainCounts[d] = [];
            domainCounts[d].push(r);
        }
    });

    const domains = Object.entries(domainCounts)
        .sort(([, a], [, b]) => b.length - a.length)
        .map(([domain, recs]) => {
            // Sentiment breakdown
            const scoreCounts: Record<number, number> = {};
            recs.forEach(r => {
                const s = Math.round(Math.max(0, Math.min(10, r.score ?? 0)));
                scoreCounts[s] = (scoreCounts[s] || 0) + 1;
            });
            const sentiment = Object.entries(scoreCounts)
                .map(([score, count]) => ({ score: Number(score), count }))
                .sort((a, b) => b.score - a.score);
            return { domain, count: recs.length, sentiment };
        });

    const data = {
        target: targetName,
        target_id: targetId,
        collected: today(),
        domains,
    };

    const blob = new Blob([JSON.stringify(data, null, 2) + '\n'], { type: 'application/json' });
    downloadBlob(blob, 'domains.json');
}

/* ─── 4. Single HTML Report ────────────────────────────── */

interface DomainEntry { domain: string; count: number; color: string; }

export function exportSingleHTML(
    records: CitationRecord[],
    targetName: string,
    domainData: DomainEntry[],
) {
    const total = records.length;
    const seminal = records.filter(r => r.is_seminal).length;
    const notable = records.filter(r => r.notable_authors.length > 0).length;
    const uniqueAuthors = new Set<string>();
    records.forEach(r => r.notable_authors.forEach(a => uniqueAuthors.add(a.name)));
    const domainTotal = domainData.reduce((s, d) => s + d.count, 0);

    // Build SVG pie
    let currentAngle = -90;
    const piePaths = domainData.map(d => {
        const pct = domainTotal > 0 ? (d.count / domainTotal) * 360 : 0;
        const startAngle = currentAngle;
        const endAngle = currentAngle + pct;
        currentAngle += pct;
        const toRad = (deg: number) => (deg * Math.PI) / 180;
        const sx = 100 + 85 * Math.cos(toRad(endAngle));
        const sy = 100 + 85 * Math.sin(toRad(endAngle));
        const ex = 100 + 85 * Math.cos(toRad(startAngle));
        const ey = 100 + 85 * Math.sin(toRad(startAngle));
        const large = endAngle - startAngle > 180 ? 1 : 0;
        const path = `M 100 100 L ${sx} ${sy} A 85 85 0 ${large} 0 ${ex} ${ey} Z`;
        return `<path d="${path}" fill="${d.color}" stroke="none" opacity="0.9"/>`;
    }).join('\n');

    const pieSvg = `<svg viewBox="0 0 200 200" width="220" height="220" style="filter:drop-shadow(0 2px 8px rgba(0,0,0,0.1))">
${piePaths}
</svg>`;

    const legendHtml = domainData.map(d =>
        `<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:6px;font-size:12px;border:1px solid #e2e8f0;background:#f8fafc"><span style="width:8px;height:8px;border-radius:50%;background:${d.color};flex-shrink:0"></span>${escHtml(d.domain)} <span style="color:#94a3b8">${d.count}</span></span>`
    ).join('\n');

    // Build table rows
    const tableRows = records.map(r => {
        const authorsStr = r.notable_authors.map(a => a.name).join(', ');
        const scoreColor = r.score >= 8 ? '#059669' : r.score >= 5 ? '#d97706' : '#dc2626';
        return `<tr>
<td style="padding:10px 12px;border-bottom:1px solid #f1f5f9"><div style="font-weight:500;color:#1e293b;margin-bottom:2px">${escHtml(r.citing_title)}</div>${r.research_domain ? `<span style="display:inline-block;font-size:10px;padding:1px 6px;border-radius:4px;background:#f0f0ff;color:#6366f1;margin-top:2px">${escHtml(r.research_domain)}</span>` : ''}</td>
<td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#64748b;font-size:13px">${escHtml(r.cited_title)}</td>
<td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;text-align:center;color:#475569">${r.year ?? ''}</td>
<td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;color:#64748b">${escHtml(r.venue ?? '')}</td>
<td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;text-align:center"><span style="display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;font-weight:700;font-size:11px;color:white;background:${scoreColor}">${r.score}</span></td>
<td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-size:12px;color:#475569">${r.is_seminal ? '🌟 ' : ''}${escHtml(r.usage_classification ?? '')}</td>
<td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-size:12px;color:#475569;font-style:italic">${escHtml(r.positive_comment ?? '')}</td>
<td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-size:12px;color:#6366f1">${escHtml(authorsStr)}</td>
</tr>`;
    }).join('\n');

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Citation Analysis — ${escHtml(targetName)}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;color:#1e293b;background:#fff;line-height:1.6;padding:32px;max-width:1400px;margin:0 auto}
h1{font-size:28px;font-weight:800;letter-spacing:-0.02em;margin-bottom:4px}
.subtitle{font-size:15px;color:#64748b;margin-bottom:24px}
.metrics{display:flex;gap:16px;margin-bottom:32px;flex-wrap:wrap}
.metric{padding:16px 24px;border-radius:12px;border:1px solid #e2e8f0;background:#f8fafc;min-width:140px}
.metric-val{font-size:28px;font-weight:800;color:#6366f1}
.metric-label{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;margin-top:2px}
.chart-section{display:flex;gap:24px;align-items:flex-start;margin-bottom:32px;flex-wrap:wrap}
.chart-section h2{font-size:16px;font-weight:600;color:#475569;margin-bottom:12px}
.legend{display:flex;flex-wrap:wrap;gap:6px}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;border-bottom:2px solid #e2e8f0;font-weight:600}
.footer{margin-top:32px;padding-top:16px;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8}
@media print{
  body{padding:16px;font-size:11px}
  .metric{padding:10px 16px}
  .metric-val{font-size:22px}
  table{font-size:11px}
  thead th,td{padding:6px 8px}
  .chart-section svg{width:160px;height:160px}
}
</style>
</head>
<body>
<h1>Citation Analysis — ${escHtml(targetName)}</h1>
<p class="subtitle">Exported on ${today()} · ${total} citations analyzed</p>

<div class="metrics">
<div class="metric"><div class="metric-val">${total}</div><div class="metric-label">Total Citations</div></div>
<div class="metric"><div class="metric-val">${seminal}</div><div class="metric-label">Seminal Works</div></div>
<div class="metric"><div class="metric-val">${notable}</div><div class="metric-label">By Notable Authors</div></div>
<div class="metric"><div class="metric-val">${uniqueAuthors.size}</div><div class="metric-label">Notable Authors</div></div>
</div>

<div class="chart-section">
<div>${pieSvg}</div>
<div style="flex:1;min-width:200px">
<h2>Research Domain Distribution</h2>
<div class="legend">${legendHtml}</div>
</div>
</div>

<h2 style="font-size:16px;font-weight:600;color:#475569;margin-bottom:12px">Citation Records</h2>
<table>
<thead><tr>
<th>Citing Paper</th><th>Cites</th><th>Year</th><th>Venue</th><th>Score</th><th>Classification</th><th>Comment</th><th>Notable Authors</th>
</tr></thead>
<tbody>${tableRows}</tbody>
</table>

<div class="footer">
Generated by <a href="https://github.com/yangyanli/citation-analyzer" style="color:#6366f1">Citation Analyzer</a> · AI-driven citation analysis
</div>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    downloadBlob(blob, `citation_report_${sanitize(targetName)}_${today()}.html`);
}

function escHtml(s: string): string {
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
