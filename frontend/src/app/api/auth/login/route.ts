import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
    try {
        const body = await req.json();

        if (!body.username || !body.password) {
            return NextResponse.json({ error: 'Username and password are required' }, { status: 400 });
        }

        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await response.json();

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status });
        }

        // Set HTTP-Only Cookie
        const cookieStore = await cookies();
        cookieStore.set({
            name: 'session_token',
            value: data.token,
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            path: '/',
            expires: new Date(data.expires_at),
        });

        return NextResponse.json({
            message: data.message,
            user: data.user
        });

    } catch (error) {
        console.error('Login error:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}
