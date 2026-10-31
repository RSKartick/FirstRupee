const rupees = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
const rupeesPrecise = new Intl.NumberFormat('en-IN', {
	style: 'currency',
	currency: 'INR',
	minimumFractionDigits: 2,
	maximumFractionDigits: 2
});

type Numeric = string | number | null | undefined;

function toNumber(value: Numeric): number | null {
	if (value === null || value === undefined || value === '') return null;
	const n = typeof value === 'number' ? value : Number(value);
	return Number.isFinite(n) ? n : null;
}

/** Indian digit grouping (₹12,34,567). Values are formatted for display only and never recalculated. */
export function inr(value: Numeric, precise = false): string {
	const n = toNumber(value);
	if (n === null) return 'n/a';
	return (precise ? rupeesPrecise : rupees).format(n);
}

export function pct(value: Numeric, digits = 1): string {
	const n = toNumber(value);
	return n === null ? 'n/a' : `${n.toFixed(digits)}%`;
}

export function signedPct(value: Numeric, digits = 2): string {
	const n = toNumber(value);
	if (n === null) return 'n/a';
	return `${n > 0 ? '+' : ''}${n.toFixed(digits)}%`;
}

export function num(value: Numeric, digits = 2, suffix = ''): string {
	const n = toNumber(value);
	return n === null ? 'n/a' : `${n.toFixed(digits)}${suffix}`;
}

export function months(value: number | null | undefined): string {
	if (value === null || value === undefined) return 'Not set';
	if (value < 0) return 'Deadline passed';
	if (value === 0) return 'Due this month';
	return value === 1 ? '1 month' : `${value} months`;
}

export function dateLabel(iso: string | null | undefined): string {
	if (!iso) return 'Not stated';
	const date = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
	if (Number.isNaN(date.getTime())) return iso;
	return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function labelize(value: string | null | undefined): string {
	if (!value) return 'Not stated';
	const text = value.replace(/_/g, ' ').toLowerCase();
	return text.charAt(0).toUpperCase() + text.slice(1);
}

export type Tone = 'success' | 'warn' | 'danger' | 'info' | 'neutral';

export function readinessTone(status: string | null | undefined): Tone {
	switch (status) {
		case 'READY_TO_EXPLORE':
		case 'OK':
		case 'FURTHER_RESEARCH_REQUIRED':
			return 'success';
		case 'PREPARATION':
		case 'CONSTRAINED':
		case 'STALE':
		case 'MATERIAL_RISKS_IDENTIFIED':
			return 'warn';
		case 'NOT_READY':
		case 'CRITICAL':
		case 'INSUFFICIENT_EVIDENCE':
		case 'FINANCIAL_CONSTRAINTS_IDENTIFIED':
		case 'GOAL_HORIZON_MISMATCH':
		case 'INVALID':
			return 'danger';
		default:
			return 'neutral';
	}
}
