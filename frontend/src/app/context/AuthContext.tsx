"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';

type Role = 'viewer' | 'editor' | 'admin' | 'super_admin';

interface User {
    id: number;
    username: string;
    role: Role;
    groups: { id: number; name: string }[];
}

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (user: User) => void;
    logout: () => Promise<void>;
    requireRole: (allowedRoles: Role[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check session on mount
        fetch('/api/auth/me')
            .then(res => res.json())
            .then(data => {
                if (data.user) {
                    setUser(data.user);
                }
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const login = (newUser: User) => {
        setUser(newUser);
    };

    const logout = async () => {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
            setUser(null);
            window.location.href = '/login';
        } catch (e) {
            console.error(e);
        }
    };

    const requireRole = (allowedRoles: Role[]) => {
        if (!user) return false;
        return allowedRoles.includes(user.role);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, requireRole }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
