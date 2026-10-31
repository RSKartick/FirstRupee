<script lang="ts">
	import { onMount } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, ApiError } from '$lib/api/client';
	import type { DebtOut, ProfileOut } from '$lib/api/types';
	import { loadProfiles, session } from '$lib/stores/session.svelte';
	import {
		EMPTY_DRAFT,
		STEPS,
		stepHasErrors,
		toPayload,
		validateDraft,
		type Draft,
		type DebtDraft
	} from '$lib/onboarding/validation';
	import { inr, labelize } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import { ChevronLeft, ChevronRight, Plus, Save, Trash2 } from 'lucide-svelte';

	let draft = $state<Draft>(structuredClone(EMPTY_DRAFT));
	let step = $state(0);
	let profileId = $state<number | null>(null);
	let loading = $state(true);
	let saving = $state(false);
	let dirty = $state(false);
	let showErrors = $state(false);
	let message = $state('');
	let failure = $state('');
	let fieldFailures = $state<{ field: string; message: string }[]>([]);

	const todayIso = (() => {
		const now = new Date();
		return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
	})();
	const errors = $derived(validateDraft(draft, todayIso));
	const errorCount = $derived(Object.keys(errors).length);

	const DEBT_TYPES = ['HOME_LOAN', 'PERSONAL_LOAN', 'CAR_LOAN', 'CREDIT_CARD', 'EDUCATION_LOAN', 'OTHER'];

	function fromProfile(p: ProfileOut): Draft {
		const q = p.questionnaire;
		return {
			...structuredClone(EMPTY_DRAFT),
			displayName: p.display_name,
			ageRange: p.age_range,
			employmentStatus: p.employment_status,
			monthlyIncome: p.monthly_income,
			essentialExpenses: p.essential_expenses,
			nonessentialExpenses: p.nonessential_expenses,
			monthlyEmi: p.monthly_emi,
			otherCommitments: p.other_commitments,
			totalSavings: p.total_savings,
			liquidSavings: p.liquid_savings,
			emergencyReserves: p.emergency_reserves,
			goalReservedAmount: p.goal_reserved_amount,
			currentInvestments: p.current_investments,
			existingLiabilities: p.existing_liabilities,
			designatedMonthly: p.monthly_investment_designated,
			debts: p.debts.map((d: DebtOut) => ({
				debtType: d.debt_type,
				outstanding: d.outstanding_amount,
				rate: d.interest_rate_pct,
				emi: d.emi_amount,
				remainingMonths: String(d.remaining_months),
				overdue: d.is_overdue
			})),
			investmentExperience: p.investment_experience,
			goalName: p.goal_name ?? '',
			goalCategory: p.goal_category ?? '',
			goalAmount: p.goal_amount ?? '',
			goalDeadline: p.goal_deadline ?? '',
			goalImportance: p.goal_importance ?? '',
			goalLiquidity: p.goal_liquidity ?? '',
			drawdownReaction: q?.drawdown_reaction ?? '',
			preferredHorizon: q?.preferred_horizon ?? '',
			gainsReaction: q?.gains_reaction ?? '',
			lossImpactOnExpenses: q?.loss_impact_on_expenses ?? '',
			incomeStability: q?.income_stability ?? ''
		};
	}

	onMount(async () => {
		const params = page.url.searchParams;
		try {
			const requested = Number(params.get('profile'));
			const targetId = params.has('new') ? null : Number.isInteger(requested) && requested > 0 ? requested : session.activeProfileId;
			if (targetId) {
				const res = await api.getProfile(targetId);
				profileId = res.profile.id;
				draft = fromProfile(res.profile);
			}
		} catch (err) {
			failure = err instanceof ApiError ? err.message : 'The profile could not be loaded.';
		} finally {
			loading = false;
			dirty = false;
		}
	});

	beforeNavigate((navigation) => {
		if (dirty && !saving && !window.confirm('You have unsaved changes. Leave this page and discard them?')) {
			navigation.cancel();
		}
	});

	function next() {
		showErrors = true;
		if (!stepHasErrors(step, errors)) {
			showErrors = false;
			step = Math.min(step + 1, STEPS.length - 1);
		}
	}

	function firstStepWithErrors(): number {
		return STEPS.findIndex((_, index) => stepHasErrors(index, errors));
	}

	function addDebt() {
		const row: DebtDraft = { debtType: 'PERSONAL_LOAN', outstanding: '', rate: '', emi: '', remainingMonths: '', overdue: false };
		draft.debts = [...draft.debts, row];
		dirty = true;
	}

	function removeDebt(index: number) {
		draft.debts = draft.debts.filter((_, i) => i !== index);
		dirty = true;
	}

	async function save() {
		showErrors = true;
		if (errorCount > 0) {
			step = firstStepWithErrors();
			return;
		}
		saving = true;
		failure = '';
		fieldFailures = [];
		try {
			const payload = toPayload(draft);
			const res = profileId
				? await api.updateProfile(profileId, payload)
				: await api.createProfile(payload);
			profileId = res.profile.id;
			dirty = false;
			message = profileId ? 'Profile saved. Readiness has been recomputed from your inputs.' : '';
			await loadProfiles(res.profile.id);
			await goto('/dashboard');
		} catch (err) {
			if (err instanceof ApiError) {
				failure = err.message;
				fieldFailures = err.errors;
			} else {
				failure = 'The profile could not be saved. Please try again.';
			}
		} finally {
			saving = false;
		}
	}

	const selectClass = 'field-input';
