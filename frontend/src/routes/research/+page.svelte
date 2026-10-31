<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, ApiError } from '$lib/api/client';
	import type { AssetSummary, CheckedClaim, ResearchAnalysis, ResearchListItem } from '$lib/api/types';
	import { session } from '$lib/stores/session.svelte';
	import { dateLabel, labelize, readinessTone } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let assets = $state<AssetSummary[]>([]);
	let assetId = $state('');
	let analysis = $state<ResearchAnalysis | null>(null);
	let history = $state<ResearchListItem[]>([]);
	let busy = $state(false);
	let passportBusy = $state(false);
	let error = $state('');
	let loadedFor = $state<number | null>(null);

	$effect(() => {
		const id = session.activeProfileId;
		void load(id);
	});

	async function load(id: number | null) {
		analysis = null;
		history = [];
		error = '';
		if (!id) return;
		loadedFor = id;
		try {
			const [catalogue, past] = await Promise.all([api.assets(), api.listResearch(id)]);
			assets = catalogue.assets;
			history = past.analyses;
			const requested = page.url.searchParams.get('asset');
			if (requested && assets.some((a) => String(a.id) === requested)) assetId = requested;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Research could not be loaded.';
		}
	}

	async function run() {
		const pid = session.activeProfileId;
		if (!pid || !assetId) return;
		busy = true;
		error = '';
		analysis = null;
		try {
			const res = await api.runResearch({ profile_id: pid, asset_id: Number(assetId) });
			if (loadedFor === pid) analysis = res.analysis;
			history = (await api.listResearch(pid)).analyses;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The analysis could not be completed.';
		} finally {
			busy = false;
		}
	}

	async function openPast(id: number) {
		error = '';
		try {
			analysis = (await api.getResearch(id)).analysis;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'That analysis could not be opened.';
		}
	}

	async function generatePassport() {
		const pid = session.activeProfileId;
		if (!pid || !analysis) return;
		passportBusy = true;
		error = '';
		try {
			const res = await api.generatePassport({ profile_id: pid, research_analysis_id: analysis.analysis_id });
			await goto(`/passports/${res.passport.passport_id}`);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The Decision Passport could not be generated.';
		} finally {
			passportBusy = false;
		}
	}

	const evaluation = $derived(analysis?.evaluation ?? null);
	const claimStatusTone = (check: CheckedClaim) =>
		check.status === 'CONTRADICTED' || check.status === 'INVALID_REFERENCE' || check.status === 'UNSUPPORTED'
			? 'danger'
			: check.status === 'HYPOTHESIS'
				? 'neutral'
				: check.status === 'SUPPORTED'
					? 'success'
					: 'warn';
</script>

<svelte:head><title>Research — FirstRupee</title></svelte:head>

