<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { Scheme, SchemeCalculation, SchemeEvaluation } from '$lib/api/types';
	import { session } from '$lib/stores/session.svelte';
	import { inr, pct } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import {
		Calculator,
		Check,
		ChevronDown,
		ChevronUp,
		HelpCircle,
		Landmark,
		Layers,
		Scale,
		ShieldCheck,
		Sparkles,
		TrendingUp
	} from 'lucide-svelte';

	let schemes = $state<Scheme[]>([]);
	let evaluations = $state<SchemeEvaluation[]>([]);
	let loading = $state(true);
	let error = $state('');

	// Category filter
	let activeCategory = $state('ALL');

	const CATEGORIES = [
		{ id: 'ALL', label: 'All Schemes' },
		{ id: 'TAX_SAVING_AND_WEALTH', label: 'Tax Saving (80C)' },
		{ id: 'RETIREMENT', label: 'Retirement & Pension' },
		{ id: 'CHILD_FUTURE', label: 'Child Future (SSY)' },
		{ id: 'SENIOR_CITIZENS', label: 'Senior Citizens (8.2%)' },
		{ id: 'REGULAR_INCOME', label: 'Monthly Income' },
		{ id: 'WOMEN_SAVINGS', label: 'Women Savings' },
		{ id: 'MACRO_AND_GOLD', label: 'SGB & Gold' }
	];

	// Interactive Calculator State
	let selectedSchemeId = $state('ppf');
	let depositMode = $state<'monthly' | 'lump_sum'>('monthly');
	let monthlyAmount = $state(10000);
	let lumpSumAmount = $state(100000);
	let horizonYears = $state(15);
	let taxBracketPct = $state(30);

	let calcResult = $state<SchemeCalculation | null>(null);
	let calculating = $state(false);
	let showSchedule = $state(false);

	// Comparison Modal State
	let compareScheme1Id = $state('ppf');
	let compareScheme2Id = $state('nps_tier1');
	let showComparison = $state(false);

	const selectedScheme = $derived(schemes.find((s) => s.id === selectedSchemeId) ?? schemes[0]);
	const compareScheme1 = $derived(schemes.find((s) => s.id === compareScheme1Id) ?? schemes[0]);
	const compareScheme2 = $derived(schemes.find((s) => s.id === compareScheme2Id) ?? schemes[1]);
	const activeProfile = $derived(session.profiles.find((p) => p.id === session.activeProfileId) ?? null);

	const filteredSchemes = $derived(
		activeCategory === 'ALL'
			? schemes
			: schemes.filter((s) => s.category === activeCategory)
	);

	onMount(async () => {
		await loadData();
	});

	$effect(() => {
		const pid = session.activeProfileId;
		if (pid) {
			void loadEvaluations(pid);
		} else {
			evaluations = [];
		}
	});

	async function loadData() {
		loading = true;
		error = '';
		try {
			const res = await api.listSchemes();
			schemes = res.schemes;
			if (session.activeProfileId) {
				await loadEvaluations(session.activeProfileId);
			}
			await runCalculation();
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load Indian schemes catalog.';
		} finally {
			loading = false;
		}
	}

	async function loadEvaluations(profileId: number) {
		try {
			const res = await api.evaluateSchemesForProfile(profileId);
			evaluations = res.evaluations;
		} catch {
			evaluations = [];
		}
	}

	async function runCalculation() {
		if (!selectedSchemeId) return;
		calculating = true;
		try {
			const res = await api.calculateScheme({
				scheme_id: selectedSchemeId,
				monthly_deposit: depositMode === 'monthly' ? monthlyAmount : 0,
				lump_sum: depositMode === 'lump_sum' ? lumpSumAmount : 0,
				horizon_years: horizonYears,
				tax_bracket_pct: taxBracketPct
			});
			calcResult = res.calculation;
		} catch {
			// keep previous result or ignore
		} finally {
			calculating = false;
		}
	}

	function selectSchemeForCalculator(schemeId: string) {
		selectedSchemeId = schemeId;
		const s = schemes.find((item) => item.id === schemeId);
		if (s) {
			horizonYears = s.lock_in_years > 0 ? s.lock_in_years : 15;
		}
		void runCalculation();
		const el = document.getElementById('scheme-calculator');
		if (el) {
			el.scrollIntoView({ behavior: 'smooth' });
		}
	}
