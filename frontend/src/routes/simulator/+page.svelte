<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { AssetSummary, Readiness, Simulation } from '$lib/api/types';
	import { session } from '$lib/stores/session.svelte';
	import { dateLabel, inr, labelize, pct } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import LineChart from '$lib/components/LineChart.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import Stat from '$lib/components/Stat.svelte';

	const SCENARIOS = [
		{ value: 'LUMP_SUM', label: 'A · Lump sum', hint: 'All the starting capital is invested on the first date.' },
		{ value: 'STAGED_INITIAL', label: 'B · Staged', hint: 'Starting capital is invested in equal monthly tranches; the rest waits in cash.' },
		{ value: 'DELAYED_START', label: 'C · Delayed', hint: 'Capital waits in cash for the delay, then is invested. Delay past the horizon keeps it in cash.' },
		{ value: 'COMPARISON', label: 'D · Compare two', hint: 'The same capital and dates in two instruments. Both must have full history.' }
	];
	const PATHS = [
		{ value: 'HISTORICAL', label: 'Recorded sample prices (synthetic)' },
		{ value: 'ZERO_RETURN', label: 'Hypothetical — price never changes' },
		{ value: 'HYPOTHETICAL_UP', label: 'Hypothetical — steady 1% a month rise' },
		{ value: 'HYPOTHETICAL_DOWN', label: 'Hypothetical — steady 1.5% a month fall' },
		{ value: 'SEEDED_GBM', label: 'Hypothetical — seeded random path (illustrative)' }
	];

	let assets = $state<AssetSummary[]>([]);
	let readiness = $state<Readiness | null>(null);
	let scenario = $state('LUMP_SUM');
	let source = $state<'PROFILE_DERIVED' | 'USER_HYPOTHETICAL'>('USER_HYPOTHETICAL');
	let assetId = $state('');
	let compareId = $state('');
	let initial = $state('');
	let monthly = $state('');
	let frequency = $state('MONTHLY');
	let duration = $state('36');
	let evaluation = $state('');
	let marketPath = $state('HISTORICAL');
	let cashRate = $state('3.5');
	let delay = $state('6');
	let seed = $state('42');
	let result = $state<Simulation | null>(null);
	let busy = $state(false);
	let error = $state('');

	const profileReady = $derived(
		readiness !== null && readiness.status !== 'NOT_READY' && Number(readiness.metrics.designated_monthly ?? 0) > 0
	);
	const profileMessage = $derived(
		!session.activeProfileId
			? 'Create a profile to use amounts from your own finances.'
			: readiness === null
				? 'Loading your readiness…'
				: readiness.status === 'NOT_READY'
					? 'Readiness is NOT_READY, so there is no investable amount. You can still run a labelled hypothetical scenario.'
					: Number(readiness.metrics.designated_monthly ?? 0) <= 0
						? 'You have not designated a monthly investment amount on your profile yet.'
						: ''
	);

	onMount(async () => {
		try {
			assets = (await api.assets()).assets;
			if (assets.length > 1) {
				assetId = String(assets[0].id);
				compareId = String(assets[1].id);
			}
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The catalogue could not be loaded.';
		}
	});

	$effect(() => {
		const id = session.activeProfileId;
		void loadReadiness(id);
	});

	async function loadReadiness(id: number | null) {
		readiness = null;
		result = null;
		source = 'USER_HYPOTHETICAL';
		if (!id) return;
		try {
			readiness = (await api.readiness(id)).readiness;
			if (readiness.status !== 'NOT_READY' && Number(readiness.metrics.designated_monthly ?? 0) > 0) source = 'PROFILE_DERIVED';
		} catch {
			readiness = null;
		}
	}

	function useProfileAmounts() {
		if (!readiness) return;
		monthly = String(readiness.metrics.designated_monthly ?? '');
		initial = String(readiness.metrics.unallocated_liquid ?? '');
	}

	async function run() {
		error = '';
		result = null;
		busy = true;
		const hypothetical = source === 'USER_HYPOTHETICAL';
		const payload = {
			profile_id: session.activeProfileId,
			asset_id: Number(assetId),
			compare_asset_id: scenario === 'COMPARISON' && compareId ? Number(compareId) : null,
			scenario_type: scenario,
			amount_source: source,
			initial_amount: hypothetical && initial.trim() !== '' ? initial.trim() : null,
			monthly_contribution: hypothetical && monthly.trim() !== '' ? monthly.trim() : null,
			contribution_frequency: frequency,
			duration_months: Number(duration),
			evaluation_date: evaluation || null,
			market_path: marketPath,
			cash_interest_pct: cashRate.trim() || '0',
			delay_months: scenario === 'DELAYED_START' ? Number(delay) : 0,
			seed: Number(seed) || 42
		};
		try {
			result = (await api.runSimulation(payload)).simulation;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The simulation could not be run.';
		} finally {
			busy = false;
		}
	}

	const primary = $derived(result?.primary.run.metrics ?? null);
	const chartSeries = $derived(
		result
			? [
					{ label: 'Portfolio value (assets + cash)', color: '#34d399', points: result.primary.run.series.map((p) => ({ x: p.date.slice(0, 7), y: p.value })) },
					{ label: 'Money you put in', color: '#60a5fa', dashed: true, points: result.primary.run.series.map((p) => ({ x: p.date.slice(0, 7), y: p.invested_cumulative })) }
				]
			: []
	);
	const scenarioHint = $derived(SCENARIOS.find((s) => s.value === scenario)?.hint ?? '');
