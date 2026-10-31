<script lang="ts">
	import { api, ApiError } from '$lib/api/client';
	import type { AssetSummary, Readiness, RecommendedAssetAllocation } from '$lib/api/types';
	import { session } from '$lib/stores/session.svelte';
	import { dateLabel, inr, labelize, months, signedPct } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';

	const TYPE_LABEL: Record<string, string> = {
		EQUITY: 'NSE Equities',
		INDEX_FUND: 'Direct Index Mutual Funds',
		MUTUAL_FUND: 'Active Direct Mutual Funds',
		ETF: 'Exchange-Traded Funds (NSE)',
		FIXED_INCOME: 'Sovereign Fixed Income (G-Sec)',
		GOLD: 'Gold Bullion ETFs'
	};

	let assets = $state<AssetSummary[]>([]);
	let note = $state('');
	let loadError = $state('');
	let refreshing = $state(false);
	let typeFilter = $state('');
	let volatilityFilter = $state('');
	let horizonFilter = $state('');
	let compare = $state<number[]>([]);
	let readiness = $state<Readiness | null>(null);

	const horizon = $derived.by<number | null>(() => {
		const raw = readiness?.metrics.goal_horizon_months;
		return raw === null || raw === undefined ? null : Number(raw);
	});

	const recMap = $derived.by<Record<string, RecommendedAssetAllocation>>(() => {
		const map: Record<string, RecommendedAssetAllocation> = {};
		for (const item of readiness?.recommendations?.asset_allocations ?? []) {
			map[item.symbol] = item;
		}
		return map;
	});

	$effect(() => {
		void load(typeFilter, volatilityFilter, horizonFilter);
	});

	$effect(() => {
		const id = session.activeProfileId;
		void loadReadiness(id);
	});

	async function load(type: string, volatility: string, horizonMax: string) {
		try {
			const res = await api.assets({
				asset_type: type || undefined,
				max_volatility: volatility || undefined,
				max_min_horizon_months: horizonMax ? Number(horizonMax) : undefined
			});
			assets = res.assets;
			note = res.note;
			loadError = '';
		} catch (err) {
			loadError = err instanceof ApiError ? err.message : 'The catalogue could not be loaded.';
		}
	}

	async function refreshLive() {
		refreshing = true;
		loadError = '';
		try {
			await api.refreshAssets();
			await load(typeFilter, volatilityFilter, horizonFilter);
		} catch (err) {
			loadError = err instanceof ApiError ? err.message : 'Could not refresh live prices.';
		} finally {
			refreshing = false;
		}
	}

	async function loadReadiness(id: number | null) {
		readiness = null;
		if (!id) return;
		try {
			readiness = (await api.readiness(id)).readiness;
		} catch {
			readiness = null;
		}
	}

	function toggle(id: number) {
		compare = compare.includes(id) ? compare.filter((x) => x !== id) : compare.length >= 3 ? compare : [...compare, id];
	}

	const selected = $derived(assets.filter((a) => compare.includes(a.id)));
</script>

<svelte:head><title>Investment Explorer - FirstRupee</title></svelte:head>

