<script lang="ts">
	import { session } from '$lib/stores/session.svelte';
	import { Scale, FlaskConical, Landmark, ArrowRight, ShieldCheck, TrendingUp } from 'lucide-svelte';

	const SCHEME_HIGHLIGHTS = [
		{ name: 'Public Provident Fund (PPF)', rate: '7.10% p.a.', tax: 'EEE (Sec 80C)', tenure: '15 Years', note: 'Triple tax-exempt sovereign compounding.' },
		{ name: 'National Pension System (NPS)', rate: '~10.20% p.a.', tax: '80CCD(1B)', tenure: 'Till Age 60', note: 'Extra ₹50,000 tax deduction over and above 80C.' },
		{ name: 'Sukanya Samriddhi Yojana (SSY)', rate: '8.20% p.a.', tax: 'EEE (Sec 80C)', tenure: '21 Years', note: 'Highest guaranteed sovereign return for girl child goals.' },
		{ name: 'Senior Citizens Savings (SCSS)', rate: '8.20% p.a.', tax: 'Sec 80C', tenure: '5 Years', note: 'Quarterly guaranteed cash flow backed by Government of India.' }
	];
</script>

<svelte:head><title>FirstRupee - Real Market Intelligence &amp; Statutory Schemes</title></svelte:head>

