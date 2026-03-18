"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Trophy, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Link from 'next/link';

export default function RegisterPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { login } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (password !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }

        setIsSubmitting(true);
        setError('');

        try {
            const res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });

            const data = await res.json();

            if (res.ok && data.user) {
                login(data.user);
                router.push('/');
            } else {
                setError(data.error || 'Failed to register');
            }
        } catch (err) {
            console.error(err);
            setError('An endpoint error occurred.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 p-8 rounded-2xl shadow-xl flex flex-col gap-6">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                        <Trophy className="text-white h-6 w-6" />
                    </div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight text-center">
                        Create an Account
                    </h1>
                    <p className="text-slate-600 dark:text-slate-400 text-sm">Join to organize and analyze scholarly citations</p>
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col gap-4 mt-4" autoComplete="off">
                    {error && <div className="p-3 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 text-red-600 dark:text-red-400 rounded-lg text-sm text-center font-medium">{error}</div>}

                    <div className="flex flex-col gap-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300 ml-1">Username</label>
                        <input
                            type="text"
                            required
                            autoComplete="off"
                            minLength={3}
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-400 dark:placeholder:text-slate-600"
                            placeholder="johndoe"
                        />
                    </div>

                    <div className="flex flex-col gap-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300 ml-1">Password</label>
                        <input
                            type="password"
                            required
                            minLength={5}
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-400 dark:placeholder:text-slate-600"
                            placeholder="••••••••"
                        />
                    </div>

                    <div className="flex flex-col gap-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300 ml-1">Confirm Password</label>
                        <input
                            type="password"
                            required
                            minLength={5}
                            value={confirmPassword}
                            onChange={e => setConfirmPassword(e.target.value)}
                            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-400 dark:placeholder:text-slate-600"
                            placeholder="••••••••"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="mt-2 w-full bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold py-3 px-4 rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                    >
                        {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                        Create Account
                    </button>
                </form>

                <div className="text-center mt-2 flex flex-col gap-2">
                    <p className="text-slate-600 dark:text-slate-400 text-sm">
                        Already have an account?{' '}
                        <Link href="/login" className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 underline underline-offset-4 font-medium">
                            Sign In
                        </Link>
                    </p>
                    <Link href="/" className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-400 text-sm mt-4">
                        Return to Public Dashboard
                    </Link>
                </div>
            </div>
        </div>
    );
}
