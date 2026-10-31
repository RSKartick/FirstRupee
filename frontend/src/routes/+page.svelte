<script lang="ts">
	import { goto } from '$app/navigation';
	import { applySignIn, loadProfiles, session } from '$lib/stores/session.svelte';
	import { api, ApiError } from '$lib/api/client';
	import { Scale, FlaskConical, ShieldCheck } from 'lucide-svelte';

	let busy = $state('');
	let error = $state('');

	async function loadDemo(key: 'rahul' | 'priya' | 'arjun') {
		busy = key;
		error = '';
		try {
			const res = await api.loadDemo(key);
			applySignIn(res.user, res.csrf_token);
			await loadProfiles(res.profile_id);
			await goto('/dashboard');
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The workspace could not be created.';
		} finally {
			busy = '';
		}
	}
</script>

<svelte:head><title>FirstRupee - Understand your money before you risk it</title></svelte:head>

<div class="space-y-16">
	<section class="card !p-10 sm:!p-14">
		<div class="max-w-3xl">
			<p class="text-[12px] font-semibold uppercase tracking-[0.2em] text-brand-soft">Educational decision support</p>
			<h1 class="mt-4 text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
				Understand your money<span class="block text-brand-soft">before you risk it.</span>
			</h1>
			<p class="mt-6 max-w-2xl text-[15px] leading-relaxed text-muted">
				Most platforms help you pick an investment. FirstRupee first looks at you: your cash flow, reserves, loans, goal date and
				the difference between how much risk you are willing to take and how much you can afford to lose. It then tells you
				honestly whether investing is appropriate yet, and shows the evidence for and against an instrument.
			</p>
			<p class="mt-3 text-sm font-medium text-brand-soft">Invest with understanding, not uncertainty.</p>

			<div class="mt-9 flex flex-wrap items-center gap-3">
				<a class="btn btn-primary !px-5 !py-3" href={session.user ? '/onboarding' : '/register?next=/onboarding'}>Understand My Financial DNA</a>
				<a class="btn !px-5 !py-3" href="/login">I already have an account</a>
			</div>
			<p class="muted mt-4">Email and password accounts are optional for the demo. No PAN, Aadhaar, bank or brokerage credentials are requested.</p>
		</div>
	</section>

	<section class="grid gap-5 md:grid-cols-3">
		<article class="card">
			<Scale size={20} class="text-azure" />
			<h2 class="mt-3 text-[15px] font-semibold">Readiness, not hype</h2>
			<p class="muted mt-2">Deterministic rules separate NOT READY, PREPARATION and READY TO EXPLORE, and show the exact inputs behind every finding.</p>
		</article>
		<article class="card">
			<FlaskConical size={20} class="text-azure" />
			<h2 class="mt-3 text-[15px] font-semibold">Two-sided research</h2>
			<p class="muted mt-2">A Research Analyst builds the case and a Devil's Advocate challenges it. A deterministic evaluator checks every cited claim.</p>
		</article>
		<article class="card">
			<ShieldCheck size={20} class="text-azure" />
			<h2 class="mt-3 text-[15px] font-semibold">Reproducible records</h2>
			<p class="muted mt-2">Decision Passports freeze the inputs, versions, evidence and review conditions, so a later rule change cannot rewrite them.</p>
		</article>
	</section>

	<section class="card">
		<div class="card-head">
			<div>
				<h2>Explore instant investor case studies (or build your own profile above)</h2>
				<p class="muted mt-1">Each button creates a private workspace pre-loaded with a realistic Indian household profile so you can immediately inspect NOT READY, Beginner Ready, and Experienced Preparation recommendations.</p>
			</div>
		</div>
		<div class="grid gap-4 md:grid-cols-3">
			<div class="rounded-xl border border-line bg-raised/40 p-5">
				<p class="font-semibold">Rahul - Constrained Early-Career Saver (NOT READY)</p>
				<p class="muted mt-2">Rs 30,000 income, Rs 4,000 surplus, 1 month of essentials in reserve and a 10-month goal. Shows why liquid reserves come before market exposure.</p>
				<button class="btn btn-primary mt-4" onclick={() => loadDemo('rahul')} disabled={busy !== ''}>
					{busy === 'rahul' ? 'Opening workspace...' : 'Open Rahul Workspace'}
				</button>
			</div>
			<div class="rounded-xl border border-line bg-raised/40 p-5">
				<p class="font-semibold">Priya - Ready to Explore (Beginner Mode)</p>
				<p class="muted mt-2">Rs 80,000 income, Rs 40,000 surplus, 8.3 months of reserves and a 10-year goal. Shows beginner-friendly plain-English textual and numerical allocations.</p>
				<button class="btn btn-primary mt-4" onclick={() => loadDemo('priya')} disabled={busy !== ''}>
					{busy === 'priya' ? 'Opening workspace...' : 'Open Priya Workspace'}
				</button>
			</div>
			<div class="rounded-xl border border-line bg-raised/40 p-5">
				<p class="font-semibold">Arjun - Experienced Portfolio Builder (Quant Mode)</p>
				<p class="muted mt-2">Rs 1,50,000 income, zero debt, Rs 2,00,000 unallocated liquid capital, and Experienced mode enabled. Classifies as PREPARATION due to an ambitious Rs 1.2 Cr retirement goal that needs slightly more than his monthly surplus.</p>
				<button class="btn btn-primary mt-4" onclick={() => loadDemo('arjun')} disabled={busy !== ''}>
					{busy === 'arjun' ? 'Opening workspace...' : 'Open Arjun Workspace'}
				</button>
			</div>
		</div>
		{#if error}<p class="field-error mt-4" role="alert">{error}</p>{/if}
	</section>

	<section class="card">
		<h2 class="text-[15px] font-semibold">How it works</h2>
		<ol class="mt-4 grid gap-4 md:grid-cols-4">
			<li><p class="text-[11px] font-semibold tracking-[0.2em] text-brand-soft">01</p><p class="mt-1 font-medium">Describe your finances</p><p class="muted mt-1">Income, outflows, reserves, loans, goal and questionnaire, each captured separately so no rupee is counted twice.</p></li>
			<li><p class="text-[11px] font-semibold tracking-[0.2em] text-brand-soft">02</p><p class="mt-1 font-medium">Check readiness</p><p class="muted mt-1">Blockers, warnings and missing information are listed, with the next steps that would change the result.</p></li>
			<li><p class="text-[11px] font-semibold tracking-[0.2em] text-brand-soft">03</p><p class="mt-1 font-medium">Research and challenge</p><p class="muted mt-1">Evidence-checked analyses, timing and scenario simulations grounded in live historical NSE &amp; AMFI market data and audited filings.</p></li>
			<li><p class="text-[11px] font-semibold tracking-[0.2em] text-brand-soft">04</p><p class="mt-1 font-medium">Record the decision</p><p class="muted mt-1">A Decision Passport captures the reasoning and the conditions under which it should be reviewed.</p></li>
		</ol>
	</section>
</div>
