/**
 * Client-side guidance for the onboarding form. The backend performs the same checks and is the authority:
 * every rule here mirrors a server rule so the user sees problems before submitting.
 */

export interface DebtDraft {
	debtType: string;
	outstanding: string;
	rate: string;
	emi: string;
	remainingMonths: string;
	overdue: boolean;
}

export interface Draft {
	displayName: string;
	ageRange: string;
	employmentStatus: string;
	monthlyIncome: string;
	essentialExpenses: string;
	nonessentialExpenses: string;
	monthlyEmi: string;
	otherCommitments: string;
	totalSavings: string;
	liquidSavings: string;
	emergencyReserves: string;
	goalReservedAmount: string;
	currentInvestments: string;
	existingLiabilities: string;
	designatedMonthly: string;
	debts: DebtDraft[];
	investmentExperience: string;
	goalName: string;
	goalCategory: string;
	goalAmount: string;
	goalDeadline: string;
	goalImportance: string;
	goalLiquidity: string;
	drawdownReaction: string;
	preferredHorizon: string;
	gainsReaction: string;
	lossImpactOnExpenses: string;
	incomeStability: string;
}

export const EMPTY_DRAFT: Draft = {
	displayName: '',
	ageRange: '',
	employmentStatus: '',
	monthlyIncome: '',
	essentialExpenses: '',
	nonessentialExpenses: '',
	monthlyEmi: '',
	otherCommitments: '',
	totalSavings: '',
	liquidSavings: '',
	emergencyReserves: '',
	goalReservedAmount: '',
	currentInvestments: '',
	existingLiabilities: '',
	designatedMonthly: '',
	debts: [],
	investmentExperience: '',
	goalName: '',
	goalCategory: '',
	goalAmount: '',
	goalDeadline: '',
	goalImportance: '',
	goalLiquidity: '',
	drawdownReaction: '',
	preferredHorizon: '',
	gainsReaction: '',
	lossImpactOnExpenses: '',
	incomeStability: ''
};

export const STEPS = [
	{ key: 'basics', title: 'Basics', fields: ['displayName', 'ageRange', 'employmentStatus', 'monthlyIncome'] },
	{ key: 'expenses', title: 'Monthly outflows', fields: ['essentialExpenses', 'nonessentialExpenses', 'monthlyEmi', 'otherCommitments'] },
	{ key: 'position', title: 'Savings and reserves', fields: ['totalSavings', 'liquidSavings', 'emergencyReserves', 'goalReservedAmount', 'currentInvestments', 'existingLiabilities', 'designatedMonthly'] },
	{ key: 'debts', title: 'Loans (optional)', fields: ['debts'] },
	{ key: 'goal', title: 'Experience and goal', fields: ['investmentExperience', 'goalCategory', 'goalAmount', 'goalDeadline', 'goalImportance', 'goalLiquidity'] },
	{ key: 'risk', title: 'Risk questionnaire', fields: ['drawdownReaction', 'preferredHorizon', 'gainsReaction', 'lossImpactOnExpenses', 'incomeStability'] },
	{ key: 'review', title: 'Review and save', fields: [] as string[] }
] as const;

const AMOUNT = /^\d+(\.\d{1,2})?$/;

/** Returns null for a blank or invalid amount, otherwise the amount as a number. Blank is handled by callers. */
export function parseAmount(value: string): number | null {
	const cleaned = value.trim().replace(/,/g, '');
	if (!AMOUNT.test(cleaned)) return null;
	const n = Number(cleaned);
	return Number.isFinite(n) ? n : null;
}

function amountOrZero(value: string): number {
	return value.trim() === '' ? 0 : (parseAmount(value) ?? Number.NaN);
}

