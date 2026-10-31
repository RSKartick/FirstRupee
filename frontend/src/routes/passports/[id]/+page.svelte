<script lang="ts">
	import { page } from '$app/state';
	import { api, ApiError } from '$lib/api/client';
	import type { Passport } from '$lib/api/types';
	import { dateLabel, inr, labelize, pct } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let passport = $state<Passport | null>(null);
	let error = $state('');

	$effect(() => {
		const id = Number(page.params.id);
		void load(id);
	});

	async function load(id: number) {
		passport = null;
		error = '';
		try {
			passport = (await api.getPassport(id)).passport;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'This passport could not be opened.';
		}
	}

	const profileName = $derived(String(passport?.investor_profile.display_name ?? 'Investor'));
	const metrics = $derived(passport?.readiness.metrics ?? {});
</script>

<svelte:head><title>Decision Passport — FirstRupee</title></svelte:head>

{#if error}
	<Notice tone="danger" title="Not available">{error}</Notice>
{:else if !passport}
	<p class="muted" role="status">Loading the passport…</p>
{:else}
	<div class="mx-auto max-w-4xl space-y-6">
		<div class="flex flex-wrap items-center justify-between gap-3 no-print">
			<a class="muted" href="/passports">← All passports</a>
			<button class="btn" onclick={() => window.print()}>Print or save as PDF</button>
		</div>

		<section class="card grain">
			<div class="flex flex-wrap items-start justify-between gap-4">
				<div>
					<p class="text-[12px] font-semibold uppercase tracking-[0.18em] text-brand-soft">Decision Passport #{passport.passport_id}</p>
					<h1 class="mt-2 text-2xl font-semibold tracking-tight">{profileName}</h1>
					<p class="muted mt-1">Reference date {dateLabel(passport.reference_date)} · schema {passport.schema_version}</p>
				</div>
				<div class="text-right"><StatusBadge status={passport.readiness.status} /><p class="muted mt-1 text-[11px]">Rule set {passport.readiness.rule_version}</p></div>
			</div>
			<p class="muted mt-4">A stored snapshot. Everything below was copied from the inputs and engine outputs at the time it was created.</p>
			{#if passport.data_status.synthetic_data_used}
				<div class="mt-4"><Notice tone="warn" title="Synthetic demonstration data is used">{passport.data_status.synthetic_notice}</Notice></div>
			{/if}
		</section>

		<Card title="1–2 · Investor profile and financial readiness">
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
				<div class="rounded-xl border border-line bg-raised/50 p-4"><p class="muted text-[11px] uppercase">Readiness</p><p class="mt-1 font-semibold">{labelize(passport.readiness.status)}</p></div>
				<div class="rounded-xl border border-line bg-raised/50 p-4"><p class="muted text-[11px] uppercase">Monthly surplus</p><p class="mt-1 font-semibold">{inr(metrics.monthly_surplus as string)}</p></div>
				<div class="rounded-xl border border-line bg-raised/50 p-4"><p class="muted text-[11px] uppercase">Emergency coverage</p><p class="mt-1 font-semibold">{metrics.emergency_coverage_months ? `${metrics.emergency_coverage_months} months` : 'Unknown'}</p></div>
				<div class="rounded-xl border border-line bg-raised/50 p-4"><p class="muted text-[11px] uppercase">Tolerance / capacity</p><p class="mt-1 font-semibold">{labelize(String(metrics.risk_tolerance_band))} / {labelize(String(metrics.risk_capacity_band))}</p></div>
			</div>
			<p class="mt-4 text-[13px] leading-relaxed">{passport.readiness.explanation}</p>
			{#if passport.readiness.blockers.length > 0}
				<h3 class="mt-4 text-[12px] font-semibold uppercase tracking-wider text-muted">Blockers at the time</h3>
				<ul class="mt-2 list-disc space-y-1 pl-5 text-[13px]">{#each passport.readiness.blockers as item (item)}<li>{item}</li>{/each}</ul>
			{/if}
		</Card>

		<Card title="3–4 · Objective and horizon">
			<dl class="kv">
				<div><dt>Stated objective</dt><dd>{passport.objective}</dd></div>
				<div><dt>Horizon</dt><dd>{passport.horizon.months === null ? 'Not set' : `${passport.horizon.months} months`} <span class="muted">({labelize(passport.horizon.basis)})</span></dd></div>
			</dl>
		</Card>

		<div class="grid gap-6 lg:grid-cols-2">
			<Card title="5 · Research thesis">
				{#if passport.research}<p class="text-[13px] leading-relaxed">{passport.research.analyst_thesis}</p>{:else}<p class="muted">No research analysis was attached. No investment thesis is recorded.</p>{/if}
			</Card>
			<Card title="6 · Counter-thesis">
				{#if passport.research}<p class="text-[13px] leading-relaxed">{passport.research.counter_thesis}</p>{:else}<p class="muted">No Devil’s Advocate output was attached.</p>{/if}
			</Card>
		</div>

		<Card title="7 · Main risks and evaluator status">
			{#if passport.research}
				<div class="mb-3 flex flex-wrap items-center gap-2"><StatusBadge status={passport.research.evaluator_status} /><span class="muted">Evidence quality {passport.research.evidence_quality.score}/100 · {passport.research.evidence_quality.label}</span></div>
				{#if passport.research.material_risks.length === 0}<p class="muted">No stored value breaches a documented risk rule.</p>{:else}
					<ul class="list-disc space-y-1 pl-5 text-[13px]">{#each passport.research.material_risks as r (r.code)}<li>{r.label} — {r.observed_value} ({r.period}), source {r.evidence_key}</li>{/each}</ul>
				{/if}
			{:else}<p class="muted">No research was attached.</p>{/if}
		</Card>

		<Card title="8 · Timing explanation">
			<p class="text-[13px] leading-relaxed"><strong>{labelize(passport.timing.verdict_code)}.</strong> {passport.timing.verdict}</p>
			<div class="mt-4 grid gap-3 sm:grid-cols-3">
				{#each [passport.timing.clocks.money, passport.timing.clocks.goal, passport.timing.clocks.market] as clock (clock.name)}
					<div class="rounded-xl border border-line bg-raised/40 p-3">
						<div class="flex items-center justify-between gap-2"><p class="text-[12px] font-semibold">{clock.name}</p><StatusBadge status={clock.status} /></div>
						<p class="muted mt-1">{clock.headline}</p>
					</div>
				{/each}
			</div>
		</Card>

		<Card title="9 · Scenario attached">
			{#if passport.simulation}
				<dl class="kv">
					<div><dt>Scenario</dt><dd>{labelize(passport.simulation.scenario_type)} · {labelize(passport.simulation.market_path)}</dd></div>
					<div><dt>Amounts</dt><dd>{passport.simulation.financially_available ? 'From the investor’s profile' : 'Hypothetical — not financially available'}</dd></div>
					<div><dt>Window</dt><dd>{dateLabel(passport.simulation.window.start)} → {dateLabel(passport.simulation.window.end)}</dd></div>
					<div><dt>Ending value</dt><dd>{inr(passport.simulation.primary_metrics.ending_value as string)}</dd></div>
					<div><dt>Money put in</dt><dd>{inr(passport.simulation.primary_metrics.total_contributions as string)}</dd></div>
					<div><dt>Time-weighted return</dt><dd>{pct(passport.simulation.primary_metrics.time_weighted_return_pct, 2)}</dd></div>
					<div><dt>Maximum drawdown</dt><dd>{pct(passport.simulation.primary_metrics.max_drawdown_pct, 1)}</dd></div>
				</dl>
			{:else}
				<Notice tone="info" title="No investment simulation attached">{passport.simulation_skipped_reason ?? 'No simulation was attached to this passport.'}</Notice>
			{/if}
		</Card>

		<Card title="10–12 · Evidence, timestamps and missing information">
			<div class="space-y-3">
				{#each passport.evidence_references as ev (ev.evidence_key)}
					<article class="rounded-xl border border-line bg-raised/40 p-4">
						<div class="flex flex-wrap items-center gap-2">
							<code class="text-[11px] text-brand-soft">{ev.evidence_key}</code>
							<span class="rounded-full border border-amber/40 px-2 py-0.5 text-[10px] uppercase text-amber">{ev.verification_status}</span>
							<span class="ml-auto text-[11px] text-muted">Published {dateLabel(ev.publication_date)}</span>
						</div>
						<p class="mt-2 text-[13px] font-medium">{ev.title}</p>
						<ul class="muted mt-1 list-disc pl-5">{#each ev.claims as claim (claim)}<li>{claim}</li>{/each}</ul>
					</article>
				{:else}
					<p class="muted">No evidence identifiers were cited.</p>
				{/each}
			</div>
			<h3 class="mt-5 text-[12px] font-semibold uppercase tracking-wider text-muted">Missing information</h3>
			<ul class="mt-2 list-disc space-y-1 pl-5 text-[13px] text-warn">{#each passport.missing_information as item (item)}<li>{item}</li>{/each}</ul>
		</Card>

		<Card title="13 · Assumptions and versions">
			<ul class="list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed">{#each passport.assumptions as item (item)}<li>{item}</li>{/each}</ul>
			<dl class="kv mt-4">
				{#each Object.entries(passport.versions) as [key, value] (key)}<div><dt>{labelize(key)} version</dt><dd>{value ?? 'not used'}</dd></div>{/each}
			</dl>
		</Card>

		<Card title="14 · Review conditions and thesis expiry" subtitle={`Review by ${dateLabel(passport.thesis_expiry.review_by)}`}>
			<p class="text-[13px] leading-relaxed">{passport.thesis_expiry.statement}</p>
			<div class="mt-4 space-y-2.5">
				{#each passport.review_conditions as rc, i (i)}
					<div class="rounded-xl border border-line bg-raised/40 p-4">
						<div class="flex flex-wrap items-center gap-2"><span class="text-[10px] uppercase text-muted">{labelize(rc.severity)}</span><p class="text-[13px] font-medium">{rc.condition}</p></div>
						<p class="muted mt-1">Trigger: {rc.trigger}</p>
					</div>
				{/each}
			</div>
			<h3 class="mt-5 text-[12px] font-semibold uppercase tracking-wider text-muted">This thesis depends on</h3>
			<ul class="mt-2 list-disc space-y-1 pl-5 text-[13px]">{#each passport.thesis_expiry.depends_on as item (item)}<li>{item}</li>{/each}</ul>
		</Card>

		<Card title="Disclaimer"><p class="muted">{passport.disclaimer}</p></Card>
	</div>
{/if}
