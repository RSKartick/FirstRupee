import { api, setCsrfToken } from '$lib/api/client';
import type { ProfileSummary, SessionUser } from '$lib/api/types';

/**
 * Client session state. Authentication is the server-side session cookie; this store only mirrors it for the UI.
 * The active profile id is a UI preference stored in sessionStorage. It is never trusted for authorisation: every API call is
 * checked by the server, and a stored id that is not in the user's own profile list is discarded.
 */
const ACTIVE_KEY = 'firstrupee.activeProfile';

export const session = $state({
	user: null as SessionUser | null,
	ready: false,
	profiles: [] as ProfileSummary[],
	activeProfileId: null as number | null
});

export async function loadSession(): Promise<void> {
	try {
		const me = await api.me();
		session.user = me.user;
		setCsrfToken(me.csrf_token);
	} catch {
		session.user = null;
		setCsrfToken(null);
	}
	session.ready = true;
}

export function applySignIn(user: SessionUser, csrfToken: string): void {
	session.user = user;
	setCsrfToken(csrfToken);
	session.ready = true;
}

export async function loadProfiles(preferredId?: number | null): Promise<void> {
	if (!session.user) {
		session.profiles = [];
		session.activeProfileId = null;
		return;
	}
	const { profiles } = await api.listProfiles();
	session.profiles = profiles;
	const stored = Number(sessionStorage.getItem(`${ACTIVE_KEY}.${session.user.id}`));
	const candidates = [preferredId ?? null, Number.isFinite(stored) ? stored : null];
	const next = candidates.find((id) => id !== null && profiles.some((p) => p.id === id)) ?? profiles[0]?.id ?? null;
	selectProfile(next);
}

export function selectProfile(id: number | null): void {
	if (id !== null && !session.profiles.some((p) => p.id === id)) id = null;
	session.activeProfileId = id;
	if (session.user) {
		if (id === null) sessionStorage.removeItem(`${ACTIVE_KEY}.${session.user.id}`);
		else sessionStorage.setItem(`${ACTIVE_KEY}.${session.user.id}`, String(id));
	}
}

export async function signOut(): Promise<void> {
	try {
		await api.logout();
	} catch {
		// Even if the server call fails the local state is cleared.
	}
	setCsrfToken(null);
	session.user = null;
	session.profiles = [];
	session.activeProfileId = null;
}
