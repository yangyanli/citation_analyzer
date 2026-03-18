"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, ArrowLeft, Loader2, Users } from 'lucide-react';
import { useAuth } from '@/app/context/AuthContext';
import Link from 'next/link';

interface UserData {
    id: number;
    username: string;
    role: 'viewer' | 'editor' | 'admin' | 'super_admin';
    created_at: string;
}

export default function AdminUsersPage() {
    const { user, loading } = useAuth();
    const router = useRouter();

    const [users, setUsers] = useState<UserData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [updatingUserId, setUpdatingUserId] = useState<number | null>(null);
    const [error, setError] = useState('');

    useEffect(() => {
        if (loading) return;
        if (!user || !['admin', 'super_admin'].includes(user.role)) {
            router.push('/');
            return;
        }

        const fetchUsers = async () => {
            try {
                const res = await fetch('/api/admin/users');
                if (res.ok) {
                    const data = await res.json();
                    setUsers(data.users);
                } else {
                    setError('Failed to fetch users');
                }
            } catch (err) {
                console.error(err);
                setError('Network error');
            } finally {
                setIsLoading(false);
            }
        };

        fetchUsers();
    }, [user, loading, router]);

    const handleRoleChange = async (userId: number, newRole: 'viewer' | 'editor' | 'admin' | 'super_admin') => {
        if (userId === user?.id) return; // Prevent changing own role

        setUpdatingUserId(userId);
        setError('');

        try {
            const res = await fetch('/api/admin/users', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId, role: newRole }),
            });

            if (res.ok) {
                setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u));
            } else {
                const data = await res.json();
                setError(data.error || 'Failed to update role');
            }
        } catch (err) {
            console.error(err);
            setError('Network error updating role');
        } finally {
            setUpdatingUserId(null);
        }
    };

    if (loading || !user || !['admin', 'super_admin'].includes(user.role)) {
        return null; // or a loading spinner while redirecting
    }

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 py-12 px-4 sm:px-6 lg:px-8 font-sans">
            <div className="max-w-5xl mx-auto">
                <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-white/5 transition-all">
                            <ArrowLeft className="h-5 w-5" />
                        </Link>
                        <div>
                            <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
                                <Users className="h-6 w-6 text-indigo-500 dark:text-indigo-400" />
                                User Management
                            </h1>
                            <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">Manage system access and privileges</p>
                        </div>
                    </div>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400 rounded-xl text-sm font-medium">
                        {error}
                    </div>
                )}

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl shadow-xl overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
                            <thead className="bg-slate-50 dark:bg-slate-950/50 text-xs uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-white/5">
                                <tr>
                                    <th className="px-6 py-4">ID</th>
                                    <th className="px-6 py-4">Username</th>
                                    <th className="px-6 py-4">Joined</th>
                                    <th className="px-6 py-4">Role / Privilege</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                {isLoading ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-12 text-center text-slate-500">
                                            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-indigo-500" />
                                            Loading users...
                                        </td>
                                    </tr>
                                ) : users.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-12 text-center text-slate-500">
                                            No users found.
                                        </td>
                                    </tr>
                                ) : (
                                    users.map((u) => (
                                        <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors">
                                            <td className="px-6 py-4 font-mono text-xs text-slate-500">#{u.id}</td>
                                            <td className="px-6 py-4 font-medium text-slate-900 dark:text-white">{u.username}</td>
                                            <td className="px-6 py-4 text-slate-500 dark:text-slate-400 text-xs">
                                                {new Date(u.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="px-6 py-4">
                                                {u.id === user.id ? (
                                                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 text-xs font-bold uppercase tracking-wider">
                                                        <Shield className="h-3.5 w-3.5 shrink-0" />
                                                        {u.role} (You)
                                                    </span>
                                                ) : (
                                                    <div className="relative inline-block w-40">
                                                        <select
                                                            disabled={updatingUserId === u.id}
                                                            value={u.role}
                                                            onChange={(e) => handleRoleChange(u.id, e.target.value as 'viewer' | 'editor' | 'admin' | 'super_admin')}
                                                            className={`w-full appearance-none bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 text-xs font-bold uppercase tracking-wider px-3 py-1.5 rounded-lg focus:outline-none focus:border-indigo-500 cursor-pointer shadow-sm transition-colors ${u.role === 'admin' ? 'border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-400' :
                                                                u.role === 'editor' ? 'border-emerald-200 dark:border-emerald-500/30 text-emerald-600 dark:text-emerald-400' :
                                                                    'border-slate-200 dark:border-slate-700/50 text-slate-700 dark:text-slate-300'
                                                                }`}
                                                        >
                                                            <option value="viewer">Viewer</option>
                                                            <option value="editor">Editor</option>
                                                            <option value="admin">Admin</option>
                                                        </select>
                                                        {updatingUserId === u.id && (
                                                            <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-indigo-500 animate-spin pointer-events-none" />
                                                        )}
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
