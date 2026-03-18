'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/app/context/AuthContext';
import { useRouter } from 'next/navigation';

interface LogEntry {
  id: string | number;
  timestamp: string;
  is_fallback: boolean;
  stage: string;
  prompt_text: string;
  response_text: string;
  system_user_id: string;
  run_id: string;
  target_id: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
}

export default function LLMLogsAdmin() {
    const { user, loading: authLoading } = useAuth();
    const router = useRouter();

    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [limit] = useState(100);
    const [offset, setOffset] = useState(0);
    const [fallbackOnly, setFallbackOnly] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);

    useEffect(() => {
        if (!authLoading) {
            if (!user) {
                router.push('/login');
            } else if (user.role !== 'admin' && user.role !== 'super_admin') {
                router.push('/analyze');
            } else {
                fetchLogs();
            }
        }
    }, [authLoading, user, limit, offset, fallbackOnly]);

    const fetchLogs = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/admin/llm-logs?limit=${limit}&offset=${offset}&fallback_only=${fallbackOnly}`);
            const data = await res.json();
            if (res.ok) {
                setLogs(data.logs);
                setTotal(data.total);
            } else {
                setError(data.error);
            }
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : String(err));
        } finally {
            setLoading(false);
        }
    };

    if (authLoading || (loading && logs.length === 0)) return <div className="p-8 text-slate-900 dark:text-white">Loading logs...</div>;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8">
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white border-b border-slate-200 dark:border-white/10 pb-4">LLM Request Logs</h1>

            {error && <div className="text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 p-4 rounded-md">{error}</div>}

            <div className="flex items-center space-x-4 pb-4">
                <label className="flex items-center space-x-2 text-sm text-slate-700 dark:text-slate-300">
                    <input
                        type="checkbox"
                        checked={fallbackOnly}
                        onChange={(e) => {
                            setFallbackOnly(e.target.checked);
                            setOffset(0);
                        }}
                        className="rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-blue-600 focus:ring-blue-500"
                    />
                    <span>Show Fallback Operations Only</span>
                </label>

                <span className="text-sm text-slate-500 dark:text-slate-400">
                    Total: {total}
                </span>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-lg shadow ring-1 ring-slate-200 dark:ring-white/10 overflow-hidden">
                <table className="min-w-full divide-y divide-slate-200 dark:divide-white/10">
                    <thead className="bg-slate-50 dark:bg-slate-950/50">
                        <tr>
                            <th className="px-3 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Timestamp</th>
                            <th className="px-3 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Type</th>
                            <th className="px-3 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Stage</th>
                            <th className="px-3 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Input Text Preview</th>
                            <th className="px-3 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Response Text Preview</th>
                            <th className="px-3 py-3 text-right text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">User</th>
                            <th className="px-3 py-3 text-right text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">View</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-white/10 bg-white dark:bg-slate-900">
                        {logs.map((log) => (
                            <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors">
                                <td className="whitespace-nowrap px-3 py-4 text-sm text-slate-500 dark:text-slate-400">
                                    {new Date(log.timestamp).toLocaleString()}
                                </td>
                                <td className="whitespace-nowrap px-3 py-4 text-sm text-slate-500 dark:text-slate-400">
                                    {log.is_fallback ? (
                                        <span className="inline-flex items-center rounded-md bg-amber-50 dark:bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-800 dark:text-amber-400 ring-1 ring-inset ring-amber-600/20">Fallback</span>
                                    ) : (
                                        <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-400 ring-1 ring-inset ring-emerald-600/20">API</span>
                                    )}
                                </td>
                                <td className="whitespace-nowrap px-3 py-4 text-sm text-slate-900 dark:text-white font-medium">
                                    {log.stage}
                                </td>
                                <td className="px-3 py-4 text-sm text-slate-500 dark:text-slate-400 max-w-xs truncate">
                                    {log.prompt_text?.substring(0, 50)}...
                                </td>
                                <td className="px-3 py-4 text-sm text-slate-500 dark:text-slate-400 max-w-xs truncate">
                                    {log.response_text?.substring(0, 50)}...
                                </td>
                                <td className="whitespace-nowrap px-3 py-4 text-sm text-slate-500 dark:text-slate-400 text-right">
                                    {log.system_user_id || 'System'}
                                </td>
                                <td className="whitespace-nowrap px-3 py-4 text-sm text-right">
                                    <button
                                        onClick={() => setSelectedLog(log)}
                                        className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300 font-medium transition-colors"
                                    >
                                        Details
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between border-t border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-4 py-3 sm:px-6 shadow rounded-lg">
                <div className="flex flex-1 justify-between sm:hidden">
                    <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0} className="relative inline-flex items-center rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">Previous</button>
                    <button onClick={() => setOffset(offset + limit)} disabled={offset + limit >= total} className="relative ml-3 inline-flex items-center rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">Next</button>
                </div>
                <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                    <div>
                        <p className="text-sm text-slate-700 dark:text-slate-300">
                            Showing <span className="font-medium">{offset + 1}</span> to <span className="font-medium">{Math.min(offset + limit, total)}</span> of <span className="font-medium">{total}</span> results
                        </p>
                    </div>
                    <div>
                        <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                            <button
                                onClick={() => setOffset(Math.max(0, offset - limit))}
                                disabled={offset === 0}
                                className="relative inline-flex items-center rounded-l-md px-2 py-2 text-slate-400 ring-1 ring-inset ring-slate-300 dark:ring-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                            >
                                <span className="sr-only">Previous</span>
                                ←
                            </button>
                            <button
                                onClick={() => setOffset(offset + limit)}
                                disabled={offset + limit >= total}
                                className="relative inline-flex items-center rounded-r-md px-2 py-2 text-slate-400 ring-1 ring-inset ring-slate-300 dark:ring-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                            >
                                <span className="sr-only">Next</span>
                                →
                            </button>
                        </nav>
                    </div>
                </div>
            </div>

            {/* View Modal */}
            {selectedLog && (
                <div className="fixed inset-0 z-50 overflow-y-auto">
                    <div className="flex min-h-screen items-end justify-center px-4 pt-4 pb-20 text-center sm:block sm:p-0">
                        <div className="fixed inset-0 bg-slate-900/50 dark:bg-slate-950/80 backdrop-blur-sm transition-opacity" onClick={() => setSelectedLog(null)}></div>
                        <span className="hidden sm:inline-block sm:h-screen sm:align-middle" aria-hidden="true">&#8203;</span>
                        <div className="inline-block transform overflow-hidden rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 px-4 pt-5 pb-4 text-left align-bottom shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-4xl sm:p-6 sm:align-middle">
                            <div>
                                <h3 className="text-lg leading-6 font-medium text-slate-900 dark:text-white">
                                    Log Details: {selectedLog.stage}
                                </h3>
                                <div className="mt-4 grid grid-cols-2 gap-4 text-sm mb-6 pb-4 border-b border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
                                    <div><span className="font-semibold text-slate-500 dark:text-slate-400">Run ID:</span> {selectedLog.run_id}</div>
                                    <div><span className="font-semibold text-slate-500 dark:text-slate-400">Target ID:</span> {selectedLog.target_id}</div>
                                    <div><span className="font-semibold text-slate-500 dark:text-slate-400">Model:</span> {selectedLog.model}</div>
                                    <div><span className="font-semibold text-slate-500 dark:text-slate-400">Timestamp:</span> {new Date(selectedLog.timestamp).toLocaleString()}</div>
                                    <div><span className="font-semibold text-slate-500 dark:text-slate-400">Input Tokens:</span> {selectedLog.input_tokens}</div>
                                    <div><span className="font-semibold text-slate-500 dark:text-slate-400">Output Tokens:</span> {selectedLog.output_tokens}</div>
                                </div>
                                <div className="mt-2 space-y-6">
                                    <div>
                                        <h4 className="font-semibold text-slate-900 dark:text-white mb-2">Prompt Setup</h4>
                                        <pre className="mt-1 text-sm text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-950/50 p-4 rounded-md overflow-x-auto whitespace-pre-wrap border border-slate-200 dark:border-white/10 max-h-96 overflow-y-auto">
                                            {selectedLog.prompt_text}
                                        </pre>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold text-slate-900 dark:text-white mb-2">Generated Response</h4>
                                        <pre className="mt-1 text-sm text-slate-700 dark:text-slate-300 bg-blue-50 dark:bg-blue-500/10 p-4 rounded-md overflow-x-auto whitespace-pre-wrap border border-blue-200 dark:border-blue-500/20 max-h-96 overflow-y-auto">
                                            {selectedLog.response_text}
                                        </pre>
                                    </div>
                                </div>
                            </div>
                            <div className="mt-6 sm:mt-6 sm:flex sm:flex-row-reverse">
                                <button
                                    type="button"
                                    className="mt-3 inline-flex w-full justify-center rounded-md border border-slate-300 dark:border-white/10 bg-white dark:bg-slate-800 px-4 py-2 text-base font-medium text-slate-700 dark:text-slate-300 shadow-sm hover:bg-slate-50 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                                    onClick={() => setSelectedLog(null)}
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
