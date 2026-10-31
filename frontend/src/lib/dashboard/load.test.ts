import { describe, expect, it, vi } from 'vitest';
import { isCurrentDashboardLoad, loadDashboardCore } from './load';

function deferred<T>() {
	let resolve!: (value: T) => void;
	const promise = new Promise<T>((done) => (resolve = done));
	return { promise, resolve };
}

describe('dashboard loading', () => {
	it('loads profile, readiness, and assets without waiting for benchmarks', async () => {
		const benchmarkResponse = deferred<{ benchmarks: [] }>();
		let benchmarkFinished = false;
		void benchmarkResponse.promise.then(() => (benchmarkFinished = true));
		const client = {
			getProfile: vi.fn(async (id: number) => ({ profile: { id } })),
			readiness: vi.fn(async (id: number) => ({ readiness: { profile_id: id } })),
			assetKeys: vi.fn(async () => ({ assets: [] }))
		};

		const result = await loadDashboardCore(12, client as never);

		expect(result.map((item) => Object.keys(item)[0])).toEqual(['profile', 'readiness', 'assets']);
		expect(benchmarkFinished).toBe(false);
		benchmarkResponse.resolve({ benchmarks: [] });
	});

	it('does not let an earlier profile response overwrite the current profile', () => {
		const visibleProfile = { id: 20 };
		const oldResponse = { id: 10 };
		const latestToken = 2;
		const activeProfileId = 20;
		if (isCurrentDashboardLoad(1, latestToken, oldResponse.id, activeProfileId)) {
			visibleProfile.id = oldResponse.id;
		}
		expect(visibleProfile.id).toBe(20);
		expect(isCurrentDashboardLoad(1, 2, 10, 20)).toBe(false);
		expect(isCurrentDashboardLoad(2, 2, 10, 20)).toBe(false);
		expect(isCurrentDashboardLoad(2, 2, 20, 20)).toBe(true);
	});
});