{#if !session.activeProfileId}
	<div class="card space-y-3 text-center">
		<p class="muted">Research is anchored to your readiness result, so the Devil’s Advocate can comment on your real constraints.</p>
		<a class="btn btn-primary" href="/onboarding?new=1">Start the assessment</a>
	</div>
{:else}
	<div class="space-y-6">
		<section class="card grain">
			<p class="text-[12px] font-semibold uppercase tracking-[0.18em] text-brand-soft">AI research assistant</p>
			<h1 class="mt-2 text-2xl font-semibold tracking-tight">Two analysts, one set of records</h1>
			<p class="muted mt-2 max-w-3xl">
				The Research Analyst builds the case from stored evidence. The Devil’s Advocate challenges it from the same records and is not
				allowed to invent negatives for balance. A deterministic evaluator then checks each claim against the stored data. Neither
				panel produces a buy or sell signal.
			</p>
			<div class="mt-5 grid gap-3 sm:grid-cols-[1fr_auto]">
				<div>
					<label class="field-label" for="asset">Instrument</label>
					<select id="asset" class="field-input" bind:value={assetId}>
						<option value="">Choose an instrument…</option>
						{#each assets as a (a.id)}<option value={String(a.id)}>{a.name} · {a.symbol}</option>{/each}
					</select>
				</div>
				<div class="flex items-end">
					<button class="btn btn-primary w-full" onclick={run} disabled={busy || !assetId}>{busy ? 'Analysing…' : 'Run analysis'}</button>
				</div>
			</div>
			{#if error}<p class="field-error mt-3" role="alert">{error}</p>{/if}
		</section>

		{#if busy}<p class="muted" role="status">Running the Research Analyst and Devil’s Advocate, then verifying every claim…</p>{/if}

		{#if history.length > 0}
			<Card title="Earlier analyses for this profile">
				<ul class="space-y-2">
					{#each history as item (item.id)}
						<li class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-raised/40 px-3 py-2 text-[13px]">
							<span>{item.asset_name} · {dateLabel(item.created_at)}</span>
							<span class="flex items-center gap-2"><StatusBadge status={item.evaluator_status} /><button class="btn !py-1 text-[12px]" onclick={() => openPast(item.id)}>Open</button></span>
						</li>
					{/each}
				</ul>
			</Card>
		{/if}

		{#if analysis && evaluation}
			<Card title={analysis.asset.name} subtitle={`${analysis.asset.symbol} · analysis #${analysis.analysis_id} · reference date ${dateLabel(analysis.as_of)}`}>
				<div class="flex flex-wrap items-center gap-3">
					<StatusBadge status={evaluation.status} />
					<span class="muted">Analyst: {analysis.engine.analyst_mode === 'LLM' ? `language model (${analysis.engine.provider})` : 'rule-based (no language model configured)'} · Devil’s Advocate: {analysis.engine.devil_mode === 'LLM' ? 'language model' : 'rule-based'}</span>
					<button class="btn btn-primary ml-auto no-print" onclick={generatePassport} disabled={passportBusy}>{passportBusy ? 'Generating…' : 'Generate Decision Passport'}</button>
				</div>
				{#if evaluation.data_status.synthetic_evidence_used}
					<div class="mt-4"><Notice tone="warn" title="Synthetic demonstration evidence">Every record used here is synthetic. The checks demonstrate the process; they are not independent verification of any real company or fund.</Notice></div>
				{/if}
				{#if analysis.engine.errors.length > 0}
					<div class="mt-3"><Notice tone="info" title="Engine notes">{#each analysis.engine.errors as note (note)}<p>{note}</p>{/each}</Notice></div>
				{/if}
			</Card>

			<div class="grid gap-6 lg:grid-cols-2">
				<Card title="Research Analyst" subtitle="Positive evidence and the case built from it.">
					<div class="space-y-4 text-[13px] leading-relaxed">
						<div><p class="muted text-[11px] uppercase tracking-wider">Overview</p><p class="mt-1">{analysis.analyst.overview}</p></div>
						{#if analysis.analyst.developments.length > 0}
							<div><p class="muted text-[11px] uppercase tracking-wider">Developments in the records</p><ul class="mt-1 list-disc space-y-1 pl-5">{#each analysis.analyst.developments as item (item)}<li>{item}</li>{/each}</ul></div>
						{/if}
						<div class="rounded-xl border border-brand/30 bg-brand/5 p-4">
							<p class="text-[11px] uppercase tracking-wider text-brand-soft">Investment thesis (conditional)</p>
							<p class="mt-1.5">{analysis.analyst.thesis}</p>
						</div>
					</div>
				</Card>

				<Card title="Devil’s Advocate" subtitle="Challenges the thesis. If nothing material is established, it says so.">
					<div class="space-y-4 text-[13px] leading-relaxed">
						{#if analysis.devil.no_material_negative_finding}
							<Notice tone="success" title="No material negative finding established">That is not the same as no risk. The missing information below still limits the assessment.</Notice>
						{/if}
						<div class="rounded-xl border border-danger/30 bg-danger/5 p-4"><p class="text-[11px] uppercase tracking-wider text-danger">Counter-thesis</p><p class="mt-1.5">{analysis.devil.counter_thesis}</p></div>
						<div><p class="muted text-[11px] uppercase tracking-wider">Missing information</p><ul class="mt-1 list-disc space-y-1 pl-5 text-muted">{#each analysis.devil.missing_information as item (item)}<li>{item}</li>{/each}</ul></div>
					</div>
				</Card>
			</div>

			<Card title="Final evidence evaluation" subtitle={`Evaluator rules ${evaluation.evaluator_version}. Every factual claim from both panels is checked.`}>
				<div class="grid gap-3 sm:grid-cols-3">
					<div class="rounded-xl border border-line bg-raised/50 p-4"><p class="muted text-[11px] uppercase">Evidence quality</p><p class="mt-1 text-xl font-semibold">{evaluation.evidence_quality.score}/100</p><p class="muted mt-1">{evaluation.evidence_quality.label}</p></div>
					<div class="rounded-xl border border-line bg-raised/50 p-4"><p class="muted text-[11px] uppercase">Claims checked</p><p class="mt-1 text-xl font-semibold">{evaluation.counts.total_factual_claims ?? 0}</p><p class="muted mt-1">{evaluation.counts.hypotheses ?? 0} labelled as hypotheses</p></div>
					<div class="rounded-xl border border-line bg-raised/50 p-4"><p class="muted text-[11px] uppercase">Reference date</p><p class="mt-1 text-xl font-semibold">{dateLabel(evaluation.data_status.reference_date)}</p><p class="muted mt-1">Freshness is measured from this date</p></div>
				</div>
				<p class="muted mt-4">{evaluation.evidence_quality.explanation}</p>

				<div class="table-wrap mt-5">
					<table class="data-table">
						<thead><tr><th>Side</th><th>Claim</th><th>Type</th><th>Evidence key</th><th>Status</th><th>Why</th></tr></thead>
						<tbody>
							{#each evaluation.claim_checks as check, i (i)}
								<tr>
									<td class="muted">{check.side === 'ANALYST' ? 'Analyst' : 'Devil'}</td>
									<td>{check.claim}</td>
									<td class="muted">{labelize(check.claim_type)}</td>
									<td><code class="text-[11px] text-brand-soft">{check.evidence_key ?? '—'}</code></td>
									<td><StatusBadge status={check.status} text={labelize(check.status)} /></td>
									<td class="muted">{check.reasons.join(' ')}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</Card>

			<div class="grid gap-6 lg:grid-cols-2">
				<Card title="Material risks (rule-confirmed)" subtitle="Only stored numbers that breach a documented rule. Text alone never creates a risk.">
					{#if evaluation.material_risks.length === 0}
						<p class="muted">No stored value breaches a documented risk rule.</p>
					{:else}
						<ul class="space-y-3">
							{#each evaluation.material_risks as risk (risk.code)}
								<li class="rounded-lg border border-danger/30 bg-danger/5 p-3 text-[13px]">
									<p class="font-medium">{risk.label}</p>
									<p class="muted mt-1">Observed {risk.observed_value} ({risk.period}), threshold {risk.threshold}. Source {risk.evidence_key} · {labelize(risk.evidence_status)}.</p>
								</li>
							{/each}
						</ul>
					{/if}
					{#if evaluation.unconfirmed_concerns.length > 0}
						<h3 class="mt-5 text-[12px] font-semibold uppercase tracking-wider text-muted">Unconfirmed concerns</h3>
						<ul class="mt-2 list-disc space-y-1 pl-5 text-[13px] text-muted">{#each evaluation.unconfirmed_concerns as item (item)}<li>{item}</li>{/each}</ul>
					{/if}
				</Card>

				<Card title="Suitability, data gaps and uncertainty">
					<ul class="list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed">
						{#each evaluation.suitability_notes as item (item)}<li>{item}</li>{/each}
						{#each evaluation.missing_data as item (item)}<li class="text-warn">{item}</li>{/each}
						{#each evaluation.unresolved_uncertainties as item (item)}<li class="muted">{item}</li>{/each}
					</ul>
					{#if evaluation.data_status.stale_sources.length > 0}
						<p class="muted mt-3">Older than its freshness limit: {evaluation.data_status.stale_sources.map((s) => s.evidence_key).join(', ')}.</p>
					{/if}
					<p class="muted mt-4">{evaluation.advisory_notice}</p>
				</Card>
			</div>
		{/if}
	</div>
{/if}
