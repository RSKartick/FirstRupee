/**
 * Response contracts mirroring the FastAPI schemas. Money and percentages arrive as fixed-point strings and are formatted in
 * `$lib/format`. They are never recalculated in the browser: every financial figure comes from the backend engines.
 */

export interface SessionUser {
	id: number;
	email: string | null;
	display_name: string;
	is_guest: boolean;
}

export interface ProfileSummary {
	id: number;
	display_name: string;
	monthly_income: string;
	goal_name: string | null;
	is_demo_clone: boolean;
	updated_at: string;
}

export interface DebtOut {
	id: number;
	debt_type: string;
	outstanding_amount: string;
	interest_rate_pct: string;
	emi_amount: string;
	remaining_months: number;
	is_overdue: boolean;
}

export interface Questionnaire {
	drawdown_reaction: string;
	preferred_horizon: string;
	gains_reaction: string;
	loss_impact_on_expenses: string;
	income_stability: string;
}

export interface ProfileOut {
	id: number;
	display_name: string;
	age_range: string;
	employment_status: string;
	monthly_income: string;
	essential_expenses: string;
	nonessential_expenses: string;
	monthly_emi: string;
	other_commitments: string;
	total_savings: string;
	liquid_savings: string;
	emergency_reserves: string;
	goal_reserved_amount: string;
	current_investments: string;
	existing_liabilities: string;
	monthly_investment_designated: string;
	debts: DebtOut[];
	investment_experience: string;
	goal_name: string | null;
	goal_category: string | null;
	goal_amount: string | null;
	goal_deadline: string | null;
	goal_importance: string | null;
	goal_liquidity: string | null;
	questionnaire: Questionnaire | null;
	is_demo_clone: boolean;
	demo_key: string | null;
	created_at: string;
	updated_at: string;
}

export interface Finding {
	code: string;
	label: string;
	severity: 'BLOCKER' | 'WARNING' | 'INFO';
	detail: string;
	inputs: Record<string, string | number | boolean | null>;
}

export interface RecommendedAssetAllocation {
	symbol: string;
	name: string;
	asset_type: string;
	role: string;
	allocation_pct: number;
	monthly_amount_inr: string;
	lump_sum_amount_inr: string;
	action_status: 'DEPLOY_NOW' | 'STAGE_CAUTIOUSLY' | 'PARK_SAFELY_UNTIL_READY';
	rationale: string;
}

export interface Recommendations {
	experience_level: 'BEGINNER' | 'INTERMEDIATE' | 'EXPERIENCED';
	tone_label: string;
	readiness_status: 'NOT_READY' | 'PREPARATION' | 'READY_TO_EXPLORE';
	headline: string;
	summary: string;
	textual_guidelines: string[];
	category_split_pct: {
		equity_pct: number;
		fixed_income_and_liquid_pct: number;
		gold_pct: number;
	};
	monthly_plan: {
		monthly_income_inr: string;
		committed_outflow_inr: string;
		monthly_surplus_inr: string;
		emergency_topup_inr: string;
		emergency_topup_pct: number;
		debt_prepayment_inr: string;
		debt_prepayment_pct: number;
		goal_reserve_inr: string;
		goal_reserve_pct: number;
		investable_capacity_inr: string;
		recommended_market_deployment_inr: string;
		recommended_market_deployment_pct: number;
	};
	lump_sum_plan: {
		liquid_savings_inr: string;
		emergency_locked_inr: string;
		goal_locked_inr: string;
		unallocated_liquid_inr: string;
		immediate_reserve_boost_inr: string;
		staged_market_deployment_inr: string;
		recommended_tranches_months: number;
		monthly_tranche_inr: string;
	};
	asset_allocations: RecommendedAssetAllocation[];
}

export interface MarketBenchmark {
	symbol: string;
	label: string;
	category: string;
	price: string;
	day_change_pct: number;
	trailing_1y_pct: number;
	as_of: string;
	source: string;
}

