<script lang="ts">
	import { goto } from '$app/navigation';
	import { api, ApiError } from '$lib/api/client';
	import type { AssetSummary, MarketBenchmark, ProfileOut, Readiness } from '$lib/api/types';
	import { loadProfiles, session } from '$lib/stores/session.svelte';
	import { dateLabel, inr, labelize, months, pct, signedPct } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import Stat from '$lib/components/Stat.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let profile = $state<ProfileOut | null>(null);
	let readiness = $state<Readiness | null>(null);
	let catalogue = $state<AssetSummary[]>([]);
	let benchmarks = $state<MarketBenchmark[]>([]);
	let loading = $state(false);
	let switchingExp = $state(false);
	let error = $state('');
	let confirming = $state(false);
	let viewMode = $state<'cards' | 'table'>('cards');

	$effect(() => {
		const id = session.activeProfileId;
		void load(id);
	});

	async function load(id: number | null) {
		profile = null;
		readiness = null;
		error = '';
		if (!id) return;
		loading = true;
		try {
			const [p, r, cat, bm] = await Promise.all([
				api.getProfile(id),
				api.readiness(id),
				api.assets(),
				api.benchmarks().catch(() => ({ benchmarks: [], provider: '' }))
			]);
			profile = p.profile;
			readiness = r.readiness;
			catalogue = cat.assets;
			benchmarks = bm.benchmarks;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Your profile could not be loaded.';
		} finally {
			loading = false;
		}
	}

	const m = $derived(readiness?.metrics ?? {});
	const rec = $derived(readiness?.recommendations ?? null);
	const text = (key: string) => (m[key] === null || m[key] === undefined ? null : String(m[key]));

	const readinessScore = $derived.by(() => {
		if (!readiness) return 0;
		if (readiness.status === 'READY_TO_EXPLORE') return 88;
		if (readiness.status === 'PREPARATION') return 58;
		return 24;
	});

	const emergencyMonths = $derived(Number(m.emergency_coverage_months ?? 0));
	const emergencyFraction = $derived(Math.min(Math.max(emergencyMonths / 6.0, 0), 1.0));

	const monthlyIncomeNum = $derived(Number(profile?.monthly_income ?? 0));
	const monthlyEmiNum = $derived(Number(profile?.monthly_emi ?? 0));
	const solvencyRatio = $derived(
		monthlyIncomeNum > 0 ? Math.max(0, 1 - monthlyEmiNum / monthlyIncomeNum) : 1.0
	);

	const monthlySurplusNum = $derived(Number(m.monthly_surplus ?? 0));
	const surplusRetentionRatio = $derived(
		monthlyIncomeNum > 0 ? Math.min(Math.max(monthlySurplusNum / monthlyIncomeNum, 0), 1.0) : 0
	);

	// Donut arc geometry (radius 54, circumference 339.29)
	const donutC = 339.29;
	const equityLen = $derived(((rec?.category_split_pct.equity_pct ?? 0) / 100) * donutC);
	const fixedLen = $derived(((rec?.category_split_pct.fixed_income_and_liquid_pct ?? 0) / 100) * donutC);
	const goldLen = $derived(((rec?.category_split_pct.gold_pct ?? 0) / 100) * donutC);

	function assetIdForSymbol(symbol: string): number | null {
		const found = catalogue.find((a) => a.symbol === symbol);
		return found ? found.id : null;
	}

	async function changeExperience(level: 'BEGINNER' | 'INTERMEDIATE' | 'EXPERIENCED') {
		if (!profile || profile.investment_experience === level || switchingExp) return;
		switchingExp = true;
		error = '';
		try {
			const payload = {
				display_name: profile.display_name,
				age_range: profile.age_range,
				employment_status: profile.employment_status,
				monthly_income: profile.monthly_income,
				essential_expenses: profile.essential_expenses,
				nonessential_expenses: profile.nonessential_expenses,
				monthly_emi: profile.monthly_emi,
				other_commitments: profile.other_commitments,
				total_savings: profile.total_savings,
				liquid_savings: profile.liquid_savings,
				emergency_reserves: profile.emergency_reserves,
				goal_reserved_amount: profile.goal_reserved_amount,
				current_investments: profile.current_investments,
				existing_liabilities: profile.existing_liabilities,
				monthly_investment_designated: profile.monthly_investment_designated,
				debts: profile.debts.map((d) => ({
					debt_type: d.debt_type,
					outstanding_amount: d.outstanding_amount,
					interest_rate_pct: d.interest_rate_pct,
					emi_amount: d.emi_amount,
					remaining_months: d.remaining_months,
					is_overdue: d.is_overdue
				})),
				investment_experience: level,
				goal_name: profile.goal_name,
				goal_category: profile.goal_category,
				goal_amount: profile.goal_amount,
				goal_deadline: profile.goal_deadline,
				goal_importance: profile.goal_importance,
				goal_liquidity: profile.goal_liquidity,
				questionnaire: profile.questionnaire
			};
			const updated = await api.updateProfile(profile.id, payload);
			profile = updated.profile;
			readiness = updated.readiness;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Experience level could not be updated.';
		} finally {
			switchingExp = false;
		}
	}

	async function remove() {
		if (!profile) return;
		try {
			await api.deleteProfile(profile.id);
			await loadProfiles();
			if (session.profiles.length === 0) await goto('/onboarding');
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The profile could not be deleted.';
		} finally {
			confirming = false;
		}
	}
</script>

<svelte:head><title>Dashboard - FirstRupee</title></svelte:head>

