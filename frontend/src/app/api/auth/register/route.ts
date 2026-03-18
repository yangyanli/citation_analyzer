import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
    try {
        const body = await req.json();

        if (!body.username || !body.password || body.username.length < 3 || body.password.length < 5) {
            return NextResponse.json({ error: 'Username must be at least 3 characters and password at least 5 characters.' }, { status: 400 });
        }

        const response = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await response.json();

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status });
        }

        const cookieStore = await cookies();
        cookieStore.set({
            name: 'session',
            value: data.token,
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            path: '/',
            expires: new Date(data.expires_at),
        });

        return NextResponse.json({ success: true, user: data.user });
    } catch (error) {
        console.error('Registration error:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}