export interface Readiness {
	status: 'NOT_READY' | 'PREPARATION' | 'READY_TO_EXPLORE';
	completeness: 'COMPLETE' | 'INCOMPLETE';
	rule_version: string;
	as_of: string;
	profile_updated_at: string | null;
	metrics: Record<string, string | number | null>;
	recommendations?: Recommendations;
	capacity_detail: { components: Record<string, { score: string; weight: number }>; caps: { code: string; cap: number; reason: string }[] };
	findings: Finding[];
	blockers: string[];
	warnings: string[];
	missing_information: string[];
	limitations: string[];
	improvement_steps: string[];
	explanation: string;
	disclaimer: string;
}

export interface AssetSummary {
	id: number;
	symbol: string;
	name: string;
	asset_type: string;
	description: string;
	volatility_class: 'LOW' | 'MODERATE' | 'HIGH';
	min_horizon_months: number;
	expense_ratio_pct: string | null;
	is_synthetic: boolean;
	data_source: string;
	data_as_of: string;
	observations: number;
	first_observation: string | null;
	last_observation: string | null;
	latest_price?: string | null;
	day_change_pct?: number | null;
}

export interface AssetDetail extends AssetSummary {
	what_it_is: string;
	how_it_works: string;
	advantages: string[];
	risks: string[];
	liquidity: string;
	fees: string;
}

export interface EvidenceItem {
	evidence_key: string;
	title: string;
	source_type: string;
	verification_status: string;
	publication_date: string | null;
	period: string | null;
	summary: string;
	metrics: Record<string, string>;
}

export interface MarketContext {
	status: 'OK' | 'STALE' | 'UNAVAILABLE' | 'FUTURE_DATA_INVALID';
	note?: string;
	annualised_volatility_pct?: number | null;
	trailing_12m_return_pct?: number | null;
	trailing_12m_note?: string;
	last_observation?: string;
	age_days?: number;
	observations_used?: number;
	is_synthetic: boolean;
	source: string;
	disclaimer: string;
}

export interface AssetPage {
	asset: AssetDetail;
	evidence: EvidenceItem[];
	market_context: MarketContext;
}

export interface HistoryPoint {
	date: string;
	close: string;
}

export interface Clock {
	name: string;
	status: string;
	headline: string;
	explanation: string;
	data: Record<string, unknown>;
}

export interface Timing {
	rule_version: string;
	as_of: string;
	verdict_code: string;
	verdict: string;
	readiness_status: string;
	precedence: { rule: string; description: string; triggered: boolean }[];
	clocks: { money: Clock; goal: Clock; market: Clock };
	caution: string;
}

export interface Claim {
	claim: string;
	claim_type: 'FACT' | 'QUALITATIVE' | 'HYPOTHESIS';
	evidence_key: string | null;
	metric_key: string | null;
	claimed_value: string | null;
	period: string | null;
}

export interface CheckedClaim extends Claim {
	side: 'ANALYST' | 'DEVIL_ADVOCATE';
	status: string;
	evidence_status: string | null;
	observed_value: string | null;
	reasons: string[];
	freshness: { publication_date: string | null; age_days: number | null; limit_days: number; status: string } | null;
}

export interface Evaluation {
	status: string;
	evaluator_version: string;
	claim_checks: CheckedClaim[];
	counts: Record<string, number>;
	evidence_quality: { score: number; label: string; explanation: string };
	conflicts: { period: string; metric_key: string; records: string[]; values: string[] }[];
	data_status: { synthetic_evidence_used: boolean; stale_sources: { evidence_key: string; status: string }[]; reference_date: string };
	material_risks: { code: string; label: string; metric_key: string; observed_value: string; threshold: string; evidence_key: string; period: string; evidence_status: string; basis: string }[];
	unconfirmed_concerns: string[];
	missing_data: string[];
	suitability_notes: string[];
	unresolved_uncertainties: string[];
	advisory_notice: string;
}

