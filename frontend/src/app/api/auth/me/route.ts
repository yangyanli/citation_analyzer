import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';

export async function GET() {
    try {
        const cookieStore = await cookies();
        const token = cookieStore.get('session_token')?.value || cookieStore.get('session')?.value;

        if (!token) {
            return NextResponse.json({ user: null });
        }

        const response = await fetch(`${API_BASE}/api/auth/me`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            cache: 'no-store'
        });

        if (response.ok) {
            const data = await response.json();
            return NextResponse.json({ user: data.user });
        }

        return NextResponse.json({ user: null });
    } catch (error) {
        console.error('Me endpoint error:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}
