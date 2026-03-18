import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { getSession, requireRole } from '@/lib/auth';

export async function POST(req: Request) {
    try {
        const user = await getSession();
        if (!requireRole(user, ['admin'])) {
            return NextResponse.json({ error: 'Unauthorized: Admin access required' }, { status: 403 });
        }

        const { target_id } = await req.json();

        if (!target_id) {
            return NextResponse.json({ error: 'Target ID is required' }, { status: 400 });
        }

        // Determine the root directory (where main.py lives)
        const rootDir = path.resolve(process.cwd(), '..');

        console.log(`[API] Starting arXiv venue resolution for target: ${target_id}`);

        // Spawn the python process
        const pythonProcess = spawn('python3', [
            'backend/main.py',
            '--user_id', target_id,
            '--resolve_arxiv'
        ], {
            cwd: rootDir,
            env: { ...process.env, PYTHONPATH: rootDir },
        });

        pythonProcess.stdout.on('data', (data: unknown) => {
            console.log(`[ArXiv Resolver]: ${String(data).trim()}`);
        });

        pythonProcess.stderr.on('data', (data: unknown) => {
            console.error(`[ArXiv Resolver Error]: ${String(data).trim()}`);
        });

        // We don't await the process, we just return success to the frontend
        // so it knows the background job started.
        return NextResponse.json({
            message: 'Venue resolution job started successfully.',
            target_id
        });

    } catch (error) {
        console.error('Error starting venue resolution:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}
