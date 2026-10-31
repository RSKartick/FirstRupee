<script lang="ts">
	import '../app.css';
	import { onMount, type Snippet } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { session, loadSession, loadProfiles, selectProfile, signOut } from '$lib/stores/session.svelte';
	import AssistantPanel from '$lib/components/AssistantPanel.svelte';
	import {
		Activity,
		FlaskConical,
		FileText,
		LayoutDashboard,
		LogOut,
		MessageCircle,
		Search,
		ShieldCheck,
		Target,
		Clock
	} from 'lucide-svelte';

	let { children }: { children: Snippet } = $props();

	const PUBLIC_PATHS = ['/', '/login', '/register'];
	const NAV = [
		{ href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
		{ href: '/financial-dna', label: 'Financial DNA', icon: ShieldCheck },
		{ href: '/explorer', label: 'Explorer', icon: Search },
		{ href: '/research', label: 'Research', icon: FlaskConical },
		{ href: '/timing', label: 'Three Clocks', icon: Clock },
		{ href: '/simulator', label: 'Simulator', icon: Activity },
		{ href: '/passports', label: 'Passports', icon: FileText }
	];

	let assistantOpen = $state(false);
	const isPublic = $derived(PUBLIC_PATHS.includes(page.url.pathname));
	const isActive = (href: string) => page.url.pathname === href || page.url.pathname.startsWith(`${href}/`);

	onMount(async () => {
		await loadSession();
		if (session.user) {
			try {
				await loadProfiles();
			} catch {
				// Profile list failure is shown on the pages that need it.
			}
		}
	});

	$effect(() => {
		if (session.ready && !session.user && !isPublic) {
			void goto(`/login?next=${encodeURIComponent(page.url.pathname)}`);
		}
	});

	async function onProfileChange(event: Event) {
		const value = Number((event.currentTarget as HTMLSelectElement).value);
		selectProfile(Number.isFinite(value) && value > 0 ? value : null);
	}

	async function onSignOut() {
		await signOut();
		await goto('/');
	}
</script>

<svelte:head>
	<title>FirstRupee - Invest with understanding, not uncertainty</title>
</svelte:head>

<div class="min-h-screen bg-canvas">
	{#if !isPublic}
		<header class="sticky top-0 z-40 border-b border-line bg-canvas/90 backdrop-blur no-print">
			<div class="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
				<a href="/dashboard" class="flex items-center gap-2.5">
					<span class="flex h-8 w-8 items-center justify-center rounded-lg bg-brand/15 text-sm font-bold text-brand-soft">₹1</span>
					<span class="leading-tight">
						<span class="block text-sm font-semibold">FirstRupee</span>
						<span class="hidden text-[10px] uppercase tracking-[0.14em] text-muted sm:block">Decision intelligence</span>
					</span>
				</a>

				<nav class="scroll-x ml-auto flex items-center gap-1 overflow-x-auto" aria-label="Main">
					{#each NAV as item (item.href)}
						{@const Icon = item.icon}
						<a
							href={item.href}
							aria-current={isActive(item.href) ? 'page' : undefined}
							class="flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors {isActive(item.href) ? 'bg-raised text-brand-soft' : 'text-muted hover:bg-raised/60 hover:text-ink'}"
						>
							<Icon size={14} />{item.label}
						</a>
					{/each}
				</nav>

				<div class="flex items-center gap-2">
					{#if session.profiles.length > 0}
						<label class="sr-only" for="profile-switch">Active profile</label>
						<select id="profile-switch" class="field-input !w-auto !py-1.5 text-[13px]" value={session.activeProfileId ?? ''} onchange={onProfileChange}>
							{#each session.profiles as profile (profile.id)}
								<option value={profile.id}>{profile.display_name}</option>
							{/each}
						</select>
					{/if}
					<button class="btn !px-3 !py-1.5 text-[13px]" onclick={() => (assistantOpen = true)}><MessageCircle size={14} />Ask</button>
					<button class="btn btn-ghost !px-2 !py-1.5" onclick={onSignOut} aria-label="Sign out"><LogOut size={16} /></button>
				</div>
			</div>
			<div class="mx-auto max-w-7xl px-4 pb-2 text-[11px] text-muted sm:px-6">
				{#if session.user}
					Signed in as {session.user.display_name}{session.user.is_guest ? ' (private case-study workspace)' : ''}.
				{/if}
				Every figure is computed by the deterministic backend engines using NSE and AMFI market data (with deterministic offline fallback when feeds are unreachable).
			</div>
		</header>
	{/if}

	<main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
		{#if !session.ready && !isPublic}
			<p class="muted" role="status">Loading your workspace...</p>
		{:else if session.user || isPublic}
			{@render children()}
		{/if}
	</main>

	<footer class="mt-12 border-t border-line no-print">
		<div class="mx-auto max-w-7xl space-y-2 px-4 py-8 text-[12px] leading-relaxed text-muted sm:px-6">
			<p class="font-medium text-ink">FirstRupee is educational decision support, not a brokerage or trade execution platform.</p>
			<p>
				Market data is sourced from public NSE / Yahoo Finance feeds and AMFI mutual fund NAV disclosures (MFAPI.in), with a deterministic baseline series used when running offline.
				All readiness classifications, risk scores and numerical portfolio allocations are deterministic rule-based calculations.
			</p>
		</div>
	</footer>
</div>

{#if assistantOpen}
	<AssistantPanel onclose={() => (assistantOpen = false)} />
{/if}
