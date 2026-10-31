<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { AssetSummary, Clock, Timing } from '$lib/api/types';
	import { session } from '$lib/stores/session.svelte';
	import { labelize } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let assets = $state<AssetSummary[]>([]);
	let assetId = $state('');
	let timing = $state<Timing | null>(null);
	let busy = $state(false);
	let error = $state('');

	onMount(async () => {
		try {
			assets = (await api.assets()).assets;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The catalogue could not be loaded.';
		}
	});

	$effect(() => {
		void session.activeProfileId;
		timing = null;
	});

	async function run() {
		const pid = session.activeProfileId;
		if (!pid) return;
		busy = true;
		error = '';
		try {
			timing = (await api.timing({ profile_id: pid, asset_id: assetId ? Number(assetId) : null })).timing;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The timing analysis could not be completed.';
		} finally {
			busy = false;
		}
	}

	const CLOCK_ORDER: (keyof Timing['clocks'])[] = ['money', 'goal', 'market'];
	const verdictTone = (code: string) =>
		code === 'RESEARCH_PERMITTED' ? 'success' : code === 'EDUCATE_ONLY' ? 'warn' : 'danger';

	function clockDataRows(clock: Clock): [string, string][] {
		return Object.entries(clock.data)
			.filter(([, value]) => value !== null && value !== undefined && typeof value !== 'object')
			.map(([key, value]) => [labelize(key), String(value)]);
	}
</script>

<svelte:head><title>Three Clocks — FirstRupee</title></svelte:head>

{#if !session.activeProfileId}
	<div class="card space-y-3 text-center">
		<p class="muted">The three clocks need a profile: the Money Clock uses your income and commitments, the Goal Clock your goal date.</p>
		<a class="btn btn-primary" href="/onboarding?new=1">Start the assessment</a>
	</div>
{:else}
	<div class="space-y-6">
		<section class="card grain">
			<p class="text-[12px] font-semibold uppercase tracking-[0.18em] text-brand-soft">Three-Clock Timing Engine</p>
			<h1 class="mt-2 text-2xl font-semibold tracking-tight">When is “now” the right time?</h1>
			<p class="muted mt-2 max-w-3xl">
				FirstRupee applies three clocks in a fixed order. The Money Clock asks when money is genuinely available. The Goal Clock asks
				when it will be needed. The Market Clock offers historical context from stored data. Readiness and goal liquidity always
				outrank market conditions. No buy dates or market-bottom predictions are produced.
			</p>
			<div class="mt-5 grid gap-3 sm:grid-cols-[1fr_auto]">
				<div>
					<label class="field-label" for="timingAsset">Reference instrument for the Market Clock (optional)</label>
					<select id="timingAsset" class="field-input" bind:value={assetId}>
						<option value="">No market context — money and goal only</option>
						{#each assets as a (a.id)}<option value={String(a.id)}>{a.name}</option>{/each}
					</select>
				</div>
				<div class="flex items-end">
					<button class="btn btn-primary w-full" onclick={run} disabled={busy}>{busy ? 'Analysing…' : 'Run timing analysis'}</button>
				</div>
			</div>
			{#if error}<p class="field-error mt-3" role="alert">{error}</p>{/if}
		</section>

		{#if timing}
			<Notice tone={verdictTone(timing.verdict_code) === 'success' ? 'success' : verdictTone(timing.verdict_code) === 'warn' ? 'warn' : 'danger'} title="Verdict: {labelize(timing.verdict_code)}">
				{timing.verdict}
			</Notice>

			<div class="grid gap-4 lg:grid-cols-3">
				{#each CLOCK_ORDER as key (key)}
					{@const clock = timing.clocks[key]}
					<Card title={clock.name} class="h-full">
						{#snippet right()}<StatusBadge status={clock.status} />{/snippet}
						<p class="text-[13px] font-medium text-brand-soft">{clock.headline}</p>
						<p class="muted mt-2">{clock.explanation}</p>
						{#if clockDataRows(clock).length > 0}
							<dl class="kv mt-4">
								{#each clockDataRows(clock) as [label, value] (label)}<div><dt>{label}</dt><dd>{value}</dd></div>{/each}
							</dl>
						{/if}
					</Card>
				{/each}
			</div>

			<Card title="How the rules were applied" subtitle={`Timing rules ${timing.rule_version}. The first triggered rule decides the verdict; later rules only add context.`}>
				<ol class="space-y-2">
					{#each timing.precedence as rule (rule.rule)}
						<li class="flex items-start gap-3 rounded-lg border px-3 py-2 text-[13px] {rule.triggered ? 'border-brand/40 bg-brand/5' : 'border-line'}">
							<span class="w-8 shrink-0 font-semibold text-muted">{rule.rule}</span>
							<span class="flex-1">{rule.description}</span>
							<span class="text-[11px] uppercase {rule.triggered ? 'text-brand-soft' : 'text-muted'}">{rule.triggered ? 'Applies' : 'Not triggered'}</span>
						</li>
					{/each}
				</ol>
				<div class="mt-4"><Notice tone="warn" title="What this is not">{timing.caution}</Notice></div>
			</Card>
		{/if}
	</div>
{/if}