</script>

<svelte:head>
	<title>Indian Investment Schemes Hub - FirstRupee</title>
</svelte:head>

<div class="space-y-6">
	<!-- Page Header Banner -->
	<section class="card grain">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<div class="flex items-center gap-2">
					<span class="rounded border border-brand/40 bg-brand/10 px-2 py-0.5 text-[10px] font-mono font-semibold uppercase text-brand-soft">
						Statutory Engine
					</span>
					<span class="text-[11px] font-mono text-muted">Ministry of Finance / RBI / PFRDA / India Post</span>
				</div>
				<h1 class="mt-2 text-2xl font-semibold tracking-tight text-ink">
					Indian Sovereign &amp; Statutory Schemes Hub
				</h1>
				<p class="muted mt-2 max-w-3xl text-[13.5px] leading-relaxed">
					Sovereign-backed capital preservation, guaranteed compounding yields, and Section 80C / 80CCD tax benefits.
					Explore official rules, verify eligibility, run custom maturity simulations, and discover how statutory schemes anchor your FirstRupee asset allocation blueprint.
				</p>
			</div>
			<div class="flex flex-wrap gap-2 no-print">
				<button class="btn btn-ghost" onclick={() => (showComparison = !showComparison)}>
					<Scale size={15} />{showComparison ? 'Hide Comparison' : 'Compare Schemes'}
				</button>
				<a class="btn btn-primary" href="#scheme-calculator">
					<Calculator size={15} />Open Calculator
				</a>
			</div>
		</div>
	</section>

	{#if error}
		<Notice tone="danger" title="Connection Error">{error}</Notice>
	{/if}

	{#if loading}
		<p class="muted font-mono text-sm" role="status">&gt; Loading Indian statutory schemes catalog...</p>
	{:else}
		<!-- SECTION 1: PERSONALIZED SCHEME FIT RADAR (For Active Profile) -->
		{#if evaluations.length > 0}
			<section class="card rounded-lg p-5">
				<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-4">
					<div class="flex items-center gap-2.5">
						<div class="rounded border border-brand/40 bg-brand/10 p-2 text-brand-soft">
							<Sparkles size={18} />
						</div>
						<div>
							<h2 class="text-base font-semibold text-ink">
								Personalised Scheme Fit Analysis for {activeProfile?.display_name ?? 'Your Profile'}
							</h2>
							<p class="text-[12px] text-muted">
								Evaluated from your goal horizon, risk capacity, and monthly surplus.
							</p>
						</div>
					</div>
					<span class="text-[11px] font-mono text-brand-soft font-semibold">
						{evaluations.filter((e) => e.fit_tier === 'HIGH_CONVICTION').length} High-Conviction Matches
					</span>
				</div>

				<div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
					{#each evaluations.slice(0, 3) as item (item.scheme.id)}
						<div class="rounded border border-line bg-canvas p-4 flex flex-col justify-between hover:border-brand/40 transition-colors">
							<div>
								<div class="flex items-start justify-between gap-2">
									<div>
										<span class="text-[10px] font-mono text-dim uppercase">{item.scheme.authority}</span>
										<h3 class="text-sm font-semibold text-ink mt-0.5">{item.scheme.name}</h3>
									</div>
									<span class="rounded border px-2 py-0.5 text-[10px] font-mono font-bold {item.fit_tier === 'HIGH_CONVICTION' ? 'border-brand/40 bg-brand/10 text-brand-soft' : 'border-line bg-raised text-muted'}">
										{item.fit_score}% FIT
									</span>
								</div>

								<div class="mt-3 flex items-baseline justify-between rounded bg-raised/40 p-2 border border-line/60">
									<span class="text-[11px] font-mono text-muted">Current Yield:</span>
									<span class="font-mono text-sm font-bold text-brand-soft">{item.scheme.interest_rate_pct}% p.a.</span>
								</div>

								<div class="mt-2.5 space-y-1.5 text-[12px]">
									{#each item.fit_reasons as reason, rIdx (rIdx)}
										<div class="flex items-start gap-1.5 text-ink/90">
											<span class="text-brand-soft font-mono font-bold">✓</span>
											<span>{reason}</span>
										</div>
									{/each}
									{#each item.cautions as caution, cIdx (cIdx)}
										<div class="flex items-start gap-1.5 text-muted">
											<span class="text-amber font-mono font-bold">!</span>
											<span>{caution}</span>
										</div>
									{/each}
								</div>
							</div>

							<div class="mt-4 pt-3 border-t border-line flex items-center justify-between">
								<span class="text-[11px] font-mono text-dim">
									Suggested: <strong class="text-ink">{item.suggested_monthly_inr > 0 ? inr(item.suggested_monthly_inr) + '/mo' : 'Discretionary'}</strong>
								</span>
								<button
									class="btn btn-ghost !px-2.5 !py-1 text-[11px]"
									onclick={() => selectSchemeForCalculator(item.scheme.id)}
								>
									Simulate
								</button>
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- SECTION 2: INTERACTIVE SCHEME MATURITY CALCULATOR -->
		<section id="scheme-calculator" class="card rounded-lg p-5 lg:p-6 space-y-5">
			<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-4">
				<div class="flex items-center gap-2.5">
					<div class="rounded border border-line bg-raised p-2 text-brand-soft">
						<Calculator size={18} />
					</div>
					<div>
						<h2 class="text-base font-semibold text-ink">
							Interactive Scheme Growth &amp; Tax Simulator
						</h2>
						<p class="text-[12px] text-muted">
							Simulate monthly deposits or lump sums with authentic compounding and statutory tax deduction math.
						</p>
					</div>
				</div>
				{#if selectedScheme}
					<span class="px-2.5 py-1 rounded bg-raised border border-line text-[11px] font-mono text-ink">
						Active: <strong class="text-brand-soft">{selectedScheme.short_name}</strong> ({selectedScheme.interest_rate_pct}% p.a.)
					</span>
				{/if}
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
				<!-- Left Controls -->
				<div class="lg:col-span-5 space-y-4">
					<div>
						<label for="select-calc-scheme" class="block text-[11px] font-mono text-dim uppercase">Select Government Scheme</label>
						<select
							id="select-calc-scheme"
							class="field-input mt-1 w-full"
							bind:value={selectedSchemeId}
							onchange={() => {
								const s = schemes.find((x) => x.id === selectedSchemeId);
								if (s) horizonYears = s.lock_in_years > 0 ? s.lock_in_years : 15;
								void runCalculation();
							}}
						>
							{#each schemes as s (s.id)}
								<option value={s.id}>{s.name} ({s.interest_rate_pct}% p.a.)</option>
							{/each}
						</select>
					</div>

					<div>
						<span class="block text-[11px] font-mono text-dim uppercase">Deposit Mode</span>
						<div class="mt-1 flex rounded border border-line bg-canvas p-0.5">
							<button
								type="button"
								class="flex-1 py-1.5 text-xs font-medium rounded transition-colors {depositMode === 'monthly' ? 'bg-raised text-ink border border-line font-semibold' : 'text-muted hover:text-ink'}"
								onclick={() => {
									depositMode = 'monthly';
									void runCalculation();
								}}
							>
								Monthly Contribution
							</button>
							<button
								type="button"
								class="flex-1 py-1.5 text-xs font-medium rounded transition-colors {depositMode === 'lump_sum' ? 'bg-raised text-ink border border-line font-semibold' : 'text-muted hover:text-ink'}"
								onclick={() => {
									depositMode = 'lump_sum';
									void runCalculation();
								}}
							>
								One-Time Lump Sum
							</button>
						</div>
					</div>

					{#if depositMode === 'monthly'}
						<div>
							<div class="flex justify-between text-xs">
								<label for="range-monthly-amount" class="font-mono text-dim uppercase text-[11px]">Monthly Amount</label>
								<span class="font-mono font-bold text-ink">{inr(monthlyAmount)}/mo</span>
							</div>
							<input
								id="range-monthly-amount"
								type="range"
								min="500"
								max="125000"
								step="500"
								bind:value={monthlyAmount}
								oninput={runCalculation}
								class="mt-2 w-full accent-emerald-500"
							/>
							<div class="mt-1 flex justify-between text-[10px] font-mono text-muted">
								<span>₹500</span>
								<span>₹25,000</span>
								<span>₹1,25,000</span>
							</div>
						</div>
					{:else}
						<div>
							<div class="flex justify-between text-xs">
								<label for="range-lump-sum" class="font-mono text-dim uppercase text-[11px]">Lump Sum Capital</label>
								<span class="font-mono font-bold text-ink">{inr(lumpSumAmount)}</span>
							</div>
							<input
								id="range-lump-sum"
								type="range"
								min="5000"
								max="1500000"
								step="5000"
								bind:value={lumpSumAmount}
								oninput={runCalculation}
								class="mt-2 w-full accent-emerald-500"
							/>
							<div class="mt-1 flex justify-between text-[10px] font-mono text-muted">
								<span>₹5,000</span>
								<span>₹5,00,000</span>
								<span>₹15,00,000</span>
							</div>
						</div>
					{/if}

					<div>
						<div class="flex justify-between text-xs">
							<label for="range-horizon-years" class="font-mono text-dim uppercase text-[11px]">Investment Horizon</label>
							<span class="font-mono font-bold text-ink">{horizonYears} Years</span>
						</div>
						<input
							id="range-horizon-years"
							type="range"
							min="1"
							max="30"
							step="1"
							bind:value={horizonYears}
							oninput={runCalculation}
							class="mt-2 w-full accent-emerald-500"
						/>
						<div class="mt-1 flex justify-between text-[10px] font-mono text-muted">
							<span>1 Year</span>
							<span>15 Years</span>
							<span>30 Years</span>
						</div>
					</div>

					<div>
						<div class="flex justify-between text-xs">
							<label for="range-tax-bracket" class="font-mono text-dim uppercase text-[11px]">Income Tax Bracket (for 80C calculation)</label>
							<span class="font-mono font-bold text-ink">{taxBracketPct}%</span>
						</div>
						<input
							id="range-tax-bracket"
							type="range"
							min="0"
							max="35"
							step="5"
							bind:value={taxBracketPct}
							oninput={runCalculation}
							class="mt-2 w-full accent-emerald-500"
						/>
						<div class="mt-1 flex justify-between text-[10px] font-mono text-muted">
							<span>0% (Exempt)</span>
							<span>20%</span>
							<span>30% + Surcharge</span>
						</div>
					</div>
				</div>

				<!-- Right Results Card -->
				<div class="lg:col-span-7 flex flex-col justify-between rounded-lg border border-line bg-canvas p-5">
					{#if calcResult}
						<div class="space-y-4">
							<div class="flex items-center justify-between border-b border-line pb-3">
								<div>
									<span class="text-[10px] font-mono text-dim uppercase">Projected Maturity Corpus ({horizonYears} Years)</span>
									<p class="font-mono text-3xl font-bold text-brand-soft tracking-tight mt-0.5">
										{inr(calcResult.gross_maturity_amount)}
									</p>
								</div>
								<div class="text-right">
									<span class="text-[10px] font-mono text-dim uppercase">Annualized Yield</span>
									<p class="font-mono text-lg font-bold text-ink">{calcResult.effective_cagr_pct}% p.a.</p>
								</div>
							</div>

							<!-- 3 Core Breakdown Metrics -->
							<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
								<div class="rounded bg-raised/50 border border-line p-3">
									<span class="text-[11px] font-mono text-dim">Total Principal</span>
									<p class="font-mono text-base font-bold text-ink mt-0.5">{inr(calcResult.total_principal_deposited)}</p>
									<span class="text-[10px] text-muted">Your capital contribution</span>
								</div>
								<div class="rounded bg-raised/50 border border-line p-3">
									<span class="text-[11px] font-mono text-dim">Total Interest Earned</span>
									<p class="font-mono text-base font-bold text-brand-soft mt-0.5">+{inr(calcResult.total_interest_earned)}</p>
									<span class="text-[10px] text-muted">Guaranteed compounding</span>
								</div>
								<div class="rounded bg-raised/50 border border-line p-3">
									<span class="text-[11px] font-mono text-dim">Est. Tax Saved</span>
									<p class="font-mono text-base font-bold text-amber mt-0.5">{inr(calcResult.total_tax_saved_over_horizon)}</p>
									<span class="text-[10px] text-muted">via {selectedScheme.tax_section.split(' ')[0]}</span>
								</div>
							</div>

							<!-- Fiduciary Blueprint Integration Callout -->
							<div class="rounded border border-line/80 bg-raised/30 p-3.5 space-y-1.5 text-[12.5px]">
								<div class="flex items-center gap-1.5 font-medium text-ink">
									<ShieldCheck size={15} class="text-brand-soft shrink-0" />
									<span>FirstRupee Asset Allocation Role</span>
								</div>
								<p class="text-muted leading-relaxed">
									{selectedScheme.fiduciary_role}
								</p>
								<div class="pt-1 flex flex-wrap gap-2 text-[11px] font-mono text-dim">
									<span class="rounded bg-canvas px-2 py-0.5 border border-line">
										Tax Treatment: <strong class="text-ink">{selectedScheme.tax_treatment}</strong>
									</span>
									<span class="rounded bg-canvas px-2 py-0.5 border border-line">
										Lock-in: <strong class="text-ink">{selectedScheme.lock_in_description}</strong>
									</span>
									<span class="rounded bg-canvas px-2 py-0.5 border border-line">
										Sovereign Guarantee: <strong class="text-brand-soft">{selectedScheme.sovereign_backed ? 'YES' : 'PFRDA'}</strong>
									</span>
								</div>
							</div>
						</div>

						<!-- Year-by-Year Schedule Toggle -->
						<div class="mt-4 pt-3 border-t border-line">
							<button
								type="button"
								class="flex items-center justify-between w-full text-xs font-mono text-dim hover:text-ink transition-colors"
								onclick={() => (showSchedule = !showSchedule)}
							>
								<span>{showSchedule ? 'Hide' : 'Inspect'} Year-by-Year Amortization Schedule ({calcResult.schedule.length} Years)</span>
								{#if showSchedule}
									<ChevronUp size={14} />
								{:else}
									<ChevronDown size={14} />
								{/if}
							</button>

							{#if showSchedule}
								<div class="table-wrap mt-3 max-h-60 overflow-y-auto">
									<table class="data-table !text-[11px]">
										<thead>
											<tr>
												<th>Year</th>
												<th>Opening Balance</th>
												<th>Deposit</th>
												<th>Interest Earned</th>
												<th>Closing Balance</th>
											</tr>
										</thead>
										<tbody>
											{#each calcResult.schedule as row (row.year)}
												<tr>
													<td class="font-mono font-bold text-ink">Yr {row.year}</td>
													<td class="font-mono text-muted">{inr(row.opening_balance)}</td>
													<td class="font-mono text-dim">+{inr(row.deposited_this_year)}</td>
													<td class="font-mono text-brand-soft">+{inr(row.interest_this_year)}</td>
													<td class="font-mono font-bold text-ink">{inr(row.closing_balance)}</td>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</section>

		<!-- SECTION 3: HEAD-TO-HEAD SCHEME COMPARISON TOOL -->
		{#if showComparison}
			<section class="card rounded-lg p-5 space-y-4">
				<div class="flex items-center justify-between border-b border-line pb-3">
					<div class="flex items-center gap-2">
						<Scale size={16} class="text-brand-soft" />
						<h2 class="text-sm font-semibold text-ink uppercase tracking-wider font-mono">
							Head-to-Head Statutory Scheme Comparison
						</h2>
					</div>
					<button class="btn btn-ghost !px-2 !py-1 text-xs text-muted" onclick={() => (showComparison = false)}>
						Close
					</button>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label for="compare-scheme-1" class="block text-[11px] font-mono text-dim uppercase">Scheme 1</label>
						<select id="compare-scheme-1" class="field-input mt-1 w-full" bind:value={compareScheme1Id}>
							{#each schemes as s (s.id)}
								<option value={s.id}>{s.name}</option>
							{/each}
						</select>
					</div>
					<div>
						<label for="compare-scheme-2" class="block text-[11px] font-mono text-dim uppercase">Scheme 2</label>
						<select id="compare-scheme-2" class="field-input mt-1 w-full" bind:value={compareScheme2Id}>
							{#each schemes as s (s.id)}
								<option value={s.id}>{s.name}</option>
							{/each}
						</select>
					</div>
				</div>

				<div class="table-wrap mt-2">
					<table class="data-table !text-[12px]">
						<thead>
							<tr>
								<th>Parameter</th>
								<th class="text-ink font-bold">{compareScheme1.short_name}</th>
								<th class="text-ink font-bold">{compareScheme2.short_name}</th>
							</tr>
						</thead>
						<tbody>
							<tr>
								<td class="font-mono text-dim">Interest Rate</td>
								<td class="font-mono font-bold text-brand-soft">{compareScheme1.interest_rate_pct}% p.a.</td>
								<td class="font-mono font-bold text-brand-soft">{compareScheme2.interest_rate_pct}% p.a.</td>
							</tr>
							<tr>
								<td class="font-mono text-dim">Authority</td>
								<td>{compareScheme1.authority}</td>
								<td>{compareScheme2.authority}</td>
							</tr>
							<tr>
								<td class="font-mono text-dim">Tax Treatment</td>
								<td>
									<span class="rounded bg-raised px-2 py-0.5 font-mono text-xs font-semibold text-ink">
										{compareScheme1.tax_treatment}
									</span>
								</td>
								<td>
									<span class="rounded bg-raised px-2 py-0.5 font-mono text-xs font-semibold text-ink">
										{compareScheme2.tax_treatment}
									</span>
								</td>
							</tr>
							<tr>
								<td class="font-mono text-dim">Tax Deduction Section</td>
								<td class="font-mono text-xs">{compareScheme1.tax_section}</td>
								<td class="font-mono text-xs">{compareScheme2.tax_section}</td>
							</tr>
							<tr>
								<td class="font-mono text-dim">Tenure / Lock-in</td>
								<td>{compareScheme1.lock_in_description}</td>
								<td>{compareScheme2.lock_in_description}</td>
							</tr>
							<tr>
								<td class="font-mono text-dim">Annual Deposit Limit</td>
								<td>{compareScheme1.max_investment_annual ? inr(compareScheme1.max_investment_annual) : 'No upper ceiling'}</td>
								<td>{compareScheme2.max_investment_annual ? inr(compareScheme2.max_investment_annual) : 'No upper ceiling'}</td>
							</tr>
							<tr>
								<td class="font-mono text-dim">Sovereign Guarantee</td>
								<td class="text-brand-soft font-semibold">{compareScheme1.sovereign_backed ? 'Sovereign (100% Capital Safety)' : 'PFRDA Regulated Trust'}</td>
								<td class="text-brand-soft font-semibold">{compareScheme2.sovereign_backed ? 'Sovereign (100% Capital Safety)' : 'PFRDA Regulated Trust'}</td>
							</tr>
							<tr>
								<td class="font-mono text-dim">Premature Liquidity</td>
								<td class="text-muted leading-relaxed">{compareScheme1.liquidity_notes}</td>
								<td class="text-muted leading-relaxed">{compareScheme2.liquidity_notes}</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>
		{/if}

		<!-- SECTION 4: FULL STATUTORY SCHEMES CATALOG & FILTERS -->
		<section class="space-y-4">
			<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-1">
				<div>
					<h2 class="text-base font-semibold text-ink">
						Indian Government Savings &amp; Investment Schemes Directory
					</h2>
					<p class="text-[12px] text-muted">
						Verified official data across small-savings instruments, pensions, and gold bonds.
					</p>
				</div>
				<span class="text-[11px] font-mono text-dim">
					Showing {filteredSchemes.length} of {schemes.length} Schemes
				</span>
			</div>

			<!-- Filter Pills -->
			<div class="scroll-x flex items-center gap-1.5 overflow-x-auto pb-1">
				{#each CATEGORIES as cat (cat.id)}
					<button
						type="button"
						class="whitespace-nowrap rounded px-3 py-1.5 text-xs font-medium transition-colors {activeCategory === cat.id ? 'bg-raised text-ink border border-line font-semibold' : 'text-muted hover:bg-raised/40 hover:text-ink'}"
						onclick={() => (activeCategory = cat.id)}
					>
						{cat.label}
					</button>
				{/each}
			</div>

			<!-- Scheme Cards Grid -->
			<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each filteredSchemes as scheme (scheme.id)}
					<div class="card rounded-lg p-5 flex flex-col justify-between hover:border-brand/40 transition-colors">
						<div>
							<div class="flex items-start justify-between gap-2">
								<div>
									<span class="text-[10px] font-mono text-dim uppercase tracking-wider">{scheme.authority}</span>
									<h3 class="text-base font-semibold text-ink mt-0.5">{scheme.name}</h3>
								</div>
								<span class="rounded bg-raised border border-line px-2 py-0.5 font-mono text-[11px] font-bold text-brand-soft">
									{scheme.tax_treatment}
								</span>
							</div>

							<!-- Big Rate Banner -->
							<div class="mt-4 rounded bg-canvas border border-line p-3 flex items-baseline justify-between">
								<div>
									<span class="text-[10px] font-mono text-dim uppercase">Current Official Rate</span>
									<p class="text-xl font-bold font-mono text-ink mt-0.5">{scheme.interest_rate_pct}% <span class="text-xs font-normal text-dim">p.a.</span></p>
								</div>
								<div class="text-right">
									<span class="text-[10px] font-mono text-dim uppercase">Tenure</span>
									<p class="text-xs font-mono font-medium text-muted mt-0.5">{scheme.lock_in_years > 0 ? scheme.lock_in_years + ' Years' : 'Retirement'}</p>
								</div>
							</div>

							<div class="mt-3.5 space-y-2 text-[12px]">
								<div>
									<span class="text-dim font-mono text-[11px]">Tax Benefit:</span>
									<p class="text-ink/90 font-medium">{scheme.tax_section}</p>
								</div>
								<div>
									<span class="text-dim font-mono text-[11px]">Deposit Limits:</span>
									<p class="text-muted">
										Min: {inr(scheme.min_investment)} / Yr {scheme.max_investment_annual ? `· Max: ${inr(scheme.max_investment_annual)} / Yr` : '· No upper ceiling'}
									</p>
								</div>
								<div>
									<span class="text-dim font-mono text-[11px]">Target Demographic:</span>
									<p class="text-muted leading-relaxed">{scheme.target_demographic}</p>
								</div>
							</div>

							<!-- Key Pro Badge -->
							{#if scheme.pros.length > 0}
								<div class="mt-3 pt-2.5 border-t border-line text-[11.5px] text-ink/80 flex items-start gap-1.5">
									<Check size={13} class="text-brand-soft shrink-0 mt-0.5" />
									<span>{scheme.pros[0]}</span>
								</div>
							{/if}
						</div>

						<div class="mt-4 pt-3 border-t border-line flex items-center justify-between no-print">
							<span class="text-[11px] font-mono text-dim">
								{scheme.sovereign_backed ? 'Sovereign Guarantee' : 'PFRDA Trust'}
							</span>
							<button
								type="button"
								class="btn btn-primary !px-3 !py-1 text-xs font-semibold"
								onclick={() => selectSchemeForCalculator(scheme.id)}
							>
								Simulate Growth
							</button>
						</div>
					</div>
				{/each}
			</div>
		</section>
	{/if}
</div>
