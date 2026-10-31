<script lang="ts">
	import { goto } from '$app/navigation';
	import { api, ApiError } from '$lib/api/client';
	import type { PassportSummary } from '$lib/api/types';
	import { session } from '$lib/stores/session.svelte';
	import { dateLabel, labelize } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let passports = $state<PassportSummary[]>([]);
	let loading = $state(false);
	let generating = $state(false);
	let error = $state('');

	$effect(() => {
		const id = session.activeProfileId;
		void load(id);
	});

	async function load(id: number | null) {
		passports = [];
		error = '';
		if (!id) return;
		loading = true;
		try {
			passports = (await api.listPassports(id)).passports;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Your passports could not be loaded.';
		} finally {
			loading = false;
		}
	}

	async function generateQuickPassport() {
		const id = session.activeProfileId;
		if (!id) return;
		generating = true;
		error = '';
		try {
			const researchList = await api.listResearch(id);
			const latestResearchId = researchList.analyses.length > 0 ? researchList.analyses[0].id : undefined;
			const res = await api.generatePassport({
				profile_id: id,
				research_analysis_id: latestResearchId
			});
			await goto(`/passports/${res.passport.passport_id}`);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not generate Decision Passport.';
		} finally {
			generating = false;
		}
	}
</script>

<svelte:head><title>Decision Passports - FirstRupee</title></svelte:head>

<div class="space-y-6">
	<div class="rounded-lg border border-brand/40 bg-brand/10 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
		<div class="space-y-1">
			<span class="text-xs font-mono font-bold text-brand-soft uppercase">Feature Evolution</span>
			<p class="text-sm font-semibold text-ink">Schemes Hub is now live in place of Passports</p>
			<p class="text-xs text-muted">Explore sovereign Indian investment schemes (PPF, NPS, SSY, SCSS, SGB) with personalized eligibility evaluation and live compounding simulators.</p>
		</div>
		<a class="btn btn-primary whitespace-nowrap !px-4 !py-2 text-xs font-semibold" href="/schemes">
			Open Schemes Hub &rarr;
		</a>
	</div>

	<section class="card grain">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<p class="text-[12px] font-semibold uppercase tracking-[0.18em] text-brand-soft">Decision Passports</p>
				<h1 class="mt-2 text-2xl font-semibold tracking-tight">Your decisions, on the record</h1>
				<p class="muted mt-2 max-w-3xl">
					A passport captures your readiness, numerical portfolio recommendations, the thesis and counter-thesis, the timing rationale,
					any scenario you attached, the evidence cited and the conditions that should trigger a review. It is a stored snapshot.
				</p>
			</div>
			{#if session.activeProfileId}
				<button class="btn btn-primary" onclick={generateQuickPassport} disabled={generating}>
					{generating ? 'Generating passport...' : 'Generate New Passport'}
				</button>
			{/if}
		</div>
	</section>

	{#if error}<Notice tone="danger">{error}</Notice>{/if}
	{#if loading}<p class="muted" role="status">Loading passports...</p>{/if}

	{#if !session.activeProfileId}
		<div class="card space-y-3 text-center"><p class="muted">A passport records who a decision belongs to, so it needs a profile.</p><a class="btn btn-primary" href="/onboarding?new=1">Start the assessment</a></div>
	{:else if !loading && passports.length === 0}
		<div class="card space-y-3 text-center">
			<p class="muted">No passports recorded for this profile yet. Generate a snapshot now or run a two-sided research analysis first.</p>
			<div class="flex flex-wrap justify-center gap-3">
				<button class="btn btn-primary" onclick={generateQuickPassport} disabled={generating}>
					{generating ? 'Generating passport...' : 'Generate Decision Passport Now'}
				</button>
				<a class="btn" href="/research">Go to Research Lab</a>
			</div>
		</div>
	{:else}
		<Card title="{passports.length} passport{passports.length === 1 ? '' : 's'}" subtitle="Newest first. Click Open to inspect or print any snapshot.">
			<ul class="space-y-3">
				{#each passports as p (p.id)}
					<li class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-raised/40 p-4">
						<div>
							<p class="font-medium">Decision Passport #{p.id}</p>
							<p class="muted mt-0.5 text-[12px]">{dateLabel(p.created_at)} · {labelize(p.timing_verdict_code)}</p>
							<p class="muted mt-0.5 text-[12px]">{p.objective}</p>
						</div>
						<div class="flex items-center gap-2">
							<StatusBadge status={p.status} />
							<a class="btn" href="/passports/{p.id}">Open</a>
						</div>
					</li>
				{/each}
			</ul>
		</Card>
	{/if}
</div>
