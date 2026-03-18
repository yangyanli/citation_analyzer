"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, ArrowLeft, Loader2, FolderPlus, Search, Users, Eye, EyeOff, Plus, X } from 'lucide-react';
import { useAuth } from '@/app/context/AuthContext';
import Link from 'next/link';

interface UserMember {
    id: number;
    username: string;
    role: string;
}

interface GroupData {
    id: number;
    name: string;
    is_public: number;
    created_at: string;
    members: UserMember[];
}

interface AllUser {
    id: number;
    username: string;
}

export default function AdminGroupsPage() {
    const { user, loading } = useAuth();
    const router = useRouter();

    const [groups, setGroups] = useState<GroupData[]>([]);
    const [allUsers, setAllUsers] = useState<AllUser[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    // New Group State
    const [newGroupName, setNewGroupName] = useState('');
    const [newGroupPublic, setNewGroupPublic] = useState(false);
    const [isCreating, setIsCreating] = useState(false);

    // Manage Users Modal State
    const [managingGroup, setManagingGroup] = useState<GroupData | null>(null);
    const [userSearch, setUserSearch] = useState('');

    useEffect(() => {
        if (loading) return;
        if (!user || !['admin', 'super_admin'].includes(user.role)) {
            router.push('/');
            return;
        }

        const fetchData = async () => {
            try {
                // Fetch groups
                const groupsRes = await fetch('/api/admin/groups');
                if (groupsRes.ok) {
                    const data = await groupsRes.json();
                    setGroups(data.groups);
                } else {
                    setError('Failed to fetch groups');
                }

                // Fetch all users to populate the Add User dropdown
                const usersRes = await fetch('/api/admin/users');
                if (usersRes.ok) {
                    const data = await usersRes.json();
                    setAllUsers(data.users.map((u: { id: number; username: string }) => ({ id: u.id, username: u.username })));
                }

            } catch (err) {
                console.error(err);
                setError('Network error');
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, [user, loading, router]);

    const handleCreateGroup = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsCreating(true);

        try {
            const res = await fetch('/api/admin/groups', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newGroupName, is_public: newGroupPublic }),
            });

            if (res.ok) {
                await res.json();
                // Refresh list
                const groupsRes = await fetch('/api/admin/groups');
                const groupsData = await groupsRes.json();
                setGroups(groupsData.groups);
                setNewGroupName('');
                setNewGroupPublic(false);
            } else {
                const data = await res.json();
                setError(data.error || 'Failed to create group');
            }
        } catch {
            setError('Network error creating group');
        } finally {
            setIsCreating(false);
        }
    };

    const togglePublicVisibility = async (groupId: number, currentStatus: number) => {
        try {
            const res = await fetch(`/api/admin/groups/${groupId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_public: currentStatus === 1 ? false : true }),
            });

            if (res.ok) {
                setGroups(prev => prev.map(g => g.id === groupId ? { ...g, is_public: currentStatus === 1 ? 0 : 1 } : g));
            } else {
                setError('Failed to toggle visibility');
            }
        } catch {
            setError('Network error updating group');
        }
    };

    const deleteGroup = async (groupId: number) => {
        if (!confirm('Are you sure you want to delete this group?')) return;
        
        try {
            const res = await fetch(`/api/admin/groups/${groupId}`, {
                method: 'DELETE',
            });

            if (res.ok) {
                setGroups(prev => prev.filter(g => g.id !== groupId));
            } else {
                const data = await res.json();
                setError(data.detail || 'Failed to delete group');
            }
        } catch {
            setError('Network error deleting group');
        }
    };

    const addUserToGroup = async (userId: number) => {
        if (!managingGroup) return;
        try {
            const res = await fetch(`/api/admin/groups/${managingGroup.id}/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId }),
            });
            if (res.ok) {
                // Refresh groups
                const groupsRes = await fetch('/api/admin/groups');
                const groupsData = await groupsRes.json();
                setGroups(groupsData.groups);
                // Update active modal view
                setManagingGroup(groupsData.groups.find((g: GroupData) => g.id === managingGroup.id));
                setUserSearch('');
            } else {
                const data = await res.json();
                alert(data.error);
            }
        } catch {
            alert("Error adding user");
        }
    };

    const removeUserFromGroup = async (userId: number) => {
        if (!managingGroup) return;
        try {
            const res = await fetch(`/api/admin/groups/${managingGroup.id}/users/${userId}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                // Refresh groups
                const groupsRes = await fetch('/api/admin/groups');
                const groupsData = await groupsRes.json();
                setGroups(groupsData.groups);
                // Update active modal view
                setManagingGroup(groupsData.groups.find((g: GroupData) => g.id === managingGroup.id));
            } else {
                alert("Failed to remove user");
            }
        } catch {
            alert("Error removing user");
        }
    };

    if (loading || !user || !['admin', 'super_admin'].includes(user.role)) {
        return null;
    }

    // Filter users not currently in the managing group
    const availableUsersForAdd = allUsers.filter(
        u => !managingGroup?.members.some(m => m.id === u.id) && u.username.toLowerCase().includes(userSearch.toLowerCase())
    );

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
                                <Shield className="h-6 w-6 text-fuchsia-500" />
                                Group Management
                            </h1>
                            <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">Super Admin portal for walled-garden visibility control</p>
                        </div>
                    </div>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400 rounded-xl text-sm font-medium">
                        {error}
                    </div>
                )}

                {/* Create Group Form */}
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl shadow-xl overflow-hidden mb-8 p-6">
                    <h3 className="text-slate-900 dark:text-white font-medium mb-4 flex items-center gap-2"><FolderPlus className="h-4 w-4 text-fuchsia-500 dark:text-fuchsia-400" /> Create New Group</h3>
                    <form onSubmit={handleCreateGroup} className="flex flex-col sm:flex-row gap-4 items-end">
                        <div className="flex-1 w-full">
                            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1 ml-1 font-medium">Group Name</label>
                            <input
                                type="text"
                                required
                                value={newGroupName}
                                onChange={(e) => setNewGroupName(e.target.value)}
                                placeholder="e.g. Stanford AI Lab"
                                className="w-full bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-900 dark:text-white focus:outline-none focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 transition-colors placeholder:text-slate-400 dark:placeholder:text-slate-500"
                            />
                        </div>
                        <div className="flex items-center h-10 px-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl gap-3">
                            <input
                                type="checkbox"
                                id="public_toggle"
                                checked={newGroupPublic}
                                onChange={(e) => setNewGroupPublic(e.target.checked)}
                                className="rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-fuchsia-600 dark:text-fuchsia-500 focus:ring-fuchsia-500 focus:ring-offset-white dark:focus:ring-offset-slate-950 h-4 w-4"
                            />
                            <label htmlFor="public_toggle" className="text-sm text-slate-700 dark:text-slate-300 select-none cursor-pointer">Global Public View</label>
                        </div>
                        <button
                            type="submit"
                            disabled={isCreating}
                            className="h-10 px-6 bg-fuchsia-600 hover:bg-fuchsia-500 text-white font-medium rounded-xl text-sm flex items-center gap-2 transition-colors focus:ring-2 focus:ring-fuchsia-500 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:opacity-50"
                        >
                            {isCreating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                            Create
                        </button>
                    </form>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl shadow-xl overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
                            <thead className="bg-slate-50 dark:bg-slate-950/50 text-xs uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-white/5">
                                <tr>
                                    <th className="px-6 py-4">ID</th>
                                    <th className="px-6 py-4">Group Name</th>
                                    <th className="px-6 py-4">Visibility</th>
                                    <th className="px-6 py-4">Members</th>
                                    <th className="px-6 py-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                {isLoading ? (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                                            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-fuchsia-500" />
                                            Loading groups...
                                        </td>
                                    </tr>
                                ) : groups.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                                            No groups found.
                                        </td>
                                    </tr>
                                ) : (
                                    groups.map((g) => (
                                        <tr key={g.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors group">
                                            <td className="px-6 py-4 font-mono text-xs text-slate-500">#{g.id}</td>
                                            <td className="px-6 py-4 font-medium text-slate-900 dark:text-white">{g.name}</td>
                                            <td className="px-6 py-4">
                                                <button
                                                    onClick={() => togglePublicVisibility(g.id, g.is_public)}
                                                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wider transition-colors ${g.is_public === 1
                                                            ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-500/20'
                                                            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                                                        }`}
                                                >
                                                    {g.is_public === 1 ? <><Eye className="h-3.5 w-3.5" /> Public</> : <><EyeOff className="h-3.5 w-3.5" /> Private</>}
                                                </button>
                                            </td>
                                            <td className="px-6 py-4 text-slate-500 dark:text-slate-400">
                                                <div className="flex items-center gap-2">
                                                    <Users className="h-4 w-4 text-slate-500" />
                                                    {g.members.length} users
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <div className="flex justify-end gap-3">
                                                    <button
                                                        onClick={() => setManagingGroup(g)}
                                                        className="text-fuchsia-600 dark:text-fuchsia-400 hover:text-fuchsia-700 dark:hover:text-fuchsia-300 text-sm font-medium transition-colors"
                                                    >
                                                        Manage
                                                    </button>
                                                    {g.members.length === 0 && (
                                                        <button
                                                            onClick={() => deleteGroup(g.id)}
                                                            className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 text-sm font-medium transition-colors"
                                                            title="Delete empty group"
                                                        >
                                                            Delete
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Modal for adding/removing users from a group */}
            {managingGroup && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-900/50 dark:bg-slate-950/80 backdrop-blur-sm">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                        <div className="px-6 py-4 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50 dark:bg-slate-950/50">
                            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Manage &quot;{managingGroup.name}&quot;</h3>
                            <button onClick={() => setManagingGroup(null)} className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        <div className="p-6">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Add User</h4>
                            <div className="relative mb-8">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                                <input
                                    type="text"
                                    placeholder="Search username to add..."
                                    value={userSearch}
                                    onChange={(e) => setUserSearch(e.target.value)}
                                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl pl-9 pr-4 py-2.5 text-sm text-slate-900 dark:text-white focus:outline-none focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 transition-colors"
                                />
                                {userSearch && availableUsersForAdd.length > 0 && (
                                    <div className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl shadow-xl overflow-hidden max-h-48 overflow-y-auto z-10">
                                        {availableUsersForAdd.map(u => (
                                            <button
                                                key={u.id}
                                                onClick={() => addUserToGroup(u.id)}
                                                className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-fuchsia-50 dark:hover:bg-fuchsia-500/10 hover:text-fuchsia-600 dark:hover:text-fuchsia-400 transition-colors flex items-center justify-between"
                                            >
                                                {u.username}
                                                <Plus className="h-4 w-4" />
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Current Members ({managingGroup.members.length})</h4>
                            <div className="bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-white/5 max-h-64 overflow-y-auto">
                                {managingGroup.members.length === 0 ? (
                                    <div className="p-4 text-center text-sm text-slate-500">No members in this group.</div>
                                ) : (
                                    <div className="divide-y divide-slate-100 dark:divide-white/5">
                                        {managingGroup.members.map(m => (
                                            <div key={m.id} className="p-3 pl-4 flex items-center justify-between hover:bg-slate-100 dark:hover:bg-white/[0.02] transition-colors">
                                                <div className="flex items-center gap-3">
                                                    <div className="h-8 w-8 rounded-full bg-slate-200 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400 font-medium text-xs">
                                                        {m.username.substring(0, 2).toUpperCase()}
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-medium text-slate-900 dark:text-white">{m.username}</div>
                                                        <div className="text-xs text-slate-500 uppercase tracking-wider">{m.role}</div>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => removeUserFromGroup(m.id)}
                                                    className="p-1.5 text-slate-400 hover:text-red-500 dark:text-slate-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-400/10 rounded transition-colors"
                                                    title="Remove from group"
                                                >
                                                    <X className="h-4 w-4" />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