</script>

<svelte:head><title>Simulator — FirstRupee</title></svelte:head>

<div class="space-y-6">
	<section class="card grain">
		<p class="text-[12px] font-semibold uppercase tracking-[0.18em] text-brand-soft">What-if simulator</p>
		<h1 class="mt-2 text-2xl font-semibold tracking-tight">Compare scenarios, not slogans</h1>
		<p class="muted mt-2 max-w-3xl">
			Every scenario uses the same capital and the same evaluation date. Money that is not yet invested is held in cash and earns the
			rate you choose. Contributions are shown separately from gains, and returns are cash-flow-neutral. Hypothetical paths are labelled
			and are never expected returns.
		</p>
	</section>

	<Card title="1 · Where the amounts come from">
		<div class="grid gap-3 sm:grid-cols-2">
			<button class="rounded-xl border p-4 text-left {source === 'PROFILE_DERIVED' ? 'border-brand/60 bg-brand/10' : 'border-line bg-raised/40'}" onclick={() => (source = 'PROFILE_DERIVED')} disabled={!profileReady} aria-pressed={source === 'PROFILE_DERIVED'}>
				<p class="font-semibold">From my profile</p>
				<p class="muted mt-1">Uses the monthly amount you designated and your unallocated liquid money. Available only when readiness allows investing.</p>
			</button>
			<button class="rounded-xl border p-4 text-left {source === 'USER_HYPOTHETICAL' ? 'border-amber/60 bg-amber/10' : 'border-line bg-raised/40'}" onclick={() => (source = 'USER_HYPOTHETICAL')} aria-pressed={source === 'USER_HYPOTHETICAL'}>
				<p class="font-semibold">Hypothetical amounts I type</p>
				<p class="muted mt-1">Educational only. These amounts are not financially available to you and are labelled that way throughout.</p>
			</button>
		</div>
		{#if source === 'PROFILE_DERIVED' && profileReady}
			<div class="mt-4 flex flex-wrap items-center gap-3">
				<Stat label="Monthly, from your designation" value={inr(readiness?.metrics.designated_monthly ?? null)} tone="success" />
				<Stat label="Unallocated liquid money" value={inr(readiness?.metrics.unallocated_liquid ?? null)} tone="info" />
			</div>
		{:else if profileMessage}
			<div class="mt-4"><Notice tone={readiness?.status === 'NOT_READY' ? 'danger' : 'warn'} title="Profile amounts unavailable">{profileMessage}</Notice></div>
		{/if}
	</Card>

	<Card title="2 · Scenario">
		<div class="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
			{#each SCENARIOS as s (s.value)}
				<button class="rounded-xl border p-3 text-left {scenario === s.value ? 'border-brand/60 bg-brand/10' : 'border-line bg-raised/40'}" onclick={() => (scenario = s.value)} aria-pressed={scenario === s.value}>
					<p class="text-[13px] font-semibold">{s.label}</p>
				</button>
			{/each}
		</div>
		<p class="muted mb-5">{scenarioHint}</p>

		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			<div>
				<label class="field-label" for="simAsset">Instrument</label>
				<select id="simAsset" class="field-input" bind:value={assetId}>
					{#each assets as a (a.id)}<option value={String(a.id)}>{a.name}</option>{/each}
				</select>
			</div>
			{#if scenario === 'COMPARISON'}
				<div>
					<label class="field-label" for="simCompare">Compare with</label>
					<select id="simCompare" class="field-input" bind:value={compareId}>
						{#each assets as a (a.id)}<option value={String(a.id)}>{a.name}</option>{/each}
					</select>
				</div>
			{/if}
			<div>
				<label class="field-label" for="simMarket">Price path</label>
				<select id="simMarket" class="field-input" bind:value={marketPath}>
					{#each PATHS as p (p.value)}<option value={p.value}>{p.label}</option>{/each}
				</select>
			</div>
			<div>
				<label class="field-label" for="simInitial">Starting capital (₹)</label>
				<input id="simInitial" class="field-input" inputmode="decimal" bind:value={initial} disabled={source === 'PROFILE_DERIVED'} placeholder={source === 'USER_HYPOTHETICAL' ? 'Enter an amount' : ''} />
			</div>
			<div>
				<label class="field-label" for="simMonthly">Monthly contribution (₹)</label>
				<input id="simMonthly" class="field-input" inputmode="decimal" bind:value={monthly} disabled={source === 'PROFILE_DERIVED'} placeholder={source === 'USER_HYPOTHETICAL' ? 'Enter an amount or leave blank' : ''} />
			</div>
			<div>
				<label class="field-label" for="simFrequency">Invest monthly contributions</label>
				<select id="simFrequency" class="field-input" bind:value={frequency}>
					<option value="MONTHLY">Each month</option>
					<option value="QUARTERLY">Save in cash and invest each quarter</option>
				</select>
			</div>
			<div>
				<label class="field-label" for="simDuration">Duration (months)</label>
				<input id="simDuration" class="field-input" inputmode="numeric" bind:value={duration} />
			</div>
			<div>
				<label class="field-label" for="simEval">Evaluation date (optional)</label>
				<input id="simEval" class="field-input" type="date" bind:value={evaluation} />
				<p class="muted mt-1">Blank uses the latest available price on or before today.</p>
			</div>
			<div>
				<label class="field-label" for="simCash">Interest on uninvested cash (% a year)</label>
				<input id="simCash" class="field-input" inputmode="decimal" bind:value={cashRate} />
			</div>
			{#if scenario === 'DELAYED_START'}
				<div>
					<label class="field-label" for="simDelay">Delay before investing (months)</label>
					<input id="simDelay" class="field-input" inputmode="numeric" bind:value={delay} />
				</div>
			{/if}
			{#if marketPath === 'SEEDED_GBM'}
				<div>
					<label class="field-label" for="simSeed">Seed (reproducible path)</label>
					<input id="simSeed" class="field-input" inputmode="numeric" bind:value={seed} />
				</div>
			{/if}
		</div>

		<div class="mt-5 flex flex-wrap items-center gap-2">
			<button class="btn btn-primary" onclick={run} disabled={busy || !assetId || (scenario === 'COMPARISON' && !compareId)}>{busy ? 'Running…' : 'Run simulation'}</button>
			{#if source === 'PROFILE_DERIVED' && profileReady}<button class="btn" onclick={useProfileAmounts}>Fill amounts from my profile</button>{/if}
		</div>
		{#if error}<p class="field-error mt-3" role="alert">{error}</p>{/if}
	</Card>

	{#if busy}<p class="muted" role="status">Computing the scenario on the backend…</p>{/if}

	{#if result && primary}
		<Notice tone={result.financially_available ? 'success' : 'warn'} title={result.financially_available ? 'Based on amounts from your profile' : 'Hypothetical — not financially available to you'}>
			{result.financially_available
				? 'These amounts come from your readiness result. Investing them would still carry the risks shown below.'
				: 'These are amounts you typed for education. They do not reflect money you have available, and they are not forecasts.'}
		</Notice>

		<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
			<Stat label="Money you put in" value={inr(primary.total_contributions as string)} hint="External contributions. Not a return." />
			<Stat label="Ending value" value={inr(primary.ending_value as string)} tone="info" hint={`Evaluated ${dateLabel(result.evaluation_date)}`} />
			<Stat label="Total gain or loss" value={inr(primary.total_gain_loss as string)} tone={Number(primary.total_gain_loss) >= 0 ? 'success' : 'danger'} hint="Ending value minus money put in" />
			<Stat label="Time-weighted return" value={pct(primary.time_weighted_return_pct, 2)} hint="Cash-flow-neutral return of the strategy" tone={Number(primary.time_weighted_return_pct) >= 0 ? 'success' : 'danger'} />
			<Stat label="Money-weighted return (XIRR)" value={pct(primary.money_weighted_return_pct, 2)} hint="Annualised return on your dated cash flows" />
			<Stat label="Annualised volatility" value={pct(primary.annualised_volatility_pct, 1)} hint="From monthly NAV returns" />
			<Stat label="Maximum drawdown" value={pct(primary.max_drawdown_pct, 1)} tone="danger" hint="Largest fall from a previous peak, cash-flow-neutral" />
			<Stat label="Asset price change" value={pct(primary.asset_return_pct, 1)} hint="Only the instrument's price, over the window" />
		</div>

		<Card title="Value against money put in" subtitle={`${result.primary.asset.name} · ${result.window.start} → ${result.window.end} · ${result.window.months} months`}>
			<LineChart label="Portfolio value compared with money contributed" series={chartSeries} height={300} formatY={(v) => `₹${Math.round(v).toLocaleString('en-IN')}`} />
		</Card>

		{#if result.comparison}
			<Card title="Comparison" subtitle="Same capital, dates and policy. A higher ending value is not enough on its own: check volatility and drawdown too.">
				<div class="table-wrap">
					<table class="data-table">
						<thead><tr><th>Instrument</th><th>Ending value</th><th>Time-weighted return</th><th>Annualised volatility</th><th>Max drawdown</th></tr></thead>
						<tbody>
							<tr><td>{result.primary.asset.name}</td><td>{inr(primary.ending_value as string)}</td><td>{pct(primary.time_weighted_return_pct, 2)}</td><td>{pct(primary.annualised_volatility_pct, 1)}</td><td>{pct(primary.max_drawdown_pct, 1)}</td></tr>
							<tr><td>{result.comparison.asset.name}</td><td>{inr(result.comparison.run.metrics.ending_value as string)}</td><td>{pct(result.comparison.run.metrics.time_weighted_return_pct, 2)}</td><td>{pct(result.comparison.run.metrics.annualised_volatility_pct, 1)}</td><td>{pct(result.comparison.run.metrics.max_drawdown_pct, 1)}</td></tr>
						</tbody>
					</table>
				</div>
			</Card>
		{/if}

		{#if result.windows}
			<Card title="Observed 12-month windows" subtitle={result.windows.method}>
				<div class="grid gap-3 sm:grid-cols-3">
					<Stat label="Windows" value={String(result.windows.count)} hint={`${result.windows.skipped} skipped for missing data`} />
					<Stat label="Worst" value={pct(result.windows.worst?.return_pct ?? null, 1)} tone="danger" hint={result.windows.worst ? `${result.windows.worst.start} → ${result.windows.worst.end}` : ''} />
					<Stat label="Best" value={pct(result.windows.best?.return_pct ?? null, 1)} tone="success" hint={result.windows.best ? `${result.windows.best.start} → ${result.windows.best.end}` : ''} />
				</div>
			</Card>
		{/if}

		<div class="grid gap-6 lg:grid-cols-2">
			<Card title="Purchases" subtitle="Each deployment, with the price and units. Monthly money saved in cash is invested on the chosen dates.">
				<div class="table-wrap max-h-72 overflow-y-auto">
					<table class="data-table">
						<thead><tr><th>Date</th><th>Amount</th><th>Price</th><th>Units</th><th>From</th></tr></thead>
						<tbody>
							{#each primary && result.primary.run.trades.slice(0, 60) as t, i (i)}
								<tr><td>{dateLabel(t.date)}</td><td>{inr(t.amount)}</td><td>{t.price.toFixed(2)}</td><td>{t.units.toFixed(4)}</td><td class="muted">{labelize(t.source)}</td></tr>
							{:else}
								<tr><td colspan="5" class="muted">Nothing was invested. Capital stayed in cash for the whole window.</td></tr>
							{/each}
						</tbody>
					</table>
				</div>
			</Card>
			<Card title="Assumptions and limitations">
				<h3 class="text-[12px] font-semibold uppercase tracking-wider text-muted">Assumptions</h3>
				<ul class="mt-2 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed">{#each result.assumptions as item (item)}<li>{item}</li>{/each}</ul>
				<h3 class="mt-5 text-[12px] font-semibold uppercase tracking-wider text-muted">Limitations</h3>
				<ul class="mt-2 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-muted">{#each result.limitations as item (item)}<li>{item}</li>{/each}</ul>
			</Card>
		</div>
	{/if}
</div>