<div class="space-y-6">
	<section class="card grain">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<p class="text-[12px] font-semibold uppercase tracking-[0.18em] text-brand-soft">Investment Explorer</p>
				<h1 class="mt-2 text-2xl font-semibold tracking-tight">Real Indian Market Instruments (NSE &amp; AMFI)</h1>
				<p class="muted mt-2 max-w-3xl">
					Each instrument is explained with its real structure, audited filings or statutory factsheets, daily NAV or exchange price,
					advantages, risks, liquidity, minimum sensible horizon and ongoing expense ratio.
				</p>
			</div>
			<button class="btn no-print" onclick={refreshLive} disabled={refreshing}>
				{refreshing ? 'Refreshing from Yahoo Finance & AMFI...' : 'Refresh Live Prices & NAVs'}
			</button>
		</div>
		{#if horizon !== null}
			<div class="mt-4">
				<Notice tone={horizon < 12 ? 'danger' : horizon < 36 ? 'warn' : 'success'} title="Your goal horizon is {months(horizon)}">
					{horizon < 12
						? 'Money needed within 12 months belongs in liquid, low-volatility holdings (such as Nippon India Liquid Fund). Volatile instruments are structurally unsuitable here.'
						: horizon < 36
							? 'A 1 to 3 year horizon supports only modest volatility. Filter to low or moderate volatility to see what fits.'
							: 'Your horizon is long enough to research volatile categories. Read the Devil\'s Advocate before deciding.'}
				</Notice>
			</div>
		{/if}
		<p class="muted mt-3 text-[11px]">{note}</p>
	</section>

	<Card title="Filters">
		<div class="grid gap-4 sm:grid-cols-3">
			<div>
				<label class="field-label" for="typeFilter">Category</label>
				<select id="typeFilter" class="field-input" bind:value={typeFilter}>
					<option value="">All categories</option>
					{#each Object.entries(TYPE_LABEL) as [value, label] (value)}<option {value}>{label}</option>{/each}
				</select>
			</div>
			<div>
				<label class="field-label" for="volFilter">Maximum volatility</label>
				<select id="volFilter" class="field-input" bind:value={volatilityFilter}>
					<option value="">Any</option>
					<option value="LOW">Low only</option>
					<option value="MODERATE">Up to moderate</option>
					<option value="HIGH">Include high</option>
				</select>
			</div>
			<div>
				<label class="field-label" for="horFilter">Minimum horizon no longer than</label>
				<select id="horFilter" class="field-input" bind:value={horizonFilter}>
					<option value="">Any</option>
					<option value="3">3 months</option>
					<option value="12">12 months</option>
					<option value="36">36 months</option>
					<option value="60">60 months</option>
				</select>
			</div>
		</div>
	</Card>

	{#if loadError}<Notice tone="danger">{loadError}</Notice>{/if}

	<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
		{#each assets as a (a.id)}
			{@const recItem = recMap[a.symbol]}
			<article class="card flex flex-col {recItem ? 'border-brand/50' : ''}">
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0 flex-1">
						<h2 class="!text-[15px]">{a.name}</h2>
						<p class="muted mt-0.5 text-[11px]">{a.symbol} · {TYPE_LABEL[a.asset_type] ?? labelize(a.asset_type)}</p>
					</div>
					<span class="shrink-0 whitespace-nowrap rounded border px-2.5 py-0.5 text-[10px] uppercase {a.volatility_class === 'LOW' ? 'border-brand/40 text-brand-soft' : a.volatility_class === 'MODERATE' ? 'border-amber/40 text-amber' : 'border-danger/40 text-danger'}">{a.volatility_class} volatility</span>
				</div>

				{#if recItem}
					<div class="mt-3 rounded-lg border border-brand/30 bg-brand/10 px-3 py-2 text-[12px]">
						<p class="font-semibold text-brand-soft">
							Recommended ({recItem.allocation_pct}% weight · {inr(recItem.monthly_amount_inr)}/mo)
						</p>
						<p class="mt-0.5 text-[11px] text-muted">{recItem.role}</p>
					</div>
				{/if}

				<p class="muted mt-3 flex-1">{a.description}</p>
				<dl class="kv mt-4 text-[12px]">
					{#if a.latest_price}
						<div>
							<dt>Latest Price / NAV</dt>
							<dd class="tabular-nums">
								{inr(a.latest_price, true)}
								{#if a.day_change_pct !== null && a.day_change_pct !== undefined}
									<span class="ml-1 text-[11px] {a.day_change_pct >= 0 ? 'text-brand-soft' : 'text-danger'}">({signedPct(a.day_change_pct, 2)})</span>
								{/if}
							</dd>
						</div>
					{/if}
					<div><dt>Ongoing expense ratio</dt><dd>{a.expense_ratio_pct ? `${a.expense_ratio_pct}% / yr` : 'Direct equity (no TER)'}</dd></div>
					<div><dt>Minimum sensible horizon</dt><dd>{months(a.min_horizon_months)}</dd></div>
					<div><dt>Data points</dt><dd>{a.observations} days (to {dateLabel(a.last_observation)})</dd></div>
				</dl>
				{#if horizon !== null && horizon < a.min_horizon_months}
					<p class="field-error mt-3">Horizon mismatch: your goal is {months(horizon)} away, this instrument asks for {months(a.min_horizon_months)} at least.</p>
				{/if}
				<div class="mt-4 flex flex-wrap items-center gap-2">
					<a class="btn" href="/explorer/{a.id}">Open details</a>
					<a class="btn" href="/research?asset={a.id}">Research</a>
					<button class="btn {compare.includes(a.id) ? 'btn-primary' : ''}" onclick={() => toggle(a.id)} aria-pressed={compare.includes(a.id)}>
						{compare.includes(a.id) ? 'In comparison' : 'Compare'}
					</button>
				</div>
			</article>
		{:else}
			{#if !loadError}<p class="muted">No instruments match these filters.</p>{/if}
		{/each}
	</div>

	{#if selected.length > 0}
		<Card title="Side-by-Side Instrument Comparison" subtitle="Compare costs, volatility, minimum holding horizon and suitability.">
			<div class="table-wrap">
				<table class="data-table">
					<thead>
						<tr>
							<th>Instrument</th>
							<th>Latest Price / NAV</th>
							<th>Volatility</th>
							<th>Minimum horizon</th>
							<th>Ongoing cost</th>
							<th>Recommended for you</th>
							<th>Suitability note</th>
						</tr>
					</thead>
					<tbody>
						{#each selected as a (a.id)}
							{@const recItem = recMap[a.symbol]}
							<tr>
								<td><a class="text-brand-soft underline" href="/explorer/{a.id}">{a.name}</a></td>
								<td class="tabular-nums">{a.latest_price ? inr(a.latest_price, true) : 'n/a'}</td>
								<td>{a.volatility_class}</td>
								<td>{months(a.min_horizon_months)}</td>
								<td>{a.expense_ratio_pct ? `${a.expense_ratio_pct}% a year` : 'Per-trade charges'}</td>
								<td>{recItem ? `${recItem.allocation_pct}% (${inr(recItem.monthly_amount_inr)}/mo)` : 'Not in primary basket'}</td>
								<td class="muted">
									{#if horizon !== null && horizon < a.min_horizon_months}
										Your goal horizon ({months(horizon)}) is shorter than its {months(a.min_horizon_months)} minimum horizon.
									{:else}
										Meets your horizon guardrail; review risks on the detail page.
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</Card>
	{/if}
</div>
