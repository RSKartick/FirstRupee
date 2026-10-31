<script lang="ts">
	import { goto } from '$app/navigation';
	import { api, ApiError } from '$lib/api/client';
	import type { ProfileOut, Readiness } from '$lib/api/types';
	import { loadProfiles, selectProfile, session } from '$lib/stores/session.svelte';
	import { dateLabel, inr, labelize, months, pct } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import Stat from '$lib/components/Stat.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let profile = $state<ProfileOut | null>(null);
	let readiness = $state<Readiness | null>(null);
	let loading = $state(false);
	let error = $state('');
	let confirming = $state(false);

	$effect(() => {
		const id = session.activeProfileId;
		void load(id);
	});

	async function load(id: number | null) {
		profile = null;
		readiness = null;
		error = '';
		if (!id) return;
		loading = true;
		try {
			const [p, r] = await Promise.all([api.getProfile(id), api.readiness(id)]);
			profile = p.profile;
			readiness = r.readiness;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Your profile could not be loaded.';
		} finally {
			loading = false;
		}
	}

	const m = $derived(readiness?.metrics ?? {});
	const text = (key: string) => (m[key] === null || m[key] === undefined ? null : String(m[key]));

	async function remove() {
		if (!profile) return;
		try {
			await api.deleteProfile(profile.id);
			await loadProfiles();
			if (session.profiles.length === 0) await goto('/onboarding');
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The profile could not be deleted.';
		} finally {
			confirming = false;
		}
	}
</script>

<svelte:head><title>Dashboard — FirstRupee</title></svelte:head>

