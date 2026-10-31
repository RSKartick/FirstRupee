<script lang="ts">
	import { api, ApiError } from '$lib/api/client';
	import type { Readiness } from '$lib/api/types';
	import { session } from '$lib/stores/session.svelte';
	import { inr, labelize, months, pct } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import Stat from '$lib/components/Stat.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let readiness = $state<Readiness | null>(null);
	let experience = $state('');
	let error = $state('');
	let loading = $state(false);

	$effect(() => {
		const id = session.activeProfileId;
		void load(id);
	});

	async function load(id: number | null) {
		readiness = null;
		error = '';
		if (!id) return;
		loading = true;
		try {
			const [dna, profile] = await Promise.all([api.readiness(id), api.getProfile(id)]);
			readiness = dna.readiness;
			experience = profile.profile.investment_experience;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Financial DNA could not be loaded.';
		} finally {
			loading = false;
		}
	}

	const m = $derived(readiness?.metrics ?? {});
	const rec = $derived(readiness?.recommendations ?? null);
	const score = (value: unknown) => (value === null || value === undefined ? 'Unknown' : `${value} / 100`);
</script>

<svelte:head><title>Financial DNA - FirstRupee</title></svelte:head>

{#if loading}
	<p class="muted" role="status">Loading your Financial DNA...</p>
{:else if error}
	<Notice tone="danger">{error}</Notice>
{:else if !readiness}
	<div class="card space-y-3 text-center">
		<p class="muted">Financial DNA needs a profile. Complete the assessment first.</p>
		<a class="btn btn-primary" href="/onboarding?new=1">Start the assessment</a>
	</div>
{:else}
	<div class="space-y-6">
		<section class="card grain">
			<p class="text-[12px] font-semibold uppercase tracking-[0.18em] text-brand-soft">Financial DNA</p>
			<h1 class="mt-2 text-2xl font-semibold tracking-tight">Your financial profile, assessed in parts</h1>
			<p class="muted mt-2 max-w-3xl">
				Each component below is a documented calculation from your inputs. Scores are deterministic guardrails for Indian retail
				investors and drive the textual and numerical portfolio recommendations below.
			</p>
			<div class="mt-4 flex flex-wrap items-center gap-2">
				<StatusBadge status={readiness.status} />
				<span class="rounded-full border border-brand/40 bg-brand/10 px-2.5 py-0.5 text-[11px] font-medium text-brand-soft">
					Experience: {labelize(experience)}
				</span>
				<span class="text-[11px] text-muted">Rule set {readiness.rule_version}</span>
			</div>
		</section>

		<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
			<Stat label="Behavioural tolerance" value={labelize(String(m.risk_tolerance_band))} hint="How you would react to a fall and how long you can wait. Willingness only." tone="info" />
			<Stat label="Financial capacity" value={labelize(String(m.risk_capacity_band))} hint="Ability to absorb a loss: reserves, surplus, loans, income stability and horizon." tone={m.risk_capacity_band === 'LOW' ? 'danger' : m.risk_capacity_band === 'HIGH' ? 'success' : 'warn'} />
			<Stat label="Horizon" value={months(m.goal_horizon_months as number | null)} hint={`Basis: ${labelize(String(m.horizon_basis))}`} />
			<Stat label="Experience (self-declared)" value={labelize(experience)} hint="Tailors recommendation complexity and instrument mix." />
		</div>

		{#if rec}
			<Card title="DNA-Derived Allocation Blueprint" subtitle={rec.tone_label}>
				<p class="text-base font-semibold text-ink">{rec.headline}</p>
				<p class="muted mt-2 text-[13px] leading-relaxed">{rec.summary}</p>
				<div class="mt-4 grid gap-3 sm:grid-cols-3">
					<div class="rounded-xl border border-line bg-raised/40 p-3">
						<p class="text-[11px] uppercase text-muted">Equity Allocation</p>
						<p class="mt-1 text-lg font-semibold text-brand-soft">{rec.category_split_pct.equity_pct}%</p>
					</div>
					<div class="rounded-xl border border-line bg-raised/40 p-3">
						<p class="text-[11px] uppercase text-muted">Fixed Income &amp; Liquid</p>
						<p class="mt-1 text-lg font-semibold text-azure">{rec.category_split_pct.fixed_income_and_liquid_pct}%</p>
					</div>
					<div class="rounded-xl border border-line bg-raised/40 p-3">
						<p class="text-[11px] uppercase text-muted">Gold Bullion ETF</p>
						<p class="mt-1 text-lg font-semibold text-amber">{rec.category_split_pct.gold_pct}%</p>
					</div>
				</div>
				<div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
					{#each rec.asset_allocations as item (item.symbol)}
						<div class="rounded-lg border border-line bg-canvas/70 p-3">
							<div class="flex items-center justify-between gap-1">
								<span class="text-[12px] font-semibold">{item.symbol}</span>
								<span class="text-[12px] font-semibold text-brand-soft">{item.allocation_pct}%</span>
							</div>
							<p class="mt-0.5 text-[11px] text-muted">{item.name}</p>
							<p class="mt-2 text-sm font-semibold tabular-nums">{inr(item.monthly_amount_inr)}/mo</p>
						</div>
					{/each}
				</div>
			</Card>
		{/if}

		<div class="grid gap-6 lg:grid-cols-2">
			<Card title="Risk tolerance and capacity, kept apart" subtitle="Tolerance is behaviour; capacity is ability. A high tolerance never compensates for low capacity.">
				<dl class="kv">
					<div><dt>Behavioural tolerance score</dt><dd>{score(m.risk_tolerance_score)}</dd></div>
					<div><dt>Financial capacity score</dt><dd>{score(m.risk_capacity_score)}</dd></div>
					<div><dt>Performance-chasing indicator</dt><dd>{labelize(String(m.performance_chasing))}</dd></div>
				</dl>
				<p class="muted mt-3">The chasing indicator measures whether you would add money after gains. It is reported separately and is not part of tolerance.</p>
				{#if Object.keys(readiness.capacity_detail.components).length > 0}
					<h3 class="mt-5 text-[12px] font-semibold uppercase tracking-wider text-muted">Capacity components</h3>
					<dl class="kv mt-2">
						{#each Object.entries(readiness.capacity_detail.components) as [name, part] (name)}
							<div><dt>{labelize(name)} (weight {part.weight}%)</dt><dd>{part.score}</dd></div>
						{/each}
					</dl>
				{/if}
				{#if readiness.capacity_detail.caps.length > 0}
					<h3 class="mt-5 text-[12px] font-semibold uppercase tracking-wider text-muted">Hard caps applied</h3>
					<ul class="mt-2 list-disc space-y-1 pl-5 text-[13px] text-muted">
						{#each readiness.capacity_detail.caps as cap (cap.code)}<li>{cap.reason} (capped at {cap.cap})</li>{/each}
					</ul>
				{/if}
			</Card>

			<Card title="Cash flow, obligations and liquidity" subtitle="Every figure is from the engine and is explained with its inputs.">
				<dl class="kv">
					<div><dt>Monthly surplus</dt><dd>{inr(m.monthly_surplus as string)}</dd></div>
					<div><dt>Emergency coverage</dt><dd>{m.emergency_coverage_months ? `${m.emergency_coverage_months} months` : 'Unknown'}</dd></div>
					<div><dt>Emergency gap to 6 months</dt><dd>{inr(m.emergency_gap as string)}</dd></div>
					<div><dt>Goal monthly need</dt><dd>{inr(m.goal_monthly_need as string)}</dd></div>
					<div><dt>Free monthly money</dt><dd>{inr(m.investable_monthly as string)}</dd></div>
					<div><dt>Free liquid balance</dt><dd>{inr(m.unallocated_liquid as string)}</dd></div>
					<div><dt>Loan balances</dt><dd>{inr(m.liabilities as string)}</dd></div>
					<div><dt>Debt to annual income</dt><dd>{m.debt_to_annual_income ? pct(Number(m.debt_to_annual_income) * 100, 1) : 'n/a'}</dd></div>
				</dl>
			</Card>
		</div>

		<Card title="Every finding, with the inputs behind it" subtitle="Nothing here is a black box.">
			<div class="space-y-3">
				{#each readiness.findings as f (f.code)}
					<article class="rounded-xl border border-line bg-raised/40 p-4">
						<div class="flex flex-wrap items-center gap-2">
							<StatusBadge status={f.severity === 'BLOCKER' ? 'NOT_READY' : f.severity === 'WARNING' ? 'PREPARATION' : 'READY_TO_EXPLORE'} text={f.severity} />
							<p class="text-[13px] font-medium">{f.label}</p>
						</div>
						<p class="muted mt-1.5">{f.detail}</p>
						<div class="mt-2 flex flex-wrap gap-1.5">
							{#each Object.entries(f.inputs) as [key, value] (key)}
								<span class="rounded border border-line bg-canvas px-1.5 py-0.5 text-[10px] tabular-nums text-muted">{labelize(key)}: {value}</span>
							{/each}
						</div>
					</article>
				{/each}
			</div>
		</Card>

		<div class="grid gap-6 lg:grid-cols-2">
			<Card title="Documented thresholds">
				<ul class="list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-muted">
					<li>Emergency reserve: floor of 2 months of essentials (blocker), target 6 months.</li>
					<li>EMI burden: warning above 30% of take-home pay, blocker above 45%.</li>
					<li>Surplus: blocker at zero or below; thin below 10% of income.</li>
					<li>Goal within 12 months is short-term money and cannot be treated as long-term risk capital.</li>
					<li>Loans above 15% a year and balances above one year of income are warnings.</li>
					<li>Thresholds are educational guardrails, not universal rules or regulatory compliance.</li>
				</ul>
			</Card>
			<Card title="Limits of this assessment">
				<ul class="list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-muted">
					{#each readiness.limitations as item (item)}<li>{item}</li>{/each}
					{#if readiness.limitations.length === 0}<li>No additional limitations were recorded for these inputs.</li>{/if}
				</ul>
				<p class="muted mt-4">{readiness.disclaimer}</p>
			</Card>
		</div>
	</div>
{/if}
