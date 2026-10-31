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
		Landmark,
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
		{ href: '/schemes', label: 'Schemes', icon: Landmark }
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
		<header class="sticky top-0 z-40 border-b border-line bg-canvas/90 backdrop-blur-md no-print">
			<div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
				<a href="/dashboard" class="flex items-center gap-3 transition-opacity hover:opacity-90">
					<img src="/logo.png" alt="FirstRupee Logo" class="h-9 w-auto object-contain" />
					<span class="leading-tight">
						<span class="block text-[15px] font-bold tracking-tight text-ink">FirstRupee</span>
						<span class="hidden text-[10px] font-semibold uppercase tracking-[0.16em] text-brand-soft sm:block">Decision Intelligence</span>
					</span>
				</a>

				<nav class="scroll-x flex items-center gap-1.5 overflow-x-auto" aria-label="Main">
					{#each NAV as item (item.href)}
						{@const Icon = item.icon}
						<a
							href={item.href}
							aria-current={isActive(item.href) ? 'page' : undefined}
							class="flex items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 py-1.5 text-[12.5px] transition-colors {isActive(item.href) ? 'bg-raised text-ink border border-line font-medium' : 'text-muted hover:bg-raised/60 hover:text-ink'}"
						>
							<Icon size={14} />{item.label}
						</a>
					{/each}
				</nav>

				<div class="flex items-center gap-2">
					<div class="hidden items-center gap-1.5 rounded border border-line bg-raised px-2 py-0.5 text-[11px] font-mono xl:flex">
						<span class="text-brand-soft font-semibold">LIVE</span>
						<span class="text-muted">FEEDS</span>
					</div>
					{#if session.profiles.length > 0}
						<label class="sr-only" for="profile-switch">Active profile</label>
						<select id="profile-switch" class="field-input !w-auto !py-1.5 !px-2.5 text-[12.5px] font-medium" value={session.activeProfileId ?? ''} onchange={onProfileChange}>
							{#each session.profiles as profile (profile.id)}
								<option value={profile.id}>{profile.display_name}</option>
							{/each}
						</select>
					{/if}
					<button class="btn !px-3 !py-1.5 text-[12.5px] font-semibold" onclick={() => (assistantOpen = true)}>
						<MessageCircle size={14} class="text-brand-soft" />Ask
					</button>
					<button class="btn btn-ghost !px-2 !py-1.5 text-muted hover:text-ink" onclick={onSignOut} aria-label="Sign out">
						<LogOut size={16} />
					</button>
				</div>
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

	<footer class="mt-16 border-t border-line/60 bg-raised/20 no-print">
		<div class="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-8 text-[12px] text-muted sm:flex-row sm:px-6">
			<div class="flex items-center gap-3">
				<img src="/logo.png" alt="FirstRupee Logo" class="h-6 w-auto opacity-80 object-contain" />
				<div>
					<p class="font-semibold text-ink">FirstRupee — Educational Decision Support</p>
					<p class="text-[11px] text-muted">Not a brokerage or trade execution platform.</p>
				</div>
			</div>
			<p class="text-center text-[11px] sm:text-right text-muted max-w-md">
				Market data sourced live from public NSE / Yahoo Finance feeds and AMFI disclosures (MFAPI.in).
				Rule-based deterministic engine.
			</p>
		</div>
	</footer>
</div>

{#if assistantOpen}
	<AssistantPanel onclose={() => (assistantOpen = false)} />
{/if}
