import { execFileSync } from 'child_process';
import path from 'path';
import fs from 'fs';

async function globalSetup() {
    console.log('--- Playwright Global Setup: Initializing Test Database ---');

    const frontendRoot = path.resolve(__dirname, '../');
    const projectRoot = path.resolve(frontendRoot, '../');
    const dbPath = path.resolve(projectRoot, 'data/citation_analyzer.db');
    const pythonBin = path.join(projectRoot, 'venv', 'bin', 'python');

    try {
        if (process.env.KEEP_DB) {
            console.log('KEEP_DB is set, skipping database wipe and seed.');
            return;
        }

        // 0. DO NOT wipe existing DB in development to avoid destroying real data.
        // In CI/CD, you would point this to a test DB using DB_PATH env var.
        // if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);
        // if (fs.existsSync(`${dbPath}-wal`)) fs.unlinkSync(`${dbPath}-wal`);
        // if (fs.existsSync(`${dbPath}-shm`)) fs.unlinkSync(`${dbPath}-shm`);

        // 1. Initialize DB schema
        // Use execFileSync to avoid shell quoting issues with spaces in the path
        execFileSync(pythonBin, ['-c', 'from backend.database.schema import init_db; init_db()'], {
            cwd: projectRoot,
            env: { ...process.env, DB_PATH: dbPath },
            stdio: 'inherit'
        });

        // 2. Seed admin users
        execFileSync(pythonBin, ['backend/scripts/seed_db.py'], {
            cwd: projectRoot,
            env: { ...process.env, DB_PATH: dbPath },
            stdio: 'inherit'
        });

        console.log('--- Test Database Ready ---');
    } catch (err) {
        console.error('Failed to setup test database:', err);
        throw err;
    }
}

export default globalSetup;