{#if loading}
	<p class="muted" role="status">Calculating your readiness…</p>
{:else if !session.activeProfileId || session.profiles.length === 0}
	<div class="card space-y-4 text-center">
		<h1 class="text-xl font-semibold">No financial profile yet</h1>
		<p class="muted mx-auto max-w-lg">The readiness engine needs your income, outflows, savings breakdown, goal and questionnaire answers. It will not estimate them for you.</p>
		<a class="btn btn-primary" href="/onboarding?new=1">Start the assessment</a>
	</div>
{:else if error}
	<Notice tone="danger" title="Something went wrong">{error}</Notice>
{:else if profile && readiness}
	<div class="space-y-6">
		<section class="card grain">
			<div class="flex flex-wrap items-start justify-between gap-4">
				<div>
					<p class="muted">Welcome back</p>
					<h1 class="mt-1 text-2xl font-semibold tracking-tight">{profile.display_name}</h1>
					<div class="mt-3 flex flex-wrap items-center gap-2">
						<StatusBadge status={readiness.status} />
						<span class="text-[11px] text-muted">Rule set {readiness.rule_version} · as of {dateLabel(readiness.as_of)}</span>
						{#if profile.is_demo_clone}<span class="rounded-full border border-amber/40 bg-amber/10 px-2.5 py-0.5 text-[11px] uppercase text-amber">Fictional demo data</span>{/if}
						{#if readiness.completeness === 'INCOMPLETE'}<span class="rounded-full border border-danger/40 bg-danger/10 px-2.5 py-0.5 text-[11px] uppercase text-danger">Assessment incomplete</span>{/if}
					</div>
				</div>
				<div class="flex flex-wrap gap-2 no-print">
					<a class="btn" href="/onboarding?profile={profile.id}">Edit inputs</a>
					<a class="btn" href="/financial-dna">Financial DNA</a>
					{#if confirming}
						<button class="btn btn-danger" onclick={remove}>Confirm delete</button>
						<button class="btn" onclick={() => (confirming = false)}>Cancel</button>
					{:else}
						<button class="btn btn-ghost" onclick={() => (confirming = true)}>Delete profile and all derived records</button>
					{/if}
				</div>
			</div>
			<p class="mt-4 max-w-3xl text-[14px] leading-relaxed text-muted">{readiness.explanation}</p>
		</section>

		<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
			<Stat label="Monthly surplus" value={inr(text('monthly_surplus'))} tone={Number(m.monthly_surplus) > 0 ? 'success' : 'danger'} hint="Income minus every recorded outflow" />
			<Stat
				label="Emergency coverage"
				value={text('emergency_coverage_months') ? `${Number(m.emergency_coverage_months).toFixed(1)} months` : 'Unknown'}
				tone={text('emergency_coverage_months') && Number(m.emergency_coverage_months) >= 6 ? 'success' : 'warn'}
				hint="Liquid reserve ÷ essential expenses (target 6 months)"
			/>
			<Stat label="Free monthly money" value={inr(text('investable_monthly'))} tone="info" hint="After goal and reserve needs; zero if none" />
			<Stat label="Goal horizon" value={months(m.goal_horizon_months as number | null)} hint={profile.goal_name ?? 'No goal named'} />
		</div>

		<div class="grid gap-6 lg:grid-cols-3">
			<Card title="Constraints and blockers" subtitle="Each finding lists the inputs that produced it." class="lg:col-span-2">
				{#if readiness.findings.filter((f) => f.severity !== 'INFO').length === 0}
					<Notice tone="success" title="No constraints recorded">
						Cash flow, reserves, loans and horizon clear every documented guardrail. That permits research; it is not a recommendation to invest.
					</Notice>
				{:else}
					<div class="space-y-3">
						{#each readiness.findings.filter((f) => f.severity !== 'INFO') as f (f.code)}
							<article class="rounded-xl border border-line bg-raised/40 p-4">
								<div class="flex flex-wrap items-center gap-2">
									<StatusBadge status={f.severity === 'BLOCKER' ? 'NOT_READY' : 'PREPARATION'} text={f.severity === 'BLOCKER' ? 'Blocker' : 'Warning'} />
									<p class="text-[14px] font-medium">{f.label}</p>
								</div>
								<p class="muted mt-2">{f.detail}</p>
								<div class="mt-2 flex flex-wrap gap-1.5">
									{#each Object.entries(f.inputs) as [key, value] (key)}
										<span class="rounded border border-line bg-canvas px-1.5 py-0.5 text-[10px] tabular-nums text-muted">{labelize(key)}: {value}</span>
									{/each}
								</div>
							</article>
						{/each}
					</div>
				{/if}
			</Card>

			<Card title="Your goal and money map" subtitle="Total savings is not the same as investable money.">
				<dl class="kv">
					<div><dt>Goal</dt><dd>{profile.goal_name ?? 'Not stated'}</dd></div>
					<div><dt>Target</dt><dd>{inr(profile.goal_amount)}</dd></div>
					<div><dt>Deadline</dt><dd>{dateLabel(profile.goal_deadline)}</dd></div>
					<div><dt>Monthly need for goal</dt><dd>{inr(text('goal_monthly_need'))}</dd></div>
					<div><dt>Total savings</dt><dd>{inr(profile.total_savings)}</dd></div>
					<div><dt>Liquid savings</dt><dd>{inr(profile.liquid_savings)}</dd></div>
					<div><dt>Emergency reserve</dt><dd>{inr(profile.emergency_reserves)}</dd></div>
					<div><dt>Goal reserve</dt><dd>{inr(profile.goal_reserved_amount)}</dd></div>
					<div><dt>Free liquid money</dt><dd>{inr(text('unallocated_liquid'))}</dd></div>
					<div><dt>You designated per month</dt><dd>{inr(profile.monthly_investment_designated)}</dd></div>
					<div><dt>Loan EMI burden</dt><dd>{text('emi_burden') ? pct(Number(m.emi_burden) * 100) : 'n/a'}</dd></div>
				</dl>
			</Card>
		</div>

		<div class="grid gap-6 lg:grid-cols-2">
			<Card title="Suggested next steps" subtitle="Ordered by what would unblock the most.">
				<ol class="list-decimal space-y-2 pl-5 text-[13px] leading-relaxed">
					{#each readiness.improvement_steps as step, i (i)}<li>{step}</li>{/each}
				</ol>
				<div class="mt-5 grid gap-2 sm:grid-cols-2">
					<a class="btn" href="/explorer">Explore instrument categories</a>
					<a class="btn" href="/timing">Read the three clocks</a>
					<a class="btn" href="/simulator">Run a labelled scenario</a>
					<a class="btn" href="/research">Run a two-sided research analysis</a>
				</div>
			</Card>

			<Card title="Missing information and limits" subtitle="Reported, never assumed.">
				{#if readiness.missing_information.length === 0 && readiness.limitations.length === 0}
					<p class="muted">Nothing is missing from the inputs you provided.</p>
				{:else}
					<ul class="list-disc space-y-2 pl-5 text-[13px] leading-relaxed text-muted">
						{#each readiness.missing_information as item (item)}<li class="text-warn">Missing: {item}</li>{/each}
						{#each readiness.limitations as item (item)}<li>{item}</li>{/each}
					</ul>
				{/if}
				<p class="muted mt-5">{readiness.disclaimer}</p>
			</Card>
		</div>
	</div>
{:else}
	<Notice tone="info">Select a profile from the switcher in the header.</Notice>
{/if}
