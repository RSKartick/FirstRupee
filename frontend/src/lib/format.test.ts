import { describe, expect, it } from 'vitest';
import { inr, labelize, months, pct, readinessTone, signedPct } from './format';

describe('money and percentage formatting', () => {
	it('uses Indian digit grouping and the rupee sign', () => {
		expect(inr('1234567')).toBe('₹12,34,567');
		expect(inr('4000.00')).toBe('₹4,000');
	});

	it('shows negative amounts with a leading minus sign', () => {
		expect(inr(-4000)).toBe('-₹4,000');
		expect(inr('-5000.00')).toBe('-₹5,000');
	});

	it('shows two decimals when precision is requested', () => {
		expect(inr('19416.67', true)).toBe('₹19,416.67');
	});

	it('returns n/a for missing or non-numeric values instead of zero', () => {
		expect(inr(null)).toBe('n/a');
		expect(inr(undefined)).toBe('n/a');
		expect(inr('')).toBe('n/a');
		expect(inr('abc')).toBe('n/a');
		expect(pct(null)).toBe('n/a');
	});

	it('formats percentages and signed percentages', () => {
		expect(pct('12.345', 1)).toBe('12.3%');
		expect(signedPct(3.456)).toBe('+3.46%');
		expect(signedPct(-2)).toBe('-2.00%');
	});
});

describe('labels and status tones', () => {
	it('humanises enum values', () => {
		expect(labelize('NOT_READY')).toBe('Not ready');
		expect(labelize(null)).toBe('Not stated');
	});

	it('describes horizons, including passed deadlines', () => {
		expect(months(-1)).toBe('Deadline passed');
		expect(months(0)).toBe('Due this month');
		expect(months(1)).toBe('1 month');
		expect(months(10)).toBe('10 months');
		expect(months(null)).toBe('Not set');
	});

	it('maps readiness statuses to tones without implying a buy signal', () => {
		expect(readinessTone('READY_TO_EXPLORE')).toBe('success');
		expect(readinessTone('PREPARATION')).toBe('warn');
		expect(readinessTone('NOT_READY')).toBe('danger');
		expect(readinessTone('INSUFFICIENT_EVIDENCE')).toBe('danger');
	});
});
