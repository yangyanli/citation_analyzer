import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { getSession } from '@/lib/auth';

const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';
const PYTHON_CMD = 'venv/bin/python3';
const SCRIPT_NAME = 'backend/main.py';

export async function POST(request: NextRequest) {
    try {
        const user = await getSession();
        if (!user) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const body = await request.json();
        const { target_id } = body;

        if (!target_id) {
            return NextResponse.json({ error: 'target_id is required' }, { status: 400 });
        }

        const fetchHeaders = new Headers();
        fetchHeaders.set('x-user-id', user.id.toString());
        fetchHeaders.set('x-user-role', user.role);
        fetchHeaders.set('x-user-groups', JSON.stringify(user.groups));

        const res = await fetch(`${API_BASE}/api/targets`, { headers: fetchHeaders, cache: 'no-store' });
        const targetsData = await res.json();
        const target = targetsData.targets?.[target_id];

        if (!target) {
            return NextResponse.json({ error: 'Target not found' }, { status: 404 });
        }

        // Enforce RBAC
        if (user.role !== 'super_admin') {
            if (user.role !== 'admin') {
                return NextResponse.json({ error: 'Unauthorized: Admin role required' }, { status: 403 });
            }
            const isMember = user.groups.some(g => g.id === target.group_id);
            if (!isMember) {
                return NextResponse.json({ error: 'Unauthorized: You are not an admin of this group' }, { status: 403 });
            }
        }

        if (target.status !== 'paused' && target.status !== 'failed' && target.status !== 'cancelled') {
            return NextResponse.json({ error: 'Target is already running or completed' }, { status: 400 });
        }

        await fetch(`${API_BASE}/api/targets/resume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...Object.fromEntries(fetchHeaders) },
            body: JSON.stringify({ target_id })
        });

        let startPhase = 0;
        if (target.progress >= 25) startPhase = 2; // skip citation collection if already done
        if (target.progress >= 55) startPhase = 3;
        if (target.progress >= 70) startPhase = 4;
        if (target.progress >= 90) startPhase = 5;

        // Spawn Python process in background
        const args = [SCRIPT_NAME, '--non-interactive', '--start_phase', startPhase.toString()];

        if (target.mode === 'scholar') {
            // we assume target_id is user_id based on previous logic
            args.push('--user_id', target_id);
        } else {
            args.push('--paper', target_id);
        }



        console.log(`Resuming: ${PYTHON_CMD} ${args.join(' ')}`);

        // We use spawn and don't wait for it to finish
        const child = spawn(PYTHON_CMD, args, {
            detached: true,
            stdio: 'ignore',
            cwd: path.resolve(process.cwd(), '..'),
            env: { ...process.env, PYTHONPATH: path.resolve(process.cwd(), '..') }
        });

        child.unref();

        return NextResponse.json({
            success: true,
            message: 'Target resumed successfully'
        });

    } catch (error: unknown) {
        console.error('Failed to resume target:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}
