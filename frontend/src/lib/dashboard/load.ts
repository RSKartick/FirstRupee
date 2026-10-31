import { api } from '$lib/api/client';
import type { AssetSummary, ProfileOut, Readiness } from '$lib/api/types';

type DashboardApi = Pick<typeof api, 'getProfile' | 'readiness' | 'assets'>;

export async function loadDashboardCore(profileId: number, client: DashboardApi = api) {
	return Promise.all([client.getProfile(profileId), client.readiness(profileId), client.assets()]);
}

export function isCurrentDashboardLoad(
	token: number,
	latestToken: number,
	profileId: number,
	activeProfileId: number | null
): boolean {
	return token === latestToken && profileId === activeProfileId;
}

export type DashboardCore = [
	{ profile: ProfileOut },
	{ readiness: Readiness },
	{ assets: AssetSummary[] }
];
