import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/auth';

const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';

async function proxyRequest(request: NextRequest) {
    try {
        const user = await getSession();
        
        // Construct the FastAPI URL
        const url = new URL(request.url);
        const fastApiUrl = `${API_BASE}${url.pathname}${url.search}`;
        
        // Forward headers, injecting user context
        const headers = new Headers(request.headers);
        if (user) {
            headers.set('x-user-id', user.id.toString());
            headers.set('x-user-role', user.role);
            headers.set('x-user-groups', JSON.stringify(user.groups));
        }

        // Forward the request
        const init: RequestInit = {
            method: request.method,
            headers,
            // Only forward body if not GET/HEAD
            body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer()
        };

        const response = await fetch(fastApiUrl, init);
        
        // Read response body
        let data;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            data = await response.text();
        }

        return NextResponse.json(data, { status: response.status });
    } catch (error: unknown) {
        console.error('Proxy error:', error);
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
