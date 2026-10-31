<script lang="ts">
	import { page } from '$app/state';
	import { api, ApiError } from '$lib/api/client';
	import type { AssetPage, HistoryPoint } from '$lib/api/types';
	import { dateLabel, labelize, pct, readinessTone } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import LineChart from '$lib/components/LineChart.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import Stat from '$lib/components/Stat.svelte';

	let data = $state<AssetPage | null>(null);
	let history = $state<HistoryPoint[]>([]);
	let error = $state('');

	$effect(() => {
		const id = Number(page.params.id);
		void load(id);
	});

	async function load(id: number) {
		data = null;
		error = '';
		try {
			const [detail, series] = await Promise.all([api.asset(id), api.history(id)]);
			data = detail;
			history = series.points;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'This instrument could not be loaded.';
		}
	}

	const market = $derived(data?.market_context);
</script>

<svelte:head><title>{data?.asset.name ?? 'Instrument'} — FirstRupee</title></svelte:head>

{#if error}
	<Notice tone="danger" title="Not available">{error}</Notice>
{:else if !data}
	<p class="muted" role="status">Loading instrument…</p>
{:else}
	{@const a = data.asset}
	<div class="space-y-6">
		<a class="muted" href="/explorer">← Back to the Explorer</a>
		<section class="card grain">
			<div class="flex flex-wrap items-start justify-between gap-4">
				<div>
					<h1 class="text-2xl font-semibold tracking-tight">{a.name}</h1>
					<p class="muted mt-1">{a.symbol} · {labelize(a.asset_type)} · {a.volatility_class.toLowerCase()} volatility</p>
				</div>
				<div class="flex flex-col items-end gap-2 no-print">
					<a class="btn btn-primary" href="/research?asset={a.id}">Run two-sided research</a>
					<a class="btn" href="/simulator">Simulate scenarios</a>
				</div>
			</div>
			{#if a.is_synthetic}
				<div class="mt-4"><Notice tone="warn" title="Synthetic demonstration instrument">{a.data_source}. This instrument is fictional and every series and record is generated. It does not describe a real company or fund.</Notice></div>
			{/if}
		</section>

		<div class="grid gap-6 lg:grid-cols-2">
			<Card title="What it is">
				<p class="text-[13px] leading-relaxed">{a.what_it_is}</p>
				<p class="muted mt-3">{a.how_it_works}</p>
			</Card>
			<Card title="Liquidity, horizon and costs">
				<dl class="kv">
					<div><dt>Liquidity</dt><dd class="!text-left">{a.liquidity}</dd></div>
					<div><dt>Minimum sensible horizon</dt><dd>{a.min_horizon_months} months</dd></div>
					<div><dt>Ongoing cost</dt><dd>{a.expense_ratio_pct ? `${a.expense_ratio_pct}% a year` : 'No expense ratio'}</dd></div>
					<div><dt>Fees and charges</dt><dd class="!text-left">{a.fees}</dd></div>
					<div><dt>Data as of</dt><dd>{dateLabel(a.data_as_of)}</dd></div>
					<div><dt>Observations</dt><dd>{a.observations} ({dateLabel(a.first_observation)} → {dateLabel(a.last_observation)})</dd></div>
				</dl>
			</Card>
		</div>

		<div class="grid gap-6 lg:grid-cols-2">
			<Card title="Potential advantages" subtitle="Why this might be worth researching.">
				<ul class="list-disc space-y-2 pl-5 text-[13px] leading-relaxed">{#each a.advantages as item (item)}<li>{item}</li>{/each}</ul>
			</Card>
			<Card title="Key risks" subtitle="Why this might not suit your circumstances.">
				<ul class="list-disc space-y-2 pl-5 text-[13px] leading-relaxed text-muted">{#each a.risks as item (item)}<li>{item}</li>{/each}</ul>
			</Card>
		</div>

		<Card title="Market context" subtitle="Historical description only. It is withheld when the data is stale or invalid.">
			{#if market}
				<div class="mb-4 flex flex-wrap items-center gap-2">
					<span class="rounded-full border px-2.5 py-0.5 text-[11px] uppercase {readinessTone(market.status) === 'success' ? 'border-brand/40 text-brand-soft' : readinessTone(market.status) === 'warn' ? 'border-amber/40 text-amber' : 'border-line text-muted'}">{market.status}</span>
					<span class="muted">{market.note ?? ''}</span>
				</div>
				{#if market.status === 'OK'}
					<div class="grid gap-3 sm:grid-cols-3">
						<Stat label="Annualised volatility" value={pct(market.annualised_volatility_pct, 1)} tone="info" />
						<Stat label="Trailing 12-month change" value={market.trailing_12m_return_pct === null || market.trailing_12m_return_pct === undefined ? 'Not available' : pct(market.trailing_12m_return_pct, 1)} hint={market.trailing_12m_note} />
						<Stat label="Latest observation" value={dateLabel(market.last_observation)} hint={`${market.age_days ?? '—'} days old`} />
					</div>
				{/if}
				<p class="muted mt-3">{market.disclaimer}</p>
			{/if}
		</Card>

		<Card title="Sample price history" subtitle="Monthly closes. Synthetic series generated with a fixed seed.">
			<LineChart
				label="Monthly closing prices for {a.symbol}"
				series={[{ label: `${a.symbol} (synthetic monthly close)`, color: '#34d399', points: history.map((p) => ({ x: p.date.slice(0, 7), y: Number(p.close) })) }]}
				height={280}
				formatY={(v) => v.toFixed(0)}
			/>
		</Card>

		<Card title="Evidence records" subtitle="Every stored record for this instrument. These are the only records the research agents may cite.">
			<div class="space-y-3">
				{#each data.evidence as e (e.evidence_key)}
					<article class="rounded-xl border border-line bg-raised/40 p-4">
						<div class="flex flex-wrap items-center gap-2">
							<code class="rounded bg-canvas px-1.5 py-0.5 text-[11px] text-brand-soft">{e.evidence_key}</code>
							<span class="rounded-full border border-amber/40 px-2 py-0.5 text-[10px] uppercase text-amber">{e.verification_status}</span>
							<span class="text-[11px] text-muted">{labelize(e.source_type)}{e.period ? ` · ${e.period}` : ''}</span>
							<span class="ml-auto text-[11px] text-muted">Published {dateLabel(e.publication_date)}</span>
						</div>
						<p class="mt-2 text-[13px] font-medium">{e.title}</p>
						<p class="muted mt-1">{e.summary}</p>
						{#if Object.keys(e.metrics).length > 0}
							<div class="mt-2 flex flex-wrap gap-1.5">
								{#each Object.entries(e.metrics) as [key, value] (key)}
									<span class="rounded border border-line bg-canvas px-1.5 py-0.5 text-[10px] tabular-nums text-muted">{key}={value}</span>
								{/each}
							</div>
						{/if}
					</article>
				{:else}
					<p class="muted">No evidence records are stored for this instrument.</p>
				{/each}
			</div>
		</Card>
	</div>
{/if}