export interface ResearchAnalysis {
	analysis_id: number;
	profile_id: number;
	as_of: string;
	asset: { id: number; symbol: string; name: string; asset_type: string; is_synthetic: boolean; data_source: string; min_horizon_months: number };
	analyst: { overview: string; thesis: string; developments: string[]; claims: Claim[] };
	devil: { counter_thesis: string; no_material_negative_finding: boolean; missing_information: string[]; claims: Claim[] };
	evaluation: Evaluation;
	engine: { analyst_mode: string; devil_mode: string; provider: string; model: string | null; prompt_version: string; errors: string[] };
	readiness_status: string;
	evidence: EvidenceItem[];
	created_at?: string;
}

export interface ResearchListItem {
	id: number;
	asset_id: number;
	asset_name: string;
	evaluator_status: string;
	created_at: string;
}

export interface SimulationSeriesPoint {
	date: string;
	value: number;
	nav: number;
	invested_cumulative: number;
	cash: number;
}

export interface SimulationRun {
	metrics: Record<string, string | number | null>;
	series: SimulationSeriesPoint[];
	trades: { date: string; source: string; price: number; amount: string; units: number }[];
	contributions: { date: string; source: string; amount: string }[];
}

export interface Simulation {
	simulation_id: number;
	scenario_type: string;
	amount_source: string;
	financially_available: boolean;
	market_path: string;
	evaluation_date: string;
	window: { start: string; end: string; months: number };
	inputs: Record<string, string | number>;
	data_period: { first_observation: string; last_observation: string; source: string; is_synthetic: boolean; observations_used: number };
	primary: { asset: { symbol: string; name: string }; run: SimulationRun };
	comparison: { asset: { symbol: string; name: string }; run: SimulationRun } | null;
	windows: { method: string; count: number; skipped: number; median_pct: number | null; best: { start: string; end: string; return_pct: number } | null; worst: { start: string; end: string; return_pct: number } | null } | null;
	labels: Record<string, string>;
	assumptions: string[];
	limitations: string[];
}

export interface Passport {
	passport_id: number;
	schema_version: string;
	reference_date: string;
	versions: Record<string, string | null>;
	investor_profile: Record<string, unknown>;
	objective: string;
	horizon: { months: number | null; basis: string };
	readiness: Readiness;
	recommendations?: Recommendations;
	timing: Timing;
	research: null | {
		analysis_id: number;
		asset: ResearchAnalysis['asset'];
		analyst_thesis: string;
		counter_thesis: string;
		no_material_negative_finding: boolean;
		evaluator_status: string;
		evidence_quality: Evaluation['evidence_quality'];
		material_risks: Evaluation['material_risks'];
		unconfirmed_concerns: string[];
		suitability_notes: string[];
		claim_counts: Record<string, number>;
	};
	simulation: null | { simulation_id: number; scenario_type: string; amount_source: string; financially_available: boolean; market_path: string; window: { start: string; end: string; months: number }; inputs: Record<string, string | number>; primary_metrics: Record<string, string | number | null>; labels: Record<string, string>; data_period: Record<string, unknown> };
	simulation_skipped_reason: string | null;
	evidence_references: { evidence_key: string; title: string; source_type: string; verification_status: string; publication_date: string | null; period: string | null; claims: string[] }[];
	data_status: { synthetic_data_used: boolean; synthetic_notice: string | null; stale_sources: unknown[]; market_context: string; as_of: string };
	missing_information: string[];
	assumptions: string[];
	review_conditions: { condition: string; trigger: string; severity: string }[];
	thesis_expiry: { statement: string; depends_on: string[]; review_by: string };
	disclaimer: string;
}

export interface PassportSummary {
	id: number;
	created_at: string;
	status: string;
	objective: string;
	timing_verdict_code: string;
	research_analysis_id: number | null;
	simulation_id: number | null;
	schema_version: string;
}

export interface ChatResponse {
	answer: string;
	mode: string;
	provider: string;
	grounding: string[];
	guardrails: string[];
}
