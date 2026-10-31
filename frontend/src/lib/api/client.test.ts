import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, describeError, request, setCsrfToken } from './client';

function jsonResponse(body: unknown, status = 200): Response {
	return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

afterEach(() => {
	vi.unstubAllGlobals();
	setCsrfToken(null);
});

describe('API client CSRF handling', () => {
	it('sends the session CSRF token on state-changing requests', async () => {
		const fetchMock = vi.fn<(input: string, init?: RequestInit) => Promise<Response>>(async () => jsonResponse({ ok: true }));
		vi.stubGlobal('fetch', fetchMock);
		setCsrfToken('token-123');

		await request('POST', '/profile', { display_name: 'A' });

		const init = fetchMock.mock.calls[0][1] as RequestInit;
		const headers = init.headers as Record<string, string>;
		expect(init.method).toBe('POST');
		expect(headers['X-CSRF-Token']).toBe('token-123');
		expect(headers['Content-Type']).toBe('application/json');
		expect(init.credentials).toBe('same-origin');
	});

	it('does not send the CSRF header on reads', async () => {
		const fetchMock = vi.fn<(input: string, init?: RequestInit) => Promise<Response>>(async () => jsonResponse({ profiles: [] }));
		vi.stubGlobal('fetch', fetchMock);
		setCsrfToken('token-123');

		await request('GET', '/profile');

		const headers = (fetchMock.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
		expect(headers['X-CSRF-Token']).toBeUndefined();
	});

	it('always targets the same-origin /api prefix', async () => {
		const fetchMock = vi.fn<(input: string, init?: RequestInit) => Promise<Response>>(async () => jsonResponse({}));
		vi.stubGlobal('fetch', fetchMock);
		await request('GET', '/health');
		expect(fetchMock.mock.calls[0][0]).toBe('/api/health');
	});
});

describe('API client error handling', () => {
	it('surfaces the server message and field errors without exposing internals', async () => {
		vi.stubGlobal('fetch', vi.fn<(input: string, init?: RequestInit) => Promise<Response>>(async () => jsonResponse({
			detail: 'The submitted data failed validation.',
			errors: [{ field: 'monthly_income', message: 'Income must be above zero' }]
		}, 422)));

		await expect(request('POST', '/profile', {})).rejects.toMatchObject({
			status: 422,
			message: 'The submitted data failed validation.',
			errors: [{ field: 'monthly_income', message: 'Income must be above zero' }]
		});
	});

	it('reports a network failure as status 0 with a helpful message', async () => {
		vi.stubGlobal('fetch', vi.fn<(input: string, init?: RequestInit) => Promise<Response>>(async () => {
			throw new TypeError('network down');
		}));
		const error = await request('GET', '/assets').catch((e: unknown) => e);
		expect(error).toBeInstanceOf(ApiError);
		expect((error as ApiError).status).toBe(0);
		expect((error as ApiError).message).toMatch(/could not be reached/);
	});

	it('maps unauthenticated and server errors to plain-language messages', () => {
		expect(describeError(null, 401).message).toMatch(/sign in/i);
		expect(describeError({}, 403).message).toMatch(/session has expired/i);
		expect(describeError(null, 500).message).toMatch(/could not complete/i);
	});

	it('never returns a stack trace or database text as the message', () => {
		const message = describeError({ detail: 'Record not found.' }, 404).message;
		expect(message).not.toMatch(/traceback|sqlalchemy|select /i);
	});
});
