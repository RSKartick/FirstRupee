<script lang="ts">
	import { api, ApiError } from '$lib/api/client';
	import type { AssetSummary, Readiness } from '$lib/api/types';
	import { session } from '$lib/stores/session.svelte';
	import { dateLabel, labelize, months } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';

	const TYPE_LABEL: Record<string, string> = {
		EQUITY: 'Stocks',
		INDEX_FUND: 'Index mutual funds',
		MUTUAL_FUND: 'Other mutual funds',
		ETF: 'ETFs',
		FIXED_INCOME: 'Fixed income',
		GOLD: 'Gold'
	};

	let assets = $state<AssetSummary[]>([]);
	let note = $state('');
	let loadError = $state('');
	let typeFilter = $state('');
	let volatilityFilter = $state('');
	let horizonFilter = $state('');
	let compare = $state<number[]>([]);
	let readiness = $state<Readiness | null>(null);

	const horizon = $derived.by<number | null>(() => {
		const raw = readiness?.metrics.goal_horizon_months;
		return raw === null || raw === undefined ? null : Number(raw);
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

<svelte:head><title>Investment Explorer — FirstRupee</title></svelte:head>

<div class="space-y-6">
	<section class="card grain">
		<p class="text-[12px] font-semibold uppercase tracking-[0.18em] text-brand-soft">Investment Explorer</p>
		<h1 class="mt-2 text-2xl font-semibold tracking-tight">Understand the instrument before its returns</h1>
		<p class="muted mt-2 max-w-3xl">
			Each category is explained the same way: what it is, how it works, advantages, risks, liquidity, minimum sensible horizon and
			costs. Nothing is ranked by recent returns, because recent returns say little about whether an instrument suits you.
		</p>
		{#if horizon !== null}
			<div class="mt-4">
				<Notice tone={horizon < 12 ? 'danger' : horizon < 36 ? 'warn' : 'success'} title="Your goal horizon is {months(horizon)}">
					{horizon < 12
						? 'Money needed within 12 months belongs in liquid, low-volatility holdings. Volatile instruments are structurally unsuitable here.'
						: horizon < 36
							? 'A 1–3 year horizon supports only modest volatility. Filter to low or moderate volatility to see what fits.'
							: 'Your horizon is long enough to research volatile categories. Read the Devil’s Advocate before deciding.'}
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
			<article class="card flex flex-col">
				<div class="flex items-start justify-between gap-2">
					<div>
						<h2 class="!text-[15px]">{a.name}</h2>
						<p class="muted mt-0.5 text-[11px]">{a.symbol} · {TYPE_LABEL[a.asset_type] ?? labelize(a.asset_type)}</p>
					</div>
					<span class="rounded-full border px-2 py-0.5 text-[10px] uppercase {a.volatility_class === 'LOW' ? 'border-brand/40 text-brand-soft' : a.volatility_class === 'MODERATE' ? 'border-amber/40 text-amber' : 'border-danger/40 text-danger'}">{a.volatility_class} volatility</span>
				</div>
				<p class="muted mt-3 flex-1">{a.description}</p>
				<dl class="kv mt-4 text-[12px]">
					<div><dt>Minimum sensible horizon</dt><dd>{months(a.min_horizon_months)}</dd></div>
					<div><dt>Data as of</dt><dd>{dateLabel(a.data_as_of)}</dd></div>
				</dl>
				{#if horizon !== null && horizon < a.min_horizon_months}
					<p class="field-error mt-3">Horizon mismatch: your goal is {months(horizon)} away, this instrument asks for {months(a.min_horizon_months)} at least.</p>
				{/if}
				<div class="mt-4 flex flex-wrap items-center gap-2">
					<a class="btn" href="/explorer/{a.id}">Open details</a>
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
		<Card title="Comparison" subtitle="Every row gives both a reason to research the instrument and a reason it may not suit you. Nothing here is a ranking.">
			<div class="table-wrap">
				<table class="data-table">
					<thead>
						<tr>
							<th>Instrument</th>
							<th>Volatility</th>
							<th>Minimum horizon</th>
							<th>Ongoing cost</th>
							<th>Why it might be worth researching</th>
							<th>Why it might not suit you</th>
						</tr>
					</thead>
					<tbody>
						{#each selected as a (a.id)}
							<tr>
								<td><a class="text-brand-soft underline" href="/explorer/{a.id}">{a.name}</a></td>
								<td>{a.volatility_class}</td>
								<td>{months(a.min_horizon_months)}</td>
								<td>{a.expense_ratio_pct ? `${a.expense_ratio_pct}% a year` : 'Per-trade charges'}</td>
								<td class="muted">Read the advantages on the detail page.</td>
								<td class="muted">
									Read the risks on the detail page.
									{#if horizon !== null && horizon < a.min_horizon_months}
										Your goal horizon is shorter than its minimum sensible horizon.
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
