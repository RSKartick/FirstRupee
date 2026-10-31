import type {
	AssetPage,
	AssetSummary,
	ChatHistoryItem,
	ChatResponse,
	HistoryPoint,
	MarketBenchmark,
	Passport,
	PassportSummary,
	ProfileOut,
	ProfileSummary,
	Readiness,
	ResearchAnalysis,
	ResearchListItem,
	Simulation,
	SessionUser,
	Timing
} from './types';

export interface FieldError {
	field: string;
	message: string;
}

export class ApiError extends Error {
	readonly status: number;
	readonly errors: FieldError[];

	constructor(status: number, message: string, errors: FieldError[] = []) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.errors = errors;
	}
}

let csrfToken: string | null = null;

/** The CSRF token is held in memory only (never in localStorage). It is issued by the server with the session. */
export function setCsrfToken(token: string | null): void {
	csrfToken = token;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null;
}

export function describeError(data: unknown, status: number): { message: string; errors: FieldError[] } {
	const body = isRecord(data) ? data : {};
	const errors: FieldError[] = Array.isArray(body.errors)
		? body.errors.map((item) => {
				const entry = isRecord(item) ? item : {};
				return { field: String(entry.field ?? ''), message: String(entry.message ?? '') };
			})
		: [];
	if (typeof body.detail === 'string') return { message: body.detail, errors };
	if (Array.isArray(body.detail)) return { message: 'Please correct the highlighted fields.', errors };
	if (status === 401) return { message: 'Please sign in to continue.', errors };
	if (status === 403) return { message: 'Your session has expired. Refresh the page and try again.', errors };
	if (status === 404) return { message: 'That record could not be found.', errors };
	if (status >= 500) return { message: 'The server could not complete the request. Please try again.', errors };
	return { message: 'The request could not be completed.', errors };
}

export async function request<T>(method: 'GET' | 'POST' | 'PUT' | 'DELETE', path: string, body?: unknown): Promise<T> {
	const headers: Record<string, string> = {};
	if (body !== undefined) headers['Content-Type'] = 'application/json';
	if (method !== 'GET' && csrfToken) headers['X-CSRF-Token'] = csrfToken;

	let response: Response;
	try {
		response = await fetch(`/api${path}`, {
			method,
			headers,
			body: body !== undefined ? JSON.stringify(body) : undefined,
			credentials: 'same-origin',
			cache: 'no-store'
		});
	} catch {
		throw new ApiError(0, 'The server could not be reached. Check that the backend is running and try again.');
	}

	const text = await response.text();
	let data: unknown = null;
	if (text) {
		try {
			data = JSON.parse(text);
		} catch {
			data = null;
		}
	}
	if (!response.ok) {
		const { message, errors } = describeError(data, response.status);
		throw new ApiError(response.status, message, errors);
	}
	return data as T;
}

function query(params: Record<string, string | number | undefined | null>): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined && value !== null && value !== '') search.set(key, String(value));
	}
	const text = search.toString();
	return text ? `?${text}` : '';
}

export const api = {
	me: () => request<{ user: SessionUser | null; csrf_token: string | null }>('GET', '/auth/me'),
	register: (payload: { email: string; password: string; display_name: string }) =>
		request<{ user: SessionUser; csrf_token: string }>('POST', '/auth/register', payload),
	login: (payload: { email: string; password: string }) =>
		request<{ user: SessionUser; csrf_token: string }>('POST', '/auth/login', payload),
	logout: () => request<{ logged_out: boolean }>('POST', '/auth/logout'),
	loadDemo: (key: 'rahul' | 'priya' | 'arjun') =>
		request<{ user: SessionUser; csrf_token: string; profile_id: number }>('POST', `/auth/demo/${key}`),

	listProfiles: () => request<{ profiles: ProfileSummary[] }>('GET', '/profile'),
	getProfile: (id: number) => request<{ profile: ProfileOut }>('GET', `/profile/${id}`),
	createProfile: (payload: unknown) => request<{ profile: ProfileOut; readiness: Readiness }>('POST', '/profile', payload),
	updateProfile: (id: number, payload: unknown) =>
		request<{ profile: ProfileOut; readiness: Readiness }>('PUT', `/profile/${id}`, payload),
	deleteProfile: (id: number) => request<void>('DELETE', `/profile/${id}`),

	readiness: (profileId: number) => request<{ readiness: Readiness }>('GET', `/readiness/${profileId}`),

	assets: (filters: { asset_type?: string; max_volatility?: string; max_min_horizon_months?: number } = {}) =>
		request<{ assets: AssetSummary[]; note: string }>('GET', `/assets${query(filters)}`),
	benchmarks: () => request<{ benchmarks: MarketBenchmark[]; provider: string }>('GET', '/assets/benchmarks'),
	refreshAssets: () => request<{ refreshed: boolean; assets: AssetSummary[]; provider: string }>('POST', '/assets/refresh'),
	asset: (id: number) => request<AssetPage>('GET', `/assets/${id}`),
	history: (id: number, from?: string, to?: string) =>
		request<{ points: HistoryPoint[]; source: string; is_synthetic: boolean }>(
			'GET',
			`/assets/${id}/history${query({ interval: 'monthly', from, to })}`
		),

	timing: (payload: { profile_id: number; asset_id?: number | null }) =>
		request<{ timing: Timing; readiness: Readiness }>('POST', '/timing/analyze', payload),

	runResearch: (payload: { profile_id: number; asset_id: number }) =>
		request<{ analysis: ResearchAnalysis }>('POST', '/research/analyze', payload),
	listResearch: (profileId: number) => request<{ analyses: ResearchListItem[] }>('GET', `/research/profile/${profileId}`),
	getResearch: (id: number) => request<{ analysis: ResearchAnalysis }>('GET', `/research/${id}`),

	runSimulation: (payload: Record<string, unknown>) =>
		request<{ simulation: Simulation }>('POST', '/simulator/run', payload),

	generatePassport: (payload: { profile_id: number; research_analysis_id?: number; simulation_id?: number }) =>
		request<{ passport: Passport }>('POST', '/passport/generate', payload),
	getPassport: (id: number) => request<{ passport: Passport }>('GET', `/passport/${id}`),
	listPassports: (profileId: number) => request<{ passports: PassportSummary[] }>('GET', `/passport/profile/${profileId}`),

	assistantHistory: () => request<{ messages: ChatHistoryItem[] }>('GET', '/assistant/history'),
	clearAssistantHistory: () => request<void>('DELETE', '/assistant/history'),
	assistant: (payload: { profile_id: number | null; messages: { role: 'user' | 'assistant'; content: string }[] }) =>
		request<ChatResponse>('POST', '/assistant/chat', payload),

	health: () => request<Record<string, unknown>>('GET', '/health')
};

