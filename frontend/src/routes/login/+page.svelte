<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, ApiError } from '$lib/api/client';
	import { applySignIn, loadProfiles } from '$lib/stores/session.svelte';

	let email = $state('');
	let password = $state('');
	let busy = $state(false);
	let error = $state('');

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = '';
		try {
			const res = await api.login({ email, password });
			applySignIn(res.user, res.csrf_token);
			await loadProfiles();
			const next = page.url.searchParams.get('next') ?? '/dashboard';
			await goto(next.startsWith('/') && !next.startsWith('//') ? next : '/dashboard');
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Sign-in failed. Please try again.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Sign in — FirstRupee</title></svelte:head>

<div class="mx-auto max-w-md space-y-6 pt-8">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">Sign in</h1>
		<p class="muted mt-2">Your profiles, research and statutory schemes are private to your account.</p>
	</div>
	<form class="card space-y-4" onsubmit={submit} novalidate>
		<div>
			<label class="field-label" for="email">Email</label>
			<input id="email" class="field-input" type="email" autocomplete="email" required bind:value={email} />
		</div>
		<div>
			<label class="field-label" for="password">Password</label>
			<input id="password" class="field-input" type="password" autocomplete="current-password" required bind:value={password} />
		</div>
		{#if error}<p class="field-error" role="alert">{error}</p>{/if}
		<button class="btn btn-primary w-full" type="submit" disabled={busy || !email || !password}>{busy ? 'Signing in…' : 'Sign in'}</button>
	</form>
	<p class="muted text-center">New here? <a class="text-brand-soft underline" href="/register">Create an account</a> to start your financial assessment.</p>
</div>
