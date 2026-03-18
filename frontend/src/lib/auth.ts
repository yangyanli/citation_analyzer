import { cookies } from 'next/headers';

const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';

type Role = 'viewer' | 'editor' | 'admin' | 'super_admin';

interface User {
    id: number;
    username: string;
    role: Role;
    groups: { id: number; name: string }[];
}

export async function getSession(): Promise<User | null> {
    try {
        const cookieStore = await cookies();
        const token = cookieStore.get('session_token')?.value || cookieStore.get('session')?.value;

        if (!token) return null;

        const response = await fetch(`${API_BASE}/api/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            },
            cache: 'no-store'
        });

        if (response.ok) {
            const data = await response.json();
            return data.user;
        }
        return null;
    } catch (error) {
        console.error("Auth helper error:", error);
        return null;
    }
}

export function requireRole(user: User | null, allowedRoles: Role[]) {
    if (!user) {
        return false;
    }
    return allowedRoles.includes(user.role);
}
