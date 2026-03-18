import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';

export async function POST() {
    try {
        const cookieStore = await cookies();
        const token = cookieStore.get('session_token')?.value || cookieStore.get('session')?.value;

        if (token) {
            // Delete session in FastAPI
            await fetch(`${API_BASE}/api/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
        }

        // Delete cookies
        cookieStore.delete('session_token');
        cookieStore.delete('session');

        return NextResponse.json({ message: 'Logged out successfully' });
    } catch (error) {
        console.error('Logout error:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}
