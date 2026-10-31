import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

/**
 * Same-origin proxy to the FastAPI backend. Cookies (session), the CSRF header and JSON bodies pass through unchanged, and
 * Set-Cookie headers from the backend are returned to the browser. Only /api/* is proxied.
 */
const BACKEND = (env.BACKEND_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
const FORWARDED_REQUEST_HEADERS = ['content-type', 'cookie', 'x-csrf-token'];

const handle: RequestHandler = async ({ request, params, url }) => {
	const target = `${BACKEND}/api/${params.path}${url.search}`;
	const headers = new Headers();
	for (const name of FORWARDED_REQUEST_HEADERS) {
		const value = request.headers.get(name);
		if (value) headers.set(name, value);
	}
	const rawBody = request.method === 'GET' || request.method === 'HEAD' ? '' : await request.text();
	const body = rawBody ? rawBody : undefined;

	let upstream: Response;
	try {
		upstream = await fetch(target, { method: request.method, headers, body, redirect: 'manual' });
	} catch {
		return new Response(JSON.stringify({ detail: 'The backend service is unavailable. Start it and try again.' }), {
			status: 503,
			headers: { 'content-type': 'application/json' }
		});
	}

	const responseHeaders = new Headers();
	const contentType = upstream.headers.get('content-type');
	if (contentType) responseHeaders.set('content-type', contentType);
	for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append('set-cookie', cookie);
	if (upstream.status === 204 || upstream.status === 205 || upstream.status === 304) {
		return new Response(null, { status: upstream.status, headers: responseHeaders });
	}
	return new Response(await upstream.arrayBuffer(), { status: upstream.status, headers: responseHeaders });
};

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const DELETE = handle;
