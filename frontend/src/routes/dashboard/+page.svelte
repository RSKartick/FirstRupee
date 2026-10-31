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
					<span class="text-[11px] font-semibold uppercase tracking-[0.14em] text-brand-soft">Live Indian Market Benchmarks (NSE / BSE / AMFI)</span>
					<span class="text-[11px] text-muted">Source: {benchmarks[0].source} (as of {dateLabel(benchmarks[0].as_of)})</span>
				</div>
				<div class="mt-2.5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
					{#each benchmarks as b (b.symbol)}
						<div class="rounded-lg border border-line/60 bg-canvas/70 px-3 py-2">
							<div class="flex items-center justify-between gap-1">
								<span class="text-[12px] font-medium">{b.label}</span>
								<span class="text-[11px] tabular-nums {b.day_change_pct >= 0 ? 'text-brand-soft' : 'text-danger'}">{signedPct(b.day_change_pct, 2)}</span>
							</div>
							<div class="mt-1 flex items-baseline justify-between gap-2">
								<span class="text-sm font-semibold tabular-nums">{Number(b.price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
								<span class="text-[10px] text-muted">1Y: {signedPct(b.trailing_1y_pct, 1)}</span>
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/if}

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

				<div class="space-y-6">
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

					<div>
						<h3 class="text-[12px] font-semibold uppercase tracking-wider text-muted">
							1. Numerical Monthly Surplus Allocation ({inr(rec.monthly_plan.monthly_surplus_inr)}/month available after {inr(rec.monthly_plan.committed_outflow_inr)} expenses &amp; EMIs)
						</h3>
						<div class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
							<div class="rounded-xl border border-line bg-raised/40 p-4">
								<p class="text-[11px] uppercase text-muted">Emergency Reserve Top-Up</p>
								<p class="mt-1 text-xl font-semibold tabular-nums text-amber">{inr(rec.monthly_plan.emergency_topup_inr)}<span class="text-xs font-normal text-muted">/mo</span></p>
								<p class="mt-1 text-[11px] text-muted">{pct(rec.monthly_plan.emergency_topup_pct, 1)} of monthly surplus</p>
							</div>
							<div class="rounded-xl border border-line bg-raised/40 p-4">
								<p class="text-[11px] uppercase text-muted">Goal Reserve Funding</p>
								<p class="mt-1 text-xl font-semibold tabular-nums text-azure">{inr(rec.monthly_plan.goal_reserve_inr)}<span class="text-xs font-normal text-muted">/mo</span></p>
								<p class="mt-1 text-[11px] text-muted">{pct(rec.monthly_plan.goal_reserve_pct, 1)} of monthly surplus</p>
							</div>
							<div class="rounded-xl border border-line bg-raised/40 p-4">
								<p class="text-[11px] uppercase text-muted">High-Cost Debt Prepayment</p>
								<p class="mt-1 text-xl font-semibold tabular-nums">{inr(rec.monthly_plan.debt_prepayment_inr)}<span class="text-xs font-normal text-muted">/mo</span></p>
								<p class="mt-1 text-[11px] text-muted">{pct(rec.monthly_plan.debt_prepayment_pct, 1)} of monthly surplus</p>
							</div>
							<div class="rounded-xl border border-brand/40 bg-brand/10 p-4">
								<p class="text-[11px] uppercase text-brand-soft">Recommended Market SIP</p>
								<p class="mt-1 text-xl font-semibold tabular-nums text-brand-soft">{inr(rec.monthly_plan.recommended_market_deployment_inr)}<span class="text-xs font-normal text-muted">/mo</span></p>
								<p class="mt-1 text-[11px] text-muted">{pct(rec.monthly_plan.recommended_market_deployment_pct, 1)} of surplus (cap {inr(rec.monthly_plan.investable_capacity_inr)})</p>
							</div>
						</div>
					</div>

					<div>
						<h3 class="text-[12px] font-semibold uppercase tracking-wider text-muted">
							{rec.readiness_status === 'NOT_READY'
								? '2. Safe Reserve-Parking Split for Emergency & Goal Savings (Rs 0 Market Risk Exposure)'
								: '2. Numerical Instrument-by-Instrument Portfolio Plan (Real NSE & AMFI Instruments)'}
						</h3>
						<div class="table-wrap mt-3">
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
												<p class="text-[11px] text-muted">{item.symbol} · {labelize(item.asset_type)}</p>
											</td>
											<td class="text-[12px]">{item.role}</td>
											<td class="whitespace-nowrap font-semibold tabular-nums text-brand-soft">{item.allocation_pct}%</td>
											<td class="whitespace-nowrap font-semibold tabular-nums">{inr(item.monthly_amount_inr)}/mo</td>
											<td class="whitespace-nowrap tabular-nums text-muted">{inr(item.lump_sum_amount_inr)}</td>
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
					</div>

					<div class="rounded-xl border border-line bg-raised/30 p-4">
						<h3 class="text-[12px] font-semibold uppercase tracking-wider text-muted">3. Lump-Sum Liquid Savings Breakdown ({inr(rec.lump_sum_plan.liquid_savings_inr)} total liquid savings)</h3>
						<div class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-[13px]">
							<div><span class="text-muted">Locked for Emergency:</span> <strong class="tabular-nums">{inr(rec.lump_sum_plan.emergency_locked_inr)}</strong></div>
							<div><span class="text-muted">Locked for Goal:</span> <strong class="tabular-nums">{inr(rec.lump_sum_plan.goal_locked_inr)}</strong></div>
							<div><span class="text-muted">Immediate Reserve Boost:</span> <strong class="tabular-nums">{inr(rec.lump_sum_plan.immediate_reserve_boost_inr)}</strong></div>
							<div>
								<span class="text-muted">Staged Market Capital:</span>
								<strong class="tabular-nums text-brand-soft">{inr(rec.lump_sum_plan.staged_market_deployment_inr)}</strong>
								{#if rec.lump_sum_plan.recommended_tranches_months > 0}
									<span class="text-[11px] text-muted">({rec.lump_sum_plan.recommended_tranches_months} monthly tranches of {inr(rec.lump_sum_plan.monthly_tranche_inr)})</span>
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
