import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/auth';
import { cookies } from 'next/headers';

const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';

export async function PUT(req: NextRequest) {
    try {
        const session = await getSession();
        if (!session) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const body = await req.json();

        const response = await fetch(`${API_BASE}/api/auth/users`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'x-user-id': session.id.toString(),
                'x-user-role': session.role,
                'x-user-groups': JSON.stringify(session.groups)
            },
            body: JSON.stringify(body)
        });

        const data = await response.json();
        return NextResponse.json(data, { status: response.status });
    } catch (error) {
        console.error('Update user error:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}

export async function DELETE(req: NextRequest) {
    try {
        const session = await getSession();
        if (!session) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const response = await fetch(`${API_BASE}/api/auth/users`, {
            method: 'DELETE',
            headers: {
                'x-user-id': session.id.toString(),
                'x-user-role': session.role,
                'x-user-groups': JSON.stringify(session.groups)
            }
        });

        if (response.ok) {
            const cookieStore = await cookies();
            cookieStore.delete('session');
            cookieStore.delete('session_token');
        }

        const data = await response.json();
        return NextResponse.json(data, { status: response.status });
    } catch (error) {
        console.error('Delete user error:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}