<div class="space-y-12">
	<!-- Hero Section -->
	<section class="card !p-8 sm:!p-12">
		<div class="max-w-3xl">
			<div class="mb-5 flex items-center gap-3">
				<img src="/logo.png" alt="FirstRupee Logo" class="h-10 w-auto object-contain" />
				<span class="rounded border border-brand/40 bg-brand/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-brand-soft">
					Real-Time Decision Intelligence
				</span>
			</div>
			<h1 class="mt-4 text-3xl font-bold leading-[1.15] tracking-tight sm:text-5xl text-ink">
				Understand your money <span class="block text-brand-soft">before you risk it.</span>
			</h1>
			<p class="mt-5 max-w-2xl text-[15px] leading-relaxed text-muted">
				Most platforms push products. FirstRupee assesses you: your verified cash flow, liquid emergency buffers, debt drag, goal horizons,
				and the difference between risk tolerance and risk capacity. Powered exclusively by live NSE market feeds, AMFI mutual fund NAVs,
				and official Indian government statutory schemes.
			</p>

			<div class="mt-8 flex flex-wrap items-center gap-3">
				<a class="btn btn-primary !px-5 !py-3 text-sm font-semibold" href={session.user ? '/onboarding' : '/register?next=/onboarding'}>
					Start Your Financial Assessment <ArrowRight size={16} />
				</a>
				<a class="btn !px-5 !py-3 text-sm font-semibold" href="/schemes">
					<Landmark size={16} /> Explore Government Schemes
				</a>
				{#if !session.user}
					<a class="btn btn-ghost !px-4 !py-3 text-sm text-muted hover:text-ink" href="/login">
						Sign In
					</a>
				{/if}
			</div>
			<p class="muted mt-3 text-xs">
				Strictly zero fictional data. Grounded in real daily NSE prices, AMFI NAVs (api.mfapi.in), and audited corporate filings.
			</p>
		</div>
	</section>

	<!-- 3 Core Institutional Pillars -->
	<section class="grid gap-4 md:grid-cols-3">
		<article class="card p-5">
			<div class="rounded border border-brand/40 bg-brand/10 p-2 w-fit text-brand-soft mb-3">
				<Scale size={20} />
			</div>
			<h2 class="text-base font-semibold text-ink">Deterministic Guardrails</h2>
			<p class="muted mt-1.5 text-xs leading-relaxed">
				Deterministic rules separate NOT READY, PREPARATION, and READY TO EXPLORE. Your emergency reserves and loan solvency always outrank market hype.
			</p>
		</article>
		<article class="card p-5">
			<div class="rounded border border-brand/40 bg-brand/10 p-2 w-fit text-brand-soft mb-3">
				<FlaskConical size={20} />
			</div>
			<h2 class="text-base font-semibold text-ink">Two-Sided Research Lab</h2>
			<p class="muted mt-1.5 text-xs leading-relaxed">
				A Research Analyst builds the investment case and an aggressive Devil's Advocate challenges it, checking audited metrics from corporate annual filings.
			</p>
		</article>
		<article class="card p-5">
			<div class="rounded border border-brand/40 bg-brand/10 p-2 w-fit text-brand-soft mb-3">
				<Landmark size={20} />
			</div>
			<h2 class="text-base font-semibold text-ink">Indian Statutory Schemes</h2>
			<p class="muted mt-1.5 text-xs leading-relaxed">
				Sovereign capital preservation through PPF, NPS, SSY, SCSS, and SGB. Verified official interest rates, Section 80C/80CCD benefits, and maturity compounding.
			</p>
		</article>
	</section>

	<!-- Live Statutory Schemes Highlight Showcase -->
	<section class="card p-6">
		<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-4">
			<div>
				<div class="flex items-center gap-2">
					<span class="rounded bg-brand/10 border border-brand/40 px-2 py-0.5 text-[10px] font-mono font-semibold text-brand-soft uppercase">
						Sovereign Catalog
					</span>
					<span class="text-xs font-mono text-muted">Ministry of Finance &amp; PFRDA Official Schemes</span>
				</div>
				<h2 class="text-lg font-semibold text-ink mt-1">Verified Indian Investment &amp; Savings Schemes</h2>
			</div>
			<a class="btn btn-ghost !px-3 !py-1.5 text-xs font-mono" href="/schemes">
				View All 10 Schemes &rarr;
			</a>
		</div>

		<div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
			{#each SCHEME_HIGHLIGHTS as s (s.name)}
				<div class="rounded border border-line bg-canvas p-4 flex flex-col justify-between hover:border-brand/40 transition-colors">
					<div>
						<div class="flex items-center justify-between">
							<span class="rounded bg-raised px-2 py-0.5 text-[10px] font-mono font-semibold text-brand-soft">{s.tax}</span>
							<span class="text-[11px] font-mono text-muted">{s.tenure}</span>
						</div>
						<h3 class="text-sm font-semibold text-ink mt-2">{s.name}</h3>
						<p class="text-lg font-bold font-mono text-brand-soft mt-1">{s.rate}</p>
						<p class="text-xs text-muted mt-2 leading-relaxed">{s.note}</p>
					</div>
					<div class="mt-3 pt-2.5 border-t border-line text-right">
						<a class="btn btn-ghost !px-2.5 !py-1 text-[11px]" href="/schemes">Calculate</a>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- Step-by-Step Methodology -->
	<section class="card p-6">
		<h2 class="text-base font-semibold text-ink">The FirstRupee Process</h2>
		<ol class="mt-4 grid gap-4 md:grid-cols-4">
			<li class="rounded border border-line bg-canvas p-4">
				<p class="text-[11px] font-mono font-semibold uppercase tracking-wider text-brand-soft">Step 01</p>
				<h3 class="mt-1 font-semibold text-ink text-sm">Describe Your Finances</h3>
				<p class="muted mt-1.5 text-xs leading-relaxed">Capture income, essential outflows, debt commitments, and liquid reserves without double-counting a single rupee.</p>
			</li>
			<li class="rounded border border-line bg-canvas p-4">
				<p class="text-[11px] font-mono font-semibold uppercase tracking-wider text-brand-soft">Step 02</p>
				<h3 class="mt-1 font-semibold text-ink text-sm">Audit Readiness</h3>
				<p class="muted mt-1.5 text-xs leading-relaxed">Evaluate emergency runway, debt burden, and solvency. Identify blockers before exposing savings to capital risk.</p>
			</li>
			<li class="rounded border border-line bg-canvas p-4">
				<p class="text-[11px] font-mono font-semibold uppercase tracking-wider text-brand-soft">Step 03</p>
				<h3 class="mt-1 font-semibold text-ink text-sm">Two-Sided Research</h3>
				<p class="muted mt-1.5 text-xs leading-relaxed">Cross-examine investments using live historical NSE &amp; AMFI market data and audited annual report filings.</p>
			</li>
			<li class="rounded border border-line bg-canvas p-4">
				<p class="text-[11px] font-mono font-semibold uppercase tracking-wider text-brand-soft">Step 04</p>
				<h3 class="mt-1 font-semibold text-ink text-sm">Deploy With Discipline</h3>
				<p class="muted mt-1.5 text-xs leading-relaxed">Allocate across core index funds, sovereign government schemes, and gold hedge in strict alignment with your capacity.</p>
			</li>
		</ol>
	</section>
</div>