</script>

<svelte:head><title>Financial DNA assessment - FirstRupee</title></svelte:head>

<div class="mx-auto max-w-3xl space-y-6">
	<div>
		<p class="text-[12px] font-semibold uppercase tracking-[0.18em] text-brand-soft">Financial DNA</p>
		<h1 class="mt-2 text-2xl font-semibold tracking-tight">{profileId ? 'Edit your financial profile' : 'Build your financial profile'}</h1>
		<p class="muted mt-2">
			Each answer feeds a deterministic engine. Amounts are exact to the paisa. Every field is checked again on the server, so the
			results always reflect what you entered.
		</p>
	</div>

	{#if loading}
		<p class="muted" role="status">Loading your saved answers…</p>
	{:else}
		<nav aria-label="Assessment steps" class="flex flex-wrap gap-1.5">
			{#each STEPS as s, i (s.key)}
				<button
					class="rounded-md px-2.5 py-1 text-[12px] {i === step ? 'bg-brand/15 text-brand-soft' : 'text-muted hover:text-ink'}"
					aria-current={i === step ? 'step' : undefined}
					onclick={() => (step = i)}
				>
					{i + 1}. {s.title}
				</button>
			{/each}
		</nav>

		<div class="h-1.5 w-full overflow-hidden rounded-full bg-raised" aria-hidden="true">
			<div class="h-full rounded-full bg-brand transition-all" style="width:{((step + 1) / STEPS.length) * 100}%"></div>
		</div>

		<form class="space-y-5" oninput={() => (dirty = true)} onchange={() => (dirty = true)} onsubmit={(e) => e.preventDefault()}>
			<Card title={STEPS[step].title}>
				{#if step === 0}
					<div class="grid gap-4 sm:grid-cols-2">
						<div>
							<label class="field-label" for="displayName">Name or nickname</label>
							<input id="displayName" class="field-input" bind:value={draft.displayName} autocomplete="nickname" />
							{#if showErrors && errors.displayName}<p class="field-error">{errors.displayName}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="ageRange">Age range</label>
							<select id="ageRange" class={selectClass} bind:value={draft.ageRange}>
								<option value="">Select...</option>
								<option value="TEN_TO_TWENTY">18-20</option>
								<option value="TWENTY_TO_THIRTY">20-30</option>
								<option value="THIRTY_TO_FORTY">30-40</option>
								<option value="FORTY_TO_SIXTY">40-60</option>
								<option value="SIXTY_PLUS">60+</option>
							</select>
							{#if showErrors && errors.ageRange}<p class="field-error">{errors.ageRange}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="employmentStatus">Employment</label>
							<select id="employmentStatus" class={selectClass} bind:value={draft.employmentStatus}>
								<option value="">Select…</option>
								<option value="SALARIED">Salaried</option>
								<option value="SELF_EMPLOYED">Self-employed</option>
								<option value="BUSINESS">Business owner</option>
								<option value="STUDENT">Student</option>
								<option value="RETIRED">Retired</option>
								<option value="NOT_EMPLOYED">Not currently employed</option>
							</select>
							{#if showErrors && errors.employmentStatus}<p class="field-error">{errors.employmentStatus}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="monthlyIncome">Monthly take-home income (₹)</label>
							<input id="monthlyIncome" class="field-input" inputmode="decimal" bind:value={draft.monthlyIncome} placeholder="30000.00" />
							<p class="muted mt-1">After tax and deductions, as it arrives.</p>
							{#if showErrors && errors.monthlyIncome}<p class="field-error">{errors.monthlyIncome}</p>{/if}
						</div>
					</div>
				{/if}

				{#if step === 1}
					<div class="grid gap-4 sm:grid-cols-2">
						<div>
							<label class="field-label" for="essentialExpenses">Essential living expenses (₹/month)</label>
							<input id="essentialExpenses" class="field-input" inputmode="decimal" bind:value={draft.essentialExpenses} />
							<p class="muted mt-1">Rent, food, utilities, transport, medicines. Exclude EMIs; they are entered below.</p>
							{#if showErrors && errors.essentialExpenses}<p class="field-error">{errors.essentialExpenses}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="nonessentialExpenses">Non-essential expenses (₹/month)</label>
							<input id="nonessentialExpenses" class="field-input" inputmode="decimal" bind:value={draft.nonessentialExpenses} />
							{#if showErrors && errors.nonessentialExpenses}<p class="field-error">{errors.nonessentialExpenses}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="monthlyEmi">Monthly EMIs (₹/month)</label>
							<input id="monthlyEmi" class="field-input" inputmode="decimal" bind:value={draft.monthlyEmi} />
							<p class="muted mt-1">If you list loans in the next step, this must equal their EMIs added together.</p>
							{#if showErrors && errors.monthlyEmi}<p class="field-error">{errors.monthlyEmi}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="otherCommitments">Other recurring commitments (₹/month)</label>
							<input id="otherCommitments" class="field-input" inputmode="decimal" bind:value={draft.otherCommitments} />
							<p class="muted mt-1">Insurance premiums, family support, school fees.</p>
							{#if showErrors && errors.otherCommitments}<p class="field-error">{errors.otherCommitments}</p>{/if}
						</div>
					</div>
					{#if draft.monthlyIncome.trim() !== ''}
						<div class="mt-5">
							<Notice tone="info" title="Preview only: surplus after the four categories above">
								Your server-side monthly surplus is calculated on save. The readiness result on the dashboard is the authoritative figure.
							</Notice>
						</div>
					{/if}
				{/if}

				{#if step === 2}
					<div class="grid gap-4 sm:grid-cols-2">
						<div>
							<label class="field-label" for="totalSavings">Total savings (₹)</label>
							<input id="totalSavings" class="field-input" inputmode="decimal" bind:value={draft.totalSavings} />
							<p class="muted mt-1">Everything you hold across accounts and deposits.</p>
							{#if showErrors && errors.totalSavings}<p class="field-error">{errors.totalSavings}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="liquidSavings">Liquid savings (₹)</label>
							<input id="liquidSavings" class="field-input" inputmode="decimal" bind:value={draft.liquidSavings} />
							<p class="muted mt-1">Reachable within a day or two without penalty.</p>
							{#if showErrors && errors.liquidSavings}<p class="field-error">{errors.liquidSavings}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="emergencyReserves">Emergency reserve (₹)</label>
							<input id="emergencyReserves" class="field-input" inputmode="decimal" bind:value={draft.emergencyReserves} />
							<p class="muted mt-1">Set aside only for genuine emergencies. Must be liquid.</p>
							{#if showErrors && errors.emergencyReserves}<p class="field-error">{errors.emergencyReserves}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="goalReservedAmount">Reserved for a specific goal (₹)</label>
							<input id="goalReservedAmount" class="field-input" inputmode="decimal" bind:value={draft.goalReservedAmount} />
							{#if showErrors && errors.goalReservedAmount}<p class="field-error">{errors.goalReservedAmount}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="currentInvestments">Current investments (₹)</label>
							<input id="currentInvestments" class="field-input" inputmode="decimal" bind:value={draft.currentInvestments} />
							{#if showErrors && errors.currentInvestments}<p class="field-error">{errors.currentInvestments}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="existingLiabilities">Outstanding loan balances (₹)</label>
							<input id="existingLiabilities" class="field-input" inputmode="decimal" bind:value={draft.existingLiabilities} />
							<p class="muted mt-1">Principal still owed, not the EMI.</p>
							{#if showErrors && errors.existingLiabilities}<p class="field-error">{errors.existingLiabilities}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="designatedMonthly">Monthly amount you want to invest (₹)</label>
							<input id="designatedMonthly" class="field-input" inputmode="decimal" bind:value={draft.designatedMonthly} />
							<p class="muted mt-1">Optional. The engine checks it against the money left after goal and reserve needs.</p>
							{#if showErrors && errors.designatedMonthly}<p class="field-error">{errors.designatedMonthly}</p>{/if}
						</div>
					</div>
					<div class="mt-5">
						<Notice tone="info" title="Money is counted once">
							Emergency reserves and goal reserves come out of liquid savings. Only what remains is considered for investing.
						</Notice>
					</div>
				{/if}

				{#if step === 3}
					<div class="space-y-4">
						<p class="muted">Add each loan separately so interest rates, remaining terms and overdue status can be assessed. Totals must match the EMI and outstanding amounts entered in the previous steps.</p>
						{#each draft.debts as debt, i (i)}
							<div class="grid gap-3 rounded-xl border border-line bg-raised/40 p-4 sm:grid-cols-3">
								<div>
									<label class="field-label" for="debtType{i}">Loan type</label>
									<select id="debtType{i}" class={selectClass} bind:value={debt.debtType}>
										{#each DEBT_TYPES as type (type)}<option value={type}>{labelize(type)}</option>{/each}
									</select>
								</div>
								<div>
									<label class="field-label" for="debtOutstanding{i}">Outstanding (₹)</label>
									<input id="debtOutstanding{i}" class="field-input" inputmode="decimal" bind:value={debt.outstanding} />
								</div>
								<div>
									<label class="field-label" for="debtRate{i}">Interest rate (% a year)</label>
									<input id="debtRate{i}" class="field-input" inputmode="decimal" bind:value={debt.rate} />
								</div>
								<div>
									<label class="field-label" for="debtEmi{i}">EMI (₹/month)</label>
									<input id="debtEmi{i}" class="field-input" inputmode="decimal" bind:value={debt.emi} />
								</div>
								<div>
									<label class="field-label" for="debtMonths{i}">Months remaining</label>
									<input id="debtMonths{i}" class="field-input" inputmode="numeric" bind:value={debt.remainingMonths} />
								</div>
								<div class="flex items-end justify-between gap-3">
									<label class="flex items-center gap-2 text-[13px]"><input type="checkbox" bind:checked={debt.overdue} /> Overdue</label>
									<button type="button" class="btn btn-danger !px-2.5 !py-1.5" onclick={() => removeDebt(i)} aria-label="Remove loan {i + 1}"><Trash2 size={14} /></button>
								</div>
							</div>
						{/each}
						<button type="button" class="btn" onclick={addDebt}><Plus size={14} /> Add a loan</button>
						{#if showErrors && (errors.monthlyEmi || errors.existingLiabilities)}
							<p class="field-error">{errors.monthlyEmi ?? ''} {errors.existingLiabilities ?? ''}</p>
						{/if}
					</div>
				{/if}

				{#if step === 4}
					<div class="grid gap-4 sm:grid-cols-2">
						<div>
							<label class="field-label" for="experience">Investment experience</label>
							<select id="experience" class={selectClass} bind:value={draft.investmentExperience}>
								<option value="">Select...</option>
								<option value="BEGINNER">Beginner - mostly savings accounts or deposits (plain-English recommendations)</option>
								<option value="INTERMEDIATE">Intermediate - some funds or shares (core-satellite recommendations)</option>
								<option value="EXPERIENCED">Experienced - several market cycles (quantitative recommendations)</option>
							</select>
							{#if showErrors && errors.investmentExperience}<p class="field-error">{errors.investmentExperience}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="goalName">Goal name (optional)</label>
							<input id="goalName" class="field-input" bind:value={draft.goalName} />
						</div>
						<div>
							<label class="field-label" for="goalCategory">Goal category</label>
							<select id="goalCategory" class={selectClass} bind:value={draft.goalCategory}>
								<option value="">Not specified</option>
								<option value="WEALTH_CREATION">Wealth creation</option>
								<option value="EDUCATION">Education</option>
								<option value="HOME_PURCHASE">Home purchase</option>
								<option value="RETIREMENT">Retirement</option>
								<option value="EMERGENCY_RESERVE">Emergency reserve</option>
								<option value="OTHER">Other</option>
							</select>
							{#if showErrors && errors.goalCategory}<p class="field-error">{errors.goalCategory}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="goalAmount">Target amount (₹)</label>
							<input id="goalAmount" class="field-input" inputmode="decimal" bind:value={draft.goalAmount} />
							{#if showErrors && errors.goalAmount}<p class="field-error">{errors.goalAmount}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="goalDeadline">Target date</label>
							<input id="goalDeadline" class="field-input" type="date" min={todayIso} bind:value={draft.goalDeadline} />
							{#if showErrors && errors.goalDeadline}<p class="field-error">{errors.goalDeadline}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="goalImportance">Importance</label>
							<select id="goalImportance" class={selectClass} bind:value={draft.goalImportance}>
								<option value="">Not specified</option>
								<option value="LOW">Low</option>
								<option value="MEDIUM">Medium</option>
								<option value="HIGH">High</option>
							</select>
						</div>
						<div>
							<label class="field-label" for="goalLiquidity">How soon might you need this money?</label>
							<select id="goalLiquidity" class={selectClass} bind:value={draft.goalLiquidity}>
								<option value="">Not specified</option>
								<option value="LOW">Not soon - I can wait</option>
								<option value="MEDIUM">Possibly within a few years</option>
								<option value="HIGH">It may be needed at short notice</option>
							</select>
						</div>
					</div>
				{/if}

				{#if step === 5}
					<div class="space-y-5">
						<Notice tone="info" title="Two different things are being measured">
							Questions 1 and 2 measure behaviour. Questions 3 to 5 help measure your capacity to absorb a loss. Comfort with volatility
							does not mean a loss is affordable, so the engine keeps these separate.
						</Notice>
						<div>
							<label class="field-label" for="drawdown">An investment of ₹10,000 falls to ₹8,000. What would you most likely do?</label>
							<select id="drawdown" class={selectClass} bind:value={draft.drawdownReaction}>
								<option value="">Select…</option>
								<option value="SELL_IMMEDIATELY">Sell to stop further loss</option>
								<option value="WAIT">Wait and hope it recovers</option>
								<option value="REASSESS_THESIS">Re-check whether my original reasons still hold</option>
								<option value="ADD_IF_THESIS_VALID">Consider adding more, if my original reasons still hold</option>
							</select>
							{#if showErrors && errors.drawdownReaction}<p class="field-error">{errors.drawdownReaction}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="horizon">How long are you prepared to stay invested?</label>
							<select id="horizon" class={selectClass} bind:value={draft.preferredHorizon}>
								<option value="">Select…</option>
								<option value="UNDER_1_YEAR">Under one year</option>
								<option value="ONE_TO_THREE_YEARS">One to three years</option>
								<option value="THREE_TO_SEVEN_YEARS">Three to seven years</option>
								<option value="OVER_SEVEN_YEARS">More than seven years</option>
							</select>
							{#if showErrors && errors.preferredHorizon}<p class="field-error">{errors.preferredHorizon}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="gains">After a strong year of gains, what would you most likely do?</label>
							<select id="gains" class={selectClass} bind:value={draft.gainsReaction}>
								<option value="">Select…</option>
								<option value="KEEP_PLAN">Keep to my plan</option>
								<option value="INVEST_MORE_ON_GAINS">Invest more because prices have been rising</option>
								<option value="WITHDRAW_SOME">Withdraw some of the gains</option>
							</select>
							{#if showErrors && errors.gainsReaction}<p class="field-error">{errors.gainsReaction}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="lossImpact">If a similar loss happened, would it affect your ability to meet monthly expenses?</label>
							<select id="lossImpact" class={selectClass} bind:value={draft.lossImpactOnExpenses}>
								<option value="">Select…</option>
								<option value="NO_IMPACT">No</option>
								<option value="TIGHTEN_BUDGET">I would have to tighten my budget</option>
								<option value="AFFECTS_ESSENTIALS">Yes, it would affect essentials</option>
							</select>
							{#if showErrors && errors.lossImpactOnExpenses}<p class="field-error">{errors.lossImpactOnExpenses}</p>{/if}
						</div>
						<div>
							<label class="field-label" for="stability">How stable is your income?</label>
							<select id="stability" class={selectClass} bind:value={draft.incomeStability}>
								<option value="">Select…</option>
								<option value="VERY_STABLE">Very stable</option>
								<option value="SOMEWHAT_STABLE">Somewhat stable</option>
								<option value="IRREGULAR">Irregular</option>
							</select>
							{#if showErrors && errors.incomeStability}<p class="field-error">{errors.incomeStability}</p>{/if}
						</div>
					</div>
				{/if}

				{#if step === 6}
					<div class="space-y-4">
						<dl class="kv">
							<div><dt>Name</dt><dd>{draft.displayName || 'n/a'}</dd></div>
							<div><dt>Monthly income</dt><dd>{inr(draft.monthlyIncome || null)}</dd></div>
							<div><dt>Essential expenses</dt><dd>{inr(draft.essentialExpenses || null)}</dd></div>
							<div><dt>EMIs</dt><dd>{inr(draft.monthlyEmi || '0')}</dd></div>
							<div><dt>Liquid savings</dt><dd>{inr(draft.liquidSavings || null)}</dd></div>
							<div><dt>Emergency reserve</dt><dd>{inr(draft.emergencyReserves || '0')}</dd></div>
							<div><dt>Goal reserve</dt><dd>{inr(draft.goalReservedAmount || '0')}</dd></div>
							<div><dt>Goal</dt><dd>{draft.goalName || labelize(draft.goalCategory)} {draft.goalDeadline ? `· by ${draft.goalDeadline}` : ''}</dd></div>
							<div><dt>Loans listed</dt><dd>{draft.debts.length}</dd></div>
						</dl>
						{#if errorCount > 0}
							<Notice tone="danger" title="Fix these before saving">
								<ul class="list-disc space-y-1 pl-5">
									{#each Object.entries(errors) as [key, text] (key)}<li>{text}</li>{/each}
								</ul>
							</Notice>
						{:else}
							<Notice tone="success" title="Ready to save">
								Saving recalculates readiness on the server with the rule set and reference date shown on your dashboard.
							</Notice>
						{/if}
						{#if failure}
							<Notice tone="danger" title="The server did not accept the profile">
								{failure}
								{#if fieldFailures.length > 0}
									<ul class="mt-2 list-disc space-y-1 pl-5">
										{#each fieldFailures as item, i (i)}<li>{item.message}</li>{/each}
									</ul>
								{/if}
							</Notice>
						{/if}
						{#if message}<p class="text-brand-soft" role="status">{message}</p>{/if}
					</div>
				{/if}
			</Card>

			<div class="flex items-center justify-between gap-3">
				<button type="button" class="btn" onclick={() => (step = Math.max(0, step - 1))} disabled={step === 0}><ChevronLeft size={14} /> Back</button>
				{#if step < STEPS.length - 1}
					<button type="button" class="btn btn-primary" onclick={next}>Continue <ChevronRight size={14} /></button>
				{:else}
					<button type="button" class="btn btn-primary" onclick={save} disabled={saving}>
						<Save size={14} />{saving ? 'Saving and recalculating…' : profileId ? 'Save changes' : 'Save and calculate readiness'}
					</button>
				{/if}
			</div>
		</form>
	{/if}
</div>