export function validateDraft(d: Draft, todayIso: string): Record<string, string> {
	const e: Record<string, string> = {};
	const money = (key: keyof Draft, label: string, required: boolean) => {
		const raw = d[key] as string;
		if (raw.trim() === '') {
			if (required) e[key] = `${label} is required.`;
			return;
		}
		if (parseAmount(raw) === null) e[key] = `${label} must be a number with at most two decimals.`;
	};

	if (d.displayName.trim().length < 2) e.displayName = 'Enter a name or nickname (at least 2 characters).';
	if (!d.ageRange) e.ageRange = 'Choose an age range.';
	if (!d.employmentStatus) e.employmentStatus = 'Choose your employment status.';
	money('monthlyIncome', 'Monthly take-home income', true);
	if (!e.monthlyIncome && (parseAmount(d.monthlyIncome) ?? 0) <= 0) e.monthlyIncome = 'Income must be above zero.';

	money('essentialExpenses', 'Essential expenses', true);
	if (!e.essentialExpenses && (parseAmount(d.essentialExpenses) ?? 0) <= 0) {
		e.essentialExpenses = 'Essential expenses must be above zero, otherwise emergency coverage cannot be measured.';
	}
	money('nonessentialExpenses', 'Non-essential expenses', false);
	money('monthlyEmi', 'Monthly EMI', false);
	money('otherCommitments', 'Other commitments', false);

	money('totalSavings', 'Total savings', true);
	money('liquidSavings', 'Liquid savings', true);
	money('emergencyReserves', 'Emergency reserves', false);
	money('goalReservedAmount', 'Money reserved for a goal', false);
	money('currentInvestments', 'Current investments', false);
	money('existingLiabilities', 'Outstanding liabilities', false);
	money('designatedMonthly', 'Monthly amount you designate for investing', false);

	const total = amountOrZero(d.totalSavings);
	const liquid = amountOrZero(d.liquidSavings);
	const emergency = amountOrZero(d.emergencyReserves);
	const goalReserved = amountOrZero(d.goalReservedAmount);
	if (!e.liquidSavings && liquid > total) e.liquidSavings = 'Liquid savings cannot exceed total savings.';
	if (!e.emergencyReserves && emergency > liquid) e.emergencyReserves = 'Emergency reserves must be held in liquid form and cannot exceed liquid savings.';
	if (!e.goalReservedAmount && goalReserved > liquid) e.goalReservedAmount = 'Goal reserves cannot exceed liquid savings.';
	if (!e.emergencyReserves && !e.goalReservedAmount && emergency + goalReserved > liquid) {
		e.goalReservedAmount = 'Emergency reserves plus goal reserves cannot exceed liquid savings. The same rupee cannot be reserved twice.';
	}

	if (d.debts.length > 0) {
		const emiTotal = d.debts.reduce((sum, debt) => sum + amountOrZero(debt.emi), 0);
		const outstandingTotal = d.debts.reduce((sum, debt) => sum + amountOrZero(debt.outstanding), 0);
		if (!e.monthlyEmi && Math.abs(emiTotal - amountOrZero(d.monthlyEmi)) > 0.001) {
			e.monthlyEmi = `Monthly EMI must equal the sum of the loan EMIs listed (${emiTotal.toFixed(2)}).`;
		}
		if (!e.existingLiabilities && Math.abs(outstandingTotal - amountOrZero(d.existingLiabilities)) > 0.001) {
			e.existingLiabilities = `Outstanding liabilities must equal the sum of listed loan balances (${outstandingTotal.toFixed(2)}).`;
		}
	}

	if (!d.investmentExperience) e.investmentExperience = 'Choose your experience level.';
	if (d.goalAmount.trim() !== '' && parseAmount(d.goalAmount) === null) e.goalAmount = 'Goal amount must be a number.';
	if (d.goalAmount.trim() !== '' && !d.goalDeadline) e.goalDeadline = 'A goal amount needs a target date.';
	if (d.goalDeadline && d.goalDeadline < todayIso) e.goalDeadline = 'The goal date is in the past. Enter a future date.';
	if (d.goalName.trim() && !d.goalDeadline) e.goalDeadline = e.goalDeadline ?? 'Add a target date so the goal horizon can be measured.';

	const required: [keyof Draft, string][] = [
		['drawdownReaction', 'Answer the ₹10,000 → ₹8,000 question'],
		['preferredHorizon', 'Choose your preferred holding period'],
		['gainsReaction', 'Answer the after-gains question'],
		['lossImpactOnExpenses', 'Say whether a similar loss would affect monthly expenses'],
		['incomeStability', 'Describe your income stability']
	];
	for (const [key, message] of required) if (!d[key]) e[key] = message;

	return e;
}

export function stepHasErrors(step: number, errors: Record<string, string>): boolean {
	const keys = STEPS[step].fields as readonly string[];
	return keys.some((key) => Boolean(errors[key]));
}

function amountString(value: string): string | null {
	if (value.trim() === '') return null;
	const parsed = parseAmount(value);
	return parsed === null ? null : parsed.toFixed(2);
}

/** Builds the exact JSON body accepted by POST/PUT /api/profile. */
export function toPayload(d: Draft): Record<string, unknown> {
	const money = (value: string) => amountString(value) ?? '0.00';
	const answered = d.drawdownReaction && d.preferredHorizon && d.gainsReaction && d.lossImpactOnExpenses && d.incomeStability;
	return {
		display_name: d.displayName.trim(),
		age_range: d.ageRange,
		employment_status: d.employmentStatus,
		monthly_income: money(d.monthlyIncome),
		essential_expenses: money(d.essentialExpenses),
		nonessential_expenses: money(d.nonessentialExpenses),
		monthly_emi: money(d.monthlyEmi),
		other_commitments: money(d.otherCommitments),
		total_savings: money(d.totalSavings),
		liquid_savings: money(d.liquidSavings),
		emergency_reserves: money(d.emergencyReserves),
		goal_reserved_amount: money(d.goalReservedAmount),
		current_investments: money(d.currentInvestments),
		existing_liabilities: money(d.existingLiabilities),
		monthly_investment_designated: money(d.designatedMonthly),
		debts: d.debts.map((debt) => ({
			debt_type: debt.debtType,
			outstanding_amount: money(debt.outstanding),
			interest_rate_pct: money(debt.rate),
			emi_amount: money(debt.emi),
			remaining_months: Number.parseInt(debt.remainingMonths || '0', 10) || 0,
			is_overdue: debt.overdue
		})),
		investment_experience: d.investmentExperience,
		goal_name: d.goalName.trim() || null,
		goal_category: d.goalCategory || null,
		goal_amount: amountString(d.goalAmount),
		goal_deadline: d.goalDeadline || null,
		goal_importance: d.goalImportance || null,
		goal_liquidity: d.goalLiquidity || null,
		questionnaire: answered
			? {
					drawdown_reaction: d.drawdownReaction,
					preferred_horizon: d.preferredHorizon,
					gains_reaction: d.gainsReaction,
					loss_impact_on_expenses: d.lossImpactOnExpenses,
					income_stability: d.incomeStability
				}
			: null
	};
}
