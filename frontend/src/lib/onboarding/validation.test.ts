import { describe, expect, it } from 'vitest';
import { EMPTY_DRAFT, parseAmount, toPayload, validateDraft, type Draft } from './validation';

const TODAY = '2026-10-31';

function complete(overrides: Partial<Draft> = {}): Draft {
	return {
		...EMPTY_DRAFT,
		displayName: 'Aditi',
		ageRange: 'TWENTY_TO_THIRTY',
		employmentStatus: 'SALARIED',
		monthlyIncome: '60000',
		essentialExpenses: '25000',
		nonessentialExpenses: '5000',
		monthlyEmi: '5000',
		otherCommitments: '0',
		totalSavings: '400000',
		liquidSavings: '300000',
		emergencyReserves: '150000',
		goalReservedAmount: '20000',
		investmentExperience: 'BEGINNER',
		drawdownReaction: 'REASSESS_THESIS',
		preferredHorizon: 'OVER_SEVEN_YEARS',
		gainsReaction: 'KEEP_PLAN',
		lossImpactOnExpenses: 'NO_IMPACT',
		incomeStability: 'VERY_STABLE',
		...overrides
	};
}

describe('amount parsing', () => {
	it('accepts grouped amounts with up to two decimals', () => {
		expect(parseAmount('30,000')).toBe(30000);
		expect(parseAmount('2500.50')).toBe(2500.5);
	});

	it('rejects negatives, scientific notation and excess decimals', () => {
		expect(parseAmount('-5')).toBeNull();
		expect(parseAmount('1e5')).toBeNull();
		expect(parseAmount('10.123')).toBeNull();
		expect(parseAmount('abc')).toBeNull();
	});
});

describe('onboarding validation mirrors the server rules', () => {
	it('accepts a complete, consistent draft', () => {
		expect(validateDraft(complete(), TODAY)).toEqual({});
	});

	it('rejects liquid savings above total savings', () => {
		expect(validateDraft(complete({ liquidSavings: '500000' }), TODAY).liquidSavings).toMatch(/cannot exceed total/);
	});

	it('rejects emergency plus goal reserves above liquid savings', () => {
		const errors = validateDraft(complete({ emergencyReserves: '280000', goalReservedAmount: '30000' }), TODAY);
		expect(errors.goalReservedAmount).toMatch(/same rupee/);
	});

	it('requires essential expenses above zero', () => {
		expect(validateDraft(complete({ essentialExpenses: '0' }), TODAY).essentialExpenses).toMatch(/above zero/);
	});

	it('rejects a goal date in the past', () => {
		expect(validateDraft(complete({ goalAmount: '50000', goalDeadline: '2020-01-01' }), TODAY).goalDeadline).toMatch(/past/);
	});

	it('requires a target date when a goal amount is entered', () => {
		expect(validateDraft(complete({ goalAmount: '50000', goalDeadline: '' }), TODAY).goalDeadline).toMatch(/target date/);
	});

	it('requires the EMI total to equal the listed loan EMIs', () => {
		const draft = complete({
			monthlyEmi: '5000',
			existingLiabilities: '100000',
			debts: [{ debtType: 'CAR_LOAN', outstanding: '100000', rate: '9', emi: '4000', remainingMonths: '24', overdue: false }]
		});
		expect(validateDraft(draft, TODAY).monthlyEmi).toMatch(/sum of the loan EMIs/);
	});

	it('requires every questionnaire answer', () => {
		expect(validateDraft(complete({ drawdownReaction: '' }), TODAY).drawdownReaction).toBeDefined();
		expect(validateDraft(complete({ incomeStability: '' }), TODAY).incomeStability).toBeDefined();
	});
});

describe('payload construction', () => {
	it('sends money as fixed two-decimal strings and omits an unanswered questionnaire', () => {
		const payload = toPayload(complete({ monthlyIncome: '30000', goalAmount: '' }));
		expect(payload.monthly_income).toBe('30000.00');
		expect(payload.goal_amount).toBeNull();
		expect(payload.questionnaire).not.toBeNull();
		expect(toPayload(complete({ gainsReaction: '' })).questionnaire).toBeNull();
	});

	it('sends blank optional money as zero, never as an empty string', () => {
		const payload = toPayload(complete({ currentInvestments: '', existingLiabilities: '' }));
		expect(payload.current_investments).toBe('0.00');
		expect(payload.existing_liabilities).toBe('0.00');
	});
});
