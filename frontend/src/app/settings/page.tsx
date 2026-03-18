"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, Key, Trash2, ArrowLeft, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Link from 'next/link';

export default function SettingsPage() {
    const { user, logout } = useAuth();
    const router = useRouter();

    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [isUpdating, setIsUpdating] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [message, setMessage] = useState({ text: '', type: '' });

    // If not logged in, redirect or show message
    if (!user) {
        return (
            <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col items-center justify-center p-4">
                <div className="text-slate-900 dark:text-white text-center">
                    <p className="mb-4">You must be logged in to view settings.</p>
                    <Link href="/login" className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 underline">Go to Login</Link>
                </div>
            </div>
        );
    }

    const handleUpdatePassword = async (e: React.FormEvent) => {
        e.preventDefault();

        if (newPassword.length < 5) {
            setMessage({ text: 'Password must be at least 5 characters.', type: 'error' });
            return;
        }

        if (newPassword !== confirmPassword) {
            setMessage({ text: 'Passwords do not match.', type: 'error' });
            return;
        }

        setIsUpdating(true);
        setMessage({ text: '', type: '' });

        try {
            const res = await fetch('/api/auth/users', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ newPassword }),
            });

            if (res.ok) {
                setMessage({ text: 'Password updated successfully.', type: 'success' });
                setNewPassword('');
                setConfirmPassword('');
            } else {
                const data = await res.json();
                setMessage({ text: data.error || 'Failed to update password.', type: 'error' });
            }
        } catch (error) {
            console.error(error);
            setMessage({ text: 'Network error occurred.', type: 'error' });
        } finally {
            setIsUpdating(false);
        }
    };

    const handleDeleteAccount = async () => {
        const confirmStr = prompt("Type 'DELETE' to confirm account deletion. This action cannot be undone.");
        if (confirmStr !== 'DELETE') return;

        setIsDeleting(true);
        try {
            const res = await fetch('/api/auth/users', {
                method: 'DELETE'
            });

            if (res.ok) {
                logout();
                router.push('/');
            } else {
                const data = await res.json();
                setMessage({ text: data.error || 'Failed to delete account.', type: 'error' });
                setIsDeleting(false);
            }
        } catch (error) {
            console.error(error);
            setMessage({ text: 'Network error occurred.', type: 'error' });
            setIsDeleting(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mx-auto">
                <div className="mb-8 flex items-center gap-4">
                    <Link href="/" className="p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-white/5 transition-all">
                        <ArrowLeft className="h-5 w-5" />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
                            <Shield className="h-6 w-6 text-indigo-500 dark:text-indigo-400" />
                            Account Settings
                        </h1>
                        <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">Manage your credentials and preferences</p>
                    </div>
                </div>

                <div className="space-y-6">
                    {/* Profile Summary Card */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl p-6 shadow-xl">
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Profile Overview</h2>
                        <div className="flex flex-col gap-2">
                            <div className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-white/5">
                                <span className="text-slate-600 dark:text-slate-400 text-sm">Username</span>
                                <span className="text-slate-900 dark:text-white font-medium">{user.username}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-white/5 disabled">
                                <span className="text-slate-600 dark:text-slate-400 text-sm">Role Privilege</span>
                                <span className="text-indigo-600 dark:text-indigo-400 font-bold uppercase text-xs tracking-wider bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-100 dark:border-transparent px-2 py-1 rounded inline-flex items-center gap-1">
                                    <Shield className="h-3 w-3" />
                                    {user.role}
                                </span>
                            </div>
                            <div className="flex items-center justify-between py-2 text-xs text-slate-500 italic mt-2">
                                * To change username or role, please contact an administrator.
                            </div>
                        </div>
                    </div>

                    {/* Change Password Card */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl p-6 shadow-xl">
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <Key className="h-5 w-5 text-indigo-500 dark:text-indigo-400" />
                            Change Password
                        </h2>

                        {message.text && (
                            <div className={`mb-4 p-3 rounded-xl text-sm font-medium border ${message.type === 'error' ? 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400' : 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-600 dark:text-emerald-400'}`}>
                                {message.text}
                            </div>
                        )}

                        <form onSubmit={handleUpdatePassword} className="space-y-4" autoComplete="off">
                            <div className="flex flex-col gap-1.5">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-300 ml-1">New Password</label>
                                <input
                                    type="password"
                                    required
                                    autoComplete="new-password"
                                    minLength={5}
                                    value={newPassword}
                                    onChange={e => setNewPassword(e.target.value)}
                                    className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-400 dark:placeholder:text-slate-600"
                                    placeholder="••••••••"
                                />
                            </div>
                            <div className="flex flex-col gap-1.5">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-300 ml-1">Confirm New Password</label>
                                <input
                                    type="password"
                                    required
                                    minLength={5}
                                    value={confirmPassword}
                                    onChange={e => setConfirmPassword(e.target.value)}
                                    className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-400 dark:placeholder:text-slate-600"
                                    placeholder="••••••••"
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={isUpdating}
                                className="mt-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-medium py-2.5 px-6 rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                            >
                                {isUpdating && <Loader2 className="w-4 h-4 animate-spin" />}
                                Update Password
                            </button>
                        </form>
                    </div>

                    {/* Danger Zone */}
                    <div className="bg-red-50 dark:bg-red-500/5 border border-red-200 dark:border-red-500/20 rounded-2xl p-6 shadow-xl relative overflow-hidden">
                        {/* Danger Stripes Background */}
                        <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, #ef4444 10px, #ef4444 20px)' }}></div>

                        <h2 className="text-lg font-semibold text-red-600 dark:text-red-500 mb-2 relative z-10 flex items-center gap-2">
                            <Trash2 className="h-5 w-5" />
                            Danger Zone
                        </h2>
                        <p className="text-slate-600 dark:text-slate-400 text-sm mb-6 relative z-10">Permanently delete your account and all associated active sessions. This action cannot be undone.</p>

                        <button
                            onClick={handleDeleteAccount}
                            disabled={isDeleting}
                            className="relative z-10 bg-white dark:bg-red-500/10 hover:bg-red-50 dark:hover:bg-red-500/20 border border-red-200 dark:border-red-500/30 text-red-600 dark:text-red-400 font-medium py-2.5 px-6 rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                        >
                            {isDeleting && <Loader2 className="w-4 h-4 animate-spin" />}
                            Delete Account
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
