import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { getSession, requireRole } from '@/lib/auth';

const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';
const PYTHON_CMD = path.resolve(process.cwd(), '..', 'venv', 'bin', 'python3');
const SCRIPT_NAME = path.resolve(process.cwd(), '..', 'backend', 'main.py');

export async function POST(request: NextRequest) {
    try {
        const user = await getSession();
        if (!requireRole(user, ['admin', 'super_admin'])) {
            return NextResponse.json({ error: 'Unauthorized: Admin access required' }, { status: 403 });
        }

        const body = await request.json();
        const { user_id, paper, total_citations_to_add = 'all', model, domain, notable_criteria, seminal_criteria, group_id, wipe_phase, run_only_phase } = body;

        if (!user_id && !paper) {
            return NextResponse.json({ error: 'Either user_id or paper title is required' }, { status: 400 });
        }

        const targetId = user_id || paper;

        // Fetch targets from FastAPI to check status
        const fetchHeaders = new Headers();
        if (user) {
            fetchHeaders.set('x-user-id', user.id.toString());
            fetchHeaders.set('x-user-role', user.role);
            fetchHeaders.set('x-user-groups', JSON.stringify(user.groups));
        }
        const res = await fetch(`${API_BASE}/api/targets`, { headers: fetchHeaders, cache: 'no-store' });
        const targetsData = await res.json();
        const target = targetsData.targets?.[targetId];

        if (target && (target.status === 'collecting' || target.status === 'scoring')) {
            return NextResponse.json({
                success: true,
                message: 'Analysis already in progress for this target.',
                status: target.status
            });
        }

        // Validate group assignment permissions
        if (group_id) {
            if (user?.role !== 'super_admin') {
                const isMember = user?.groups.some(g => g.id === group_id);
                if (!isMember) {
                    return NextResponse.json({ error: 'Unauthorized: You are not a member of the selected group' }, { status: 403 });
                }
            }
        } else {
            return NextResponse.json({ error: 'A destination group must be selected' }, { status: 400 });
        }

        // Spawn Python process in background
        const args = ['-u', SCRIPT_NAME, '--non-interactive'];



        if (user_id) {
            args.push('--user_id', user_id);
        } else {
            args.push('--paper', paper);
        }

        args.push('--total_citations_to_add', total_citations_to_add.toString());
        if (model) {
            args.push('--model', model);
        }
        if (domain) {
            args.push('--domain', domain);
        }
        if (notable_criteria) {
            args.push('--notable_criteria', notable_criteria);
        }
        if (seminal_criteria) {
            args.push('--seminal_criteria', seminal_criteria);
        }
        if (group_id) {
            args.push('--group_id', group_id.toString());
        }
        if (wipe_phase !== undefined) {
            args.push('--wipe_phase', wipe_phase.toString());
        }
        if (run_only_phase !== undefined) {
            args.push('--run_only_phase', run_only_phase.toString());
        }

        if (user?.id) {
            args.push('--system_user_id', user.id.toString());
        }

        console.log(`Spawning: ${PYTHON_CMD} ${args.join(' ')}`);

        // We use spawn and don't wait for it to finish
        const child = spawn(PYTHON_CMD, args, {
            cwd: path.resolve(process.cwd(), '..'),
            env: { ...process.env, PYTHONPATH: path.resolve(process.cwd(), '..') }
        });

        if (child.stdout) {
            child.stdout.on('data', (data: unknown) => fs.appendFileSync('/tmp/real_python_out.txt', `[PYTHON OUT]: ${String(data)}`));
        }
        if (child.stderr) {
            child.stderr.on('data', (data: unknown) => fs.appendFileSync('/tmp/real_python_out.txt', `[PYTHON ERR]: ${String(data)}`));
        }

        child.on('error', (err) => {
            console.error('Failed to spawn Python process:', err);
        });

        // do NOT unref so streams remain open

        return NextResponse.json({
            success: true,
            message: 'Analysis started in background',
            target_id: targetId
        });

    } catch (error: unknown) {
        console.error('Failed to trigger analysis:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}