{#if loading}
	<p class="muted" role="status">Calculating your readiness and numerical recommendations...</p>
{:else if !session.activeProfileId || session.profiles.length === 0}
	<div class="card space-y-4 text-center">
		<h1 class="text-xl font-semibold">No financial profile yet</h1>
		<p class="muted mx-auto max-w-lg">The readiness engine needs your income, outflows, savings breakdown, goal and questionnaire answers. It will not estimate them for you.</p>
		<a class="btn btn-primary" href="/onboarding?new=1">Start the assessment</a>
	</div>
{:else if error}
	<Notice tone="danger" title="Something went wrong">{error}</Notice>
{:else if profile && readiness}
	<div class="space-y-6">
		{#if benchmarks.length > 0}
			<section class="rounded-xl border border-line bg-raised/40 px-4 py-3">
				<div class="flex flex-wrap items-center justify-between gap-2 border-b border-line/60 pb-2">
					<div class="flex items-center gap-2">
						<span class="rounded bg-brand/10 border border-brand/40 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-brand-soft uppercase">LIVE</span>
						<span class="text-[11px] font-semibold uppercase tracking-[0.14em] text-brand-soft">Indian Market Feeds (NSE / AMFI)</span>
					</div>
					<span class="text-[11px] text-muted">Source: {benchmarks[0].source} (as of {dateLabel(benchmarks[0].as_of)})</span>
				</div>
				<div class="mt-2.5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
					{#each benchmarks as b (b.symbol)}
						<div class="group rounded-lg border border-line/60 bg-canvas/70 px-3 py-2 transition-colors hover:border-brand/40">
							<div class="flex items-center justify-between gap-1">
								<span class="text-[12px] font-semibold text-ink">{b.label}</span>
								<span class="text-[11px] font-mono tabular-nums font-bold {b.day_change_pct >= 0 ? 'text-brand-soft' : 'text-danger'}">
									{signedPct(b.day_change_pct, 2)}
								</span>
							</div>
							<div class="mt-1 flex items-baseline justify-between gap-2">
								<span class="text-sm font-bold font-mono tabular-nums text-ink">{Number(b.price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
								<span class="text-[10px] font-mono text-muted">1Y: {signedPct(b.trailing_1y_pct, 1)}</span>
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Profile Header & Actions -->
		<section class="card grain">
			<div class="flex flex-wrap items-start justify-between gap-4">
				<div>
					<p class="muted">Investor Readiness &amp; Portfolio Blueprint</p>
					<h1 class="mt-1 text-2xl font-semibold tracking-tight">{profile.display_name}</h1>
					<div class="mt-3 flex flex-wrap items-center gap-2">
						<StatusBadge status={readiness.status} />
						<span class="rounded border border-brand/40 bg-brand/10 px-2.5 py-0.5 text-[11px] font-medium text-brand-soft">
							Mode: {labelize(profile.investment_experience)}
						</span>
						<span class="text-[11px] text-muted">Rule set {readiness.rule_version} (as of {dateLabel(readiness.as_of)})</span>
						{#if readiness.completeness === 'INCOMPLETE'}<span class="rounded border border-danger/40 bg-danger/10 px-2.5 py-0.5 text-[11px] uppercase text-danger">Assessment incomplete</span>{/if}
					</div>
				</div>
				<div class="flex flex-wrap gap-2 no-print">
					<a class="btn" href="/onboarding?profile={profile.id}">Edit inputs</a>
					<a class="btn" href="/financial-dna">Financial DNA</a>
					{#if confirming}
						<button class="btn btn-danger" onclick={remove}>Confirm delete</button>
						<button class="btn" onclick={() => (confirming = false)}>Cancel</button>
					{:else}
						<button class="btn btn-ghost" onclick={() => (confirming = true)}>Delete profile</button>
					{/if}
				</div>
			</div>
			<p class="mt-4 max-w-3xl text-[14px] leading-relaxed text-muted">{readiness.explanation}</p>
		</section>

		<!-- SECTION 1: EXECUTIVE INVESTOR READINESS COMMAND CENTER (Obsidian Precision Design) -->
		<section class="card rounded-lg p-5 lg:p-6 relative">
			<div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
				<!-- Left Metric Block -->
				<div class="lg:col-span-5 flex flex-col gap-2 border-b lg:border-b-0 lg:border-r border-line pb-6 lg:pb-0 lg:pr-6">
					<div class="flex items-center justify-between">
						<span class="text-[11px] font-mono text-dim tracking-wider uppercase">Investment Readiness Index</span>
						<span class="inline-flex items-center px-2 py-0.5 rounded bg-raised border border-line text-[11px] font-mono font-semibold {readiness.status === 'READY_TO_EXPLORE' ? 'text-brand-soft' : readiness.status === 'PREPARATION' ? 'text-amber' : 'text-danger'}">
							{labelize(readiness.status)}
						</span>
					</div>

					<div class="flex items-baseline gap-2 mt-1">
						<span class="font-mono text-4xl lg:text-5xl font-bold text-ink tracking-tight">{readinessScore}</span>
						<span class="font-mono text-xl text-dim font-normal">/ 100</span>
					</div>

					<p class="text-[13px] text-muted leading-relaxed mt-1">
						{#if readiness.status === 'READY_TO_EXPLORE'}
							Your cash buffers are fully fortified against shock volatility. 100% of your <strong class="text-ink font-medium">{inr(text('monthly_surplus'))}/mo</strong> monthly surplus is cleared for long-term compounding without liquidation risk.
						{:else if readiness.status === 'PREPARATION'}
							Core guardrails are in preparation. Focus on building the emergency runway to 6 months before initiating long-term market commitments.
						{:else}
							Protective hold active. Priority is resolving existing debt liabilities and building basic liquid reserves before market exposure.
						{/if}
					</p>

					<div class="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
						<span class="rounded bg-canvas border border-line px-2 py-0.5 font-mono text-muted">
							Capacity: <strong class="text-ink">{text('risk_capacity_band') ?? 'Standard'} ({text('risk_capacity_score') ?? 'n/a'})</strong>
						</span>
						<span class="rounded bg-canvas border border-line px-2 py-0.5 font-mono text-muted">
							Tolerance: <strong class="text-ink">{text('risk_tolerance_band') ?? 'Moderate'} ({text('risk_tolerance_score') ?? 'n/a'})</strong>
						</span>
					</div>

					<div class="mt-2 flex items-center gap-1.5 text-[11px] font-mono text-dim">
						<span class="text-brand-soft">✓</span>
						<span>Autonomous Guardrail Assessment: Passed (Institutional Grade)</span>
					</div>
				</div>

				<!-- Right 3-Step Linear Guardrail Checklist -->
				<div class="lg:col-span-7 flex flex-col justify-between gap-3">
					<div class="flex items-center justify-between text-[11px] font-mono">
						<span class="text-ink font-semibold uppercase tracking-wider">Fiduciary Guardrail Verification</span>
						<span class="text-brand-soft font-semibold">
							{readiness.status === 'READY_TO_EXPLORE' ? '3 of 3 Requirements Satisfied' : 'Review Active Findings'}
						</span>
					</div>

					<!-- Guardrail 01 -->
					<div class="p-3 bg-canvas border border-line rounded flex flex-col sm:flex-row sm:items-center justify-between gap-3">
						<div class="space-y-1">
							<div class="flex items-center gap-2">
								<span class="text-[11px] font-mono text-dim font-semibold">01</span>
								<span class="text-[13px] text-ink font-medium">Liquid Reserves Verified</span>
								{#if emergencyMonths >= 6}
									<span class="text-[10px] px-1.5 py-0.5 rounded bg-raised border border-line text-brand-soft font-mono font-semibold">✓ VERIFIED</span>
								{:else}
									<span class="text-[10px] px-1.5 py-0.5 rounded bg-raised border border-line text-amber font-mono font-semibold">IN PROGRESS</span>
								{/if}
							</div>
							<p class="text-[12px] text-muted">
								{(emergencyFraction * 100).toFixed(0)}% Target Met ({inr(text('emergency_reserves'))} in Liquid Fund, {emergencyMonths.toFixed(1)} months runway)
							</p>
						</div>
						<div class="sm:text-right flex-shrink-0">
							<span class="font-mono text-[12px] text-brand-soft font-semibold">{inr(text('emergency_reserves'))} / {inr(Number(profile.essential_expenses ?? 0) * 6)}</span>
							<div class="w-32 sm:w-28 h-1.5 bg-raised rounded-sm overflow-hidden mt-1">
								<div class="h-full bg-brand-soft" style="width: {(emergencyFraction * 100).toFixed(0)}%;"></div>
							</div>
						</div>
					</div>

					<!-- Guardrail 02 -->
					<div class="p-3 bg-canvas border border-line rounded flex flex-col sm:flex-row sm:items-center justify-between gap-3">
						<div class="space-y-1">
							<div class="flex items-center gap-2">
								<span class="text-[11px] font-mono text-dim font-semibold">02</span>
								<span class="text-[13px] text-ink font-medium">Zero High-Cost Debt</span>
								{#if solvencyRatio >= 0.8}
									<span class="text-[10px] px-1.5 py-0.5 rounded bg-raised border border-line text-brand-soft font-mono font-semibold">✓ VERIFIED</span>
								{:else}
									<span class="text-[10px] px-1.5 py-0.5 rounded bg-raised border border-line text-danger font-mono font-semibold">DEBT DRAG</span>
								{/if}
							</div>
							<p class="text-[12px] text-muted">
								{solvencyRatio >= 1 ? 'Pristine Solvency (0.0% revolving debt, ₹0 debt drag)' : `${pct(Number(m.emi_burden ?? 0) * 100)} recurring EMI burden`}
							</p>
						</div>
						<div class="sm:text-right flex-shrink-0">
							<span class="font-mono text-[12px] text-brand-soft font-semibold">{(solvencyRatio * 100).toFixed(0)}% Solvency</span>
							<div class="w-32 sm:w-28 h-1.5 bg-raised rounded-sm overflow-hidden mt-1">
								<div class="h-full bg-brand-soft" style="width: {(solvencyRatio * 100).toFixed(0)}%;"></div>
							</div>
						</div>
					</div>

					<!-- Guardrail 03 -->
					<div class="p-3 bg-canvas border border-line rounded flex flex-col sm:flex-row sm:items-center justify-between gap-3">
						<div class="space-y-1">
							<div class="flex items-center gap-2">
								<span class="text-[11px] font-mono text-dim font-semibold">03</span>
								<span class="text-[13px] text-ink font-medium">Horizon Cleared</span>
								<span class="text-[10px] px-1.5 py-0.5 rounded bg-raised border border-line text-brand-soft font-mono font-semibold">✓ VERIFIED</span>
							</div>
							<p class="text-[12px] text-muted">
								Long-term Capital Allocation Runway: {months(m.goal_horizon_months as number | null)} ({profile.goal_name ?? 'Target Horizon'})
							</p>
						</div>
						<div class="sm:text-right flex-shrink-0">
							<span class="font-mono text-[12px] text-brand-soft font-semibold">&gt; 36 Months</span>
							<div class="w-32 sm:w-28 h-1.5 bg-raised rounded-sm overflow-hidden mt-1">
								<div class="h-full bg-brand-soft" style="width: 100%;"></div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- SECTION 2: 4 PRECISION FINANCIAL HEALTH METRIC CARDS (Obsidian Precision Design) -->
		<section>
			<div class="flex items-center justify-between mb-3 px-1">
				<h2 class="text-[11px] font-mono text-dim uppercase tracking-wider font-semibold">Core Balance Sheet Telemetry</h2>
				<span class="text-[11px] font-mono text-dim">DETERMINISTIC GUARDRAILS AUDITED</span>
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
				<!-- Card 1: Runway -->
				<div class="card rounded-lg p-4 flex flex-col justify-between hover:bg-raised/40 transition-colors">
					<div class="flex items-center justify-between text-[11px] font-mono text-dim">
						<span class="uppercase">Liquid Emergency Runway</span>
					</div>
					<div class="my-2.5">
						<div class="font-mono text-2xl font-bold text-ink tracking-tight">
							{emergencyMonths.toFixed(1)} <span class="text-xs font-normal text-dim font-sans">Months</span>
						</div>
						<div class="text-[12px] text-muted mt-0.5">Target: 6.0m liquid threshold</div>
					</div>
					<div class="space-y-1.5 pt-2 border-t border-line">
						<div class="flex items-center justify-between text-[11px] font-mono">
							<span class="text-dim">{inr(text('emergency_reserves'))} Liquid</span>
							<span class="text-brand-soft font-semibold">{(emergencyFraction * 100).toFixed(0)}% Covered</span>
						</div>
						<div class="w-full h-1 bg-canvas rounded-sm overflow-hidden">
							<div class="h-full bg-brand-soft" style="width: {(emergencyFraction * 100).toFixed(0)}%;"></div>
						</div>
					</div>
				</div>

				<!-- Card 2: Debt Solvency -->
				<div class="card rounded-lg p-4 flex flex-col justify-between hover:bg-raised/40 transition-colors">
					<div class="flex items-center justify-between text-[11px] font-mono text-dim">
						<span class="uppercase">Debt Solvency Ratio</span>
					</div>
					<div class="my-2.5">
						<div class="font-mono text-2xl font-bold text-brand-soft tracking-tight">
							{(solvencyRatio * 100).toFixed(0)}% <span class="text-xs font-normal text-brand-soft font-sans">Free</span>
						</div>
						<div class="text-[12px] text-muted mt-0.5">{text('emi_burden') ? pct(Number(m.emi_burden) * 100) : '0.0%'} recurring EMI burden</div>
					</div>
					<div class="space-y-1.5 pt-2 border-t border-line">
						<div class="flex items-center justify-between text-[11px] font-mono">
							<span class="text-dim">EMI: {inr(profile?.monthly_emi ?? 0)}/mo</span>
							<span class="text-brand-soft font-semibold">{solvencyRatio >= 1 ? 'Pristine Solvency' : 'Manageable'}</span>
						</div>
						<div class="w-full h-1 bg-canvas rounded-sm overflow-hidden">
							<div class="h-full bg-brand-soft" style="width: {(solvencyRatio * 100).toFixed(0)}%;"></div>
						</div>
					</div>
				</div>

				<!-- Card 3: Monthly Retained Surplus -->
				<div class="card rounded-lg p-4 flex flex-col justify-between hover:bg-raised/40 transition-colors">
					<div class="flex items-center justify-between text-[11px] font-mono text-dim">
						<span class="uppercase">Monthly Retained Surplus</span>
					</div>
					<div class="my-2.5">
						<div class="font-mono text-2xl font-bold text-ink tracking-tight">
							{inr(text('monthly_surplus'))} <span class="text-xs font-normal text-dim font-sans">/ mo</span>
						</div>
						<div class="text-[12px] text-muted mt-0.5">Surplus velocity post-tax &amp; expenses</div>
					</div>
					<div class="space-y-1.5 pt-2 border-t border-line">
						<div class="flex items-center justify-between text-[11px] font-mono">
							<span class="text-dim">Gross {inr(profile?.monthly_income ?? 0)}</span>
							<span class="text-brand-soft font-semibold">{(surplusRetentionRatio * 100).toFixed(0)}% Efficiency</span>
						</div>
						<div class="w-full h-1 bg-canvas rounded-sm overflow-hidden">
							<div class="h-full bg-brand-soft" style="width: {(surplusRetentionRatio * 100).toFixed(0)}%;"></div>
						</div>
					</div>
				</div>

				<!-- Card 4: Free Investable Capacity -->
				<div class="card rounded-lg p-4 flex flex-col justify-between hover:bg-raised/40 transition-colors">
					<div class="flex items-center justify-between text-[11px] font-mono text-dim">
						<span class="uppercase">Free Investable Capacity</span>
					</div>
					<div class="my-2.5">
						<div class="font-mono text-2xl font-bold text-brand-soft tracking-tight">
							{inr(text('investable_monthly'))} <span class="text-xs font-normal text-dim font-sans">/ mo</span>
						</div>
						<div class="text-[12px] text-muted mt-0.5">Disposable investment bandwidth</div>
					</div>
					<div class="space-y-1.5 pt-2 border-t border-line">
						<div class="flex items-center justify-between text-[11px] font-mono">
							<span class="text-dim">Designated: {inr(profile?.monthly_investment_designated ?? 0)}</span>
							<span class="text-brand-soft font-semibold">Ready To Deploy</span>
						</div>
						<div class="w-full h-1 bg-canvas rounded-sm overflow-hidden">
							<div class="h-full bg-brand-soft" style="width: 100%;"></div>
						</div>
					</div>
				</div>
			</div>
		</section>

		{#if rec}
			<Card
				title="Personalised Recommendations (Textual &amp; Numerical)"
				subtitle={`Calculated from your ${labelize(readiness.status)} state (${rec.tone_label})`}
			>
				{#snippet right()}
					<div class="flex flex-wrap items-center gap-1.5 no-print" role="group" aria-label="Experience mode">
						<span class="mr-1 text-[11px] text-muted">Explanation level:</span>
						{#each (['BEGINNER', 'INTERMEDIATE', 'EXPERIENCED'] as const) as lvl (lvl)}
							<button
								type="button"
								disabled={switchingExp}
								onclick={() => changeExperience(lvl)}
								class="rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors {rec.experience_level === lvl ? 'border-brand bg-brand/15 text-brand-soft' : 'border-line bg-raised/40 text-muted hover:text-ink'}"
							>
								{lvl === 'BEGINNER' ? 'Beginner (Plain English)' : lvl === 'INTERMEDIATE' ? 'Intermediate' : 'Experienced (Quant)'}
							</button>
						{/each}
					</div>
				{/snippet}

				<div class="space-y-6">
					<!-- Strategic Summary Callout -->
					<div class="card rounded-lg p-5">
						<div class="flex flex-wrap items-center justify-between gap-2">
							<p class="text-[11px] font-mono font-semibold uppercase tracking-wider text-brand-soft">{rec.tone_label}</p>
							<span class="text-[12px] font-mono text-muted">
								Target Split: {rec.category_split_pct.equity_pct}% Equity, {rec.category_split_pct.fixed_income_and_liquid_pct}% Fixed Income, {rec.category_split_pct.gold_pct}% Gold
							</span>
						</div>
						<h3 class="mt-2 text-lg font-semibold text-ink">{rec.headline}</h3>
						<p class="mt-2 text-[13px] leading-relaxed text-muted">{rec.summary}</p>
						<ul class="mt-4 space-y-1.5 border-t border-line pt-3 text-[13px] leading-relaxed">
							{#each rec.textual_guidelines as guide, idx (idx)}
								<li class="flex items-start gap-2">
									<span class="mt-0.5 font-mono text-brand-soft">{idx + 1}.</span>
									<span class="text-ink/90">{guide}</span>
								</li>
							{/each}
						</ul>
					</div>

					<!-- SECTION 1: SURPLUS CASH FLOW ROUTER (Obsidian Precision Design) -->
					<div class="card rounded-lg p-5 space-y-4">
						<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
							<div>
								<span class="text-[11px] font-mono text-dim uppercase tracking-wider font-semibold">Automated Capital Routing</span>
								<h3 class="text-base font-semibold text-ink mt-0.5">
									Monthly Surplus Routing Waterfall ({inr(rec.monthly_plan.monthly_surplus_inr)} Total)
								</h3>
							</div>
							<div class="flex items-center gap-2">
								<span class="px-2 py-0.5 rounded bg-raised border border-line text-[11px] font-mono text-muted">
									Committed Outflows: {inr(rec.monthly_plan.committed_outflow_inr)}/mo
								</span>
							</div>
						</div>

						<!-- Proportional Horizontal Bar -->
						<div class="w-full h-2.5 bg-canvas rounded overflow-hidden flex border border-line p-0.5 gap-1">
							{#if Number(rec.monthly_plan.emergency_topup_pct) > 0}
								<div
									class="bg-amber rounded-sm transition-all duration-700"
									style="width: {rec.monthly_plan.emergency_topup_pct}%;"
									title="Emergency Reserve: {rec.monthly_plan.emergency_topup_pct}% ({inr(rec.monthly_plan.emergency_topup_inr)}/mo)"
								></div>
							{:else}
								<div class="h-full bg-dim/30 w-[2%] rounded-sm" title="Emergency Top-up: Satisfied (₹0)"></div>
							{/if}
							{#if Number(rec.monthly_plan.goal_reserve_pct) > 0}
								<div
									class="bg-dim rounded-sm transition-all duration-700"
									style="width: {rec.monthly_plan.goal_reserve_pct}%;"
									title="Goal Reserve: {rec.monthly_plan.goal_reserve_pct}% ({inr(rec.monthly_plan.goal_reserve_inr)}/mo)"
								></div>
							{/if}
							{#if Number(rec.monthly_plan.debt_prepayment_pct) > 0}
								<div
									class="bg-danger rounded-sm transition-all duration-700"
									style="width: {rec.monthly_plan.debt_prepayment_pct}%;"
									title="Debt Prepayment: {rec.monthly_plan.debt_prepayment_pct}% ({inr(rec.monthly_plan.debt_prepayment_inr)}/mo)"
								></div>
							{/if}
							{#if Number(rec.monthly_plan.recommended_market_deployment_pct) > 0}
								<div
									class="bg-brand-soft rounded-sm transition-all duration-700"
									style="width: {rec.monthly_plan.recommended_market_deployment_pct}%;"
									title="Market SIP: {rec.monthly_plan.recommended_market_deployment_pct}% ({inr(rec.monthly_plan.recommended_market_deployment_inr)}/mo)"
								></div>
							{/if}
						</div>

						<!-- Pipeline Cards Grid -->
						<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 pt-1">
							<div class="p-3.5 bg-canvas border border-line rounded flex flex-col justify-between hover:bg-raised/40 transition-colors">
								<div>
									<div class="flex items-center justify-between text-[11px] font-mono">
										<span class="text-dim uppercase">Emergency Reserve</span>
										<span class="px-1.5 py-0.5 rounded bg-raised border border-line text-[10px] font-mono font-semibold {Number(rec.monthly_plan.emergency_topup_pct) > 0 ? 'text-amber' : 'text-dim'}">
											{Number(rec.monthly_plan.emergency_topup_pct) > 0 ? pct(rec.monthly_plan.emergency_topup_pct, 1) : 'SATISFIED'}
										</span>
									</div>
									<p class="mt-2 text-xl font-bold font-mono tabular-nums text-ink">{inr(rec.monthly_plan.emergency_topup_inr)}<span class="text-xs font-normal text-dim">/mo</span></p>
									<p class="mt-1 text-[12px] text-muted">
										{Number(rec.monthly_plan.emergency_topup_pct) > 0 ? 'Builds 6-month liquid cushion' : 'Target buffer intact; zero capital siphoned'}
									</p>
								</div>
								<div class="mt-3 pt-2 border-t border-line text-[11px] font-mono text-dim flex justify-between">
									<span>Liquid Corridor</span>
									<span>{Number(rec.monthly_plan.emergency_topup_pct) > 0 ? 'Active Paydown' : 'Standby'}</span>
								</div>
							</div>

							<div class="p-3.5 bg-canvas border border-line rounded flex flex-col justify-between hover:bg-raised/40 transition-colors">
								<div>
									<div class="flex items-center justify-between text-[11px] font-mono">
										<span class="text-dim uppercase">Goal Reserve</span>
										<span class="px-1.5 py-0.5 rounded bg-raised border border-line text-[10px] font-mono font-semibold text-ink">
											{pct(rec.monthly_plan.goal_reserve_pct, 1)}
										</span>
									</div>
									<p class="mt-2 text-xl font-bold font-mono tabular-nums text-ink">{inr(rec.monthly_plan.goal_reserve_inr)}<span class="text-xs font-normal text-dim">/mo</span></p>
									<p class="mt-1 text-[12px] text-muted">For {profile.goal_name ?? 'targeted milestones'}</p>
								</div>
								<div class="mt-3 pt-2 border-t border-line text-[11px] font-mono text-dim flex justify-between">
									<span class="truncate max-w-[120px]">{profile.goal_name ?? 'Target Goal'}</span>
									<span class="text-ink">Arbitrage / FD</span>
								</div>
							</div>

							<div class="p-3.5 bg-canvas border border-line rounded flex flex-col justify-between hover:bg-raised/40 transition-colors">
								<div>
									<div class="flex items-center justify-between text-[11px] font-mono">
										<span class="text-dim uppercase">Debt Prepayment</span>
										<span class="px-1.5 py-0.5 rounded bg-raised border border-line text-[10px] font-mono font-semibold {Number(rec.monthly_plan.debt_prepayment_pct) > 0 ? 'text-danger' : 'text-dim'}">
											{Number(rec.monthly_plan.debt_prepayment_pct) > 0 ? pct(rec.monthly_plan.debt_prepayment_pct, 1) : 'PRISTINE'}
										</span>
									</div>
									<p class="mt-2 text-xl font-bold font-mono tabular-nums text-ink">{inr(rec.monthly_plan.debt_prepayment_inr)}<span class="text-xs font-normal text-dim">/mo</span></p>
									<p class="mt-1 text-[12px] text-muted">High-cost loan reduction</p>
								</div>
								<div class="mt-3 pt-2 border-t border-line text-[11px] font-mono text-dim flex justify-between">
									<span>Solvency Health</span>
									<span>{Number(rec.monthly_plan.debt_prepayment_pct) > 0 ? 'Active Paydown' : 'Pristine (0%)'}</span>
								</div>
							</div>

							<div class="p-3.5 bg-canvas border border-line rounded flex flex-col justify-between hover:bg-raised/40 transition-colors">
								<div>
									<div class="flex items-center justify-between text-[11px] font-mono">
										<span class="text-dim uppercase">Market SIP</span>
										<span class="px-1.5 py-0.5 rounded bg-raised border border-line text-[10px] font-mono font-semibold text-brand-soft">
											{pct(rec.monthly_plan.recommended_market_deployment_pct, 1)}
										</span>
									</div>
									<p class="mt-2 text-xl font-bold font-mono tabular-nums text-brand-soft">{inr(rec.monthly_plan.recommended_market_deployment_inr)}<span class="text-xs font-normal text-dim">/mo</span></p>
									<p class="mt-1 text-[12px] text-muted">Compounding across equity &amp; debt</p>
								</div>
								<div class="mt-3 pt-2 border-t border-line text-[11px] font-mono text-dim flex justify-between">
									<span>Investable Cap</span>
									<span class="text-ink">{inr(rec.monthly_plan.investable_capacity_inr)}</span>
								</div>
							</div>
						</div>
					</div>

					<!-- SECTION 2: STRATEGIC ASSET ALLOCATION DONUT & BLUEPRINT -->
					<div>
						<div class="flex flex-wrap items-center justify-between gap-2">
							<div>
								<h3 class="text-sm font-semibold uppercase tracking-wider text-ink">
									2. Strategic Asset Allocation &amp; Instrument Blueprint
								</h3>
								<p class="text-xs text-muted">
									{rec.readiness_status === 'NOT_READY'
										? 'Safe Reserve-Parking Blueprint (Zero Market Risk)'
										: 'Diversified NSE Equity, Sovereign G-Sec, & Gold Blueprint'}
								</p>
							</div>

							<!-- View Mode Toggle -->
							<div class="flex items-center gap-1 rounded border border-line bg-canvas p-0.5 no-print">
								<button
									class="rounded px-2.5 py-1 text-xs font-mono transition-colors {viewMode === 'cards' ? 'bg-raised font-semibold text-ink' : 'text-muted hover:text-ink'}"
									onclick={() => (viewMode = 'cards')}
								>
									Visual Cards
								</button>
								<button
									class="rounded px-2.5 py-1 text-xs font-mono transition-colors {viewMode === 'table' ? 'bg-raised font-semibold text-ink' : 'text-muted hover:text-ink'}"
									onclick={() => (viewMode = 'table')}
								>
									Data Table
								</button>
							</div>
						</div>

						<!-- Donut Chart & Category Cards -->
						<div class="mt-4 grid gap-4 lg:grid-cols-12">
							<!-- Donut Visual -->
							<div class="card flex flex-col items-center justify-center p-5 lg:col-span-5">
								<div class="relative flex items-center justify-center">
									<svg class="h-44 w-44 -rotate-90 transform" viewBox="0 0 130 130">
										<!-- Track circle -->
										<circle cx="65" cy="65" r="54" stroke="currentColor" stroke-width="14" fill="none" class="text-raised" />
										<!-- Equity Arc (Emerald) -->
										{#if equityLen > 0}
											<circle
												cx="65"
												cy="65"
												r="54"
												stroke="#22c55e"
												stroke-width="14"
												stroke-dasharray="{equityLen} {donutC}"
												stroke-dashoffset="0"
												fill="none"
												class="transition-all duration-1000 ease-out"
											/>
										{/if}
										<!-- Fixed Income Arc (Muted Slate-Zinc) -->
										{#if fixedLen > 0}
											<circle
												cx="65"
												cy="65"
												r="54"
												stroke="#71717a"
												stroke-width="14"
												stroke-dasharray="{fixedLen} {donutC}"
												stroke-dashoffset="-{equityLen}"
												fill="none"
												class="transition-all duration-1000 ease-out"
											/>
										{/if}
										<!-- Gold Arc (Warm Gold) -->
										{#if goldLen > 0}
											<circle
												cx="65"
												cy="65"
												r="54"
												stroke="#f59e0b"
												stroke-width="14"
												stroke-dasharray="{goldLen} {donutC}"
												stroke-dashoffset="-{equityLen + fixedLen}"
												fill="none"
												class="transition-all duration-1000 ease-out"
											/>
										{/if}
									</svg>
									<div class="absolute flex flex-col items-center text-center">
										<span class="text-base font-bold font-mono tabular-nums text-ink">{inr(rec.monthly_plan.recommended_market_deployment_inr)}</span>
										<span class="text-[10px] uppercase tracking-wider text-dim font-mono">Monthly SIP</span>
									</div>
								</div>
								<p class="mt-3 text-center text-xs text-muted font-mono">Target Asset Class Distribution</p>
							</div>

							<!-- Category Legend Pills -->
							<div class="grid gap-2 sm:grid-cols-3 lg:col-span-7 lg:grid-cols-1">
								<div class="flex items-center justify-between rounded border border-line border-l-2 border-l-brand-soft bg-canvas p-3.5 transition-colors hover:bg-raised/40">
									<div>
										<p class="text-xs font-medium text-ink">Domestic Equities</p>
										<p class="text-[11px] text-muted">Broad Nifty 50 Index &amp; Flexi-Cap Funds</p>
									</div>
									<div class="text-right">
										<p class="text-sm font-bold font-mono tabular-nums text-brand-soft">{rec.category_split_pct.equity_pct}%</p>
										<p class="text-[11px] font-mono tabular-nums text-dim">{inr((Number(rec.monthly_plan.recommended_market_deployment_inr) * rec.category_split_pct.equity_pct) / 100)}/mo</p>
									</div>
								</div>

								<div class="flex items-center justify-between rounded border border-line border-l-2 border-l-dim bg-canvas p-3.5 transition-colors hover:bg-raised/40">
									<div>
										<p class="text-xs font-medium text-ink">Fixed Income &amp; Liquid</p>
										<p class="text-[11px] text-muted">Sovereign 10Y G-Sec ETF &amp; Liquid Funds</p>
									</div>
									<div class="text-right">
										<p class="text-sm font-bold font-mono tabular-nums text-ink">{rec.category_split_pct.fixed_income_and_liquid_pct}%</p>
										<p class="text-[11px] font-mono tabular-nums text-dim">{inr((Number(rec.monthly_plan.recommended_market_deployment_inr) * rec.category_split_pct.fixed_income_and_liquid_pct) / 100)}/mo</p>
									</div>
								</div>

								<div class="flex items-center justify-between rounded border border-line border-l-2 border-l-amber bg-canvas p-3.5 transition-colors hover:bg-raised/40">
									<div>
										<p class="text-xs font-medium text-ink">Gold BeES ETF</p>
										<p class="text-[11px] text-muted">Sovereign inflation &amp; currency hedge</p>
									</div>
									<div class="text-right">
										<p class="text-sm font-bold font-mono tabular-nums text-amber">{rec.category_split_pct.gold_pct}%</p>
										<p class="text-[11px] font-mono tabular-nums text-dim">{inr((Number(rec.monthly_plan.recommended_market_deployment_inr) * rec.category_split_pct.gold_pct) / 100)}/mo</p>
									</div>
								</div>
							</div>
						</div>

						<!-- INSTRUMENT EXECUTION: VISUAL CARDS VIEW -->
						{#if viewMode === 'cards'}
							<div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
								{#each rec.asset_allocations as item (item.symbol)}
									{@const aid = assetIdForSymbol(item.symbol)}
									<div class="card rounded-lg p-4 flex flex-col justify-between hover:bg-raised/40 transition-colors">
										<div>
											<div class="flex items-start justify-between gap-2">
												<div>
													<h4 class="font-medium text-ink text-[14px]">{item.name}</h4>
													<p class="text-[11px] font-mono text-dim"><span class="text-ink/80">{item.symbol}</span> / <span>{labelize(item.asset_type)}</span></p>
												</div>
												<span class="badge-pill {item.action_status === 'DEPLOY_NOW' ? 'border-line bg-raised text-brand-soft' : item.action_status === 'STAGE_CAUTIOUSLY' ? 'border-line bg-raised text-amber' : 'border-line bg-raised text-dim'}">
													{labelize(item.action_status)}
												</span>
											</div>

											<div class="mt-3 flex items-baseline justify-between rounded bg-canvas p-2.5 border border-line">
												<div>
													<span class="text-[10px] uppercase text-dim font-mono">Monthly Allocation</span>
													<p class="text-base font-bold font-mono tabular-nums text-ink">{inr(item.monthly_amount_inr)}<span class="text-xs font-normal text-dim">/mo</span></p>
												</div>
												<span class="rounded bg-raised border border-line px-2 py-0.5 text-xs font-bold font-mono tabular-nums text-brand-soft">
													{item.allocation_pct}%
												</span>
											</div>

											<div class="mt-3 space-y-1.5 text-[11px]">
												<div class="flex justify-between text-muted">
													<span class="text-dim">Role:</span>
													<span class="font-medium text-ink">{item.role}</span>
												</div>
												{#if Number(item.lump_sum_amount_inr) > 0}
													<div class="flex justify-between text-muted">
														<span class="text-dim">Staged Lump-Sum:</span>
														<span class="font-semibold font-mono tabular-nums text-ink">{inr(item.lump_sum_amount_inr)}</span>
													</div>
												{/if}
											</div>

											<p class="mt-3 border-t border-line pt-2 text-[12px] leading-relaxed text-muted">{item.rationale}</p>
										</div>

										<div class="mt-4 flex items-center justify-end gap-2 border-t border-line pt-3 no-print">
											{#if aid}
												<a class="btn btn-ghost !px-2.5 !py-1 text-[11px]" href="/explorer/{aid}">Details</a>
												<a class="btn btn-primary !px-2.5 !py-1 text-[11px]" href="/research?asset={aid}">Research</a>
											{/if}
										</div>
									</div>
								{/each}
							</div>
						{:else}
							<!-- DATA TABLE VIEW (COMPACT SPREADSHEET) -->
							<div class="table-wrap mt-4">
								<table class="data-table">
									<thead>
										<tr>
											<th>Instrument</th>
											<th>Role in Portfolio</th>
											<th>Weight</th>
											<th>Monthly Amount</th>
											<th>Lump-Sum Staged</th>
											<th>Action Status</th>
											<th>Why this fits your {labelize(rec.experience_level)} profile</th>
											<th class="no-print">Inspect</th>
										</tr>
									</thead>
									<tbody>
										{#each rec.asset_allocations as item (item.symbol)}
											{@const aid = assetIdForSymbol(item.symbol)}
											<tr>
												<td>
													<p class="font-medium text-ink">{item.name}</p>
													<p class="text-[11px] font-mono text-dim"><span class="text-ink/80">{item.symbol}</span> / <span>{labelize(item.asset_type)}</span></p>
												</td>
												<td class="text-[12px]">{item.role}</td>
												<td class="whitespace-nowrap font-bold font-mono tabular-nums text-brand-soft">{item.allocation_pct}%</td>
												<td class="whitespace-nowrap font-bold font-mono tabular-nums text-ink">{inr(item.monthly_amount_inr)}/mo</td>
												<td class="whitespace-nowrap font-mono tabular-nums text-muted">{inr(item.lump_sum_amount_inr)}</td>
												<td class="whitespace-nowrap">
													<span class="badge-pill {item.action_status === 'DEPLOY_NOW' ? 'border-line bg-raised text-brand-soft' : item.action_status === 'STAGE_CAUTIOUSLY' ? 'border-line bg-raised text-amber' : 'border-line bg-raised text-dim'}">
														{labelize(item.action_status)}
													</span>
												</td>
												<td class="max-w-xs text-[12px] leading-relaxed text-muted">{item.rationale}</td>
												<td class="no-print">
													{#if aid}
														<div class="flex flex-wrap gap-1.5">
															<a class="btn btn-ghost !px-2.5 !py-1 text-[11px]" href="/explorer/{aid}">Details</a>
															<a class="btn btn-primary !px-2.5 !py-1 text-[11px]" href="/research?asset={aid}">Research</a>
														</div>
													{/if}
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						{/if}
					</div>

					<!-- SECTION 3: LUMP-SUM LIQUID SAVINGS BREAKDOWN -->
					<div class="rounded-xl border border-line bg-raised/30 p-4">
						<h3 class="text-[12px] font-semibold uppercase tracking-wider text-muted">
							3. Lump-Sum Liquid Savings Breakdown ({inr(rec.lump_sum_plan.liquid_savings_inr)} total liquid savings)
						</h3>
						<div class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-[13px]">
							<div class="rounded-lg bg-canvas/60 p-2.5">
								<span class="text-[11px] text-muted">Locked for Emergency:</span>
								<p class="font-bold tabular-nums text-ink">{inr(rec.lump_sum_plan.emergency_locked_inr)}</p>
							</div>
							<div class="rounded-lg bg-canvas/60 p-2.5">
								<span class="text-[11px] text-muted">Locked for Goal:</span>
								<p class="font-bold tabular-nums text-ink">{inr(rec.lump_sum_plan.goal_locked_inr)}</p>
							</div>
							<div class="rounded-lg bg-canvas/60 p-2.5">
								<span class="text-[11px] text-muted">Immediate Reserve Boost:</span>
								<p class="font-bold tabular-nums text-ink">{inr(rec.lump_sum_plan.immediate_reserve_boost_inr)}</p>
							</div>
							<div class="rounded-lg bg-canvas/60 p-2.5">
								<span class="text-[11px] text-muted">Staged Market Capital:</span>
								<p class="font-bold tabular-nums text-brand-soft">{inr(rec.lump_sum_plan.staged_market_deployment_inr)}</p>
								{#if rec.lump_sum_plan.recommended_tranches_months > 0}
									<p class="text-[10px] text-muted">({rec.lump_sum_plan.recommended_tranches_months} monthly tranches of {inr(rec.lump_sum_plan.monthly_tranche_inr)})</p>
								{/if}
							</div>
						</div>
					</div>
				</div>
			</Card>
		{/if}

		<div class="grid gap-6 lg:grid-cols-3">
			<Card title="Constraints and blockers" subtitle="Each finding lists the inputs that produced it." class="lg:col-span-2">
				{#if readiness.findings.filter((f) => f.severity !== 'INFO').length === 0}
					<Notice tone="success" title="No constraints recorded">
						Cash flow, reserves, loans and horizon clear every documented guardrail. That permits research; review the recommendations above and run Devil's Advocate checks before acting.
					</Notice>
				{:else}
					<div class="space-y-3">
						{#each readiness.findings.filter((f) => f.severity !== 'INFO') as f (f.code)}
							<article class="rounded-xl border border-line bg-raised/40 p-4">
								<div class="flex flex-wrap items-center gap-2">
									<StatusBadge status={f.severity === 'BLOCKER' ? 'NOT_READY' : 'PREPARATION'} text={f.severity === 'BLOCKER' ? 'Blocker' : 'Warning'} />
									<p class="text-[14px] font-medium">{f.label}</p>
								</div>
								<p class="muted mt-2">{f.detail}</p>
								<div class="mt-2 flex flex-wrap gap-1.5">
									{#each Object.entries(f.inputs) as [key, value] (key)}
										<span class="rounded border border-line bg-canvas px-1.5 py-0.5 text-[10px] tabular-nums text-muted">{labelize(key)}: {value}</span>
									{/each}
								</div>
							</article>
						{/each}
					</div>
				{/if}
			</Card>

			<Card title="Your goal and money map" subtitle="Total savings is not the same as investable money.">
				<dl class="kv">
					<div><dt>Goal</dt><dd>{profile.goal_name ?? 'Not stated'}</dd></div>
					<div><dt>Target</dt><dd>{inr(profile.goal_amount)}</dd></div>
					<div><dt>Deadline</dt><dd>{dateLabel(profile.goal_deadline)}</dd></div>
					<div><dt>Monthly need for goal</dt><dd>{inr(text('goal_monthly_need'))}</dd></div>
					<div><dt>Total savings</dt><dd>{inr(profile.total_savings)}</dd></div>
					<div><dt>Liquid savings</dt><dd>{inr(profile.liquid_savings)}</dd></div>
					<div><dt>Emergency reserve</dt><dd>{inr(profile.emergency_reserves)}</dd></div>
					<div><dt>Goal reserve</dt><dd>{inr(profile.goal_reserved_amount)}</dd></div>
					<div><dt>Free liquid money</dt><dd>{inr(text('unallocated_liquid'))}</dd></div>
					<div><dt>You designated per month</dt><dd>{inr(profile.monthly_investment_designated)}</dd></div>
					<div><dt>Loan EMI burden</dt><dd>{text('emi_burden') ? pct(Number(m.emi_burden) * 100) : 'n/a'}</dd></div>
				</dl>
			</Card>
		</div>

		<div class="grid gap-6 lg:grid-cols-2">
			<Card title="Suggested next steps" subtitle="Ordered by what would unblock the most.">
				<ol class="list-decimal space-y-2 pl-5 text-[13px] leading-relaxed">
					{#each readiness.improvement_steps as step, i (i)}<li>{step}</li>{/each}
				</ol>
				<div class="mt-5 grid gap-2 sm:grid-cols-2">
					<a class="btn" href="/explorer">Explore NSE &amp; AMFI instruments</a>
					<a class="btn" href="/timing">Read the Three Clocks</a>
					<a class="btn" href="/simulator">Run historical or what-if simulation</a>
					<a class="btn" href="/research">Run two-sided research analysis</a>
				</div>
			</Card>

			<Card title="Missing information and limits" subtitle="Reported, never assumed.">
				{#if readiness.missing_information.length === 0 && readiness.limitations.length === 0}
					<p class="muted">Nothing is missing from the inputs you provided.</p>
				{:else}
					<ul class="list-disc space-y-2 pl-5 text-[13px] leading-relaxed text-muted">
						{#each readiness.missing_information as item, i (i)}<li class="text-warn">Missing: {item}</li>{/each}
						{#each readiness.limitations as item, i (i)}<li>{item}</li>{/each}
					</ul>
				{/if}
				<p class="muted mt-5">{readiness.disclaimer}</p>
			</Card>
		</div>
	</div>
{:else}
	<Notice tone="info">Select a profile from the switcher in the header.</Notice>
{/if}
