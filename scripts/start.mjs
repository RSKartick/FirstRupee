#!/usr/bin/env node
/**
 * Starts the production stack:
 *   - FastAPI backend (uvicorn) on BACKEND_PORT (default 8000, loopback only). Migrations and seeding run at start-up.
 *   - SvelteKit Node server on PORT (default 3000). It serves the app and proxies /api/* to the backend.
 * Only PORT is exposed to users; the backend is reached through the proxy.
 */
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const backendDir = path.join(root, 'backend');
const frontendDir = path.join(root, 'frontend');

const venvSubdir = process.platform === 'win32' ? 'Scripts' : 'bin';
const pythonExe = process.platform === 'win32' ? 'python.exe' : 'python';

const candidatePythons = [
	path.join(backendDir, '.venv', venvSubdir, pythonExe),
	path.join(root, '.venv', venvSubdir, pythonExe)
];

let python = candidatePythons.find((p) => existsSync(p));

if (!python) {
	if (process.env.PYTHON) {
		python = process.env.PYTHON;
	} else {
		const pipPath = process.platform === 'win32' ? '.venv\\Scripts\\pip' : '.venv/bin/pip';
		console.warn('\nNotice: Backend virtual environment was not found in backend/.venv.');
		console.warn('Run these commands to set up the backend dependencies:');
		console.warn(`  cd backend; python -m venv .venv; ${pipPath} install -r requirements.txt; cd ..\n`);
		python = process.platform === 'win32' ? 'python' : 'python3';
	}
}
const buildEntry = path.join(frontendDir, 'build', 'index.js');

if (!existsSync(buildEntry)) {
	console.error('The frontend build was not found. Run `npm run build` first.');
	process.exit(1);
}

const backendPort = process.env.BACKEND_PORT ?? '8000';
const frontendPort = process.env.PORT ?? '3000';

const backend = spawn(
	python,
	['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', backendPort],
	{ cwd: backendDir, stdio: 'inherit', env: process.env }
);

const frontend = spawn(process.execPath, [buildEntry], {
	cwd: frontendDir,
	stdio: 'inherit',
	env: {
		...process.env,
		PORT: frontendPort,
		HOST: process.env.HOST ?? '0.0.0.0',
		BACKEND_URL: process.env.BACKEND_URL ?? `http://127.0.0.1:${backendPort}`
	}
});

const children = [backend, frontend];
let shuttingDown = false;

function shutdown(code) {
	if (shuttingDown) return;
	shuttingDown = true;
	for (const child of children) {
		if (!child.killed) child.kill('SIGTERM');
	}
	setTimeout(() => process.exit(code), 500);
}

for (const child of children) {
	child.on('exit', (code) => shutdown(code ?? 0));
}
process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));
