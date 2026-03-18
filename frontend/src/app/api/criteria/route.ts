import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

const PYTHON_CMD = path.resolve(process.cwd(), '..', 'venv', 'bin', 'python3');
const SCRIPT_NAME = path.resolve(process.cwd(), '..', 'backend', 'main.py');

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { user_id, paper, model } = body;

        if (!user_id && !paper) {
            return NextResponse.json({ error: 'Either user_id or paper title is required' }, { status: 400 });
        }

        const args = [SCRIPT_NAME, '--generate_criteria_only'];
        if (user_id) {
            args.push('--user_id', user_id);
        } else {
            args.push('--paper', paper);
        }

        if (model) {
            args.push('--model', model);
        }



        return new Promise<NextResponse>((resolve) => {
            const child = spawn(PYTHON_CMD, args, {
                cwd: path.resolve(process.cwd(), '..'),
                env: { ...process.env, PYTHONPATH: path.resolve(process.cwd(), '..') }
            });

            let stdout = '';
            let stderr = '';

            child.stdout.on('data', (data: unknown) => {
                stdout += String(data);
            });

            child.stderr.on('data', (data: unknown) => {
                stderr += String(data);
            });

            child.on('close', (code) => {
                if (code !== 0) {
                    console.error('Criteria generation failed:', stderr);
                    resolve(NextResponse.json({ error: 'Failed to generate criteria', details: stderr }, { status: 500 }));
                    return;
                }

                const match = stdout.match(/---CRITERIA_JSON_START---([\s\S]*?)---CRITERIA_JSON_END---/);
                if (match && match[1]) {
                    try {
                        const criteria = JSON.parse(match[1]);
                        resolve(NextResponse.json({ success: true, criteria }));
                    } catch {
                        resolve(NextResponse.json({ error: 'Failed to parse criteria JSON' }, { status: 500 }));
                    }
                } else {
                    resolve(NextResponse.json({ error: 'Criteria JSON not found in output', stdout }, { status: 500 }));
                }
            });
        });

    } catch (error: unknown) {
        console.error('Failed to trigger criteria generation:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 });
    }
}
