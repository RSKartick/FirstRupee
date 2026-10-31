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

	const gaugeAngle = $derived.by(() => {
		// Semicircle from -180 deg to 0 deg
		return -180 + (readinessScore / 100) * 180;
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
						<span class="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-500"></span>
						<span class="text-[11px] font-semibold uppercase tracking-[0.14em] text-brand-soft">Live Indian Market Feeds (NSE / AMFI)</span>
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
						<span class="rounded-full border border-brand/40 bg-brand/10 px-2.5 py-0.5 text-[11px] font-medium text-brand-soft">
							Mode: {labelize(profile.investment_experience)}
						</span>
						<span class="text-[11px] text-muted">Rule set {readiness.rule_version} · as of {dateLabel(readiness.as_of)}</span>
						{#if readiness.completeness === 'INCOMPLETE'}<span class="rounded-full border border-danger/40 bg-danger/10 px-2.5 py-0.5 text-[11px] uppercase text-danger">Assessment incomplete</span>{/if}
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

		<!-- VISUAL TELEMETRY COCKPIT: RADIAL GAUGE & TRI-RING DIAGNOSTICS -->
		<section class="grid gap-4 lg:grid-cols-12">
			<!-- Speed Gauge Card -->
			<div class="card flex flex-col items-center justify-center p-6 lg:col-span-5">
				<div class="flex w-full items-center justify-between border-b border-line/60 pb-3">
					<div>
						<h3 class="text-sm font-semibold text-ink">Readiness Telemetry</h3>
						<p class="text-[11px] text-muted">Deterministic Guardrail Assessment</p>
					</div>
					<StatusBadge status={readiness.status} />
				</div>

				<div class="relative mt-4 flex flex-col items-center">
					<svg class="h-36 w-64 overflow-visible" viewBox="0 0 200 125">
						<!-- Track Arc -->
						<path
							d="M 20 105 A 80 80 0 0 1 180 105"
							fill="none"
							stroke="currentColor"
							stroke-width="14"
							stroke-linecap="round"
							class="text-raised"
						/>
						<!-- Value Arc -->
						<path
							d="M 20 105 A 80 80 0 0 1 180 105"
							fill="none"
							stroke={readiness.status === 'READY_TO_EXPLORE' ? '#10b981' : readiness.status === 'PREPARATION' ? '#f59e0b' : '#f43f5e'}
							stroke-width="14"
							stroke-linecap="round"
							stroke-dasharray="251.33"
							stroke-dashoffset={251.33 * (1 - readinessScore / 100)}
							class="transition-all duration-1000 ease-out"
						/>
						<!-- Min / Max scale labels -->
						<text x="18" y="122" font-size="9" fill="currentColor" class="text-muted font-mono" text-anchor="middle">0</text>
						<text x="182" y="122" font-size="9" fill="currentColor" class="text-muted font-mono" text-anchor="middle">100</text>

						<!-- Dynamic Pointer Needle -->
						<g transform="rotate({gaugeAngle}, 100, 105)" class="transition-transform duration-1000 ease-out">
							<line x1="100" y1="105" x2="30" y2="105" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="text-ink" />
							<polygon points="26,105 36,101 36,109" fill="currentColor" class="text-ink" />
						</g>
						<!-- Needle Pivot -->
						<circle cx="100" cy="105" r="7" class="fill-canvas stroke-ink stroke-2" />
						<circle cx="100" cy="105" r="3.5" class="fill-brand-soft" />
					</svg>

					<div class="-mt-3 text-center">
						<span class="text-3xl font-bold font-mono tabular-nums tracking-tight text-ink">{readinessScore}</span>
						<span class="text-xs font-semibold font-mono text-muted">/ 100</span>
						<p class="mt-0.5 text-[11px] font-bold uppercase tracking-wider {readiness.status === 'READY_TO_EXPLORE' ? 'text-brand-soft' : readiness.status === 'PREPARATION' ? 'text-amber' : 'text-danger'}">
							{labelize(readiness.status)}
						</p>
					</div>
				</div>

				<div class="mt-4 grid w-full grid-cols-2 gap-2 border-t border-line/60 pt-3 text-center text-[11px]">
					<div class="rounded-lg bg-raised/40 p-2">
						<span class="text-muted">Risk Capacity:</span>
						<p class="font-semibold text-ink">{text('risk_capacity_band') ?? 'Standard'} ({text('risk_capacity_score') ?? 'n/a'})</p>
					</div>
					<div class="rounded-lg bg-raised/40 p-2">
						<span class="text-muted">Risk Tolerance:</span>
						<p class="font-semibold text-ink">{text('risk_tolerance_band') ?? 'Moderate'} ({text('risk_tolerance_score') ?? 'n/a'})</p>
					</div>
				</div>
			</div>

			<!-- Tri-Ring Diagnostic Telemetry -->
			<div class="card flex flex-col justify-between p-6 lg:col-span-7">
				<div class="flex items-center justify-between border-b border-line/60 pb-3">
					<div>
						<h3 class="text-sm font-semibold text-ink">Diagnostic Health Rings</h3>
						<p class="text-[11px] text-muted">Core Solvency &amp; Liquidity Guardrails</p>
					</div>
					<span class="text-[11px] text-muted">3-Vector Telemetry</span>
				</div>

				<div class="my-auto grid gap-4 py-4 sm:grid-cols-3">
					<!-- Ring 1: Emergency Runway -->
					<div class="flex flex-col items-center text-center">
						<div class="relative flex items-center justify-center">
							<svg class="h-24 w-24 -rotate-90 transform" viewBox="0 0 84 84">
								<circle cx="42" cy="42" r="36" stroke="currentColor" stroke-width="7" fill="none" class="text-raised" />
								<circle
									cx="42"
									cy="42"
									r="36"
									stroke={emergencyMonths >= 6 ? '#10b981' : '#f59e0b'}
									stroke-width="7"
									stroke-linecap="round"
									stroke-dasharray="226.2"
									stroke-dashoffset={226.2 * (1 - emergencyFraction)}
									fill="none"
									class="transition-all duration-1000 ease-out"
								/>
							</svg>
							<div class="absolute flex flex-col items-center">
								<span class="text-sm font-bold font-mono tabular-nums text-ink">{emergencyMonths.toFixed(1)}m</span>
								<span class="text-[9px] font-semibold uppercase tracking-wider text-muted">Runway</span>
							</div>
						</div>
						<h4 class="mt-2 text-xs font-semibold text-ink">Liquid Reserve</h4>
						<p class="text-[10px] font-mono text-muted">Target: 6.0m ({inr(text('emergency_reserves'))})</p>
					</div>

					<!-- Ring 2: Solvency & Debt Burden -->
					<div class="flex flex-col items-center text-center">
						<div class="relative flex items-center justify-center">
							<svg class="h-24 w-24 -rotate-90 transform" viewBox="0 0 84 84">
								<circle cx="42" cy="42" r="36" stroke="currentColor" stroke-width="7" fill="none" class="text-raised" />
								<circle
									cx="42"
									cy="42"
									r="36"
									stroke="#06b6d4"
									stroke-width="7"
									stroke-linecap="round"
									stroke-dasharray="226.2"
									stroke-dashoffset={226.2 * (1 - solvencyRatio)}
									fill="none"
									class="transition-all duration-1000 ease-out"
								/>
							</svg>
							<div class="absolute flex flex-col items-center">
								<span class="text-sm font-bold font-mono tabular-nums text-ink">{(solvencyRatio * 100).toFixed(0)}%</span>
								<span class="text-[9px] font-semibold uppercase tracking-wider text-muted">Solvency</span>
							</div>
						</div>
						<h4 class="mt-2 text-xs font-semibold text-ink">Debt Freedom</h4>
						<p class="text-[10px] font-mono text-muted">EMI Burden: {text('emi_burden') ? pct(Number(m.emi_burden) * 100) : '0%'}</p>
					</div>

					<!-- Ring 3: Surplus Velocity -->
					<div class="flex flex-col items-center text-center">
						<div class="relative flex items-center justify-center">
							<svg class="h-24 w-24 -rotate-90 transform" viewBox="0 0 84 84">
								<circle cx="42" cy="42" r="36" stroke="currentColor" stroke-width="7" fill="none" class="text-raised" />
								<circle
									cx="42"
									cy="42"
									r="36"
									stroke="#a855f7"
									stroke-width="7"
									stroke-linecap="round"
									stroke-dasharray="226.2"
									stroke-dashoffset={226.2 * (1 - surplusRetentionRatio)}
									fill="none"
									class="transition-all duration-1000 ease-out"
								/>
							</svg>
							<div class="absolute flex flex-col items-center">
								<span class="text-sm font-bold font-mono tabular-nums text-ink">{(surplusRetentionRatio * 100).toFixed(0)}%</span>
								<span class="text-[9px] font-semibold uppercase tracking-wider text-muted">Velocity</span>
							</div>
						</div>
						<h4 class="mt-2 text-xs font-semibold text-ink">Surplus Velocity</h4>
						<p class="text-[10px] font-mono text-muted">{inr(text('monthly_surplus'))}/mo</p>
					</div>
				</div>

				<div class="flex flex-wrap items-center justify-between gap-2 border-t border-line/60 pt-3 text-[12px]">
					<span class="text-muted">Investable Monthly Capacity:</span>
					<span class="font-bold tabular-nums text-brand-soft">{inr(text('investable_monthly'))}/month</span>
				</div>
			</div>
		</section>

		<!-- 4 CORE METRIC CARDS -->
		<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
			<Stat label="Monthly surplus" value={inr(text('monthly_surplus'))} tone={Number(m.monthly_surplus) > 0 ? 'success' : 'danger'} hint="Income minus every recorded outflow" />
			<Stat
				label="Emergency coverage"
				value={text('emergency_coverage_months') ? `${Number(m.emergency_coverage_months).toFixed(1)} months` : 'Unknown'}
				tone={text('emergency_coverage_months') && Number(m.emergency_coverage_months) >= 6 ? 'success' : 'warn'}
				hint="Liquid reserve / essential expenses (target 6 months)"
			/>
			<Stat label="Free monthly money" value={inr(text('investable_monthly'))} tone="info" hint="After goal and reserve needs; zero if none" />
			<Stat label="Goal horizon" value={months(m.goal_horizon_months as number | null)} hint={profile.goal_name ?? 'No goal named'} />
		</div>

		{#if rec}
			<Card
				title="Personalised Recommendations (Textual &amp; Numerical)"
				subtitle={`Calculated from your ${labelize(readiness.status)} state · ${rec.tone_label}`}
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

				<div class="space-y-8">
					<!-- Strategic Summary Callout -->
					<div class="rounded-xl border border-brand/30 bg-brand/5 p-5">
						<div class="flex flex-wrap items-center justify-between gap-2">
							<p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-brand-soft">{rec.tone_label}</p>
							<span class="text-[12px] font-medium text-muted">
								Target Category Split: {rec.category_split_pct.equity_pct}% Equity · {rec.category_split_pct.fixed_income_and_liquid_pct}% Fixed Income / Liquid · {rec.category_split_pct.gold_pct}% Gold
							</span>
						</div>
						<h3 class="mt-2 text-lg font-semibold text-ink">{rec.headline}</h3>
						<p class="mt-2 text-[14px] leading-relaxed text-muted">{rec.summary}</p>
						<ul class="mt-4 space-y-1.5 border-t border-line/60 pt-3 text-[13px] leading-relaxed">
							{#each rec.textual_guidelines as guide, idx (idx)}
								<li class="flex items-start gap-2">
									<span class="mt-0.5 font-semibold text-brand-soft">{idx + 1}.</span>
									<span>{guide}</span>
								</li>
							{/each}
						</ul>
					</div>

					<!-- SECTION 1: SURPLUS CASH FLOW ROUTER (HORIZONTAL PIPELINE) -->
					<div>
						<div class="flex flex-wrap items-baseline justify-between gap-2">
							<h3 class="text-sm font-semibold uppercase tracking-wider text-ink">
								1. Surplus Cash Flow Router
							</h3>
							<span class="text-xs text-muted">
								Available Surplus: <strong class="tabular-nums text-ink">{inr(rec.monthly_plan.monthly_surplus_inr)}/mo</strong>
								(Outflows: {inr(rec.monthly_plan.committed_outflow_inr)}/mo)
							</span>
						</div>

						<!-- Proportional Horizontal Bar -->
						<div class="mt-3 overflow-hidden rounded-full border border-line bg-canvas p-1">
							<div class="flex h-4 w-full overflow-hidden rounded-full">
								{#if Number(rec.monthly_plan.emergency_topup_pct) > 0}
									<div
										class="bg-amber transition-all duration-700"
										style="width: {rec.monthly_plan.emergency_topup_pct}%;"
										title="Emergency Reserve: {rec.monthly_plan.emergency_topup_pct}% ({inr(rec.monthly_plan.emergency_topup_inr)}/mo)"
									></div>
								{/if}
								{#if Number(rec.monthly_plan.goal_reserve_pct) > 0}
									<div
										class="bg-azure transition-all duration-700"
										style="width: {rec.monthly_plan.goal_reserve_pct}%;"
										title="Goal Reserve: {rec.monthly_plan.goal_reserve_pct}% ({inr(rec.monthly_plan.goal_reserve_inr)}/mo)"
									></div>
								{/if}
								{#if Number(rec.monthly_plan.debt_prepayment_pct) > 0}
									<div
										class="bg-danger transition-all duration-700"
										style="width: {rec.monthly_plan.debt_prepayment_pct}%;"
										title="Debt Prepayment: {rec.monthly_plan.debt_prepayment_pct}% ({inr(rec.monthly_plan.debt_prepayment_inr)}/mo)"
									></div>
								{/if}
								{#if Number(rec.monthly_plan.recommended_market_deployment_pct) > 0}
									<div
										class="bg-brand-soft transition-all duration-700"
										style="width: {rec.monthly_plan.recommended_market_deployment_pct}%;"
										title="Market SIP: {rec.monthly_plan.recommended_market_deployment_pct}% ({inr(rec.monthly_plan.recommended_market_deployment_inr)}/mo)"
									></div>
								{/if}
							</div>
						</div>

						<!-- Pipeline Cards Grid -->
						<div class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
							<div class="rounded-xl border border-line bg-raised/40 p-4 transition-colors hover:border-amber/40">
								<div class="flex items-center justify-between">
									<p class="text-[11px] font-semibold uppercase text-amber">Emergency Reserve</p>
									<span class="rounded bg-amber/15 px-1.5 py-0.5 text-[10px] font-mono font-bold text-amber">{pct(rec.monthly_plan.emergency_topup_pct, 1)}</span>
								</div>
								<p class="mt-2 text-xl font-bold font-mono tabular-nums text-ink">{inr(rec.monthly_plan.emergency_topup_inr)}<span class="text-xs font-normal text-muted">/mo</span></p>
								<p class="mt-1 text-[11px] text-muted">Builds 6-month liquid cushion</p>
							</div>

							<div class="rounded-xl border border-line bg-raised/40 p-4 transition-colors hover:border-azure/40">
								<div class="flex items-center justify-between">
									<p class="text-[11px] font-semibold uppercase text-azure">Goal Reserve Funding</p>
									<span class="rounded bg-azure/15 px-1.5 py-0.5 text-[10px] font-mono font-bold text-azure">{pct(rec.monthly_plan.goal_reserve_pct, 1)}</span>
								</div>
								<p class="mt-2 text-xl font-bold font-mono tabular-nums text-ink">{inr(rec.monthly_plan.goal_reserve_inr)}<span class="text-xs font-normal text-muted">/mo</span></p>
								<p class="mt-1 text-[11px] text-muted">For {profile.goal_name ?? 'targeted milestones'}</p>
							</div>

							<div class="rounded-xl border border-line bg-raised/40 p-4 transition-colors hover:border-danger/40">
								<div class="flex items-center justify-between">
									<p class="text-[11px] font-semibold uppercase text-muted">Debt Prepayment</p>
									<span class="rounded bg-raised px-1.5 py-0.5 text-[10px] font-mono font-bold text-muted">{pct(rec.monthly_plan.debt_prepayment_pct, 1)}</span>
								</div>
								<p class="mt-2 text-xl font-bold font-mono tabular-nums text-ink">{inr(rec.monthly_plan.debt_prepayment_inr)}<span class="text-xs font-normal text-muted">/mo</span></p>
								<p class="mt-1 text-[11px] text-muted">High-cost loan reduction</p>
							</div>

							<div class="rounded-xl border border-brand/50 bg-brand/10 p-4 shadow-sm">
								<div class="flex items-center justify-between">
									<p class="text-[11px] font-semibold uppercase text-brand-soft">Recommended Market SIP</p>
									<span class="rounded bg-brand/20 px-1.5 py-0.5 text-[10px] font-mono font-bold text-brand-soft">{pct(rec.monthly_plan.recommended_market_deployment_pct, 1)}</span>
								</div>
								<p class="mt-2 text-xl font-bold font-mono tabular-nums text-brand-soft">{inr(rec.monthly_plan.recommended_market_deployment_inr)}<span class="text-xs font-normal text-muted">/mo</span></p>
								<p class="mt-1 text-[11px] text-muted">Investable cap: {inr(rec.monthly_plan.investable_capacity_inr)}</p>
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
							<div class="flex items-center gap-1 rounded-lg border border-line bg-raised/40 p-0.5 no-print">
								<button
									class="rounded-md px-2.5 py-1 text-xs font-medium transition-colors {viewMode === 'cards' ? 'bg-brand/15 font-semibold text-brand-soft' : 'text-muted hover:text-ink'}"
									onclick={() => (viewMode = 'cards')}
								>
									Visual Cards
								</button>
								<button
									class="rounded-md px-2.5 py-1 text-xs font-medium transition-colors {viewMode === 'table' ? 'bg-brand/15 font-semibold text-brand-soft' : 'text-muted hover:text-ink'}"
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
										<circle cx="65" cy="65" r="54" stroke="currentColor" stroke-width="15" fill="none" class="text-raised" />
										<!-- Equity Arc (Green) -->
										{#if equityLen > 0}
											<circle
												cx="65"
												cy="65"
												r="54"
												stroke="#10b981"
												stroke-width="15"
												stroke-dasharray="{equityLen} {donutC}"
												stroke-dashoffset="0"
												fill="none"
												class="transition-all duration-1000 ease-out"
											/>
										{/if}
										<!-- Fixed Income Arc (Azure) -->
										{#if fixedLen > 0}
											<circle
												cx="65"
												cy="65"
												r="54"
												stroke="#06b6d4"
												stroke-width="15"
												stroke-dasharray="{fixedLen} {donutC}"
												stroke-dashoffset="-{equityLen}"
												fill="none"
												class="transition-all duration-1000 ease-out"
											/>
										{/if}
										<!-- Gold Arc (Amber) -->
										{#if goldLen > 0}
											<circle
												cx="65"
												cy="65"
												r="54"
												stroke="#f59e0b"
												stroke-width="15"
												stroke-dasharray="{goldLen} {donutC}"
												stroke-dashoffset="-{equityLen + fixedLen}"
												fill="none"
												class="transition-all duration-1000 ease-out"
											/>
										{/if}
									</svg>
									<div class="absolute flex flex-col items-center text-center">
										<span class="text-base font-bold font-mono tabular-nums text-ink">{inr(rec.monthly_plan.recommended_market_deployment_inr)}</span>
										<span class="text-[10px] uppercase tracking-wider text-muted font-medium">Monthly SIP</span>
									</div>
								</div>
								<p class="mt-3 text-center text-xs text-muted">Target Asset Class Distribution</p>
							</div>

							<!-- Category Legend Pills -->
							<div class="grid gap-2 sm:grid-cols-3 lg:col-span-7 lg:grid-cols-1">
								<div class="flex items-center justify-between rounded-xl border border-line bg-raised/30 p-3.5 transition-colors hover:border-brand/40">
									<div class="flex items-center gap-3">
										<div class="h-3 w-3 rounded-full bg-emerald-500 shadow-sm"></div>
										<div>
											<p class="text-xs font-semibold text-ink">Domestic Equities</p>
											<p class="text-[11px] text-muted">Broad Nifty 50 Index &amp; Flexi-Cap Funds</p>
										</div>
									</div>
									<div class="text-right">
										<p class="text-sm font-bold font-mono tabular-nums text-brand-soft">{rec.category_split_pct.equity_pct}%</p>
										<p class="text-[11px] font-mono tabular-nums text-muted">{inr((Number(rec.monthly_plan.recommended_market_deployment_inr) * rec.category_split_pct.equity_pct) / 100)}/mo</p>
									</div>
								</div>

								<div class="flex items-center justify-between rounded-xl border border-line bg-raised/30 p-3.5 transition-colors hover:border-azure/40">
									<div class="flex items-center gap-3">
										<div class="h-3 w-3 rounded-full bg-cyan-500 shadow-sm"></div>
										<div>
											<p class="text-xs font-semibold text-ink">Fixed Income &amp; Liquid</p>
											<p class="text-[11px] text-muted">Sovereign 10Y G-Sec ETF &amp; Liquid Funds</p>
										</div>
									</div>
									<div class="text-right">
										<p class="text-sm font-bold font-mono tabular-nums text-azure">{rec.category_split_pct.fixed_income_and_liquid_pct}%</p>
										<p class="text-[11px] font-mono tabular-nums text-muted">{inr((Number(rec.monthly_plan.recommended_market_deployment_inr) * rec.category_split_pct.fixed_income_and_liquid_pct) / 100)}/mo</p>
									</div>
								</div>

								<div class="flex items-center justify-between rounded-xl border border-line bg-raised/30 p-3.5 transition-colors hover:border-amber/40">
									<div class="flex items-center gap-3">
										<div class="h-3 w-3 rounded-full bg-amber-500 shadow-sm"></div>
										<div>
											<p class="text-xs font-semibold text-ink">Gold BeES ETF</p>
											<p class="text-[11px] text-muted">Sovereign inflation &amp; currency hedge</p>
										</div>
									</div>
									<div class="text-right">
										<p class="text-sm font-bold font-mono tabular-nums text-amber">{rec.category_split_pct.gold_pct}%</p>
										<p class="text-[11px] font-mono tabular-nums text-muted">{inr((Number(rec.monthly_plan.recommended_market_deployment_inr) * rec.category_split_pct.gold_pct) / 100)}/mo</p>
									</div>
								</div>
							</div>
						</div>

						<!-- INSTRUMENT EXECUTION: VISUAL CARDS VIEW -->
						{#if viewMode === 'cards'}
							<div class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
								{#each rec.asset_allocations as item (item.symbol)}
									{@const aid = assetIdForSymbol(item.symbol)}
									<div class="group flex flex-col justify-between rounded-xl border border-line bg-canvas/80 p-4 shadow-sm transition-all hover:border-brand/50 hover:bg-raised/30">
										<div>
											<div class="flex items-start justify-between gap-2">
												<div>
													<h4 class="font-semibold text-ink">{item.name}</h4>
													<p class="text-[11px] font-mono text-muted">{item.symbol} · {labelize(item.asset_type)}</p>
												</div>
												<span class="badge-pill {item.action_status === 'DEPLOY_NOW' ? 'border-brand/40 bg-brand/10 text-brand-soft' : item.action_status === 'STAGE_CAUTIOUSLY' ? 'border-amber/40 bg-amber/10 text-amber' : 'border-azure/40 bg-azure/10 text-azure'}">
													{labelize(item.action_status)}
												</span>
											</div>

											<div class="mt-3 flex items-baseline justify-between rounded-lg bg-raised/50 p-2.5">
												<div>
													<span class="text-[10px] uppercase text-muted font-medium">Monthly Allocation</span>
													<p class="text-lg font-bold font-mono tabular-nums text-ink">{inr(item.monthly_amount_inr)}<span class="text-xs font-normal text-muted">/mo</span></p>
												</div>
												<span class="rounded-md bg-brand/15 px-2 py-0.5 text-xs font-bold font-mono tabular-nums text-brand-soft">
													{item.allocation_pct}%
												</span>
											</div>

											<div class="mt-3 space-y-1.5 text-[11px]">
												<div class="flex justify-between text-muted">
													<span>Role:</span>
													<span class="font-medium text-ink">{item.role}</span>
												</div>
												{#if Number(item.lump_sum_amount_inr) > 0}
													<div class="flex justify-between text-muted">
														<span>Staged Lump-Sum:</span>
														<span class="font-semibold font-mono tabular-nums text-ink">{inr(item.lump_sum_amount_inr)}</span>
													</div>
												{/if}
											</div>

											<p class="mt-3 border-t border-line/60 pt-2 text-[12px] leading-relaxed text-muted">{item.rationale}</p>
										</div>

										<div class="mt-4 flex items-center justify-end gap-2 border-t border-line/60 pt-3 no-print">
											{#if aid}
												<a class="btn !px-3 !py-1 text-[11px]" href="/explorer/{aid}">Inspect Details</a>
												<a class="btn btn-primary !px-3 !py-1 text-[11px]" href="/research?asset={aid}">Research</a>
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
													<p class="text-[11px] font-mono text-muted">{item.symbol} · {labelize(item.asset_type)}</p>
												</td>
												<td class="text-[12px]">{item.role}</td>
												<td class="whitespace-nowrap font-bold font-mono tabular-nums text-brand-soft">{item.allocation_pct}%</td>
												<td class="whitespace-nowrap font-bold font-mono tabular-nums text-ink">{inr(item.monthly_amount_inr)}/mo</td>
												<td class="whitespace-nowrap font-mono tabular-nums text-muted">{inr(item.lump_sum_amount_inr)}</td>
												<td class="whitespace-nowrap">
													<span class="badge-pill {item.action_status === 'DEPLOY_NOW' ? 'border-brand/40 bg-brand/10 text-brand-soft' : item.action_status === 'STAGE_CAUTIOUSLY' ? 'border-amber/40 bg-amber/10 text-amber' : 'border-azure/40 bg-azure/10 text-azure'}">
														{labelize(item.action_status)}
													</span>
												</td>
												<td class="max-w-xs text-[12px] leading-relaxed text-muted">{item.rationale}</td>
												<td class="no-print">
													{#if aid}
														<div class="flex flex-wrap gap-1.5">
															<a class="btn !px-2.5 !py-1 text-[11px]" href="/explorer/{aid}">Details</a>
															<a class="btn !px-2.5 !py-1 text-[11px]" href="/research?asset={aid}">Research</a>
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
